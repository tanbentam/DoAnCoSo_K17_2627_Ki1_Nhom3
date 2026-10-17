/**
 * js/admin.js — Bảng điều khiển HR (admin.html)
 * Mục 6: 6.1 khung trang (đăng nhập, thanh điều hướng, chọn tin tuyển dụng, khung Kanban 5 cột)
 */

// 5 cột khớp 5 trạng thái của backend (nhóm chốt 17/10/2026: tách offer và rejected)
const KANBAN_COLUMNS = [
  { status: "applied",   label: "Mới nộp",           dot: "bg-secondary", badge: "bg-secondary-lt", hint: "Hồ sơ mới, AI đang xử lý" },
  { status: "screening", label: "Sàng lọc",          dot: "bg-azure",     badge: "bg-azure-lt" },
  { status: "interview", label: "Phỏng vấn",         dot: "bg-purple",    badge: "bg-purple-lt" },
  { status: "offer",     label: "Đề nghị nhận việc", dot: "bg-green",     badge: "bg-green-lt" },
  { status: "rejected",  label: "Từ chối",           dot: "bg-red",       badge: "bg-red-lt" },
];

const SELECTED_JOB_KEY = "sr_admin_job";

const loginViewEl = document.getElementById("view-login");
const dashboardViewEl = document.getElementById("view-dashboard");
const loginFormEl = document.getElementById("login-form");
const loginEmailEl = document.getElementById("login-email");
const loginPasswordEl = document.getElementById("login-password");
const loginErrorEl = document.getElementById("login-error");
const loginSubmitEl = document.getElementById("login-submit");
const togglePasswordEl = document.getElementById("login-toggle-password");

const jobSelectEl = document.getElementById("job-select");
const jobMetaEl = document.getElementById("job-meta");
const boardEl = document.getElementById("kanban-board");
const editJobBtn = document.getElementById("edit-job-btn");

let jobs = [];
let lastEmail = "";
let jobsRequestId = 0; // bỏ kết quả của lần tải cũ khi đã bấm "Tải lại" lần nữa

// ===== Ghi nhớ tin đang chọn (localStorage có thể bị chặn → bỏ qua) =====
function getSavedJobId() {
  try { return Number(localStorage.getItem(SELECTED_JOB_KEY)) || null; } catch { return null; }
}

function saveJobId(id) {
  try { localStorage.setItem(SELECTED_JOB_KEY, String(id)); } catch { /* không lưu được thì thôi */ }
}

// ===== A1: Đăng nhập / đăng xuất =====
function showLoginError(message) {
  loginErrorEl.querySelector("span").textContent = message;
  loginErrorEl.classList.toggle("d-none", !message);
}

/** Về màn hình đăng nhập; message hiện trong khung lỗi (VD hết phiên). */
function showLogin(message = "") {
  dashboardViewEl.classList.add("d-none");
  loginViewEl.classList.remove("d-none");
  document.title = "Đăng nhập — SmartRecruit AI";
  loginPasswordEl.value = "";
  // Hết phiên thì api.js đã xóa email khỏi localStorage → điền lại email vừa dùng
  if (!loginEmailEl.value) loginEmailEl.value = Auth.getEmail() ?? lastEmail;
  showLoginError(message);
  (loginEmailEl.value ? loginPasswordEl : loginEmailEl).focus();
}

function showDashboard() {
  loginViewEl.classList.add("d-none");
  dashboardViewEl.classList.remove("d-none");
  document.title = "SmartRecruit AI — HR Dashboard";

  const email = Auth.getEmail() ?? "";
  lastEmail = email;
  document.querySelectorAll(".user-email").forEach((el) => { el.textContent = email; });
  document.getElementById("user-avatar").textContent = (email.trim()[0] ?? "H").toUpperCase();

  loadJobs();
}

function setLoginLoading(loading) {
  loginSubmitEl.disabled = loading;
  loginSubmitEl.innerHTML = loading
    ? '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Đang đăng nhập…'
    : '<i class="bi bi-box-arrow-in-right me-1"></i>Đăng nhập';
}

loginFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  showLoginError("");

  const email = loginEmailEl.value.trim();
  const password = loginPasswordEl.value;
  loginEmailEl.classList.toggle("is-invalid", !loginEmailEl.checkValidity() || !email);
  loginPasswordEl.classList.toggle("is-invalid", !password);
  if (!email || !loginEmailEl.checkValidity() || !password) {
    loginFormEl.querySelector(".is-invalid")?.focus();
    return;
  }

  setLoginLoading(true);
  try {
    await AuthAPI.login(email, password);
    loginFormEl.reset();
    showDashboard();
  } catch (err) {
    showLoginError(err.message);
    loginPasswordEl.select();
  } finally {
    setLoginLoading(false);
  }
});

[loginEmailEl, loginPasswordEl].forEach((input) => {
  input.addEventListener("input", () => input.classList.remove("is-invalid"));
});

togglePasswordEl.addEventListener("click", () => {
  const show = loginPasswordEl.type === "password";
  loginPasswordEl.type = show ? "text" : "password";
  togglePasswordEl.setAttribute("aria-pressed", String(show));
  togglePasswordEl.setAttribute("aria-label", show ? "Ẩn mật khẩu" : "Hiện mật khẩu");
  togglePasswordEl.querySelector("i").className = show ? "bi bi-eye-slash" : "bi bi-eye";
});

