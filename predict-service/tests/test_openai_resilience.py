from __future__ import annotations

import json

from app.utils.report_explainer import update_report_explanation_status
from openai_rate_control import SharedOpenAIRequestGate


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
