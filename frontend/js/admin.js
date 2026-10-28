/**
 * js/admin.js — Bảng điều khiển HR (admin.html)
 * Mục 6: 6.1 khung trang (đăng nhập, thanh điều hướng, chọn tin tuyển dụng, khung Kanban 5 cột)
 *        6.2 form tạo / sửa tin (ô nhập kỹ năng dạng nhãn), đóng tin có xác nhận
 *        6.3–6.6 bảng Kanban 5 cột, thẻ ứng viên, kéo thả SortableJS + gọi API đổi trạng thái
 *        6.7–6.8 modal hồ sơ chi tiết: kết quả AI (5 tab), kỹ năng, câu hỏi phỏng vấn, CV gốc
 *        6.9 trang quản lý tin tuyển dụng (#tin-tuyen-dung): bảng tin, lọc / tìm, Kanban / sửa / đóng tin
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
const BOARD_SORT_KEY = "sr_admin_sort";
const BOARD_MIN_SCORE_KEY = "sr_admin_min_score";

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
const boardSortEl = document.getElementById("board-sort");
const boardMinScoreEl = document.getElementById("board-min-score");

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
  showView(viewFromHash(), { initial: true });
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
    <span class="stat-pill"><i class="bi bi-award me-1"></i>${exp}</span>${job.location
      ? `<span class="stat-pill text-break"><i class="bi bi-geo-alt me-1"></i>${escapeHtml(job.location)}</span>`
      : ""}`;
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
  if (currentView === "kanban" && applications.some((a) => AI_RUNNING.includes(a.ai_status))) {
    pollTimer = setTimeout(() => loadApplications({ silent: true }), POLL_INTERVAL_MS);
  }
}

/** Dòng thống kê dưới ô chọn tin: tổng hồ sơ, số hồ sơ AI đang chấm, số hồ sơ đang hiện khi lọc điểm. */
function renderAppStats(visibleCount) {
  jobMetaEl.querySelector(".app-stats")?.remove();
  const running = applications.filter((a) => AI_RUNNING.includes(a.ai_status)).length;
  const minScore = Number(boardMinScoreEl.value) || 0;
  const wrap = document.createElement("span");
  wrap.className = "app-stats";
  wrap.innerHTML = `
    <span class="stat-pill"><i class="bi bi-people me-1"></i>${applications.length} hồ sơ</span>
    ${running ? `<span class="stat-pill"><i class="bi bi-hourglass-split me-1"></i>${running} đang chấm AI</span>` : ""}
    ${minScore ? `<span class="stat-pill"><i class="bi bi-funnel me-1"></i>Đang hiện ${visibleCount} hồ sơ từ ${minScore} điểm</span>` : ""}`;
  jobMetaEl.appendChild(wrap);
}

// ===== 7.5: Sắp xếp / lọc theo điểm (trên dữ liệu đã tải, không gọi lại API) =====
function loadBoardFilters() {
  try {
    const sort = localStorage.getItem(BOARD_SORT_KEY);
    const min = localStorage.getItem(BOARD_MIN_SCORE_KEY);
    if ([...boardSortEl.options].some((o) => o.value === sort)) boardSortEl.value = sort;
    if ([...boardMinScoreEl.options].some((o) => o.value === min)) boardMinScoreEl.value = min;
  } catch { /* không đọc được thì dùng mặc định */ }
}

function saveBoardFilters() {
  try {
    localStorage.setItem(BOARD_SORT_KEY, boardSortEl.value);
    localStorage.setItem(BOARD_MIN_SCORE_KEY, boardMinScoreEl.value);
  } catch { /* không lưu được thì thôi */ }
}

/**
 * Hồ sơ hiện trên bảng theo 2 ô "Sắp xếp" và "Điểm tối thiểu".
 * - Lọc điểm so với điểm đã làm tròn (giống huy hiệu); hồ sơ chưa có điểm bị ẩn khi đang lọc.
 * - "Điểm cao → thấp": hồ sơ chưa có điểm xếp cuối; bằng điểm thì giữ thứ tự API (mới nộp trước).
 */