document.getElementById("logout-btn").addEventListener("click", () => {
  AuthAPI.logout();
  jobs = [];
  showLogin();
  showToast("Đã đăng xuất", "info");
});

// API HR trả 401 (thiếu / hết hạn token) → api.js đã xóa token, gọi hàm này
Auth.onUnauthorized = () => showLogin("Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.");

// ===== A3: Chọn tin tuyển dụng =====
/** Tin đang mở lên trước, trong mỗi nhóm tin mới nhất lên trước. */
function sortJobs(list) {
  return [...list].sort((a, b) =>
    (a.status === "open" ? 0 : 1) - (b.status === "open" ? 0 : 1)
    || String(b.created_at ?? "").localeCompare(String(a.created_at ?? ""))
    || b.id - a.id);
}

function selectedJob() {
  return jobs.find((j) => j.id === Number(jobSelectEl.value)) ?? null;
}

function renderJobSelect(selectedId) {
  jobSelectEl.innerHTML = "";
  jobs.forEach((job) => {
    const option = document.createElement("option");
    option.value = job.id;
    option.textContent = job.status === "open" ? job.title : `[Đã đóng] ${job.title}`;
    jobSelectEl.appendChild(option);
  });
  jobSelectEl.value = String(selectedId);
  jobSelectEl.disabled = false;
}

function renderJobMeta(job) {
  if (!job) {
    jobMetaEl.innerHTML = "";
    return;
  }
  const isOpen = job.status === "open";
  const exp = Number(job.experience_years_min) > 0
    ? `Từ ${escapeHtml(job.experience_years_min)} năm kinh nghiệm`
    : "Không yêu cầu kinh nghiệm";
  jobMetaEl.innerHTML = `
    <span class="badge ${isOpen ? "bg-green-lt" : "bg-secondary-lt"}">${isOpen ? "Đang mở" : "Đã đóng"}</span>
    <span class="stat-pill"><i class="bi bi-calendar3 me-1"></i>Đăng ${escapeHtml(formatDate(job.created_at, false))}</span>
    <span class="stat-pill"><i class="bi bi-award me-1"></i>${exp}</span>`;
}

/** Khung 5 cột rỗng; mục 6.3 sẽ đổ thẻ ứng viên vào `.kanban-list`. */
function renderBoard() {
  boardEl.innerHTML = `
    <div class="kanban-board">
      ${KANBAN_COLUMNS.map((col) => `
        <section class="kanban-col" data-status="${col.status}" aria-label="${col.label}">
          <div class="col-title">
            <span class="col-dot ${col.dot}"></span>${col.label}
            <span class="badge ${col.badge} col-count">0</span>
          </div>
          ${col.hint ? `<p class="col-hint">${col.hint}</p>` : ""}
          <div class="kanban-list" data-status="${col.status}">
            <div class="text-center text-secondary small py-4 kanban-empty">
              <i class="bi bi-inbox d-block fs-3 mb-1"></i>Chưa có hồ sơ
            </div>
          </div>
        </section>`).join("")}
    </div>`;
}

function onJobChanged() {
  const job = selectedJob();
  if (!job) return;
  saveJobId(job.id);
  renderJobMeta(job);
  editJobBtn.disabled = false;
  renderBoard();
}

async function loadJobs() {
  const requestId = ++jobsRequestId;
  jobSelectEl.disabled = true;
  editJobBtn.disabled = true;
  jobSelectEl.innerHTML = "<option>Đang tải tin tuyển dụng…</option>";
  renderJobMeta(null);
  renderState(boardEl, "loading", { message: "Đang tải tin tuyển dụng…" });

  try {
    const data = await JobAPI.list();
    if (requestId !== jobsRequestId) return;
    jobs = sortJobs(Array.isArray(data) ? data : []);
  } catch (err) {
    if (requestId !== jobsRequestId) return;
    jobs = [];
    jobSelectEl.innerHTML = "<option>Không tải được tin tuyển dụng</option>";
    renderState(boardEl, "error", {
      message: "Không tải được danh sách tin tuyển dụng",
      hint: err.message,
      onRetry: loadJobs,
    });
    return;
  }

  if (!jobs.length) {
    jobSelectEl.innerHTML = "<option>Chưa có tin tuyển dụng</option>";
    renderState(boardEl, "empty", {
      message: "Chưa có tin tuyển dụng nào",
      hint: "Bấm \"Tạo tin mới\" để đăng tin đầu tiên.",
    });
    return;
  }

  // Ưu tiên tin đã chọn lần trước; không còn thì chọn tin mới nhất đang mở
  const saved = getSavedJobId();
  const initial = jobs.find((j) => j.id === saved) ?? jobs[0];
  renderJobSelect(initial.id);
  onJobChanged();
}

jobSelectEl.addEventListener("change", onJobChanged);
document.getElementById("reload-btn").addEventListener("click", loadJobs);

// Tạo / sửa tin: làm ở mục 6.2
document.getElementById("create-job-btn").addEventListener("click", () => {
  showToast("Form tạo tin tuyển dụng sẽ có ở mục 6.2", "info");
});
editJobBtn.addEventListener("click", () => {
  showToast("Form sửa tin tuyển dụng sẽ có ở mục 6.2", "info");
});
document.getElementById("nav-jobs").addEventListener("click", (event) => {
  event.preventDefault();
  showToast("Trang quản lý tin tuyển dụng sẽ có ở mục 6.2", "info");
});

// ===== Khởi động =====
if (Auth.isLoggedIn()) {
  showDashboard();
} else {
  showLogin();
}
