"""
Chạy toàn bộ kiểm thử backend và ghi báo cáo có mốc thời gian vào docs/Test-Reports/.

    Cấp 0 — Kiểm tra môi trường qua /health (CSDL mã hóa TLS, mô hình nhúng, nhà cung cấp AI)
    Cấp 1 — Unit test (python -m unittest, chạy offline, giả lập AI)
    Cấp 2 — Smoke test API nghiệp vụ (xác thực, tin tuyển dụng, nộp hồ sơ, lọc, Kanban)
    Cấp 3 — End-to-End luồng AI trên CV mẫu Mục 8.1 + CV thật (nộp CV → chấm điểm → câu hỏi phỏng vấn)

Server phải đang chạy ở cửa sổ khác (chế độ AI theo AI_PROVIDER của server):
    python -m uvicorn app.main:app

Chạy (tại thư mục backend):
    python scripts/run_backend_tests.py --cleanup-first              # đầy đủ, xóa dữ liệu test cũ trước
    python scripts/run_backend_tests.py --only-samples               # E2E chỉ 3 CV mẫu (6 lượt gọi AI)
    python scripts/run_backend_tests.py --note "Test sau khi sửa X"  # ghi chú vào báo cáo

Kết quả:
    docs/Test-Reports/<YYYY-MM-DD_HHMM>_backend-<chế độ AI>.md   — báo cáo chi tiết
    docs/Test-Reports/README.md                                  — thêm 1 dòng vào lịch sử các lần test
Mã thoát 0 nếu mọi kiểm tra đạt, 1 nếu có kiểm tra không đạt.
"""
import argparse
import json
import platform
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import e2e_test_pipeline as e2e  # noqa: E402
from smoke_test_api import Check, run_smoke_tests  # noqa: E402

BACKEND_DIR = SCRIPTS_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
REPORT_DIR = PROJECT_DIR / "docs" / "Test-Reports"
HISTORY_FILE = REPORT_DIR / "README.md"


# ── Thông tin môi trường ──────────────────────────────────────────────────────
def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=PROJECT_DIR, capture_output=True, text=True,
                              encoding="utf-8", timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def git_info() -> Dict[str, str]:
    dirty = [line for line in _git("status", "--porcelain").splitlines() if line.strip()]
    return {
        "commit": _git("rev-parse", "--short", "HEAD") or "?",
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD") or "?",
        "subject": _git("log", "-1", "--format=%s"),
        "uncommitted": str(len(dirty)),
        "user": _git("config", "user.name") or "?",
    }


# ── Cấp 0: /health ────────────────────────────────────────────────────────────
def preflight(health: Dict[str, Any]) -> List[Check]:
    db = health.get("database") or {}
    ai = health.get("ai_provider") or {}
    mode = ai.get("mode")
    checks = [
        Check("Môi trường", "Server phản hồi /health", health.get("status") == "healthy", health.get("status", "")),
        Check("Môi trường", "Kết nối CSDL Aiven được mã hóa TLS", bool(db.get("encrypted")),
              f"{db.get('tls_version')} {db.get('cipher')}" if db.get("encrypted") else str(db)),
        Check("Môi trường", "Mô hình nhúng đã nạp", bool(health.get("embedding_model_loaded")), ""),
        Check("Môi trường", "AI_PROVIDER hợp lệ", mode in ("cloud", "local", "auto"), str(mode)),
    ]
    if mode in ("local", "auto"):
        ollama = ai.get("ollama") or {}
        checks.append(Check("Môi trường", "Ollama sẵn sàng (đã có model)", bool(ollama.get("model_ready")),
                            f"{ollama.get('model')} @ {ollama.get('base_url')}"))
    if mode in ("cloud", "auto"):
        gemini = ai.get("gemini") or {}
        exhausted = gemini.get("exhausted_models") or {}
        available = [m for m in gemini.get("model_chain", []) if m not in exhausted]
        checks.append(Check("Môi trường", "Còn model Gemini chưa hết hạn mức", bool(available),
                            f"còn {available}; đang hết lượt: {exhausted or 'không'}"))
    return checks


# ── Cấp 1: unit test ─────────────────────────────────────────────────────────
def run_unit_tests() -> Dict[str, Any]:
    started = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        cwd=BACKEND_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    output = proc.stderr + proc.stdout
    ran = re.search(r"Ran (\d+) tests? in ([\d.]+)s", output)
    status_line = next((line for line in reversed(output.splitlines()) if line.startswith(("OK", "FAILED"))), "?")
    failures = re.findall(r"^(?:FAIL|ERROR): (.+)$", output, flags=re.M)
    return {
        "passed": proc.returncode == 0,
        "count": int(ran.group(1)) if ran else 0,
        "seconds": round(time.time() - started, 1),
        "status": status_line,
        "failures": failures,
    }