function visibleApplications() {
  const minScore = Number(boardMinScoreEl.value) || 0;
  const list = minScore
    ? applications.filter((a) => (formatScore(a.matching_score) ?? -1) >= minScore)
    : [...applications];
  if (boardSortEl.value === "newest") {
    return list.sort((a, b) => String(b.created_at ?? "").localeCompare(String(a.created_at ?? "")));
  }
  return list.sort((a, b) => (b.matching_score ?? -1) - (a.matching_score ?? -1));
}

function onBoardFilterChanged() {
  saveBoardFilters();
  // Đang tải / lỗi thì chưa có bảng: lần tải xong sẽ tự áp lựa chọn mới
  if (boardEl.querySelector(".kanban-board")) renderBoard();
}

loadBoardFilters();
boardSortEl.addEventListener("change", onBoardFilterChanged);
boardMinScoreEl.addEventListener("change", onBoardFilterChanged);

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

/** Vẽ 5 cột; thẻ trong mỗi cột theo ô "Sắp xếp" / "Điểm tối thiểu" (7.5, xem visibleApplications). */
function renderBoard() {
  sortables.forEach((s) => s.destroy());
  sortables = [];

  const visible = visibleApplications();
  let emptyNote = "";
  if (!applications.length) {
    emptyNote = `<div class="alert alert-info py-2 small d-flex align-items-center gap-2 mb-3" role="status">
         <i class="bi bi-inbox"></i>Tin này chưa có hồ sơ nào. Hồ sơ nộp từ cổng ứng viên sẽ tự hiện ở cột "Mới nộp".
       </div>`;
  } else if (!visible.length) {
    emptyNote = `<div class="alert alert-info py-2 small d-flex flex-wrap align-items-center gap-2 mb-3" role="status">
         <i class="bi bi-funnel"></i>Không có hồ sơ nào từ ${Number(boardMinScoreEl.value)} điểm trở lên.
         <button type="button" class="btn btn-sm btn-outline-primary py-0" data-clear-score-filter>Hiện tất cả hồ sơ</button>
       </div>`;
  }

  boardEl.innerHTML = `${emptyNote}
    <div class="kanban-board">
      ${KANBAN_COLUMNS.map((col) => {
        const cards = visible.filter((a) => columnOf(a.status).status === col.status);
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

  boardEl.querySelector("[data-clear-score-filter]")?.addEventListener("click", () => {
    boardMinScoreEl.value = "0";
    onBoardFilterChanged();
  });
  initSortable();
  renderAppStats(visible.length);
}

/** 6.4: kéo thả giữa các cột. `sort: false` → không đổi thứ tự trong cùng cột (luôn theo ô "Sắp xếp"). */
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
        requestMove(id, to);
      },
    }));
  });
}

/**
 * 6.6: đổi trạng thái hồ sơ. Cập nhật giao diện ngay (thẻ sang cột mới, xếp lại theo điểm),
 * rồi gọi API; lỗi thì trả thẻ về cột cũ và báo lỗi.
 */
async function moveApplication(id, newStatus, extra = {}) {
  const app = applications.find((a) => a.id === id);
  if (!app || savingIds.has(id)) return false;
  const oldStatus = app.status;
  if (oldStatus === newStatus) {
    renderBoard();
    return false;
  }

  const name = app.candidate?.full_name ?? `#${id}`;
  app.status = newStatus;
  savingIds.add(id);
  renderBoard();
  if (detailAppId === id) renderDetailHeader();

  try {
    const updated = await ApplicationAPI.updateStatus(id, newStatus, extra);
    const index = applications.findIndex((a) => a.id === id);
    if (index !== -1 && updated && typeof updated === "object") applications[index] = updated;
    const emailNote = updated?.email_queued ? ", email đang được gửi tới ứng viên" : "";
    showToast(`Đã chuyển "${name}" sang ${columnOf(newStatus).label}${emailNote}`, "success");
    return true;
  } catch (err) {
    const current = applications.find((a) => a.id === id);
    if (current) current.status = oldStatus;
    if (err.status !== 401) {
      showToast(`Chưa chuyển được "${name}": ${err.message.replace(/[.\s]+$/, "")}. Thẻ đã về cột ${columnOf(oldStatus).label}.`, "danger");
    }
    return false;
  } finally {
    savingIds.delete(id);
    if (!dashboardViewEl.classList.contains("d-none")) renderBoard();
    if (detailAppId === id) renderDetailHeader();
  }
}

