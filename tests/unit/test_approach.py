"""!
@brief safety.approach 단위 테스트 (SWR-005·006·009, SWD 3.4).
"""

from dataclasses import replace

import pytest

from child_lock.safety.approach import (
    approach_candidate,
    unlock_requested,
    update_door,
    update_doors,
)
from child_lock.types import (
    Candidate,
    Command,
    Door,
    DoorApproach,
    Group,
    Intake,
    Lock,
    Reason,
    Rule,
    frozen,
)
from tests.unit.helpers import NORMAL_VALUES, doors, make_ctx

BOTH = frozenset(Door)
LEFT = frozenset({Door.LEFT})
UNLOCK_ALL = Command(doors=BOTH, action=Lock.RELEASE, source="avn")
LOCK_ALL = Command(doors=BOTH, action=Lock.LOCK, source="avn")
SUPPRESSED_AT_0 = DoorApproach(t0=0.0)
OVERRIDDEN = DoorApproach(t0=0.0, override=True)


def test_unlock_requested_only_for_unlock_covering_door():
    """! unlock이고 해당 도어를 포함할 때만 해제 요청."""
    assert unlock_requested(UNLOCK_ALL, Door.LEFT) is True
    assert unlock_requested(LOCK_ALL, Door.LEFT) is False
    right_only = Command(doors=frozenset({Door.RIGHT}), action=Lock.RELEASE, source="voice")
    assert unlock_requested(right_only, Door.LEFT) is False
    assert unlock_requested(None, Door.LEFT) is False


# update_door 판정표 (SWD 3.4): 행마다 시험 하나
@pytest.mark.parametrize("risk", [False, None])
def test_row1_no_risk_resets_door(risk):
    """! 위험 FALSE/미수신 → t0·override 초기화, 억제 없음."""
    assert update_door(OVERRIDDEN, risk, 0.0, True, 1.0) == (DoorApproach(), False)


def test_row2_moving_without_unlock_resets():
    """! 주행 중 → override·t0 초기화 (SWR-006-5)."""
    assert update_door(OVERRIDDEN, True, 3.0, False, 1.0) == (DoorApproach(), False)


def test_row3_moving_unlock_is_suppressed_without_t0():
    """! 주행 중 해제 요청은 억제하되 t0를 기록하지 않는다."""
    assert update_door(DoorApproach(), True, 3.0, True, 1.0) == (DoorApproach(), True)


def test_row4_existing_override_is_kept_while_stopped():
    """! 정지 중 override 유지."""
    assert update_door(OVERRIDDEN, True, 2.9, False, 1.0) == (OVERRIDDEN, False)


def test_row5_risk_without_unlock_keeps_t0():
    """! 위험 중 요청 없음 → t0 유지, 억제 없음."""
    assert update_door(SUPPRESSED_AT_0, True, 0.0, False, 5.0) == (SUPPRESSED_AT_0, False)


def test_row6_first_unlock_is_suppressed_and_sets_t0():
    """! 첫 해제 요청 → 억제, t0 = 명령 시각."""
    assert update_door(DoorApproach(), True, 0.0, True, 2.5) == (DoorApproach(t0=2.5), True)


def test_row6_unlock_after_10_1s_restarts_suppression():
    """! t0 후 10.1 s 재입력 → 새 억제, t0 갱신 (경계)."""
    assert update_door(SUPPRESSED_AT_0, True, 0.0, True, 10.1) == (DoorApproach(t0=10.1), True)


def test_row7_unlock_within_10s_establishes_override():
    """! t0 후 정확히 10.0 s 재입력 → override (이하 포함, 경계)."""
    assert update_door(SUPPRESSED_AT_0, True, 2.9, True, 10.0) == (OVERRIDDEN, False)


def test_row7_float_error_at_10s_boundary_still_overrides():
    """! 10.3 - 0.3 = 10.000000000000002여도 10.0 s로 판정."""
    assert update_door(DoorApproach(t0=0.3), True, 0.0, True, 10.3)[0].override is True


