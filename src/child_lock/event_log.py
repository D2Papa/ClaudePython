"""!
@brief 최근 결정 이벤트 기록 (QM, SWR-010·011·012, SWD 3.8).
@details 프로세스 메모리에만 보존하며 파일·DB에 쓰지 않는다 (SWR-012).
         입력 스냅샷을 받지 않으므로 허용 외 필드가 섞일 수 없다 (SWR-011).
"""

from collections import deque
from dataclasses import dataclass

from child_lock.types import EVENT_CAPACITY, Decision, Lock, Reason, State, Validity


@dataclass(frozen=True)
class Event:
    """! @brief 기록된 결정 하나 (SWR-011의 11개 필드만)."""

    event_id: int
    now_s: float
    lock_left: Lock
    lock_right: Lock
    state: State
    priority_reason: str
    reason_code: Reason
    reason_left: Reason
    reason_right: Reason
    input_validity: Validity
    warning_code: str | None


class EventLog:
    """! @brief 최신 결정을 정해진 건수만 보존하는 링 버퍼."""

    def __init__(self, capacity: int = EVENT_CAPACITY) -> None:
        """!
        @brief 빈 기록을 만든다.
        @param capacity 보존 건수 (기본 100)
        """
        self._events: deque[Event] = deque(maxlen=capacity)
        self._next_id = 1

    def append(self, decision: Decision, now_s: float) -> Event:
        """!
        @brief 결정을 이벤트로 기록한다. 가장 오래된 것은 자동으로 밀려난다.
        @param decision 이번 주기 결정
        @param now_s 평가 시각
        @return 기록된 이벤트
        """
        # 필드를 명시적으로 복사해 허용 필드만 담는다
        event = Event(
            event_id=self._next_id,
            now_s=now_s,
            lock_left=decision.lock_left,
            lock_right=decision.lock_right,
            state=decision.state,
            priority_reason=decision.priority_reason,
            reason_code=decision.reason_code,
            reason_left=decision.reason_left,
            reason_right=decision.reason_right,
            input_validity=decision.input_validity,
            warning_code=decision.warning_code,
        )
        self._events.append(event)
        self._next_id += 1
        return event

    def events(self) -> list[Event]:
        """!
        @brief 보존 중인 이벤트를 오래된 것부터 돌려준다.
        @return 이벤트 목록
        """
        return list(self._events)