// ===== Mục 7: hỏi xác nhận trước khi chuyển sang cột có gửi email cho ứng viên =====
const EMAIL_STATUSES = {
  interview: { title: "Mời phỏng vấn",         bar: "bg-purple", button: "btn-primary", mail: "thư mời phỏng vấn" },
  offer:     { title: "Gửi đề nghị nhận việc", bar: "bg-green",  button: "btn-success", mail: "thư báo trúng tuyển" },
  rejected:  { title: "Từ chối hồ sơ",         bar: "bg-red",    button: "btn-danger",  mail: "thư cảm ơn, báo chưa phù hợp" },
};
const moveModalEl = document.getElementById("move-modal");
const moveModal = new bootstrap.Modal(moveModalEl);
const moveFormEl = document.getElementById("move-form");
const moveInterviewAtEl = document.getElementById("move-interview-at");
const moveLocationEl = document.getElementById("move-interview-location");
const moveSendEmailEl = document.getElementById("move-send-email");
const moveErrorEl = document.getElementById("move-error");
const moveConfirmBtn = document.getElementById("move-confirm-btn");
let pendingMove = null; // { id, status, fromDetail }
let moveSaving = false;

/** Giá trị cho <input type="datetime-local"> theo giờ máy, VD "2026-10-26T09:30". */
function toLocalInputValue(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** Chuyển cột: cột có gửi email thì mở hộp xác nhận, cột khác chuyển ngay. */
function requestMove(id, newStatus, { fromDetail = false } = {}) {
  const app = applications.find((a) => a.id === id);
  const info = EMAIL_STATUSES[newStatus];
  if (!info || !app || savingIds.has(id) || app.status === newStatus) {
    moveApplication(id, newStatus);
    return;
  }

  pendingMove = { id, status: newStatus, fromDetail };
  const name = app.candidate?.full_name ?? `#${id}`;
  const jobTitle = app.job?.title ?? selectedJob()?.title ?? "";
  document.getElementById("move-title").textContent = info.title;
  document.getElementById("move-status-bar").className = `modal-status ${info.bar}`;
  document.getElementById("move-desc").innerHTML =
    `Chuyển <b>${escapeHtml(name)}</b>${jobTitle ? ` (${escapeHtml(jobTitle)})` : ""} sang cột <b>${escapeHtml(columnOf(newStatus).label)}</b>.`;
  document.getElementById("move-mail-kind").textContent = info.mail;
  document.getElementById("move-email").textContent = app.candidate?.email ?? "ứng viên";
  moveSendEmailEl.checked = true;

  const isInterview = newStatus === "interview";
  document.getElementById("move-interview-fields").classList.toggle("d-none", !isInterview);
  moveInterviewAtEl.classList.remove("is-invalid");
  moveInterviewAtEl.value = "";
  moveInterviewAtEl.min = toLocalInputValue(new Date());
  moveLocationEl.value = app.job?.location ?? selectedJob()?.location ?? "";

  moveErrorEl.classList.add("d-none");
  moveConfirmBtn.className = `btn ${info.button}`;
  setMoveSaving(false);

  // Bootstrap không chồng 2 modal: đang mở hồ sơ chi tiết thì ẩn trước, xong việc mở lại
  if (fromDetail && detailModalEl.classList.contains("show")) {
    detailModalEl.addEventListener("hidden.bs.modal", () => moveModal.show(), { once: true });
    detailModal.hide();
  } else {
    moveModal.show();
  }
}

function setMoveSaving(saving) {
  moveSaving = saving;
  moveFormEl.querySelectorAll("input, button").forEach((el) => { el.disabled = saving; });
  moveConfirmBtn.innerHTML = saving
    ? '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Đang lưu…'
    : "Xác nhận";
}

moveInterviewAtEl.addEventListener("input", () => moveInterviewAtEl.classList.remove("is-invalid"));

moveModalEl.addEventListener("shown.bs.modal", () => {
  (pendingMove?.status === "interview" ? moveInterviewAtEl : moveConfirmBtn).focus();
});

// Đang lưu thì không cho đóng hộp (Esc, bấm nền, nút X)
moveModalEl.addEventListener("hide.bs.modal", (event) => {
  if (moveSaving) event.preventDefault();
});

moveModalEl.addEventListener("hidden.bs.modal", () => {
  const done = pendingMove;
  pendingMove = null;
  if (!dashboardViewEl.classList.contains("d-none")) renderBoard(); // Hủy: thẻ đã kéo quay về cột cũ
  if (done?.fromDetail && Auth.isLoggedIn()) openApplicationDetail(done.id);
});

moveFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!pendingMove || moveSaving) return;
  const { id, status } = pendingMove;
  const extra = { send_email: moveSendEmailEl.checked };

  if (status === "interview") {
    const value = moveInterviewAtEl.value;
    const at = value ? new Date(value) : null;
    if (at && (Number.isNaN(at.getTime()) || at.getTime() < Date.now() - 60 * 1000)) {
      moveInterviewAtEl.classList.add("is-invalid");
      moveInterviewAtEl.focus();
      return;
    }
    extra.interview_at = at ? at.toISOString() : null;
    extra.interview_location = moveLocationEl.value.trim() || null;
  }

  setMoveSaving(true);
  moveErrorEl.classList.add("d-none");
  const ok = await moveApplication(id, status, extra);
  setMoveSaving(false);
  if (ok) {
    moveModal.hide();
  } else if (Auth.isLoggedIn()) {
    moveErrorEl.textContent = "Chưa lưu được, thẻ vẫn ở cột cũ. Xem thông báo lỗi ở góc màn hình rồi thử lại.";
    moveErrorEl.classList.remove("d-none");
  }
});

