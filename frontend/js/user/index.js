/**
 * Cổng ứng viên SmartRecruit AI.
 * P1: Danh sách việc làm đang mở.
 * P2: Chi tiết tin tuyển dụng.
 * P3: Form và kiểm tra dữ liệu.
 * P4–P5: Gửi CV, hiển thị trạng thái và kết quả.
 */

"use strict";

let detailElements;
let detailModal;
let applicationElements;

let selectedJob = null;
let currentJobId = null;
let detailRequestVersion = 0;
let listRequestVersion = 0;

let applicationSubmitting = false;
let applicationSent = false;
let modalClosing = false;

// --- Hàm dùng chung ---

function createElement(tag, className, text) {
  const element = document.createElement(tag);

  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;

  return element;
}

function collectElements(ids) {
  const elements = {};

  for (const [key, id] of Object.entries(ids)) {
    const element = document.getElementById(id);

    if (!element) {
      console.error(`Thiếu phần tử #${id}. Hãy kiểm tra index.html.`);
      return null;
    }

    elements[key] = element;
  }

  return elements;
}

function formatJobDate(value) {
  if (!value) return "Chưa cập nhật";

  const raw = String(value);
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw);
  const date = new Date(hasTimezone ? raw : `${raw}Z`);

  if (Number.isNaN(date.getTime())) {
    return "Chưa cập nhật";
  }

  return date.toLocaleDateString("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
  });
}

function getExperienceText(value) {
  if (value == null || value === "") {
    return "Kinh nghiệm: chưa cập nhật";
  }

  const years = Number(value);

  if (!Number.isFinite(years) || years < 0) {
    return "Kinh nghiệm: chưa cập nhật";
  }

  return years > 0
    ? `Kinh nghiệm tối thiểu: ${years} năm`
    : "Không yêu cầu kinh nghiệm";
}

function renderSkills(container, skills, badgeClass, emptyText) {
  container.replaceChildren();

  const items = Array.isArray(skills) ? skills : [];

  if (items.length === 0) {
    container.append(createElement("span", "text-muted", emptyText));
    return;
  }

  items.forEach((skill) => {
    container.append(
      createElement("span", `badge ${badgeClass}`, String(skill))
    );
  });
}

// --- P1: Danh sách việc làm ---

function renderLoading(container) {
  const wrapper = createElement(
    "div",
    "col-12 text-center text-muted py-5"
  );

  wrapper.setAttribute("role", "status");

  const spinner = createElement("div", "spinner-border");
  spinner.setAttribute("aria-hidden", "true");

  wrapper.append(
    spinner,
    createElement("p", "mt-2", "Đang tải danh sách việc làm…")
  );

  container.replaceChildren(wrapper);
}

function renderEmpty(container) {
  const wrapper = createElement("div", "col-12");

  wrapper.append(
    createElement(
      "div",
      "alert alert-info text-center",
      "Hiện chưa có vị trí đang tuyển. Bạn vui lòng quay lại sau."
    )
  );

  container.replaceChildren(wrapper);
}

function renderError(container, message, onRetry) {
  const wrapper = createElement("div", "col-12");
  const alert = createElement("div", "alert alert-danger");

  alert.setAttribute("role", "alert");

  const button = createElement(
    "button",
    "btn btn-outline-danger",
    "Thử lại"
  );

  button.type = "button";
  button.addEventListener("click", onRetry);

  alert.append(
    createElement("p", "mb-3", message),
    button
  );

  wrapper.append(alert);
  container.replaceChildren(wrapper);
}

function createJobCard(job) {
  const column = createElement("div", "col-12 col-md-6 col-xl-4");
  const card = createElement("article", "card h-100 shadow-sm");
  const body = createElement("div", "card-body");
  const skills = createElement("div", "d-flex flex-wrap gap-2 mb-3");

  renderSkills(
    skills,
    job.required_skills,
    "bg-primary-subtle text-primary-emphasis",
    "Chưa cập nhật"
  );

  body.append(
    createElement(
      "h2",
      "h5 card-title",
      job.title || "Vị trí tuyển dụng"
    ),
    createElement(
      "p",
      "fw-semibold mt-3 mb-2",
      "Kỹ năng bắt buộc"
    ),
    skills,
    createElement(
      "p",
      "mb-2",
      getExperienceText(job.experience_years_min)
    ),
    createElement(
      "p",
      "small text-muted mb-0",
      `Ngày đăng: ${formatJobDate(job.created_at)}`
    )
  );

  const footer = createElement(
    "div",
    "card-footer bg-transparent border-0 pt-0 pb-3"
  );

  const button = createElement(
    "button",
    "btn btn-primary",
    "Xem chi tiết"
  );

  button.type = "button";

  if (detailModal) {
    button.addEventListener("click", () => openJobDetail(job.id));
  } else {
    button.disabled = true;
    button.title = "Không tải được thành phần xem chi tiết.";
  }

  footer.append(button);
  card.append(body, footer);
  column.append(card);

  return column;
}

