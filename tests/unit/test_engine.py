"""!
@brief engine 단위 테스트 (SWR-016·022, SWD 3.7).
@details 각 유닛은 개별 시험에서 검증했으므로 여기서는 조립 순서와 상태 전달을 확인한다.
"""

from child_lock.engine import evaluate, initial_state
from child_lock.types import Door, Lock, Reason, State, Validity
from tests.unit.test_validation import snap


def test_first_cycle_without_snapshot_is_degraded_without_error():
    """! 초기 상태에서 스냅샷 없이 평가 → 예외 없이 DEGRADED, 양쪽 RELEASE."""
    d = evaluate(initial_state(), 0.0, None).decision
    assert d.state is State.DEGRADED
    assert (d.lock_left, d.lock_right) == (Lock.RELEASE, Lock.RELEASE)
    assert d.input_validity is Validity.STALE


def test_valid_snapshot_gives_normal_and_updates_state():
    """! 정상 스냅샷 → NORMAL, VALID, 다음 상태에 시각 반영."""
    result = evaluate(initial_state(), 1.0, snap())
    assert result.decision.state is State.NORMAL
    assert result.decision.input_validity is Validity.VALID
    assert result.state.last_ts == 1.0


def test_driver_command_output_is_carried_to_next_cycle():
    """! ALL LOCK 후 다음 주기(명령 없음)에도 LOCK 유지 — 출력이 상태로 전달된다."""
    first = evaluate(
        initial_state(), 1.0, snap(command={"side": "all", "action": "lock", "source": "avn"})
    )
    assert first.state.outputs == {Door.LEFT: Lock.LOCK, Door.RIGHT: Lock.LOCK}
    second = evaluate(first.state, 1.05, snap(source_timestamp_s=1.05))
    assert (second.decision.lock_left, second.decision.lock_right) == (Lock.LOCK, Lock.LOCK)


def test_crash_latch_survives_return_to_none():
    """! CONFIRMED 후 NONE + LOCK 명령이 와도 RELEASE 유지 (SWR-007)."""
    s = evaluate(initial_state(), 1.0, snap(crash_status="CONFIRMED")).state
    d = evaluate(
        s,
        1.05,
        snap(source_timestamp_s=1.05, command={"side": "all", "action": "lock", "source": "avn"}),
    ).decision
    assert (d.lock_left, d.lock_right) == (Lock.RELEASE, Lock.RELEASE)
    assert d.reason_code is Reason.CRASH_RELEASE


def test_suppression_is_recorded_through_the_engine():
    """! 좌 위험 + left unlock → 좌 LOCK, SUPPRESSED, 상태에 t0 기록."""
    result = evaluate(
        initial_state(),
        1.0,
        snap(
            rear_left_approach_risk=True,
            command={"side": "left", "action": "unlock", "source": "physical_button"},
        ),
    )
    assert result.decision.reason_left is Reason.APPROACH_RISK_SUPPRESSED
    assert result.state.doors[Door.LEFT].t0 == 1.0
