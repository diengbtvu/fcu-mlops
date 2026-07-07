from flask import Blueprint, request, jsonify, send_from_directory, abort
from app.middlewares.auth import token_required
import json
import os
import shutil
import threading
from datetime import datetime
import traceback
from pathlib import Path
from typing import Any, Dict
from zipfile import ZIP_DEFLATED, ZipFile
from app.utils.database_utils import DatabaseUtils
from app.utils.progress_tracker import TrainingProgressTracker
from app.utils.mlflow_tracking import configure_mlflow_tracking_uri
from app.utils.report_explainer import (
    GROQ_REPORT_MODELS,
    generate_report_explanations,
    update_report_explanation_status,
)
from app.utils.report_benchmark import (
    publish_benchmark_results,
    run_report_benchmark,
    update_report_benchmark_status,
)
from app.utils.training_report import generate_training_report
from groq_key_pool import parse_groq_api_keys
import sys
import mlflow
import mlflow.sklearn
import mlflow.xgboost

# Append the base directory to the path for module imports
current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
sys.path.append(project_root)
REPORTS_ROOT = os.path.join(project_root, "app", "reports")

# Import paper-aligned training pipeline
from ml_train.train_pipeline import (
    BEST_MODEL_FILENAME,
    inspect_dataset_file,
    train_and_save_model,
)

train_bp = Blueprint('train', __name__, url_prefix='/train')
LLM_MODEL_ALLOWLIST = {
    "groq": set(GROQ_REPORT_MODELS),
}

# Try to import swagger decorator
try:
    from flasgger import swag_from
    HAS_SWAGGER = True
except ImportError:
    def swag_from(spec):
        def decorator(f):
            return f
        return decorator
    HAS_SWAGGER = False


def _get_request_data() -> Dict[str, Any]:
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict(flat=True)


def _coerce_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _resolve_llm_config(data: Dict[str, Any]) -> tuple[str | None, str | None]:
    provider = str(
        data.get("llm_provider")
        or data.get("report_llm_provider")
        or "groq"
    ).strip().lower() or "groq"
    model = str(
        data.get("llm_model")
        or data.get("report_llm_model")
        or ""
    ).strip() or None

    if provider not in ("groq", "openai"):
        raise ValueError("llm_provider must be 'groq' or 'openai'.")
    if provider in LLM_MODEL_ALLOWLIST and model:
        allowed_models = LLM_MODEL_ALLOWLIST[provider]
        if model not in allowed_models:
            raise ValueError(
                f"Unsupported {provider} llm_model. Allowed values: "
                + ", ".join(sorted(allowed_models))
            )
    return provider, model


def _resolve_training_input(data: Dict[str, Any]) -> tuple[Any, str]:
    uploaded_file = request.files.get("dataset_file")
    if uploaded_file:
        return uploaded_file, uploaded_file.filename or "uploaded dataset"

    dataset_path = str(data.get("dataset_path", "")).strip()
    if not dataset_path:
        raise ValueError("Missing required field: dataset_path or dataset_file")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
    return dataset_path, dataset_path


def _validate_dataset_extension(source_name: str) -> None:
    if not str(source_name).lower().endswith((".csv", ".xls", ".xlsx")):
        raise ValueError(
            "Unsupported dataset format. Only .csv, .xls, and .xlsx are allowed."
        )


def _copy_source_dataset_to_report_dir(
    file_input: Any,
    source_name: str,
    report_dir: str,
) -> None:
    dataset_filename = os.path.basename(str(source_name).strip()) or "input_dataset"
    destination_path = os.path.join(report_dir, dataset_filename)

    if isinstance(file_input, str) and os.path.exists(file_input):
        shutil.copy2(file_input, destination_path)
        return

    stream = getattr(file_input, "stream", file_input)
    if hasattr(stream, "seek"):
        stream.seek(0)
    file_bytes = stream.read()
    if hasattr(stream, "seek"):
        stream.seek(0)

    with open(destination_path, "wb") as handle:
        handle.write(file_bytes)


