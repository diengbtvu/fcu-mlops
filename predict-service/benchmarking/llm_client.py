from __future__ import annotations

import copy
import json
import os
import random
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from groq_key_pool import GroqApiKeyPool, groq_api_keys_from_env, parse_groq_api_keys, record_blocked_groq_key
from openai_rate_control import shared_openai_request_gate
from .claim_alignment import (
    claims_payload_to_variable_mentions,
    variable_mentions_to_payload,
)
from .prompts import (
    ARM_INSTRUCTIONS,
    build_claim_extraction_prompt,
    build_explanation_prompt,
    build_prompt_context,
    build_variable_mention_extraction_prompt,
    extract_claim_extraction_context,
    extract_prompt_context,
    extract_variable_mention_context,
)
from .schemas import ArtifactInputs, CANONICAL_CLAIM_TYPES, SUPPORTED_SEMANTIC_LEVELS

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_BENCHMARK_MODEL = os.getenv("OPENAI_BENCHMARK_MODEL", os.getenv("OPENAI_REPORT_MODEL", "gpt-5.2"))
DEFAULT_GROQ_CHAT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_BENCHMARK_MODEL = "openai/gpt-oss-120b"
GROQ_BENCHMARK_MODELS = {
    "openai/gpt-oss-120b": "GPT-OSS 120B",
    "llama-3.3-70b-versatile": "Llama 3.3 70B Versatile",
}
GROQ_BENCHMARK_MODEL = os.getenv("GROQ_BENCHMARK_MODEL", os.getenv("GROQ_REPORT_MODEL", DEFAULT_GROQ_BENCHMARK_MODEL))
GROQ_BENCHMARK_TIMEOUT_SECONDS = max(60, int(os.getenv("GROQ_BENCHMARK_TIMEOUT_SECONDS", "300")))
GROQ_BENCHMARK_MAX_RETRIES = max(1, int(os.getenv("GROQ_BENCHMARK_MAX_RETRIES", "5")))
GROQ_BENCHMARK_RETRY_FOREVER = str(
    os.getenv("GROQ_BENCHMARK_RETRY_FOREVER", "1")
).strip().lower() not in {"0", "false", "no", "off"}
GROQ_BENCHMARK_MIN_REQUEST_INTERVAL_SECONDS = max(
    0.0,
    float(os.getenv("GROQ_BENCHMARK_MIN_REQUEST_INTERVAL_SECONDS", "3")),
)
GROQ_BENCHMARK_MAX_RETRY_WAIT_SECONDS = max(
    1.0,
    float(os.getenv("GROQ_BENCHMARK_MAX_RETRY_WAIT_SECONDS", "3")),
)
GROQ_BENCHMARK_MAX_COMPLETION_TOKENS = max(
    700,
    int(os.getenv("GROQ_BENCHMARK_MAX_COMPLETION_TOKENS", "800")),
)
GROQ_BENCHMARK_RETRY_BACKOFF_SECONDS = max(
    1.0,
    float(os.getenv("GROQ_BENCHMARK_RETRY_BACKOFF_SECONDS", "3")),
)
GROQ_BENCHMARK_RETRY_JITTER_SECONDS = max(
    0.0,
    float(os.getenv("GROQ_BENCHMARK_RETRY_JITTER_SECONDS", "0.5")),
)
GROQ_BENCHMARK_MAX_REQUEST_ATTEMPTS = max(
    1,
    int(os.getenv("GROQ_BENCHMARK_MAX_REQUEST_ATTEMPTS", "3")),
)
OPENAI_BENCHMARK_MAX_RETRIES = max(1, int(os.getenv("OPENAI_BENCHMARK_MAX_RETRIES", "8")))
OPENAI_BENCHMARK_RETRY_BACKOFF_SECONDS = max(
    1.0,
    float(os.getenv("OPENAI_BENCHMARK_RETRY_BACKOFF_SECONDS", "8")),
)
OPENAI_BENCHMARK_MIN_REQUEST_INTERVAL_SECONDS = max(
    0.0,
    float(os.getenv("OPENAI_BENCHMARK_MIN_REQUEST_INTERVAL_SECONDS", "6")),
)
OPENAI_BENCHMARK_RETRY_JITTER_SECONDS = max(
    0.0,
    float(os.getenv("OPENAI_BENCHMARK_RETRY_JITTER_SECONDS", "1.0")),
)
OPENAI_BENCHMARK_TIMEOUT_SECONDS = max(60, int(os.getenv("OPENAI_BENCHMARK_TIMEOUT_SECONDS", "240")))
OLLAMA_BENCHMARK_MODEL = os.getenv("OLLAMA_BENCHMARK_MODEL", os.getenv("OLLAMA_REPORT_MODEL", "gemma2:9b"))
OLLAMA_BENCHMARK_TIMEOUT_SECONDS = max(60, int(os.getenv("OLLAMA_BENCHMARK_TIMEOUT_SECONDS", "300")))
OLLAMA_BENCHMARK_MAX_RETRIES = max(1, int(os.getenv("OLLAMA_BENCHMARK_MAX_RETRIES", "3")))
OLLAMA_BENCHMARK_RETRY_BACKOFF_SECONDS = max(
    1.0,
    float(os.getenv("OLLAMA_BENCHMARK_RETRY_BACKOFF_SECONDS", "4")),
)
OLLAMA_BENCHMARK_RETRY_JITTER_SECONDS = max(
    0.0,
    float(os.getenv("OLLAMA_BENCHMARK_RETRY_JITTER_SECONDS", "0.5")),
)
OLLAMA_BASE_URL = str(os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).strip().rstrip("/")
OLLAMA_BENCHMARK_NUM_CTX = max(4096, int(os.getenv("OLLAMA_BENCHMARK_NUM_CTX", os.getenv("OLLAMA_NUM_CTX", "16384"))))
OLLAMA_BENCHMARK_GENERATION_NUM_PREDICT = max(
    1024,
    int(os.getenv("OLLAMA_BENCHMARK_GENERATION_NUM_PREDICT", "2200")),
)
OLLAMA_BENCHMARK_JSON_NUM_PREDICT = max(
    2048,
    int(os.getenv("OLLAMA_BENCHMARK_JSON_NUM_PREDICT", "4096")),
)
OLLAMA_BENCHMARK_DISABLE_THINKING = str(
    os.getenv("OLLAMA_BENCHMARK_DISABLE_THINKING", "1")
).strip().lower() not in {"0", "false", "no", "off"}
BENCHMARK_RUNTIME_STATUS_PATH_ENV = "BENCHMARK_RUNTIME_STATUS_PATH"
BENCHMARK_RUNTIME_ERROR_PATH_ENV = "BENCHMARK_RUNTIME_ERROR_PATH"
L1_CLAIM_TYPES = {"metric_value", "rank_score"}
L2L3_CLAIM_TYPES = {"best_model", "ranking", "top_feature", "feature_subset_optimum", "plateau"}


