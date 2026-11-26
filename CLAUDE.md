# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 이 저장소에서 작업할 때 따라야 할 지침이다.

**이 파일은 반드시 한글로 작성한다.** 내용을 추가·수정할 때도 한글로 쓰고, 코드 식별자·경로·명령어·기술 용어만 원래 표기를 유지한다.

## 프로젝트

ClaudePython — Python 프로젝트. 현재 저장소에는 `README.md`와 Claude Code 설정(`.claude/`)만 있고, 소스 코드·의존성·빌드·테스트 구성은 아직 없다. 이런 것들이 추가되면 이 파일을 갱신한다.

## 환경

- 플랫폼: Windows 11, 셸은 Windows PowerShell 5.1 (`&&`/`||` 사용 불가 — `;`와 `if ($?) { ... }`로 연결).
- Git: `C:\Program Files\Git\cmd\git.exe` (오래된 셸에서는 PATH에 없을 수 있음).
- Python 3.13: `%LOCALAPPDATA%\Programs\Python\Python313\python.exe` (`openpyxl`, `pytest` 설치됨). 오래된 셸에서는 `python`이 Microsoft Store 별칭으로 연결될 수 있으므로 전체 경로를 쓴다.
- PICT(microsoft/pict) 실행 파일: `.claude/skills/system-test-skill/bin/pict.exe` (git 제외 대상, 없으면 `scripts/run_pict.py`가 다시 받는다).
- 원격 저장소: `https://github.com/D2Papa/ClaudePython.git`, 기본 브랜치 `main`.
- git push 인증: Claude Code에서 실행한 명령은 `GCM_INTERACTIVE=never`, `GIT_TERMINAL_PROMPT=0` 환경 때문에 로그인 창을 띄울 수 없다. 자격 증명이 저장되지 않은 상태라면 사용자가 별도 터미널에서 한 번 로그인해야 한다.

## 개발 워크플로: TDD

이 저장소에서 기능 추가, 버그 수정, 리팩터링, 동작 변경을 할 때는 **구현 코드를 쓰기 전에** `test-driven-development` 스킬(`.claude/skills/test-driven-development/`)을 호출하고 Red-Green-Refactor 사이클을 따른다: 실패하는 테스트 작성 → 실행해서 예상한 이유로 실패하는지 확인 → 통과시키는 최소 코드 작성 → 전체 테스트 실행 → 리팩터링.

- 테스트 실행기: pytest. `python -m pytest`로 실행한다 (필요하면 위의 python 전체 경로 사용 — `Scripts` 폴더가 PATH에 없을 수 있음).
- 테스트는 `tests/` 아래에 `test_*.py` 이름으로 둔다.
- 버그 수정은 버그를 재현하는 실패 테스트부터 시작한다.
- 스킬 자체의 예외를 따른다 — 버리는 시제품, 생성된 코드, 설정·문서 파일(예: `CLAUDE.md`, 스킬·에이전트 Markdown)은 TDD 대상이 아니다. 애매하면 사용자에게 묻는다.
- 스킬 출처: github.com/obra/superpowers v7.0.2 (`22f0b46`), MIT 라이선스 (스킬 폴더에 사본 포함).

## 규칙

- 사용자와는 한국어로 소통하고, 코드 식별자와 기술 용어는 원래 표기를 유지한다.
- `CLAUDE.md`는 한글로 작성한다 (위 참고).