# ── Cấp 3: E2E ───────────────────────────────────────────────────────────────
def run_e2e(client: httpx.Client, token: str, run_tag: str, only_samples: bool, timeout: int) -> List[Dict[str, Any]]:
    cases = [(e2e.SAMPLE_DIR / f, n, j, ex) for f, n, j, ex in e2e.SAMPLE_CASES]
    if not only_samples:
        cases += [(e2e.REAL_CV_DIR / f, n, j, ex) for f, n, j, ex in e2e.REAL_CASES if (e2e.REAL_CV_DIR / f).exists()]
    missing = [p.name for p, *_ in cases if not p.exists()]
    if missing:
        sys.exit(f"Thiếu tệp CV: {missing}. Chạy trước: python scripts/generate_sample_cvs.py")

    results = []
    for index, (path, name, job_id, expected) in enumerate(cases, 1):
        print(f"   [{index}/{len(cases)}] {path.name} → Job {job_id} ...", end="", flush=True)
        started = time.time()
        app_id = e2e.apply(client, path, name, job_id, run_tag)
        data = e2e.wait_for_analysis(client, token, app_id, timeout)
        result = e2e.evaluate_case(path.name, job_id, expected, data, time.time() - started)
        results.append(result)
        print(f" {'✅' if result['passed'] else '❌'} matching={result['matching']} ({result['elapsed']}s)")
    return results


# ── Báo cáo ──────────────────────────────────────────────────────────────────
def _yes(ok: bool) -> str:
    return "✅" if ok else "❌"


def _cell(value: Any) -> str:
    return "—" if value is None or value == "" else str(value).replace("|", "\\|").replace("\n", " ")