class BenchmarkRequestError(RuntimeError):
    def __init__(self, message: str, *, debug_payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.debug_payload = dict(debug_payload or {})


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_status_path() -> Path | None:
    raw_path = str(os.getenv(BENCHMARK_RUNTIME_STATUS_PATH_ENV) or "").strip()
    return Path(raw_path) if raw_path else None


def _runtime_error_path() -> Path | None:
    raw_path = str(os.getenv(BENCHMARK_RUNTIME_ERROR_PATH_ENV) or "").strip()
    return Path(raw_path) if raw_path else None


def _write_runtime_json(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _raw_response_payload(response: Any) -> dict[str, Any]:
    if response is None:
        return {}
    try:
        payload = response.json()
    except ValueError:
        payload = None
    return payload if isinstance(payload, dict) else {}


def _raw_response_snapshot(response: Any) -> dict[str, Any]:
    if response is None:
        return {}
    headers = {}
    for key, value in dict(getattr(response, "headers", {}) or {}).items():
        normalized_key = str(key or "").strip()
        if normalized_key.lower() in {"retry-after", "content-type", "x-request-id"}:
            headers[normalized_key] = str(value)
    return {
        "captured_at": _utc_timestamp(),
        "status_code": getattr(response, "status_code", None),
        "headers": headers,
        "json": _raw_response_payload(response),
        "text": str(getattr(response, "text", "") or "").strip()[:8000],
    }


def _exception_debug_payload(error: Exception) -> dict[str, Any]:
    if isinstance(error, BenchmarkRequestError):
        return dict(error.debug_payload or {})
    return {}


def _as_float(value: Any) -> float:
    return float(str(value).strip())


def _round_number(value: float) -> float:
    return round(value, 6)


def _extract_json_object(raw_content: str, provider: str) -> dict[str, Any]:
    candidates: list[str] = []
    stripped = raw_content.strip()
    if stripped:
        candidates.append(stripped)

        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3:
                fenced_body = "\n".join(lines[1:-1]).strip()
                if fenced_body:
                    candidates.append(fenced_body)

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            embedded_json = stripped[start:end + 1].strip()
            if embedded_json:
                candidates.append(embedded_json)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ValueError(f"{provider} benchmark response did not contain a valid JSON object.")


def _build_ollama_json_only_instruction(schema: dict[str, Any]) -> str:
    compact_schema = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    return " ".join(
        [
            "Return ONLY one valid JSON object.",
            "The first character of the final answer must be { and the last character must be }.",
            "Do not output markdown, headings, explanations, or prose outside JSON.",
            "Do not think out loud.",
            "Do not place the answer in a hidden thinking field; the final assistant content must contain the JSON object.",
            "If you need to reason, do it silently and output only the final JSON.",
            "The JSON must exactly match this schema:",
            compact_schema,
            "If any field is unsupported, keep the JSON valid and use an empty string or empty array.",
        ]
    )


def _build_groq_json_only_instruction() -> str:
    return " ".join(
        [
            "Return ONLY one valid JSON object.",
            "The first character of the final answer must be { and the last character must be }.",
            "Do not output markdown, headings, prose, or reasoning outside JSON.",
            "If a field has no value, use null or an empty array instead of omitting required keys.",
        ]
    )


def _ollama_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if OLLAMA_BENCHMARK_DISABLE_THINKING:
        payload = dict(payload)
        payload["think"] = False
    return payload


def _ollama_message_text(message: dict[str, Any]) -> str:
    primary = message.get("content")
    if isinstance(primary, str) and primary.strip():
        return primary.strip()
    fallback = message.get("thinking")
    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip()
    return ""


def _groq_chat_completions_url() -> str:
    base_url = str(
        os.getenv("GROQ_BASE_URL") or DEFAULT_GROQ_CHAT_BASE_URL
    ).strip().rstrip("/")
    return f"{base_url}/chat/completions"


def _groq_supports_json_schema(model: str) -> bool:
    return str(model or "").strip().startswith("openai/gpt-oss")


def _groq_retry_after_seconds(response: Any) -> float | None:
    if response is None:
        return None
    retry_after = str(getattr(response, "headers", {}).get("Retry-After") or "").strip()
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            return None
    try:
        payload = response.json()
    except ValueError:
        return None
    message = str((payload.get("error") or {}).get("message") or payload.get("message") or "")
    match = re.search(r"try again in\s+([0-9]+(?:\.[0-9]+)?)s", message, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return max(0.0, float(match.group(1)))
    except ValueError:
        return None


def _response_error_payload(response: Any) -> dict[str, Any]:
    if response is None:
        return {}
    try:
        payload = response.json()
    except ValueError:
        text = str(getattr(response, "text", "") or "").strip()
        return {"message": text[:1000]} if text else {}
    return payload if isinstance(payload, dict) else {}


def _format_http_error(exc: Exception, provider: str) -> str:
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", "unknown")
    payload = _response_error_payload(response)
    error_payload = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    message = str(
        error_payload.get("message")
        or payload.get("message")
        or getattr(response, "text", "")
        or exc
    ).strip()
    code = str(error_payload.get("code") or payload.get("code") or "").strip()
    detail = f"{provider} request failed with HTTP {status_code}"
    if code:
        detail += f" ({code})"
    if message:
        detail += f": {message[:1000]}"
    return detail


def _is_groq_json_validate_failed(response: Any) -> bool:
    if response is None or getattr(response, "status_code", None) != 400:
        return False
    payload = _response_error_payload(response)
    error_payload = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    code = str(error_payload.get("code") or payload.get("code") or "").strip()
    return code == "json_validate_failed"


def _is_groq_rate_limit_error(response: Any) -> bool:
    if response is None:
        return False
    status_code = getattr(response, "status_code", None)
    if status_code == 429:
        return True
    if status_code != 413:
        return False
    payload = _response_error_payload(response)
    error_payload = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    code = str(error_payload.get("code") or payload.get("code") or "").strip().lower()
    message = str(error_payload.get("message") or payload.get("message") or "").lower()
    return code == "rate_limit_exceeded" or "tokens per minute" in message


def _groq_error_code(response: Any) -> str:
    payload = _response_error_payload(response)
    error_payload = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    return str(error_payload.get("code") or payload.get("code") or "").strip().lower()


def _groq_error_message(response: Any) -> str:
    payload = _response_error_payload(response)
    error_payload = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    return str(error_payload.get("message") or payload.get("message") or "").strip()


def _is_groq_key_blocked_error(response: Any) -> bool:
    if response is None:
        return False
    status_code = getattr(response, "status_code", None)
    if status_code not in {400, 401, 403}:
        return False
    code = _groq_error_code(response)
    message = _groq_error_message(response).lower()
    if code in {"organization_restricted", "account_restricted", "api_key_restricted", "invalid_api_key"}:
        return True
    return (
        "organization has been restricted" in message
        or "account has been restricted" in message
        or "api key has been disabled" in message
        or "invalid api key" in message
    )


def _benchmark_error_status_code(error: Exception) -> int | None:
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    return int(status_code) if status_code is not None else None


def _benchmark_retry_reason(error: Exception, provider_label: str = "Groq") -> str:
    status_code = _benchmark_error_status_code(error)
    if status_code in {413, 429}:
        return f"{provider_label} rate limit"
    if status_code is not None and status_code >= 500:
        return f"{provider_label} server error"
    return f"{provider_label} request retry"


def _chat_message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("content") or ""
            if isinstance(text, str) and text.strip():
                text_parts.append(text)
        return "".join(text_parts).strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def _failed_generation_payload(
    artifact_id: str,
    arm: str,
    input_condition: str,
    error_message: str,
    semantic_level: str | None = None,
) -> dict[str, Any]:
    trimmed_error = str(error_message or "generation_failed").strip()[:240]
    return {
        "artifact_id": artifact_id,
        "arm": arm,
        "input_condition": input_condition,
        "semantic_level": semantic_level,
        "generation_stage": "failed",
        "explanation_short": "Benchmark generation failed to produce valid JSON.",
        "explanation_full": (
            "Benchmark generation failed before producing a grounded explanation. "
            f"Error: {trimmed_error}"
        ),
        "claims": [],
    }


def _explanation_only_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": str(payload.get("artifact_id") or "").strip(),
        "arm": str(payload.get("arm") or "").strip(),
        "input_condition": str(payload.get("input_condition") or "").strip(),
        "semantic_level": str(payload.get("semantic_level") or "").strip() or None,
        "explanation_short": str(payload.get("explanation_short") or "").strip(),
        "explanation_full": str(payload.get("explanation_full") or payload.get("explanation_short") or "").strip(),
    }


def _merge_explanation_and_claims(
    explanation_payload: dict[str, Any],
    claims_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    claims = claims_payload.get("claims") if isinstance(claims_payload, dict) else []
    if not isinstance(claims, list):
        claims = []
    merged = _explanation_only_payload(explanation_payload)
    merged["semantic_level"] = (
        merged.get("semantic_level")
        or str(claims_payload.get("semantic_level") or "").strip()
        if isinstance(claims_payload, dict)
        else merged.get("semantic_level")
    )
    merged["claims"] = claims
    return merged


def _normalize_embedded_claims(
    payload: dict[str, Any],
    variable_catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized = dict(payload)
    raw_claims = normalized.get("claims")
    if not isinstance(raw_claims, list):
        normalized["claims"] = []
        return normalized

    claims: list[dict[str, Any]] = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict):
            continue
        claim = dict(raw_claim)
        source_variable_id = _source_variable_id_for_claim(claim, variable_catalog)
        if not source_variable_id:
            source_variable_id = str(claim.get("source_variable_id") or "").strip() or None
        if not source_variable_id:
            continue
        claim["source_variable_id"] = source_variable_id
        claims.append(claim)

    normalized["claims"] = claims
    return normalized


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _source_variable_id_for_claim(
    claim_payload: dict[str, Any],
    variable_catalog: list[dict[str, Any]],
) -> str | None:
    claim_type = _normalized_text(claim_payload.get("claim_type"))
    subject = _normalized_text(claim_payload.get("subject"))
    metric = _normalized_text(claim_payload.get("metric"))
    for variable in variable_catalog:
        variable_claim_type = _normalized_text(variable.get("claim_type"))
        variable_subject = _normalized_text(variable.get("subject"))
        variable_metric = _normalized_text(variable.get("metric"))
        if claim_type != variable_claim_type:
            continue
        if claim_type in {"metric_value", "rank_score"} and subject == variable_subject and metric == variable_metric:
            return str(variable.get("source_variable_id") or "").strip() or None
        if claim_type in {"feature_subset_optimum", "plateau"} and subject == variable_subject:
            return str(variable.get("source_variable_id") or "").strip() or None
        if claim_type == "ranking" and metric == variable_metric:
            return str(variable.get("source_variable_id") or "").strip() or None
        if claim_type in {"best_model", "top_feature"} and (
            metric == variable_metric or not variable_metric
        ):
            return str(variable.get("source_variable_id") or "").strip() or None
    return None


def _requested_runs(
    arms: list[str],
    conditions: list[str],
    semantic_levels: list[str] | None,
) -> list[tuple[str, str, str | None]]:
    runs: list[tuple[str, str, str | None]] = []
    effective_levels = [level for level in (semantic_levels or SUPPORTED_SEMANTIC_LEVELS) if level in SUPPORTED_SEMANTIC_LEVELS]
    if not effective_levels:
        effective_levels = list(SUPPORTED_SEMANTIC_LEVELS)
    for arm in arms:
        for condition in conditions:
            if arm == "B":
                for semantic_level in effective_levels:
                    runs.append((arm, condition, semantic_level))
            else:
                runs.append((arm, condition, None))
    return runs


def _variable_catalog_for_level(
    variable_catalog_by_level: dict[str | None, list[dict[str, Any]]],
    semantic_level: str | None,
) -> list[dict[str, Any]]:
    if semantic_level in variable_catalog_by_level:
        return variable_catalog_by_level[semantic_level]
    return variable_catalog_by_level.get(None, [])


class BaseLLMClient(ABC):
    name = "base"
    model_name: str | None = None

    def set_runtime_context(self, **context: Any) -> None:
        self._runtime_context = {
            str(key): value
            for key, value in context.items()
            if value not in (None, "", [], {})
        }

    def clear_runtime_context(self) -> None:
        self._runtime_context = {}

    def _runtime_context_payload(self) -> dict[str, Any]:
        payload = dict(getattr(self, "_runtime_context", {}) or {})
        if getattr(self, "name", ""):
            payload.setdefault("client", self.name)
        if getattr(self, "model_name", None):
            payload.setdefault("model", self.model_name)
        return payload

    def _write_runtime_status(self, payload: dict[str, Any]) -> None:
        status_payload = {
            "updated_at": _utc_timestamp(),
            **self._runtime_context_payload(),
            **payload,
        }
        _write_runtime_json(_runtime_status_path(), status_payload)

    def _write_runtime_error(self, payload: dict[str, Any]) -> str | None:
        error_path = _runtime_error_path()
        if error_path is None:
            return None
        _write_runtime_json(error_path, {
            "updated_at": _utc_timestamp(),
            **self._runtime_context_payload(),
            **payload,
        })
        try:
            return str(error_path.resolve())
        except OSError:
            return str(error_path)

    @abstractmethod
    def generate_explanation_json(self, prompt: str) -> dict[str, Any]:
        """Return a JSON-like dictionary for the explanation-generation prompt."""

    @abstractmethod
    def extract_claims_json(self, prompt: str) -> dict[str, Any]:
        """Return a JSON-like dictionary for the claim-extraction prompt."""

    def extract_variable_mentions_json(self, prompt: str) -> dict[str, Any]:
        """Return standardized variable mentions for the variable-first Arm C path."""
        context = extract_variable_mention_context(prompt)
        claims_payload = self.extract_claims_json(
            build_claim_extraction_prompt(
                artifact_id=str(context.get("artifact_id") or ""),
                arm=str(context.get("arm") or ""),
                input_condition=str(context.get("input_condition") or ""),
                semantic_level=str(context.get("semantic_level") or "").strip() or None,
                explanation_short=str((context.get("explanation") or {}).get("explanation_short") or ""),
                explanation_full=str((context.get("explanation") or {}).get("explanation_full") or ""),
                primary_entities=list(context.get("primary_entities") or []),
                variable_catalog=list(context.get("allowed_variables") or []),
            )
        )
        mentions = claims_payload_to_variable_mentions(
            claims_payload,
            artifact_id=str(context.get("artifact_id") or ""),
        )
        return variable_mentions_to_payload(
            mentions,
            artifact_id=str(context.get("artifact_id") or ""),
            arm=str(context.get("arm") or ""),
            input_condition=str(context.get("input_condition") or ""),
            semantic_level=str(context.get("semantic_level") or "").strip() or None,
        )

    @abstractmethod
    def validate_arm_c_json(self, prompt: str) -> dict[str, Any]:
        """Return validator records for the Arm C correction loop."""

    @abstractmethod
    def correct_arm_c_json(self, prompt: str) -> dict[str, Any]:
        """Return corrected explanation plus structured claims for the Arm C loop."""

    def generate_artifact(
        self,
        inputs: ArtifactInputs,
        arms: list[str],
        conditions: list[str],
        semantic_levels: list[str] | None = None,
        variable_catalog_by_level: dict[str | None, list[dict[str, Any]]] | None = None,
    ) -> list[dict[str, Any]]:
        catalogs = variable_catalog_by_level or {None: []}
        outputs: list[dict[str, Any]] = []
        for arm, condition, semantic_level in _requested_runs(arms, conditions, semantic_levels):
            variable_catalog = _variable_catalog_for_level(catalogs, semantic_level)
            explanation_prompt = build_explanation_prompt(
                inputs=inputs,
                arm=arm,
                condition=condition,
                semantic_level=semantic_level,
            )
            try:
                self.set_runtime_context(
                    artifact_id=inputs.record.artifact_id,
                    arm=arm,
                    input_condition=condition,
                    semantic_level=semantic_level,
                    stage="generate_explanation",
                )
                explanation_payload = self.generate_explanation_json(explanation_prompt)
            except Exception as exc:
                outputs.append(
                    _failed_generation_payload(
                        artifact_id=inputs.record.artifact_id,
                        arm=arm,
                        input_condition=condition,
                        error_message=str(exc),
                        semantic_level=semantic_level,
                    )
                )
                continue

            try:
                self.set_runtime_context(
                    artifact_id=inputs.record.artifact_id,
                    arm=arm,
                    input_condition=condition,
                    semantic_level=semantic_level,
                    stage="extract_claims",
                )
                claims_payload = self.extract_claims_json(
                    build_claim_extraction_prompt(
                        artifact_id=inputs.record.artifact_id,
                        arm=arm,
                        input_condition=condition,
                        semantic_level=semantic_level,
                        explanation_short=str(explanation_payload.get("explanation_short") or ""),
                        explanation_full=str(explanation_payload.get("explanation_full") or ""),
                        primary_entities=inputs.record.primary_entities,
                        variable_catalog=variable_catalog,
                    )
                )
            except Exception:
                claims_payload = {
                    "artifact_id": inputs.record.artifact_id,
                    "arm": arm,
                    "input_condition": condition,
                    "semantic_level": semantic_level,
                    "claims": [],
                }

            outputs.append(_merge_explanation_and_claims(explanation_payload, claims_payload))
        self.clear_runtime_context()
        return outputs

    def metadata(self) -> dict[str, Any]:
        return {
            "client": self.name,
            "model": self.model_name,
        }


class FixtureLLMClient(BaseLLMClient):
    """Deterministic local client for tests and smoke runs."""

    name = "fixture"

    def __init__(self) -> None:
        self._cached_generations: dict[tuple[str, str, str, str | None], dict[str, Any]] = {}

    @staticmethod
    def _cache_key(
        artifact_id: str,
        arm: str,
        input_condition: str,
        semantic_level: str | None,
    ) -> tuple[str, str, str, str | None]:
        return (artifact_id, arm, input_condition, semantic_level)

    @staticmethod
    def _metric_claims(payload: dict[str, Any]) -> list[dict[str, Any]]:
        raw_claims = payload.get("claims")
        if not isinstance(raw_claims, list):
            return []
        return [
            dict(claim)
            for claim in raw_claims
            if isinstance(claim, dict) and str(claim.get("claim_type") or "") in L1_CLAIM_TYPES
        ]

    @staticmethod
    def _analytic_claims(payload: dict[str, Any]) -> list[dict[str, Any]]:
        raw_claims = payload.get("claims")
        if not isinstance(raw_claims, list):
            return []
        return [
            dict(claim)
            for claim in raw_claims
            if isinstance(claim, dict) and str(claim.get("claim_type") or "") in L2L3_CLAIM_TYPES
        ]

    @staticmethod
    def _metric_names_from_payload(payload: dict[str, Any]) -> list[str]:
        metric_names: list[str] = []
        for claim in FixtureLLMClient._metric_claims(payload):
            metric = str(claim.get("metric") or "").strip()
            if metric and metric not in metric_names:
                metric_names.append(metric)
        return metric_names

    def _structural_text(self, context: dict[str, Any], payload: dict[str, Any]) -> tuple[str, str]:
        primary_entities = [str(item) for item in context.get("primary_entities") or [] if str(item).strip()]
        metric_names = self._metric_names_from_payload(payload)
        chart_asset = dict(context.get("chart_asset") or {})
        artifact_type = str(context.get("artifact_type") or "")

        if artifact_type == "model_comparison/main":
            rows = list(context.get("table_model_comparison", []))
            model_names = [str(row.get("model") or "").strip() for row in rows if str(row.get("model") or "").strip()]
            metric_names = [
                key
                for key in (rows[0].keys() if rows else [])
                if key != "model" and str(rows[0].get(key, "")).strip()
            ]
            short = f"This is a model comparison table with {len(model_names)} models and {len(metric_names)} metrics."
            full = (
                f"The model comparison table compares {', '.join(model_names)}. Metrics include {', '.join(metric_names)}. "
                "Each row reports one model and its corresponding metric values."
            )
            return short, full

        if artifact_type == "incremental_feature_analysis/main":
            rows = list(context.get("table1_incremental_results", []))
            feature_counts = sorted({int(float(row["n_features"])) for row in rows if row.get("n_features") is not None})
            model_names = sorted({key[:-3] for row in rows for key in row.keys() if key.endswith("_R2")})
            feature_range = ""
            if feature_counts:
                feature_range = f" across feature counts {feature_counts[0]}-{feature_counts[-1]}"
            short = f"This is an incremental feature analysis table for {len(model_names)} models."
            full = (
                f"The table tracks {', '.join(model_names)}{feature_range}. "
                "Rows enumerate feature subsets and columns report performance metrics such as R2 and MSE."
            )
            return short, full

        if artifact_type == "feature_ranking/gra":
            ranking = list(context.get("gra_ranking", []))
            feature_names = [str(item.get("feature") or "").strip() for item in ranking if str(item.get("feature") or "").strip()]
            short = f"This is a GRA ranking table with {len(feature_names)} listed features."
            full = (
                f"The table lists ranked features such as {', '.join(feature_names[:4])}. "
                "Each row includes a feature name, its rank, and its gra_score."
            )
            return short, full

        asset_title = str(chart_asset.get("asset_title") or "").strip()
        asset_family = str(chart_asset.get("asset_family") or "").strip().replace("_", " ")
        artifact_label = asset_title or asset_family or "chart"
        entity_text = ", ".join(primary_entities[:4]) if primary_entities else "the listed entities"
        metric_text = ", ".join(metric_names[:4]) if metric_names else "the listed metrics"
        short = f"This chart presents {artifact_label} for {entity_text}."
        full = (
            f"The chart shows {artifact_label}. It references {entity_text} and reports metrics such as "
            f"{metric_text}."
        )
        return short, full

    def _apply_semantic_level(self, context: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        semantic_level = str(context.get("semantic_level") or "").strip() or None
        payload = copy.deepcopy(payload)
        payload["semantic_level"] = semantic_level
        if str(context.get("arm") or "") != "B" or semantic_level is None:
            return payload

        structural_short, structural_full = self._structural_text(context, payload)
        analytical_claims = self._analytic_claims(payload)
        structural_claims = self._metric_claims(payload)

        if semantic_level == "L1":
            payload["explanation_short"] = structural_short
            payload["explanation_full"] = structural_full
            payload["claims"] = structural_claims
            return payload
        if semantic_level == "L2L3":
            payload["claims"] = analytical_claims
            return payload
        if semantic_level == "L1L2L3":
            payload["explanation_short"] = structural_short
            payload["explanation_full"] = f"{structural_full} {str(payload.get('explanation_full') or '').strip()}".strip()
            return payload
        return payload

    @staticmethod
    def _arm_c_draft_payload(context: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        mutated = copy.deepcopy(payload)
        raw_claims = mutated.get("claims")
        if not isinstance(raw_claims, list):
            return mutated

        for claim in raw_claims:
            if not isinstance(claim, dict):
                continue
            claim_type = str(claim.get("claim_type") or "").strip()
            if claim_type in {"metric_value", "rank_score"} and isinstance(claim.get("value"), (int, float)):
                original_value = float(claim["value"])
                draft_value = _round_number(original_value + max(abs(original_value) * 0.08, 0.01))
                claim["value"] = draft_value
                subject = str(claim.get("subject") or "The highlighted item").strip()
                metric = str(claim.get("metric") or claim.get("predicate") or "value").strip()
                claim["claim_text"] = f"{subject} has {metric}={draft_value:.6f}."
                mutated["explanation_short"] = f"{subject} draft estimate is {metric}={draft_value:.6f}."
                mutated["explanation_full"] = (
                    f"{subject} is described with {metric}={draft_value:.6f} in the draft explanation. "
                    f"{str(payload.get('explanation_full') or '').strip()}"
                ).strip()
                return mutated

        for claim in raw_claims:
            if not isinstance(claim, dict):
                continue
            claim_type = str(claim.get("claim_type") or "").strip()
            if claim_type in {"best_model", "top_feature"}:
                alternatives = [str(item).strip() for item in context.get("primary_entities") or [] if str(item).strip()]
                current_value = str(claim.get("object") or claim.get("subject") or "").strip()
                replacement = next((item for item in alternatives if item and item != current_value), current_value)
                claim["object"] = replacement
                claim["subject"] = replacement if claim_type == "top_feature" else claim.get("subject")
                mutated["explanation_short"] = f"{replacement} is highlighted in the draft explanation."
                mutated["explanation_full"] = (
                    f"The draft explanation highlights {replacement} before correction. "
                    f"{str(payload.get('explanation_full') or '').strip()}"
                ).strip()
                return mutated

        return mutated

    @staticmethod
    def _fact_summary(fact: dict[str, Any]) -> str:
        fact_type = str(fact.get("fact_type") or "").strip()
        subject = str(fact.get("subject") or "").strip()
        predicate = str(fact.get("predicate") or "").strip()
        object_value = fact.get("object")
        value = fact.get("value")
        if fact_type in {"metric_value", "rank_score"}:
            if isinstance(value, (int, float)):
                return f"{subject} {predicate}={float(value):.6f}"
            return f"{subject} {predicate}={value}"
        if fact_type in {"best_model", "top_feature"}:
            metric_suffix = f" by {predicate}" if predicate else ""
            return f"{fact_type} is {object_value}{metric_suffix}"
        if fact_type == "ranking":
            ordered_items = object_value if isinstance(object_value, list) else []
            return f"{predicate or 'ranking'} = {' > '.join(str(item) for item in ordered_items)}"
        if fact_type in {"feature_subset_optimum", "plateau"}:
            return f"{subject} {fact_type} at {value}"
        return f"{fact_type}: {object_value if object_value not in (None, '') else value}"

    @staticmethod
    def _normalized_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [_normalized_text(item) for item in value if _normalized_text(item)]

    @staticmethod
    def _claim_metric_key(claim: dict[str, Any]) -> str:
        return _normalized_text(claim.get("metric") or claim.get("predicate"))

    @staticmethod
    def _fact_metric_key(fact: dict[str, Any]) -> str:
        return _normalized_text(fact.get("predicate"))

    @staticmethod
    def _find_matching_fact(claim: dict[str, Any], facts: list[dict[str, Any]]) -> dict[str, Any] | None:
        claim_type = _normalized_text(claim.get("claim_type"))
        subject = _normalized_text(claim.get("subject"))
        metric = FixtureLLMClient._claim_metric_key(claim)
        source_variable_id = str(claim.get("source_variable_id") or "").strip()

        def compatible(fact: dict[str, Any]) -> bool:
            fact_type = _normalized_text(fact.get("fact_type"))
            fact_subject = _normalized_text(fact.get("subject"))
            fact_metric = FixtureLLMClient._fact_metric_key(fact)
            if claim_type != fact_type:
                return False
            if claim_type in {"metric_value", "rank_score"}:
                return subject == fact_subject and metric == fact_metric
            if claim_type in {"feature_subset_optimum", "plateau"}:
                return subject == fact_subject
            if claim_type == "ranking":
                return metric == fact_metric
            if claim_type in {"best_model", "top_feature"}:
                return metric == fact_metric or not metric or not fact_metric
            return False

        if source_variable_id:
            direct_match = next(
                (
                    fact
                    for fact in facts
                    if str(fact.get("fact_id") or "").strip() == source_variable_id and compatible(fact)
                ),
                None,
            )
            if direct_match is not None:
                return direct_match

        return next((fact for fact in facts if compatible(fact)), None)

    @staticmethod
    def _claim_status_against_fact(claim: dict[str, Any], fact: dict[str, Any]) -> str:
        claim_type = _normalized_text(claim.get("claim_type"))
        if claim_type in {"metric_value", "rank_score"}:
            claim_value = claim.get("value")
            fact_value = fact.get("value")
            if isinstance(claim_value, (int, float)) and isinstance(fact_value, (int, float)):
                return "supported" if abs(float(claim_value) - float(fact_value)) <= 1e-6 else "contradicted"
            return "supported" if _normalized_text(claim_value) == _normalized_text(fact_value) else "contradicted"

        if claim_type in {"best_model", "top_feature"}:
            claim_target = _normalized_text(claim.get("object") or claim.get("subject"))
            fact_target = _normalized_text(fact.get("object") or fact.get("subject"))
            return "supported" if claim_target == fact_target else "contradicted"

        if claim_type == "ranking":
            claim_items = FixtureLLMClient._normalized_list(claim.get("ordered_items"))
            fact_items = FixtureLLMClient._normalized_list(fact.get("object"))
            if claim_items == fact_items:
                return "supported"
            if claim_items and fact_items and claim_items[0] == fact_items[0]:
                return "partially_supported"
            return "contradicted"

        if claim_type in {"feature_subset_optimum", "plateau"}:
            claim_value = claim.get("feature_count")
            if claim_value is None:
                claim_value = claim.get("value")
            fact_value = fact.get("value")
            if claim_value == fact_value:
                return "supported"
            return "contradicted"

        return "unverifiable"

    def validate_arm_c_json(self, prompt: str) -> dict[str, Any]:
        context = extract_prompt_context(prompt)
        evidence_packet = dict(context.get("evidence_packet") or {})
        facts = [dict(item) for item in list(evidence_packet.get("validated_facts") or []) if isinstance(item, dict)]
        claims = [dict(item) for item in list(context.get("claims") or []) if isinstance(item, dict)]

        validation_records: list[dict[str, Any]] = []
        for claim in claims:
            matching_fact = self._find_matching_fact(claim, facts)
            if matching_fact is None:
                validation_records.append(
                    {
                        "claim_id": str(claim.get("claim_id") or ""),
                        "claim_text": str(claim.get("claim_text") or ""),
                        "status": "unverifiable",
                        "recommended_action": "drop",
                        "rationale": "No aligned fact was found in the evidence packet.",
                        "matched_fact_ids": [],
                        "grounded_fact_summary": None,
                    }
                )
                continue

            status = self._claim_status_against_fact(claim, matching_fact)
            recommended_action = "keep" if status == "supported" else "edit"
            rationale = {
                "supported": "The structured claim matches the evidence packet.",
                "partially_supported": "The claim overlaps with the evidence packet but needs correction.",
                "contradicted": "The evidence packet contains a conflicting grounded fact.",
                "unverifiable": "The evidence packet does not support the structured claim.",
            }.get(status, "Validator review completed.")
            validation_records.append(
                {
                    "claim_id": str(claim.get("claim_id") or ""),
                    "claim_text": str(claim.get("claim_text") or ""),
                    "status": status,
                    "recommended_action": recommended_action,
                    "rationale": rationale,
                    "matched_fact_ids": [str(matching_fact.get("fact_id") or "").strip()],
                    "grounded_fact_summary": self._fact_summary(matching_fact),
                }
            )

        return {
            "artifact_id": str(context.get("artifact_id") or ""),
            "arm": "C",
            "input_condition": str(context.get("input_condition") or ""),
            "validation_records": validation_records,
        }

    def correct_arm_c_json(self, prompt: str) -> dict[str, Any]:
        context = extract_prompt_context(prompt)
        correction_context = dict(context.get("evidence_packet") or {})
        payload = self._full_generation_payload(correction_context)
        payload["artifact_id"] = str(context.get("artifact_id") or payload.get("artifact_id") or "")
        payload["arm"] = "C"
        payload["input_condition"] = str(context.get("input_condition") or payload.get("input_condition") or "")
        payload["semantic_level"] = None
        normalized = _normalize_embedded_claims(
            payload,
            list(correction_context.get("allowed_variables") or []),
        )
        cache_key = self._cache_key(
            str(normalized.get("artifact_id") or ""),
            str(normalized.get("arm") or ""),
            str(normalized.get("input_condition") or ""),
            str(normalized.get("semantic_level") or "").strip() or None,
        )
        self._cached_generations[cache_key] = copy.deepcopy(normalized)
        return normalized

    def generate_explanation_json(self, prompt: str) -> dict[str, Any]:
        context = extract_prompt_context(prompt)
        arm_c_stage = str(context.get("arm_c_stage") or "").strip()
        if str(context.get("arm") or "") == "C" and arm_c_stage == "corrector":
            correction_context = dict(context.get("evidence_packet") or {})
            payload = self._full_generation_payload(correction_context)
        else:
            payload = self._full_generation_payload(context)
            if str(context.get("arm") or "") == "C" and arm_c_stage == "draft":
                payload = self._arm_c_draft_payload(context, payload)
            payload = self._apply_semantic_level(context, payload)
        cache_key = self._cache_key(
            str(payload.get("artifact_id") or ""),
            str(payload.get("arm") or ""),
            str(payload.get("input_condition") or ""),
            str(payload.get("semantic_level") or "").strip() or None,
        )
        self._cached_generations[cache_key] = copy.deepcopy(payload)
        return _explanation_only_payload(payload)

    def extract_claims_json(self, prompt: str) -> dict[str, Any]:
        context = extract_claim_extraction_context(prompt)
        cache_key = self._cache_key(
            str(context.get("artifact_id") or ""),
            str(context.get("arm") or ""),
            str(context.get("input_condition") or ""),
            str(context.get("semantic_level") or "").strip() or None,
        )
        payload = copy.deepcopy(self._cached_generations.get(cache_key) or {})
        raw_claims = payload.get("claims")
        if not isinstance(raw_claims, list):
            raw_claims = []

        variable_catalog = list(context.get("allowed_variables") or [])
        claims: list[dict[str, Any]] = []
        for raw_claim in raw_claims:
            if not isinstance(raw_claim, dict):
                continue
            claim = dict(raw_claim)
            claim["source_variable_id"] = _source_variable_id_for_claim(claim, variable_catalog)
            if claim["source_variable_id"]:
                claims.append(claim)

        return {
            "artifact_id": str(context.get("artifact_id") or ""),
            "arm": str(context.get("arm") or ""),
            "input_condition": str(context.get("input_condition") or ""),
            "semantic_level": str(context.get("semantic_level") or "").strip() or None,
            "claims": claims,
        }

    def extract_variable_mentions_json(self, prompt: str) -> dict[str, Any]:
        context = extract_variable_mention_context(prompt)
        cache_key = self._cache_key(
            str(context.get("artifact_id") or ""),
            str(context.get("arm") or ""),
            str(context.get("input_condition") or ""),
            str(context.get("semantic_level") or "").strip() or None,
        )
        payload = copy.deepcopy(self._cached_generations.get(cache_key) or {})
        raw_claims = payload.get("claims")
        if not isinstance(raw_claims, list):
            raw_claims = []

        variable_catalog = list(context.get("allowed_variables") or [])
        claims: list[dict[str, Any]] = []
        for raw_claim in raw_claims:
            if not isinstance(raw_claim, dict):
                continue
            claim = dict(raw_claim)
            claim["source_variable_id"] = _source_variable_id_for_claim(claim, variable_catalog)
            if claim["source_variable_id"]:
                claims.append(claim)

        mentions = claims_payload_to_variable_mentions(
            {
                "artifact_id": str(context.get("artifact_id") or ""),
                "arm": str(context.get("arm") or ""),
                "input_condition": str(context.get("input_condition") or ""),
                "semantic_level": str(context.get("semantic_level") or "").strip() or None,
                "claims": claims,
            },
            artifact_id=str(context.get("artifact_id") or ""),
        )
        return variable_mentions_to_payload(
            mentions,
            artifact_id=str(context.get("artifact_id") or ""),
            arm=str(context.get("arm") or ""),
            input_condition=str(context.get("input_condition") or ""),
            semantic_level=str(context.get("semantic_level") or "").strip() or None,
        )

    def _full_generation_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        if context.get("chart_asset"):
            return self._chart_output(context)
        artifact_type = str(context["artifact_type"])
        if artifact_type == "model_comparison/main":
            return self._model_comparison_output(context)
        if artifact_type == "incremental_feature_analysis/main":
            return self._incremental_output(context)
        if artifact_type == "feature_ranking/gra":
            return self._ranking_output(context)
        raise ValueError(f"Unsupported artifact type for fixture client: {artifact_type}")

    def _chart_output(self, context: dict[str, Any]) -> dict[str, Any]:
        chart_asset = dict(context.get("chart_asset") or {})
        family = str(chart_asset.get("asset_family") or "").strip()
        if family == "model_comparison_chart":
            return self._chart_model_comparison_output(context, chart_asset)
        if family == "incremental_feature_analysis_chart":
            return self._chart_incremental_output(context, chart_asset)
        if family == "feature_ranking":
            return self._chart_ranking_output(context, chart_asset)
        if family == "feature_story_shap":
            return self._feature_story_output(
                context,
                chart_asset,
                source_key="top_shap_features",
                value_key="mean_abs_shap",
                metric="mean_abs_shap",
                label="SHAP",
            )
        if family == "feature_story_importance":
            return self._feature_story_output(
                context,
                chart_asset,
                source_key="top_feature_importance",
                value_key="importance",
                metric="importance",
                label="feature importance",
            )
        if family == "feature_analysis_combined":
            return self._combined_feature_output(context, chart_asset)
        if family == "correlation":
            return self._correlation_output(context, chart_asset)
        if family == "distribution":
            return self._distribution_output(context, chart_asset)
        if family in {"prediction_overview", "prediction_residuals", "prediction_scatter"}:
            return self._prediction_metrics_output(context, chart_asset)
        if family == "prediction_sequence":
            return self._prediction_sequence_output(context, chart_asset)
        raise ValueError(f"Unsupported chart family for fixture client: {family}")

    def _chart_model_comparison_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        model_metrics = dict(evidence.get("model_metrics") or {})
        rows = list(model_metrics.get("benchmark_models_sorted") or context.get("asset_tables", {}).get("table_model_comparison.csv", []))
        ranked_rows = sorted(rows, key=lambda row: _as_float(row["r2_score"]), reverse=True)
        best_row = ranked_rows[0]
        ranking = [str(row["model"]) for row in ranked_rows[:3]]
        best_model = str(best_row["model"])
        best_r2 = _round_number(_as_float(best_row["r2_score"]))
        explanation_full = (
            f"{best_model} leads this model-comparison chart with R2={best_r2:.6f}. "
            f"The R2 ordering is {' > '.join(ranking)}."
        )
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{best_model} leads the chart-level model comparison.",
            "explanation_full": explanation_full,
            "claims": [
                {
                    "claim_id": "best-model",
                    "claim_text": f"{best_model} is the best model in the chart comparison.",
                    "claim_type": "best_model",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.97,
                    "object": best_model,
                },
                {
                    "claim_id": "best-r2",
                    "claim_text": f"{best_model} achieved R2={best_r2:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.97,
                    "subject": best_model,
                    "metric": "r2_score",
                    "value": best_r2,
                },
                {
                    "claim_id": "ranking",
                    "claim_text": f"The R2 ranking is {' > '.join(ranking)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.92,
                    "metric": "r2_score",
                    "ordered_items": ranking,
                },
            ],
        }

    def _chart_incremental_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        incremental_story = dict(evidence.get("incremental_story") or {})
        best_steps = list(incremental_story.get("best_step_per_model") or [])
        best_by_r2 = max(best_steps, key=lambda item: _as_float(item["best_r2"]))
        ranked_models = [
            str(item["model"])
            for item in sorted(best_steps, key=lambda item: _as_float(item["best_r2"]), reverse=True)[:3]
        ]
        model_name = str(best_by_r2["model"])
        feature_count = int(best_by_r2["best_n_features"])
        best_r2 = _round_number(_as_float(best_by_r2["best_r2"]))
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{model_name} has the strongest best-step result at {feature_count} features.",
            "explanation_full": (
                f"{model_name} has the strongest best-step result at {feature_count} features "
                f"with R2={best_r2:.6f}. The best-step ranking by R2 is {' > '.join(ranked_models)}."
            ),
            "claims": [
                {
                    "claim_id": "optimum-subset",
                    "claim_text": f"{model_name} reaches its best subset at {feature_count} features.",
                    "claim_type": "feature_subset_optimum",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.96,
                    "subject": model_name,
                    "feature_count": feature_count,
                    "object": str(best_by_r2["best_feature_subset"]),
                    "value": feature_count,
                },
                {
                    "claim_id": "best-r2",
                    "claim_text": f"{model_name} reaches R2={best_r2:.6f} at its best step.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.96,
                    "subject": model_name,
                    "metric": "r2_score",
                    "value": best_r2,
                },
                {
                    "claim_id": "ranking",
                    "claim_text": f"The best-step R2 ranking is {' > '.join(ranked_models)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.9,
                    "metric": "r2_score",
                    "ordered_items": ranked_models,
                },
            ],
        }

    def _feature_story_output(
        self,
        context: dict[str, Any],
        chart_asset: dict[str, Any],
        *,
        source_key: str,
        value_key: str,
        metric: str,
        label: str,
    ) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        feature_story = dict(evidence.get("feature_story") or {})
        rows = sorted(
            list(feature_story.get(source_key) or []),
            key=lambda item: _as_float(item[value_key]),
            reverse=True,
        )
        top_item = rows[0]
        ordered_items = [str(item["feature"]) for item in rows[:3]]
        top_feature = str(top_item["feature"])
        top_value = _round_number(_as_float(top_item[value_key]))
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{top_feature} leads the {label} chart.",
            "explanation_full": (
                f"{top_feature} leads the {label} chart with {metric}={top_value:.6f}. "
                f"The top ordering is {' > '.join(ordered_items)}."
            ),
            "claims": [
                {
                    "claim_id": "top-feature",
                    "claim_text": f"{top_feature} is the top feature by {metric}.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.97,
                    "object": top_feature,
                    "metric": metric,
                },
                {
                    "claim_id": "ranking",
                    "claim_text": f"The {metric} ordering is {' > '.join(ordered_items)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.92,
                    "metric": metric,
                    "ordered_items": ordered_items,
                },
                {
                    "claim_id": "top-score",
                    "claim_text": f"{top_feature} has {metric}={top_value:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.95,
                    "subject": top_feature,
                    "metric": metric,
                    "value": top_value,
                },
            ],
        }

    def _chart_ranking_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        asset_json_payloads = dict(context.get("asset_json_payloads") or {})
        ranking = list(asset_json_payloads.get("gra_ranking.json") or [])
        if not ranking:
            evidence = dict(chart_asset.get("evidence") or {})
            feature_story = dict(evidence.get("feature_story") or {})
            ranking = list(feature_story.get("top_gra_features") or [])
            for index, item in enumerate(ranking, start=1):
                item.setdefault("rank", index)
        ranking = sorted(ranking, key=lambda item: int(item.get("rank", 10_000)))
        ranking_context = dict(context)
        ranking_context["gra_ranking"] = ranking
        return self._ranking_output(ranking_context)

    def _combined_feature_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        feature_story = dict(evidence.get("feature_story") or {})
        correlation_story = dict(evidence.get("correlation_story") or {})
        top_gra = max(list(feature_story.get("top_gra_features") or []), key=lambda item: _as_float(item["score"]))
        top_importance = max(
            list(feature_story.get("top_feature_importance") or []),
            key=lambda item: _as_float(item["importance"]),
        )
        top_shap = max(
            list(feature_story.get("top_shap_features") or []),
            key=lambda item: _as_float(item["mean_abs_shap"]),
        )
        top_target = max(
            list(correlation_story.get("top_target_correlations") or []),
            key=lambda item: _as_float(item["abs_correlation"]),
        )
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": "The combined feature chart highlights different leaders across lenses.",
            "explanation_full": (
                f"GRA is led by {top_gra['feature']}, feature importance by {top_importance['feature']}, "
                f"SHAP by {top_shap['feature']}, and target correlation by {top_target['feature']}."
            ),
            "claims": [
                {
                    "claim_id": "gra-top",
                    "claim_text": f"{top_gra['feature']} is the top feature by gra_score.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.93,
                    "object": str(top_gra["feature"]),
                    "metric": "gra_score",
                },
                {
                    "claim_id": "importance-top",
                    "claim_text": f"{top_importance['feature']} is the top feature by importance.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.93,
                    "object": str(top_importance["feature"]),
                    "metric": "importance",
                },
                {
                    "claim_id": "shap-top",
                    "claim_text": f"{top_shap['feature']} is the top feature by mean_abs_shap.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.93,
                    "object": str(top_shap["feature"]),
                    "metric": "mean_abs_shap",
                },
                {
                    "claim_id": "target-correlation-top",
                    "claim_text": f"{top_target['feature']} is the top feature by target_correlation.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.91,
                    "object": str(top_target["feature"]),
                    "metric": "target_correlation",
                },
            ],
        }

    def _correlation_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        correlation_story = dict(evidence.get("correlation_story") or {})
        target_rows = sorted(
            list(correlation_story.get("top_target_correlations") or []),
            key=lambda item: _as_float(item["abs_correlation"]),
            reverse=True,
        )
        pair_rows = sorted(
            list(correlation_story.get("strongest_correlations") or []),
            key=lambda item: _as_float(item["abs_correlation"]),
            reverse=True,
        )
        top_target = target_rows[0]
        top_pair = pair_rows[0]
        ordered_items = [str(item["feature"]) for item in target_rows[:3]]
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{top_target['feature']} has the strongest listed target correlation.",
            "explanation_full": (
                f"{top_target['feature']} has the strongest listed target correlation, while the "
                f"strongest pairwise correlation is {top_pair['pair']} at {float(top_pair['correlation']):.6f}."
            ),
            "claims": [
                {
                    "claim_id": "top-target-feature",
                    "claim_text": f"{top_target['feature']} is the top feature by target_correlation.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.95,
                    "object": str(top_target["feature"]),
                    "metric": "target_correlation",
                },
                {
                    "claim_id": "target-ranking",
                    "claim_text": f"The target_correlation ordering is {' > '.join(ordered_items)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.9,
                    "metric": "target_correlation",
                    "ordered_items": ordered_items,
                },
                {
                    "claim_id": "top-pair",
                    "claim_text": f"{top_pair['pair']} has correlation={float(top_pair['correlation']):.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.93,
                    "subject": str(top_pair["pair"]),
                    "metric": "correlation",
                    "value": _round_number(_as_float(top_pair["correlation"])),
                },
            ],
        }

    def _distribution_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        distribution_story = dict(evidence.get("distribution_story") or {})
        rows = list(distribution_story.get("descriptive_statistics_sample") or [])
        mean_rows = sorted(rows, key=lambda item: _as_float(item["mean"]), reverse=True)
        std_rows = sorted(rows, key=lambda item: _as_float(item["std"]), reverse=True)
        top_mean = mean_rows[0]
        top_std = std_rows[0]
        ordered_mean = [str(item["Unnamed: 0"]) for item in mean_rows[:3]]
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{top_mean['Unnamed: 0']} has the highest mean in the sample summary.",
            "explanation_full": (
                f"{top_mean['Unnamed: 0']} has the highest mean, while {top_std['Unnamed: 0']} has the highest std. "
                f"The leading mean ordering is {' > '.join(ordered_mean)}."
            ),
            "claims": [
                {
                    "claim_id": "top-mean",
                    "claim_text": f"{top_mean['Unnamed: 0']} is the top feature by mean.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.95,
                    "object": str(top_mean["Unnamed: 0"]),
                    "metric": "mean",
                },
                {
                    "claim_id": "mean-ranking",
                    "claim_text": f"The mean ordering is {' > '.join(ordered_mean)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.89,
                    "metric": "mean",
                    "ordered_items": ordered_mean,
                },
                {
                    "claim_id": "top-std",
                    "claim_text": f"{top_std['Unnamed: 0']} is the top feature by std.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.9,
                    "object": str(top_std["Unnamed: 0"]),
                    "metric": "std",
                },
            ],
        }

    def _prediction_metrics_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        model_metrics = dict(evidence.get("model_metrics") or {})
        prediction_story = dict(evidence.get("prediction_story") or {})
        if str(chart_asset.get("asset_family")) == "prediction_scatter":
            model_name = str(model_metrics.get("model_name") or "").strip()
            metrics_row = dict(model_metrics.get("metrics") or {})
            diagnostics = dict(prediction_story.get("diagnostics") or {})
            third_metric = "linear_fit_slope"
        else:
            model_name = str(model_metrics.get("winning_model") or "").strip()
            metrics_row = dict(model_metrics.get("best_model_metrics") or {})
            diagnostics = dict(prediction_story.get("winning_model_diagnostics") or {})
            third_metric = "residual_std" if str(chart_asset.get("asset_family")) == "prediction_residuals" else "max_abs_residual"

        r2_value = _round_number(_as_float(metrics_row["r2_score"]))
        correlation_value = _round_number(_as_float(diagnostics["pred_actual_correlation"]))
        third_value = _round_number(_as_float(diagnostics[third_metric]))
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{model_name} diagnostics show a strong overall fit.",
            "explanation_full": (
                f"{model_name} reaches R2={r2_value:.6f}, pred_actual_correlation={correlation_value:.6f}, "
                f"and {third_metric}={third_value:.6f}."
            ),
            "claims": [
                {
                    "claim_id": "r2",
                    "claim_text": f"{model_name} has r2_score={r2_value:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.95,
                    "subject": model_name,
                    "metric": "r2_score",
                    "value": r2_value,
                },
                {
                    "claim_id": "correlation",
                    "claim_text": f"{model_name} has pred_actual_correlation={correlation_value:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.94,
                    "subject": model_name,
                    "metric": "pred_actual_correlation",
                    "value": correlation_value,
                },
                {
                    "claim_id": "third-metric",
                    "claim_text": f"{model_name} has {third_metric}={third_value:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.92,
                    "subject": model_name,
                    "metric": third_metric,
                    "value": third_value,
                },
            ],
        }

    def _prediction_sequence_output(self, context: dict[str, Any], chart_asset: dict[str, Any]) -> dict[str, Any]:
        evidence = dict(chart_asset.get("evidence") or {})
        model_metrics = dict(evidence.get("model_metrics") or {})
        sequence_story = dict(evidence.get("sequence_story") or {})
        model_name = str(model_metrics.get("winning_model") or "").strip()
        diagnostics = dict(sequence_story.get("winning_model_sequence_diagnostics") or {})
        sequence_correlation = _round_number(_as_float(diagnostics["sequence_correlation"]))
        mean_abs_gap = _round_number(_as_float(diagnostics["mean_abs_gap"]))
        actual_peak_index = int(diagnostics["actual_peak_index"])
        predicted_peak_index = int(diagnostics["predicted_peak_index"])
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{model_name} tracks the overall sequence well but misses peak timing.",
            "explanation_full": (
                f"{model_name} reaches sequence_correlation={sequence_correlation:.6f} with "
                f"mean_abs_gap={mean_abs_gap:.6f}; the actual peak is at index {actual_peak_index} "
                f"while the predicted peak is at index {predicted_peak_index}."
            ),
            "claims": [
                {
                    "claim_id": "sequence-correlation",
                    "claim_text": f"{model_name} has sequence_correlation={sequence_correlation:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.95,
                    "subject": model_name,
                    "metric": "sequence_correlation",
                    "value": sequence_correlation,
                },
                {
                    "claim_id": "mean-gap",
                    "claim_text": f"{model_name} has mean_abs_gap={mean_abs_gap:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.94,
                    "subject": model_name,
                    "metric": "mean_abs_gap",
                    "value": mean_abs_gap,
                },
                {
                    "claim_id": "actual-peak-index",
                    "claim_text": f"{model_name} has actual_peak_index={actual_peak_index}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.9,
                    "subject": model_name,
                    "metric": "actual_peak_index",
                    "value": actual_peak_index,
                },
                {
                    "claim_id": "predicted-peak-index",
                    "claim_text": f"{model_name} has predicted_peak_index={predicted_peak_index}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.9,
                    "subject": model_name,
                    "metric": "predicted_peak_index",
                    "value": predicted_peak_index,
                },
            ],
        }

    def _model_comparison_output(self, context: dict[str, Any]) -> dict[str, Any]:
        rows = list(context.get("table_model_comparison", []))
        ranked_rows = sorted(rows, key=lambda row: _as_float(row["r2_score"]), reverse=True)
        best_row = ranked_rows[0]
        second_row = ranked_rows[1] if len(ranked_rows) > 1 else ranked_rows[0]
        ranking = [str(row["model"]) for row in ranked_rows[:3]]
        best_model = str(best_row["model"])
        best_r2 = _round_number(_as_float(best_row["r2_score"]))
        gap = _round_number(_as_float(best_row["r2_score"]) - _as_float(second_row["r2_score"]))

        explanation_full = (
            f"{best_model} is the best-performing model in this comparison with "
            f"R2={best_r2:.6f}. The leading order by R2 is "
            f"{' > '.join(ranking)}. The R2 gap between {best_model} and "
            f"{second_row['model']} is {gap:.6f}."
        )
        if context.get("input_condition") == "image_table_summary":
            explanation_full += " Summary text was available, but the table remained the primary source."
        elif context.get("chart_files"):
            explanation_full += " Chart files were available as secondary evidence."

        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{best_model} leads the model comparison on R2 and error metrics.",
            "explanation_full": explanation_full,
            "claims": [
                {
                    "claim_id": "best-model",
                    "claim_text": f"{best_model} is the best model in the comparison.",
                    "claim_type": "best_model",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.98,
                    "object": best_model,
                },
                {
                    "claim_id": "best-r2",
                    "claim_text": f"{best_model} achieved R2={best_r2:.6f}.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.98,
                    "subject": best_model,
                    "metric": "r2_score",
                    "value": best_r2,
                },
                {
                    "claim_id": "ranking",
                    "claim_text": f"The leading R2 ranking is {' > '.join(ranking)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.94,
                    "metric": "r2_score",
                    "ordered_items": ranking,
                },
            ],
        }

    def _incremental_output(self, context: dict[str, Any]) -> dict[str, Any]:
        rows = list(context.get("table1_incremental_results", []))
        best_model = ""
        best_row: dict[str, Any] = {}
        best_r2 = None
        for row in rows:
            for key, raw_value in row.items():
                if not key.endswith("_R2"):
                    continue
                value = _as_float(raw_value)
                if best_r2 is None or value > best_r2:
                    best_r2 = value
                    best_model = key[:-3]
                    best_row = row
        if best_r2 is None:
            raise ValueError("Fixture client could not find incremental R2 values.")

        best_r2 = _round_number(best_r2)
        feature_count = int(float(best_row["n_features"]))
        feature_subset = str(best_row["feature_subset"])
        explanation_full = (
            f"The strongest incremental result occurs for {best_model} at {feature_count} "
            f"features with R2={best_r2:.6f}. The best subset is {feature_subset}, and "
            f"performance has effectively plateaued from that point onward."
        )
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{best_model} peaks at {feature_count} features.",
            "explanation_full": explanation_full,
            "claims": [
                {
                    "claim_id": "optimum-subset",
                    "claim_text": f"{best_model} reaches its best subset at {feature_count} features.",
                    "claim_type": "feature_subset_optimum",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.97,
                    "subject": best_model,
                    "feature_count": feature_count,
                    "object": feature_subset,
                    "value": feature_count,
                },
                {
                    "claim_id": "best-r2",
                    "claim_text": f"{best_model} reaches R2={best_r2:.6f} at the optimum subset.",
                    "claim_type": "metric_value",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.97,
                    "subject": best_model,
                    "metric": "r2_score",
                    "value": best_r2,
                },
                {
                    "claim_id": "plateau",
                    "claim_text": f"Performance plateaus after {feature_count} features.",
                    "claim_type": "plateau",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.92,
                    "subject": best_model,
                    "feature_count": feature_count,
                    "value": feature_count,
                },
            ],
        }

    def _ranking_output(self, context: dict[str, Any]) -> dict[str, Any]:
        ranking = sorted(context.get("gra_ranking", []), key=lambda item: int(item.get("rank", 10_000)))
        top = ranking[0]
        ordered_items = [str(item["feature"]) for item in ranking[:3]]
        top_feature = str(top["feature"])
        top_score = _round_number(_as_float(top["score"]))
        explanation_full = (
            f"The GRA ranking is led by {top_feature} with score {top_score:.6f}. "
            f"The top ordering is {' > '.join(ordered_items)}."
        )
        return {
            "artifact_id": context["artifact_id"],
            "arm": context["arm"],
            "input_condition": context["input_condition"],
            "explanation_short": f"{top_feature} is the top-ranked GRA feature.",
            "explanation_full": explanation_full,
            "claims": [
                {
                    "claim_id": "top-feature",
                    "claim_text": f"{top_feature} is the top feature in the GRA ranking.",
                    "claim_type": "top_feature",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.98,
                    "object": top_feature,
                },
                {
                    "claim_id": "rank-order",
                    "claim_text": f"The top GRA ordering is {' > '.join(ordered_items)}.",
                    "claim_type": "ranking",
                    "span_category": "sentence",
                    "is_numeric": False,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.95,
                    "ordered_items": ordered_items,
                },
                {
                    "claim_id": "top-score",
                    "claim_text": f"{top_feature} has GRA score {top_score:.6f}.",
                    "claim_type": "rank_score",
                    "span_category": "sentence",
                    "is_numeric": True,
                    "requires_grounding_from": "table/json",
                    "confidence": 0.96,
                    "subject": top_feature,
                    "metric": "gra_score",
                    "value": top_score,
                },
            ],
        }


