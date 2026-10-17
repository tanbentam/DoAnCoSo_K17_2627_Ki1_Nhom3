/**
 * js/admin.js — Bảng điều khiển HR (admin.html)
 * Mục 6: 6.1 khung trang (đăng nhập, thanh điều hướng, chọn tin tuyển dụng, khung Kanban 5 cột)
 *        6.2 form tạo / sửa tin (ô nhập kỹ năng dạng nhãn), đóng tin có xác nhận
 *        6.3–6.6 bảng Kanban 5 cột, thẻ ứng viên, kéo thả SortableJS + gọi API đổi trạng thái
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
  stopPolling();
  appsRequestId++;
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

function onJobChanged() {
  const job = selectedJob();
  if (!job) return;
  saveJobId(job.id);
  renderJobMeta(job);
  editJobBtn.disabled = false;
  loadApplications();
}

// ===== A5–A8: Bảng Kanban (6.3), thẻ ứng viên (6.5), kéo thả (6.4, 6.6) =====
const POLL_INTERVAL_MS = 7000;             // A8: gọi lại khi còn thẻ AI đang chấm
const AI_RUNNING = ["pending", "processing"];

let applications = [];
let appsRequestId = 0;
let pollTimer = null;
let sortables = [];
let isDragging = false;
const savingIds = new Set(); // hồ sơ đang chờ API đổi trạng thái

function columnOf(status) {
  return KANBAN_COLUMNS.find((c) => c.status === status) ?? KANBAN_COLUMNS[0];
}

function stopPolling() {
  clearTimeout(pollTimer);
  pollTimer = null;
}

function schedulePoll() {
  stopPolling();
  if (applications.some((a) => AI_RUNNING.includes(a.ai_status))) {
    pollTimer = setTimeout(() => loadApplications({ silent: true }), POLL_INTERVAL_MS);
  }
}

/** Dòng thống kê dưới ô chọn tin: tổng hồ sơ, số hồ sơ AI đang chấm. */
function renderAppStats() {
  jobMetaEl.querySelector(".app-stats")?.remove();
  const running = applications.filter((a) => AI_RUNNING.includes(a.ai_status)).length;
  const wrap = document.createElement("span");
  wrap.className = "app-stats";
  wrap.innerHTML = `
    <span class="stat-pill"><i class="bi bi-people me-1"></i>${applications.length} hồ sơ</span>
    ${running ? `<span class="stat-pill"><i class="bi bi-hourglass-split me-1"></i>${running} đang chấm AI</span>` : ""}`;
  jobMetaEl.appendChild(wrap);
}

/** Huy hiệu góc thẻ theo `ai_status` (bảng gợi ý trong API cho Frontend.md). */
function cardBadge(app) {
  const error = escapeHtml(app.ai_error ?? "");
  switch (app.ai_status) {
    case "pending":
    case "processing":
      return `<span class="badge bg-azure-lt text-nowrap"><span class="spinner-border spinner-border-sm me-1 card-spinner" role="status"></span>${app.ai_status === "pending" ? "Chờ AI" : "Đang chấm"}</span>`;
    case "failed":
      return `<span class="badge bg-red-lt text-nowrap" title="${error}"><i class="bi bi-x-circle me-1"></i>Không chấm được</span>`;
    default: {
      const score = formatScore(app.matching_score);
      if (score === null) return '<span class="badge bg-secondary-lt" title="Chưa có điểm">—</span>';
      const warn = app.ai_status === "partial"
        ? `<i class="bi bi-exclamation-triangle-fill text-warning ms-1" title="${error || "Thiếu một phần kết quả AI"}"></i>`
        : "";
      return `<span class="d-inline-flex align-items-center"><span class="badge ${scoreClass(app.matching_score)}" title="Matching Score">${score}%</span>${warn}</span>`;
    }
  }
}

