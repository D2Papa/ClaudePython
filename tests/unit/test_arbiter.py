"""!
@brief safety.arbiter 단위 테스트 (SWR-013-4·021·022, SWD 3.6).
"""

from dataclasses import replace

import pytest

from child_lock.safety.arbiter import (
    accept_qm,
    decide,
    door_state,
    no_change_reason,
    pick,
    safety_candidates,
    validity,
)
from child_lock.types import (
    Candidate,
    Command,
    Door,
    DoorApproach,
    Group,
    Lock,
    Reason,
    Rule,
    State,
    Validity,
    Values,
    frozen,
)
from tests.unit.helpers import NORMAL_VALUES, doors, make_ctx

L, R = Door.LEFT, Door.RIGHT
PREV_LOCKED = frozen({L: Lock.LOCK, R: Lock.LOCK})
ISOFIX_LOCK = Candidate(Rule.ISOFIX, Lock.LOCK, Reason.ISOFIX_LOCK)
DRIVER_RELEASE = Candidate(Rule.DRIVER_COMMAND, Lock.RELEASE, Reason.DRIVER_COMMAND)
IGNITION = Candidate(Rule.IGNITION_OFF, Lock.RELEASE, Reason.IGNITION_OFF)
FIRE = Candidate(Rule.EMERGENCY_RELEASE, Lock.RELEASE, Reason.FIRE_RELEASE)


# --- QM 후보 검사 (간섭 방지, SWA 5장) ---


def test_accept_qm_rejects_safety_rule_from_qm():
    """! QM 쪽에서 ASIL B 규칙(CRASH) 후보가 오면 버린다."""
    forged = Candidate(Rule.CRASH, Lock.RELEASE, Reason.CRASH_RELEASE)
    assert accept_qm(forged, make_ctx(), L) is False


def test_accept_qm_rejects_rule_output_mismatch():
    """! 결함 후보 (ISOFIX, RELEASE)는 버린다 — 접근위험 잠금을 풀 수 없게 (REV-G2-001 지적 1)."""
    ctx = make_ctx(replace(NORMAL_VALUES, isofix=frozen({L: True, R: False})))
    assert accept_qm(Candidate(Rule.ISOFIX, Lock.RELEASE, Reason.ISOFIX_LOCK), ctx, L) is False


def test_accept_qm_allows_driver_command_in_either_direction_but_not_hold():
    """! 운전자 명령은 LOCK/RELEASE 모두 허용, 유지(None)는 불가."""
    assert accept_qm(DRIVER_RELEASE, make_ctx(), L) is True
    hold = Candidate(Rule.DRIVER_COMMAND, None, Reason.DRIVER_COMMAND)
    assert accept_qm(hold, make_ctx(), L) is False


def test_accept_qm_rejects_ignition_off_when_ignition_is_on():
    """! 조건 재확인: 시동 ON인데 IGNITION_OFF 후보 → 버린다."""
    assert accept_qm(IGNITION, make_ctx(), L) is False
    off = make_ctx(replace(NORMAL_VALUES, ignition_on=False))
    assert accept_qm(IGNITION, off, L) is True


def test_accept_qm_rejects_emergency_without_fresh_fire_or_overtemp():
    """! 조건 재확인: 화재·과온 FALSE 또는 G7 지연이면 버린다."""
    assert accept_qm(FIRE, make_ctx(), L) is False
    fire = replace(NORMAL_VALUES, fire=True)
    assert accept_qm(FIRE, make_ctx(fire), L) is True
    assert accept_qm(FIRE, make_ctx(fire, stale=frozenset({Group.G7})), L) is False
    overtemp = replace(NORMAL_VALUES, overtemp=True)
    assert accept_qm(FIRE, make_ctx(overtemp), L) is True


def test_accept_qm_rejects_isofix_when_unreceived_without_error():
    """! G8 미수신에서 ISOFIX 후보 → 예외 없이 버린다 (REV-G2-001 재검증 A)."""
    assert accept_qm(ISOFIX_LOCK, make_ctx(replace(NORMAL_VALUES, isofix=None)), L) is False
    assert accept_qm(ISOFIX_LOCK, make_ctx(), L) is False


def test_accept_qm_does_not_recheck_rules_below_safety_rules():
    """! 성인·자동 잠금은 우선순위로 막히므로 재확인 없이 수락."""
    adult = Candidate(Rule.ADULT_RELEASE, Lock.RELEASE, Reason.ADULT_RELEASE)
    assert accept_qm(adult, make_ctx(), L) is True


# --- ASIL B 후보 ---


