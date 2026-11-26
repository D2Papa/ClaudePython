"""!
@brief safety.validation 단위 테스트 (SWR-013-1~3, SWD 3.1).
"""

import pytest

from child_lock.engine import initial_state
from child_lock.safety.validation import (
    check_timestamp,
    intake,
    is_number,
    parse_command,
    parse_group,
)
from child_lock.types import Door, Group, Lock

## 모든 그룹이 유효한 스냅샷 (시각 1.0 s)
VALID = {
    "source_timestamp_s": 1.0,
    "vehicle_speed_kph": 0.0,
    "gear": "P",
    "crash_status": "NONE",
    "rear_left_approach_risk": False,
    "rear_right_approach_risk": False,
    "fire_detected": False,
    "overtemperature_detected": False,
    "adult_present": False,
    "isofix_left": False,
    "isofix_right": False,
    "ignition_on": True,
    "sensor_fault": False,
}


def snap(**changes):
    """! VALID를 복사해 일부 필드를 바꾼 스냅샷."""
    raw = dict(VALID)
    raw.update(changes)
    return raw


@pytest.mark.parametrize(
    "value", [True, False, "3.0", None, float("nan"), float("inf"), float("-inf")]
)
def test_is_number_rejects_bool_text_none_and_non_finite(value):
    """! 불리언(int 하위형), 문자열, None, NaN, ±inf는 숫자가 아니다."""
    assert is_number(value) is False


@pytest.mark.parametrize("value", [0, 0.0, 300, 300.0, 12.5])
def test_is_number_accepts_finite_int_and_float(value):
    """! 유한한 int/float는 숫자다."""
    assert is_number(value) is True


def test_timestamp_missing_negative_nan_or_regressing_is_rejected():
    """! 누락·음수·NaN·직전보다 이른 타임스탬프는 거절 (A-16)."""
    assert check_timestamp({}, None) is None
    assert check_timestamp({"source_timestamp_s": -0.1}, None) is None
    assert check_timestamp({"source_timestamp_s": float("nan")}, None) is None
    assert check_timestamp({"source_timestamp_s": 0.9}, 1.0) is None


def test_timestamp_equal_to_previous_is_accepted():
    """! 직전과 같은 시각은 역행이 아니다 (경계)."""
    assert check_timestamp({"source_timestamp_s": 1.0}, 1.0) == 1.0


@pytest.mark.parametrize("speed", [-0.1, 300.1, True, "10"])
def test_g1_rejects_out_of_range_or_non_number_speed(speed):
    """! 차속 범위 0.0~300.0 밖이거나 숫자가 아니면 G1 거절."""
    assert parse_group(Group.G1, snap(vehicle_speed_kph=speed)) is None


@pytest.mark.parametrize("speed", [0.0, 300.0])
def test_g1_accepts_speed_range_limits(speed):
    """! 범위 양 끝은 포함."""
    assert parse_group(Group.G1, snap(vehicle_speed_kph=speed))["vehicle_speed_kph"] == speed


def test_g1_rejects_unknown_gear_and_missing_field():
    """! 기어 미등록 값, 필드 누락은 위반."""
    assert parse_group(Group.G1, snap(gear="X")) is None
    raw = snap()
    del raw["gear"]
    assert parse_group(Group.G1, raw) is None


def test_g2_rejects_undefined_crash_status():
    """! NONE/PENDING/CONFIRMED 외 값은 거절."""
    assert parse_group(Group.G2, snap(crash_status="MAYBE")) is None


def test_boolean_group_rejects_integer_one():
    """! 불리언 필드에 1을 넣으면 거절 (bool과 int 혼동 결함 검출)."""
    assert parse_group(Group.G3, snap(rear_left_approach_risk=1)) is None


def test_command_absent_is_not_rejected():
    """! 명령 키가 없으면 명령 없음, 거절 아님."""
    assert parse_command(snap()) == (None, False)


@pytest.mark.parametrize(
    "command",
    [
        {"side": "left", "action": "unlock"},
        {"side": "middle", "action": "unlock", "source": "avn"},
        {"side": "left", "action": "open", "source": "avn"},
        {"side": "left", "action": "unlock", "source": "smart_watch"},
        "left unlock",
    ],
)
def test_malformed_command_is_rejected(command):
    """! 필드 누락, 미등록 side/action/source, 객체 아님 → 명령만 거절."""
    assert parse_command(snap(command=command)) == (None, True)


def test_all_side_unlock_command_targets_both_doors_with_release():
    """! side=all은 양쪽 도어, unlock은 RELEASE."""
    command, rejected = parse_command(
        snap(command={"side": "all", "action": "unlock", "source": "mobile_app"})
    )
    assert rejected is False
    assert command.doors == frozenset({Door.LEFT, Door.RIGHT})
    assert command.action is Lock.RELEASE


def test_intake_without_snapshot_keeps_state():
    """! 스냅샷이 없는 주기는 값·시각 불변, 명령 없음."""
    state = initial_state()
    result = intake(state, None)
    assert (result.values, result.group_ts, result.last_ts) == (
        state.values,
        state.group_ts,
        state.last_ts,
    )
    assert (result.command, result.input_rejected) == (None, False)


def test_intake_bad_timestamp_rejects_whole_snapshot_and_discards_command():
    """! 타임스탬프 불량 → 전체 거절, 명령도 폐기 (SWD 3.1)."""
    raw = snap(source_timestamp_s="1.0", command={"side": "all", "action": "lock", "source": "avn"})
    result = intake(initial_state(), raw)
    assert result.input_rejected is True
    assert result.command is None
    assert result.command_rejected is False
    assert result.group_ts == {}


def test_intake_rejects_only_invalid_group_and_keeps_crash_confirmed():
    """! G1 범위 오류 + G2 CONFIRMED → G1만 거절, 충돌 값은 수락 (SWR-013 수용기준, A-19)."""
    result = intake(initial_state(), snap(vehicle_speed_kph=300.1, crash_status="CONFIRMED"))
    assert result.input_rejected is True
    assert result.values.crash_status == "CONFIRMED"
    assert result.values.speed_kph is None
    assert Group.G1 not in result.group_ts
    assert result.group_ts[Group.G2] == 1.0


def test_intake_accepts_all_groups_and_records_command_time():
    """! 정상 스냅샷: 모든 그룹 수락, 도어별 값 매핑, 명령 시각 = 스냅샷 시각."""
    raw = snap(
        rear_right_approach_risk=True,
        isofix_left=True,
        command={"side": "right", "action": "lock", "source": "voice"},
    )
    result = intake(initial_state(), raw)
    assert result.input_rejected is False
    assert set(result.group_ts) == set(Group)
    assert result.values.risk == {Door.LEFT: False, Door.RIGHT: True}
    assert result.values.isofix == {Door.LEFT: True, Door.RIGHT: False}
    assert result.last_ts == 1.0
    assert result.command_ts == 1.0
    assert result.command.doors == frozenset({Door.RIGHT})
