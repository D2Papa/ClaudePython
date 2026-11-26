"""!
@brief child_lock.types 단위 테스트 (SWD 2장).
"""

from child_lock.types import INITIAL_DECISION, Lock, Reason, Rule, State, Validity


def test_rule_order_matches_swrs_priority_table():
    """! SWRS 3.1 순위 순서 (7a는 7보다 앞). 순서가 바뀌면 중재 결과가 바뀐다."""
    assert sorted(Rule) == [
        Rule.IGNITION_OFF,
        Rule.CRASH,
        Rule.EMERGENCY_RELEASE,
        Rule.INPUT_STALE,
        Rule.SENSOR_FAULT,
        Rule.ISOFIX,
        Rule.DRIVER_OVERRIDE,
        Rule.APPROACH_RISK,
        Rule.ADULT_RELEASE,
        Rule.AUTO_LOCK,
        Rule.DRIVER_COMMAND,
        Rule.NO_CHANGE,
    ]


def test_initial_decision_matches_swrs_2_2():
    """! 첫 평가 전 결정 값 (SWRS 2.2, CR-001)."""
    d = INITIAL_DECISION
    assert (d.lock_left, d.lock_right) == (Lock.RELEASE, Lock.RELEASE)
    assert d.state is State.OFF
    assert d.priority_reason == "NO_CHANGE"
    assert (d.reason_code, d.reason_left, d.reason_right) == (Reason.NO_CHANGE,) * 3
    assert d.input_validity is Validity.STALE
    assert d.warning_code is None
