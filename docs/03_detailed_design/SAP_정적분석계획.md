# 정적 분석 계획

| 항목 | 내용 |
|---|---|
| 문서 ID | SAP-001 |
| 관련 문서 | SWA-001, SWD-001, CLAUDE.md 소스 코드 품질 기준 |
| 기준선 | BL-SWD-1.0 |

## 1. 도구와 검사 항목

| 검사 | 도구·설정 | 기준 | 대상 | 실행 시점 |
|---|---|---|---|---|
| 코딩 규칙·잠재 결함 | Ruff `E`, `W`, `F`, `B`, `UP` | 위반 0 | `src`, `tests`, `tools` | 커밋 전, CI |
| import 정렬 | Ruff `I` | 위반 0 | 전체 | 커밋 전, CI |
| 명명 규칙 (Google) | Ruff `N` | 위반 0 | 전체 | 커밋 전, CI |
| 순환 복잡도 | Ruff `C901`, `max-complexity = 10` | 함수당 10 이하 | 전체 | 커밋 전, CI |
| 포맷 | `ruff format --check` | 차이 0 | 전체 | CI |
| 함수 길이 | `tools/check_quality.py` | 순수 코드 50줄 이하 | `src`, `tools` | CI |
| 주석률 | `tools/check_quality.py` | 파일당 20% 이상 | `src`, `tools` | CI |
| 의존 규칙 | `tests/unit/test_architecture.py` | SWA 2.2 위반 0 | `src/child_lock` | 단위 시험, CI |
| 경고 | `pytest -W error` | 경고 0 | 시험 실행 | CI |
| 주석 존재 (Doxygen) | Ruff `D1` (모듈·클래스·공개 함수 docstring 누락) | 위반 0 | `src`, `tools` (`tests`는 제외) | 커밋 전, CI |
| 주석 형식 (Doxygen) | 리뷰 — docstring이 `"""!`로 시작하고 `@brief`, 매개변수가 있으면 `@param`, 반환값이 있으면 `@return` | 위반 0 | `src`, `tools` | PR 리뷰 |
| branch 커버리지 (동적 분석, 참고) | `pytest --cov --cov-branch --cov-fail-under=100` | 100% | `src`, `tools` | CI |
| 대상 Python 문법 | Ruff `target-version = "py312"` + CI 3.12·3.13 실행 | 3.12에서 동작 | 전체 | CI |

## 2. 추가로 적용하는 ASIL B 코드 규칙 (리뷰로 확인)

| 규칙 | 이유 |
|---|---|
| `safety`, `types`, `engine`에서 전역 가변 상태 금지 (모듈 상수는 불변 타입만) | 결정론, 간섭 방지 |
| `safety`, `types`, `engine`에서 `time`, `random`, `datetime`, 파일·네트워크 I/O 금지 | SWR-016, SWR-012 |
| 부동소수 경계 비교는 `round(…, 9)` 후 비교 | 경계값 판정 안정성 |
| 예외 삼키기(`except Exception: pass`) 금지 | 결함 은폐 방지 |

`time`/`random`/I/O 금지는 아키텍처 시험에서 금지 import 목록으로 함께 검사한다.

## 3. 채택하지 않은 도구

| 도구 | 사유 |
|---|---|
| mypy 등 정적 타입 검사 | CLAUDE.md 필수 도구가 아님. 타입 힌트는 작성하되 검사는 도입 여부를 G3 이후 재검토 |
| 보안 정적 분석 (bandit 등) | 네트워크 노출이 시뮬레이터 로컬 실행에 한정되어 현 범위에서 제외 |

## 4. 위반 처리

- CI에서 하나라도 실패하면 PR을 병합하지 않는다.
- 예외 처리(`# noqa`, 커버리지 제외)는 사용하지 않는다. 불가피하면 PR에 사유를 적고 사용자 승인을 받는다.