def _materialize_training_bundle(
    report_info: Dict[str, Any] | None,
    pipeline_result: Dict[str, Any],
    runtime: Dict[str, Any],
    file_input: Any,
    source_name: str,
    selected_sheet: str | None,
) -> Dict[str, Any] | None:
    if not isinstance(report_info, dict):
        return report_info

    report_id = str(report_info.get("report_id") or "").strip()
    if not report_id:
        return report_info

    report_dir = os.path.abspath(os.path.join(REPORTS_ROOT, report_id))
    reports_root = os.path.abspath(REPORTS_ROOT)
    if not report_dir.startswith(reports_root + os.sep):
        return report_info

    os.makedirs(report_dir, exist_ok=True)

    files = dict(report_info.get("files") or {})
    artifact_paths = pipeline_result.get("artifacts") or {}
    copied_artifact_files: Dict[str, str] = {}

    for artifact_key, artifact_path in artifact_paths.items():
        if not artifact_path or not os.path.exists(artifact_path):
            continue
        artifact_filename = os.path.basename(artifact_path)
        destination_path = os.path.join(report_dir, artifact_filename)
        if os.path.abspath(artifact_path) != os.path.abspath(destination_path):
            shutil.copy2(artifact_path, destination_path)
        artifact_file_key = Path(artifact_filename).stem
        if artifact_key == "summary_path":
            artifact_file_key = "best_model_summary"
        copied_artifact_files[artifact_file_key] = artifact_filename

    try:
        _copy_source_dataset_to_report_dir(file_input, source_name, report_dir)
    except Exception as dataset_copy_error:
        print(f"⚠️ Could not copy source dataset into report bundle: {dataset_copy_error}")

    cleaned_df = runtime.get("cleaned_df")
    if hasattr(cleaned_df, "to_csv"):
        cleaned_df.to_csv(
            os.path.join(report_dir, "preprocessed_training_data.csv"),
            index=False,
        )

    bundle_manifest = {
        "created_at": datetime.now().isoformat(),
        "source_name": source_name,
        "selected_sheet": selected_sheet,
        "best_model": pipeline_result.get("best_model"),
        "best_model_type": pipeline_result.get("best_model_type"),
        "r2": pipeline_result.get("r2"),
        "mse": pipeline_result.get("mse"),
        "rows_after_preprocessing": pipeline_result.get("rows_after_preprocessing"),
        "top_features": pipeline_result.get("top_features"),
        "report_id": report_id,
        "report_route_prefix": report_info.get("route_prefix"),
    }
    with open(
        os.path.join(report_dir, "bundle_manifest.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(bundle_manifest, handle, ensure_ascii=False, indent=2)

    zip_filename = "training_bundle.zip"
    zip_path = os.path.join(report_dir, zip_filename)
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zip_handle:
        for entry_name in sorted(os.listdir(report_dir)):
            if entry_name == zip_filename or entry_name.startswith("."):
                continue
            entry_path = os.path.join(report_dir, entry_name)
            if os.path.isfile(entry_path):
                zip_handle.write(entry_path, arcname=entry_name)

    files["training_bundle_zip"] = zip_filename
    files.update(copied_artifact_files)
    report_info["files"] = files

    summary_path = os.path.join(report_dir, "summary.json")
    if os.path.exists(summary_path):
        try:
            with open(summary_path, "r", encoding="utf-8") as handle:
                summary_payload = json.load(handle)
            summary_payload["files"] = files
            with open(summary_path, "w", encoding="utf-8") as handle:
                json.dump(summary_payload, handle, ensure_ascii=False, indent=2)
        except Exception as summary_error:
            print(f"⚠️ Could not update report summary with bundle files: {summary_error}")

    return report_info


def _read_report_summary(summary_path: str) -> Dict[str, Any]:
    if not os.path.exists(summary_path):
        return {}
    try:
        with open(summary_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _reconcile_report_summary_state(report_dir: str) -> None:
    summary_path = os.path.join(report_dir, "summary.json")
    summary = _read_report_summary(summary_path)
    if not summary:
        return

    report_id = os.path.basename(report_dir.rstrip(os.sep))
    report_info: Dict[str, Any] = {
        "report_id": report_id,
        "files": dict(summary.get("files") or {}),
        "selected_benchmark_explanations": summary.get("selected_benchmark_explanations"),
    }

    llm_path = os.path.join(report_dir, "llm_explanations.json")
    llm_status = summary.get("llm_explanations_status")
    if os.path.exists(llm_path):
        report_info["files"]["llm_explanations"] = "llm_explanations.json"
        if not isinstance(llm_status, dict) or str(llm_status.get("status") or "").strip().lower() != "success":
            existing_started_at = (
                llm_status.get("started_at")
                if isinstance(llm_status, dict)
                else None
            )
            update_report_explanation_status(
                report_info=report_info,
                status="success",
                message="AI explanations generated successfully.",
                report_root=REPORTS_ROOT,
                started_at=existing_started_at,
                progress=100,
                phase="completed",
                step_index=(llm_status or {}).get("step_index") if isinstance(llm_status, dict) else None,
                total_steps=(llm_status or {}).get("total_steps") if isinstance(llm_status, dict) else None,
            )

    benchmark_dir = os.path.join(report_dir, "benchmark_eval")
    leaderboard_path = os.path.join(benchmark_dir, "scores", "leaderboard.json")
    run_metadata_path = os.path.join(benchmark_dir, "run_metadata.json")
    benchmark_status = summary.get("benchmark_status")
    if os.path.exists(leaderboard_path):
        publish_benchmark_results(
            report_info=report_info,
            report_root=REPORTS_ROOT,
            benchmark_dirname="benchmark_eval",
        )
        existing_started_at = (
            benchmark_status.get("started_at")
            if isinstance(benchmark_status, dict)
            else None
        )
        update_report_benchmark_status(
            report_info=report_info,
            status="success",
            message="Benchmark evaluation completed successfully.",
            report_root=REPORTS_ROOT,
            started_at=existing_started_at,
            progress=100,
            phase="completed",
            step_index=3,
            total_steps=3,
            current_items=["leaderboard", "run metadata"],
            output_dir="benchmark_eval",
        )
    elif os.path.exists(run_metadata_path):
        benchmark_status_value = (
            str(benchmark_status.get("status") or "").strip().lower()
            if isinstance(benchmark_status, dict)
            else ""
        )
        if benchmark_status_value in {"", "pending"}:
            existing_started_at = (
                benchmark_status.get("started_at")
                if isinstance(benchmark_status, dict)
                else None
            )
            update_report_benchmark_status(
                report_info=report_info,
                status="pending",
                message="Benchmark evaluation is running on generated outputs.",
                report_root=REPORTS_ROOT,
                started_at=existing_started_at,
                progress=90,
                phase="finalizing",
                step_index=3,
                total_steps=3,
                current_items=["leaderboard", "run metadata"],
                output_dir="benchmark_eval",
            )


def _report_dir_for_id(report_id: str) -> str:
    normalized_report_id = str(report_id or "").strip()
    if not normalized_report_id:
        raise ValueError("Training report metadata is missing report_id.")
    return os.path.join(REPORTS_ROOT, normalized_report_id)


def _load_existing_report_bundle(report_id: str) -> tuple[str, Dict[str, Any], Dict[str, Any]]:
    report_dir = _report_dir_for_id(report_id)
    summary_path = os.path.join(report_dir, "summary.json")
    summary = _read_report_summary(summary_path)
    report_info: Dict[str, Any] = {
        "report_id": report_id,
        "route_prefix": f"/train/reports/{report_id}",
        "files": dict(summary.get("files") or {}),
    }
    if isinstance(summary.get("selected_benchmark_explanations"), dict):
        report_info["selected_benchmark_explanations"] = summary["selected_benchmark_explanations"]
    return report_dir, summary, report_info


def _resume_pipeline_result_from_summary(report_dir: str, summary: Dict[str, Any]) -> Dict[str, Any]:
    files = dict(summary.get("files") or {})
    best_model_summary = _read_report_summary(
        os.path.join(report_dir, str(files.get("best_model_summary") or ""))
    )
    gra_payload = _read_report_summary(
        os.path.join(report_dir, str(files.get("gra_ranking") or ""))
    )

    metrics = summary.get("selected_model_metrics")
    if not isinstance(metrics, dict) or not metrics:
        metrics = best_model_summary.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        metrics = {
            "r2_score": best_model_summary.get("r2"),
            "mse": best_model_summary.get("mse"),
            "mae": best_model_summary.get("mae"),
            "rmse": best_model_summary.get("rmse"),
        }

    gra_ranking = gra_payload.get("ranking")
    if not isinstance(gra_ranking, list):
        gra_ranking = best_model_summary.get("gra_ranking")
    if not isinstance(gra_ranking, list):
        gra_ranking = []

    top_features = summary.get("top_features")
    if not isinstance(top_features, list):
        top_features = best_model_summary.get("top_features")
    if not isinstance(top_features, list):
        top_features = []

    selected_sheet = (
        summary.get("selected_sheet")
        or best_model_summary.get("selected_sheet")
        or best_model_summary.get("sheet_name")
    )

    return {
        "best_model": (
            summary.get("selected_model_name")
            or best_model_summary.get("best_model")
            or best_model_summary.get("model_name")
        ),
        "selected_sheet": selected_sheet,
        "rows_after_preprocessing": (
            summary.get("rows_after_preprocessing")
            or best_model_summary.get("rows_after_preprocessing")
            or best_model_summary.get("total_samples")
        ),
        "top_features": top_features,
        "metrics": metrics,
        "gra_ranking": gra_ranking,
    }


def _start_async_report_post_processing_resume(
    report_info: Dict[str, Any],
    pipeline_result: Dict[str, Any],
    llm_provider: str | None,
    llm_model: str | None,
    groq_api_keys: Any | None = None,
) -> None:
    report_id = str(report_info.get("report_id") or "").strip()
    report_dir = _report_dir_for_id(report_id)
    llm_path = os.path.join(report_dir, "llm_explanations.json")
    leaderboard_path = os.path.join(report_dir, "benchmark_eval", "scores", "leaderboard.json")

    def _runner() -> None:
        llm_exists = os.path.exists(llm_path)
        try:
            if not llm_exists:
                started_at = datetime.now().isoformat()
                update_report_explanation_status(
                    report_info=report_info,
                    status="pending",
                    message="AI explanations are queued and will resume shortly.",
                    report_root=REPORTS_ROOT,
                    started_at=started_at,
                    progress=0,
                    phase="queued",
                )
                update_report_benchmark_status(
                    report_info=report_info,
                    status="pending",
                    message="Benchmark evaluation is queued and will resume after AI explanations finish.",
                    report_root=REPORTS_ROOT,
                    started_at=started_at,
                    progress=0,
                    phase="queued",
                    step_index=1,
                    total_steps=3,
                    current_items=["waiting for AI explanations"],
                    output_dir="benchmark_eval",
                    retry_payload={},
                )
                explanation_payload = generate_report_explanations(
                    report_info=report_info,
                    pipeline_result=pipeline_result,
                    runtime=None,
                    report_root=REPORTS_ROOT,
                    llm_provider=llm_provider,
                    llm_model=llm_model,
                    groq_api_keys=groq_api_keys,
                )
                if explanation_payload:
                    report_info["llm_explanations"] = explanation_payload
            else:
                update_report_explanation_status(
                    report_info=report_info,
                    status="success",
                    message="AI explanations generated successfully.",
                    report_root=REPORTS_ROOT,
                    progress=100,
                    phase="completed",
                )

            if os.path.exists(leaderboard_path):
                publish_benchmark_results(
                    report_info=report_info,
                    report_root=REPORTS_ROOT,
                    benchmark_dirname="benchmark_eval",
                )
                update_report_benchmark_status(
                    report_info=report_info,
                    status="success",
                    message="Benchmark evaluation completed successfully.",
                    report_root=REPORTS_ROOT,
                    progress=100,
                    phase="completed",
                    step_index=3,
                    total_steps=3,
                    current_items=["leaderboard", "run metadata"],
                    output_dir="benchmark_eval",
                    retry_payload={},
                )
                return

            run_report_benchmark(
                report_info=report_info,
                report_root=REPORTS_ROOT,
                llm_provider=llm_provider,
                llm_model=llm_model,
                groq_api_keys=groq_api_keys,
            )
            print(f"🔁 Report post-processing resumed for {report_id}")
        except Exception as exc:
            if not llm_exists:
                update_report_explanation_status(
                    report_info=report_info,
                    status="error",
                    message=str(exc),
                    report_root=REPORTS_ROOT,
                    phase="error",
                )
            else:
                update_report_benchmark_status(
                    report_info=report_info,
                    status="error",
                    message=str(exc),
                    report_root=REPORTS_ROOT,
                    progress=100,
                    phase="error",
                    step_index=3,
                    total_steps=3,
                    output_dir="benchmark_eval",
                    retry_payload={},
                )
            print(f"⚠️ Report post-processing resume failed for {report_id}: {exc}")

    threading.Thread(target=_runner, daemon=True).start()


def _build_progress_callback(session_id: str | None) -> Any:
    if not session_id:
        return None

    tracker = TrainingProgressTracker()

    def _callback(progress: float, message: str) -> None:
        tracker.update_progress(session_id, progress=progress, message=message)

    return _callback


def _start_async_report_explanations(
    report_info: Dict[str, Any],
    pipeline_result: Dict[str, Any],
    runtime: Dict[str, Any],
    source_name: str,
    selected_sheet: str | None,
    llm_provider: str | None,
    llm_model: str | None,
    groq_api_keys: Any | None = None,
) -> None:
    started_at = datetime.now().isoformat()
    update_report_explanation_status(
        report_info=report_info,
        status="pending",
        message="AI explanations are queued and will start shortly.",
        report_root=REPORTS_ROOT,
        started_at=started_at,
        progress=0,
        phase="queued",
    )
    update_report_benchmark_status(
        report_info=report_info,
        status="pending",
        message="Benchmark evaluation is queued and will start after AI explanations finish.",
        report_root=REPORTS_ROOT,
        started_at=started_at,
        progress=0,
        phase="queued",
        step_index=1,
        total_steps=3,
        current_items=["waiting for AI explanations"],
        output_dir="benchmark_eval",
    )

    def _runner() -> None:
        try:
            explanation_payload = generate_report_explanations(
                report_info=report_info,
                pipeline_result=pipeline_result,
                runtime=runtime,
                report_root=REPORTS_ROOT,
                llm_provider=llm_provider,
                llm_model=llm_model,
                groq_api_keys=groq_api_keys,
            )
            if explanation_payload:
                report_info["llm_explanations"] = explanation_payload
                report_id = str(report_info.get("report_id") or "").strip()
                source_path = os.path.join(REPORTS_ROOT, report_id, os.path.basename(source_name))
                bundle_source = source_path if os.path.exists(source_path) else source_name
                _materialize_training_bundle(
                    report_info=report_info,
                    pipeline_result=pipeline_result,
                    runtime=runtime,
                    file_input=bundle_source,
                    source_name=source_name,
                    selected_sheet=selected_sheet,
                )
                try:
                    run_report_benchmark(
                        report_info=report_info,
                        report_root=REPORTS_ROOT,
                        llm_provider=llm_provider,
                        llm_model=llm_model,
                        groq_api_keys=groq_api_keys,
                    )
                except Exception as benchmark_error:
                    print(f"⚠️ Async benchmark evaluation failed: {benchmark_error}")
                print(f"🤖 AI report explanations generated for {report_info.get('report_id')}")
        except Exception as explanation_error:
            update_report_explanation_status(
                report_info=report_info,
                status="error",
                message=str(explanation_error),
                report_root=REPORTS_ROOT,
                started_at=started_at,
                phase="error",
            )
            update_report_benchmark_status(
                report_info=report_info,
                status="error",
                message=(
                    "Benchmark evaluation was not completed because the AI explanation step failed: "
                    f"{explanation_error}"
                ),
                report_root=REPORTS_ROOT,
                started_at=started_at,
                progress=100,
                phase="blocked",
                step_index=1,
                total_steps=3,
                current_items=["AI explanations"],
                output_dir="benchmark_eval",
            )
            print(f"⚠️ Async AI explanation generation failed: {explanation_error}")

    threading.Thread(target=_runner, daemon=True).start()


@train_bp.route('/inspect', methods=['POST'])
def inspect_dataset():
    """Inspect workbook sheets, preview rows, and validate required columns."""
    try:
        uploaded_file = request.files.get("dataset_file")
        if uploaded_file is None:
            return jsonify({"success": False, "error": "Missing required file: dataset_file"}), 400

        source_name = uploaded_file.filename or "uploaded dataset"
        _validate_dataset_extension(source_name)

        sheet_name = str(request.form.get("sheet_name") or "").strip() or None
        preview_rows = _coerce_int(request.form.get("preview_rows"), 10) or 10

        inspection = inspect_dataset_file(
            uploaded_file,
            sheet_name=sheet_name,
            preview_rows=max(1, min(preview_rows, 20)),
        )
        return jsonify({"success": True, **inspection}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@train_bp.route('/model', methods=['POST'])
# @token_required  # Temporarily disabled for development
@swag_from({
    'tags': ['Training'],
    'summary': 'Train the paper-aligned best-model workflow',
    'description': 'Run the Wang et al. (2024) workflow end-to-end, compare all 5 models, and save the best one.',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'description': 'Training parameters',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['dataset_path'],
                'properties': {
                    'dataset_path': {
                        'type': 'string',
                        'description': 'Absolute path to the dataset file (.csv, .xls, or .xlsx)'
                    },
                    'sheet_name': {
                        'type': 'string',
                        'description': 'Excel sheet to use when the uploaded workbook contains multiple sheets'
                    },
                    'model_name': {
                        'type': 'string',
                        'description': 'Custom name for the trained model (optional)'
                    },
                    'training_scope': {
                        'type': 'string',
                        'default': 'all_models_compare',
                        'description': 'single_model (no benchmark comparison) or all_models_compare'
                    },
                    'n_estimators': {
                        'type': 'integer',
                        'default': 100,
                        'description': 'Number of trees in the forest'
                    },
                    'max_depth': {
                        'type': 'integer',
                        'default': None,
                        'description': 'Maximum depth of trees'
                    },
                    'test_size': {
                        'type': 'number',
                        'default': 0.2,
                        'minimum': 0.1,
                        'maximum': 0.5,
                        'description': 'Proportion of dataset for testing'
                    },
                    'random_state': {
                        'type': 'integer',
                        'default': 42,
                        'description': 'Random state for reproducibility'
                    },
                    'dataset_id': {
                        'type': 'integer',
                        'description': 'Optional dataset ID for database reference'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Training completed successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'model_path': {'type': 'string'},
                    'metrics': {
                        'type': 'object',
                        'properties': {
                            'r2_score': {'type': 'number'},
                            'rmse': {'type': 'number'},
                            'mae': {'type': 'number'}
                        }
                    },
                    'training_info': {
                        'type': 'object',
                        'properties': {
                            'train_samples': {'type': 'integer'},
                            'test_samples': {'type': 'integer'},
                            'n_features': {'type': 'integer'},
                            'trained_by': {'type': 'string'},
                            'trained_at': {'type': 'string'},
                            'saved_to_database': {'type': 'boolean'}
                        }
                    },
                    'database_id': {'type': 'integer', 'description': 'Database ID of saved model'},
                    'scaler_path': {'type': 'string', 'description': 'Path to saved scaler file'},
                    'model_name': {'type': 'string', 'description': 'Name of the trained model'}
                }
            }
        },
        '400': {'description': 'Bad request - invalid parameters'},
        '401': {'description': 'Unauthorized'},
        '404': {'description': 'Dataset file not found'},
        '500': {'description': 'Training failed'}
    }
})
def train_model():
    """
    Train using the paper-aligned workflow and save the winning model.
    """
    try:
        data = _get_request_data()

        trained_by = _coerce_int(data.get("trained_by"), 1) or 1
        dataset_id = _coerce_int(data.get("dataset_id"))
        session_id = str(data.get("session_id") or "").strip() or None
        sheet_name = str(data.get("sheet_name") or data.get("selected_sheet") or "").strip() or None
        requested_model_type = str(data.get("model_type", "auto_best")).lower().strip()
        training_scope = str(data.get("training_scope", "all_models_compare")).lower().strip()
        test_size = _coerce_float(data.get("test_size"), 0.2) or 0.2
        random_state = _coerce_int(data.get("random_state"), 42) or 42
        model_name = str(
            data.get("model_name")
            or f"Best_Model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ).strip()
        try:
            llm_provider, llm_model = _resolve_llm_config(data)
        except ValueError as config_error:
            return jsonify({"error": str(config_error)}), 400
        groq_api_keys = (
            data.get("groq_api_keys")
            or data.get("groq_api_key_pool")
            or data.get("groq_api_key")
        )
        groq_api_key_count = len(parse_groq_api_keys(groq_api_keys))

        if training_scope not in {"single_model", "all_models_compare"}:
            return jsonify(
                {"error": "training_scope must be one of: single_model, all_models_compare"}
            ), 400
        if not (0.1 <= test_size <= 0.5):
            return jsonify({"error": "test_size must be between 0.1 and 0.5"}), 400

        file_input, source_name = _resolve_training_input(data)
        _validate_dataset_extension(source_name)

        tracker = TrainingProgressTracker()
        if session_id:
            tracker.start_training(session_id)

        progress_callback = _build_progress_callback(session_id)

        mlflow_run_id = None
        mlflow_experiment_id = None
        active_run = None
        experiment_name = "hydrogen_production_training"

        try:
            tracking_info = configure_mlflow_tracking_uri()
            if tracking_info.get("used_fallback"):
                print(
                    f"⚠️ MLflow default directory is not writable, using fallback: "
                    f"{tracking_info.get('tracking_dir')}"
                )
            mlflow.set_experiment(experiment_name)
            active_run = mlflow.start_run(run_name=model_name)
            mlflow.log_param("requested_model_type", requested_model_type)
            mlflow.log_param("effective_workflow", "paper_auto_best")
            mlflow.log_param("training_scope", training_scope)
            mlflow.log_param("test_size", test_size)
            mlflow.log_param("random_state", random_state)
            mlflow.log_param("trained_by", trained_by)
            if "dataset_path" in data:
                mlflow.log_param("dataset_path", data.get("dataset_path"))
            if sheet_name:
                mlflow.log_param("sheet_name", sheet_name)
            if dataset_id is not None:
                mlflow.log_param("dataset_id", dataset_id)
            if llm_provider:
                mlflow.log_param("report_llm_provider", llm_provider)
            if llm_model:
                mlflow.log_param("report_llm_model", llm_model)
        except Exception as mlflow_error:
            print(f"⚠️ MLflow initialization skipped: {mlflow_error}")
            active_run = None

        pipeline_result = train_and_save_model(
            file_input,
            sheet_name=sheet_name,
            progress_callback=progress_callback,
            return_runtime=True,
        )
        runtime = pipeline_result.pop("_runtime", {})
        resolved_sheet = pipeline_result.get("selected_sheet")

        metrics = pipeline_result["metrics"]
        best_model_name = pipeline_result["best_model"]
        best_model_type = pipeline_result["best_model_type"]

        if active_run is not None:
            try:
                mlflow.log_param("winning_model", best_model_name)
                mlflow.log_param("model_type", best_model_type)
                for metric_name, metric_value in metrics.items():
                    mlflow.log_metric(metric_name, float(metric_value))
                artifact_paths = pipeline_result.get("artifacts", {})
                best_model_path = artifact_paths.get("best_model_path")
                best_scaler_x_path = artifact_paths.get("best_scaler_x_path")
                best_scaler_y_path = artifact_paths.get("best_scaler_y_path")

                if runtime.get("best_model_object") is not None:
                    if best_model_type == "xgboost":
                        mlflow.xgboost.log_model(runtime["best_model_object"], artifact_path="model")
                    else:
                        mlflow.sklearn.log_model(runtime["best_model_object"], artifact_path="model")

                if best_scaler_x_path and os.path.exists(best_scaler_x_path):
                    mlflow.log_artifact(best_scaler_x_path, "scaler")
                if best_scaler_y_path and os.path.exists(best_scaler_y_path):
                    mlflow.log_artifact(best_scaler_y_path, "scaler_y")

                for artifact_key in (
                    "summary_path",
                    "gra_ranking_path",
                    "incremental_results_path",
                    "shap_importance_path",
                    "best_model_info_path",
                ):
                    artifact_path = artifact_paths.get(artifact_key)
                    if artifact_path and os.path.exists(artifact_path):
                        mlflow.log_artifact(artifact_path, "paper_training")
                mlflow_run_id = mlflow.active_run().info.run_id
                mlflow_experiment_id = mlflow.active_run().info.experiment_id
                print(f"\n🔗 MLflow Tracking:")
                print(f"   Experiment: {experiment_name}")
                print(f"   Run ID: {mlflow_run_id}")
            except Exception as mlflow_log_error:
                print(f"⚠️ MLflow logging skipped: {mlflow_log_error}")
            finally:
                mlflow.end_run()

        report_info = None
        try:
            if runtime:
                report_info = generate_training_report(
                    model_name=model_name,
                    model_type=best_model_type,
                    trained_model=runtime["best_model_object"],
                    X_train=runtime["X_train_df"],
                    X_test=runtime["X_test_df"],
                    y_train=runtime["y_train_series"],
                    y_test=runtime["y_test_series"],
                    selected_metrics=metrics,
                    gra_ranking=pipeline_result["gra_ranking"],
                    include_comparison=True,
                )
                if isinstance(report_info, dict):
                    report_info["training_scope"] = "all_models_compare"
                    report_info["llm_config"] = {
                        "provider": llm_provider,
                        "model": llm_model,
                        "groq_api_key_count": groq_api_key_count if llm_provider == "groq" else 0,
                    }
                    report_info = _materialize_training_bundle(
                        report_info=report_info,
                        pipeline_result=pipeline_result,
                        runtime=runtime,
                        file_input=file_input,
                        source_name=source_name,
                        selected_sheet=resolved_sheet,
                    )
                    _start_async_report_explanations(
                        report_info=report_info,
                        pipeline_result=pipeline_result,
                        runtime=runtime,
                        source_name=source_name,
                        selected_sheet=resolved_sheet,
                        llm_provider=llm_provider,
                        llm_model=llm_model,
                        groq_api_keys=groq_api_keys,
                    )
                print(f"📊 Training report generated: {report_info.get('route_prefix')}")
        except Exception as report_error:
            print(f"⚠️ Report generation failed: {report_error}")
            report_info = None

        try:
            db_utils = DatabaseUtils()
            if not db_utils.test_connection():
                print("⚠️ Cannot connect to Laravel API - skipping database save")
                model_db_id = None
            else:
                model_info = {
                    "MLMName": model_name,
                    "FilePath": f"models/{BEST_MODEL_FILENAME}",
                    "LibType": "sklearn",
                    "IsActive": True,
                    "MSEValue": round(metrics["mse"], 6),
                    "MAEValue": round(metrics["mae"], 6),
                    "R2Value": round(metrics["r2_score"], 6),
                    "RMSEValue": round(metrics["rmse"], 6),
                    "TrainedBy": trained_by,
                    "DatasetId": dataset_id,
                    "mlflow_run_id": mlflow_run_id,
                    "mlflow_experiment_id": mlflow_experiment_id,
                    "gra_ranking": pipeline_result["gra_ranking"],
                    "training_report": report_info,
                    "auth_token": request.headers.get("Authorization", "").replace("Bearer ", ""),
                }
                db_result = db_utils.save_ml_model_to_db(model_info)
                model_db_id = db_result.get("data", {}).get("id") if db_result else None
        except Exception as db_error:
            print(f"⚠️ Database save error: {db_error}")
            model_db_id = None

        gra_response = {"ranking": pipeline_result["gra_ranking"]}
        response_data = {
            "success": True,
            "status": "success",
            "message": pipeline_result["message"],
            "best_model": best_model_name,
            "top_features": pipeline_result["top_features"],
            "r2": pipeline_result["r2"],
            "mse": pipeline_result["mse"],
            "model_path": pipeline_result["artifacts"]["best_model_path"],
            "scaler_path": pipeline_result["artifacts"]["shared_scaler_path"],
            "model_name": model_name,
            "model_type": best_model_type,
            "requested_model_type": requested_model_type,
            "selected_sheet": resolved_sheet,
            "database_id": model_db_id,
            "mlflow_run_id": mlflow_run_id,
            "mlflow_experiment_id": mlflow_experiment_id,
            "metrics": metrics,
            "gra_ranking": gra_response,
            "report_info": report_info,
            "training_info": {
                "model_type": best_model_type,
                "training_scope": "all_models_compare",
                "lib_type": "sklearn",
                "trained_by": trained_by,
                "trained_at": datetime.now().isoformat(),
                "saved_to_database": model_db_id is not None,
                "report_generated": report_info is not None,
                "rows_after_preprocessing": pipeline_result["rows_after_preprocessing"],
                "selected_sheet": resolved_sheet,
                "source_workflow": "paper_aligned_auto_best",
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "groq_api_key_count": groq_api_key_count if llm_provider == "groq" else 0,
            },
        }

        if session_id:
            tracker.complete_training(
                session_id,
                result=response_data,
                message=(
                    f"Training completed! Best model: {best_model_name} "
                    f"(R²={metrics['r2_score']:.4f})"
                ),
            )

        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"\n❌ Training Error: {str(e)}")
        traceback.print_exc()

        if "active_run" in locals() and active_run is not None:
            try:
                mlflow.end_run(status="FAILED")
            except Exception:
                pass
        
        # Mark training as failed
        if 'session_id' in locals() and session_id:
            tracker = TrainingProgressTracker()
            tracker.fail_training(session_id, error=str(e))
        
        return jsonify({
            'success': False,
            'error': f'Training failed: {str(e)}'
        }), 500


@train_bp.route('/report-post-processing/resume', methods=['POST'])
def resume_report_post_processing():
    data = _get_request_data()
    report_id = str(data.get("report_id") or "").strip()
    if not report_id:
        return jsonify({
            "success": False,
            "error": "Missing required field: report_id",
        }), 400

    try:
        report_dir = _report_dir_for_id(report_id)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    if not os.path.isdir(report_dir):
        return jsonify({
            "success": False,
            "error": f"Report directory not found: {report_id}",
        }), 404

    _reconcile_report_summary_state(report_dir)
    report_dir, summary, report_info = _load_existing_report_bundle(report_id)

    llm_config = summary.get("llm_config") if isinstance(summary.get("llm_config"), dict) else {}
    request_llm_data = dict(data)
    if "llm_provider" not in request_llm_data and llm_config.get("provider"):
        request_llm_data["llm_provider"] = llm_config.get("provider")
    if "llm_model" not in request_llm_data and llm_config.get("model"):
        request_llm_data["llm_model"] = llm_config.get("model")

    try:
        llm_provider, llm_model = _resolve_llm_config(request_llm_data)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    pipeline_result = _resume_pipeline_result_from_summary(report_dir, summary)
    if not str(pipeline_result.get("best_model") or "").strip():
        return jsonify({
            "success": False,
            "error": "The saved report bundle is missing best-model metadata required to resume post-processing.",
        }), 400

    leaderboard_path = os.path.join(report_dir, "benchmark_eval", "scores", "leaderboard.json")
    llm_path = os.path.join(report_dir, "llm_explanations.json")
    if os.path.exists(leaderboard_path) and os.path.exists(llm_path):
        return jsonify({
            "success": True,
            "status": "completed",
            "report_id": report_id,
            "message": "Report post-processing is already completed.",
        }), 200

    _start_async_report_post_processing_resume(
        report_info=report_info,
        pipeline_result=pipeline_result,
        llm_provider=llm_provider,
        llm_model=llm_model,
        groq_api_keys=data.get("groq_api_keys"),
    )
    return jsonify({
        "success": True,
        "status": "queued",
        "report_id": report_id,
        "message": "Report post-processing resume started.",
    }), 202


@train_bp.route('/reports/<report_id>/<path:filename>', methods=['GET'])
def get_training_report_asset(report_id, filename):
    """Serve generated training report assets."""
    reports_root = os.path.abspath(REPORTS_ROOT)
    report_dir = os.path.abspath(os.path.join(reports_root, report_id))

    # Block path traversal
    if not report_dir.startswith(reports_root + os.sep):
        abort(400)
    if not os.path.exists(report_dir):
        abort(404)

    if filename == "summary.json":
        _reconcile_report_summary_state(report_dir)

    return send_from_directory(report_dir, filename)


@train_bp.route('/status', methods=['GET'])
@swag_from({
    'tags': ['Training'],
    'summary': 'Get training service status',
    'description': 'Check if training service is available',
    'responses': {
        '200': {
            'description': 'Service status',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'available_models_dir': {'type': 'string'}
                }
            }
        }
    }
})
def training_status():
    """Check training service status"""
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_model')
    return jsonify({
        'status': 'available',
        'models_directory': model_dir,
        'models_count': len([f for f in os.listdir(model_dir) if f.endswith('.pkl')]) if os.path.exists(model_dir) else 0
    }), 200


