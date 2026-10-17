/**
 * js/admin.js — Bảng điều khiển HR (admin.html)
 * Mục 6: 6.1 khung trang (đăng nhập, thanh điều hướng, chọn tin tuyển dụng, khung Kanban 5 cột)
 *        6.2 form tạo / sửa tin (ô nhập kỹ năng dạng nhãn), đóng tin có xác nhận
 *        6.3–6.6 bảng Kanban 5 cột, thẻ ứng viên, kéo thả SortableJS + gọi API đổi trạng thái
 *        6.7–6.8 modal hồ sơ chi tiết: kết quả AI (5 tab), kỹ năng, câu hỏi phỏng vấn, CV gốc
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
  // Modal đang chạy hiệu ứng mở thì Bootstrap bỏ qua hide() → đóng lại ngay khi mở xong
  document.querySelectorAll(".modal").forEach((el) => {
    const modal = bootstrap.Modal.getInstance(el);
    if (!modal) return;
    modal.hide();
    el.addEventListener("shown.bs.modal", () => {
      if (!loginViewEl.classList.contains("d-none")) modal.hide();
    }, { once: true });
  });
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
  if (detailAppId === id) renderDetailHeader();

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
    if (detailAppId === id) renderDetailHeader();
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

// ===== A9, A10: Modal hồ sơ chi tiết + đánh giá AI (6.7, 6.8) =====
const detailModalEl = document.getElementById("detail-modal");
const detailModal = new bootstrap.Modal(detailModalEl);
const detailAlertEl = document.getElementById("detail-alert");
const detailPanes = {
  overview: document.getElementById("pane-overview"),
  skills: document.getElementById("pane-skills"),
  exp: document.getElementById("pane-exp"),
  questions: document.getElementById("pane-questions"),
  cv: document.getElementById("pane-cv"),
};

const QUESTION_CATEGORIES = {
  skill_gap:          { label: "Kỹ năng còn thiếu",  badge: "bg-red-lt" },
  skill_verification: { label: "Kiểm chứng kỹ năng", badge: "bg-blue-lt" },
  experience:         { label: "Kinh nghiệm",         badge: "bg-purple-lt" },
  behavioral:         { label: "Tình huống",          badge: "bg-green-lt" },
};
const SCORE_COLORS = { "badge-high": "var(--sr-score-high)", "badge-medium": "var(--sr-score-medium)", "badge-low": "var(--sr-score-low)" };

let detailAppId = null;
let detailRequestId = 0;
let detailCvUrl = null;   // object URL của CV đang xem, thu hồi khi đóng modal
let detailCvLoaded = false;

/** Số kiểu Việt Nam: 5.3 → "5,3". */
function formatNumber(value, digits = 1) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString("vi-VN", { maximumFractionDigits: digits }) : "";
}

/** Mốc thời gian trong CV: "2023-03" → "03/2023", "present" → "nay". */
function formatPeriod(value) {
  const s = String(value ?? "").trim();
  if (!s) return "?";
  if (/^(present|now|current|hiện tại|nay)$/i.test(s)) return "nay";
  const m = s.match(/^(\d{4})-(\d{2})/);
  return m ? `${m[2]}/${m[1]}` : s;
}

/** Danh sách nhãn; rỗng thì hiện câu thay thế. */
function chipsHtml(list, className, emptyText) {
  const items = (Array.isArray(list) ? list : []).filter((x) => x !== null && x !== undefined && x !== "");
  if (!items.length) return `<p class="text-secondary small mb-0">${emptyText}</p>`;
  return `<div class="d-flex flex-wrap gap-2">${items.map((x) => `<span class="${className}">${escapeHtml(x)}</span>`).join("")}</div>`;
}

function detailApp() {
  return applications.find((a) => a.id === detailAppId) ?? null;
}

