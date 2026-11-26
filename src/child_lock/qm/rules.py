"""!
@brief QM 규칙 후보 (SWR-001~004·017·018·020, SWD 3.5).
@details 미수신 값(None)이면 후보를 만들지 않는다. 지연·고장 차단은 중재기가 우선순위로 보장한다.
"""

from child_lock.types import AUTO_LOCK_KPH, Candidate, Context, Door, Group, Lock, Reason, Rule


def ignition_candidate(ctx: Context) -> Candidate | None:
    """!
    @brief 시동 OFF 해제 후보 (SWRS 3.1 순위 1).
    @param ctx 판정 문맥
    @return G9 신선·ignition_on FALSE이면 후보
    """
    if Group.G9 in ctx.stale or ctx.values.ignition_on is not False:
        return None
    return Candidate(Rule.IGNITION_OFF, Lock.RELEASE, Reason.IGNITION_OFF)


def emergency_candidate(ctx: Context) -> Candidate | None:
    """!
    @brief 화재·과온 강제 해제 후보 (순위 3). 화재가 과온보다 이유 코드 우선.
    @param ctx 판정 문맥
    @return G7 신선·화재 또는 과온 TRUE이면 후보
    """
    if Group.G7 in ctx.stale:
        return None
    if ctx.values.fire is True:
        return Candidate(Rule.EMERGENCY_RELEASE, Lock.RELEASE, Reason.FIRE_RELEASE)
    if ctx.values.overtemp is True:
        return Candidate(Rule.EMERGENCY_RELEASE, Lock.RELEASE, Reason.OVERTEMP_RELEASE)
    return None


def isofix_candidate(ctx: Context, door: Door) -> Candidate | None:
    """!
    @brief ISOFIX 강제 잠금 후보 (순위 6).
    @param ctx 판정 문맥
    @param door 도어
    @return 해당 도어 ISOFIX TRUE이면 후보
    """
    isofix = ctx.values.isofix
    if isofix is None or isofix[door] is not True:
        return None
    return Candidate(Rule.ISOFIX, Lock.LOCK, Reason.ISOFIX_LOCK)


def adult_candidate(ctx: Context) -> Candidate | None:
    """!
    @brief 성인 탑승 강제 해제 후보 (순위 8).
    @param ctx 판정 문맥
    @return 성인 탑승 TRUE이면 후보
    """
    if ctx.values.adult is not True:
        return None
    return Candidate(Rule.ADULT_RELEASE, Lock.RELEASE, Reason.ADULT_RELEASE)


def auto_lock_candidate(ctx: Context) -> Candidate | None:
    """!
    @brief 주행 자동 잠금 후보 (순위 9, 3.0 km/h 이상).
    @param ctx 판정 문맥
    @return 차속 3.0 km/h 이상이면 후보
    """
    speed = ctx.values.speed_kph
    if speed is None or speed < AUTO_LOCK_KPH:
        return None
    return Candidate(Rule.AUTO_LOCK, Lock.LOCK, Reason.AUTO_LOCK_SPEED)


def driver_candidate(ctx: Context, door: Door) -> Candidate | None:
    """!
    @brief 운전자 명령 후보 (순위 10).
    @param ctx 판정 문맥
    @param door 도어
    @return 명령이 이 도어를 선택했으면 후보
    """
    command = ctx.command
    if command is None or door not in command.doors:
        return None
    return Candidate(Rule.DRIVER_COMMAND, command.action, Reason.DRIVER_COMMAND)


def qm_candidates(ctx: Context, door: Door) -> list[Candidate]:
    """!
    @brief 도어 하나에 대한 활성 QM 후보를 모두 모은다.
    @param ctx 판정 문맥
    @param door 도어
    @return 후보 목록 (우선순위 선택은 중재기가 한다)
    """
    found = [
        ignition_candidate(ctx),
        emergency_candidate(ctx),
        isofix_candidate(ctx, door),
        adult_candidate(ctx),
        auto_lock_candidate(ctx),
        driver_candidate(ctx, door),
    ]
    return [c for c in found if c is not None]