@train_bp.route('/models', methods=['GET'])
@token_required
@swag_from({
    'tags': ['Training'],
    'summary': 'List all trained models',
    'description': 'Get list of all trained models in ml_model directory',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': 'List of models',
            'schema': {
                'type': 'object',
                'properties': {
                    'models': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'name': {'type': 'string'},
                                'path': {'type': 'string'},
                                'size': {'type': 'integer'},
                                'created_at': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    }
})
def list_models():
    """List all trained models"""
    try:
        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_model')
        
        if not os.path.exists(model_dir):
            return jsonify({'models': []}), 200
        
        models = []
        for filename in os.listdir(model_dir):
            if filename.endswith('.pkl') and not filename.endswith('_scaler.pkl'):
                filepath = os.path.join(model_dir, filename)
                stat = os.stat(filepath)
                models.append({
                    'name': filename,
                    'path': filepath,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return jsonify({'models': models}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@train_bp.route('/mlflow/experiments', methods=['GET'])
@swag_from({
    'tags': ['MLflow Tracking'],
    'summary': 'Get MLflow experiments',
    'description': 'List all MLflow experiments',
    'responses': {
        '200': {
            'description': 'List of experiments',
            'schema': {
                'type': 'object',
                'properties': {
                    'experiments': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'experiment_id': {'type': 'string'},
                                'name': {'type': 'string'},
                                'artifact_location': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    }
})
def get_mlflow_experiments():
    """Get all MLflow experiments"""
    try:
        configure_mlflow_tracking_uri()
        
        client = mlflow.tracking.MlflowClient()
        experiments = client.search_experiments()
        
        exp_list = []
        for exp in experiments:
            exp_list.append({
                'experiment_id': exp.experiment_id,
                'name': exp.name,
                'artifact_location': exp.artifact_location,
                'lifecycle_stage': exp.lifecycle_stage
            })
        
        return jsonify({'experiments': exp_list}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@train_bp.route('/mlflow/runs', methods=['GET'])
@swag_from({
    'tags': ['MLflow Tracking'],
    'summary': 'Get MLflow runs',
    'description': 'List all MLflow runs for an experiment',
    'parameters': [
        {
            'name': 'experiment_name',
            'in': 'query',
            'type': 'string',
            'required': False,
            'default': 'hydrogen_production_training',
            'description': 'Experiment name to filter runs'
        },
        {
            'name': 'limit',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'default': 10,
            'description': 'Maximum number of runs to return'
        }
    ],
    'responses': {
        '200': {
            'description': 'List of runs',
            'schema': {
                'type': 'object',
                'properties': {
                    'runs': {
                        'type': 'array',
                        'items': {
                            'type': 'object'
                        }
                    }
                }
            }
        }
    }
})
def get_mlflow_runs():
    """Get MLflow runs for an experiment"""
    try:
        # Get query parameters
        experiment_name = request.args.get('experiment_name', 'hydrogen_production_training')
        limit = int(request.args.get('limit', 10))
        
        configure_mlflow_tracking_uri()
        
        # Get experiment
        client = mlflow.tracking.MlflowClient()
        experiment = client.get_experiment_by_name(experiment_name)
        
        if not experiment:
            return jsonify({'error': f'Experiment {experiment_name} not found'}), 404
        
        # Search runs
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            max_results=limit,
            order_by=["start_time DESC"]
        )
        
        runs_list = []
        for run in runs:
            runs_list.append({
                'run_id': run.info.run_id,
                'run_name': run.data.tags.get('mlflow.runName', 'N/A'),
                'status': run.info.status,
                'start_time': datetime.fromtimestamp(run.info.start_time / 1000).isoformat(),
                'end_time': datetime.fromtimestamp(run.info.end_time / 1000).isoformat() if run.info.end_time else None,
                'metrics': run.data.metrics,
                'params': run.data.params,
                'artifact_uri': run.info.artifact_uri
            })
        
        return jsonify({
            'experiment': experiment_name,
            'total_runs': len(runs_list),
            'runs': runs_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