def _claim_schema() -> dict[str, Any]:
    scalar_or_null = {
        "anyOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "boolean"},
            {"type": "null"},
        ]
    }
    string_array_or_null = {
        "anyOf": [
            {
                "type": "array",
                "items": {"type": "string"},
            },
            {"type": "null"},
        ]
    }
    return {
        "type": "object",
        "properties": {
            "claim_id": {"type": "string"},
            "claim_text": {"type": "string"},
            "claim_type": {"type": "string", "enum": list(CANONICAL_CLAIM_TYPES)},
            "span_category": {"type": "string"},
            "is_numeric": {"type": "boolean"},
            "requires_grounding_from": {"type": "string"},
            "confidence": {"type": "number"},
            "source_variable_id": {"type": ["string", "null"]},
            "subject": {"type": ["string", "null"]},
            "predicate": {"type": ["string", "null"]},
            "object": scalar_or_null,
            "metric": {"type": ["string", "null"]},
            "value": scalar_or_null,
            "unit": {"type": ["string", "null"]},
            "ordered_items": string_array_or_null,
            "feature_count": {"type": ["integer", "null"]},
            "hedged": {"type": "boolean"},
        },
        "required": [
            "claim_id",
            "claim_text",
            "claim_type",
            "span_category",
            "is_numeric",
            "requires_grounding_from",
            "confidence",
            "source_variable_id",
            "subject",
            "predicate",
            "object",
            "metric",
            "value",
            "unit",
            "ordered_items",
            "feature_count",
            "hedged",
        ],
        "additionalProperties": False,
    }