def make_intake(values=NORMAL_VALUES, command=None, ts=1.0):
    """! update_doors용 Intake."""
    return Intake(values=values, group_ts=frozen({}), last_ts=ts, command=command, command_ts=ts)


def test_update_doors_resets_all_on_ignition_off():
    """! 시동 OFF → 모든 도어 초기화."""
    result = update_doors(doors(OVERRIDDEN, OVERRIDDEN), make_intake(), frozenset(), True)
    assert result == (doors(), frozenset())


def test_update_doors_resets_all_while_stale():
    """! 입력 지연 주기에는 override 초기화, 새 판정 없음 (A-21)."""
    risky = replace(NORMAL_VALUES, risk=frozen({Door.LEFT: True, Door.RIGHT: True}))
    result = update_doors(
        doors(OVERRIDDEN), make_intake(risky, UNLOCK_ALL), frozenset({Group.G8}), False
    )
    assert result == (doors(), frozenset())


def test_update_doors_resets_all_on_sensor_fault():
    """! 센서 고장 주기에는 override 초기화 (A-21)."""
    faulty = replace(NORMAL_VALUES, sensor_fault=True)
    assert update_doors(doors(OVERRIDDEN), make_intake(faulty), frozenset(), False) == (
        doors(),
        frozenset(),
    )


def test_update_doors_handles_each_door_independently():
    """! 좌 위험만 TRUE에서 ALL unlock → 좌만 억제·t0 (SWR-009)."""
    left_risk = replace(NORMAL_VALUES, risk=frozen({Door.LEFT: True, Door.RIGHT: False}))
    new_doors, suppressed = update_doors(
        doors(), make_intake(left_risk, UNLOCK_ALL, ts=4.0), frozenset(), False
    )
    assert new_doors == doors(DoorApproach(t0=4.0), DoorApproach())
    assert suppressed == LEFT


def test_update_doors_with_unreceived_risk_group_changes_nothing():
    """! G3 미수신(risk None)이면 위험 없음으로 처리, 예외 없음."""
    no_risk = replace(NORMAL_VALUES, risk=None)
    assert update_doors(doors(), make_intake(no_risk, UNLOCK_ALL), frozenset(), False) == (
        doors(),
        frozenset(),
    )


def test_candidate_none_without_risk():
    """! 위험 FALSE 또는 미수신이면 후보 없음."""
    assert approach_candidate(make_ctx(), Door.LEFT) is None
    assert approach_candidate(make_ctx(replace(NORMAL_VALUES, risk=None)), Door.LEFT) is None


RISK_LEFT = replace(NORMAL_VALUES, risk=frozen({Door.LEFT: True, Door.RIGHT: False}))


def test_candidate_lock_with_risk():
    """! 위험 TRUE → APPROACH_RISK LOCK."""
    assert approach_candidate(make_ctx(RISK_LEFT), Door.LEFT) == Candidate(
        Rule.APPROACH_RISK, Lock.LOCK, Reason.APPROACH_RISK_LOCK
    )


def test_candidate_reports_suppression():
    """! 이번 주기 억제 → APPROACH_RISK_SUPPRESSED (SWR-005 원인 기록)."""
    ctx = make_ctx(RISK_LEFT, suppressed=LEFT)
    assert approach_candidate(ctx, Door.LEFT).reason is Reason.APPROACH_RISK_SUPPRESSED


def test_candidate_override_releases():
    """! override 성립 → DRIVER_OVERRIDE RELEASE."""
    ctx = make_ctx(RISK_LEFT, doors=doors(OVERRIDDEN))
    assert approach_candidate(ctx, Door.LEFT) == Candidate(
        Rule.DRIVER_OVERRIDE, Lock.RELEASE, Reason.DRIVER_OVERRIDE
    )
