"""!
@brief safety.freshness 단위 테스트 (SWR-013-4·5, SWD 3.2).
"""

from child_lock.safety.freshness import stale_groups
from child_lock.types import Group

## 모든 그룹이 시각 1.0 s에 갱신된 상태
ALL_AT_1 = dict.fromkeys(Group, 1.0)


def test_never_received_groups_are_stale():
    """! 한 번도 수락되지 않은 그룹은 지연."""
    assert stale_groups({}, 0.0) == frozenset(Group)


def test_delay_of_exactly_200ms_is_fresh():
    """! 갱신 지연 0.200 s는 '초과'가 아니므로 신선 (경계)."""
    assert stale_groups(ALL_AT_1, 1.2) == frozenset()


def test_delay_of_250ms_is_stale():
    """! 다음 주기(0.250 s)에는 지연."""
    assert stale_groups(ALL_AT_1, 1.25) == frozenset(Group)


def test_float_error_at_boundary_does_not_make_group_stale():
    """! 0.8 - 0.6 = 0.20000000000000007이지만 0.200 s로 판정해야 한다."""
    assert stale_groups(dict.fromkeys(Group, 0.6), 0.8) == frozenset()


def test_only_the_late_group_is_stale():
    """! 그룹별 판정: 한 그룹만 늦으면 그 그룹만 지연."""
    ts = dict(ALL_AT_1)
    ts[Group.G8] = 0.9
    assert stale_groups(ts, 1.2) == frozenset({Group.G8})
