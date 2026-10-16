/**
 * SmartRecruit AI — HR Dashboard.
 * A1: Đăng nhập.
 * A2: Thông tin phiên và đăng xuất.
 * A3: Chọn tin tuyển dụng.
 * A4: Tạo, sửa và đóng tin tuyển dụng.
 */

"use strict";

let ui;
let editorModal;

let jobs = [];
let selectedJobId = null;
let editingJobId = null;

let loginBusy = false;
let actionBusy = false;
let listLoading = false;
let listVersion = 0;
let sessionVersion = 0;
let editorClosing = false;

const skillValues = {
  required: [],
  preferred: [],
};

// --- Hàm dùng chung ---

function el(id) {
  const element = document.getElementById(id);

  if (!element) {
    throw new Error(`Thiếu phần tử #${id} trong admin.html.`);
  }

  return element;
}

function showMessage(element, text = "", type = "danger") {
  element.textContent = text;
  element.className = `alert alert-${type}`;
  element.hidden = !text;
}

function setButtonLoading(button, loading, text) {
  if (!loading) {
    button.textContent = text;
    return;
  }

  const spinner = document.createElement("span");
  spinner.className = "spinner-border spinner-border-sm me-2";
  spinner.setAttribute("aria-hidden", "true");

  button.replaceChildren(
    spinner,
    document.createTextNode(text)
  );
}

function selectedJob() {
  return jobs.find(
    (job) => String(job.id) === String(selectedJobId)
  ) || null;
}

function updateControls() {
  const job = selectedJob();
  const hasSelection = Boolean(job) && !listLoading;

  ui.logout.disabled = actionBusy;
  ui.refresh.disabled = actionBusy || listLoading;
  ui.create.disabled = actionBusy;
  ui.select.disabled = actionBusy || listLoading || !jobs.length;

  ui.edit.disabled = actionBusy || !hasSelection;
  ui.close.disabled =
    actionBusy || !hasSelection || job?.status !== "open";

  ui.fields.disabled = actionBusy;
  ui.save.disabled = actionBusy;

  ui.editor.querySelectorAll('[data-bs-dismiss="modal"]')
    .forEach((button) => {
      button.disabled = actionBusy;
    });

  ui.form.setAttribute("aria-busy", String(actionBusy));
}

function setActionBusy(value) {
  actionBusy = value;
  updateControls();
}

// --- A1–A2: Phiên đăng nhập ---

function setLoginBusy(value) {
  loginBusy = value;

  ui.email.disabled = value;
  ui.password.disabled = value;
  ui.loginButton.disabled = value;

  ui.loginForm.setAttribute("aria-busy", String(value));

  setButtonLoading(
    ui.loginButton,
    value,
    value ? "Đang đăng nhập…" : "Đăng nhập"
  );
}

function showLogin(message = "", type = "info") {
  sessionVersion += 1;
  listVersion += 1;

  jobs = [];
  selectedJobId = null;
  editingJobId = null;
  listLoading = false;
  actionBusy = false;

  updateControls();

  editorModal.hide();

  ui.login.hidden = false;
  ui.dashboard.hidden = true;
  ui.session.hidden = true;

  ui.sessionEmail.textContent = "";
  ui.password.value = "";

  ui.select.replaceChildren();
  ui.board.replaceChildren();
  ui.summary.textContent = "";

  showMessage(ui.dashboardMessage);
  showMessage(ui.loginMessage, message, type);
}

function showDashboard() {
  ui.login.hidden = true;
  ui.dashboard.hidden = false;
  ui.session.hidden = false;

  ui.sessionEmail.textContent =
    AuthSession.getEmail() || "Tài khoản HR";

  ui.password.value = "";
  showMessage(ui.loginMessage);

  loadHRJobs();
  ui.heading.focus();
}

