"""!
@brief 판정 코어 (ASIL B, SWR-016·022, SWD 3.7).
@details 전역 상태·실제 시계·난수를 쓰지 않는 순수 함수로 구성한다 (SWA P-01, P-02).
         QM 규칙은 후보만 만들고 최종 결정은 safety.arbiter가 한다 (SWA P-03).
"""

from collections.abc import Mapping

from child_lock.qm.rules import qm_candidates
from child_lock.safety.approach import update_doors
from child_lock.safety.arbiter import decide
from child_lock.safety.crash import ignition_off, update_latch
from child_lock.safety.freshness import stale_groups
from child_lock.safety.validation import intake
from child_lock.types import Context, ControllerState, Door, StepResult, frozen


def initial_state() -> ControllerState:
    """!
    @brief 시작 상태: 값 미수신, 래치 없음, 양쪽 RELEASE.
    @return 초기 판정 상태
    """
    return ControllerState()


def evaluate(state: ControllerState, now_s: float, raw: Mapping | None) -> StepResult:
    """!
    @brief 평가 주기 하나를 수행한다 (SWA 4.1 시퀀스).
    @param state 이전 판정 상태
    @param now_s 평가 시각 (호출자가 주입)
    @param raw 이번 주기 원시 스냅샷 (없으면 None)
    @return 다음 상태와 결정
    """
    taken = intake(state, raw)
    stale = stale_groups(taken.group_ts, now_s)
    off = ignition_off(taken.values, stale)
    latched = update_latch(state.crash_latched, taken.values, stale)
    doors, suppressed = update_doors(state.doors, taken, stale, off)
    # 문맥은 래치·도어 갱신 후에 만든다 (REV-G2-001 지적 6)
    ctx = Context(
        now_s=now_s,
        values=taken.values,
        stale=stale,
        command=taken.command,
        command_rejected=taken.command_rejected,
        input_rejected=taken.input_rejected,
        crash_latched=latched,
        doors=doors,
        suppressed=suppressed,
    )
    decision = decide(ctx, {d: qm_candidates(ctx, d) for d in Door}, state.outputs)
    next_state = ControllerState(
        values=taken.values,
        group_ts=taken.group_ts,
        last_ts=taken.last_ts,
        crash_latched=latched,
        doors=doors,
        outputs=frozen({Door.LEFT: decision.lock_left, Door.RIGHT: decision.lock_right}),
    )
    return StepResult(state=next_state, decision=decision)