def _variable_mention_schema() -> dict[str, Any]:
    scalar_or_null = {
        "anyOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "null"},
        ]
    }
    string_array_or_null = {
        "anyOf": [
            {
                "type": "array",
                "items": {"type": "string"},
            },
            {"type": "null"},
        ]
    }
    return {
        "type": "object",
        "properties": {
            "mention_id": {"type": "string"},
            "source_variable_id": {"type": "string"},
            "evidence_span": {"type": "string"},
            "stated_value": scalar_or_null,
            "stated_object": {"type": ["string", "null"]},
            "stated_ordered_items": string_array_or_null,
            "stated_feature_count": {"type": ["integer", "null"]},
            "confidence": {"type": "number"},
        },
        "required": [
            "mention_id",
            "source_variable_id",
            "evidence_span",
            "stated_value",
            "stated_object",
            "stated_ordered_items",
            "stated_feature_count",
            "confidence",
        ],
        "additionalProperties": False,
    }


def _semantic_level_schema(allowed_semantic_levels: list[str] | None = None) -> dict[str, Any]:
    levels = [level for level in (allowed_semantic_levels or SUPPORTED_SEMANTIC_LEVELS) if level in SUPPORTED_SEMANTIC_LEVELS]
    return {
        "anyOf": [
            {"type": "null"},
            {"type": "string", "enum": levels},
        ]
    }


