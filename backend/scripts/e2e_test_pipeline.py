"""
Kiểm thử End-to-End luồng AI qua API thật (server FastAPI đang chạy):

    Ứng viên nộp CV (POST /api/applications/apply)
    → BackgroundTasks: đọc PDF → làm sạch → AI bóc tách → Semantic match → Hybrid score → câu hỏi phỏng vấn
    → HR xem kết quả (GET /api/applications/{id}/ai-analysis)

Để chạy toàn bộ kiểm thử backend kèm báo cáo có mốc thời gian, dùng scripts/run_backend_tests.py.
Script này dùng khi chỉ muốn xem nhanh kết quả AI trên màn hình.

Chạy (server phải đang chạy ở cửa sổ khác: python -m uvicorn app.main:app):
    python scripts/e2e_test_pipeline.py                 # 3 CV mẫu Mục 8.1 + CV thật trong uploads/cv
    python scripts/e2e_test_pipeline.py --only-samples  # chỉ 3 CV mẫu
    python scripts/e2e_test_pipeline.py --cleanup       # xóa toàn bộ dữ liệu test (email test.*@example.com)

Dữ liệu test dùng email dạng test.<tên>.<mã lần chạy>@example.com để chạy lại nhiều lần không bị trùng.
"""
import argparse
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR.parent / ".env")

SAMPLE_DIR = BACKEND_DIR / "tests" / "fixtures" / "sample_cvs"
REAL_CV_DIR = BACKEND_DIR / "uploads" / "cv"

HR_EMAIL = os.getenv("E2E_HR_EMAIL", "hr@smartrecruit.com")
HR_PASSWORD = os.getenv("E2E_HR_PASSWORD", "admin123")
TEST_EMAIL_PATTERN = "test.%@example.com"
TEST_JOB_TITLE_PATTERN = "[TEST]%"
INTERVIEW_GRACE_SECONDS = 120
AI_FINISHED_STATUSES = ("done", "partial", "failed")

# (tên file, họ tên, job_id, kỳ vọng) — job 1: Backend Python/FastAPI, job 2: Frontend VueJS
SAMPLE_CASES = [
    ("CV1_phu_hop_backend_python.pdf", "Nguyễn Minh Khoa", 1, "> 85"),
    ("CV2_trai_nganh_ke_toan.pdf", "Trần Thị Hồng Nhung", 1, "< 40"),
    ("CV3_dong_nghia_server_side.pdf", "Lê Hoàng Phúc", 1, "semantic"),
]
REAL_CASES = [
    ("Hung-resume.pdf", "Lê Viết Hưng", 1, None),
    ("Nguyen_Van_Huy_CV.pdf", "Nguyễn Văn Huy", 1, None),
    ("resume (1).pdf", "Abhinav Gangwar", 1, None),
    ("Resume-Nuriana.pdf", "Nuriana Santiara", 1, None),
    ("resume.pdf", "Steven Lara", 1, None),
    ("Hung-resume.pdf", "Lê Viết Hưng", 2, None),
    ("Nguyen_Van_Huy_CV.pdf", "Nguyễn Văn Huy", 2, None),
]


def login(client: httpx.Client) -> str:
    resp = client.post("/api/auth/login", data={"username": HR_EMAIL, "password": HR_PASSWORD})
    resp.raise_for_status()
    return resp.json()["access_token"]


def apply(client: httpx.Client, path: Path, full_name: str, job_id: int, run_tag: str) -> int:
    slug = "".join(c for c in path.stem.lower() if c.isalnum())[:20]
    email = f"test.{slug}.{run_tag}@example.com"
    with open(path, "rb") as f:
        resp = client.post(
            "/api/applications/apply",
            data={"job_id": job_id, "full_name": full_name, "email": email, "phone": "0900000000"},
            files={"cv_file": (path.name, f, "application/pdf")},
        )
    if resp.status_code != 201:
        raise RuntimeError(f"Nộp {path.name} thất bại: {resp.status_code} {resp.text}")
    return resp.json()["application_id"]