/** Đầu modal: tên, vị trí, ngày nộp, cột hiện tại, menu chuyển cột. */
function renderDetailHeader(analysis = null) {
  const app = detailApp();
  const name = app?.candidate?.full_name ?? analysis?.candidate_name ?? `Hồ sơ #${detailAppId}`;
  const jobTitle = analysis?.job_title ?? selectedJob()?.title ?? "";
  document.getElementById("detail-name").textContent = name;
  document.getElementById("detail-avatar").textContent = (String(name).match(/\p{L}/u)?.[0] ?? "?").toUpperCase(); // bỏ qua ký tự như "[" trong "[TEST]"
  document.getElementById("detail-sub").innerHTML =
    `Ứng tuyển: <b>${escapeHtml(jobTitle)}</b>${app?.created_at ? ` · Nộp ${escapeHtml(formatDate(app.created_at))}` : ""}`;

  const status = app?.status ?? analysis?.status;
  const col = columnOf(status);
  const statusEl = document.getElementById("detail-status");
  statusEl.className = `badge ${col.badge}`;
  statusEl.innerHTML = `<span class="col-dot ${col.dot} d-inline-block me-1"></span>${col.label}${savingIds.has(detailAppId) ? '<span class="spinner-border spinner-border-sm ms-2 card-spinner" role="status"></span>' : ""}`;

  document.getElementById("detail-move-btn").disabled = !app || savingIds.has(detailAppId);
  document.getElementById("detail-move-menu").innerHTML = '<span class="dropdown-header">Chuyển sang</span>'
    + KANBAN_COLUMNS.filter((c) => c.status !== col.status)
      .map((c) => `<button type="button" class="dropdown-item" data-detail-move="${c.status}"><span class="col-dot ${c.dot} me-2"></span>${c.label}</button>`)
      .join("");
}

document.getElementById("detail-move-menu").addEventListener("click", (event) => {
  const btn = event.target.closest("[data-detail-move]");
  if (btn && detailAppId !== null) moveApplication(detailAppId, btn.dataset.detailMove);
});

function setTabCount(tabId, text, badgeClass) {
  const el = document.querySelector(`#${tabId} .tab-count`);
  el.className = text ? `tab-count badge ${badgeClass} ms-1` : "tab-count";
  el.textContent = text;
}

/** Thông báo đầu modal theo `ai_status`. */
function renderDetailAlert(d) {
  const error = d.ai_error ? escapeHtml(d.ai_error) : "";
  const map = {
    pending:    `<div class="alert alert-info d-flex align-items-center gap-2 mt-3 mb-0" role="status"><span class="spinner-border spinner-border-sm"></span>Hồ sơ đang chờ AI chấm. Kết quả sẽ tự hiện khi chấm xong.</div>`,
    processing: `<div class="alert alert-info d-flex align-items-center gap-2 mt-3 mb-0" role="status"><span class="spinner-border spinner-border-sm"></span>AI đang chấm hồ sơ này (khoảng 30–40 giây). Kết quả sẽ tự hiện khi chấm xong.</div>`,
    partial:    `<div class="alert alert-warning d-flex align-items-center gap-2 mt-3 mb-0" role="status"><i class="bi bi-exclamation-triangle-fill"></i>Kết quả AI chưa đầy đủ${error ? `: ${error}` : "."}</div>`,
    failed:     `<div class="alert alert-danger d-flex align-items-center gap-2 mt-3 mb-0" role="alert"><i class="bi bi-x-circle-fill"></i>AI không chấm được hồ sơ này${error ? `: ${error}` : "."} Vẫn xem được CV gốc.</div>`,
  };
  detailAlertEl.innerHTML = map[d.ai_status] ?? "";
}

