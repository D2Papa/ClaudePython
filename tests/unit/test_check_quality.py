"""!
@brief tools/check_quality.py 단위 테스트.
"""

import runpy
import sys

import pytest
from tools.check_quality import comment_ratio, function_lengths, main

## 기준을 만족하는 파일: 비어 있지 않은 4줄 중 주석 2줄(50%), 함수 순수 코드 2줄
COMPLIANT = '"""! @brief 모듈 """\ndef f():\n    # 주석\n    return 1\n'


def test_main_reports_function_longer_than_limit(tmp_path, capsys):
    """! 순수 코드 2줄 함수에 한도 1줄을 주면 위반을 출력하고 1을 반환한다."""
    target = tmp_path / "a.py"
    target.write_text(COMPLIANT, encoding="utf-8")
    assert main(["--max-function-lines", "1", str(target)]) == 1
    assert f"{target}:2: 함수 'f' 순수 코드 2줄 (최대 1줄)" in capsys.readouterr().out


def test_main_reports_comment_ratio_below_minimum(tmp_path, capsys):
    """! 주석률 0%인 파일은 최소 20%를 위반한다."""
    target = tmp_path / "b.py"
    target.write_text("x = 1\n", encoding="utf-8")
    assert main([str(target)]) == 1
    assert f"{target}: 주석률 0.0% (최소 20%)" in capsys.readouterr().out


def test_main_scans_directory_and_passes_compliant_files(tmp_path, capsys):
    """! 디렉터리를 재귀 탐색하고, 기준을 만족하는 파일과 빈 __init__.py는 통과한다."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "ok.py").write_text(COMPLIANT, encoding="utf-8")
    assert main([str(tmp_path)]) == 0
    assert "위반 0건" in capsys.readouterr().out


def test_main_finds_violation_in_nested_directory(tmp_path, capsys):
    """! 하위 디렉터리의 위반 파일도 찾는다 (재귀 탐색 누락 결함 검출)."""
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "bad.py").write_text("x = 1\n", encoding="utf-8")
    assert main([str(tmp_path)]) == 1
    assert "bad.py: 주석률 0.0%" in capsys.readouterr().out


def test_comment_ratio_counts_docstring_comment_and_inline_comment_lines():
    """! 비어 있지 않은 6줄 중 docstring 3줄 + 주석 줄 1 + 인라인 주석 줄 1 = 5/6."""
    source = '"""!\n@brief 모듈\n"""\n# 주석\nx = 1  # 인라인\n\ny = 2\n'
    assert comment_ratio(source) == pytest.approx(5 / 6)


def test_comment_ratio_ignores_multiline_string_that_is_not_docstring():
    """! 대입문의 여러 줄 문자열은 주석이 아니다."""
    source = 's = """a\nb"""\n'
    assert comment_ratio(source) == 0.0


def test_comment_ratio_does_not_treat_leading_non_string_constant_as_docstring():
    """! 첫 문장이 문자열이 아닌 상수 식이면 docstring이 아니다: 2줄 중 주석 1줄 = 50%."""
    assert comment_ratio("1\n# 주석\n") == pytest.approx(0.5)


def test_module_entry_point_exits_with_violation_status(tmp_path, monkeypatch):
    """! python -m tools.check_quality 실행 시 위반이 있으면 종료 코드 1로 끝난다."""
    target = tmp_path / "c.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_quality", str(target)])
    # 이미 import된 모듈을 __main__으로 다시 실행하면 runpy가 경고하므로 캐시에서 뺀다
    monkeypatch.delitem(sys.modules, "tools.check_quality", raising=False)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("tools.check_quality", run_name="__main__")
    assert exc.value.code == 1


def test_comment_ratio_of_empty_source_is_none():
    """! 빈 파일(예: 빈 __init__.py)은 주석률을 정의하지 않는다."""
    assert comment_ratio("\n\n") is None


def test_function_length_excludes_blank_comment_and_docstring_lines():
    """! 빈 줄·주석 전용 줄·docstring을 빼고, 인라인 주석이 있는 코드 줄은 센다."""
    source = (
        "def f(x):\n"
        '    """!\n'
        "    @brief 설명\n"
        '    """\n'
        "    # 주석\n"
        "    y = x + 1\n"
        "\n"
        "    return y  # 인라인\n"
    )
    assert [(f.name, f.lineno, f.pure_lines) for f in function_lengths(source)] == [("f", 1, 3)]


def test_function_length_starts_at_signature_not_decorator():
    """! 데코레이터 줄은 빼고, 여러 줄 시그니처는 센다."""
    source = "@staticmethod\ndef g(\n    a,\n    b,\n):\n    return a\n"
    assert [(f.name, f.lineno, f.pure_lines) for f in function_lengths(source)] == [("g", 2, 5)]


def test_function_length_reports_methods_and_nested_with_qualified_names():
    """! 메서드와 중첩 함수도 각각 보고하고, 바깥 함수 길이에는 안쪽 줄이 포함된다."""
    source = (
        "class Box:\n"
        "    def size(self):\n"
        "        def inner():\n"
        "            return 1\n"
        "        return inner()\n"
    )
    result = [(f.name, f.pure_lines) for f in function_lengths(source)]
    assert result == [("Box.size", 4), ("Box.size.inner", 2)]