async function submitLogin(event) {
  event.preventDefault();

  if (loginBusy) return;

  showMessage(ui.loginMessage);

  ui.email.value = ui.email.value.trim();

  if (!ui.loginForm.checkValidity()) {
    ui.loginForm.reportValidity();
    return;
  }

  const version = sessionVersion;
  setLoginBusy(true);

  try {
    await AuthAPI.login(ui.email.value, ui.password.value);

    if (version !== sessionVersion) {
      AuthSession.clear();
      return;
    }

    showDashboard();
  } catch (error) {
    if (version === sessionVersion) {
      showMessage(
        ui.loginMessage,
        error.message || "Không thể đăng nhập."
      );
    }
  } finally {
    setLoginBusy(false);
  }
}

// --- A3: Chọn tin tuyển dụng ---

function jobTimestamp(job) {
  if (!job.created_at) return 0;

  const raw = String(job.created_at);
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw);
  const timestamp = Date.parse(hasTimezone ? raw : `${raw}Z`);

  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function setListState(state, message = "") {
  listLoading = state === "loading";

  ui.loading.hidden = state !== "loading";
  ui.listError.hidden = state !== "error";
  ui.empty.hidden = state !== "empty";
  ui.content.hidden = state !== "content";

  ui.listErrorMessage.textContent = message;
  updateControls();
}

function updateSelectedJob() {
  selectedJobId = ui.select.value || null;

  const job = selectedJob();

  ui.summary.textContent = job
    ? `Mã tin: ${job.id} · ${
        job.status === "open" ? "Đang tuyển" : "Đã đóng"
      }`
    : "";

  ui.board.replaceChildren();

  if (job) {
    const column = document.createElement("div");
    column.className = "col-12";

    const message = document.createElement("div");
    message.className = "alert alert-secondary";

    message.textContent =
      `Đã chọn "${job.title}". ` +
      "Bảng Kanban sẽ được bổ sung ở bước A5.";

    column.append(message);
    ui.board.append(column);
  }

  updateControls();
}

async function loadHRJobs(preferredId = null) {
  if (!AuthSession.getToken()) return;

  const version = ++listVersion;
  const token = AuthSession.getToken();

  setListState("loading");
  ui.board.replaceChildren();

  try {
    const result = await JobAPI.list();

    if (
      version !== listVersion ||
      AuthSession.getToken() !== token
    ) {
      return;
    }

    if (!Array.isArray(result)) {
      throw new Error("Dữ liệu tin tuyển dụng không hợp lệ.");
    }

    jobs = result
      .filter((job) => job && job.id != null)
      .sort((a, b) => (
        jobTimestamp(b) - jobTimestamp(a) ||
        Number(b.id) - Number(a.id)
      ));

    ui.select.replaceChildren();

    if (!jobs.length) {
      selectedJobId = null;
      ui.summary.textContent = "";
      setListState("empty");
      return;
    }

    const fragment = document.createDocumentFragment();

    jobs.forEach((job) => {
      const option = document.createElement("option");

      option.value = String(job.id);
      option.textContent =
        `${job.title || "Chưa có tiêu đề"} — ` +
        (job.status === "open" ? "Đang tuyển" : "Đã đóng");

      fragment.append(option);
    });

    ui.select.append(fragment);

    const preferred = jobs.find(
      (job) => String(job.id) === String(preferredId)
    );

    const defaultJob =
      preferred ||
      jobs.find((job) => job.status === "open") ||
      jobs[0];

    ui.select.value = String(defaultJob.id);

    setListState("content");
    updateSelectedJob();
  } catch (error) {
    if (
      version !== listVersion ||
      AuthSession.getToken() !== token
    ) {
      return;
    }

    jobs = [];
    selectedJobId = null;
    ui.select.replaceChildren();
    ui.summary.textContent = "";

    setListState(
      "error",
      error.message || "Không tải được danh sách tin."
    );
  }
}

// --- A4: Nhập kỹ năng dạng nhãn ---

function skillInput(kind) {
  return kind === "required"
    ? ui.requiredInput
    : ui.preferredInput;
}

