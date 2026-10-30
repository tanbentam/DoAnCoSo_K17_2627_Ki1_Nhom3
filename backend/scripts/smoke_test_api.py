"""
Smoke test các API nghiệp vụ (Mục 3) qua server thật: xác thực, tin tuyển dụng, nộp hồ sơ, danh sách/lọc, Kanban.

Không kiểm tra chất lượng AI (đã có e2e_test_pipeline.py), chỉ kiểm tra hợp đồng API:
mã HTTP, phân quyền, kiểm tra dữ liệu đầu vào, bộ lọc/sắp xếp và cập nhật trạng thái.

Chạy riêng (server phải đang chạy):
    python scripts/smoke_test_api.py
Dữ liệu tạo ra: tin tuyển dụng "[TEST] ..." và ứng viên test.*@example.com — xóa bằng:
    python scripts/e2e_test_pipeline.py --cleanup
"""
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e2e_test_pipeline import HR_EMAIL, HR_PASSWORD, SAMPLE_DIR, login  # noqa: E402

SAMPLE_CV = SAMPLE_DIR / "CV1_phu_hop_backend_python.pdf"


@dataclass
class Check:
    group: str
    name: str
    passed: bool
    detail: str = ""


class SmokeRunner:
    def __init__(self, client: httpx.Client, token: str, run_tag: str):
        self.client = client
        self.auth = {"Authorization": f"Bearer {token}"}
        self.run_tag = run_tag
        self.checks: List[Check] = []

    def check(self, group: str, name: str, fn: Callable[[], Optional[str]]) -> None:
        """fn trả về chuỗi mô tả (đạt) hoặc ném AssertionError/Exception (không đạt)."""
        try:
            detail = fn() or ""
            self.checks.append(Check(group, name, True, detail))
        except Exception as e:  # ghi nhận mọi lỗi thành "không đạt", chạy tiếp các bước sau
            self.checks.append(Check(group, name, False, f"{type(e).__name__}: {e}"))

    def apply(self, job_id: int, email_slug: str, filename: str = "cv.pdf", content: Optional[bytes] = None):
        content = content if content is not None else SAMPLE_CV.read_bytes()
        return self.client.post(
            "/api/applications/apply",
            data={"job_id": job_id, "full_name": "Smoke Test", "email": f"test.smoke{email_slug}.{self.run_tag}@example.com"},
            files={"cv_file": (filename, content, "application/pdf")},
        )


def _expect(resp: httpx.Response, status: int) -> httpx.Response:
    assert resp.status_code == status, f"mong đợi HTTP {status}, nhận {resp.status_code}: {resp.text[:150]}"
    return resp


