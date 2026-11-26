"""!
@brief 우선순위 중재와 결정 생성 (ASIL B, SWR-013-4·021·022, SWD 3.6).
@details 최종 출력은 이 모듈만 만든다. QM 후보는 규칙 소속·고정 출력·조건 재확인을
         통과해야 반영된다 (SWA 5장 간섭 방지).
"""

from collections.abc import Mapping

from child_lock.safety.approach import approach_candidate
from child_lock.safety.crash import crash_candidate, crash_pending, ignition_off
from child_lock.types import (
    QM_RULES,
    RULE_OUTPUT,
    Candidate,
    Context,
    Decision,
    Door,
    Group,
    Lock,
    Reason,
    Rule,
    State,
    Validity,
)

## 센서 고장 경고 코드 (SWR-021)
W_SENSOR_FAULT = "W_SENSOR_FAULT"
## state 표시 우선순위 (선언 순서, 앞이 높음)
_STATE_ORDER = list(State)
## 규칙이 직접 정하는 state (표에 없으면 NORMAL, CRASH·EMERGENCY는 표시 규칙)
_RULE_STATE = {
    Rule.IGNITION_OFF: State.OFF,
    Rule.INPUT_STALE: State.DEGRADED,
    Rule.SENSOR_FAULT: State.FAULT,
    Rule.DRIVER_OVERRIDE: State.OVERRIDE,
}


def safety_candidates(ctx: Context, door: Door) -> list[Candidate]:
    """!
    @brief ASIL B 규칙 후보를 모은다 (충돌, 입력 지연, 센서 고장, 접근위험).
    @param ctx 판정 문맥
    @param door 도어
    @return 후보 목록
    """
    found = [crash_candidate(ctx.crash_latched)]
    if ctx.stale:
        found.append(Candidate(Rule.INPUT_STALE, None, Reason.INPUT_STALE))
    if ctx.values.sensor_fault is True:
        found.append(Candidate(Rule.SENSOR_FAULT, None, Reason.SENSOR_FAULT))
    found.append(approach_candidate(ctx, door))
    return [c for c in found if c is not None]


def qm_plausible(candidate: Candidate, ctx: Context, door: Door) -> bool:
    """!
    @brief ASIL B 규칙보다 우선하는 QM 후보의 조건을 독립 재확인한다.
    @param candidate QM 후보
    @param ctx 판정 문맥
    @param door 도어
    @return 조건이 실제로 참이면 True (재확인 대상이 아닌 규칙은 True)
    """
    values = ctx.values
    if candidate.rule is Rule.IGNITION_OFF:
        return ignition_off(values, ctx.stale)
    if candidate.rule is Rule.EMERGENCY_RELEASE:
        return Group.G7 not in ctx.stale and (values.fire is True or values.overtemp is True)
    if candidate.rule is Rule.ISOFIX:
        # 미수신(None)에서도 예외 없이 거짓으로 판정한다
        return values.isofix is not None and values.isofix[door] is True
    return True


def accept_qm(candidate: Candidate, ctx: Context, door: Door) -> bool:
    """!
    @brief QM 후보를 결정에 반영해도 되는지 검사한다 (SWA 5장).
    @param candidate QM 후보
    @param ctx 판정 문맥
    @param door 도어
    @return 규칙 소속·고정 출력·조건 재확인을 모두 통과하면 True
    """
    if candidate.rule not in QM_RULES:
        return False
    if candidate.rule is Rule.DRIVER_COMMAND:
        output_ok = isinstance(candidate.lock, Lock)
    else:
        output_ok = candidate.lock == RULE_OUTPUT[candidate.rule]
    return output_ok and qm_plausible(candidate, ctx, door)


def no_change_reason(ctx: Context) -> Reason:
    """!
    @brief 활성 규칙이 없을 때의 이유 코드 (SWRS 3.2).
    @param ctx 판정 문맥
    @return INPUT_INVALID → COMMAND_REJECTED → CRASH_PENDING → NO_CHANGE 순 첫 해당
    """
    if ctx.input_rejected:
        return Reason.INPUT_INVALID
    if ctx.command_rejected:
        return Reason.COMMAND_REJECTED
    if crash_pending(ctx.values, ctx.stale):
        return Reason.CRASH_PENDING
    return Reason.NO_CHANGE


def pick(candidates: list[Candidate], ctx: Context) -> Candidate:
    """!
    @brief 우선순위가 가장 높은 후보를 고른다.
    @param candidates 후보 목록
    @param ctx 판정 문맥 (후보가 없을 때 이유 결정용)
    @return 선택 후보 (없으면 NO_CHANGE 유지 후보)
    """
    if not candidates:
        return Candidate(Rule.NO_CHANGE, None, no_change_reason(ctx))
    return min(candidates, key=lambda c: c.rule)


def door_state(rule: Rule, ctx: Context) -> State:
    """!
    @brief 도어 결정 규칙에 대응하는 state를 정한다 (SWRS 3.1 표시 규칙 포함).
    @param rule 도어 결정 규칙
    @param ctx 판정 문맥
    @return state
    """
    if rule in (Rule.CRASH, Rule.EMERGENCY_RELEASE):
        # 해제 중에도 지연·고장 사실을 숨기지 않는다
        if ctx.stale:
            return State.DEGRADED
        return State.FAULT if ctx.values.sensor_fault is True else State.NORMAL
    return _RULE_STATE.get(rule, State.NORMAL)


def validity(ctx: Context) -> Validity:
    """!
    @brief 입력 유효성 표시 (SWRS 2.2).
    @param ctx 판정 문맥
    @return 지연 → STALE, 거절 → INVALID, 아니면 VALID
    """
    if ctx.stale:
        return Validity.STALE
    return Validity.INVALID if ctx.input_rejected else Validity.VALID


def decide(
    ctx: Context,
    qm_by_door: Mapping[Door, list[Candidate]],
    previous: Mapping[Door, Lock],
) -> Decision:
    """!
    @brief 도어별 최상위 후보로 결정을 만든다 (SWR-022).
    @param ctx 판정 문맥
    @param qm_by_door 도어별 QM 후보
    @param previous 도어별 직전 출력
    @return 이 주기의 결정
    """
    chosen = {}
    for door in Door:
        accepted = [c for c in qm_by_door[door] if accept_qm(c, ctx, door)]
        chosen[door] = pick(safety_candidates(ctx, door) + accepted, ctx)
    outputs = {d: chosen[d].lock or previous[d] for d in Door}
    # 동률이면 Door 선언 순서(LEFT)가 먼저 — min은 처음 만난 최솟값을 돌려준다
    top = min(Door, key=lambda d: chosen[d].rule)
    states = [door_state(chosen[d].rule, ctx) for d in Door]
    fault_warning = Group.G9 not in ctx.stale and ctx.values.sensor_fault is True
    return Decision(
        lock_left=outputs[Door.LEFT],
        lock_right=outputs[Door.RIGHT],
        state=min(states, key=_STATE_ORDER.index),
        priority_reason=chosen[top].rule.name,
        reason_code=chosen[top].reason,
        reason_left=chosen[Door.LEFT].reason,
        reason_right=chosen[Door.RIGHT].reason,
        input_validity=validity(ctx),
        warning_code=W_SENSOR_FAULT if fault_warning else None,
    )