async function loadOpenJobs(container) {
  const requestVersion = ++listRequestVersion;

  renderLoading(container);

  try {
    const jobs = await JobAPI.listOpen();

    if (requestVersion !== listRequestVersion) return;

    if (!Array.isArray(jobs)) {
      throw new Error("Dữ liệu danh sách việc làm không hợp lệ.");
    }

    const openJobs = jobs.filter((job) => job?.status === "open");

    if (openJobs.length === 0) {
      renderEmpty(container);
      return;
    }

    const fragment = document.createDocumentFragment();

    openJobs.forEach((job) => {
      fragment.append(createJobCard(job));
    });

    container.replaceChildren(fragment);
  } catch (error) {
    if (requestVersion !== listRequestVersion) return;

    renderError(
      container,
      error.message || "Không tải được danh sách việc làm.",
      () => loadOpenJobs(container)
    );
  }
}

// --- P3: Form và kiểm tra dữ liệu ---

function setFieldError(input, message) {
  input.classList.toggle("is-invalid", Boolean(message));
  input.setAttribute("aria-invalid", String(Boolean(message)));

  const feedback = document.getElementById(`${input.id}-error`);

  if (feedback) {
    feedback.textContent = message;
  }
}

function showApplicationMessage(type, text) {
  const message = applicationElements.message;

  message.className = `alert alert-${type}`;
  message.textContent = text;
  message.hidden = false;

  message.scrollIntoView({
    behavior: "smooth",
    block: "nearest",
  });
}

function updateApplicationControls() {
  const { form, inputs, submit } = applicationElements;
  const locked = applicationSubmitting || applicationSent;

  inputs.forEach((input) => {
    input.disabled = locked;
  });

  submit.disabled =
    locked || selectedJob?.status !== "open";

  form.setAttribute("aria-busy", String(applicationSubmitting));

  if (applicationSubmitting) {
    const spinner = createElement(
      "span",
      "spinner-border spinner-border-sm me-2"
    );

    spinner.setAttribute("aria-hidden", "true");

    submit.replaceChildren(
      spinner,
      document.createTextNode("Đang gửi…")
    );
  } else {
    submit.textContent = applicationSent
      ? "Đã gửi hồ sơ"
      : "Gửi hồ sơ";
  }

  if (!detailElements?.modal) return;

  detailElements.apply.hidden =
    applicationSent || selectedJob?.status !== "open";

  detailElements.apply.disabled =
    locked || selectedJob?.status !== "open";

  detailElements.modal
    .querySelectorAll('[data-bs-dismiss="modal"]')
    .forEach((button) => {
      button.disabled = applicationSubmitting;
    });
}

function resetApplicationForm() {
  if (applicationSubmitting) return;

  applicationSent = false;

  applicationElements.form.reset();
  applicationElements.section.hidden = true;
  applicationElements.message.hidden = true;
  applicationElements.message.textContent = "";

  applicationElements.inputs.forEach((input) => {
    setFieldError(input, "");
  });

  updateApplicationControls();
}

