"""!
@brief 접근위험 잠금·해제 억제·override (ASIL B, SWR-005·006·009, SWD 3.4).
@details 도어마다 독립적으로 판정한다 (SWR-009).
"""

from collections.abc import Mapping

from child_lock.types import (
    AUTO_LOCK_KPH,
    INITIAL_DOORS,
    OVERRIDE_WINDOW_S,
    TIME_DIGITS,
    Candidate,
    Command,
    Context,
    Door,
    DoorApproach,
    Group,
    Intake,
    Lock,
    Reason,
    Rule,
    frozen,
)


def unlock_requested(command: Command | None, door: Door) -> bool:
    """!
    @brief 이 주기에 해당 도어 해제 요청이 있는지 확인한다.
    @param command 검증된 운전자 명령 (없으면 None)
    @param door 도어
    @return unlock 명령이 도어를 포함하면 True
    """
    return command is not None and command.action is Lock.RELEASE and door in command.doors


def _within_window(t0: float | None, t: float) -> bool:
    """!
    @brief 첫 억제 후 10.0 s 이하인지 판정한다 (경계 포함, 반올림 비교).
    @param t0 첫 억제 시각
    @param t 재입력 시각
    @return t0가 있고 t - t0 <= 10.0이면 True
    """
    return t0 is not None and round(t - t0, TIME_DIGITS) <= OVERRIDE_WINDOW_S


def update_door(
    prev: DoorApproach, risk: bool | None, speed: float | None, unlock: bool, t: float | None
) -> tuple[DoorApproach, bool]:
    """!
    @brief 도어 하나의 억제·override 상태를 갱신한다 (SWD 3.4 판정표).
    @param prev 이전 도어 상태
    @param risk 접근위험 (미수신이면 None)
    @param speed 차속 (미수신이면 None)
    @param unlock 이 주기 해제 요청 여부
    @param t 명령 스냅샷 시각
    @return (새 도어 상태, 이번 주기 억제 여부)
    """
    if risk is not True:
        return DoorApproach(), False
    if speed is not None and speed >= AUTO_LOCK_KPH:
        # 주행 중: override 불가, 억제는 하되 t0를 남기지 않는다
        return DoorApproach(), unlock
    if prev.override or not unlock:
        return prev, False
    if _within_window(prev.t0, t):
        return DoorApproach(t0=prev.t0, override=True), False
    return DoorApproach(t0=t), True


def update_doors(
    prev_doors: Mapping[Door, DoorApproach],
    intake: Intake,
    stale: frozenset[Group],
    ignition_off: bool,
) -> tuple[Mapping[Door, DoorApproach], frozenset[Door]]:
    """!
    @brief 양쪽 도어의 접근위험 상태를 갱신한다.
    @param prev_doors 이전 도어 상태
    @param intake 이번 주기 검증 결과
    @param stale 지연 그룹
    @param ignition_off 시동 OFF 여부
    @return (새 도어 상태, 억제된 도어 집합)
    """
    values = intake.values
    # 시동 OFF·입력 지연·센서 고장: 지연·고장 값으로 판정하지 않고
    # override를 보수적으로 끝낸다 (A-21)
    if ignition_off or stale or values.sensor_fault is True:
        return INITIAL_DOORS, frozenset()
    new_doors, suppressed = {}, set()
    for door in Door:
        risk = values.risk[door] if values.risk is not None else None
        unlock = unlock_requested(intake.command, door)
        new_doors[door], held = update_door(
            prev_doors[door], risk, values.speed_kph, unlock, intake.command_ts
        )
        if held:
            suppressed.add(door)
    return frozen(new_doors), frozenset(suppressed)


def approach_candidate(ctx: Context, door: Door) -> Candidate | None:
    """!
    @brief 접근위험 도어의 후보를 만든다 (SWRS 3.1 순위 7, 7a).
    @param ctx 판정 문맥
    @param door 도어
    @return override면 해제 후보, 아니면 잠금 후보, 위험이 없으면 None
    """
    risk = ctx.values.risk
    if risk is None or risk[door] is not True:
        return None
    if ctx.doors[door].override:
        return Candidate(Rule.DRIVER_OVERRIDE, Lock.RELEASE, Reason.DRIVER_OVERRIDE)
    reason = (
        Reason.APPROACH_RISK_SUPPRESSED if door in ctx.suppressed else Reason.APPROACH_RISK_LOCK
    )
    return Candidate(Rule.APPROACH_RISK, Lock.LOCK, reason)
