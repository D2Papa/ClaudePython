"""!
@brief qm.rules 단위 테스트 (SWR-001~004·017·018·020, SWD 3.5).
"""

from dataclasses import replace

import pytest

from child_lock.qm.rules import (
    adult_candidate,
    auto_lock_candidate,
    driver_candidate,
    emergency_candidate,
    ignition_candidate,
    isofix_candidate,
    qm_candidates,
)
from child_lock.types import Candidate, Command, Door, Group, Lock, Reason, Rule, Values, frozen
from tests.unit.helpers import NORMAL_VALUES, make_ctx

## 모든 값이 미수신인 문맥 (초기 상태 — 예외 없이 후보 없음이어야 함)
EMPTY = make_ctx(Values(), stale=frozenset(Group))


def ctx_with(**value_changes):
    """! NORMAL_VALUES 일부를 바꾼 Context."""
    return make_ctx(replace(NORMAL_VALUES, **value_changes))


def test_ignition_candidate_requires_fresh_false():
    """! G9 신선·OFF → IGNITION_OFF RELEASE. 지연이면 없음."""
    assert ignition_candidate(ctx_with(ignition_on=False)) == Candidate(
        Rule.IGNITION_OFF, Lock.RELEASE, Reason.IGNITION_OFF
    )
    stale_off = make_ctx(replace(NORMAL_VALUES, ignition_on=False), stale=frozenset({Group.G9}))
    assert ignition_candidate(stale_off) is None
    assert ignition_candidate(ctx_with()) is None


def test_emergency_candidate_fire_takes_precedence_over_overtemp():
    """! 화재와 과온이 함께면 FIRE_RELEASE (SWR-017 이유 코드 순서)."""
    assert emergency_candidate(ctx_with(fire=True, overtemp=True)).reason is Reason.FIRE_RELEASE
    assert emergency_candidate(ctx_with(overtemp=True)) == Candidate(
        Rule.EMERGENCY_RELEASE, Lock.RELEASE, Reason.OVERTEMP_RELEASE
    )
    assert emergency_candidate(ctx_with()) is None


def test_emergency_candidate_ignores_stale_g7():
    """! G7 지연이면 오래된 화재 값으로 해제하지 않는다."""
    ctx = make_ctx(replace(NORMAL_VALUES, fire=True), stale=frozenset({Group.G7}))
    assert emergency_candidate(ctx) is None


def test_isofix_candidate_locks_only_its_door():
    """! 좌 ISOFIX만 TRUE → 좌만 LOCK (SWR-018)."""
    ctx = ctx_with(isofix=frozen({Door.LEFT: True, Door.RIGHT: False}))
    assert isofix_candidate(ctx, Door.LEFT) == Candidate(Rule.ISOFIX, Lock.LOCK, Reason.ISOFIX_LOCK)
    assert isofix_candidate(ctx, Door.RIGHT) is None


def test_adult_candidate_releases():
    """! 성인 탑승 → ADULT_RELEASE RELEASE."""
    assert adult_candidate(ctx_with(adult=True)) == Candidate(
        Rule.ADULT_RELEASE, Lock.RELEASE, Reason.ADULT_RELEASE
    )
    assert adult_candidate(ctx_with()) is None


@pytest.mark.parametrize(("speed", "active"), [(2.9, False), (3.0, True), (300.0, True)])
def test_auto_lock_at_3_kph_or_more(speed, active):
    """! 3.0 km/h 이상에서 자동 잠금 (경계 2.9/3.0)."""
    assert (auto_lock_candidate(ctx_with(speed_kph=speed)) is not None) is active


def test_driver_candidate_applies_only_to_selected_door():
    """! right lock 명령은 우 도어에만 (SWR-002)."""
    command = Command(doors=frozenset({Door.RIGHT}), action=Lock.LOCK, source="physical_button")
    ctx = make_ctx(command=command)
    assert driver_candidate(ctx, Door.RIGHT) == Candidate(
        Rule.DRIVER_COMMAND, Lock.LOCK, Reason.DRIVER_COMMAND
    )
    assert driver_candidate(ctx, Door.LEFT) is None


def test_unreceived_values_produce_no_candidates_without_error():
    """! 모든 값 미수신(None)에서 예외 없이 후보 없음 (REV-G2-001 지적 2)."""
    assert qm_candidates(EMPTY, Door.LEFT) == []


def test_qm_candidates_collects_all_active_rules():
    """! 활성 규칙 후보를 모두 모은다 (순서는 중재기가 정함)."""
    ctx = make_ctx(
        replace(NORMAL_VALUES, adult=True, speed_kph=50.0),
        command=Command(doors=frozenset(Door), action=Lock.RELEASE, source="avn"),
    )
    rules = {c.rule for c in qm_candidates(ctx, Door.LEFT)}
    assert rules == {Rule.ADULT_RELEASE, Rule.AUTO_LOCK, Rule.DRIVER_COMMAND}