def wait_for_analysis(client: httpx.Client, token: str, application_id: int, timeout: int) -> dict:
    """
    Chờ tác vụ ngầm chạy xong: ai_status chuyển sang done / partial / failed (cách frontend cũng nên dùng).
    Dự phòng cho server cũ chưa có ai_status: đã chấm điểm và có câu hỏi phỏng vấn, hoặc quá INTERVIEW_GRACE_SECONDS.
    """
    deadline = time.time() + timeout
    scored_at = None
    data = {}
    while time.time() < deadline:
        resp = client.get(
            f"/api/applications/{application_id}/ai-analysis",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("ai_status") in AI_FINISHED_STATUSES:
            return data
        if "ai_status" not in data and (data.get("ai_extracted_info") or {}).get("scoring_details"):
            scored_at = scored_at or time.time()
            if data.get("interview_questions") or time.time() - scored_at > INTERVIEW_GRACE_SECONDS:
                return data
        time.sleep(3)
    data["_timeout"] = True
    return data


def evaluate_case(label: str, job_id: int, expected, data: dict, elapsed: float) -> dict:
    """
    Tóm tắt kết quả một hồ sơ và chấm đạt/không đạt theo tiêu chí trong docs/Huong dan kiem thu Backend.md.
    Dùng cho báo cáo tự động (scripts/run_backend_tests.py).
    """
    info = data.get("ai_extracted_info") or {}
    experience = info.get("experience_details") or {}
    interview = info.get("interview_details") or {}
    questions = interview.get("questions") or []
    score = data.get("matching_score")

    checks = {
        "Hoàn tất trước khi hết giờ chờ": not data.get("_timeout"),
        "ai_status = done": data.get("ai_status") == "done",
        "Có Matching Score": score is not None,
        "AI bóc tách được CV": bool(info.get("full_name")),
        "Có giải thích số năm kinh nghiệm": "final" in experience,
        "Sinh 3–5 câu hỏi phỏng vấn": 3 <= len(questions) <= 5,
    }
    if expected == "> 85":
        checks["Matching > 85"] = score is not None and score > 85
    elif expected == "< 40":
        checks["Matching < 40"] = score is not None and score < 40

    return {
        "label": label,
        "job_id": job_id,
        "application_id": data.get("application_id"),
        "expected": expected,
        "matching": score,
        "hard_filter": data.get("hard_filter_score"),
        "semantic": data.get("semantic_score"),
        "missing_skills": data.get("missing_skills") or [],
        "full_name": info.get("full_name"),
        "skills_count": len(info.get("skills") or []),
        "experience_years": experience.get("final", info.get("experience_years")),
        "experience_source": experience.get("source"),
        "experience_discrepancy": experience.get("discrepancy"),
        "extract_model": _model_label(info.get("ai_meta")),
        "questions": [q.get("question") for q in questions],
        "questions_model": _model_label(interview.get("ai_meta")),
        "elapsed": round(elapsed, 1),
        "checks": checks,
        "passed": all(checks.values()),
    }


def _model_label(meta) -> str:
    if not meta:
        return "—"
    fallback = " (dự phòng)" if any(not a.endswith(": OK") for a in meta.get("attempts", [])) else ""
    return f"{meta.get('provider')}/{meta.get('model')}{fallback}"


def check_expectation(score, expected) -> str:
    if score is None:
        return "❌ chưa có điểm"
    if expected == "> 85":
        return "✅ đạt" if score > 85 else "❌ chưa đạt"
    if expected == "< 40":
        return "✅ đạt" if score < 40 else "❌ chưa đạt"
    return ""


def print_result(label: str, job_id: int, expected, data: dict, elapsed: float) -> None:
    info = data.get("ai_extracted_info") or {}
    details = info.get("scoring_details") or {}
    print(f"\n━━ {label} → Job {job_id} (Application #{data.get('application_id')}, {elapsed:.0f}s)")
    if data.get("_timeout"):
        print("   ⚠️ Hết thời gian chờ — xem log server để biết bước nào lỗi.")
    print(f"   Matching: {data.get('matching_score')}  | Hard filter: {data.get('hard_filter_score')}"
          f"  | Semantic: {data.get('semantic_score')}  {check_expectation(data.get('matching_score'), expected)}"
          f"{' (kỳ vọng ' + expected + ')' if expected in ('> 85', '< 40') else ''}")
    if details:
        print(f"   Chi tiết: kỹ năng bắt buộc {details.get('required_skills_score')} | kinh nghiệm "
              f"{details.get('experience_score')} ({details.get('candidate_experience_years')}/"
              f"{details.get('required_experience_years')} năm) | ưu tiên {details.get('preferred_skills_score')}")
        matches = [f"{m['skill']}({m['match_type']}{'→' + m['matched_with'] if m['match_type'] in ('alias', 'semantic') else ''})"
                   for m in details.get("skill_matches", []) if m["matched"]]
        print(f"   Khớp: {', '.join(matches) or '—'}")
    print(f"   Thiếu: {', '.join(data.get('missing_skills') or []) or '—'}")
    print(f"   Gemini: {info.get('full_name') or '❌ không bóc tách được'} | {len(info.get('skills') or [])} kỹ năng"
          f" | {info.get('experience_years')} năm KN")
    if data.get("ai_summary"):
        print(f"   Tóm tắt: {data['ai_summary'][:220]}")
    interview = info.get("interview_details") or {}
    questions = interview.get("questions") or []
    if questions:
        meta = interview.get("ai_meta") or {}
        print(f"   Câu hỏi phỏng vấn ({len(questions)} câu, {meta.get('provider')}/{meta.get('model')}):")
        for i, q in enumerate(questions, 1):
            print(f"     {i}. [{q.get('category')} · {q.get('target_skill')}] {q.get('question')}")
    else:
        print("   Câu hỏi phỏng vấn: ❌ chưa có")


def cleanup() -> None:
    from sqlalchemy import text

    from app.core.database import engine

    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT id, cv_file_path FROM candidates WHERE email LIKE :p"), {"p": TEST_EMAIL_PATTERN}
        ).fetchall()
        for _, cv_path in rows:
            if cv_path and (BACKEND_DIR / cv_path).exists():
                (BACKEND_DIR / cv_path).unlink()
        conn.execute(
            text("DELETE FROM applications WHERE candidate_id IN "
                 "(SELECT id FROM candidates WHERE email LIKE :p)"), {"p": TEST_EMAIL_PATTERN})
        conn.execute(text("DELETE FROM candidates WHERE email LIKE :p"), {"p": TEST_EMAIL_PATTERN})
        # Tin tuyển dụng do smoke test tạo (tiêu đề bắt đầu bằng [TEST]); hồ sơ liên quan xóa theo khóa ngoại CASCADE
        conn.execute(text("DELETE FROM applications WHERE job_id IN (SELECT id FROM jobs WHERE title LIKE :t)"),
                     {"t": TEST_JOB_TITLE_PATTERN})
        jobs = conn.execute(text("DELETE FROM jobs WHERE title LIKE :t"), {"t": TEST_JOB_TITLE_PATTERN}).rowcount
    print(f"🧹 Đã xóa {len(rows)} ứng viên test (kèm hồ sơ ứng tuyển, tệp CV đã upload) và {jobs} tin tuyển dụng test.")