def test_safety_candidates_stale_and_fault_hold_outputs():
    """! 지연 → INPUT_STALE, 고장 → SENSOR_FAULT (둘 다 출력 유지)."""
    ctx = make_ctx(replace(NORMAL_VALUES, sensor_fault=True), stale=frozenset({Group.G8}))
    assert safety_candidates(ctx, L) == [
        Candidate(Rule.INPUT_STALE, None, Reason.INPUT_STALE),
        Candidate(Rule.SENSOR_FAULT, None, Reason.SENSOR_FAULT),
    ]


def test_safety_candidates_include_crash_and_approach():
    """! 래치 → CRASH, 위험 → APPROACH_RISK."""
    ctx = make_ctx(replace(NORMAL_VALUES, risk=frozen({L: True, R: False})), crash_latched=True)
    assert [c.rule for c in safety_candidates(ctx, L)] == [Rule.CRASH, Rule.APPROACH_RISK]
    assert [c.rule for c in safety_candidates(ctx, R)] == [Rule.CRASH]


# --- NO_CHANGE 이유 (SWRS 3.2) ---


def test_no_change_reason_order():
    """! INPUT_INVALID → COMMAND_REJECTED → CRASH_PENDING → NO_CHANGE."""
    pending = replace(NORMAL_VALUES, crash_status="PENDING")
    assert no_change_reason(make_ctx(pending, input_rejected=True, command_rejected=True)) is (
        Reason.INPUT_INVALID
    )
    assert no_change_reason(make_ctx(pending, command_rejected=True)) is Reason.COMMAND_REJECTED
    assert no_change_reason(make_ctx(pending)) is Reason.CRASH_PENDING
    assert no_change_reason(make_ctx()) is Reason.NO_CHANGE


def test_pick_highest_priority_and_default_no_change():
    """! 규칙 값이 가장 작은 후보 선택, 후보 없으면 NO_CHANGE 유지."""
    assert pick([DRIVER_RELEASE, ISOFIX_LOCK], make_ctx()) == ISOFIX_LOCK
    assert pick([], make_ctx()) == Candidate(Rule.NO_CHANGE, None, Reason.NO_CHANGE)


# --- 상태·유효성 ---


@pytest.mark.parametrize(
    ("rule", "state"),
    [
        (Rule.IGNITION_OFF, State.OFF),
        (Rule.INPUT_STALE, State.DEGRADED),
        (Rule.SENSOR_FAULT, State.FAULT),
        (Rule.DRIVER_OVERRIDE, State.OVERRIDE),
        (Rule.APPROACH_RISK, State.NORMAL),
        (Rule.NO_CHANGE, State.NORMAL),
    ],
)
def test_door_state_mapping(rule, state):
    """! 규칙별 state (SWRS 3.1)."""
    assert door_state(rule, make_ctx()) is state


@pytest.mark.parametrize("rule", [Rule.CRASH, Rule.EMERGENCY_RELEASE])
def test_release_rules_do_not_hide_stale_or_fault(rule):
    """! 표시 규칙: 충돌·화재 해제 중에도 지연 → DEGRADED, 고장 → FAULT, 아니면 NORMAL."""
    faulty = replace(NORMAL_VALUES, sensor_fault=True)
    assert door_state(rule, make_ctx(faulty, stale=frozenset({Group.G1}))) is State.DEGRADED
    assert door_state(rule, make_ctx(faulty)) is State.FAULT
    assert door_state(rule, make_ctx()) is State.NORMAL


def test_validity_stale_over_invalid():
    """! 지연 → STALE (거절보다 우선), 거절 → INVALID, 아니면 VALID."""
    assert validity(make_ctx(stale=frozenset({Group.G2}), input_rejected=True)) is Validity.STALE
    assert validity(make_ctx(input_rejected=True)) is Validity.INVALID
    assert validity(make_ctx()) is Validity.VALID


# --- decide ---


def test_decide_holds_previous_output_when_no_rule():
    """! 활성 규칙 없음 → 직전 출력 유지, NORMAL, VALID."""
    d = decide(make_ctx(), {L: [], R: []}, PREV_LOCKED)
    assert (d.lock_left, d.lock_right, d.state) == (Lock.LOCK, Lock.LOCK, State.NORMAL)
    assert (d.priority_reason, d.reason_code) == ("NO_CHANGE", Reason.NO_CHANGE)
    assert d.input_validity is Validity.VALID
    assert d.warning_code is None