function validateApplicationForm() {
  const { name, email, phone, cv, inputs } = applicationElements;

  name.value = name.value.trim();
  email.value = email.value.trim();
  phone.value = phone.value.trim();

  const errors = new Map();

  if (name.value.length < 2 || name.value.length > 150) {
    errors.set(name, "Họ tên phải có từ 2 đến 150 ký tự.");
  }

  if (
    !email.value ||
    email.value.length > 255 ||
    email.validity.typeMismatch
  ) {
    errors.set(email, "Vui lòng nhập email hợp lệ, tối đa 255 ký tự.");
  }

  if (
    phone.value.length > 30 ||
    (phone.value && !/^[0-9 +.\-]+$/.test(phone.value))
  ) {
    errors.set(
      phone,
      "Số điện thoại tối đa 30 ký tự, chỉ gồm số, khoảng trắng, +, - và dấu chấm."
    );
  }

  const file = cv.files[0];

  if (!file) {
    errors.set(cv, "Vui lòng chọn CV.");
  } else if (!/\.pdf$/i.test(file.name)) {
    errors.set(cv, "Chỉ chấp nhận tệp PDF.");
  } else if (file.size === 0) {
    errors.set(cv, "Tệp CV đang rỗng.");
  } else if (file.size >= 5 * 1024 * 1024) {
    errors.set(cv, "Tệp CV phải nhỏ hơn 5 MB.");
  }

  inputs.forEach((input) => {
    setFieldError(input, errors.get(input) || "");
  });

  if (errors.size > 0) {
    errors.keys().next().value.focus();
    return false;
  }

  return true;
}

// --- P4–P5: Gửi hồ sơ thật ---

async function submitApplication(event) {
  event.preventDefault();

  if (applicationSubmitting || applicationSent) return;

  applicationElements.message.hidden = true;

  if (!validateApplicationForm()) return;

  if (selectedJob?.status !== "open") {
    showApplicationMessage(
      "warning",
      "Tin tuyển dụng không còn sẵn sàng để ứng tuyển."
    );
    return;
  }

  const { name, email, phone, cv } = applicationElements;

  const formData = new FormData();

  formData.append("job_id", String(selectedJob.id));
  formData.append("full_name", name.value);
  formData.append("email", email.value);

  if (phone.value) {
    formData.append("phone", phone.value);
  }

  // Tên trường tệp phải khớp API backend.
  formData.append("cv_file", cv.files[0]);

  applicationSubmitting = true;
  updateApplicationControls();

  try {
    // api.js kiểm tra response.ok và chuẩn hóa lỗi backend.
    // Không tự đặt Content-Type khi gửi FormData.
    await ApplicationAPI.apply(formData);

    applicationSent = true;

    showApplicationMessage(
      "success",
      "Hồ sơ đã được gửi, bộ phận tuyển dụng sẽ liên hệ với bạn."
    );

    // Không hiển thị điểm AI cho ứng viên.
  } catch (error) {
    showApplicationMessage(
      "danger",
      error.message || "Không gửi được hồ sơ. Vui lòng thử lại."
    );
  } finally {
    applicationSubmitting = false;
    updateApplicationControls();
  }
}

function initializeApplicationForm() {
  applicationElements = collectElements({
    section: "application-section",
    form: "application-form",
    message: "application-message",
    name: "candidate-name",
    email: "candidate-email",
    phone: "candidate-phone",
    cv: "candidate-cv",
  });

  if (!applicationElements) return false;

  applicationElements.submit =
    applicationElements.form.querySelector('button[type="submit"]');

  if (!applicationElements.submit) {
    console.error("Thiếu nút submit trong #application-form.");
    return false;
  }

  applicationElements.inputs = [
    applicationElements.name,
    applicationElements.email,
    applicationElements.phone,
    applicationElements.cv,
  ];

  applicationElements.submit.textContent = "Gửi hồ sơ";

  applicationElements.form.addEventListener(
    "submit",
    submitApplication
  );

  return true;
}

// --- P2: Chi tiết tin tuyển dụng ---

function setDetailState(state, message = "") {
  detailElements.loading.hidden = state !== "loading";
  detailElements.error.hidden = state !== "error";
  detailElements.empty.hidden = state !== "empty";
  detailElements.content.hidden = state !== "content";

  detailElements.errorMessage.textContent = message;

  detailElements.modal.setAttribute(
    "aria-busy",
    String(state === "loading")
  );

  updateApplicationControls();

  if (state !== "content" || selectedJob?.status !== "open") {
    applicationElements.section.hidden = true;
    detailElements.apply.hidden = true;
    detailElements.apply.disabled = true;
  }
}