// Menu ⋮ trên thẻ (cách chuyển cột không cần kéo: bàn phím, điện thoại)
boardEl.addEventListener("click", (event) => {
  const moveBtn = event.target.closest("[data-move]");
  if (moveBtn) {
    const card = moveBtn.closest(".candidate-card");
    requestMove(Number(card.dataset.id), moveBtn.dataset.move);
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
  const schedule = app?.status === "interview" && (app.interview_at || app.interview_location)
    ? `<div class="mt-1"><i class="bi bi-calendar-event me-1"></i>Phỏng vấn: ${app.interview_at ? `<b>${escapeHtml(formatDate(app.interview_at))}</b>` : "chưa chốt giờ"}${app.interview_location ? ` · ${escapeHtml(app.interview_location)}` : ""}</div>`
    : "";
  document.getElementById("detail-sub").innerHTML =
    `Ứng tuyển: <b>${escapeHtml(jobTitle)}</b>${app?.created_at ? ` · Nộp ${escapeHtml(formatDate(app.created_at))}` : ""}${schedule}`;

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
  if (btn && detailAppId !== null) requestMove(detailAppId, btn.dataset.detailMove, { fromDetail: true });
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
const jobLocationEl = document.getElementById("job-location");
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
  jobLocationEl.value = job?.location ?? "";
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
    location: jobLocationEl.value.trim() || null,
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
    refreshAfterJobChange(saved.id);
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
    refreshAfterJobChange(closed.id);
  } catch (err) {
    closeJobErrorEl.textContent = err.message;
    closeJobErrorEl.classList.remove("d-none");
  } finally {
    setClosingJob(false);
  }
});

/** Sau khi tạo / sửa / đóng tin: tải lại danh sách ở màn hình đang xem. */
function refreshAfterJobChange(jobId) {
  if (currentView === "kanban") saveJobId(jobId); // Kanban tự chọn tin vừa lưu
  loadJobs();
  if (currentView === "jobs") loadJobsPage();
}

/** Mở hộp xác nhận đóng tin trực tiếp (không qua form sửa), dùng ở trang quản lý tin. */
function confirmCloseJob(job) {
  editingJob = job;
  returnToJobForm = false;
  document.getElementById("close-job-name").textContent = job.title;
  closeJobErrorEl.classList.add("d-none");
  setClosingJob(false);
  closeJobModal.show();
}

