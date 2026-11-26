"""!
@brief SW 검증 시험 실행기 (SWE.6, G4).
@details docs/06_system_test/scenarios.json의 시나리오를 Web API(PC/SIL)로 실행해
         기대값과 비교한다. 기대값은 시험 명세(요구사항)에서 도출하며, 구현에 맞춰 고치지 않는다.

시나리오 형식:
    {"tc_id": "STC-F-001", "steps": [
        {"now_s": 1.0,                       # 평가 시각 (필수)
         "snapshot": {...} | null,           # 기본 스냅샷에 덮어쓸 필드, null = 입력 없음
         "remove": ["gear"],                 # (선택) 기본 스냅샷에서 뺄 필드
         "raw": {...},                       # (선택) 기본값 없이 그대로 보낼 스냅샷
         "body": "...",                      # (선택) 요청 본문 문자열 그대로 (요청 오류 시험)
         "expect": {"lock_left": "LOCK", ...},   # 상태 응답 필드 부분 일치
         "expect_http": 422,                 # (선택) 기대 HTTP 상태 (기본 200)
         "expect_events": {"count": 100, "first_id": 2, "last_id": 101}}  # (선택)
    ]}
기본 스냅샷의 source_timestamp_s는 그 단계의 now_s다 (snapshot에서 덮어쓸 수 있음).
"""

import json
from pathlib import Path

import pytest

from child_lock.web.app import create_app
from tests.unit.test_validation import VALID
from tests.unit.test_web_app import AsgiClient

## 시나리오 파일
SCENARIOS = Path(__file__).resolve().parents[2] / "docs" / "06_system_test" / "scenarios.json"


def load_scenarios() -> list[dict]:
    """! 시나리오 목록 (파일이 없으면 빈 목록)."""
    if not SCENARIOS.exists():
        return []
    return json.loads(SCENARIOS.read_text(encoding="utf-8"))


def build_snapshot(step: dict) -> dict | None:
    """! 단계 정의로 요청 스냅샷을 만든다."""
    if "raw" in step:
        return step["raw"]
    if step.get("snapshot", {}) is None:
        return None
    raw = dict(VALID, source_timestamp_s=step["now_s"])
    raw.update(step.get("snapshot") or {})
    for name in step.get("remove", []):
        raw.pop(name, None)
    return raw


def send(client: AsgiClient, step: dict):
    """! 단계 하나를 API로 보낸다."""
    if "body" in step:
        return client.post(
            "/api/step", content=step["body"], headers={"content-type": "application/json"}
        )
    return client.post("/api/step", json={"now_s": step["now_s"], "snapshot": build_snapshot(step)})


def check_events(client: AsgiClient, expected: dict, where: str) -> None:
    """! 이벤트 기록 기대값 확인."""
    events = client.get("/api/events").json()
    actual = {
        "count": len(events),
        "first_id": events[0]["event_id"] if events else None,
        "last_id": events[-1]["event_id"] if events else None,
    }
    for key, value in expected.items():
        assert actual[key] == value, f"{where} events.{key}: 기대 {value}, 실제 {actual[key]}"


@pytest.mark.parametrize("scenario", load_scenarios(), ids=lambda s: s["tc_id"])
def test_scenario(scenario):
    """! 시나리오 하나를 새 앱(초기 상태)에서 실행한다."""
    client = AsgiClient(create_app())
    for index, step in enumerate(scenario["steps"], start=1):
        where = f"{scenario['tc_id']} 단계 {index} (now_s={step.get('now_s')})"
        response = send(client, step)
        assert response.status_code == step.get("expect_http", 200), where
        body = response.json()
        for field, value in step.get("expect", {}).items():
            assert body.get(field) == value, (
                f"{where} {field}: 기대 {value}, 실제 {body.get(field)}"
            )
        if "expect_events" in step:
            check_events(client, step["expect_events"], where)