/** Tab 1 – Tổng quan: điểm tổng, 2 điểm thành phần, tóm tắt AI, liên hệ, nguồn AI. */
function overviewHtml(d, app) {
  const info = d.ai_extracted_info ?? {};
  const score = formatScore(d.matching_score);
  const color = score === null ? "#c5ccd6" : SCORE_COLORS[scoreClass(d.matching_score)];
  const bar = (label, value, cls) => {
    const v = formatScore(value);
    return `
      <div class="d-flex justify-content-between metric-label"><span>${label}</span><b class="text-body">${v ?? "—"}</b></div>
      <div class="progress progress-sm mb-2"><div class="progress-bar ${cls}" style="width:${v ?? 0}%"></div></div>`;
  };
  const contact = [
    ["bi-envelope", info.email ?? app?.candidate?.email],
    ["bi-telephone", info.phone ?? app?.candidate?.phone],
    ["bi-geo-alt", info.location],
    ["bi-person-badge", info.current_title],
  ].filter(([, v]) => v);
  const meta = info.ai_meta;

  return `
    <div class="row g-4">
      <div class="col-12 col-md-4 text-center">
        <div class="score-ring mx-auto" style="--v:${score ?? 0};--c:${color}">
          <div><div><div class="ring-value">${score === null ? "—" : `${score}%`}</div><div class="metric-label">Matching Score</div></div></div>
        </div>
        <div class="text-start mt-3">
          ${bar("Lọc cứng (40%)", d.hard_filter_score, "bg-green")}
          ${bar("Ngữ nghĩa (60%)", d.semantic_score, "bg-blue")}
          <div class="metric-label mt-2">Công thức: ${escapeHtml(info.scoring_details?.formula ?? "0.4 × lọc cứng + 0.6 × ngữ nghĩa")}</div>
        </div>
      </div>
      <div class="col-12 col-md-8">
        <h3 class="h4"><i class="bi bi-stars text-primary me-1"></i>Tóm tắt của AI</h3>
        <p class="text-secondary jd-text">${d.ai_summary ? escapeHtml(d.ai_summary) : "Chưa có tóm tắt."}</p>
        <h3 class="h4 mt-4">Liên hệ</h3>
        ${contact.length
          ? `<div class="row g-2 small">${contact.map(([icon, v]) => `<div class="col-12 col-sm-6 text-break"><i class="bi ${icon} me-2 text-secondary"></i>${escapeHtml(v)}</div>`).join("")}</div>`
          : '<p class="text-secondary small mb-0">Chưa có thông tin</p>'}
        ${meta?.provider
          ? `<div class="metric-label mt-4"><i class="bi bi-cpu me-1"></i>Chấm bởi: ${escapeHtml(meta.provider)}${meta.model ? ` · ${escapeHtml(meta.model)}` : ""}${meta.latency_seconds ? ` · ${escapeHtml(formatNumber(meta.latency_seconds))} giây` : ""}</div>`
          : ""}
      </div>
    </div>`;
}

/** Tab 2 – Kỹ năng (6.8): đáp ứng / bắt buộc còn thiếu / ưu tiên còn thiếu. */
function skillsHtml(d) {
  const sd = d.ai_extracted_info?.scoring_details ?? {};
  const matches = new Map((sd.skill_matches ?? []).map((m) => [String(m.skill).toLowerCase(), m]));
  const matched = d.matched_skills ?? [];
  const missing = d.missing_skills ?? [];
  const missingPref = sd.missing_preferred_skills ?? [];

  const matchedHtml = matched.length
    ? `<div class="d-flex flex-wrap gap-2">${matched.map((skill) => {
        const m = matches.get(String(skill).toLowerCase());
        const indirect = m && ["semantic", "alias"].includes(m.match_type) && m.matched_with
          && String(m.matched_with).toLowerCase() !== String(skill).toLowerCase();
        return `<span class="skill-chip skill-ok">${escapeHtml(skill)}${indirect ? `<span class="skill-note">· tương đương: ${escapeHtml(m.matched_with)}</span>` : ""}</span>`;
      }).join("")}</div>`
    : '<p class="text-secondary small mb-0">Chưa có kỹ năng nào khớp.</p>';

  return `
    <h3 class="h4 mb-2"><i class="bi bi-check-circle-fill text-green me-1"></i>Kỹ năng đáp ứng <span class="text-secondary fw-normal">(${matched.length})</span></h3>
    <div class="mb-4">${matchedHtml}</div>
    <h3 class="h4 mb-2"><i class="bi bi-x-circle-fill text-red me-1"></i>Kỹ năng bắt buộc còn thiếu <span class="text-secondary fw-normal">(${missing.length})</span></h3>
    <div class="mb-4">${chipsHtml(missing, "skill-chip skill-missing", "Không thiếu kỹ năng bắt buộc nào.")}</div>
    <h3 class="h4 mb-2"><i class="bi bi-dash-circle-fill text-yellow me-1"></i>Kỹ năng ưu tiên còn thiếu <span class="text-secondary fw-normal">(${missingPref.length})</span></h3>
    ${chipsHtml(missingPref, "skill-chip skill-pref", "Không thiếu kỹ năng ưu tiên nào.")}`;
}