// ===== 6.9: Trang quản lý tin tuyển dụng =====
const viewKanbanEl = document.getElementById("view-kanban");
const viewJobsEl = document.getElementById("view-jobs");
const jobsListEl = document.getElementById("jobs-list");
const jobsStatsEl = document.getElementById("jobs-stats");
const jobsSearchEl = document.getElementById("jobs-search");
const APP_LIMIT = 500; // tối đa của API; vượt thì số hồ sơ có thể thiếu

let currentView = "kanban";
let jobsPageJobs = [];
let appCounts = new Map(); // job_id → { total, fresh } (fresh = hồ sơ còn ở cột "Mới nộp")
let appsTruncated = false;
let jobsFilter = "all";
let jobsPageRequestId = 0;

async function loadJobsPage() {
  const requestId = ++jobsPageRequestId;
  jobsStatsEl.innerHTML = "";
  renderState(jobsListEl, "loading", { message: "Đang tải tin tuyển dụng…" });
  try {
    // 2 lời gọi: mọi tin + mọi hồ sơ (để đếm theo tin), không gọi riêng từng tin
    const [jobList, apps] = await Promise.all([
      JobAPI.list(),
      ApplicationAPI.list({ limit: APP_LIMIT }),
    ]);
    if (requestId !== jobsPageRequestId) return;
    jobsPageJobs = sortJobs(Array.isArray(jobList) ? jobList : []);
    const appList = Array.isArray(apps) ? apps : [];
    appsTruncated = appList.length >= APP_LIMIT;
    appCounts = new Map();
    appList.forEach((a) => {
      const c = appCounts.get(a.job_id) ?? { total: 0, fresh: 0 };
      c.total += 1;
      if (a.status === "applied") c.fresh += 1;
      appCounts.set(a.job_id, c);
    });
  } catch (err) {
    if (requestId !== jobsPageRequestId || err.status === 401) return;
    renderState(jobsListEl, "error", {
      message: "Không tải được danh sách tin tuyển dụng",
      hint: err.message,
      onRetry: loadJobsPage,
    });
    return;
  }
  renderJobsPage();
}

function filteredJobs() {
  const keyword = normalizeText(jobsSearchEl.value.trim());
  return jobsPageJobs.filter((job) =>
    (jobsFilter === "all" || job.status === jobsFilter)
    && (!keyword || normalizeText([job.title, ...(job.required_skills ?? []), ...(job.preferred_skills ?? [])].join(" ")).includes(keyword)));
}

function jobStatusBadge(job) {
  return job.status === "open"
    ? '<span class="badge bg-green-lt">Đang mở</span>'
    : '<span class="badge bg-secondary-lt"><i class="bi bi-lock me-1"></i>Đã đóng</span>';
}

function jobExpText(job) {
  return Number(job.experience_years_min) > 0
    ? `Từ ${escapeHtml(job.experience_years_min)} năm kinh nghiệm`
    : "Không yêu cầu kinh nghiệm";
}

/** 3 kỹ năng bắt buộc đầu tiên, còn lại ghi "+N". */
function jobSkillsHtml(job) {
  const skills = Array.isArray(job.required_skills) ? job.required_skills : [];
  if (!skills.length) return '<span class="small text-secondary">—</span>';
  const more = skills.length > 3 ? `<span class="small text-secondary">+${skills.length - 3}</span>` : "";
  return `<div class="d-flex flex-wrap gap-1">${skills.slice(0, 3).map((s) => `<span class="skill-mini">${escapeHtml(s)}</span>`).join("")}${more}</div>`;
}

function jobCountText(job) {
  const c = appCounts.get(job.id);
  if (!c?.total) return '<span class="text-secondary">0</span>';
  return `<b>${c.total}</b>${c.fresh ? ` <span class="text-secondary">(${c.fresh} mới)</span>` : ""}`;
}