function skillContainer(kind) {
  return kind === "required"
    ? ui.requiredTags
    : ui.preferredTags;
}

function renderSkillTags(kind) {
  const container = skillContainer(kind);
  container.replaceChildren();

  skillValues[kind].forEach((skill, index) => {
    const tag = document.createElement("span");
    tag.className =
      "badge d-inline-flex align-items-center gap-2 " +
      (kind === "required"
        ? "text-bg-primary"
        : "text-bg-success");

    const label = document.createElement("span");
    label.textContent = skill;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn-close btn-close-white";
    remove.style.fontSize = "0.6rem";
    remove.setAttribute("aria-label", `Xóa kỹ năng ${skill}`);

    remove.addEventListener("click", () => {
      if (actionBusy) return;

      skillValues[kind].splice(index, 1);
      renderSkillTags(kind);
      skillInput(kind).focus();
    });

    tag.append(label, remove);
    container.append(tag);
  });
}

function addSkill(kind) {
  const input = skillInput(kind);
  const value = input.value.trim();

  if (!value) return;

  const exists = skillValues[kind].some(
    (skill) => skill.toLocaleLowerCase() === value.toLocaleLowerCase()
  );

  if (!exists) {
    skillValues[kind].push(value);
  }

  input.value = "";
  renderSkillTags(kind);
}

function setupSkillInput(kind, button) {
  const input = skillInput(kind);

  button.addEventListener("click", () => {
    if (actionBusy) return;

    addSkill(kind);
    input.focus();
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.isComposing) {
      event.preventDefault();

      if (!actionBusy) {
        addSkill(kind);
      }
    }
  });
}

// --- A4: Tạo / sửa tin ---

function resetEditor() {
  ui.form.reset();

  editingJobId = null;
  skillValues.required = [];
  skillValues.preferred = [];

  renderSkillTags("required");
  renderSkillTags("preferred");

  showMessage(ui.editorMessage);
  ui.form.hidden = false;
  ui.save.textContent = "Lưu tin";
}

function openCreateJob() {
  if (actionBusy || editorClosing) return;

  resetEditor();
  ui.editorTitle.textContent = "Tạo tin tuyển dụng";

  updateControls();
  editorModal.show();
}

async function openEditJob() {
  const job = selectedJob();

  if (!job || actionBusy || editorClosing) return;

  resetEditor();

  const version = sessionVersion;

  ui.editorTitle.textContent = "Sửa tin tuyển dụng";
  ui.form.hidden = true;

  showMessage(ui.editorMessage, "Đang tải nội dung tin…", "info");

  setActionBusy(true);
  editorModal.show();

  try {
    // Lấy nội dung mới nhất thay vì dùng bản cũ trong dropdown.
    const freshJob = await JobAPI.get(job.id);

    if (version !== sessionVersion) return;

    editingJobId = freshJob.id;

    ui.title.value = freshJob.title || "";
    ui.description.value = freshJob.description || "";
    ui.requirements.value = freshJob.requirements || "";
    ui.experience.value = freshJob.experience_years_min ?? 0;

    skillValues.required = Array.isArray(freshJob.required_skills)
      ? [...freshJob.required_skills]
      : [];

    skillValues.preferred = Array.isArray(freshJob.preferred_skills)
      ? [...freshJob.preferred_skills]
      : [];

    renderSkillTags("required");
    renderSkillTags("preferred");

    ui.form.hidden = false;
    showMessage(ui.editorMessage);
  } catch (error) {
    if (version !== sessionVersion) return;

    showMessage(
      ui.editorMessage,
      error.message || "Không tải được tin. Đóng cửa sổ và thử lại."
    );
  } finally {
    if (version === sessionVersion) {
      setActionBusy(false);

      // Không cho lưu nếu tải nội dung sửa thất bại.
      ui.save.disabled = ui.form.hidden;
    }
  }
}