/** Tab 3 – Kinh nghiệm & học vấn. */
function experienceHtml(d) {
  const info = d.ai_extracted_info ?? {};
  const years = info.experience_years ?? info.experience_details?.final;
  const required = Number(info.scoring_details?.required_experience_years ?? selectedJob()?.experience_years_min ?? 0);
  const details = info.experience_details ?? {};
  const works = Array.isArray(info.work_experience) ? info.work_experience : [];
  const edus = Array.isArray(info.education) ? info.education : [];

  const yearsHtml = years === null || years === undefined
    ? '<span class="h3 mb-0 text-secondary">Chưa rõ số năm kinh nghiệm</span>'
    : `<span class="h3 mb-0">${escapeHtml(formatNumber(years))} năm kinh nghiệm</span>
       ${required > 0
         ? `<span class="badge ${Number(years) >= required ? "bg-green-lt" : "bg-red-lt"}">${Number(years) >= required ? "Đạt" : "Chưa đạt"} yêu cầu ≥ ${escapeHtml(required)} năm</span>`
         : '<span class="badge bg-secondary-lt">Tin không yêu cầu kinh nghiệm</span>'}`;

  const hasBothYears = Number.isFinite(Number(details.stated)) && details.stated !== null
    && Number.isFinite(Number(details.calculated)) && details.calculated !== null;
  const discrepancy = details.discrepancy && hasBothYears
    ?`<div class="alert alert-warning py-2 small"><i class="bi bi-exclamation-triangle me-1"></i>CV ghi <b>${escapeHtml(formatNumber(details.stated))} năm</b>, mốc thời gian các công việc cho <b>${escapeHtml(formatNumber(details.calculated))} năm</b> — cần xác minh khi phỏng vấn.</div>`
    : "";

  const worksHtml = works.length
    ? works.map((w) => `
        <div class="timeline-item">
          <div class="fw-semibold text-break">${escapeHtml(w.position ?? "Không rõ vị trí")}${w.company ? ` · ${escapeHtml(w.company)}` : ""}</div>
          <div class="metric-label">${escapeHtml(formatPeriod(w.start_date))} – ${escapeHtml(formatPeriod(w.end_date))}</div>
          ${w.description ? `<div class="small text-secondary mt-1 jd-text">${escapeHtml(w.description)}</div>` : ""}
        </div>`).join("")
    : '<p class="text-secondary small mb-0">Chưa có thông tin</p>';

  const edusHtml = edus.length
    ? edus.map((e) => `
        <div class="mb-3">
          <div class="fw-semibold text-break">${escapeHtml([e.degree, e.major].filter(Boolean).join(" · ") || "Không rõ bằng cấp")}</div>
          <div class="small text-secondary">${escapeHtml([e.institution, e.graduation_year, e.gpa ? `GPA ${e.gpa}` : ""].filter(Boolean).join(" · "))}</div>
        </div>`).join("")
    : '<p class="text-secondary small">Chưa có thông tin</p>';

  return `
    <div class="d-flex flex-wrap align-items-center gap-2 mb-2">${yearsHtml}</div>
    ${discrepancy}
    <div class="row g-4 mt-1">
      <div class="col-12 col-lg-7">
        <h3 class="h4">Quá trình làm việc</h3>
        ${worksHtml}
      </div>
      <div class="col-12 col-lg-5">
        <h3 class="h4">Học vấn</h3>
        ${edusHtml}
        <h3 class="h4">Chứng chỉ</h3>
        <div class="mb-3">${chipsHtml(info.certifications, "skill-tag", "Chưa có thông tin")}</div>
        <h3 class="h4">Ngoại ngữ</h3>
        <div class="mb-3">${chipsHtml(info.languages, "skill-tag", "Chưa có thông tin")}</div>
        <h3 class="h4">Kỹ năng mềm</h3>
        ${chipsHtml(info.soft_skills, "skill-tag-outline", "Chưa có thông tin")}
      </div>
    </div>`;
}

