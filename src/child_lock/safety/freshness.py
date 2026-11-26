"""!
@brief 입력 그룹 신선도 판정 (ASIL B, SWR-013-4·5, SWD 3.2).
"""

from collections.abc import Mapping

from child_lock.types import STALE_AFTER_S, TIME_DIGITS, Group


def stale_groups(group_ts: Mapping[Group, float], now_s: float) -> frozenset[Group]:
    """!
    @brief 갱신이 200 ms를 넘게 지연된 그룹을 찾는다.
    @param group_ts 그룹별 마지막 수락 시각
    @param now_s 평가 시각
    @return 지연 그룹 집합 (미수신 그룹 포함)
    """
    # 부동소수 오차로 0.200 s 경계가 흔들리지 않도록 반올림 후 비교한다
    return frozenset(
        g
        for g in Group
        if g not in group_ts or round(now_s - group_ts[g], TIME_DIGITS) > STALE_AFTER_S
    )