def _explanation_schema(
    allowed_arms: list[str],
    allowed_conditions: list[str],
    allowed_semantic_levels: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "artifact_id": {"type": "string"},
            "arm": {"type": "string", "enum": allowed_arms},
            "input_condition": {"type": "string", "enum": allowed_conditions},
            "semantic_level": _semantic_level_schema(allowed_semantic_levels),
            "explanation_short": {"type": "string"},
            "explanation_full": {"type": "string"},
        },
        "required": [
            "artifact_id",
            "arm",
            "input_condition",
            "semantic_level",
            "explanation_short",
            "explanation_full",
        ],
        "additionalProperties": False,
    }


def _claim_extraction_schema(
    allowed_arms: list[str],
    allowed_conditions: list[str],
    allowed_semantic_levels: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "artifact_id": {"type": "string"},
            "arm": {"type": "string", "enum": allowed_arms},
            "input_condition": {"type": "string", "enum": allowed_conditions},
            "semantic_level": _semantic_level_schema(allowed_semantic_levels),
            "claims": {
                "type": "array",
                "items": _claim_schema(),
            },
        },
        "required": [
            "artifact_id",
            "arm",
            "input_condition",
            "semantic_level",
            "claims",
        ],
        "additionalProperties": False,
    }


def _variable_mention_extraction_schema(
    allowed_arms: list[str],
    allowed_conditions: list[str],
    allowed_semantic_levels: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "artifact_id": {"type": "string"},
            "arm": {"type": "string", "enum": allowed_arms},
            "input_condition": {"type": "string", "enum": allowed_conditions},
            "semantic_level": _semantic_level_schema(allowed_semantic_levels),
            "mentions": {
                "type": "array",
                "items": _variable_mention_schema(),
            },
        },
        "required": [
            "artifact_id",
            "arm",
            "input_condition",
            "semantic_level",
            "mentions",
        ],
        "additionalProperties": False,
    }


def _arm_c_validation_record_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "claim_id": {"type": "string"},
            "claim_text": {"type": "string"},
            "status": {
                "type": "string",
                "enum": ["supported", "partially_supported", "contradicted", "unverifiable"],
            },
            "recommended_action": {
                "type": "string",
                "enum": ["keep", "edit", "drop"],
            },
            "rationale": {"type": "string"},
            "matched_fact_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
            "grounded_fact_summary": {"type": ["string", "null"]},
        },
        "required": [
            "claim_id",
            "claim_text",
            "status",
            "recommended_action",
            "rationale",
            "matched_fact_ids",
            "grounded_fact_summary",
        ],
        "additionalProperties": False,
    }


def _arm_c_validation_schema(
    allowed_conditions: list[str],
    claim_count: int | None = None,
) -> dict[str, Any]:
    records_schema: dict[str, Any] = {
        "type": "array",
        "items": _arm_c_validation_record_schema(),
    }
    if claim_count is not None:
        records_schema["minItems"] = claim_count
        records_schema["maxItems"] = claim_count
    return {
        "type": "object",
        "properties": {
            "artifact_id": {"type": "string"},
            "arm": {"type": "string", "enum": ["C"]},
            "input_condition": {"type": "string", "enum": allowed_conditions},
            "validation_records": records_schema,
        },
        "required": [
            "artifact_id",
            "arm",
            "input_condition",
            "validation_records",
        ],
        "additionalProperties": False,
    }


