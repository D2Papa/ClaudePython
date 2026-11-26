"""!
@brief web.app 단위 테스트 (SWR-014·015, SWD 3.10).
"""

import asyncio

import httpx
import pytest

from child_lock.web.app import create_app
from tests.unit.test_validation import snap


class AsgiClient:
    """! 시험용 동기 클라이언트: httpx ASGI 전송으로 앱을 직접 호출한다.

    starlette.testclient는 설치 버전에서 사용 중단 경고를 내므로(-W error로 실패) 쓰지 않는다.
    """

    def __init__(self, app):
        """! 앱을 감싼다."""
        self.app = app

    def request(self, method, url, **kwargs):
        """! 요청 하나를 보내고 응답을 돌려준다."""

        async def send():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(send())

    def get(self, url):
        """! GET 요청."""
        return self.request("GET", url)

    def post(self, url, **kwargs):
        """! POST 요청."""
        return self.request("POST", url, **kwargs)


## SWR-014 상태 응답 필드
STATUS_FIELDS = {
    "lock_left",
    "lock_right",
    "state",
    "input_validity",
    "priority_reason",
    "reason_code",
    "reason_left",
    "reason_right",
    "warning_code",
}


@pytest.fixture
def client():
    """! 새 앱(새 프로세스와 같은 초기 상태)의 시험 클라이언트."""
    return AsgiClient(create_app())


def test_status_before_any_step_is_initial_decision(client):
    """! 평가 전 상태 = SWRS 2.2 초기 결정."""
    body = client.get("/api/status").json()
    assert set(body) == STATUS_FIELDS
    assert (body["lock_left"], body["state"], body["input_validity"]) == ("RELEASE", "OFF", "STALE")
    assert body["warning_code"] is None


def test_step_evaluates_and_status_reflects_decision(client):
    """! 좌 접근위험 주입 → 좌 LOCK, APPROACH_RISK_LOCK (SWR-015 수용기준)."""
    response = client.post(
        "/api/step", json={"now_s": 1.0, "snapshot": snap(rear_left_approach_risk=True)}
    )
    assert response.status_code == 200
    assert response.json()["lock_left"] == "LOCK"
    assert response.json()["reason_left"] == "APPROACH_RISK_LOCK"
    assert client.get("/api/status").json() == response.json()


def test_step_without_snapshot_is_allowed(client):
    """! snapshot 생략·null → 입력 없는 주기로 평가."""
    assert client.post("/api/step", json={"now_s": 0.0}).json()["state"] == "DEGRADED"


@pytest.mark.parametrize(
    "body",
    [
        '{"now_s": "1.0"}',
        '{"now_s": true}',
        '{"now_s": NaN}',
        '{"snapshot": null}',
        '{"now_s": 1.0, "snapshot": [1, 2]}',
        "[1]",
    ],
)
def test_step_rejects_bad_request_body_with_422(client, body):
    """! now_s가 유한한 숫자가 아니거나 snapshot이 객체가 아니면 422, 평가하지 않음."""
    response = client.post("/api/step", content=body, headers={"content-type": "application/json"})
    assert response.status_code == 422
    assert client.get("/api/events").json() == []


def test_events_are_recorded_per_step(client):
    """! 평가마다 이벤트 1건, 시각 포함."""
    client.post("/api/step", json={"now_s": 1.0, "snapshot": snap()})
    client.post("/api/step", json={"now_s": 1.05})
    events = client.get("/api/events").json()
    assert [(e["event_id"], e["now_s"]) for e in events] == [(1, 1.0), (2, 1.05)]


def test_serialization_failure_returns_http_500():
    """! 직렬화 실패 주입 → HTTP 500 (SWR-014, OEM-IF-006)."""

    def broken(_decision):
        """! 직렬화할 수 없는 값을 돌려주는 시험용 직렬화 함수."""
        return {"bad": object()}

    response = AsgiClient(create_app(serialize=broken)).get("/api/status")
    assert response.status_code == 500
    assert response.json() == {"error": "serialization_failed"}


def test_index_page_is_served(client):
    """! 시뮬레이터 화면 제공."""
    response = client.get("/")
    assert response.status_code == 200
    assert "차일드락 시뮬레이터" in response.text
