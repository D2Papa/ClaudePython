# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 이 저장소에서 작업할 때 따라야 할 지침이다.

## 프로젝트

ClaudePython — 전자식 차일드락 제어 SW의 PC/SIL 참조 구현 (교육용 가상 OEM 요구사항 `OEM/`, 저장소에 커밋하지 않음).

- 소스: `src/child_lock/` — `safety/`(ASIL B), `qm/`(QM), `engine.py`(판정 코어), `event_log.py`, `replay.py`, `web/`(FastAPI 시뮬레이터). 구조와 의존 규칙은 `docs/02_architecture/`, 함수 설계는 `docs/03_detailed_design/`.
- 시험: `tests/unit`(단위), `tests/integration`(통합), `tests/system`(`docs/06_system_test/scenarios.json` 실행). 아키텍처 의존 규칙은 `tests/unit/test_architecture.py`가 검사하므로, 새 모듈을 추가하면 그 파일의 `ALLOWED` 표에 등록한다.
- 시뮬레이터 실행: `python -m uvicorn child_lock.web.app:app --app-dir src` 후 브라우저에서 `http://127.0.0.1:8000/`.
- 진행 상태와 미결 사항: `docs/06_system_test/SVR-001_SW검증보고서.md`, OEM 질의는 `docs/00_plan/OEM-Q-001_OEM질의서.md`, 작업 가정은 `docs/00_plan/개발계획서.md` 5장.

## 개발 환경

- 언어: Python. 코드는 3.12 호환으로 작성하고 CI에서 3.12·3.13 모두 시험한다 (OEM 사양이 3.12, 개발계획서 D-01). Ruff `target-version = "py312"`.
- 단위 테스트: pytest, 커버리지는 pytest-cov.
- 정적 분석·포맷: Ruff. 설정은 `pyproject.toml`의 `[tool.ruff]`에 두고, 아래 품질 기준 중 Ruff로 검사할 수 있는 규칙(순환 복잡도 `C901`, 명명 규칙 `N`)을 켠다.
- 이 PC의 실행 정보:
  - 셸은 Windows PowerShell 5.1 (`&&`/`||` 사용 불가 — `;`와 `if ($?) { ... }`로 연결).
  - Python: `%LOCALAPPDATA%\Programs\Python\Python313\python.exe` (3.12는 `Python312`), Git: `C:\Program Files\Git\cmd\git.exe`. 오래된 셸에서는 PATH에 없을 수 있으므로 전체 경로를 쓴다.
  - Web 시험은 `starlette.testclient`가 아니라 `tests/unit/test_web_app.py`의 `AsgiClient`(httpx ASGI 전송)를 쓴다 — 설치된 Starlette의 사용 중단 경고가 `-W error`로 실패하기 때문.
  - GitHub API로 PR을 만드는 것은 권한 설정상 막혀 있다. 브랜치를 push하고 PR 생성 링크를 사용자에게 전달한다.
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

- Jenkins를 사용한다. 서버: `http://172.16.7.122` (포트 80, 이 PC에서 서비스로 실행, Windows 11 내장 노드, 서비스 계정 LocalSystem).
- Job: `ClaudePython-CI` (Multibranch Pipeline). GitHub에서 사설 IP로 webhook을 보낼 수 없으므로 5분마다 브랜치를 검사해 새 커밋을 빌드한다. 기존 `ClaudePython`(FreeStyle) Job은 사용자가 만든 것이므로 건드리지 않는다.
- API 인증: 사용자 `admin` + API 키. **API 키는 저장소·커밋·메모리 어디에도 저장하지 않는다.** 필요하면 사용자에게 받는다.
- 파이프라인은 저장소 루트의 `Jenkinsfile`로 정의하고, Python 3.12·3.13에서 다음을 실행한다:
  1. `ruff check .` 및 `ruff format --check .`
  2. `python -m pytest -W error --cov --cov-branch --cov-fail-under=100`
  3. `python -m tools.check_quality tools src` (함수 길이·주석률)
- CI 결과가 실패하면 병합하지 않는다. 보고할 때는 Jenkins 결과인지 로컬 실행 결과인지 구분해 밝힌다.

## 기타

- `CLAUDE.md`는 한글로 작성한다. 코드 식별자·경로·명령어·기술 용어만 원래 표기를 유지한다.
- 모든 산출물(문서, 주석, 커밋 메시지, PR)은 한글로 작성한다. 코드 식별자는 영문으로 쓴다.
- 의미 없는 사과를 하지 않는다.