def _arm_c_corrector_schema(
    allowed_conditions: list[str],
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "artifact_id": {"type": "string"},
            "arm": {"type": "string", "enum": ["C"]},
            "input_condition": {"type": "string", "enum": allowed_conditions},
            "semantic_level": {"type": "null"},
            "explanation_short": {"type": "string"},
            "explanation_full": {"type": "string"},
            "claims": {
                "type": "array",
                "items": _claim_schema(),
            },
        },
        "required": [
            "artifact_id",
            "arm",
            "input_condition",
            "semantic_level",
            "explanation_short",
            "explanation_full",
            "claims",
        ],
        "additionalProperties": False,
    }


def _single_explanation_schema(
    allowed_arms: list[str],
    allowed_conditions: list[str],
    allowed_semantic_levels: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "benchmark_explanation",
            "strict": True,
            "schema": _explanation_schema(
                allowed_arms,
                allowed_conditions,
                allowed_semantic_levels,
            ),
        },
    }


def _single_claim_extraction_schema(
    allowed_arms: list[str],
    allowed_conditions: list[str],
    allowed_semantic_levels: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "benchmark_claim_extraction",
            "strict": True,
            "schema": _claim_extraction_schema(
                allowed_arms,
                allowed_conditions,
                allowed_semantic_levels,
            ),
        },
    }


def _single_variable_mention_extraction_schema(
    allowed_arms: list[str],
    allowed_conditions: list[str],
    allowed_semantic_levels: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "benchmark_variable_mention_extraction",
            "strict": True,
            "schema": _variable_mention_extraction_schema(
                allowed_arms,
                allowed_conditions,
                allowed_semantic_levels,
            ),
        },
    }


def _single_arm_c_validation_schema(
    allowed_conditions: list[str],
    claim_count: int | None = None,
) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "arm_c_validator_output",
            "strict": True,
            "schema": _arm_c_validation_schema(allowed_conditions, claim_count),
        },
    }


def _single_arm_c_corrector_schema(
    allowed_conditions: list[str],
) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "arm_c_corrector_output",
            "strict": True,
            "schema": _arm_c_corrector_schema(allowed_conditions),
        },
    }


def _batch_explanation_schema(
    *,
    explanation_count: int,
    allowed_arms: list[str],
    allowed_conditions: list[str],
    allowed_semantic_levels: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "benchmark_explanation_batch",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "generations": {
                        "type": "array",
                        "items": _explanation_schema(
                            allowed_arms,
                            allowed_conditions,
                            allowed_semantic_levels,
                        ),
                        "minItems": explanation_count,
                        "maxItems": explanation_count,
                    }
                },
                "required": ["generations"],
                "additionalProperties": False,
            },
        },
    }


class OllamaLLMClient(BaseLLMClient):
    """Local Ollama benchmark client using one request per arm-condition output."""

    name = "ollama"

    def __init__(
        self,
        *,
        model: str | None = None,
        timeout_seconds: int = OLLAMA_BENCHMARK_TIMEOUT_SECONDS,
    ) -> None:
        from dotenv import load_dotenv

        env_path = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(dotenv_path=env_path, override=False)
        self.model_name = str(
            model
            or os.getenv("OLLAMA_BENCHMARK_MODEL")
            or os.getenv("OLLAMA_REPORT_MODEL")
            or OLLAMA_BENCHMARK_MODEL
        ).strip()
        if not self.model_name:
            raise RuntimeError("OLLAMA_BENCHMARK_MODEL is not configured for the benchmark client.")
        self.timeout_seconds = max(60, int(timeout_seconds))

    def _call_ollama(self, payload: dict[str, Any]) -> dict[str, Any]:
        import requests

        chat_url = f"{OLLAMA_BASE_URL}/api/chat"

        def _post(chat_payload: dict[str, Any]) -> dict[str, Any]:
            response = requests.post(
                chat_url,
                headers={"Content-Type": "application/json"},
                json=_ollama_json_payload(chat_payload),
                timeout=self.timeout_seconds,
            )
            if not response.ok:
                body = response.text.strip()
                detail = body[:800] if body else response.reason
                raise RuntimeError(
                    f"Ollama benchmark HTTP {response.status_code}: {detail}"
                )
            return response.json()

        def _repair(raw_content: str, original_payload: dict[str, Any]) -> dict[str, Any]:
            repair_schema = dict(original_payload.get("format") or {})
            repair_payload = {
                "model": original_payload["model"],
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Convert the provided content into one valid JSON object only. "
                            "Do not add markdown or commentary."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            _build_ollama_json_only_instruction(repair_schema)
                            + "\n\nContent to convert:\n"
                            + raw_content
                        ),
                    },
                ],
                "stream": False,
                "format": repair_schema,
                "options": {
                    "temperature": 0,
                    "num_predict": max(
                        int((original_payload.get("options") or {}).get("num_predict") or OLLAMA_BENCHMARK_JSON_NUM_PREDICT),
                        OLLAMA_BENCHMARK_JSON_NUM_PREDICT,
                    ),
                    "num_ctx": max(
                        int((original_payload.get("options") or {}).get("num_ctx") or OLLAMA_BENCHMARK_NUM_CTX),
                        8192,
                    ),
                },
            }
            repair_data = _post(repair_payload)
            repair_content = _ollama_message_text(repair_data.get("message") or {})
            if not repair_content:
                raise ValueError("Ollama benchmark repair response returned empty content.")
            return _extract_json_object(repair_content, "Ollama")

        last_error: Exception | None = None
        for attempt_index in range(OLLAMA_BENCHMARK_MAX_RETRIES):
            request_payload = copy.deepcopy(payload)
            if attempt_index > 0 and request_payload.get("messages"):
                retry_message = (
                    "Your previous response was empty or invalid. "
                    "Return only one valid JSON object that matches the requested schema. "
                    "Do not write reasoning, do not use markdown, and do not leave message.content empty. "
                    "Put the JSON object in the final assistant content."
                )
                first_message = dict(request_payload["messages"][0])
                first_message["content"] = f"{first_message.get('content', '')} {retry_message}".strip()
                request_payload["messages"][0] = first_message

            try:
                data = _post(request_payload)
                message = data.get("message") or {}
                content = _ollama_message_text(message)
                if not content.strip():
                    raise ValueError("Ollama benchmark response returned empty content.")
                try:
                    return _extract_json_object(content, "Ollama")
                except ValueError:
                    return _repair(content, request_payload)
            except Exception as exc:
                last_error = exc
                if attempt_index + 1 >= OLLAMA_BENCHMARK_MAX_RETRIES:
                    break
                wait_seconds = (
                    OLLAMA_BENCHMARK_RETRY_BACKOFF_SECONDS * (attempt_index + 1)
                    + random.uniform(0.0, OLLAMA_BENCHMARK_RETRY_JITTER_SECONDS)
                )
                print(
                    "⚠️ Ollama benchmark request "
                    f"attempt {attempt_index + 1}/{OLLAMA_BENCHMARK_MAX_RETRIES} failed: "
                    f"{exc}. Retrying in {wait_seconds:.1f}s."
                )
                time.sleep(wait_seconds)

        if last_error is not None:
            raise last_error
        raise ValueError("Ollama benchmark request failed for an unknown reason.")

    def generate_explanation_json(self, prompt: str) -> dict[str, Any]:
        context = extract_prompt_context(prompt)
        schema = _single_explanation_schema(
            allowed_arms=[str(context.get("arm") or "A")],
            allowed_conditions=[str(context.get("input_condition") or "table_only")],
            allowed_semantic_levels=[str(context.get("semantic_level") or "").strip()]
            if str(context.get("semantic_level") or "").strip()
            else None,
        )["json_schema"]["schema"]
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        _build_ollama_json_only_instruction(schema)
                        + " Unsupported claims must be omitted rather than guessed."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0,
                "num_predict": OLLAMA_BENCHMARK_GENERATION_NUM_PREDICT,
                "num_ctx": OLLAMA_BENCHMARK_NUM_CTX,
            },
        }
        return self._call_ollama(payload)

    def extract_claims_json(self, prompt: str) -> dict[str, Any]:
        context = extract_claim_extraction_context(prompt)
        schema = _single_claim_extraction_schema(
            allowed_arms=[str(context.get("arm") or "A")],
            allowed_conditions=[str(context.get("input_condition") or "table_only")],
            allowed_semantic_levels=[str(context.get("semantic_level") or "").strip()]
            if str(context.get("semantic_level") or "").strip()
            else None,
        )["json_schema"]["schema"]
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        _build_ollama_json_only_instruction(schema)
                        + " Extract only the listed standardized variables that are explicitly present in the explanation."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0,
                "num_predict": OLLAMA_BENCHMARK_JSON_NUM_PREDICT,
                "num_ctx": OLLAMA_BENCHMARK_NUM_CTX,
            },
        }
        return self._call_ollama(payload)

    def extract_variable_mentions_json(self, prompt: str) -> dict[str, Any]:
        context = extract_variable_mention_context(prompt)
        schema = _single_variable_mention_extraction_schema(
            allowed_arms=[str(context.get("arm") or "A")],
            allowed_conditions=[str(context.get("input_condition") or "table_only")],
            allowed_semantic_levels=[str(context.get("semantic_level") or "").strip()]
            if str(context.get("semantic_level") or "").strip()
            else None,
        )["json_schema"]["schema"]
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        _build_ollama_json_only_instruction(schema)
                        + " Select only listed source_variable_id values explicitly present in the explanation. "
                        + "Do not convert rank positions into metric values."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0,
                "num_predict": OLLAMA_BENCHMARK_JSON_NUM_PREDICT,
                "num_ctx": OLLAMA_BENCHMARK_NUM_CTX,
            },
        }
        return self._call_ollama(payload)

    def validate_arm_c_json(self, prompt: str) -> dict[str, Any]:
        context = extract_prompt_context(prompt)
        schema = _single_arm_c_validation_schema(
            allowed_conditions=[str(context.get("input_condition") or "table_only")],
            claim_count=len(list(context.get("claims") or [])),
        )["json_schema"]["schema"]
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        _build_ollama_json_only_instruction(schema)
                        + " You are an adversarial evidence validator. "
                        + "Do not trust extracted source_variable_id values. "
                        + "Mark keep only when every entity, metric, object, ranking, and numeric value is fully grounded."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0,
                "num_predict": OLLAMA_BENCHMARK_JSON_NUM_PREDICT,
                "num_ctx": OLLAMA_BENCHMARK_NUM_CTX,
            },
        }
        return self._call_ollama(payload)

    def correct_arm_c_json(self, prompt: str) -> dict[str, Any]:
        context = extract_prompt_context(prompt)
        schema = _single_arm_c_corrector_schema(
            allowed_conditions=[str(context.get("input_condition") or "table_only")],
        )["json_schema"]["schema"]
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        _build_ollama_json_only_instruction(schema)
                        + " You are correcting an explanation and must return the corrected explanation plus grounded structured claims only."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0,
                "num_predict": OLLAMA_BENCHMARK_JSON_NUM_PREDICT,
                "num_ctx": OLLAMA_BENCHMARK_NUM_CTX,
            },
        }
        response = self._call_ollama(payload)
        return _normalize_embedded_claims(
            response,
            list((context.get("evidence_packet") or {}).get("allowed_variables") or []),
        )

    def generate_artifact(
        self,
        inputs: ArtifactInputs,
        arms: list[str],
        conditions: list[str],
        semantic_levels: list[str] | None = None,
        variable_catalog_by_level: dict[str | None, list[dict[str, Any]]] | None = None,
    ) -> list[dict[str, Any]]:
        requested_outputs: list[dict[str, Any]] = []
        requested_runs = _requested_runs(arms, conditions, semantic_levels)
        for arm, condition, semantic_level in requested_runs:
            requested_outputs.append(
                {
                    "arm": arm,
                    "input_condition": condition,
                    "semantic_level": semantic_level,
                    "arm_instruction": ARM_INSTRUCTIONS.get(arm, ARM_INSTRUCTIONS["A"]),
                    "context": build_prompt_context(
                        inputs=inputs,
                        arm=arm,
                        condition=condition,
                        semantic_level=semantic_level,
                    ),
                }
            )

        schema = _batch_explanation_schema(
            explanation_count=len(requested_outputs),
            allowed_arms=arms,
            allowed_conditions=conditions,
            allowed_semantic_levels=semantic_levels,
        )["json_schema"]["schema"]
        payload = {
            "task": (
                "Generate one explanation output for each requested arm-condition pair. "
                "Each output must stay artifact-grounded and contain explanation text only."
            ),
            "rules": [
                "Table/json evidence outranks chart evidence.",
                "Chart evidence outranks summary text.",
                "Do not use llm_explanations.json as ground truth.",
                "Keep explanation_short to one sentence.",
                "Keep explanation_full concise: roughly 60-100 words per output.",
            ],
            "requested_outputs": requested_outputs,
        }
        request_payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        _build_ollama_json_only_instruction(schema)
                        + " You generate artifact-grounded ML explanations for offline benchmarking. "
                        + "Keep the explanation grounded in the artifact context."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0,
                "num_predict": max(
                    OLLAMA_BENCHMARK_GENERATION_NUM_PREDICT,
                    1200 * len(requested_outputs),
                ),
                "num_ctx": OLLAMA_BENCHMARK_NUM_CTX,
            },
        }
        explanations_by_pair: dict[tuple[str, str, str | None], dict[str, Any]] = {}

        try:
            parsed = self._call_ollama(request_payload)
            generations = parsed.get("generations")
            if not isinstance(generations, list):
                raise ValueError("Ollama benchmark response did not contain a generations array.")
            for generation in generations:
                if not isinstance(generation, dict):
                    continue
                arm = str(generation.get("arm") or "").strip()
                condition = str(generation.get("input_condition") or "").strip()
                semantic_level = str(generation.get("semantic_level") or "").strip() or None
                if (arm, condition, semantic_level) not in requested_runs:
                    continue
                explanations_by_pair[(arm, condition, semantic_level)] = generation
        except Exception:
            explanations_by_pair = {}

        for arm, condition, semantic_level in requested_runs:
            if (arm, condition, semantic_level) in explanations_by_pair:
                continue
            prompt = build_explanation_prompt(
                inputs=inputs,
                arm=arm,
                condition=condition,
                semantic_level=semantic_level,
            )
            try:
                explanations_by_pair[(arm, condition, semantic_level)] = self.generate_explanation_json(prompt)
            except Exception as exc:
                explanations_by_pair[(arm, condition, semantic_level)] = _failed_generation_payload(
                    artifact_id=inputs.record.artifact_id,
                    arm=arm,
                    input_condition=condition,
                    error_message=str(exc),
                    semantic_level=semantic_level,
                )

        outputs: list[dict[str, Any]] = []
        catalogs = variable_catalog_by_level or {None: []}
        for arm, condition, semantic_level in requested_runs:
            explanation_payload = explanations_by_pair[(arm, condition, semantic_level)]
            if not explanation_payload.get("explanation_full"):
                outputs.append(_merge_explanation_and_claims(explanation_payload, None))
                continue
            try:
                claims_payload = self.extract_claims_json(
                    build_claim_extraction_prompt(
                        artifact_id=inputs.record.artifact_id,
                        arm=arm,
                        input_condition=condition,
                        semantic_level=semantic_level,
                        explanation_short=str(explanation_payload.get("explanation_short") or ""),
                        explanation_full=str(explanation_payload.get("explanation_full") or ""),
                        primary_entities=inputs.record.primary_entities,
                        variable_catalog=_variable_catalog_for_level(catalogs, semantic_level),
                    )
                )
            except Exception:
                claims_payload = {
                    "artifact_id": inputs.record.artifact_id,
                    "arm": arm,
                    "input_condition": condition,
                    "semantic_level": semantic_level,
                    "claims": [],
                }
            outputs.append(_merge_explanation_and_claims(explanation_payload, claims_payload))

        return outputs


