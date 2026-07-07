from __future__ import annotations

import json

from app.utils.report_explainer import _build_llm_request_payload
from app.utils.report_explainer import _build_response_schema
from app.utils.report_explainer import _get_report_model
from app.utils.report_explainer import _needs_inline_json_schema_instruction
from app.utils.report_explainer import _normalize_asset_explanation_item
from app.utils.report_explainer import _normalize_benchmark_payload
from app.utils.report_explainer import update_report_explanation_status
from openai_rate_control import SharedOpenAIRequestGate


def _anyof_type_sets(schema: object) -> list[set[str]]:
    type_sets: list[set[str]] = []
    if isinstance(schema, dict):
        any_of = schema.get("anyOf")
        if isinstance(any_of, list):
            types = {
                str(item.get("type"))
                for item in any_of
                if isinstance(item, dict) and isinstance(item.get("type"), str)
            }
            if types:
                type_sets.append(types)
        for value in schema.values():
            type_sets.extend(_anyof_type_sets(value))
    elif isinstance(schema, list):
        for item in schema:
            type_sets.extend(_anyof_type_sets(item))
    return type_sets


def test_update_report_explanation_status_tracks_and_clears_retry_payload(tmp_path) -> None:
    report_info = {"report_id": "retry_status_report"}
    report_dir = tmp_path / "retry_status_report"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "summary.json").write_text("{}", encoding="utf-8")

    update_report_explanation_status(
        report_info=report_info,
        status="pending",
        message="Retrying batch 1.",
        report_root=tmp_path,
        progress=25,
        phase="assets",
        retry_payload={
            "attempt": 3,
            "max_attempts": 8,
            "wait_seconds": 18.0,
            "reason": "OpenAI rate limit",
            "status_code": 429,
        },
    )

    summary_path = tmp_path / "retry_status_report" / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    retry = summary["llm_explanations_status"]["retry"]
    assert retry["attempt"] == 3
    assert retry["wait_seconds"] == 18.0

    update_report_explanation_status(
        report_info=report_info,
        status="pending",
        message="Completed batch 1/28.",
        report_root=tmp_path,
        progress=40,
        phase="assets",
    )

    updated = json.loads(summary_path.read_text(encoding="utf-8"))
    assert "retry" not in updated["llm_explanations_status"]


def test_shared_openai_request_gate_honors_shared_cooldown(monkeypatch, tmp_path) -> None:
    gate = SharedOpenAIRequestGate(tmp_path / "openai_gate.json")
    current_time = {"value": 100.0}
    sleeps: list[float] = []

    def fake_time() -> float:
        return current_time["value"]

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        current_time["value"] += seconds

    monkeypatch.setattr("openai_rate_control.time.time", fake_time)
    monkeypatch.setattr("openai_rate_control.time.sleep", fake_sleep)
    monkeypatch.setattr("openai_rate_control.random.uniform", lambda _a, _b: 0.0)

    gate.push_cooldown(12.0)
    with gate.request_slot(6.0, 0.0):
        pass

    assert sleeps == [12.0]


def test_report_explainer_groq_payload_uses_inline_json_for_gpt_oss() -> None:
    response_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "asset_explanations",
            "schema": {
                "type": "object",
                "properties": {"assets": {"type": "object"}},
                "required": ["assets"],
            },
        },
    }

    payload = _build_llm_request_payload(
        provider="groq",
        model="openai/gpt-oss-120b",
        messages=[{"role": "system", "content": "Return JSON only."}],
        response_schema=response_schema,
        max_completion_tokens=1200,
        reasoning_effort="low",
        verbosity="medium",
    )

    assert "response_format" not in payload
    assert payload["reasoning_effort"] == "low"
    assert "verbosity" not in payload


def test_report_explainer_groq_payload_uses_inline_json_for_llama() -> None:
    response_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "asset_explanations",
            "schema": {"type": "object"},
        },
    }

    payload = _build_llm_request_payload(
        provider="groq",
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": "Return JSON only."}],
        response_schema=response_schema,
        max_completion_tokens=1200,
        reasoning_effort="low",
        verbosity="medium",
    )

    assert "response_format" not in payload
    assert "reasoning_effort" not in payload
    assert "verbosity" not in payload


def test_report_explainer_accepts_supported_groq_model_override() -> None:
    assert _get_report_model("groq", "llama-3.3-70b-versatile") == "llama-3.3-70b-versatile"


def test_report_explainer_inlines_schema_for_groq_json_object_mode() -> None:
    assert _needs_inline_json_schema_instruction("groq", "openai/gpt-oss-120b")
    assert _needs_inline_json_schema_instruction("groq", "llama-3.3-70b-versatile")
    assert _needs_inline_json_schema_instruction("ollama", "gemma2:9b")


def test_report_explainer_schema_avoids_ambiguous_integer_number_unions() -> None:
    schema = _build_response_schema(["metrics_overview"], include_overview=False)

    assert all({"integer", "number"} - type_set for type_set in _anyof_type_sets(schema))


def test_report_explainer_normalizes_null_ordered_items() -> None:
    payload = _normalize_benchmark_payload(
        asset_key="metrics_overview",
        raw_payload={
            "explanation_short": "KNN performs best.",
            "explanation_full": "KNN has the strongest score.",
            "claims": [
                {
                    "claim_id": "claim-1",
                    "claim_text": "KNN performs best.",
                    "claim_type": "best_model",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.9,
                    "subject": "KNN",
                    "predicate": "performs best",
                    "object": None,
                    "metric": None,
                    "value": None,
                    "unit": None,
                    "ordered_items": None,
                    "feature_count": None,
                    "hedged": False,
                }
            ],
        },
        english_text="KNN has the strongest score.",
    )

    assert payload["claims"][0]["ordered_items"] == []


def test_report_explainer_falls_back_when_asset_text_or_claims_are_empty() -> None:
    payload = _normalize_asset_explanation_item(
        {
            "key": "fig6c_prediction_time",
            "en": "",
            "zh_TW": "",
            "benchmark_payload": {
                "explanation_short": "KNN tracks the time-series pattern.",
                "explanation_full": "KNN tracks the time-series pattern with visible gaps near peaks.",
                "claims": None,
            },
        }
    )

    assert payload["en"] == "KNN tracks the time-series pattern with visible gaps near peaks."
    assert payload["benchmark_payload"]["claims"] == []
