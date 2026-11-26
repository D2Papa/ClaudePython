"""!
@brief event_log 단위 테스트 (SWR-010·011·012, SWD 3.8).
"""

from dataclasses import fields, replace

from child_lock.event_log import Event, EventLog
from child_lock.types import INITIAL_DECISION, Lock, Reason


def test_event_ids_start_at_one_and_increase():
    """! event_id는 1부터 1씩 증가."""
    log = EventLog()
    assert [log.append(INITIAL_DECISION, t).event_id for t in (0.0, 0.05, 0.1)] == [1, 2, 3]


def test_keeps_only_latest_100_in_order():
    """! 101건 기록 후 event_id 2~101의 100건, 오름차순 (SWR-010 수용기준)."""
    log = EventLog()
    for i in range(101):
        log.append(INITIAL_DECISION, i * 0.05)
    assert [e.event_id for e in log.events()] == list(range(2, 102))


def test_event_has_exactly_the_allowed_fields():
    """! 이벤트 필드는 SWR-011의 11개뿐 (영상·음성·개인 식별자 없음)."""
    assert [f.name for f in fields(Event)] == [
        "event_id",
        "now_s",
        "lock_left",
        "lock_right",
        "state",
        "priority_reason",
        "reason_code",
        "reason_left",
        "reason_right",
        "input_validity",
        "warning_code",
    ]


def test_event_copies_decision_values_and_time():
    """! 결정 값과 평가 시각을 그대로 담는다."""
    decision = replace(INITIAL_DECISION, lock_left=Lock.LOCK, reason_left=Reason.ISOFIX_LOCK)
    event = EventLog().append(decision, 1.25)
    assert (event.now_s, event.lock_left, event.reason_left) == (
        1.25,
        Lock.LOCK,
        Reason.ISOFIX_LOCK,
    )


def test_new_log_is_empty():
    """! 새 저장소(재기동)는 0건 (SWR-012)."""
    assert EventLog().events() == []