def main() -> None:
    parser = argparse.ArgumentParser(description="E2E test luồng nộp CV → AI chấm điểm")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--only-samples", action="store_true", help="Chỉ chạy 3 CV mẫu Mục 8.1")
    parser.add_argument("--timeout", type=int, default=240, help="Số giây chờ tối đa mỗi hồ sơ")
    parser.add_argument("--cleanup", action="store_true", help="Xóa dữ liệu test khỏi CSDL")
    args = parser.parse_args()

    if args.cleanup:
        cleanup()
        return

    cases = [(SAMPLE_DIR / f, n, j, e) for f, n, j, e in SAMPLE_CASES]
    if not args.only_samples:
        cases += [(REAL_CV_DIR / f, n, j, e) for f, n, j, e in REAL_CASES if (REAL_CV_DIR / f).exists()]
    missing = [str(p) for p, *_ in cases if not p.exists()]
    if missing:
        sys.exit(f"Thiếu tệp CV: {missing}. Với CV mẫu, chạy trước: python scripts/generate_sample_cvs.py")

    run_tag = time.strftime("%m%d%H%M%S")
    with httpx.Client(base_url=args.base_url, timeout=60) as client:
        try:
            client.get("/health").raise_for_status()
        except httpx.HTTPError:
            sys.exit(f"Không kết nối được server tại {args.base_url}. Hãy chạy: python -m uvicorn app.main:app")
        token = login(client)
        print(f"🔐 Đăng nhập HR thành công. Mã lần chạy: {run_tag}. Tổng {len(cases)} hồ sơ.")

        # Nộp lần lượt và chờ từng hồ sơ để log server dễ theo dõi
        for path, name, job_id, expected in cases:
            started = time.time()
            app_id = apply(client, path, name, job_id, run_tag)
            data = wait_for_analysis(client, token, app_id, args.timeout)
            print_result(path.name, job_id, expected, data, time.time() - started)

    print("\nXong. Xóa dữ liệu test bằng: python scripts/e2e_test_pipeline.py --cleanup")


if __name__ == "__main__":
    main()