/** Thẻ ứng viên (6.5): tên, chức danh hiện tại (AI bóc tách), huy hiệu điểm, ngày nộp, menu chuyển cột. */
function cardHtml(app) {
  const name = escapeHtml(app.candidate?.full_name ?? "(Không tên)");
  const title = app.ai_extracted_info?.current_title;
  const moveItems = KANBAN_COLUMNS
    .filter((c) => c.status !== app.status)
    .map((c) => `<button type="button" class="dropdown-item" data-move="${c.status}"><span class="col-dot ${c.dot} me-2"></span>${c.label}</button>`)
    .join("");
  return `
    <article class="candidate-card${savingIds.has(app.id) ? " is-saving" : ""}" data-id="${Number(app.id)}" tabindex="0" aria-label="Hồ sơ ${name}">
      <div class="d-flex justify-content-between align-items-start gap-2">
        <div class="fw-semibold text-break card-name">${name}</div>
        <div class="flex-shrink-0">
          <div class="dropdown card-menu" data-bs-popper-config='{"strategy":"fixed"}'>
            <button type="button" class="btn btn-sm btn-ghost-secondary btn-icon card-menu-btn" data-bs-toggle="dropdown" aria-expanded="false" aria-label="Chuyển cột hồ sơ ${name}">
              <i class="bi bi-three-dots-vertical"></i>
            </button>
            <div class="dropdown-menu dropdown-menu-end">
              <span class="dropdown-header">Chuyển sang</span>
              ${moveItems}
            </div>
          </div>
        </div>
      </div>
      <div class="small text-truncate ${title ? "text-secondary" : "text-muted fst-italic"}">${title ? escapeHtml(title) : "Chưa có chức danh"}</div>
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-1 mt-2">
        ${cardBadge(app)}
        <span class="small text-muted text-nowrap" title="Ngày nộp">${escapeHtml(formatDate(app.created_at, false))}</span>
      </div>
    </article>`;
}

/** Vẽ 5 cột; thẻ trong mỗi cột giữ thứ tự API trả về (điểm cao → thấp, chưa có điểm xếp cuối). */
function renderBoard() {
  sortables.forEach((s) => s.destroy());
  sortables = [];

  const emptyNote = applications.length
    ? ""
    : `<div class="alert alert-info py-2 small d-flex align-items-center gap-2 mb-3" role="status">
         <i class="bi bi-inbox"></i>Tin này chưa có hồ sơ nào. Hồ sơ nộp từ cổng ứng viên sẽ tự hiện ở cột "Mới nộp".
       </div>`;

  boardEl.innerHTML = `${emptyNote}
    <div class="kanban-board">
      ${KANBAN_COLUMNS.map((col) => {
        const cards = applications.filter((a) => columnOf(a.status).status === col.status);
        return `
        <section class="kanban-col" data-status="${col.status}" aria-label="${col.label}">
          <div class="col-title">
            <span class="col-dot ${col.dot}"></span>${col.label}
            <span class="badge ${col.badge} col-count">${cards.length}</span>
          </div>
          ${col.hint ? `<p class="col-hint">${col.hint}</p>` : ""}
          <div class="kanban-list" data-status="${col.status}">
            ${cards.map(cardHtml).join("")}
            <div class="text-center text-secondary small py-4 kanban-empty${cards.length ? " d-none" : ""}">
              <i class="bi bi-inbox d-block fs-3 mb-1"></i>Kéo thẻ vào đây
            </div>
          </div>
        </section>`;
      }).join("")}
    </div>`;

  initSortable();
  renderAppStats();
}

/** 6.4: kéo thả giữa các cột. `sort: false` → không đổi thứ tự trong cùng cột (luôn xếp theo điểm). */
function initSortable() {
  if (typeof Sortable === "undefined") {
    showToast("Không tải được thư viện kéo thả. Dùng menu ⋮ trên thẻ để chuyển cột.", "warning");
    return;
  }
  boardEl.querySelectorAll(".kanban-list").forEach((list) => {
    sortables.push(new Sortable(list, {
      group: "kanban",
      sort: false,
      animation: 150,
      draggable: ".candidate-card",
      filter: ".is-saving, .card-menu",
      preventOnFilter: false,
      ghostClass: "sortable-ghost",
      chosenClass: "sortable-chosen",
      delay: 150,              // trên điện thoại: giữ tay một chút mới kéo, để vẫn cuộn ngang được
      delayOnTouchOnly: true,
      onStart: () => {
        isDragging = true;
        boardEl.querySelectorAll(".kanban-empty").forEach((el) => el.classList.add("d-none"));
      },
      onEnd: (evt) => {
        isDragging = false;
        const id = Number(evt.item.dataset.id);
        const to = evt.to.dataset.status;
        if (evt.from === evt.to) {
          renderBoard(); // thả lại cột cũ: hiện lại ô "Kéo thẻ vào đây"
          return;
        }
        moveApplication(id, to);
      },
    }));
  });
}

/**
 * 6.6: đổi trạng thái hồ sơ. Cập nhật giao diện ngay (thẻ sang cột mới, xếp lại theo điểm),
 * rồi gọi API; lỗi thì trả thẻ về cột cũ và báo lỗi.
 */