function renderJobDetail(job) {
  const isOpen = job.status === "open";

  detailElements.title.textContent =
    job.title || "Chi tiết tuyển dụng";

  detailElements.status.textContent =
    isOpen ? "Đang tuyển" : "Tin đã đóng";

  detailElements.status.className =
    `badge ${isOpen ? "text-bg-success" : "text-bg-secondary"}`;

  detailElements.experience.textContent =
    getExperienceText(job.experience_years_min);

  detailElements.date.textContent = formatJobDate(job.created_at);

  detailElements.description.textContent =
    job.description || "Chưa cập nhật mô tả công việc.";

  detailElements.requirements.textContent =
    job.requirements || "Chưa cập nhật yêu cầu ứng viên.";

  detailElements.closed.hidden = isOpen;

  renderSkills(
    detailElements.requiredSkills,
    job.required_skills,
    "bg-primary-subtle text-primary-emphasis",
    "Chưa cập nhật kỹ năng bắt buộc."
  );

  renderSkills(
    detailElements.preferredSkills,
    job.preferred_skills,
    "bg-success-subtle text-success-emphasis",
    "Không có kỹ năng ưu tiên."
  );

  setDetailState("content");
}

async function openJobDetail(jobId) {
  if (!detailModal || applicationSubmitting || modalClosing) return;

  const requestVersion = ++detailRequestVersion;

  currentJobId = jobId;
  selectedJob = null;

  resetApplicationForm();

  detailElements.title.textContent = "Chi tiết tuyển dụng";
  setDetailState("loading");
  detailModal.show();

  try {
    const job = await JobAPI.get(jobId);

    if (requestVersion !== detailRequestVersion) return;

    if (!job) {
      setDetailState("empty");
      return;
    }

    if (
      typeof job !== "object" ||
      Array.isArray(job) ||
      job.id == null
    ) {
      throw new Error("Thông tin tuyển dụng không hợp lệ.");
    }

    selectedJob = job;
    renderJobDetail(job);
  } catch (error) {
    if (requestVersion !== detailRequestVersion) return;

    selectedJob = null;

    setDetailState(
      "error",
      error.message || "Không tải được chi tiết tuyển dụng."
    );
  }
}

function initializeJobDetail() {
  detailElements = collectElements({
    modal: "job-detail-modal",
    title: "job-detail-title",
    loading: "job-detail-loading",
    error: "job-detail-error",
    errorMessage: "job-detail-error-message",
    retry: "job-detail-retry",
    empty: "job-detail-empty",
    content: "job-detail-content",
    status: "job-detail-status",
    experience: "job-detail-experience",
    date: "job-detail-date",
    closed: "job-detail-closed",
    description: "job-detail-description",
    requirements: "job-detail-requirements",
    requiredSkills: "job-detail-required-skills",
    preferredSkills: "job-detail-preferred-skills",
    apply: "job-detail-apply",
  });

  if (!detailElements) return false;

  if (!window.bootstrap?.Modal) {
    console.error("Bootstrap JS chưa tải được.");
    return false;
  }

  detailModal = bootstrap.Modal.getOrCreateInstance(
    detailElements.modal
  );

  detailElements.retry.addEventListener("click", () => {
    if (currentJobId != null) {
      openJobDetail(currentJobId);
    }
  });

  detailElements.apply.addEventListener("click", () => {
    if (
      selectedJob?.status !== "open" ||
      applicationSubmitting ||
      applicationSent
    ) {
      return;
    }

    applicationElements.section.hidden = false;

    applicationElements.section.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });

    applicationElements.name.focus({ preventScroll: true });
  });

  detailElements.modal.addEventListener("hide.bs.modal", (event) => {
    // Chặn cả nút đóng, Escape và bấm nền khi đang gửi.
    if (applicationSubmitting) {
      event.preventDefault();
      return;
    }

    modalClosing = true;
    detailRequestVersion += 1;
    selectedJob = null;

    detailElements.apply.disabled = true;
  });

  detailElements.modal.addEventListener("hidden.bs.modal", () => {
    resetApplicationForm();
    currentJobId = null;
    modalClosing = false;
  });

  return true;
}

// --- Khởi tạo trang ---

document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("job-list");

  if (!container) {
    console.error("Không tìm thấy phần tử #job-list.");
    return;
  }

  if (initializeApplicationForm()) {
    initializeJobDetail();
  }

  loadOpenJobs(container);
});