/** Danh sách câu hỏi: ưu tiên bản chi tiết (interview_details), không có thì dùng mảng chuỗi cũ. */
function interviewQuestions(d) {
  const detailed = d.ai_extracted_info?.interview_details?.questions;
  if (Array.isArray(detailed) && detailed.length) return detailed.filter((q) => q?.question);
  return (d.interview_questions ?? []).filter(Boolean).map((q) => (typeof q === "string" ? { question: q } : q));
}

/** Tab 4 – Câu hỏi phỏng vấn (6.8): nhãn loại, kỹ năng; mở rộng xem mục đích và gợi ý câu trả lời. */
function questionsHtml(questions) {
  if (!questions.length) {
    return '<p class="text-secondary small mb-0">Chưa có câu hỏi phỏng vấn gợi ý cho hồ sơ này.</p>';
  }
  const items = questions.map((q, i) => {
    const cat = QUESTION_CATEGORIES[q.category];
    const hasMore = q.target_skill || q.purpose || q.good_answer_hints;
    const head = `${cat ? `<span class="badge ${cat.badge} flex-shrink-0">${cat.label}</span>` : ""}<span>${i + 1}. ${escapeHtml(q.question)}</span>`;
    if (!hasMore) {
      return `<div class="accordion-item question-item"><div class="accordion-header"><div class="accordion-button collapsed no-toggle">${head}</div></div></div>`;
    }
    return `
      <div class="accordion-item question-item">
        <h3 class="accordion-header">
          <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#question-${i}" aria-expanded="false" aria-controls="question-${i}">${head}</button>
        </h3>
        <div id="question-${i}" class="accordion-collapse collapse" data-bs-parent="#question-list">
          <div class="accordion-body small">
            ${q.target_skill ? `<div class="mb-1"><b>Kỹ năng:</b> <span class="skill-tag">${escapeHtml(q.target_skill)}</span></div>` : ""}
            ${q.purpose ? `<div class="mb-1"><b>Mục đích:</b> ${escapeHtml(q.purpose)}</div>` : ""}
            ${q.good_answer_hints ? `<div><b>Câu trả lời tốt:</b> ${escapeHtml(q.good_answer_hints)}</div>` : ""}
          </div>
        </div>
      </div>`;
  }).join("");
  return `
    <p class="text-secondary small">AI gợi ý dựa trên kỹ năng còn thiếu và các điểm cần kiểm chứng. Bấm vào câu hỏi để xem mục đích và gợi ý câu trả lời tốt.</p>
    <div class="accordion" id="question-list">${items}</div>`;
}

function renderDetail(d) {
  const app = detailApp();
  renderDetailHeader(d);
  renderDetailAlert(d);
  const missingCount = (d.missing_skills ?? []).length;
  const questions = interviewQuestions(d);
  setTabCount("tab-skills", missingCount ? `${missingCount} thiếu` : "", "bg-red-lt");
  setTabCount("tab-questions", questions.length ? String(questions.length) : "", "bg-blue-lt");
  detailPanes.overview.innerHTML = overviewHtml(d, app);
  detailPanes.skills.innerHTML = skillsHtml(d);
  detailPanes.exp.innerHTML = experienceHtml(d);
  detailPanes.questions.innerHTML = questionsHtml(questions);
}

/** Tải kết quả AI của hồ sơ. keepTab = true khi tự làm mới (giữ tab đang xem). */
async function loadDetail({ keepTab = false } = {}) {
  const id = detailAppId;
  const requestId = ++detailRequestId;
  if (!keepTab) {
    detailAlertEl.innerHTML = "";
    setTabCount("tab-skills", "", "");
    setTabCount("tab-questions", "", "");
    ["overview", "skills", "exp", "questions"].forEach((k) => renderState(detailPanes[k], "loading", { message: "Đang tải kết quả AI…" }));
  }
  try {
    const d = await ApplicationAPI.getAiAnalysis(id);
    if (requestId !== detailRequestId || id !== detailAppId) return;
    renderDetail(d ?? {});
  } catch (err) {
    if (requestId !== detailRequestId || err.status === 401) return;
    if (keepTab) return; // tự làm mới lỗi: giữ nội dung cũ
    detailAlertEl.innerHTML = "";
    ["overview", "skills", "exp", "questions"].forEach((k) => renderState(detailPanes[k], "error", {
      message: "Không tải được kết quả AI",
      hint: err.message,
      onRetry: () => loadDetail(),
    }));
  }
}

