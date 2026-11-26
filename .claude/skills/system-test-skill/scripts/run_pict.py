#!/usr/bin/env python3
"""Run Microsoft PICT (https://github.com/microsoft/pict) on a model file.

Finds pict via $PICT_PATH, PATH, or <skill>/bin. If absent, installs it:
  1. a prebuilt binary from the latest GitHub release, when one matches this OS
  2. otherwise clones the repo and builds with CMake (needs git, cmake, a C++ compiler)

Usage:
    python run_pict.py model.txt [--order 2] [--seed N] [--out-json r.json] [--out-tsv r.tsv]
    python run_pict.py --install-only
"""
import argparse
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO = "microsoft/pict"
BIN_DIR = Path(__file__).resolve().parent.parent / "bin"
EXE = "pict.exe" if os.name == "nt" else "pict"


def find_pict():
    cand = [os.environ.get("PICT_PATH"), shutil.which("pict"), str(BIN_DIR / EXE)]
    for c in cand:
        if c and Path(c).is_file():
            return c
    return None


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "system-test-skill", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def install_from_release():
    rel = json.loads(_get(f"https://api.github.com/repos/{REPO}/releases/latest"))
    system = platform.system().lower()
    keys = {"windows": ["win", ".exe"], "linux": ["linux"], "darwin": ["mac", "osx", "darwin"]}.get(system, [])
    for asset in rel.get("assets", []):
        name = asset["name"].lower()
        if not any(k in name for k in keys):
            continue
        data = _get(asset["browser_download_url"])
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        target = BIN_DIR / EXE
        if name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                member = next((m for m in z.namelist() if Path(m).name.lower() == EXE), None)
                if not member:
                    continue
                target.write_bytes(z.read(member))
        elif name.endswith(".exe") or name == "pict":
            target.write_bytes(data)
        else:
            continue
        if os.name != "nt":
            target.chmod(0o755)
        print(f"PICT {rel.get('tag_name')} 설치: {target}", file=sys.stderr)
        return str(target)
    return None


def install_from_direct_url():
    """Windows: release asset via the plain download URL (no GitHub API rate limit)."""
    if os.name != "nt":
        return None
    data = _get(f"https://github.com/{REPO}/releases/latest/download/pict.exe")
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    target = BIN_DIR / EXE
    target.write_bytes(data)
    print(f"PICT 설치 (latest release): {target}", file=sys.stderr)
    return str(target)


def install_from_source():
    for tool in ("git", "cmake"):
        if not shutil.which(tool):
            return None
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "pict"
        subprocess.run(["git", "clone", "--depth", "1", f"https://github.com/{REPO}.git", str(src)], check=True)
        subprocess.run(["cmake", "-S", str(src), "-B", str(src / "build"), "-DCMAKE_BUILD_TYPE=Release"], check=True)
        subprocess.run(["cmake", "--build", str(src / "build"), "--config", "Release"], check=True)
        built = next((p for p in (src / "build").rglob(EXE) if p.is_file()), None)
        if not built:
            return None
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        target = BIN_DIR / EXE
        shutil.copy2(built, target)
        print(f"PICT 소스 빌드 설치: {target}", file=sys.stderr)
        return str(target)


def ensure_pict():
    p = find_pict()
    if p:
        return p
    for installer in (install_from_direct_url, install_from_release, install_from_source):
        try:
            p = installer()
        except Exception as e:  # network / build failures fall through to the next method
            print(f"{installer.__name__} 실패: {e}", file=sys.stderr)
            p = None
        if p:
            return p
    raise SystemExit(
        "PICT를 설치하지 못했습니다. https://github.com/microsoft/pict 에서 직접 받아 "
        f"PATH에 두거나 PICT_PATH 환경변수로 지정하세요. (예상 위치: {BIN_DIR / EXE})\n"
        "PICT 없이 페어와이즈 케이스를 손으로 만들지 마세요."
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", nargs="?")
    ap.add_argument("--order", type=int, default=2)
    ap.add_argument("--seed", type=int, help="/r:seed 로 무작위화 (재현용 시드)")
    ap.add_argument("--out-json")
    ap.add_argument("--out-tsv")
    ap.add_argument("--install-only", action="store_true")
    args = ap.parse_args()

    pict = ensure_pict()
    if args.install_only:
        print(pict)
        return
    if not args.model:
        ap.error("model 파일이 필요합니다.")

    cmd = [pict, args.model, f"/o:{args.order}"]
    if args.seed is not None:
        cmd.append(f"/r:{args.seed}")
    res = subprocess.run(cmd, capture_output=True)
    out = res.stdout.decode("utf-8", errors="replace")
    if res.returncode != 0:
        sys.stderr.write(res.stderr.decode("utf-8", errors="replace"))
        raise SystemExit(f"PICT 실행 실패 (exit {res.returncode})")

    lines = [l for l in out.splitlines() if l.strip()]
    header = lines[0].split("\t")
    rows = [dict(zip(header, l.split("\t"))) for l in lines[1:]]

    if args.out_tsv:
        Path(args.out_tsv).write_text(out, encoding="utf-8")
    result = {"model": Path(args.model).read_text(encoding="utf-8"), "order": args.order,
              "seed": args.seed, "parameters": header, "rows": rows, "row_count": len(rows)}
    if args.out_json:
        Path(args.out_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)
    print(f"# {len(rows)} rows, order={args.order}", file=sys.stderr)


if __name__ == "__main__":
    main()
