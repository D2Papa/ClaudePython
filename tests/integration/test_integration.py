"""!
@brief SW 통합 시험 (SWE.5): engine + event_log + replay + web을 인터페이스로 연결해 검증.
@details 단위 시험이 유닛 내부 논리를 보았다면, 여기서는 컴포넌트 사이 데이터 전달과
         SWA 3장 인터페이스 계약을 확인한다.
"""

import builtins

from child_lock.replay import digest, replay
from child_lock.web.app import create_app
from tests.unit.test_validation import snap
from tests.unit.test_web_app import AsgiClient

## 주기 50 ms
PERIOD = 0.05


def step(client, now_s, **changes):
    """! 시각 now_s의 정상 스냅샷(변경 포함)으로 한 주기 평가."""
    raw = snap(source_timestamp_s=now_s, **changes)
    return client.post("/api/step", json={"now_s": now_s, "snapshot": raw}).json()


def test_crash_release_flows_from_http_input_to_event_log():
    """! HTTP 입력 → 판정 코어 → 상태 응답 → 이벤트 기록까지 충돌 해제가 일관되게 전달된다."""
    client = AsgiClient(create_app())
    step(client, 1.0, command={"side": "all", "action": "lock", "source": "avn"})
    status = step(client, 1.05, crash_status="CONFIRMED")
    events = client.get("/api/events").json()
    assert (status["lock_left"], status["lock_right"], status["reason_code"]) == (
        "RELEASE",
        "RELEASE",
        "CRASH_RELEASE",
    )
    assert [e["reason_code"] for e in events] == ["DRIVER_COMMAND", "CRASH_RELEASE"]


def test_missing_snapshots_degrade_state_over_http():
    """! 입력이 끊기면 0.200 s까지는 NORMAL, 0.250 s에 DEGRADED (SWR-013, HTTP 경로)."""
    client = AsgiClient(create_app())
    step(client, 1.0)
    states = [
        client.post("/api/step", json={"now_s": 1.0 + k * PERIOD}).json()["state"]
        for k in (1, 2, 3, 4, 5)
    ]
    assert states == ["NORMAL", "NORMAL", "NORMAL", "NORMAL", "DEGRADED"]


def test_event_log_keeps_latest_100_through_api():
    """! API로 101주기 평가 → 이벤트 100건(id 2~101) (SWR-010, 통합 경로)."""
    client = AsgiClient(create_app())
    for k in range(101):
        client.post("/api/step", json={"now_s": k * PERIOD})
    ids = [e["event_id"] for e in client.get("/api/events").json()]
    assert ids == list(range(2, 102))


def test_restart_loses_events_and_writes_no_files(monkeypatch):
    """! 실행 중 파일 쓰기 없음, 재기동(새 앱) 후 이벤트 0건 (SWR-012)."""
    writes = []
    real_open = builtins.open

    def spy_open(file, mode="r", *args, **kwargs):
        """! 쓰기 모드로 여는 파일을 기록한다."""
        if any(m in mode for m in "wax+"):
            writes.append(file)
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy_open)
    client = AsgiClient(create_app())
    for k in range(5):
        step(client, 1.0 + k * PERIOD)
    assert len(client.get("/api/events").json()) == 5
    assert writes == []
    assert AsgiClient(create_app()).get("/api/events").json() == []


def test_replay_1000_times_gives_identical_digest():
    """! 고정 시계로 같은 벡터를 1,000회 재생 → 해시 모두 동일 (SWR-016 수용기준)."""
    vector = [
        {"now_s": 1.0, "snapshot": snap()},
        {
            "now_s": 1.05,
            "snapshot": snap(
                source_timestamp_s=1.05,
                rear_left_approach_risk=True,
                command={"side": "left", "action": "unlock", "source": "voice"},
            ),
        },
        {"now_s": 1.1, "snapshot": snap(source_timestamp_s=1.1, vehicle_speed_kph=12.0)},
        {"now_s": 1.4, "snapshot": None},
    ]
    digests = {digest(replay(vector)) for _ in range(1000)}
    assert len(digests) == 1
