"""
Kiểm thử End-to-End luồng AI qua API thật (server FastAPI đang chạy):

    Ứng viên nộp CV (POST /api/applications/apply)
    → BackgroundTasks: đọc PDF → làm sạch → Gemini bóc tách → Semantic match → Hybrid score
    → HR xem kết quả (GET /api/applications/{id}/ai-analysis)

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
INTERVIEW_GRACE_SECONDS = 120

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
    Chờ tác vụ ngầm chạy xong: đã chấm điểm (scoring_details) và đã sinh câu hỏi phỏng vấn (bước cuối, Mục 4.8).
    Nếu chấm điểm xong mà quá INTERVIEW_GRACE_SECONDS vẫn chưa có câu hỏi (AI lỗi) thì trả kết quả hiện có.
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
        if (data.get("ai_extracted_info") or {}).get("scoring_details"):
            scored_at = scored_at or time.time()
            if data.get("interview_questions") or time.time() - scored_at > INTERVIEW_GRACE_SECONDS:
                return data
        time.sleep(3)
    data["_timeout"] = True
    return data


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
    print(f"🧹 Đã xóa {len(rows)} ứng viên test cùng hồ sơ ứng tuyển và tệp CV đã upload.")


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
