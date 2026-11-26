# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 이 저장소에서 작업할 때 따라야 할 지침이다.

## 프로젝트

ClaudePython — Python 프로젝트. 현재 저장소에는 `README.md`와 Claude Code 설정(`.claude/`)만 있고, 소스 코드·의존성·빌드·테스트 구성은 아직 없다. 이런 것들이 추가되면 이 파일을 갱신한다.

## 개발 환경

- 언어: Python 3.13 이상. 새 문법·표준 라이브러리 기능은 3.13에서 동작하는 것만 쓴다.
- 단위 테스트: pytest, 커버리지는 pytest-cov.
- 정적 분석·포맷: Ruff. 설정은 `pyproject.toml`의 `[tool.ruff]`에 두고, 아래 품질 기준 중 Ruff로 검사할 수 있는 규칙(순환 복잡도 `C901`, 명명 규칙 `N`)을 켠다.
- 이 PC의 실행 정보:
  - 셸은 Windows PowerShell 5.1 (`&&`/`||` 사용 불가 — `;`와 `if ($?) { ... }`로 연결).
  - Python: `%LOCALAPPDATA%\Programs\Python\Python313\python.exe`, Git: `C:\Program Files\Git\cmd\git.exe`. 오래된 셸에서는 PATH에 없을 수 있으므로 전체 경로를 쓴다.
  - 테스트는 `python -m pytest`로 실행한다 (`Scripts` 폴더가 PATH에 없을 수 있음).

## 개발 절차

A-SPICE V-모델을 따른다. 각 단계의 산출물은 `docs/` 아래에 한글로 작성하고, 앞 단계 산출물과 ID로 양방향 추적이 가능해야 한다.

| 순서 | 단계 | A-SPICE | 산출물 위치 | 비고 |
|---|---|---|---|---|
| 1 | 요구사항 분석 | SWE.1 | `docs/01_requirements/` | 요구사항마다 ID 부여 (`SWR-001` 형식) |
| 2 | 아키텍처 설계 | SWE.2 | `docs/02_architecture/` | 컴포넌트 ↔ 요구사항 ID 추적 |
| 3 | 상세 설계 | SWE.3 | `docs/03_detailed_design/` | 모듈·함수 단위 설계 |
| 4 | 구현 | SWE.3 | `src/` | TDD로 진행 (아래 참고) |
| 5 | 단위 테스트 | SWE.4 | `tests/unit/` | 아래 품질 기준 충족 |
| 6 | 통합 테스트 | SWE.5 | `tests/integration/` | 아키텍처의 인터페이스 기준 |
| 7 | 시스템 테스트 | SWE.6 | `docs/06_system_test/` | `system-test-case` 에이전트로 케이스 생성 |

- 앞 단계 산출물이 없으면 다음 단계로 넘어가지 않고 사용자에게 알린다.
- 요구사항이 바뀌면 영향받는 설계·코드·테스트를 같은 작업에서 함께 갱신한다.

### 구현: TDD

구현 코드를 쓰기 **전에** `test-driven-development` 스킬(`.claude/skills/test-driven-development/`)을 호출하고 Red-Green-Refactor 사이클을 따른다: 실패하는 테스트 작성 → 실행해서 예상한 이유로 실패하는지 확인 → 통과시키는 최소 코드 작성 → 전체 테스트 실행 → 리팩터링.

- 버그 수정은 버그를 재현하는 실패 테스트부터 시작한다.
- 설정·문서 파일(`CLAUDE.md`, `pyproject.toml`, 스킬·에이전트 Markdown 등)은 TDD 대상이 아니다.
- 스킬 출처: github.com/obra/superpowers v7.0.2 (`22f0b46`), MIT 라이선스.

## 소스 코드 품질 기준

모든 기준은 PR 병합 전에 충족해야 하며, CI에서 하나라도 실패하면 병합하지 않는다.

| 항목 | 기준 | 측정 방법 |
|---|---|---|
| 단위 테스트 branch 커버리지 | **반드시 100%** | `python -m pytest --cov=src --cov-branch --cov-fail-under=100` |
| 단위 테스트 성공률 | 100% | 실패 0건. `skip`/`xfail`은 사유를 적은 경우에만 허용 |
| 순환 복잡도 | 함수당 **반드시 10 이하** | Ruff `C901` (`max-complexity = 10`) |
| 함수 길이 | 순수 코드 50줄 이하 | 함수 시그니처부터 끝까지에서 빈 줄·주석·docstring을 뺀 줄 수 |
| 주석률 | 20% 이상 (파일 단위) | (주석 줄 + docstring 줄) ÷ (빈 줄을 뺀 전체 줄) |
| 명명 규칙 | Google Python Style Guide | Ruff `N` 규칙 + 리뷰 |

