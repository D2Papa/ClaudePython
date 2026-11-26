"""!
@brief Web 시뮬레이터 HTTP API (QM, SWR-014·015, SWD 3.10).
@details 시계 주입 원칙(SWA P-02)에 따라 평가 시각 now_s를 요청으로 받는다.
         입력은 판정 코어의 검증(SWR-013)을 그대로 거친다.
"""

import threading
from collections.abc import Callable, Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

from fastapi import Body, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from child_lock.engine import evaluate, initial_state
from child_lock.event_log import EventLog
from child_lock.safety.validation import is_number
from child_lock.types import INITIAL_DECISION, Decision

## 시뮬레이터 화면 파일
INDEX_HTML = Path(__file__).parent / "static" / "index.html"
## 직렬화 실패 응답 본문
SERIALIZATION_ERROR = {"error": "serialization_failed"}


def decision_json(decision: Decision) -> dict:
    """!
    @brief 상태 조회 응답 (SWR-014의 9개 필드).
    @param decision 결정
    @return JSON 직렬화용 사전
    """
    return asdict(decision)


class Simulator:
    """! @brief 앱 하나가 소유하는 판정 상태·이벤트 기록 (평가는 잠금으로 직렬화)."""

    def __init__(self) -> None:
        """! @brief 초기 상태로 시작한다 (재기동 = 새 인스턴스, SWR-012)."""
        self._state = initial_state()
        self._log = EventLog()
        self.last: Decision = INITIAL_DECISION
        self._lock = threading.Lock()

    def step(self, now_s: float, snapshot: Mapping | None) -> Decision:
        """!
        @brief 평가 주기 하나를 수행하고 기록한다.
        @param now_s 평가 시각
        @param snapshot 원시 스냅샷 (없으면 None)
        @return 결정
        """
        with self._lock:
            result = evaluate(self._state, now_s, snapshot)
            self._state = result.state
            self._log.append(result.decision, now_s)
            self.last = result.decision
            return self.last

    def events(self) -> list[dict]:
        """! @brief 이벤트 목록 (JSON용). @return 사전 목록"""
        return [asdict(e) for e in self._log.events()]


def _bad_request(payload: object) -> bool:
    """!
    @brief 요청 본문 형식 오류 여부 (now_s 유한 숫자, snapshot 객체 또는 null).
    @param payload 요청 본문
    @return 오류면 True
    """
    if not isinstance(payload, dict) or not is_number(payload.get("now_s")):
        return True
    return not isinstance(payload.get("snapshot"), dict | type(None))


def create_app(serialize: Callable[[Decision], dict] = decision_json) -> FastAPI:
    """!
    @brief 시뮬레이터 앱을 만든다.
    @param serialize 결정 직렬화 함수 (직렬화 실패 시험 주입용)
    @return FastAPI 앱
    """
    app = FastAPI(title="전자식 차일드락 시뮬레이터")
    sim = Simulator()

    def respond(decision: Decision) -> JSONResponse:
        """! @brief 결정 응답, 직렬화 실패는 HTTP 500. @param decision 결정 @return 응답"""
        try:
            return JSONResponse(serialize(decision))
        except (TypeError, ValueError):
            return JSONResponse(SERIALIZATION_ERROR, status_code=500)

    @app.post("/api/step")
    def step(payload: Annotated[object, Body()]) -> JSONResponse:
        """! @brief 평가 주기 수행. @param payload {"now_s", "snapshot"} @return 상태"""
        if _bad_request(payload):
            return JSONResponse({"error": "invalid_request"}, status_code=422)
        return respond(sim.step(payload["now_s"], payload.get("snapshot")))

    @app.get("/api/status")
    def status() -> JSONResponse:
        """! @brief 마지막 결정 조회. @return 상태"""
        return respond(sim.last)

    @app.get("/api/events")
    def events() -> list[dict]:
        """! @brief 최근 이벤트 조회 (최대 100건). @return 이벤트 목록"""
        return sim.events()

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        """! @brief 시뮬레이터 화면. @return HTML"""
        return INDEX_HTML.read_text(encoding="utf-8")

    return app


## uvicorn 실행용 앱 인스턴스
app = create_app()
