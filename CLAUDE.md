# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ClaudePython — a Python project. The repository currently contains only `README.md`; no source code, dependencies, build, or test setup exists yet. Update this file as those are added.

## Environment

- Platform: Windows 11, shell is Windows PowerShell 5.1 (no `&&`/`||`; chain with `;` and `if ($?) { ... }`).
- Git is installed at `C:\Program Files\Git\cmd\git.exe` (may not be on PATH in older shells).
- Python 3.13 is installed at `%LOCALAPPDATA%\Programs\Python\Python313\python.exe` (with `openpyxl`). In older shells `python` may still resolve to the Microsoft Store alias — use the full path.
- PICT (microsoft/pict) binary lives at `.claude/skills/system-test-skill/bin/pict.exe` (git-ignored; `scripts/run_pict.py` re-downloads it if missing).
- Remote: `https://github.com/D2Papa/ClaudePython.git`, default branch `main`.

## Development workflow: TDD

When implementing any feature, bug fix, refactor, or behavior change in this repository, invoke the `test-driven-development` skill (`.claude/skills/test-driven-development/`) **before writing implementation code**, and follow its Red-Green-Refactor cycle: write a failing test, run it and confirm it fails for the expected reason, write the minimal code to pass, run the full suite, then refactor.

- Test runner: pytest. Run it as `python -m pytest` (full path to python above if needed; the `Scripts` dir may not be on PATH).
- Put tests under `tests/`, named `test_*.py`.
- Bug reports start with a failing test that reproduces the bug.
- The skill's own exceptions apply — throwaway prototypes, generated code, and config/docs (e.g. `CLAUDE.md`, skill/agent Markdown files) don't need TDD; ask the user if unsure.
- Skill source: github.com/obra/superpowers v7.0.2 (`22f0b46`), MIT license (copied in the skill folder).

## Conventions

- Communicate with the user in Korean; keep code identifiers and technical terms in their original form.
