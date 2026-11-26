"""!
@brief 함수 길이와 주석률을 측정하는 품질 검사 도구.
@details CLAUDE.md 품질 기준 중 Ruff로 검사할 수 없는 두 항목을 측정한다.
         - 함수 순수 코드 줄 수: 시그니처부터 끝까지에서 빈 줄·주석 전용 줄·docstring 제외
         - 파일 주석률: (주석 줄 + docstring 줄) / 빈 줄을 뺀 전체 줄
@par 사용법
     python -m tools.check_quality [--max-function-lines N] [--min-comment-ratio R] 경로...
"""

import argparse
import ast
import io
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

## docstring을 가질 수 있는 AST 노드 종류
_DOC_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
## 함수 정의 AST 노드 종류
_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass(frozen=True)
class FunctionLength:
    """!
    @brief 함수 하나의 측정 결과.
    @param name 클래스·바깥 함수를 포함한 이름 (예: Box.size.inner)
    @param lineno def 문이 있는 줄 번호
    @param pure_lines 순수 코드 줄 수
    """

    name: str
    lineno: int
    pure_lines: int


def _docstring_rows(tree: ast.AST) -> set[int]:
    """!
    @brief 모듈·클래스·함수 docstring이 차지하는 줄 번호를 모은다.
    @param tree 파싱된 AST
    @return docstring 줄 번호 집합
    """
    rows: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _DOC_OWNERS) or not node.body:
            continue
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                rows.update(range(first.lineno, first.end_lineno + 1))
    return rows


def _comment_only_rows(source: str) -> set[int]:
    """!
    @brief 주석만 있는 줄 번호를 모은다 (인라인 주석이 있는 코드 줄은 제외).
    @param source 소스 코드
    @return 주석 전용 줄 번호 집합
    """
    lines = source.splitlines()
    return {r for r in _comment_rows(source) if lines[r - 1].lstrip().startswith("#")}


def _walk_functions(node: ast.AST, prefix: str):
    """!
    @brief 함수 정의를 소스 순서대로 찾고 한정 이름을 붙인다.
    @param node 탐색 시작 노드
    @param prefix 바깥 클래스·함수 이름 접두사
    @return (한정 이름, 함수 노드) 생성기
    """
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _FUNCTIONS + (ast.ClassDef,)):
            name = f"{prefix}{child.name}"
            if isinstance(child, _FUNCTIONS):
                yield name, child
            yield from _walk_functions(child, f"{name}.")
        else:
            yield from _walk_functions(child, prefix)


def _comment_rows(source: str) -> set[int]:
    """!
    @brief 주석 토큰이 있는 모든 줄 번호를 모은다 (인라인 주석 포함).
    @param source 소스 코드
    @return 주석이 있는 줄 번호 집합
    """
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return {tok.start[0] for tok in tokens if tok.type == tokenize.COMMENT}


def comment_ratio(source: str) -> float | None:
    """!
    @brief 파일 주석률 = (주석 줄 + docstring 줄) / 빈 줄을 뺀 전체 줄.
    @param source 소스 코드
    @return 0.0~1.0 비율, 빈 소스이면 None
    """
    lines = source.splitlines()
    non_blank = {i + 1 for i, line in enumerate(lines) if line.strip()}
    if not non_blank:
        return None
    commented = (_docstring_rows(ast.parse(source)) | _comment_rows(source)) & non_blank
    return len(commented) / len(non_blank)


def function_lengths(source: str) -> list[FunctionLength]:
    """!
    @brief 소스의 모든 함수(메서드·중첩 함수 포함)의 순수 코드 줄 수를 잰다.
    @param source 소스 코드
    @return 소스 순서대로 정렬된 측정 결과 목록
    """
    tree = ast.parse(source)
    lines = source.splitlines()
    excluded = _docstring_rows(tree) | _comment_only_rows(source)
    result = []
    for name, node in _walk_functions(tree, ""):
        rows = range(node.lineno, node.end_lineno + 1)
        count = sum(1 for r in rows if r not in excluded and lines[r - 1].strip())
        result.append(FunctionLength(name, node.lineno, count))
    return result


def _python_files(paths: list[str]) -> list[Path]:
    """!
    @brief 인자로 받은 파일·디렉터리에서 검사할 .py 파일을 모은다.
    @param paths 파일 또는 디렉터리 경로 목록
    @return 정렬된 파일 경로 목록 (디렉터리는 재귀 탐색)
    """
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        files.extend(sorted(path.rglob("*.py")) if path.is_dir() else [path])
    return files


def check_file(path: Path, max_lines: int, min_ratio: float) -> list[str]:
    """!
    @brief 파일 하나를 검사해 위반 메시지를 만든다.
    @param path 검사할 파일
    @param max_lines 함수 순수 코드 최대 줄 수
    @param min_ratio 최소 주석률 (0.0~1.0)
    @return 위반 메시지 목록 (위반이 없으면 빈 목록)
    """
    source = path.read_text(encoding="utf-8")
    messages = [
        f"{path}:{f.lineno}: 함수 '{f.name}' 순수 코드 {f.pure_lines}줄 (최대 {max_lines}줄)"
        for f in function_lengths(source)
        if f.pure_lines > max_lines
    ]
    ratio = comment_ratio(source)
    if ratio is not None and ratio < min_ratio:
        messages.append(f"{path}: 주석률 {ratio:.1%} (최소 {min_ratio:.0%})")
    return messages


def main(argv: list[str] | None = None) -> int:
    """!
    @brief 명령행 진입점.
    @param argv 명령행 인자 (None이면 sys.argv 사용)
    @return 위반이 없으면 0, 있으면 1
    """
    parser = argparse.ArgumentParser(description="함수 길이·주석률 검사")
    parser.add_argument("paths", nargs="+", help="검사할 파일 또는 디렉터리")
    parser.add_argument("--max-function-lines", type=int, default=50)
    parser.add_argument("--min-comment-ratio", type=float, default=0.20)
    args = parser.parse_args(argv)
    violations = [
        message
        for path in _python_files(args.paths)
        for message in check_file(path, args.max_function_lines, args.min_comment_ratio)
    ]
    for message in violations:
        print(message)
    print(f"위반 {len(violations)}건")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