function getJobPayload() {
  ui.title.value = ui.title.value.trim();
  ui.description.value = ui.description.value.trim();
  ui.requirements.value = ui.requirements.value.trim();

  // Ghi nhận cả kỹ năng đã gõ nhưng chưa nhấn Thêm.
  addSkill("required");
  addSkill("preferred");

  if (!ui.form.checkValidity()) {
    ui.form.reportValidity();
    return null;
  }

  if (
    !ui.title.value ||
    !ui.description.value ||
    !ui.requirements.value
  ) {
    showMessage(
      ui.editorMessage,
      "Tiêu đề, mô tả và yêu cầu không được để trống."
    );
    return null;
  }

  if (!skillValues.required.length) {
    showMessage(
      ui.editorMessage,
      "Vui lòng thêm ít nhất một kỹ năng bắt buộc."
    );
    ui.requiredInput.focus();
    return null;
  }

  const years = Number(ui.experience.value);

  if (!Number.isSafeInteger(years) || years < 0) {
    showMessage(
      ui.editorMessage,
      "Số năm kinh nghiệm phải là số nguyên không âm."
    );
    ui.experience.focus();
    return null;
  }

  return {
    title: ui.title.value,
    description: ui.description.value,
    requirements: ui.requirements.value,
    required_skills: [...skillValues.required],
    preferred_skills: [...skillValues.preferred],
    experience_years_min: years,
  };
}

async function saveJob(event) {
  event.preventDefault();

  if (actionBusy || ui.form.hidden) return;

  showMessage(ui.editorMessage);

  const payload = getJobPayload();
  if (!payload) return;

  const version = sessionVersion;
  const editingId = editingJobId;

  setActionBusy(true);
  setButtonLoading(ui.save, true, "Đang lưu…");

  let savedJob;

  try {
    savedJob = editingId == null
      ? await JobAPI.create(payload)
      : await JobAPI.update(editingId, payload);
  } catch (error) {
    if (version === sessionVersion) {
      showMessage(
        ui.editorMessage,
        error.message || "Không lưu được tin tuyển dụng."
      );
    }
    return;
  } finally {
    if (version === sessionVersion) {
      setActionBusy(false);
      ui.save.textContent = "Lưu tin";
    }
  }

  if (version !== sessionVersion) return;

  editorModal.hide();

  showMessage(
    ui.dashboardMessage,
    editingId == null
      ? "Đã tạo tin tuyển dụng."
      : "Đã cập nhật tin tuyển dụng.",
    "success"
  );

  // Chọn đúng tin vừa tạo hoặc vừa sửa.
  await loadHRJobs(savedJob.id);
}

// --- A4: Đóng tin ---

async function closeSelectedJob() {
  const job = selectedJob();

  if (!job || job.status !== "open" || actionBusy) return;

  const confirmed = window.confirm(
    `Đóng tin "${job.title}"?\n` +
    "Ứng viên sẽ không thể nộp thêm hồ sơ vào tin này."
  );

  if (!confirmed) return;

  const version = sessionVersion;

  showMessage(ui.dashboardMessage);
  setActionBusy(true);
  setButtonLoading(ui.close, true, "Đang đóng…");

  try {
    await JobAPI.close(job.id);

    if (version !== sessionVersion) return;

    showMessage(
      ui.dashboardMessage,
      "Đã đóng tin tuyển dụng.",
      "success"
    );

    await loadHRJobs(job.id);
  } catch (error) {
    if (version !== sessionVersion) return;

    showMessage(
      ui.dashboardMessage,
      error.message || "Không đóng được tin tuyển dụng."
    );
  } finally {
    if (version === sessionVersion) {
      ui.close.textContent = "Đóng tin";
      setActionBusy(false);
    }
  }
}

// --- Khởi tạo ---

