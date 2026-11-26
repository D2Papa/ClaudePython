"""!
@brief replay 단위 테스트 (SWR-016, SWD 3.9).
"""

from dataclasses import replace

from child_lock.engine import evaluate, initial_state
from child_lock.replay import digest, replay
from child_lock.types import INITIAL_DECISION, Lock
from tests.unit.test_validation import snap

## 3주기 입력 벡터: 정상 → 명령 → 스냅샷 없음
VECTOR = [
    {"now_s": 1.0, "snapshot": snap()},
    {
        "now_s": 1.05,
        "snapshot": snap(
            source_timestamp_s=1.05, command={"side": "all", "action": "lock", "source": "avn"}
        ),
    },
    {"now_s": 1.1, "snapshot": None},
]


def test_replay_matches_manual_evaluation_chain():
    """! replay는 initial_state부터 evaluate를 차례로 적용한 결과와 같다."""
    state, expected = initial_state(), []
    for step in VECTOR:
        result = evaluate(state, step["now_s"], step["snapshot"])
        state = result.state
        expected.append(result.decision)
    assert replay(VECTOR) == expected


def test_replay_carries_state_between_steps():
    """! 2주기 LOCK 명령이 3주기(입력 없음)에도 유지된다."""
    decisions = replay(VECTOR)
    assert (decisions[2].lock_left, decisions[2].lock_right) == (Lock.LOCK, Lock.LOCK)


def test_digest_is_sha256_hex_and_sensitive_to_any_field():
    """! 같은 결정 → 같은 해시, 필드 하나만 달라도 다른 해시."""
    base = digest([INITIAL_DECISION])
    assert len(base) == 64
    assert digest([INITIAL_DECISION]) == base
    assert digest([replace(INITIAL_DECISION, lock_left=Lock.LOCK)]) != base
