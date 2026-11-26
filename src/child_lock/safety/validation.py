"""!
@brief 입력 검증 (ASIL B, SWR-013-1~3, SWD 3.1).
@details 형식·범위 오류는 예외가 아니라 값으로 처리한다 (SWD 4장).
         타임스탬프 오류만 스냅샷 전체를 거절하고, 그 밖의 오류는 그룹 단위로 거절한다 (A-19).
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import replace

from child_lock.types import (
    SPEED_MAX_KPH,
    SPEED_MIN_KPH,
    Command,
    ControllerState,
    Door,
    Group,
    Intake,
    Lock,
    Values,
    frozen,
)

## 등록된 운전자 명령 값 (OEM-IF-004)
_SIDES = {"left": frozenset({Door.LEFT}), "right": frozenset({Door.RIGHT}), "all": frozenset(Door)}
_ACTIONS = {"lock": Lock.LOCK, "unlock": Lock.RELEASE}
_SOURCES = frozenset({"physical_button", "avn", "voice", "mobile_app"})


def is_number(x: object) -> bool:
    """!
    @brief 유한한 실수인지 확인한다 (bool, NaN, ±inf 제외).
    @param x 검사할 값
    @return 숫자이면 True
    """
    # bool은 int의 하위 형이므로 먼저 배제한다
    if isinstance(x, bool) or not isinstance(x, int | float):
        return False
    return math.isfinite(x)


def _is_bool(x: object) -> bool:
    """! @brief 불리언인지 확인한다. @param x 값 @return 불리언이면 True"""
    return isinstance(x, bool)


def _is_speed(x: object) -> bool:
    """! @brief 차속 범위 0.0~300.0 (양 끝 포함). @param x 값 @return 유효하면 True"""
    return is_number(x) and SPEED_MIN_KPH <= x <= SPEED_MAX_KPH


def _one_of(*allowed: str) -> Callable[[object], bool]:
    """! @brief 허용 문자열 검사 함수를 만든다. @param allowed 허용 값 @return 검사 함수"""
    return lambda x: isinstance(x, str) and x in allowed


## 그룹별 필드 계약 (SWRS 4.1 SWR-013 표)
GROUP_FIELDS: Mapping[Group, Mapping[str, Callable[[object], bool]]] = frozen(
    {
        Group.G1: {"vehicle_speed_kph": _is_speed, "gear": _one_of("P", "N", "D", "R")},
        Group.G2: {"crash_status": _one_of("NONE", "PENDING", "CONFIRMED")},
        Group.G3: {"rear_left_approach_risk": _is_bool, "rear_right_approach_risk": _is_bool},
        Group.G7: {
            "fire_detected": _is_bool,
            "overtemperature_detected": _is_bool,
            "adult_present": _is_bool,
        },
        Group.G8: {"isofix_left": _is_bool, "isofix_right": _is_bool},
        Group.G9: {"ignition_on": _is_bool, "sensor_fault": _is_bool},
    }
)


def check_timestamp(raw: Mapping, last_ts: float | None) -> float | None:
    """!
    @brief 스냅샷 타임스탬프를 검사한다 (A-16).
    @param raw 원시 스냅샷
    @param last_ts 직전 수락 스냅샷 시각
    @return 유효하면 시각, 아니면 None
    """
    ts = raw.get("source_timestamp_s")
    if not is_number(ts) or ts < 0:
        return None
    if last_ts is not None and ts < last_ts:
        return None
    return ts


def parse_group(group: Group, raw: Mapping) -> dict | None:
    """!
    @brief 그룹 하나의 필드 계약을 검사한다.
    @param group 입력 그룹
    @param raw 원시 스냅샷
    @return 유효하면 {필드: 값}, 누락·위반이면 None
    """
    contract = GROUP_FIELDS[group]
    if not all(name in raw and check(raw[name]) for name, check in contract.items()):
        return None
    return {name: raw[name] for name in contract}


def parse_command(raw: Mapping) -> tuple[Command | None, bool]:
    """!
    @brief 운전자 명령을 검증한다 (OEM-IF-004).
    @param raw 원시 스냅샷
    @return (명령, 거절 여부). 명령 키가 없으면 (None, False)
    """
    if "command" not in raw:
        return None, False
    cmd = raw["command"]
    if not isinstance(cmd, Mapping):
        return None, True
    side, action, source = cmd.get("side"), cmd.get("action"), cmd.get("source")
    if side not in _SIDES or action not in _ACTIONS or source not in _SOURCES:
        return None, True
    return Command(doors=_SIDES[side], action=_ACTIONS[action], source=source), False


def _apply(values: Values, group: Group, f: Mapping) -> Values:
    """!
    @brief 수락된 그룹 필드를 Values에 반영한다.
    @param values 이전 값
    @param group 입력 그룹
    @param f 검증된 필드
    @return 갱신된 값
    """
    updates = {
        Group.G1: lambda: {"speed_kph": f["vehicle_speed_kph"], "gear": f["gear"]},
        Group.G2: lambda: {"crash_status": f["crash_status"]},
        Group.G3: lambda: {
            "risk": frozen(
                {Door.LEFT: f["rear_left_approach_risk"], Door.RIGHT: f["rear_right_approach_risk"]}
            )
        },
        Group.G7: lambda: {
            "fire": f["fire_detected"],
            "overtemp": f["overtemperature_detected"],
            "adult": f["adult_present"],
        },
        Group.G8: lambda: {
            "isofix": frozen({Door.LEFT: f["isofix_left"], Door.RIGHT: f["isofix_right"]})
        },
        Group.G9: lambda: {"ignition_on": f["ignition_on"], "sensor_fault": f["sensor_fault"]},
    }
    return replace(values, **updates[group]())


def intake(state: ControllerState, raw: Mapping | None) -> Intake:
    """!
    @brief 스냅샷을 검증하고 수락된 그룹 값을 반영한다.
    @param state 이전 판정 상태
    @param raw 원시 스냅샷 (없으면 None)
    @return 검증 결과
    """
    unchanged = Intake(values=state.values, group_ts=state.group_ts, last_ts=state.last_ts)
    if raw is None:
        return unchanged
    ts = check_timestamp(raw, state.last_ts)
    if ts is None:
        # 시각을 알 수 없으므로 명령을 포함해 전체를 버린다
        return replace(unchanged, input_rejected=True)
    values, group_ts, rejected = state.values, dict(state.group_ts), False
    for group in Group:
        fields = parse_group(group, raw)
        if fields is None:
            rejected = True
            continue
        values = _apply(values, group, fields)
        group_ts[group] = ts
    command, command_rejected = parse_command(raw)
    return Intake(
        values=values,
        group_ts=frozen(group_ts),
        last_ts=ts,
        command=command,
        command_ts=ts,
        command_rejected=command_rejected,
        input_rejected=rejected,
    )