- **커버리지 100%를 채우려고 의미 없는 테스트를 만들지 않는다.** 모든 테스트는 실제 동작을 검증해야 한다. 도달할 수 없는 분기는 테스트를 억지로 만들지 말고 코드에서 제거한다. `# pragma: no cover`는 사용하지 않고, 꼭 필요하면 사용자 승인을 받는다.
- 100%를 달성하지 못하면 빠진 분기를 확인해 테스트를 추가하고 다시 측정하는 과정을 반복한다.
- 함수 길이와 주석률은 Ruff로 검사할 수 없다. 측정 스크립트를 만들기 전까지는 직접 세어 확인한다.
- 명명 규칙 (Google Python Style Guide): 모듈·패키지·함수·메서드·변수는 `lower_snake_case`, 클래스·예외는 `CapWords`, 상수는 `UPPER_SNAKE_CASE`, 내부용은 앞에 `_`.
- 주석은 Doxygen 스타일로 쓴다. 모든 모듈·클래스·공개 함수에 `"""!`로 시작하는 docstring을 단다. 주석 내용은 한글로 쓴다.

  ```python
  def clamp(value: int, low: int, high: int) -> int:
      """!
      @brief 값을 [low, high] 범위로 제한한다.
      @param value 입력 값
      @param low 하한
      @param high 상한
      @return 제한된 값
      @throws ValueError low가 high보다 클 때
      """
  ```

## Git 브랜치·PR 규칙

GitHub Flow를 따른다: `main`과 짧게 쓰고 지우는 작업 브랜치만 둔다.

- **`main`에 직접 커밋·push하지 않는다.** 모든 변경은 작업 브랜치 → PR → 병합으로 반영한다.
- 브랜치 이름: `<유형>/<짧은-설명>` (영문 소문자, 하이픈 구분). 이슈가 있으면 번호를 붙인다: `feature/12-voltage-monitor`.

  | 유형 | 용도 |
  |---|---|
  | `feature/` | 새 기능 |
  | `fix/` | 버그 수정 |
  | `refactor/` | 동작 변경 없는 구조 개선 |
  | `docs/` | 문서·산출물 |
  | `test/` | 테스트만 추가·수정 |
  | `chore/` | 설정·빌드·CI |

- 브랜치는 최신 `main`에서 만든다. 작업 중 `main`이 바뀌면 rebase로 따라간다.
- 커밋 메시지: `<유형>: <한글 요약>` 형식 (예: `feat: 저전압 경고 판정 추가`). 유형은 `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
- PR:
  - 제목은 커밋 메시지와 같은 형식, 본문은 한글로 변경 내용·관련 요구사항 ID·테스트 결과를 적는다.
  - 병합 조건: Jenkins CI 통과 + 리뷰어 1명 이상 승인.
  - 병합 방식은 squash merge. 병합 후 작업 브랜치는 삭제한다.
  - **Claude는 PR을 만들 수는 있지만 병합하지 않는다.** 병합은 사람이 한다.

## CI

- Jenkins를 사용한다. 서버: `72.16.7.122` (포트·Job 이름 미정).
- 파이프라인은 저장소 루트의 `Jenkinsfile`로 정의하고, PR마다 다음을 실행한다:
  1. `ruff check .` 및 `ruff format --check .`
  2. `python -m pytest --cov=src --cov-branch --cov-fail-under=100`
  3. 함수 길이·주석률 검사 (측정 스크립트 추가 후)
- CI 결과는 PR에 표시되어야 하며, 실패하면 병합하지 않는다.

## 기타

- `CLAUDE.md`는 한글로 작성한다. 코드 식별자·경로·명령어·기술 용어만 원래 표기를 유지한다.
- 모든 산출물(문서, 주석, 커밋 메시지, PR)은 한글로 작성한다. 코드 식별자는 영문으로 쓴다.
- 의미 없는 사과를 하지 않는다.