class OpenAILLMClient(BaseLLMClient):
    """Real LLM client for benchmark generation with one request per artifact."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = OPENAI_BENCHMARK_TIMEOUT_SECONDS,
    ) -> None:
        from dotenv import load_dotenv

        env_path = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(dotenv_path=env_path, override=False)
        resolved_api_key = str(api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if not resolved_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured for the benchmark client.")
        self.api_key = resolved_api_key
        self.model_name = str(model or os.getenv("OPENAI_BENCHMARK_MODEL") or OPENAI_BENCHMARK_MODEL).strip()
        self.timeout_seconds = max(60, int(timeout_seconds))

    @staticmethod
    def _retry_after_seconds(response: Any) -> float | None:
        if response is None:
            return None

        retry_after = str(response.headers.get("Retry-After") or "").strip()
        if not retry_after:
            return None

        try:
            return max(0.0, float(retry_after))
        except ValueError:
            return None

    def _call_openai(self, payload: dict[str, Any]) -> dict[str, Any]:
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(1, OPENAI_BENCHMARK_MAX_RETRIES + 1):
            try:
                with shared_openai_request_gate().request_slot(
                    OPENAI_BENCHMARK_MIN_REQUEST_INTERVAL_SECONDS,
                    OPENAI_BENCHMARK_RETRY_JITTER_SECONDS,
                ):
                    response = requests.post(
                        OPENAI_CHAT_COMPLETIONS_URL,
                        headers=headers,
                        json=payload,
                        timeout=self.timeout_seconds,
                    )
                response.raise_for_status()
                data = response.json()
                choice = data["choices"][0]
                message = choice.get("message") or {}
                parsed = message.get("parsed")
                if isinstance(parsed, dict):
                    return parsed

                content = message.get("content")
                if isinstance(content, list):
                    text_parts: list[str] = []
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        text = item.get("text") or item.get("content") or ""
                        if isinstance(text, str) and text.strip():
                            text_parts.append(text)
                    content = "".join(text_parts)

                if not isinstance(content, str) or not content.strip():
                    finish_reason = choice.get("finish_reason")
                    if finish_reason == "length":
                        raise ValueError(
                            "OpenAI benchmark response hit finish_reason='length' before emitting JSON. "
                            "Increase max_completion_tokens or reduce prompt size."
                        )
                    raise ValueError(
                        "OpenAI benchmark response did not contain a parseable JSON payload."
                    )
                return json.loads(content)
            except requests.HTTPError as exc:
                last_error = exc
                status_code = exc.response.status_code if exc.response is not None else None
                should_retry = status_code == 429 or (status_code is not None and status_code >= 500)
                if not should_retry or attempt >= OPENAI_BENCHMARK_MAX_RETRIES:
                    raise
                retry_after_seconds = self._retry_after_seconds(exc.response)
            except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt >= OPENAI_BENCHMARK_MAX_RETRIES:
                    raise
                retry_after_seconds = None

            wait_seconds = max(
                retry_after_seconds or 0.0,
                OPENAI_BENCHMARK_RETRY_BACKOFF_SECONDS * attempt,
            ) + random.uniform(0.0, OPENAI_BENCHMARK_RETRY_JITTER_SECONDS)
            shared_openai_request_gate().push_cooldown(wait_seconds)
            print(
                f"⚠️ Benchmark OpenAI request attempt {attempt}/{OPENAI_BENCHMARK_MAX_RETRIES} failed: "
                f"{last_error}. Retrying in {wait_seconds:.1f}s."
            )
            time.sleep(wait_seconds)

        raise RuntimeError(
            f"Benchmark OpenAI request failed after {OPENAI_BENCHMARK_MAX_RETRIES} attempts: {last_error}"
        )

    def generate_explanation_json(self, prompt: str) -> dict[str, Any]:
        context = extract_prompt_context(prompt)
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate artifact-grounded ML explanations for offline benchmarking. "
                        "Return strict JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "response_format": _single_explanation_schema(
                allowed_arms=[str(context.get("arm") or "A")],
                allowed_conditions=[str(context.get("input_condition") or "table_only")],
                allowed_semantic_levels=[str(context.get("semantic_level") or "").strip()]
                if str(context.get("semantic_level") or "").strip()
                else None,
            ),
            "reasoning_effort": "low",
            "verbosity": "low",
            "max_completion_tokens": 1800,
        }
        return self._call_openai(payload)

    def extract_claims_json(self, prompt: str) -> dict[str, Any]:
        context = extract_claim_extraction_context(prompt)
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You extract standardized benchmark variables from explanations. "
                        "Return strict JSON only. Extract only variables explicitly present in the explanation."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "response_format": _single_claim_extraction_schema(
                allowed_arms=[str(context.get("arm") or "A")],
                allowed_conditions=[str(context.get("input_condition") or "table_only")],
                allowed_semantic_levels=[str(context.get("semantic_level") or "").strip()]
                if str(context.get("semantic_level") or "").strip()
                else None,
            ),
            "reasoning_effort": "low",
            "verbosity": "low",
            "max_completion_tokens": 1800,
        }
        return self._call_openai(payload)

    def extract_variable_mentions_json(self, prompt: str) -> dict[str, Any]:
        context = extract_variable_mention_context(prompt)
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You select standardized benchmark variables from explanations. "
                        "Return strict JSON only. Select only listed source_variable_id values explicitly present in the explanation. "
                        "Do not convert rank positions into metric values."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "response_format": _single_variable_mention_extraction_schema(
                allowed_arms=[str(context.get("arm") or "A")],
                allowed_conditions=[str(context.get("input_condition") or "table_only")],
                allowed_semantic_levels=[str(context.get("semantic_level") or "").strip()]
                if str(context.get("semantic_level") or "").strip()
                else None,
            ),
            "reasoning_effort": "low",
            "verbosity": "low",
            "max_completion_tokens": 1800,
        }
        return self._call_openai(payload)

    def validate_arm_c_json(self, prompt: str) -> dict[str, Any]:
        context = extract_prompt_context(prompt)
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an adversarial evidence validator for a multi-stage factual correction "
                        "pipeline. Do not trust extracted source_variable_id values. Mark keep only when "
                        "every entity, metric, object, ranking, and numeric value is fully grounded. "
                        "Return strict JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "response_format": _single_arm_c_validation_schema(
                allowed_conditions=[str(context.get("input_condition") or "table_only")],
                claim_count=len(list(context.get("claims") or [])),
            ),
            "reasoning_effort": "low",
            "verbosity": "low",
            "max_completion_tokens": 1800,
        }
        return self._call_openai(payload)

    def correct_arm_c_json(self, prompt: str) -> dict[str, Any]:
        context = extract_prompt_context(prompt)
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You correct artifact-grounded ML explanations. Return strict JSON only with the corrected explanation and structured claims."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "response_format": _single_arm_c_corrector_schema(
                allowed_conditions=[str(context.get("input_condition") or "table_only")],
            ),
            "reasoning_effort": "low",
            "verbosity": "low",
            "max_completion_tokens": 1800,
        }
        response = self._call_openai(payload)
        return _normalize_embedded_claims(
            response,
            list((context.get("evidence_packet") or {}).get("allowed_variables") or []),
        )

    def generate_artifact(
        self,
        inputs: ArtifactInputs,
        arms: list[str],
        conditions: list[str],
        semantic_levels: list[str] | None = None,
        variable_catalog_by_level: dict[str | None, list[dict[str, Any]]] | None = None,
    ) -> list[dict[str, Any]]:
        requested_outputs: list[dict[str, Any]] = []
        requested_runs = _requested_runs(arms, conditions, semantic_levels)
        for arm, condition, semantic_level in requested_runs:
            requested_outputs.append(
                {
                    "arm": arm,
                    "input_condition": condition,
                    "semantic_level": semantic_level,
                    "arm_instruction": ARM_INSTRUCTIONS.get(arm, ARM_INSTRUCTIONS["A"]),
                    "context": build_prompt_context(
                        inputs=inputs,
                        arm=arm,
                        condition=condition,
                        semantic_level=semantic_level,
                    ),
                }
            )

        payload = {
            "task": (
                "Generate one explanation output for each requested arm-condition pair. "
                "Each output must stay artifact-grounded and contain explanation text only."
            ),
            "rules": [
                "Table/json evidence outranks chart evidence.",
                "Chart evidence outranks summary text.",
                "Do not use llm_explanations.json as ground truth.",
                "Keep explanation_short to one sentence.",
                "Keep explanation_full concise: roughly 60-100 words per output.",
            ],
            "requested_outputs": requested_outputs,
        }
        request_payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate artifact-grounded ML explanations for offline benchmarking. "
                        "Return strict JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            "response_format": _batch_explanation_schema(
                explanation_count=len(requested_outputs),
                allowed_arms=arms,
                allowed_conditions=conditions,
                allowed_semantic_levels=semantic_levels,
            ),
            "reasoning_effort": "low",
            "verbosity": "low",
            "max_completion_tokens": max(2200, 1200 * len(requested_outputs)),
        }
        explanations_by_pair: dict[tuple[str, str, str | None], dict[str, Any]] = {}
        try:
            self.set_runtime_context(
                artifact_id=inputs.record.artifact_id,
                stage="generate_batch",
                requested_runs=len(requested_runs),
            )
            parsed = self._call_openai(request_payload)
            generations = parsed.get("generations")
            if not isinstance(generations, list):
                raise ValueError("OpenAI benchmark response did not contain a generations array.")
            for generation in generations:
                if not isinstance(generation, dict):
                    continue
                arm = str(generation.get("arm") or "").strip()
                condition = str(generation.get("input_condition") or "").strip()
                semantic_level = str(generation.get("semantic_level") or "").strip() or None
                if (arm, condition, semantic_level) not in requested_runs:
                    continue
                explanations_by_pair[(arm, condition, semantic_level)] = generation
        except Exception:
            explanations_by_pair = {}

        for arm, condition, semantic_level in requested_runs:
            if (arm, condition, semantic_level) in explanations_by_pair:
                continue
            try:
                self.set_runtime_context(
                    artifact_id=inputs.record.artifact_id,
                    arm=arm,
                    input_condition=condition,
                    semantic_level=semantic_level,
                    stage="generate_explanation",
                )
                explanations_by_pair[(arm, condition, semantic_level)] = self.generate_explanation_json(
                    build_explanation_prompt(
                        inputs=inputs,
                        arm=arm,
                        condition=condition,
                        semantic_level=semantic_level,
                    )
                )
            except Exception as exc:
                explanations_by_pair[(arm, condition, semantic_level)] = _failed_generation_payload(
                    artifact_id=inputs.record.artifact_id,
                    arm=arm,
                    input_condition=condition,
                    error_message=str(exc),
                    semantic_level=semantic_level,
                )

        outputs: list[dict[str, Any]] = []
        catalogs = variable_catalog_by_level or {None: []}
        for arm, condition, semantic_level in requested_runs:
            explanation_payload = explanations_by_pair[(arm, condition, semantic_level)]
            try:
                self.set_runtime_context(
                    artifact_id=inputs.record.artifact_id,
                    arm=arm,
                    input_condition=condition,
                    semantic_level=semantic_level,
                    stage="extract_claims",
                )
                claims_payload = self.extract_claims_json(
                    build_claim_extraction_prompt(
                        artifact_id=inputs.record.artifact_id,
                        arm=arm,
                        input_condition=condition,
                        semantic_level=semantic_level,
                        explanation_short=str(explanation_payload.get("explanation_short") or ""),
                        explanation_full=str(explanation_payload.get("explanation_full") or ""),
                        primary_entities=inputs.record.primary_entities,
                        variable_catalog=_variable_catalog_for_level(catalogs, semantic_level),
                    )
                )
            except Exception:
                claims_payload = {
                    "artifact_id": inputs.record.artifact_id,
                    "arm": arm,
                    "input_condition": condition,
                    "semantic_level": semantic_level,
                    "claims": [],
                }
            outputs.append(_merge_explanation_and_claims(explanation_payload, claims_payload))

        self.clear_runtime_context()
        return outputs


class GroqLLMClient(OpenAILLMClient):
    """Groq OpenAI-compatible benchmark client."""

    name = "groq"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = GROQ_BENCHMARK_TIMEOUT_SECONDS,
    ) -> None:
        from dotenv import load_dotenv

        env_path = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(dotenv_path=env_path, override=False)
        resolved_api_keys = parse_groq_api_keys(api_key) or groq_api_keys_from_env()
        if not resolved_api_keys:
            raise RuntimeError("GROQ_API_KEY or GROQ_API_KEYS is not configured for the benchmark client.")
        self.api_key = resolved_api_keys[0]
        self.api_key_pool = GroqApiKeyPool(resolved_api_keys)
        self.model_name = str(
            model
            or os.getenv("GROQ_BENCHMARK_MODEL")
            or os.getenv("GROQ_REPORT_MODEL")
            or GROQ_BENCHMARK_MODEL
        ).strip()
        if self.model_name not in GROQ_BENCHMARK_MODELS:
            allowed = ", ".join(GROQ_BENCHMARK_MODELS)
            raise RuntimeError(
                f"Unsupported GROQ_BENCHMARK_MODEL '{self.model_name}'. Supported values: {allowed}."
            )
        self.timeout_seconds = max(60, int(timeout_seconds))

    def _prepare_groq_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_payload = copy.deepcopy(payload)
        request_payload.pop("verbosity", None)
        request_payload["temperature"] = 0
        if request_payload.get("max_completion_tokens") is not None:
            completion_cap = GROQ_BENCHMARK_MAX_COMPLETION_TOKENS
            if self.model_name == "llama-3.3-70b-versatile":
                completion_cap = min(completion_cap, 600)
            request_payload["max_completion_tokens"] = min(
                int(request_payload["max_completion_tokens"]),
                completion_cap,
            )

        if not str(self.model_name).startswith("openai/gpt-oss"):
            request_payload.pop("reasoning_effort", None)
        elif request_payload.get("reasoning_effort") not in {"low", "medium", "high"}:
            request_payload["reasoning_effort"] = "low"

        response_format = request_payload.get("response_format")
        schema = None
        if isinstance(response_format, dict):
            json_schema = response_format.get("json_schema")
            if isinstance(json_schema, dict):
                schema = json_schema.get("schema")
        request_payload.pop("response_format", None)
        if isinstance(schema, dict):
            messages = list(request_payload.get("messages") or [])
            if messages:
                first_message = dict(messages[0])
                first_message["content"] = (
                    f"{first_message.get('content', '')} "
                    f"{_build_groq_json_only_instruction()}"
                ).strip()
                messages[0] = first_message
                request_payload["messages"] = messages
        return request_payload

    def _call_openai(self, payload: dict[str, Any]) -> dict[str, Any]:
        import requests
        key_pool = getattr(self, "api_key_pool", None)
        if not isinstance(key_pool, GroqApiKeyPool):
            key_pool = GroqApiKeyPool(parse_groq_api_keys(getattr(self, "api_key", "")))
            self.api_key_pool = key_pool
        request_payload = self._prepare_groq_payload(payload)

        last_error: Exception | None = None
        last_response: Any = None
        attempt = 0
        effective_max_attempts = (
            GROQ_BENCHMARK_MAX_REQUEST_ATTEMPTS
            if GROQ_BENCHMARK_RETRY_FOREVER
            else max(GROQ_BENCHMARK_MAX_RETRIES, GROQ_BENCHMARK_MAX_REQUEST_ATTEMPTS)
        )

        def _emit_retry_runtime_status(
            *,
            key_label: str,
            wait_seconds: float,
            error: Exception,
            response: Any = None,
        ) -> None:
            error_text = (
                _format_http_error(error, "Groq benchmark")
                if isinstance(error, requests.HTTPError)
                else str(error)
            )
            retry_payload: dict[str, Any] = {
                "attempt": int(attempt),
                "max_attempts": int(effective_max_attempts),
                "retry_forever": bool(GROQ_BENCHMARK_RETRY_FOREVER),
                "wait_seconds": round(float(wait_seconds), 1),
                "reason": _benchmark_retry_reason(error, provider_label="Groq benchmark"),
                "key_label": key_label,
            }
            status_code = _benchmark_error_status_code(error)
            if status_code is not None:
                retry_payload["status_code"] = status_code
            if error_text:
                retry_payload["error_message"] = error_text[:500]
            debug_file = self._write_runtime_error(
                {
                    "status": "retrying",
                    "retry": retry_payload,
                    "error_message": error_text,
                    "raw_response": _raw_response_snapshot(response),
                }
            )
            if debug_file:
                retry_payload["debug_file"] = debug_file
            self._write_runtime_status(
                {
                    "status": "retrying",
                    "stage": str(self._runtime_context_payload().get("stage") or "benchmark_request"),
                    "message": (
                        f"{retry_payload['reason']} while generating benchmark output. "
                        f"Retry {attempt}/{effective_max_attempts} in {wait_seconds:.1f}s."
                    ),
                    "retry": retry_payload,
                }
            )

        def _raise_terminal_error(error: Exception, *, key_label: str, response: Any = None) -> None:
            error_text = (
                _format_http_error(error, "Groq benchmark")
                if isinstance(error, requests.HTTPError)
                else str(error)
            )
            debug_payload: dict[str, Any] = {
                "attempt": int(attempt),
                "max_attempts": int(effective_max_attempts),
                "retry_forever": bool(GROQ_BENCHMARK_RETRY_FOREVER),
                "reason": _benchmark_retry_reason(error, provider_label="Groq benchmark"),
                "key_label": key_label,
                "error_message": error_text,
            }
            status_code = _benchmark_error_status_code(error)
            if status_code is not None:
                debug_payload["status_code"] = status_code
            debug_file = self._write_runtime_error(
                {
                    "status": "failed",
                    "retry": debug_payload,
                    "error_message": error_text,
                    "raw_response": _raw_response_snapshot(response),
                }
            )
            if debug_file:
                debug_payload["debug_file"] = debug_file
            self._write_runtime_status(
                {
                    "status": "failed",
                    "stage": str(self._runtime_context_payload().get("stage") or "benchmark_request"),
                    "message": error_text[:500],
                    "retry": debug_payload,
                }
            )
            raise BenchmarkRequestError(error_text, debug_payload=debug_payload) from error

        while True:
            key_pool.refresh_from_laravel()
            if not key_pool.has_usable_key(ignore_cooldown=True):
                key_pool.refresh_from_laravel(force=True)
            if not key_pool.has_usable_key(ignore_cooldown=True):
                raise RuntimeError(
                    "All configured Groq API keys are marked blocked. "
                    "Open Admin > Settings > AI to reactivate or replace a key."
                )
            attempt += 1
            alternate_wait_seconds: float | None = None
            push_global_cooldown = True
            use_alternate_wait = False
            key_pool.wait_for_available_key(GROQ_BENCHMARK_MAX_RETRY_WAIT_SECONDS)
            key_index, api_key = key_pool.next_key()
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            try:
                with shared_openai_request_gate().request_slot(
                    GROQ_BENCHMARK_MIN_REQUEST_INTERVAL_SECONDS,
                    GROQ_BENCHMARK_RETRY_JITTER_SECONDS,
                ):
                    response = requests.post(
                        _groq_chat_completions_url(),
                        headers=headers,
                        json=request_payload,
                        timeout=self.timeout_seconds,
                    )
                last_response = response
                response.raise_for_status()
                data = response.json()
                choice = data["choices"][0]
                message = choice.get("message") or {}
                parsed = message.get("parsed")
                if isinstance(parsed, dict):
                    self._write_runtime_status({"status": "running", "message": "", "retry": {}})
                    return parsed

                content = _chat_message_text(message)
                if not content:
                    finish_reason = choice.get("finish_reason")
                    if finish_reason == "length":
                        raise ValueError(
                            "Groq benchmark response hit finish_reason='length' before emitting JSON. "
                            "Increase max_completion_tokens or reduce prompt size."
                        )
                    raise ValueError("Groq benchmark response did not contain a parseable JSON payload.")
                try:
                    parsed_payload = _extract_json_object(content, "Groq")
                except ValueError as exc:
                    finish_reason = choice.get("finish_reason")
                    if finish_reason == "length":
                        raise ValueError(
                            "Groq benchmark response hit finish_reason='length' before emitting complete JSON. "
                            "Increase max_completion_tokens or reduce prompt size."
                        ) from exc
                    raise
                self._write_runtime_status({"status": "running", "message": "", "retry": {}})
                return parsed_payload
            except requests.HTTPError as exc:
                last_error = exc
                last_response = exc.response
                status_code = exc.response.status_code if exc.response is not None else None
                runtime_stage = str(self._runtime_context_payload().get("stage") or "").strip().lower()
                if _is_groq_key_blocked_error(exc.response):
                    key_pool.mark_blocked(key_index)
                    record_blocked_groq_key(
                        api_key,
                        reason=_groq_error_code(exc.response) or "blocked",
                        message=_groq_error_message(exc.response) or _format_http_error(exc, "Groq benchmark"),
                        status_code=status_code,
                        source="benchmarking",
                    )
                    key_pool.refresh_from_laravel(force=True)
                    if not key_pool.has_usable_key(ignore_cooldown=True):
                        raise RuntimeError(
                            "All configured Groq API keys are marked blocked. "
                            f"Last error: {_format_http_error(exc, 'Groq benchmark')}"
                        ) from exc
                    self._write_runtime_status(
                        {
                            "status": "running",
                            "stage": str(self._runtime_context_payload().get("stage") or "benchmark_request"),
                            "message": (
                                f"{key_pool.label(key_index)} was marked blocked after "
                                f"{_format_http_error(exc, 'Groq benchmark')}"
                            )[:500],
                            "retry": {},
                        }
                    )
                    print(
                        f"⚠️ {_format_http_error(exc, 'Groq benchmark')}. "
                        f"{key_pool.label(key_index)} was marked blocked and will not be used again in this run."
                    )
                    attempt -= 1
                    continue
                if runtime_stage == "extract_claims" and (
                    _is_groq_rate_limit_error(exc.response)
                    or _is_groq_json_validate_failed(exc.response)
                ):
                    _raise_terminal_error(exc, key_label=key_pool.label(key_index), response=exc.response)
                if status_code in {413, 429}:
                    _raise_terminal_error(exc, key_label=key_pool.label(key_index), response=exc.response)
                should_retry = (
                    _is_groq_rate_limit_error(exc.response)
                    or (status_code is not None and status_code >= 500)
                    or _is_groq_json_validate_failed(exc.response)
                )
                if not should_retry:
                    _raise_terminal_error(exc, key_label=key_pool.label(key_index), response=exc.response)
                if attempt >= effective_max_attempts or (
                    not GROQ_BENCHMARK_RETRY_FOREVER
                    and attempt >= GROQ_BENCHMARK_MAX_RETRIES
                ):
                    _raise_terminal_error(exc, key_label=key_pool.label(key_index), response=exc.response)
                retry_after_seconds = (
                    None
                    if _is_groq_json_validate_failed(exc.response)
                    else _groq_retry_after_seconds(exc.response)
                )
                if _is_groq_rate_limit_error(exc.response):
                    key_pool.mark_rate_limited(
                        key_index,
                        retry_after_seconds or GROQ_BENCHMARK_MAX_RETRY_WAIT_SECONDS,
                    )
                    alternate_wait_seconds = key_pool.next_available_delay(exclude_index=key_index)
                    if (
                        key_pool.size > 1
                        and alternate_wait_seconds is not None
                        and (retry_after_seconds is None or alternate_wait_seconds < retry_after_seconds)
                    ):
                        push_global_cooldown = False
                        use_alternate_wait = True
            except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt >= effective_max_attempts or (
                    not GROQ_BENCHMARK_RETRY_FOREVER
                    and attempt >= GROQ_BENCHMARK_MAX_RETRIES
                ):
                    _raise_terminal_error(exc, key_label=key_pool.label(key_index), response=last_response)
                runtime_stage = str(self._runtime_context_payload().get("stage") or "").strip().lower()
                if runtime_stage == "extract_claims" and isinstance(
                    exc,
                    (ValueError, KeyError, json.JSONDecodeError),
                ):
                    _raise_terminal_error(exc, key_label=key_pool.label(key_index), response=last_response)
                retry_after_seconds = None

            if use_alternate_wait and alternate_wait_seconds is not None and key_pool.size > 1:
                wait_seconds = max(0.0, alternate_wait_seconds)
            else:
                has_ready_key = key_pool.has_available_key()
                wait_seconds = max(
                    retry_after_seconds or 0.0,
                    GROQ_BENCHMARK_RETRY_BACKOFF_SECONDS * attempt,
                    (
                        0.0
                        if has_ready_key and key_pool.size > 1
                        else GROQ_BENCHMARK_MAX_RETRY_WAIT_SECONDS
                        if GROQ_BENCHMARK_RETRY_FOREVER
                        else 0.0
                    ),
                ) + random.uniform(0.0, GROQ_BENCHMARK_RETRY_JITTER_SECONDS)
                if retry_after_seconds is None:
                    wait_seconds = min(wait_seconds, GROQ_BENCHMARK_MAX_RETRY_WAIT_SECONDS)
            if push_global_cooldown and wait_seconds > 0:
                shared_openai_request_gate().push_cooldown(wait_seconds)
            error_text = (
                _format_http_error(last_error, "Groq benchmark")
                if isinstance(last_error, requests.HTTPError)
                else str(last_error)
            )
            _emit_retry_runtime_status(
                key_label=key_pool.label(key_index),
                wait_seconds=wait_seconds,
                error=last_error,
                response=last_response,
            )
            print(
                f"⚠️ Benchmark Groq request attempt {attempt}/"
                f"{effective_max_attempts if GROQ_BENCHMARK_RETRY_FOREVER else GROQ_BENCHMARK_MAX_RETRIES} failed: "
                f"{error_text}. {key_pool.label(key_index)} will rotate if another key is available. "
                f"Retrying in {wait_seconds:.1f}s."
            )
            if wait_seconds > 0:
                time.sleep(wait_seconds)

        raise BenchmarkRequestError(
            f"Benchmark Groq request failed after {effective_max_attempts} attempts: {last_error}"
        )