async function moveApplication(id, newStatus) {
  const app = applications.find((a) => a.id === id);
  if (!app || savingIds.has(id)) return;
  const oldStatus = app.status;
  if (oldStatus === newStatus) {
    renderBoard();
    return;
  }

  const name = app.candidate?.full_name ?? `#${id}`;
  app.status = newStatus;
  savingIds.add(id);
  renderBoard();

  try {
    const updated = await ApplicationAPI.updateStatus(id, newStatus);
    const index = applications.findIndex((a) => a.id === id);
    if (index !== -1 && updated && typeof updated === "object") applications[index] = updated;
    showToast(`Đã chuyển "${name}" sang ${columnOf(newStatus).label}`, "success");
  } catch (err) {
    const current = applications.find((a) => a.id === id);
    if (current) current.status = oldStatus;
    if (err.status !== 401) {
      showToast(`Chưa chuyển được "${name}": ${err.message.replace(/[.\s]+$/, "")}. Thẻ đã về cột ${columnOf(oldStatus).label}.`, "danger");
    }
  } finally {
    savingIds.delete(id);
    if (!dashboardViewEl.classList.contains("d-none")) renderBoard();
  }
}

// Menu ⋮ trên thẻ (cách chuyển cột không cần kéo: bàn phím, điện thoại)
boardEl.addEventListener("click", (event) => {
  const moveBtn = event.target.closest("[data-move]");
  if (moveBtn) {
    const card = moveBtn.closest(".candidate-card");
    moveApplication(Number(card.dataset.id), moveBtn.dataset.move);
    return;
  }
  if (event.target.closest(".card-menu")) return;
  const card = event.target.closest(".candidate-card");
  if (card) openApplicationDetail(Number(card.dataset.id));
});

boardEl.addEventListener("keydown", (event) => {
  if (event.target.matches?.(".candidate-card") && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    openApplicationDetail(Number(event.target.dataset.id));
  }
});

/** Bấm vào thẻ: modal hồ sơ chi tiết làm ở mục 6.7. */
function openApplicationDetail(id) {
  const app = applications.find((a) => a.id === id);
  showToast(`Chi tiết hồ sơ "${app?.candidate?.full_name ?? id}" sẽ có ở mục 6.7`, "info");
}

/** Chuỗi so sánh để biết dữ liệu mới có khác dữ liệu đang hiện không (tránh vẽ lại khi không đổi). */
function boardSignature(list) {
  return list.map((a) => `${a.id}:${a.status}:${a.ai_status}:${a.matching_score}`).join("|");
}

/**
 * A5: tải toàn bộ hồ sơ của tin đang chọn (1 lần, điểm cao → thấp), tự chia vào cột theo `status`.
 * silent = true (gọi lại định kỳ): không hiện spinner; lỗi thì giữ bảng cũ và thử lại lần sau.
 */
async function loadApplications({ silent = false } = {}) {
  const job = selectedJob();
  if (!job) return;
  stopPolling();

  // Đang kéo thẻ hoặc chờ API đổi trạng thái: để lần sau mới vẽ lại
  if (silent && (isDragging || savingIds.size)) {
    pollTimer = setTimeout(() => loadApplications({ silent: true }), POLL_INTERVAL_MS);
    return;
  }

  const requestId = ++appsRequestId;
  if (!silent) {
    sortables.forEach((s) => s.destroy());
    sortables = [];
    jobMetaEl.querySelector(".app-stats")?.remove();
    renderState(boardEl, "loading", { message: "Đang tải hồ sơ ứng viên…" });
  }

  try {
    const data = await ApplicationAPI.list({ job_id: job.id, sort_by: "score_desc", limit: 500 });
    if (requestId !== appsRequestId) return;
    const next = Array.isArray(data) ? data : [];
    const changed = !silent || boardSignature(next) !== boardSignature(applications);
    applications = next;
    if (changed && !isDragging && !savingIds.size) renderBoard();
  } catch (err) {
    if (requestId !== appsRequestId || err.status === 401) return;
    if (silent) {
      pollTimer = setTimeout(() => loadApplications({ silent: true }), POLL_INTERVAL_MS);
      return;
    }
    applications = [];
    renderState(boardEl, "error", {
      message: "Không tải được hồ sơ ứng viên",
      hint: err.message,
      onRetry: () => loadApplications(),
    });
    return;
  }
  schedulePoll();
}

async function loadJobs() {
  const requestId = ++jobsRequestId;
  stopPolling();
  appsRequestId++; // bỏ kết quả hồ sơ của lần tải trước
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