/** Menu ⋮: sửa tin, xem trên cổng ứng viên, đóng tin (2 mục sau chỉ với tin đang mở). */
function jobMenuHtml(job) {
  const id = Number(job.id);
  const isOpen = job.status === "open";
  return `
    <div class="dropdown d-inline-block">
      <button type="button" class="btn btn-sm btn-ghost-secondary btn-icon" data-bs-toggle="dropdown" aria-expanded="false" aria-label="Thao tác với tin ${escapeHtml(job.title)}">
        <i class="bi bi-three-dots-vertical"></i>
      </button>
      <div class="dropdown-menu dropdown-menu-end">
        <button type="button" class="dropdown-item" data-job-action="edit" data-job-id="${id}"><i class="bi bi-pencil me-2"></i>Sửa tin</button>
        ${isOpen ? `
          <a class="dropdown-item" href="index.html" target="_blank" rel="noopener"><i class="bi bi-box-arrow-up-right me-2"></i>Xem trên cổng ứng viên</a>
          <div class="dropdown-divider"></div>
          <button type="button" class="dropdown-item text-danger" data-job-action="close" data-job-id="${id}"><i class="bi bi-lock me-2"></i>Đóng tin</button>` : ""}
      </div>
    </div>`;
}

function renderJobsPage() {
  const total = jobsPageJobs.length;
  const open = jobsPageJobs.filter((j) => j.status === "open").length;
  const apps = [...appCounts.values()].reduce((n, c) => n + c.total, 0);
  jobsStatsEl.innerHTML = `
    <span class="stat-pill"><i class="bi bi-briefcase me-1"></i>${total} tin</span>
    <span class="stat-pill"><i class="bi bi-broadcast me-1"></i>${open} đang mở</span>
    <span class="stat-pill"><i class="bi bi-people me-1"></i>${apps}${appsTruncated ? "+" : ""} hồ sơ</span>`;
  const counts = { all: total, open, closed: total - open };
  Object.entries(counts).forEach(([k, v]) => { document.querySelector(`#jobs-filter [data-count="${k}"]`).textContent = v; });

  if (!total) {
    renderState(jobsListEl, "empty", { message: "Chưa có tin tuyển dụng nào", hint: "Bấm \"Tạo tin mới\" để đăng tin đầu tiên." });
    return;
  }
  const list = filteredJobs();
  if (!list.length) {
    renderState(jobsListEl, "empty", { message: "Không tìm thấy tin phù hợp", hint: "Thử đổi bộ lọc hoặc từ khóa tìm kiếm." });
    return;
  }

  const rows = list.map((job) => {
    const id = Number(job.id);
    const isOpen = job.status === "open";
    return `
      <tr class="${isOpen ? "" : "job-row-closed"}">
        <td class="job-title-cell">
          <button type="button" class="job-title-link text-break" data-job-action="kanban" data-job-id="${id}">${escapeHtml(job.title)}</button>
          <div class="small text-secondary">${jobExpText(job)}</div>
        </td>
        <td>${jobStatusBadge(job)}</td>
        <td>${jobSkillsHtml(job)}</td>
        <td class="text-center text-nowrap">${jobCountText(job)}</td>
        <td class="text-nowrap small">${escapeHtml(formatDate(job.created_at, false))}</td>
        <td class="text-nowrap text-end">
          <button type="button" class="btn btn-sm ${isOpen ? "btn-outline-primary" : "btn-outline-secondary"}" data-job-action="kanban" data-job-id="${id}"><i class="bi bi-kanban me-1"></i>Kanban</button>
          ${jobMenuHtml(job)}
        </td>
      </tr>`;
  }).join("");

  const cards = list.map((job) => {
    const id = Number(job.id);
    const isOpen = job.status === "open";
    return `
      <div class="list-group-item ${isOpen ? "" : "job-row-closed"}">
        <div class="d-flex justify-content-between align-items-start gap-2">
          <button type="button" class="job-title-link text-break" data-job-action="kanban" data-job-id="${id}">${escapeHtml(job.title)}</button>
          <span class="flex-shrink-0">${jobStatusBadge(job)}</span>
        </div>
        <div class="small text-secondary mt-1">${jobCountText(job)} hồ sơ · Đăng ${escapeHtml(formatDate(job.created_at, false))}</div>
        <div class="mt-2">${jobSkillsHtml(job)}</div>
        <div class="d-flex gap-2 mt-2">
          <button type="button" class="btn btn-sm ${isOpen ? "btn-outline-primary" : "btn-outline-secondary"} flex-fill" data-job-action="kanban" data-job-id="${id}"><i class="bi bi-kanban me-1"></i>Kanban</button>
          <button type="button" class="btn btn-sm btn-outline-secondary" data-job-action="edit" data-job-id="${id}" aria-label="Sửa tin ${escapeHtml(job.title)}"><i class="bi bi-pencil"></i></button>
          ${isOpen ? `<button type="button" class="btn btn-sm btn-outline-danger" data-job-action="close" data-job-id="${id}" aria-label="Đóng tin ${escapeHtml(job.title)}"><i class="bi bi-lock"></i></button>` : ""}
        </div>
      </div>`;
  }).join("");

  jobsListEl.innerHTML = `
    <div class="table-responsive d-none d-md-block">
      <table class="table table-vcenter card-table jobs-table">
        <thead>
          <tr><th>Vị trí</th><th>Trạng thái</th><th>Kỹ năng bắt buộc</th><th class="text-center">Hồ sơ</th><th>Ngày đăng</th><th class="w-1"><span class="visually-hidden">Thao tác</span></th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <div class="list-group list-group-flush d-md-none">${cards}</div>
    ${appsTruncated ? `<div class="card-footer small text-secondary">Số hồ sơ chỉ đếm ${APP_LIMIT} hồ sơ mới nhất (giới hạn của API).</div>` : ""}`;
}

