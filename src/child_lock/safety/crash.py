"""!
@brief 충돌 판정과 시동 OFF 판정 (ASIL B, SWR-007·008·020, SWD 3.3).
"""

from child_lock.types import Candidate, Group, Lock, Reason, Rule, Values


def ignition_off(values: Values, stale: frozenset[Group]) -> bool:
    """!
    @brief 신선한 G9에서 시동이 꺼졌는지 판정한다.
    @param values 그룹별 마지막 수락 값
    @param stale 지연 그룹
    @return G9 신선이고 ignition_on이 FALSE이면 True
    """
    # 지연·미수신 값으로는 판정하지 않는다 (SWRS 3.1 순위 1)
    return Group.G9 not in stale and values.ignition_on is False


def update_latch(latched: bool, values: Values, stale: frozenset[Group]) -> bool:
    """!
    @brief 충돌 래치를 갱신한다 (A-15).
    @param latched 이전 래치
    @param values 그룹별 마지막 수락 값
    @param stale 지연 그룹
    @return 새 래치 (시동 OFF면 해제, 신선한 CONFIRMED면 설정)
    """
    if ignition_off(values, stale):
        return False
    if Group.G2 not in stale and values.crash_status == "CONFIRMED":
        return True
    return latched


def crash_candidate(latched: bool) -> Candidate | None:
    """!
    @brief 래치 중이면 양쪽 해제 후보를 만든다 (SWRS 3.1 순위 2).
    @param latched 충돌 래치
    @return CRASH 후보 또는 None
    """
    return Candidate(Rule.CRASH, Lock.RELEASE, Reason.CRASH_RELEASE) if latched else None


def crash_pending(values: Values, stale: frozenset[Group]) -> bool:
    """!
    @brief 신선한 충돌 판정 대기 상태인지 확인한다 (SWR-008).
    @param values 그룹별 마지막 수락 값
    @param stale 지연 그룹
    @return G2 신선이고 PENDING이면 True
    """
    return Group.G2 not in stale and values.crash_status == "PENDING"
