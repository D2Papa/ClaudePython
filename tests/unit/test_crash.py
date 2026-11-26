"""!
@brief safety.crash 단위 테스트 (SWR-007·008·020, SWD 3.3).
"""

from dataclasses import replace

from child_lock.safety.crash import crash_candidate, crash_pending, ignition_off, update_latch
from child_lock.types import Candidate, Group, Lock, Reason, Rule
from tests.unit.helpers import NORMAL_VALUES

OFF = replace(NORMAL_VALUES, ignition_on=False)
CONFIRMED = replace(NORMAL_VALUES, crash_status="CONFIRMED")
PENDING = replace(NORMAL_VALUES, crash_status="PENDING")


def test_ignition_off_requires_fresh_g9_and_false():
    """! G9 신선·ignition_on FALSE일 때만 시동 OFF. 지연·미수신 값으로 판정하지 않는다."""
    assert ignition_off(OFF, frozenset()) is True
    assert ignition_off(OFF, frozenset({Group.G9})) is False
    assert ignition_off(NORMAL_VALUES, frozenset()) is False
    assert ignition_off(replace(NORMAL_VALUES, ignition_on=None), frozenset()) is False


def test_confirmed_crash_sets_latch():
    """! 신선한 CONFIRMED → 래치."""
    assert update_latch(False, CONFIRMED, frozenset()) is True


def test_stale_confirmed_does_not_set_latch():
    """! G2가 지연이면 오래된 CONFIRMED로 래치하지 않는다."""
    assert update_latch(False, CONFIRMED, frozenset({Group.G2})) is False


def test_latch_holds_after_crash_status_returns_to_none():
    """! 확정 후 NONE이 와도 래치 유지 (A-15)."""
    assert update_latch(True, NORMAL_VALUES, frozenset()) is True


def test_ignition_off_clears_latch_even_with_confirmed():
    """! 시동 OFF 주기에 래치 해제 (SWR-020)."""
    assert update_latch(True, replace(CONFIRMED, ignition_on=False), frozenset()) is False


def test_crash_candidate_releases_both_only_when_latched():
    """! 래치면 CRASH RELEASE 후보, 아니면 없음."""
    assert crash_candidate(True) == Candidate(Rule.CRASH, Lock.RELEASE, Reason.CRASH_RELEASE)
    assert crash_candidate(False) is None


def test_crash_pending_requires_fresh_pending():
    """! G2 신선·PENDING일 때만 대기 (SWR-008)."""
    assert crash_pending(PENDING, frozenset()) is True
    assert crash_pending(PENDING, frozenset({Group.G2})) is False
    assert crash_pending(CONFIRMED, frozenset()) is False