def run_smoke_tests(client: httpx.Client, run_tag: str, processed_app_id: Optional[int] = None) -> List[Check]:
    """
    Chạy toàn bộ smoke test. `processed_app_id` là hồ sơ đã được AI chấm xong (từ bước E2E) để test
    cập nhật trạng thái Kanban — tránh tranh chấp với tác vụ ngầm đang chạy trên hồ sơ vừa nộp.
    """
    token = login(client)
    r = SmokeRunner(client, token, run_tag)
    state = {}

    # ── Xác thực ────────────────────────────────────────────────────────────
    r.check("Xác thực", "Đăng nhập HR đúng mật khẩu → 200 + JWT", lambda: f"token {len(token)} ký tự")
    r.check("Xác thực", "Sai mật khẩu → 401", lambda: _expect(
        client.post("/api/auth/login", data={"username": HR_EMAIL, "password": HR_PASSWORD + "x"}), 401) and None)
    r.check("Xác thực", "API HR không gửi token → 401", lambda: _expect(client.get("/api/applications"), 401) and None)
    r.check("Xác thực", "Token giả mạo → 401", lambda: _expect(
        client.get("/api/applications", headers={"Authorization": "Bearer abc.def.ghi"}), 401) and None)

    # ── Tin tuyển dụng ──────────────────────────────────────────────────────
    job_body = {
        "title": f"[TEST] Smoke Job {run_tag}",
        "description": "Tin tuyển dụng tạo tự động bởi smoke test.",
        "requirements": "Python, FastAPI.",
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["Docker"],
        "experience_years_min": 1,
    }

    def create_job():
        job = _expect(client.post("/api/jobs", json=job_body, headers=r.auth), 201).json()
        assert job["status"] == "open", job["status"]
        state["job_id"] = job["id"]
        return f"job #{job['id']}"

    r.check("Tin tuyển dụng", "HR tạo tin mới → 201, trạng thái open", create_job)
    r.check("Tin tuyển dụng", "Tạo tin không có token → 401", lambda: _expect(client.post("/api/jobs", json=job_body), 401) and None)
    r.check("Tin tuyển dụng", "Tạo tin thiếu tiêu đề → 422", lambda: _expect(
        client.post("/api/jobs", json={k: v for k, v in job_body.items() if k != "title"}, headers=r.auth), 422) and None)

    def get_job():
        job = _expect(client.get(f"/api/jobs/{state['job_id']}"), 200).json()
        assert job["required_skills"] == ["Python", "FastAPI"], job["required_skills"]

    r.check("Tin tuyển dụng", "Xem chi tiết tin → 200, đúng dữ liệu", get_job)

    def update_job():
        job = _expect(client.put(f"/api/jobs/{state['job_id']}",
                                 json={"required_skills": ["Python", "FastAPI", "MySQL"]}, headers=r.auth), 200).json()
        assert job["required_skills"] == ["Python", "FastAPI", "MySQL"], job["required_skills"]
        assert job["title"] == job_body["title"], "PUT làm mất trường không gửi lên"

    r.check("Tin tuyển dụng", "Sửa tin (chỉ gửi trường cần đổi) → 200, giữ nguyên trường khác", update_job)
    r.check("Tin tuyển dụng", "Tin không tồn tại → 404", lambda: _expect(client.get("/api/jobs/99999999"), 404) and None)

    def open_jobs_public():
        jobs = _expect(client.get("/api/jobs/open"), 200).json()
        assert all(j["status"] == "open" for j in jobs), "có tin không ở trạng thái open"
        assert any(j["id"] == state["job_id"] for j in jobs), "không thấy tin vừa tạo"
        return f"{len(jobs)} tin đang mở"

    r.check("Tin tuyển dụng", "Danh sách việc đang mở (public, không cần token)", open_jobs_public)

    # ── Nộp hồ sơ ──────────────────────────────────────────────────────────
    def apply_ok():
        data = _expect(r.apply(state["job_id"], "ok"), 201).json()
        assert data["status"] == "applied", data["status"]
        state["app_id"] = data["application_id"]
        return f"application #{data['application_id']}"

    r.check("Nộp hồ sơ", "Nộp CV PDF hợp lệ → 201, trạng thái applied", apply_ok)
    r.check("Nộp hồ sơ", "Nộp trùng (cùng email, cùng tin) → 400",
            lambda: _expect(r.apply(state["job_id"], "ok"), 400) and None)
    r.check("Nộp hồ sơ", "Tệp sai định dạng (.txt) → 400",
            lambda: _expect(r.apply(state["job_id"], "txt", "cv.txt", b"hello"), 400) and None)
    r.check("Nộp hồ sơ", "Tệp .docx (Issue 06: chỉ nhận PDF) → 400",
            lambda: _expect(r.apply(state["job_id"], "docx", "cv.docx", b"PK\x03\x04docx"), 400) and None)
    r.check("Nộp hồ sơ", "Tệp quá 5MB → 400",
            lambda: _expect(r.apply(state["job_id"], "big", "big.pdf", b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024 + 10)), 400) and None)
    r.check("Nộp hồ sơ", "Tin không tồn tại → 404", lambda: _expect(r.apply(99999999, "nojob"), 404) and None)
    r.check("Nộp hồ sơ", "Email sai định dạng (thiếu @) → 422",
            lambda: _expect(r.client.post(
                "/api/applications/apply",
                data={"job_id": state["job_id"], "full_name": "Smoke Test", "email": f"test.smokebad.{r.run_tag}example.com"},
                files={"cv_file": ("cv.pdf", SAMPLE_CV.read_bytes(), "application/pdf")},
            ), 422) and None)

    # ── Danh sách & bộ lọc (HR) ──────────────────────────────────────────────
    def list_by_job():
        apps = _expect(client.get("/api/applications", params={"job_id": state["job_id"]}, headers=r.auth), 200).json()
        assert [a["id"] for a in apps] == [state["app_id"]], [a["id"] for a in apps]
        assert apps[0]["candidate"] is not None, "thiếu thông tin ứng viên"

    r.check("Danh sách hồ sơ", "Lọc theo job_id → đúng hồ sơ, kèm ứng viên", list_by_job)

    def sort_score_desc():
        apps = _expect(client.get("/api/applications", params={"sort_by": "score_desc"}, headers=r.auth), 200).json()
        scores = [a["matching_score"] for a in apps if a["matching_score"] is not None]
        assert scores == sorted(scores, reverse=True), "chưa sắp xếp giảm dần"
        nulls_at_end = all(a["matching_score"] is None for a in apps[len(scores):])
        assert nulls_at_end, "hồ sơ chưa có điểm không nằm cuối"
        return f"{len(scores)} hồ sơ có điểm"

    r.check("Danh sách hồ sơ", "Sắp xếp điểm cao → thấp (chưa có điểm xếp cuối)", sort_score_desc)

    def min_score_filter():
        apps = _expect(client.get("/api/applications", params={"min_score": 50}, headers=r.auth), 200).json()
        assert all(a["matching_score"] is not None and a["matching_score"] >= 50 for a in apps), "có hồ sơ < 50"
        return f"{len(apps)} hồ sơ ≥ 50"

    r.check("Danh sách hồ sơ", "Lọc min_score=50", min_score_filter)
    r.check("Danh sách hồ sơ", "min_score ngoài khoảng 0–100 → 422", lambda: _expect(
        client.get("/api/applications", params={"min_score": 150}, headers=r.auth), 422) and None)

    def detail():
        app = _expect(client.get(f"/api/applications/{state['app_id']}", headers=r.auth), 200).json()
        assert app["candidate"] and app["job"], "thiếu candidate/job"

    r.check("Danh sách hồ sơ", "Chi tiết hồ sơ kèm ứng viên và tin tuyển dụng", detail)
    r.check("Danh sách hồ sơ", "Hồ sơ không tồn tại → 404", lambda: _expect(
        client.get("/api/applications/99999999/ai-analysis", headers=r.auth), 404) and None)

    # ── Kanban (trên hồ sơ AI đã chấm xong) ─────────────────────────────────
    if processed_app_id:
        def move(status_value):
            def _move():
                app = _expect(client.patch(f"/api/applications/{processed_app_id}/status",
                                           json={"status": status_value}, headers=r.auth), 200).json()
                assert app["status"] == status_value, app["status"]
                listed = client.get("/api/applications", params={"status": status_value}, headers=r.auth).json()
                assert any(a["id"] == processed_app_id for a in listed), "lọc theo trạng thái không thấy hồ sơ"
            return _move

        for value in ("interview", "offer", "rejected", "screening"):
            r.check("Kanban", f"Kéo thẻ sang '{value}' → 200, lọc theo trạng thái thấy hồ sơ", move(value))
        r.check("Kanban", "Trạng thái không hợp lệ → 422", lambda: _expect(client.patch(
            f"/api/applications/{processed_app_id}/status", json={"status": "hired"}, headers=r.auth), 422) and None)
        r.check("Kanban", "Đổi trạng thái không có token → 401", lambda: _expect(client.patch(
            f"/api/applications/{processed_app_id}/status", json={"status": "interview"}), 401) and None)
    else:
        r.checks.append(Check("Kanban", "Cập nhật trạng thái", False, "bỏ qua: không có hồ sơ đã chấm xong"))

    # ── Tiến trình AI & tệp CV ───────────────────────────────────────────────
    def new_app_ai_status():
        app = _expect(client.get(f"/api/applications/{state['app_id']}", headers=r.auth), 200).json()
        assert app["ai_status"] in ("pending", "processing", "done", "partial"), app["ai_status"]
        return app["ai_status"]

    r.check("Tiến trình AI", "Hồ sơ vừa nộp có ai_status (pending/processing/...)", new_app_ai_status)

    if processed_app_id:
        def processed_ai_status():
            data = _expect(client.get(f"/api/applications/{processed_app_id}/ai-analysis", headers=r.auth), 200).json()
            assert data["ai_status"] == "done", f"{data['ai_status']} — {data.get('ai_error')}"

        r.check("Tiến trình AI", "Hồ sơ đã chấm xong có ai_status = done", processed_ai_status)

        def cv_download():
            resp = _expect(client.get(f"/api/applications/{processed_app_id}/cv", headers=r.auth), 200)
            assert resp.headers["content-type"] == "application/pdf", resp.headers["content-type"]
            assert resp.content.startswith(b"%PDF"), "nội dung không phải PDF"
            assert resp.headers.get("content-disposition", "").startswith("inline"), "không hiển thị inline"
            return f"{len(resp.content)} bytes"

        r.check("Tệp CV", "HR xem tệp CV gốc → 200, application/pdf, inline", cv_download)
        r.check("Tệp CV", "Xem tệp CV không có token → 401",
                lambda: _expect(client.get(f"/api/applications/{processed_app_id}/cv"), 401) and None)
    r.check("Tệp CV", "Tệp CV của hồ sơ không tồn tại → 404",
            lambda: _expect(client.get("/api/applications/99999999/cv", headers=r.auth), 404) and None)

    # ── Đóng tin ────────────────────────────────────────────────────────────
    def close_job():
        job = _expect(client.patch(f"/api/jobs/{state['job_id']}/close", headers=r.auth), 200).json()
        assert job["status"] == "closed", job["status"]
        assert all(j["id"] != state["job_id"] for j in client.get("/api/jobs/open").json()), "tin đã đóng vẫn hiện"

    r.check("Tin tuyển dụng", "Đóng tin → closed, biến mất khỏi danh sách public", close_job)
    r.check("Nộp hồ sơ", "Nộp vào tin đã đóng → 400", lambda: _expect(r.apply(state["job_id"], "closed"), 400) and None)

    return r.checks


def main() -> None:
    run_tag = time.strftime("%m%d%H%M%S")
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=60) as client:
        checks = run_smoke_tests(client, run_tag)
    for c in checks:
        print(f"{'✅' if c.passed else '❌'} [{c.group}] {c.name}{' — ' + c.detail if c.detail else ''}")
    failed = sum(not c.passed for c in checks)
    print(f"\n{len(checks) - failed}/{len(checks)} đạt.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
