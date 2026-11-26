#!/usr/bin/env python3
"""System test spec JSON -> validated Excel workbook.

Validates traceability, coverage, mandatory techniques (BVA/ECP), PICT row
completeness, duplicates and vague expected results. If any error is found the
workbook is NOT written (unless --allow-errors) and the errors are printed.

Usage:
    python build_workbook.py spec.json -o out.xlsx [--template form.xlsx] [--allow-errors]
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from copy import copy
from pathlib import Path

TECH_BVA = "경계값 분석"
TECH_ECP = "동치 클래스 분할"
TECH_PICT = "페어와이즈 (PICT)"
TECH_WOW = "WoW 검증"

# Loose aliases -> canonical names, so small spelling differences don't break counting.
TECH_ALIASES = {
    "경계값분석": TECH_BVA, "경계값 분석": TECH_BVA, "bva": TECH_BVA, "boundary value analysis": TECH_BVA,
    "동치클래스": TECH_ECP, "동치 클래스": TECH_ECP, "동치 클래스 분할": TECH_ECP, "동치분할": TECH_ECP,
    "ecp": TECH_ECP, "equivalence partitioning": TECH_ECP, "equivalence class": TECH_ECP,
    "페어와이즈": TECH_PICT, "페어와이즈(pict)": TECH_PICT, "페어와이즈 (pict)": TECH_PICT,
    "pairwise": TECH_PICT, "pict": TECH_PICT,
    "wow 검증": TECH_WOW, "wow검증": TECH_WOW, "wow": TECH_WOW,
}

VAGUE_EXPECTED = re.compile(
    r"^\s*(정상|정상\s*동작(함|한다)?|정상적으로\s*(동작|처리)(함|한다|됨)?|적절히\s*(동작|처리)(함|한다|됨)?|"
    r"ok|pass|works?( correctly| properly)?|as expected|문제\s*없음|이상\s*없음)\s*\.?\s*$",
    re.IGNORECASE,
)

FIELDS = [
    ("id", "테스트 케이스 ID", 16),
    ("basis_ids", "테스트 베이시스 ID", 18),
    ("objective", "테스트 목적", 36),
    ("preconditions", "사전 조건", 30),
    ("inputs", "입력값", 32),
    ("procedure", "절차", 44),
    ("expected", "예상 출력값", 40),
    ("techniques", "사용한 테스트 기법", 20),
    ("suggested", "제안", 8),
    ("notes", "비고", 24),
]
SHEET_NAMES = {"functional": "기능 테스트", "non-functional": "비기능 테스트"}


def norm_tech(t):
    key = re.sub(r"\s+", " ", str(t).strip().lower())
    return TECH_ALIASES.get(key, TECH_ALIASES.get(key.replace(" ", ""), str(t).strip()))


def norm_text(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def validate(spec):
    errors, warnings = [], []
    basis = spec.get("test_basis") or []
    cases = spec.get("test_cases") or []
    pict_models = {m.get("name"): m for m in spec.get("pict_models") or []}

    if not basis:
        errors.append("test_basis가 비어 있습니다.")
    if not cases:
        errors.append("test_cases가 비어 있습니다.")

    basis_ids = [b.get("id") for b in basis]
    for bid, n in Counter(basis_ids).items():
        if n > 1:
            errors.append(f"베이시스 ID 중복: {bid} ({n}회)")
    basis_by_id = {b.get("id"): b for b in basis}
    for b in basis:
        if b.get("type") not in SHEET_NAMES:
            errors.append(f"[{b.get('id')}] type은 functional/non-functional 중 하나여야 합니다: {b.get('type')!r}")

    for cid, n in Counter(c.get("id") for c in cases).items():
        if n > 1:
            errors.append(f"테스트 케이스 ID 중복: {cid} ({n}회)")

    seen_signature = {}
    for c in cases:
        cid = c.get("id") or "(ID 없음)"
        c["techniques"] = [norm_tech(t) for t in (c.get("techniques") or [])]
        sugg = bool(c.get("suggested"))

        for field in ("id", "objective", "inputs", "procedure", "expected"):
            if not str(c.get(field) or "").strip():
                errors.append(f"[{cid}] 필수 항목 '{field}'이(가) 비어 있습니다.")
        if not c["techniques"]:
            errors.append(f"[{cid}] 사용한 테스트 기법이 비어 있습니다.")
        if c.get("sheet") not in SHEET_NAMES:
            errors.append(f"[{cid}] sheet는 functional/non-functional 중 하나여야 합니다: {c.get('sheet')!r}")

        bids = c.get("basis_ids") or []
        if not bids:
            if not (sugg and str(c.get("gap_reason") or "").strip()):
                errors.append(f"[{cid}] 테스트 베이시스 ID가 없습니다 (요구사항 갭 제안 케이스라면 suggested=true와 gap_reason 필요).")
        for bid in bids:
            if bid not in basis_by_id:
                errors.append(f"[{cid}] 존재하지 않는 베이시스 ID 참조: {bid}")
            elif c.get("sheet") in SHEET_NAMES and basis_by_id[bid].get("type") != c.get("sheet"):
                warnings.append(f"[{cid}] 시트({c.get('sheet')})와 베이시스 {bid}의 유형({basis_by_id[bid].get('type')})이 다릅니다.")

        exp = str(c.get("expected") or "")
        if exp.strip() and (VAGUE_EXPECTED.match(exp) or len(exp.strip()) < 5):
            errors.append(f"[{cid}] 예상 출력값이 판정 불가능할 만큼 모호합니다: {exp!r}")

        sig = (tuple(sorted(bids)), norm_text(c.get("preconditions")), norm_text(c.get("inputs")), norm_text(exp))
        if sig in seen_signature:
            errors.append(f"[{cid}] {seen_signature[sig]}와 베이시스·사전조건·입력·기대값이 동일한 중복 케이스입니다.")
        else:
            seen_signature[sig] = cid

        if TECH_PICT in c["techniques"]:
            m = c.get("pict_model")
            if not m or m not in pict_models:
                errors.append(f"[{cid}] 페어와이즈 케이스는 pict_models에 정의된 pict_model을 참조해야 합니다: {m!r}")

    # PICT row completeness
    pict_counts = Counter(c.get("pict_model") for c in cases if TECH_PICT in c["techniques"])
    for name, m in pict_models.items():
        rows = m.get("rows")
        if not str(m.get("model") or "").strip():
            errors.append(f"[PICT {name}] model 텍스트가 비어 있습니다.")
        if rows is None:
            errors.append(f"[PICT {name}] rows(결과 행 수)가 없습니다.")
        elif pict_counts.get(name, 0) != rows:
            errors.append(f"[PICT {name}] PICT 결과 {rows}행 중 {pict_counts.get(name, 0)}개만 케이스화되었습니다 — 모든 행을 케이스로 만들어야 쌍 커버리지가 유지됩니다.")

    # Coverage & mandatory techniques (suggested cases excluded)
    cov = defaultdict(lambda: {"cases": [], "suggested": [], "techs": set()})
    for c in cases:
        for bid in c.get("basis_ids") or []:
            if bid not in basis_by_id:
                continue
            if c.get("suggested"):
                cov[bid]["suggested"].append(c.get("id"))
            else:
                cov[bid]["cases"].append(c.get("id"))
                cov[bid]["techs"].update(c["techniques"])
    for b in basis:
        bid = b.get("id")
        info = cov[bid]
        if not info["cases"]:
            errors.append(f"[{bid}] 커버하는 (제안이 아닌) 테스트 케이스가 없습니다.")
            continue
        if not str(b.get("bva_ecp_na_reason") or "").strip():
            if TECH_BVA not in info["techs"]:
                errors.append(f"[{bid}] 경계값 분석 케이스가 없습니다 (적용 불가면 bva_ecp_na_reason에 사유 기재).")
            if TECH_ECP not in info["techs"]:
                errors.append(f"[{bid}] 동치 클래스 분할 케이스가 없습니다 (적용 불가면 bva_ecp_na_reason에 사유 기재).")

    if not any(TECH_WOW in c["techniques"] for c in cases):
        warnings.append("WoW 검증(엣지) 케이스가 하나도 없습니다.")
    for b in basis:
        if b.get("assigned_id") and not str(b.get("text") or "").strip():
            warnings.append(f"[{b.get('id')}] 부여한 ID인데 원문(text)이 없어 매핑 시트에 원문이 빠집니다.")

    return errors, warnings, cov


# ---------------------------------------------------------------- workbook

def cell_value(c, key):
    v = c.get(key)
    if key == "basis_ids":
        return ", ".join(v or []) or f"(요구사항 갭) {c.get('gap_reason', '')}".strip()
    if key == "techniques":
        return ", ".join(v or [])
    if key == "suggested":
        return "제안" if v else ""
    if key == "notes":
        parts = [str(v or "").strip()]
        if c.get("pict_model"):
            parts.append(f"PICT 모델: {c['pict_model']}")
        if c.get("gap_reason") and c.get("basis_ids"):
            parts.append(f"갭: {c['gap_reason']}")
        return "\n".join(p for p in parts if p)
    return v if v is not None else ""


def style_header(ws, row, ncols, openpyxl):
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    thin = Side(style="thin", color="999999")
    for col in range(1, ncols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="305496")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)


def write_table(ws, headers, rows, widths=None, highlight=None):
    import openpyxl
    from openpyxl.styles import Alignment, Border, PatternFill, Side
    from openpyxl.utils import get_column_letter
    thin = Side(style="thin", color="BBBBBB")
    ws.append(headers)
    style_header(ws, 1, len(headers), openpyxl)
    fill = PatternFill("solid", fgColor="FFF2CC")
    for r in rows:
        ws.append(list(r))
        rr = ws.max_row
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=rr, column=col)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
            if highlight and highlight(r):
                cell.fill = fill
    for i, w in enumerate(widths or [], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"


def find_header_row(ws, wanted):
    wanted_n = {norm_text(w) for w in wanted}
    best, best_hits = None, 0
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 30)):
        hits = sum(1 for c in row if norm_text(c.value) in wanted_n)
        if hits > best_hits:
            best, best_hits = row[0].row, hits
    return best


def fill_template_sheet(ws, header_row, column_map, cases):
    from openpyxl.utils import get_column_letter
    header_cols = {}
    for cell in ws[header_row]:
        if cell.value is not None:
            header_cols[norm_text(cell.value)] = cell.column
    col_of = {}
    for key, header in column_map.items():
        if norm_text(header) in header_cols:
            col_of[key] = header_cols[norm_text(header)]
    # Required info with no template column gets appended on the right.
    last = ws.max_column
    for key, title in (("techniques", "사용한 테스트 기법"), ("suggested", "제안")):
        if key not in col_of:
            last += 1
            src = ws.cell(row=header_row, column=max(1, last - 1))
            dst = ws.cell(row=header_row, column=last, value=title)
            dst._style = copy(src._style)
            ws.column_dimensions[get_column_letter(last)].width = 16
            col_of[key] = last
    # Style sample = first data row (if any), then clear old data.
    sample = {c.column: copy(c._style) for c in ws[header_row + 1]} if ws.max_row > header_row else {}
    if ws.max_row > header_row:
        ws.delete_rows(header_row + 1, ws.max_row - header_row)
    for i, c in enumerate(cases):
        r = header_row + 1 + i
        for key, col in col_of.items():
            cell = ws.cell(row=r, column=col, value=cell_value(c, key))
            if col in sample:
                cell._style = copy(sample[col])
    return col_of


def build(spec, out_path, template=None):
    import openpyxl
    from openpyxl.utils import get_column_letter

    cases = spec["test_cases"]
    by_sheet = {k: [c for c in cases if c.get("sheet") == k] for k in SHEET_NAMES}

    if template:
        wb = openpyxl.load_workbook(template)
        column_map = spec.get("column_map") or {}
        if not column_map:
            raise SystemExit("--template를 쓰려면 spec.column_map이 필요합니다 (references/spec_schema.md 참고).")
        tname = spec.get("template_sheet") or wb.sheetnames[0]
        tws = wb[tname]
        header_row = find_header_row(tws, column_map.values())
        if not header_row:
            raise SystemExit(f"양식 시트 '{tname}'에서 column_map의 헤더를 찾지 못했습니다.")
        for key, sheet_title in SHEET_NAMES.items():
            ws = wb.copy_worksheet(tws)
            ws.title = sheet_title
            fill_template_sheet(ws, header_row, column_map, by_sheet[key])
        wb.remove(tws)
    else:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        for key, sheet_title in SHEET_NAMES.items():
            ws = wb.create_sheet(sheet_title)
            rows = [[cell_value(c, f) for f, _, _ in FIELDS] for c in by_sheet[key]]
            write_table(ws, [h for _, h, _ in FIELDS], rows, [w for _, _, w in FIELDS],
                        highlight=lambda r: r[8] == "제안")

    errors, warnings, cov = spec["_validation"]
    basis = spec["test_basis"]

    # Traceability matrix (basis -> cases); case -> basis is the basis column in case sheets.
    ws = wb.create_sheet("추적성 매트릭스")
    rows = []
    for b in basis:
        info = cov[b["id"]]
        techs = info["techs"]
        na = str(b.get("bva_ecp_na_reason") or "").strip()
        rows.append([
            b["id"], b.get("title", ""), "기능" if b.get("type") == "functional" else "비기능", b.get("asil", ""),
            ", ".join(info["cases"]), len(info["cases"]), ", ".join(info["suggested"]),
            "N/A" if na else ("O" if TECH_ECP in techs else "X"),
            "N/A" if na else ("O" if TECH_BVA in techs else "X"),
            "O" if TECH_PICT in techs else "", "O" if TECH_WOW in techs else "",
            "Covered" if info["cases"] else "Not covered", na,
        ])
    write_table(ws, ["베이시스 ID", "요구사항", "유형", "ASIL", "테스트 케이스 ID", "케이스 수", "제안 케이스",
                     "ECP", "BVA", "PICT", "WoW", "상태", "BVA/ECP 미적용 사유"], rows,
                [14, 40, 8, 6, 36, 8, 20, 6, 6, 6, 6, 12, 30],
                highlight=lambda r: r[11] != "Covered")

    # Coverage summary
    ws = wb.create_sheet("커버리지 요약")
    total = len(basis)
    covered = sum(1 for b in basis if cov[b["id"]]["cases"])
    tech_counter = Counter(t for c in cases for t in c["techniques"])
    summary = [
        ["테스트 베이시스 수", total],
        ["커버된 베이시스 수 (제안 제외)", covered],
        ["베이시스 커버리지", f"{(covered / total * 100) if total else 0:.1f}%"],
        ["기능 테스트 케이스", len(by_sheet["functional"])],
        ["비기능 테스트 케이스", len(by_sheet["non-functional"])],
        ["제안 케이스", sum(1 for c in cases if c.get("suggested"))],
        ["", ""],
    ]
    for t in (TECH_ECP, TECH_BVA, TECH_PICT, TECH_WOW):
        summary.append([f"기법: {t}", tech_counter.get(t, 0)])
    for t, n in sorted(tech_counter.items()):
        if t not in (TECH_ECP, TECH_BVA, TECH_PICT, TECH_WOW):
            summary.append([f"기법: {t}", n])
    summary += [["", ""], ["검증 오류", len(errors)], ["검증 경고", len(warnings)]]
    summary += [["경고", w] for w in warnings]
    write_table(ws, ["항목", "값"], summary, [36, 80])

    if spec.get("pict_models"):
        ws = wb.create_sheet("PICT 모델")
        write_table(ws, ["모델 이름", "베이시스 ID", "차수", "결과 행 수", "모델"],
                    [[m.get("name"), ", ".join(m.get("basis_ids") or []), m.get("order", 2), m.get("rows"), m.get("model")]
                     for m in spec["pict_models"]], [18, 20, 6, 10, 70])

    if spec.get("requirement_issues"):
        ws = wb.create_sheet("요구사항 이슈")
        write_table(ws, ["베이시스 ID", "이슈", "영향"],
                    [[i.get("basis_id", ""), i.get("issue", ""), i.get("impact", "")] for i in spec["requirement_issues"]],
                    [14, 60, 40])

    assigned = [b for b in basis if b.get("assigned_id")]
    if assigned:
        ws = wb.create_sheet("베이시스 ID 매핑")
        write_table(ws, ["부여한 ID", "요구사항 원문"], [[b["id"], b.get("text", "")] for b in assigned], [14, 100])

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return covered, total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--template")
    ap.add_argument("--allow-errors", action="store_true", help="오류가 있어도 워크북을 생성 (검토용)")
    ap.add_argument("--check-only", action="store_true", help="검증만 하고 파일은 만들지 않음")
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    errors, warnings, cov = validate(spec)
    spec["_validation"] = (errors, warnings, cov)

    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    print(f"--- 오류 {len(errors)}건, 경고 {len(warnings)}건")

    if args.check_only:
        sys.exit(1 if errors else 0)
    if errors and not args.allow_errors:
        print("오류가 있어 워크북을 생성하지 않았습니다. 케이스를 수정한 뒤 다시 실행하세요.")
        sys.exit(1)
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        raise SystemExit("openpyxl이 필요합니다: pip install openpyxl")
    covered, total = build(spec, args.out, args.template)
    print(f"워크북 생성: {args.out}  (베이시스 커버리지 {covered}/{total})")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