def write_report(ctx: Dict[str, Any]) -> Path:
    started: datetime = ctx["started"]
    finished: datetime = ctx["finished"]
    mode = ctx["mode"]
    git = ctx["git"]
    health = ctx["health"]
    pre: List[Check] = ctx["preflight"]
    unit = ctx["unit"]
    smoke: List[Check] = ctx["smoke"]
    cases: List[Dict[str, Any]] = ctx["e2e"]

    def stage_line(name, ok, summary, seconds):
        return f"| {name} | {_yes(ok) if ok is not None else '⏭️ bỏ qua'} | {summary} | {seconds} |"

    pre_ok = all(c.passed for c in pre)
    smoke_ok = all(c.passed for c in smoke) if smoke else None
    e2e_ok = all(c["passed"] for c in cases) if cases else None
    unit_ok = unit["passed"] if unit else None
    overall = all(v is not False for v in (pre_ok, unit_ok, smoke_ok, e2e_ok))

    ai = health.get("ai_provider") or {}
    db = health.get("database") or {}
    lines = [
        f"# Báo cáo kiểm thử Backend — {started:%d/%m/%Y %H:%M}",
        "",
        f"**Kết quả chung:** {'✅ ĐẠT' if overall else '❌ CÓ KIỂM TRA KHÔNG ĐẠT'}",
        "",
        "## Thông tin lần chạy",
        "",
        "| Mục | Giá trị |",
        "| --- | --- |",
        f"| Bắt đầu | {started:%Y-%m-%d %H:%M:%S} |",
        f"| Kết thúc | {finished:%Y-%m-%d %H:%M:%S} (tổng {(finished - started).total_seconds() / 60:.1f} phút) |",
        f"| Người chạy | {git['user']} |",
        f"| Commit | `{git['commit']}` ({git['branch']}) — {_cell(git['subject'])} |",
        f"| Thay đổi chưa commit | {git['uncommitted']} tệp |",
        f"| AI_PROVIDER | `{mode}` |",
        f"| Chuỗi model Gemini | {_cell(', '.join((ai.get('gemini') or {}).get('model_chain', [])))} |",
        f"| Model Ollama | {_cell((ai.get('ollama') or {}).get('model'))} |",
        f"| CSDL | Aiven MySQL, {db.get('tls_version') or 'KHÔNG mã hóa'} |",
        f"| Python / OS | {platform.python_version()} / {platform.system()} {platform.release()} |",
        f"| Mã lần chạy (email test) | `{ctx['run_tag']}` |",
    ]
    if ctx.get("note"):
        lines.append(f"| Ghi chú | {_cell(ctx['note'])} |")

    lines += [
        "",
        "## Tổng kết",
        "",
        "| Cấp | Kết quả | Chi tiết | Thời gian (s) |",
        "| --- | --- | --- | --- |",
        stage_line("0. Môi trường (/health)", pre_ok, f"{sum(c.passed for c in pre)}/{len(pre)} đạt", "—"),
        stage_line("1. Unit test", unit_ok, f"{unit['count']} test — {unit['status']}" if unit else "—",
                   unit["seconds"] if unit else "—"),
        stage_line("2. Smoke test API", smoke_ok, f"{sum(c.passed for c in smoke)}/{len(smoke)} đạt" if smoke else "—",
                   ctx.get("smoke_seconds", "—")),
        stage_line("3. End-to-End AI", e2e_ok, f"{sum(c['passed'] for c in cases)}/{len(cases)} hồ sơ đạt" if cases else "—",
                   ctx.get("e2e_seconds", "—")),
        "",
        "## Cấp 0 — Môi trường",
        "",
        "| Kiểm tra | Kết quả | Chi tiết |",
        "| --- | --- | --- |",
        *[f"| {c.name} | {_yes(c.passed)} | {_cell(c.detail)} |" for c in pre],
    ]

    lines += ["", "## Cấp 1 — Unit test", ""]
    if unit:
        lines.append(f"`python -m unittest discover -s tests -t .` → **{unit['status']}**, "
                     f"{unit['count']} test trong {unit['seconds']}s.")
        lines += [f"- ❌ {f}" for f in unit["failures"]]
    else:
        lines.append("Bỏ qua (--skip-unit).")

    lines += ["", "## Cấp 2 — Smoke test API", ""]
    if smoke:
        lines += ["| Nhóm | Kiểm tra | Kết quả | Chi tiết |", "| --- | --- | --- | --- |"]
        lines += [f"| {c.group} | {c.name} | {_yes(c.passed)} | {_cell(c.detail)} |" for c in smoke]
    else:
        lines.append("Bỏ qua (--skip-smoke).")

    lines += ["", "## Cấp 3 — End-to-End luồng AI", ""]
    if cases:
        lines += [
            "| CV | Job | Hồ sơ | Matching | Hard | Semantic | Kỳ vọng | Kinh nghiệm (nguồn) | Bóc tách bởi | Câu hỏi | Thời gian | Đạt |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for c in cases:
            exp = c["expected"] if c["expected"] in ("> 85", "< 40") else "—"
            experience = f"{c['experience_years']} ({c['experience_source']}{', lệch' if c['experience_discrepancy'] else ''})"
            lines.append(
                f"| {_cell(c['label'])} | {c['job_id']} | #{c['application_id']} | {_cell(c['matching'])} | "
                f"{_cell(c['hard_filter'])} | {_cell(c['semantic'])} | {exp} | {experience} | {_cell(c['extract_model'])} | "
                f"{len(c['questions'])} ({_cell(c['questions_model'])}) | {c['elapsed']}s | {_yes(c['passed'])} |"
            )
        lines += ["", "### Chi tiết từng hồ sơ", ""]
        for c in cases:
            failed = [name for name, ok in c["checks"].items() if not ok]
            lines += [
                f"**{c['label']} → Job {c['job_id']} (#{c['application_id']})** — {_yes(c['passed'])}"
                f"{' — không đạt: ' + ', '.join(failed) if failed else ''}",
                "",
                f"- Ứng viên (AI bóc tách): {_cell(c['full_name'])}, {c['skills_count']} kỹ năng",
                f"- Kỹ năng bắt buộc còn thiếu: {_cell(', '.join(c['missing_skills']))}",
            ]
            lines.append("- Câu hỏi phỏng vấn:" if c["questions"] else "- Câu hỏi phỏng vấn: ❌ chưa có")
            lines += [f"  {i}. {_cell(q)}" for i, q in enumerate(c["questions"], 1)]
            lines.append("")
    else:
        lines.append("Bỏ qua (--skip-e2e).")

    lines += [
        "",
        "---",
        "Báo cáo tạo tự động bởi `backend/scripts/run_backend_tests.py`. "
        "Hướng dẫn và tiêu chí đạt: [Huong dan kiem thu Backend.md](../Huong%20dan%20kiem%20thu%20Backend.md).",
        "",
    ]

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{started:%Y-%m-%d_%H%M}_backend-{mode}.md"
    path.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "overall": overall, "unit": unit, "smoke_ok": smoke_ok, "smoke": smoke,
        "e2e_ok": e2e_ok, "cases": cases,
    }
    append_history(path, started, git, mode, summary, ctx.get("note"))
    return path


