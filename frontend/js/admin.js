/**
 * js/admin.js — Bảng điều khiển HR (admin.html)
 * Mục 6: 6.1 khung trang (đăng nhập, thanh điều hướng, chọn tin tuyển dụng, khung Kanban 5 cột)
 *        6.2 form tạo / sửa tin (ô nhập kỹ năng dạng nhãn), đóng tin có xác nhận
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
  // Hết phiên khi đang mở form → đóng mọi modal (không mở lại form sửa)
  returnToJobForm = false;
  document.querySelectorAll(".modal.show").forEach((el) => bootstrap.Modal.getInstance(el)?.hide());
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

// Trang quản lý tin: làm ở mục 6.9
document.getElementById("nav-jobs").addEventListener("click", (event) => {
  event.preventDefault();
  showToast("Trang quản lý tin tuyển dụng sẽ có ở mục 6.9", "info");
});

// ===== A4: Ô nhập kỹ năng dạng nhãn =====
const TAG_MAX_LENGTH = 60;

/**
 * Biến `.tag-input` thành ô nhập nhãn: Enter / dấu phẩy để thêm, × hoặc Backspace để xóa,
 * bỏ nhãn trùng (không phân biệt hoa thường). Trả về { get, set, commit }.
 */
function createTagInput(boxEl) {
  const input = boxEl.querySelector("input");
  const kind = boxEl.dataset.kind;
  let tags = [];

  function render() {
    boxEl.querySelectorAll(".tag-chip").forEach((chip) => chip.remove());
    tags.forEach((tag, index) => {
      const chip = document.createElement("span");
      chip.className = `tag-chip ${kind}`;
      chip.append(document.createTextNode(tag));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.dataset.index = index;
      remove.setAttribute("aria-label", `Xóa ${tag}`);
      chip.appendChild(remove);
      boxEl.insertBefore(chip, input);
    });
    boxEl.classList.remove("is-invalid");
  }

  function addOne(raw) {
    const tag = String(raw ?? "").replace(/\s+/g, " ").trim().slice(0, TAG_MAX_LENGTH);
    if (!tag || tags.some((t) => t.toLowerCase() === tag.toLowerCase())) return;
    tags.push(tag);
  }

  /** Thêm phần chữ đang gõ dở (có thể chứa nhiều kỹ năng cách nhau bằng dấu phẩy). */
  function commit() {
    if (!input.value.trim()) return;
    input.value.split(/[,;\n]/).forEach(addOne);
    input.value = "";
    render();
  }

  input.addEventListener("keydown", (event) => {
    if (event.isComposing) return; // đang gõ dấu tiếng Việt bằng bộ gõ
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commit();
    } else if (event.key === "Backspace" && !input.value && tags.length) {
      tags.pop();
      render();
    }
  });
  // Dán "Python, FastAPI, MySQL" → tách thành 3 nhãn
  input.addEventListener("input", () => {
    if (/[,;\n]/.test(input.value)) commit();
  });
  input.addEventListener("blur", commit);

  boxEl.addEventListener("click", (event) => {
    const remove = event.target.closest("button[data-index]");
    if (remove) {
      tags.splice(Number(remove.dataset.index), 1);
      render();
    }
    input.focus();
  });

  return {
    get: () => [...tags],
    set(list) {
      tags = [];
      input.value = "";
      (Array.isArray(list) ? list : []).forEach(addOne);
      render();
    },
    commit,
  };
}

// ===== A4: Form tạo / sửa tin =====
const jobModalEl = document.getElementById("job-modal");
const jobModal = new bootstrap.Modal(jobModalEl);
const jobFormEl = document.getElementById("job-form");
const jobFieldsetEl = document.getElementById("job-fieldset");
const jobFormErrorEl = document.getElementById("job-form-error");
const jobTitleEl = document.getElementById("job-title");
const jobExpEl = document.getElementById("job-exp");
const jobDescriptionEl = document.getElementById("job-description");
const jobRequirementsEl = document.getElementById("job-requirements");
const requiredSkillsBoxEl = document.getElementById("job-required-skills");
const jobSaveBtn = document.getElementById("job-save-btn");
const jobCloseBtn = document.getElementById("job-close-btn");
const requiredSkills = createTagInput(requiredSkillsBoxEl);
const preferredSkills = createTagInput(document.getElementById("job-preferred-skills"));

let editingJob = null; // null = đang tạo tin mới
let jobSaving = false;

function showJobFormError(message) {
  jobFormErrorEl.querySelector("span").textContent = message;
  jobFormErrorEl.classList.toggle("d-none", !message);
}

function saveButtonHtml() {
  return editingJob
    ? '<i class="bi bi-check-lg me-1"></i>Lưu thay đổi'
    : '<i class="bi bi-check-lg me-1"></i>Đăng tin';
}

function setJobSaving(saving) {
  jobSaving = saving;
  jobFieldsetEl.disabled = saving;
  jobSaveBtn.disabled = saving;
  jobCloseBtn.disabled = saving;
  jobSaveBtn.innerHTML = saving
    ? '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Đang lưu…'
    : saveButtonHtml();
}

