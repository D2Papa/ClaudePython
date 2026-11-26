"""!
@brief 결정론 재생과 출력 해시 (QM, SWR-016, SWD 3.9).
"""

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict

from child_lock.engine import evaluate, initial_state
from child_lock.types import Decision


def replay(vector: Iterable[Mapping]) -> list[Decision]:
    """!
    @brief 입력 벡터를 초기 상태부터 차례로 평가한다.
    @param vector [{"now_s": 시각, "snapshot": 스냅샷 또는 None}, ...]
    @return 주기별 결정 목록
    """
    state, decisions = initial_state(), []
    for step in vector:
        result = evaluate(state, step["now_s"], step["snapshot"])
        state = result.state
        decisions.append(result.decision)
    return decisions


def digest(decisions: Iterable[Decision]) -> str:
    """!
    @brief 결정 순서의 SHA-256 해시를 만든다 (키 정렬로 표현을 고정).
    @param decisions 결정 목록
    @return 64자리 16진수 해시
    """
    text = json.dumps([asdict(d) for d in decisions], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