def test_decide_per_door_reasons_and_overall_highest_rule():
    """! 좌 ISOFIX(6), 우 운전자(11) → 전체 이유는 ISOFIX (SWRS 2.2)."""
    ctx = make_ctx(replace(NORMAL_VALUES, isofix=frozen({L: True, R: False})))
    d = decide(ctx, {L: [ISOFIX_LOCK], R: [DRIVER_RELEASE]}, PREV_LOCKED)
    assert (d.lock_left, d.lock_right) == (Lock.LOCK, Lock.RELEASE)
    assert (d.reason_left, d.reason_right) == (Reason.ISOFIX_LOCK, Reason.DRIVER_COMMAND)
    assert (d.priority_reason, d.reason_code) == ("ISOFIX", Reason.ISOFIX_LOCK)


def test_decide_isofix_check_uses_each_door():
    """! ISOFIX 재확인은 도어별: 좌만 TRUE면 우의 ISOFIX 후보는 버려진다."""
    ctx = make_ctx(replace(NORMAL_VALUES, isofix=frozen({L: True, R: False})))
    d = decide(ctx, {L: [ISOFIX_LOCK], R: [ISOFIX_LOCK]}, frozen(dict.fromkeys(Door, Lock.RELEASE)))
    assert (d.lock_left, d.lock_right) == (Lock.LOCK, Lock.RELEASE)


def test_decide_tie_uses_left_door_reason():
    """! 양쪽 같은 규칙이면 좌 도어 이유 (SWRS 2.2)."""
    risk = replace(NORMAL_VALUES, risk=frozen({L: True, R: True}))
    d = decide(make_ctx(risk, suppressed=frozenset({R})), {L: [], R: []}, PREV_LOCKED)
    assert d.reason_left is Reason.APPROACH_RISK_LOCK
    assert d.reason_right is Reason.APPROACH_RISK_SUPPRESSED
    assert d.reason_code is Reason.APPROACH_RISK_LOCK


def test_decide_state_precedence_override_over_normal():
    """! 좌 OVERRIDE, 우 NORMAL → OVERRIDE (OFF > DEGRADED > FAULT > OVERRIDE > NORMAL)."""
    risk = replace(NORMAL_VALUES, risk=frozen({L: True, R: False}))
    ctx = make_ctx(risk, doors=doors(DoorApproach(t0=0.0, override=True)))
    d = decide(ctx, {L: [], R: [ISOFIX_LOCK]}, PREV_LOCKED)
    assert d.state is State.OVERRIDE
    assert d.lock_left is Lock.RELEASE


def test_decide_sensor_fault_blocks_driver_command_and_warns():
    """! 센서 고장 → 운전자 명령 무시, 출력 유지, FAULT, W_SENSOR_FAULT (SWR-021)."""
    lock_all = Candidate(Rule.DRIVER_COMMAND, Lock.LOCK, Reason.DRIVER_COMMAND)
    prev = frozen({L: Lock.LOCK, R: Lock.RELEASE})
    d = decide(
        make_ctx(replace(NORMAL_VALUES, sensor_fault=True)), {L: [lock_all], R: [lock_all]}, prev
    )
    assert (d.lock_left, d.lock_right) == (Lock.LOCK, Lock.RELEASE)
    assert d.state is State.FAULT
    assert d.warning_code == "W_SENSOR_FAULT"


def test_decide_no_warning_from_stale_sensor_fault_value():
    """! G9 지연이면 오래된 sensor_fault로 경고하지 않는다."""
    ctx = make_ctx(replace(NORMAL_VALUES, sensor_fault=True), stale=frozenset({Group.G9}))
    assert decide(ctx, {L: [], R: []}, PREV_LOCKED).warning_code is None


def test_decide_unreceived_values_give_degraded_without_error():
    """! 모든 값 미수신 → 예외 없이 DEGRADED, INPUT_STALE (SWD 3.5)."""
    ctx = make_ctx(Values(), stale=frozenset(Group))
    d = decide(ctx, {L: [], R: []}, frozen(dict.fromkeys(Door, Lock.RELEASE)))
    assert d.state is State.DEGRADED
    assert d.reason_code is Reason.INPUT_STALE


def test_decide_command_reject_is_reported_when_nothing_else_applies():
    """! 명령 형식 오류만 있으면 COMMAND_REJECTED."""
    ctx = make_ctx(command_rejected=True, command=None)
    assert decide(ctx, {L: [], R: []}, PREV_LOCKED).reason_code is Reason.COMMAND_REJECTED


def test_decide_ignores_unused_command_object():
    """! 명령은 후보로만 반영된다: 후보가 없으면 출력 불변."""
    ctx = make_ctx(command=Command(doors=frozenset(Door), action=Lock.RELEASE, source="avn"))
    d = decide(ctx, {L: [], R: []}, PREV_LOCKED)
    assert (d.lock_left, d.lock_right) == (Lock.LOCK, Lock.LOCK)