/** Mở form: job = null → tạo mới; job = tin đang chọn → sửa. */
function openJobForm(job = null) {
  editingJob = job;
  jobFormEl.querySelectorAll(".is-invalid").forEach((el) => el.classList.remove("is-invalid"));
  showJobFormError("");

  jobTitleEl.value = job?.title ?? "";
  jobDescriptionEl.value = job?.description ?? "";
  jobRequirementsEl.value = job?.requirements ?? "";
  jobExpEl.value = job?.experience_years_min ?? 0;
  requiredSkills.set(job?.required_skills ?? []);
  preferredSkills.set(job?.preferred_skills ?? []);

  document.getElementById("job-modal-title").textContent = job ? "Sửa tin tuyển dụng" : "Tạo tin tuyển dụng mới";
  jobFormEl.querySelectorAll(".job-edit-only").forEach((el) => el.classList.toggle("d-none", !job));
  jobCloseBtn.classList.toggle("d-none", !(job && job.status === "open"));
  setJobSaving(false);
  jobModal.show();
}

jobModalEl.addEventListener("shown.bs.modal", () => {
  if (!jobFormErrorEl.classList.contains("d-none")) return;
  jobTitleEl.focus();
});

/** Kiểm tra dữ liệu; trả về payload hoặc null (đã tô đỏ ô sai và đưa con trỏ tới ô đầu tiên). */
function readJobForm() {
  requiredSkills.commit();
  preferredSkills.commit();

  const title = jobTitleEl.value.trim();
  const description = jobDescriptionEl.value.trim();
  const requirements = jobRequirementsEl.value.trim();
  const required = requiredSkills.get();
  const expText = jobExpEl.value.trim();
  const exp = expText === "" ? 0 : Number(expText);
  const expValid = Number.isInteger(exp) && exp >= 0 && exp <= 50;

  const checks = [
    [jobTitleEl, title.length > 0],
    [requiredSkillsBoxEl, required.length > 0],
    [jobExpEl, expValid],
    [jobDescriptionEl, description.length > 0],
    [jobRequirementsEl, requirements.length > 0],
  ];
  checks.forEach(([el, ok]) => el.classList.toggle("is-invalid", !ok));
  const firstInvalid = checks.find(([, ok]) => !ok)?.[0];
  if (firstInvalid) {
    (firstInvalid === requiredSkillsBoxEl ? requiredSkillsBoxEl.querySelector("input") : firstInvalid).focus();
    return null;
  }

  return {
    title,
    description,
    requirements,
    required_skills: required,
    preferred_skills: preferredSkills.get(),
    experience_years_min: exp,
  };
}

[jobTitleEl, jobExpEl, jobDescriptionEl, jobRequirementsEl].forEach((el) => {
  el.addEventListener("input", () => el.classList.remove("is-invalid"));
});

jobFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (jobSaving) return;
  showJobFormError("");
  const payload = readJobForm();
  if (!payload) return;

  setJobSaving(true);
  try {
    const saved = editingJob
      ? await JobAPI.update(editingJob.id, payload)
      : await JobAPI.create(payload);
    jobModal.hide();
    showToast(editingJob ? `Đã lưu tin "${saved.title}"` : `Đã đăng tin "${saved.title}"`, "success");
    saveJobId(saved.id);
    loadJobs();
  } catch (err) {
    showJobFormError(err.message);
    jobFormErrorEl.scrollIntoView({ block: "nearest" });
  } finally {
    setJobSaving(false);
  }
});

document.getElementById("create-job-btn").addEventListener("click", () => openJobForm(null));
editJobBtn.addEventListener("click", () => {
  const job = selectedJob();
  if (job) openJobForm(job);
});

// ===== Đóng tin (hỏi xác nhận) =====
const closeJobModalEl = document.getElementById("close-job-modal");
const closeJobModal = new bootstrap.Modal(closeJobModalEl);
const closeJobErrorEl = document.getElementById("close-job-error");
const closeJobConfirmBtn = document.getElementById("close-job-confirm");
let returnToJobForm = false; // "Quay lại" / Esc → mở lại form sửa, giữ nguyên chữ đang gõ

function setClosingJob(closing) {
  closeJobConfirmBtn.disabled = closing;
  document.getElementById("close-job-back").disabled = closing;
  closeJobConfirmBtn.innerHTML = closing
    ? '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Đang đóng…'
    : "Đóng tin";
}

jobCloseBtn.addEventListener("click", () => {
  if (!editingJob) return;
  document.getElementById("close-job-name").textContent = editingJob.title;
  closeJobErrorEl.classList.add("d-none");
  setClosingJob(false);
  returnToJobForm = true;
  // Bootstrap không chồng 2 modal: ẩn form trước rồi mới hiện hộp xác nhận
  jobModalEl.addEventListener("hidden.bs.modal", () => closeJobModal.show(), { once: true });
  jobModal.hide();
});

document.getElementById("close-job-back").addEventListener("click", () => closeJobModal.hide());

closeJobModalEl.addEventListener("hidden.bs.modal", () => {
  if (returnToJobForm) jobModal.show();
});

closeJobConfirmBtn.addEventListener("click", async () => {
  if (!editingJob) return;
  setClosingJob(true);
  closeJobErrorEl.classList.add("d-none");
  try {
    const closed = await JobAPI.close(editingJob.id);
    returnToJobForm = false;
    closeJobModal.hide();
    showToast(`Đã đóng tin "${closed.title}"`, "success");
    saveJobId(closed.id);
    loadJobs();
  } catch (err) {
    closeJobErrorEl.textContent = err.message;
    closeJobErrorEl.classList.remove("d-none");
  } finally {
    setClosingJob(false);
  }
});

// ===== Khởi động =====
if (Auth.isLoggedIn()) {
  showDashboard();
} else {
  showLogin();
}