jobsListEl.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-job-action]");
  if (!btn) return;
  const job = jobsPageJobs.find((j) => j.id === Number(btn.dataset.jobId));
  if (!job) return;
  if (btn.dataset.jobAction === "kanban") {
    saveJobId(job.id);
    location.hash = "#kanban";
  } else if (btn.dataset.jobAction === "edit") {
    openJobForm(job);
  } else if (btn.dataset.jobAction === "close") {
    confirmCloseJob(job);
  }
});

document.getElementById("jobs-filter").addEventListener("click", (event) => {
  const btn = event.target.closest("[data-filter]");
  if (!btn) return;
  jobsFilter = btn.dataset.filter;
  document.querySelectorAll("#jobs-filter [data-filter]").forEach((b) => {
    b.classList.toggle("active", b === btn);
    b.setAttribute("aria-pressed", String(b === btn));
  });
  renderJobsPage();
});
jobsSearchEl.addEventListener("input", () => { if (jobsPageJobs.length) renderJobsPage(); });
document.getElementById("jobs-reload-btn").addEventListener("click", loadJobsPage);
document.getElementById("jobs-create-btn").addEventListener("click", () => openJobForm(null));

// ===== Chuyển màn hình: #kanban (mặc định) / #tin-tuyen-dung =====
function viewFromHash() {
  return location.hash === "#tin-tuyen-dung" ? "jobs" : "kanban";
}

function showView(view, { initial = false } = {}) {
  const previous = currentView;
  currentView = view;
  viewKanbanEl.classList.toggle("d-none", view !== "kanban");
  viewJobsEl.classList.toggle("d-none", view !== "jobs");
  document.querySelectorAll("[data-view-nav]").forEach((li) => {
    const active = li.dataset.viewNav === view;
    li.classList.toggle("active", active);
    const link = li.querySelector(".nav-link");
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  // Điện thoại: chọn xong thì thu menu lại
  bootstrap.Collapse.getInstance(document.getElementById("admin-nav"))?.hide();
  document.title = view === "jobs" ? "Tin tuyển dụng — SmartRecruit AI" : "SmartRecruit AI — HR Dashboard";

  if (view === "jobs") {
    stopPolling(); // Kanban đang ẩn thì không cần tự gọi lại
    loadJobsPage();
  } else if (!initial && previous !== "kanban") {
    loadJobs(); // dữ liệu có thể đã đổi ở trang quản lý tin; giữ tin đã chọn (sr_admin_job)
  }
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", () => {
  if (!dashboardViewEl.classList.contains("d-none")) showView(viewFromHash());
});

// ===== Khởi động =====
if (Auth.isLoggedIn()) {
  showDashboard();
} else {
  showLogin();
}