def append_history(report: Path, started: datetime, git: Dict[str, str], mode: str, s: Dict[str, Any],
                   note: Optional[str]) -> None:
    """Thêm một dòng vào bảng lịch sử docs/Test-Reports/README.md (tạo file nếu chưa có)."""
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(
            "# Lịch sử kiểm thử Backend\n\n"
            "| Thời điểm | Commit | AI_PROVIDER | Unit | Smoke API | E2E | Kết quả | Báo cáo / Ghi chú |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
    unit = s["unit"]
    smoke, cases = s["smoke"], s["cases"]
    unit_cell = f"{unit['count']} {_yes(unit['passed'])}" if unit else "—"
    smoke_cell = f"{sum(c.passed for c in smoke)}/{len(smoke)}" if smoke else "—"
    e2e_cell = f"{sum(c['passed'] for c in cases)}/{len(cases)}" if cases else "—"
    commit = f"`{git['commit']}`" + ("*" if git["uncommitted"] != "0" else "")
    note_cell = f" — {_cell(note)}" if note else ""
    row = (
        f"| {started:%Y-%m-%d %H:%M} | {commit} | `{mode}` | {unit_cell} | {smoke_cell} | {e2e_cell} | "
        f"{_yes(s['overall'])} | [{report.name}]({report.name}){note_cell} |\n"
    )
    text = HISTORY_FILE.read_text(encoding="utf-8")
    marker = "<!-- Dòng mới được thêm tự động phía trên dòng này -->"
    text = text.replace(marker, row.rstrip("\n") + "\n" + marker) if marker in text else text + row
    HISTORY_FILE.write_text(text, encoding="utf-8")


# ── Chương trình chính ────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy toàn bộ kiểm thử backend và ghi báo cáo có mốc thời gian")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--only-samples", action="store_true", help="E2E chỉ chạy 3 CV mẫu Mục 8.1")
    parser.add_argument("--cleanup-first", action="store_true", help="Xóa dữ liệu test cũ trước khi chạy")
    parser.add_argument("--skip-unit", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--skip-e2e", action="store_true")
    parser.add_argument("--timeout", type=int, default=300, help="Số giây chờ tối đa mỗi hồ sơ E2E")
    parser.add_argument("--note", default="", help="Ghi chú đưa vào báo cáo")
    args = parser.parse_args()

    started = datetime.now()
    run_tag = started.strftime("%m%d%H%M%S")
    ctx: Dict[str, Any] = {"started": started, "run_tag": run_tag, "note": args.note, "git": git_info(),
                           "unit": None, "smoke": [], "e2e": []}

    with httpx.Client(base_url=args.base_url, timeout=60) as client:
        try:
            health = client.get("/health").json()
        except httpx.HTTPError:
            sys.exit(f"Không kết nối được server tại {args.base_url}. Hãy chạy: python -m uvicorn app.main:app")
        ctx["health"] = health
        ctx["mode"] = (health.get("ai_provider") or {}).get("mode", "?")
        print(f"🕒 Bắt đầu {started:%Y-%m-%d %H:%M:%S} | AI_PROVIDER={ctx['mode']} | commit {ctx['git']['commit']}")

        ctx["preflight"] = preflight(health)
        for c in ctx["preflight"]:
            print(f"   {_yes(c.passed)} {c.name}: {c.detail}")
        if not all(c.passed for c in ctx["preflight"]):
            print("⚠️ Môi trường chưa đạt — vẫn chạy tiếp, xem báo cáo để biết chi tiết.")

        if args.cleanup_first:
            e2e.cleanup()

        if not args.skip_unit:
            print("🧪 Cấp 1 — Unit test ...")
            ctx["unit"] = run_unit_tests()
            print(f"   {_yes(ctx['unit']['passed'])} {ctx['unit']['count']} test — {ctx['unit']['status']}")

        token = e2e.login(client)
        if not args.skip_e2e:
            print("🤖 Cấp 3 — End-to-End luồng AI ...")
            t = time.time()
            ctx["e2e"] = run_e2e(client, token, run_tag, args.only_samples, args.timeout)
            ctx["e2e_seconds"] = round(time.time() - t, 1)

        if not args.skip_smoke:
            print("🔌 Cấp 2 — Smoke test API ...")
            t = time.time()
            processed = next((c["application_id"] for c in ctx["e2e"] if c["matching"] is not None), None)
            ctx["smoke"] = run_smoke_tests(client, run_tag, processed)
            ctx["smoke_seconds"] = round(time.time() - t, 1)
            for c in ctx["smoke"]:
                if not c.passed:
                    print(f"   ❌ [{c.group}] {c.name}: {c.detail}")
            print(f"   {sum(c.passed for c in ctx['smoke'])}/{len(ctx['smoke'])} đạt")

    ctx["finished"] = datetime.now()
    report = write_report(ctx)
    failed = (not all(c.passed for c in ctx["preflight"])
              or (ctx["unit"] and not ctx["unit"]["passed"])
              or any(not c.passed for c in ctx["smoke"])
              or any(not c["passed"] for c in ctx["e2e"]))
    print(f"\n{'❌ Có kiểm tra không đạt' if failed else '✅ Tất cả đạt'} — báo cáo: {report}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
