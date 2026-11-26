"""!
@brief 아키텍처 의존 규칙 시험 (SWA 2.2, SAP-001).
@details src/child_lock의 import 문을 분석해 금지된 의존과 금지 모듈 사용을 찾는다.
"""

import ast
from pathlib import Path

import pytest

## 패키지 루트
ROOT = Path(__file__).resolve().parents[2] / "src" / "child_lock"

## 내부 모듈별 허용 import 접두사 (SWA 2.2). 표에 없는 내부 import는 금지
ALLOWED = {
    "child_lock.types": [],
    "child_lock.safety.validation": ["child_lock.types"],
    "child_lock.safety.freshness": ["child_lock.types"],
    "child_lock.safety.crash": ["child_lock.types"],
    "child_lock.safety.approach": ["child_lock.types"],
    "child_lock.safety.arbiter": [
        "child_lock.types",
        "child_lock.safety.crash",
        "child_lock.safety.approach",
    ],
    "child_lock.qm.rules": ["child_lock.types"],
    "child_lock.engine": ["child_lock.types", "child_lock.safety", "child_lock.qm"],
    "child_lock.event_log": ["child_lock.types", "child_lock.engine"],
    "child_lock.replay": ["child_lock.types", "child_lock.engine"],
    "child_lock.web.app": [
        "child_lock.types",
        "child_lock.engine",
        "child_lock.event_log",
        "child_lock.safety.validation",
    ],
}

## ASIL B 코어에서 금지하는 표준 모듈 (실제 시간·난수·I/O, SAP 2장)
FORBIDDEN_IN_CORE = {"time", "random", "datetime", "os", "io", "pathlib", "socket", "shutil"}
## 금지 모듈 검사 대상
CORE_PREFIXES = ("child_lock.types", "child_lock.safety", "child_lock.engine")


def module_name(path: Path) -> str:
    """! 파일 경로 → 모듈 이름 (__init__은 패키지 이름)."""
    parts = ["child_lock", *path.relative_to(ROOT).with_suffix("").parts]
    return ".".join(p for p in parts if p != "__init__")


def imports_of(source: str) -> set[str]:
    """! 소스의 절대 import 대상 모듈 이름 집합."""
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def violations(module: str, imported: set[str]) -> list[str]:
    """! 모듈 하나의 import 위반 목록."""
    found = []
    allowed = ALLOWED.get(module)
    for name in sorted(imported):
        internal = name.startswith("child_lock")
        if internal and (allowed is None or not any(name.startswith(a) for a in allowed)):
            found.append(f"{module} → {name}")
        if module.startswith(CORE_PREFIXES) and name.split(".")[0] in FORBIDDEN_IN_CORE:
            found.append(f"{module} → {name} (코어 금지 모듈)")
    return found


def test_checker_detects_safety_importing_qm():
    """! 검사기 자체 확인: safety → qm import를 위반으로 잡는다."""
    assert violations("child_lock.safety.crash", {"child_lock.qm.rules"}) == [
        "child_lock.safety.crash → child_lock.qm.rules"
    ]


def test_checker_detects_time_in_core():
    """! 검사기 자체 확인: 코어의 time import를 잡는다 (결정론 위반)."""
    assert violations("child_lock.engine", {"time"}) == [
        "child_lock.engine → time (코어 금지 모듈)"
    ]


def test_checker_flags_unlisted_module_importing_internal():
    """! 허용표에 없는 모듈의 내부 import는 위반 (새 모듈은 표에 등록해야 함)."""
    assert violations("child_lock.unknown", {"child_lock.types"}) != []


@pytest.mark.parametrize("path", sorted(ROOT.rglob("*.py")), ids=lambda p: p.name)
def test_module_follows_dependency_rules(path):
    """! 실제 소스의 모든 모듈이 SWA 2.2 의존 규칙을 지킨다."""
    source = path.read_text(encoding="utf-8")
    assert violations(module_name(path), imports_of(source)) == []