function initializeHR() {
  const ids = {
    login: "login-section",
    dashboard: "dashboard-section",
    heading: "dashboard-heading",
    session: "hr-session",
    sessionEmail: "hr-email",
    logout: "logout-button",

    loginForm: "login-form",
    loginMessage: "login-message",
    email: "login-email",
    password: "login-password",
    loginButton: "login-button",

    dashboardMessage: "dashboard-message",
    loading: "hr-jobs-loading",
    listError: "hr-jobs-error",
    listErrorMessage: "hr-jobs-error-message",
    empty: "hr-jobs-empty",
    content: "hr-jobs-content",
    select: "hr-job-select",
    summary: "hr-job-summary",
    refresh: "hr-jobs-refresh",
    retry: "hr-jobs-retry",
    create: "job-create-button",
    edit: "job-edit-button",
    close: "job-close-button",
    board: "kanban-board",

    editor: "job-editor-modal",
    editorTitle: "job-editor-title",
    editorMessage: "job-editor-message",
    form: "job-form",
    fields: "job-fields",
    title: "job-title",
    description: "job-description",
    requirements: "job-requirements",
    experience: "job-experience",
    save: "job-save-button",

    requiredInput: "required-skill-input",
    requiredAdd: "required-skill-add",
    requiredTags: "required-skill-tags",
    preferredInput: "preferred-skill-input",
    preferredAdd: "preferred-skill-add",
    preferredTags: "preferred-skill-tags",
  };

  try {
    ui = {};

    for (const [key, id] of Object.entries(ids)) {
      ui[key] = el(id);
    }

    if (
      typeof AuthAPI === "undefined" ||
      typeof AuthSession === "undefined" ||
      typeof JobAPI === "undefined"
    ) {
      throw new Error("Hãy kiểm tra đường dẫn và nội dung api.js.");
    }

    if (!window.bootstrap?.Modal) {
      throw new Error("Bootstrap JS chưa tải được.");
    }

    editorModal = bootstrap.Modal.getOrCreateInstance(ui.editor);
  } catch (error) {
    console.error(error);

    const message = document.getElementById("login-message");
    if (message) showMessage(message, error.message);

    const button = document.getElementById("login-button");
    if (button) button.disabled = true;

    return;
  }

  ui.loginForm.addEventListener("submit", submitLogin);
  ui.form.addEventListener("submit", saveJob);

  ui.select.addEventListener("change", updateSelectedJob);

  ui.refresh.addEventListener("click", () => loadHRJobs());
  ui.retry.addEventListener("click", () => loadHRJobs());

  ui.create.addEventListener("click", openCreateJob);
  ui.edit.addEventListener("click", openEditJob);
  ui.close.addEventListener("click", closeSelectedJob);

  setupSkillInput("required", ui.requiredAdd);
  setupSkillInput("preferred", ui.preferredAdd);

  ui.editor.addEventListener("hide.bs.modal", (event) => {
    if (actionBusy) {
      event.preventDefault();
      return;
    }

    editorClosing = true;
  });

  ui.editor.addEventListener("hidden.bs.modal", () => {
    editorClosing = false;
    resetEditor();
  });

  ui.editor.addEventListener("shown.bs.modal", () => {
    if (!actionBusy && !ui.form.hidden) {
      ui.title.focus();
    }
  });

  window.addEventListener("auth:required", () => {
    showLogin(
      "Phiên đăng nhập không còn hợp lệ. Vui lòng đăng nhập lại.",
      "warning"
    );
  });

  ui.logout.addEventListener("click", () => {
    if (actionBusy) return;

    AuthAPI.logout();
    showLogin("Bạn đã đăng xuất.", "success");
    ui.email.focus();
  });

  window.addEventListener("storage", (event) => {
    if (
      event.key === AUTH_TOKEN_KEY ||
      event.key === null
    ) {
      showLogin(
        "Phiên đăng nhập đã thay đổi ở tab khác. Vui lòng đăng nhập lại.",
        "info"
      );
    }
  });

  updateControls();

  if (AuthSession.getToken()) {
    showDashboard();
  } else {
    showLogin();
  }
}

document.addEventListener("DOMContentLoaded", initializeHR);