// ===== A10: CV gốc (cần token → fetch blob → object URL → iframe) =====
function revokeCvUrl() {
  if (detailCvUrl) URL.revokeObjectURL(detailCvUrl);
  detailCvUrl = null;
}

async function loadCv() {
  const id = detailAppId;
  detailCvLoaded = true;
  revokeCvUrl();
  renderState(detailPanes.cv, "loading", { message: "Đang tải CV gốc…" });
  try {
    const blob = await ApplicationAPI.getCvBlob(id);
    if (id !== detailAppId) return;
    detailCvUrl = URL.createObjectURL(blob);
    const isPdf = (blob.type || "").includes("pdf");
    const name = detailApp()?.candidate?.full_name ?? `ho-so-${id}`;
    detailPanes.cv.innerHTML = `
      <div class="d-flex flex-wrap justify-content-end gap-2 mb-2">
        <a class="btn btn-sm btn-outline-primary cv-open" target="_blank" rel="noopener"><i class="bi bi-box-arrow-up-right me-1"></i>Mở trong tab mới</a>
        <a class="btn btn-sm btn-outline-secondary cv-download"><i class="bi bi-download me-1"></i>Tải về</a>
      </div>
      ${isPdf
        ? '<iframe class="cv-frame" title="CV gốc"></iframe>'
        : '<div class="alert alert-info small mb-0"><i class="bi bi-info-circle me-1"></i>Tệp CV không phải PDF nên không xem trực tiếp được. Bấm "Tải về" để mở bằng phần mềm trên máy.</div>'}`;
    detailPanes.cv.querySelector(".cv-open").href = detailCvUrl;
    const download = detailPanes.cv.querySelector(".cv-download");
    download.href = detailCvUrl;
    const ext = isPdf ? ".pdf" : (blob.type || "").includes("wordprocessingml") ? ".docx" : "";
    download.download = `CV - ${name}${ext}`;
    if (isPdf) detailPanes.cv.querySelector("iframe").src = detailCvUrl;
    if (!isPdf) detailPanes.cv.querySelector(".cv-open").classList.add("d-none");
  } catch (err) {
    if (id !== detailAppId || err.status === 401) return;
    detailCvLoaded = false;
    renderState(detailPanes.cv, "error", {
      message: err.status === 404 ? "Không tìm thấy tệp CV của hồ sơ này" : "Không tải được CV gốc",
      hint: err.message,
      onRetry: loadCv,
    });
  }
}

// CV chỉ tải khi mở tab (tệp có thể lớn)
document.getElementById("tab-cv").addEventListener("shown.bs.tab", () => {
  if (!detailCvLoaded && detailAppId !== null) loadCv();
});

detailModalEl.addEventListener("hidden.bs.modal", () => {
  detailAppId = null;
  detailRequestId++;
  revokeCvUrl();
  detailPanes.cv.innerHTML = "";
});

/** Bấm vào thẻ: mở modal hồ sơ chi tiết, luôn bắt đầu ở tab Tổng quan. */
function openApplicationDetail(id) {
  if (!applications.some((a) => a.id === id)) return;
  detailAppId = id;
  detailCvLoaded = false;
  revokeCvUrl();
  detailPanes.cv.innerHTML = "";
  bootstrap.Tab.getOrCreateInstance(document.getElementById("tab-overview")).show();
  renderDetailHeader();
  loadDetail();
  detailModal.show();
}

/** Bảng tự làm mới (A8): hồ sơ đang mở vừa chấm xong / đổi trạng thái → cập nhật modal. */
function syncDetailWithBoard(previous) {
  if (detailAppId === null) return;
  const before = previous.find((a) => a.id === detailAppId);
  const after = detailApp();
  if (!after) return;
  renderDetailHeader();
  if (before && (before.ai_status !== after.ai_status || before.matching_score !== after.matching_score)) {
    loadDetail({ keepTab: true });
  }
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
    const previous = applications;
    applications = next;
    if (changed && !isDragging && !savingIds.size) renderBoard();
    syncDetailWithBoard(previous);
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
