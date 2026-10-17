/**
 * js/index.js — Candidate portal logic
 * Mục 5: Candidate Portal (5.1 danh sách việc làm, 5.2 modal chi tiết JD, 5.3 form nộp CV)
 */

const jobListEl = document.getElementById("job-list");
const jobSearchEl = document.getElementById("job-search");
const jobCountEl = document.getElementById("job-count");

let allJobs = [];

/** Bỏ dấu tiếng Việt + chữ thường, để tìm "lap trinh" vẫn ra "Lập trình". */
function normalizeText(text) {
  return String(text ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

function experienceLabel(years) {
  return years > 0 ? `Từ ${years} năm kinh nghiệm` : "Không yêu cầu kinh nghiệm";
}

function jobCardHtml(job) {
  const skills = (job.required_skills ?? [])
    .map((s) => `<span class="skill-tag">${escapeHtml(s)}</span>`)
    .join("");

  return `
    <div class="col-md-6 col-lg-4">
      <article class="card job-card h-100" tabindex="0" role="button" data-job-id="${Number(job.id)}"
        aria-label="Xem chi tiết ${escapeHtml(job.title)}">
        <div class="card-body d-flex flex-column">
          <div class="d-flex gap-3 align-items-start mb-3">
            <div class="job-icon"><i class="bi bi-briefcase"></i></div>
            <div>
              <h3 class="h6 fw-bold mb-1">${escapeHtml(job.title)}</h3>
              <div class="small text-muted"><i class="bi bi-clock-history me-1"></i>${experienceLabel(job.experience_years_min)}</div>
            </div>
          </div>
          <div class="d-flex flex-wrap gap-1 mb-3">${skills}</div>
          <div class="d-flex justify-content-between align-items-center mt-auto pt-2 border-top">
            <span class="small text-muted"><i class="bi bi-calendar3 me-1"></i>${formatDate(job.created_at, false)}</span>
            <span class="text-primary fw-semibold small">Xem chi tiết <i class="bi bi-arrow-right"></i></span>
          </div>
        </div>
      </article>
    </div>`;
}

function renderJobs() {
  const keyword = normalizeText(jobSearchEl.value.trim());
  const jobs = keyword
    ? allJobs.filter((job) =>
        normalizeText([job.title, ...(job.required_skills ?? []), ...(job.preferred_skills ?? [])].join(" ")).includes(keyword))
    : allJobs;

  if (allJobs.length === 0) {
    renderState(jobListEl, "empty", {
      message: "Hiện chưa có vị trí nào đang tuyển",
      hint: "Bạn quay lại sau nhé.",
    });
    return;
  }

  if (jobs.length === 0) {
    renderState(jobListEl, "empty", {
      message: "Không tìm thấy vị trí phù hợp",
      hint: "Thử từ khóa khác, ví dụ tên kỹ năng.",
    });
    return;
  }

  jobListEl.innerHTML = jobs.map(jobCardHtml).join("");
}

async function loadJobs() {
  renderState(jobListEl, "loading", { message: "Đang tải danh sách việc làm…" });
  jobCountEl.textContent = "Đang tải…";

  try {
    allJobs = await JobAPI.listOpen();
    jobCountEl.textContent = `${allJobs.length} việc đang tuyển`;
    renderJobs();
  } catch (err) {
    jobCountEl.textContent = "Chưa tải được danh sách";
    renderState(jobListEl, "error", {
      message: "Không tải được danh sách việc làm",
      hint: err.message,
      onRetry: loadJobs,
    });
  }
}

// ===== 5.2 Modal chi tiết JD =====
const jobModalEl = document.getElementById("job-modal");
const jobModal = new bootstrap.Modal(jobModalEl);
const jobModalTitleEl = document.getElementById("job-modal-title");
const jobModalMetaEl = document.getElementById("job-modal-meta");
const jobModalBodyEl = document.getElementById("job-modal-body");
const jobApplyBtn = document.getElementById("job-apply-btn");
const jobClosedBadge = document.getElementById("job-closed-badge");

let currentJob = null;
let detailRequestId = 0; // bỏ qua kết quả cũ khi người dùng mở tin khác liên tiếp

function jobMetaHtml(job) {
  return `<i class="bi bi-clock-history me-1"></i>${experienceLabel(job.experience_years_min)}`
    + ` · <i class="bi bi-calendar3 ms-1 me-1"></i>Đăng ${formatDate(job.created_at, false)}`;
}

function skillTagsHtml(skills, cls) {
  return (skills ?? []).map((s) => `<span class="${cls}">${escapeHtml(s)}</span>`).join(" ");
}

function jobDetailHtml(job) {
  const preferred = job.preferred_skills?.length
    ? `<div class="mb-2"><span class="small fw-semibold me-2">Ưu tiên:</span>${skillTagsHtml(job.preferred_skills, "skill-tag-outline")}</div>`
    : "";

  return `
    <div class="col-12">
      <h3 class="h6 fw-semibold">Mô tả công việc</h3>
      <p class="jd-text">${escapeHtml(job.description)}</p>
      <h3 class="h6 fw-semibold">Yêu cầu</h3>
      <p class="jd-text">${escapeHtml(job.requirements)}</p>
      <h3 class="h6 fw-semibold">Kỹ năng</h3>
      <div class="mb-2"><span class="small fw-semibold me-2">Bắt buộc:</span>${skillTagsHtml(job.required_skills, "skill-tag")}</div>
      ${preferred}
    </div>`;
}

function setApplyAvailable(isOpen) {
  jobApplyBtn.classList.toggle("d-none", !isOpen);
  jobClosedBadge.classList.toggle("d-none", isOpen);
}

async function openJobDetail(jobId) {
  const requestId = ++detailRequestId;
  const listed = allJobs.find((j) => j.id === jobId);

  currentJob = null;
  jobModalTitleEl.textContent = listed?.title ?? "Chi tiết công việc";
  jobModalMetaEl.innerHTML = listed ? jobMetaHtml(listed) : "";
  jobApplyBtn.classList.add("d-none");
  jobClosedBadge.classList.add("d-none");
  hideApplyForm();
  renderState(jobModalBodyEl, "loading", { message: "Đang tải chi tiết công việc…" });
  jobModal.show();

  try {
    const job = await JobAPI.get(jobId);
    if (requestId !== detailRequestId) return;

    currentJob = job;
    jobModalTitleEl.textContent = job.title;
    jobModalMetaEl.innerHTML = jobMetaHtml(job);
    jobModalBodyEl.innerHTML = jobDetailHtml(job);
    // API trả cả tin đã đóng (VD: HR vừa đóng sau khi trang đã tải)
    setApplyAvailable(job.status === "open");
  } catch (err) {
    if (requestId !== detailRequestId) return;
    renderState(jobModalBodyEl, "error", {
      message: "Không tải được chi tiết công việc",
      hint: err.message,
      onRetry: () => openJobDetail(jobId),
    });
  } finally {
    // Nút "Thử lại" bị xóa khi vẽ lại nội dung → đưa focus về modal để phím Esc vẫn đóng được
    if (requestId === detailRequestId && !jobModalEl.contains(document.activeElement)) {
      jobModalEl.focus();
    }
  }
}

// ===== 5.3 Form nộp CV =====
const applySectionEl = document.getElementById("apply-section");
const applyFormEl = document.getElementById("apply-form");
const applySubmitBtn = document.getElementById("apply-submit-btn");
const cvInputEl = document.getElementById("apply-cv");
const dropzoneEl = document.getElementById("apply-dropzone");
const cvLabelEl = document.getElementById("apply-cv-label");

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_PATTERN = /^[0-9+\-. ]+$/;

/** Quy tắc khớp với kiểm tra phía backend (tài liệu Hướng dẫn phát triển Frontend, Mục 4.1). Trả "" nếu hợp lệ. */
const fieldValidators = {
  full_name: (v) => {
    if (!v) return "Vui lòng nhập họ tên";
    if (v.length < 2 || v.length > 150) return "Họ tên cần từ 2 đến 150 ký tự";
    return "";
  },
  email: (v) => {
    if (!v) return "Vui lòng nhập email";
    if (v.length > 255) return "Email tối đa 255 ký tự";
    if (!EMAIL_PATTERN.test(v)) return "Email chưa đúng định dạng";
    return "";
  },
  phone: (v) => {
    if (!v) return "";
    if (v.length > 30) return "Số điện thoại tối đa 30 ký tự";
    if (!PHONE_PATTERN.test(v)) return "Số điện thoại chỉ gồm chữ số, khoảng trắng và các ký tự + - .";
    return "";
  },
  // Kiểm tra định dạng và dung lượng tệp: mục 5.4
  cv_file: (file) => (file ? "" : "Vui lòng chọn tệp CV"),
};

let applyAttempted = false; // chỉ báo lỗi khi đang gõ sau lần bấm Gửi đầu tiên

function fieldValue(name) {
  if (name === "cv_file") return cvInputEl.files[0] ?? null;
  return applyFormEl.elements[name].value.trim();
}

/** Kiểm tra một trường, tô đỏ và hiện câu lỗi ngay dưới trường. */
function validateField(name) {
  const input = applyFormEl.elements[name];
  const message = fieldValidators[name](fieldValue(name));
  input.classList.toggle("is-invalid", !!message);
  input.parentElement.querySelector(".invalid-feedback").textContent = message;
  if (name === "cv_file") dropzoneEl.classList.toggle("is-invalid", !!message);
  return !message;
}

/** Kiểm tra cả form; trả về true nếu hợp lệ, ngược lại focus vào trường lỗi đầu tiên. */
function validateApplyForm() {
  const names = Object.keys(fieldValidators);
  const results = names.map(validateField);
  const firstInvalid = names.find((_, i) => !results[i]);
  if (firstInvalid) {
    (firstInvalid === "cv_file" ? cvInputEl : applyFormEl.elements[firstInvalid]).focus();
  }
  return !firstInvalid;
}

function updateCvLabel() {
  const file = cvInputEl.files[0];
  dropzoneEl.classList.toggle("has-file", !!file);
  if (file) {
    cvLabelEl.innerHTML = `<i class="bi bi-file-earmark-pdf me-1"></i><span class="fw-semibold"></span>`
      + ` <span class="text-muted small">(${(file.size / 1024 / 1024).toFixed(2)} MB) · bấm để đổi tệp</span>`;
    cvLabelEl.querySelector(".fw-semibold").textContent = file.name;
  } else {
    cvLabelEl.innerHTML = "Kéo thả tệp vào đây hoặc <u>chọn tệp</u>";
  }
}

function resetApplyForm() {
  applyFormEl.reset();
  applyAttempted = false;
  applyFormEl.querySelectorAll(".is-invalid").forEach((el) => el.classList.remove("is-invalid"));
  dropzoneEl.classList.remove("is-invalid", "is-dragover");
  updateCvLabel();
}

/** Ẩn form, footer quay về nút "Ứng tuyển" (gọi khi mở tin khác). */
function hideApplyForm() {
  applySectionEl.classList.add("d-none");
  applySubmitBtn.classList.add("d-none");
  resetApplyForm();
}

function openApplyForm() {
  applySectionEl.classList.remove("d-none");
  jobApplyBtn.classList.add("d-none");
  applySubmitBtn.classList.remove("d-none");
  applySectionEl.scrollIntoView({ behavior: "smooth", block: "start" });
  applyFormEl.elements.full_name.focus({ preventScroll: true });
}

jobApplyBtn.addEventListener("click", () => {
  if (currentJob?.status === "open") openApplyForm();
});

applyFormEl.addEventListener("input", (e) => {
  if (applyAttempted && e.target.name in fieldValidators) validateField(e.target.name);
});

cvInputEl.addEventListener("change", () => {
  updateCvLabel();
  if (applyAttempted) validateField("cv_file");
});

// Kéo thả tệp vào vùng dropzone
["dragenter", "dragover"].forEach((type) => dropzoneEl.addEventListener(type, (e) => {
  e.preventDefault();
  dropzoneEl.classList.add("is-dragover");
}));
["dragleave", "drop"].forEach((type) => dropzoneEl.addEventListener(type, () => {
  dropzoneEl.classList.remove("is-dragover");
}));
dropzoneEl.addEventListener("drop", (e) => {
  e.preventDefault();
  if (!e.dataTransfer.files.length) return;
  const dt = new DataTransfer();
  dt.items.add(e.dataTransfer.files[0]); // chỉ nhận 1 tệp
  cvInputEl.files = dt.files;
  cvInputEl.dispatchEvent(new Event("change"));
});

applyFormEl.addEventListener("submit", (e) => {
  e.preventDefault();
  applyAttempted = true;
  if (!validateApplyForm()) return;
  // Gửi hồ sơ lên server: mục 5.5
  showToast("Thông tin hợp lệ. Chức năng gửi hồ sơ sẽ có ở mục 5.5", "info");
});

jobListEl.addEventListener("click", (e) => {
  const card = e.target.closest(".job-card");
  if (card) openJobDetail(Number(card.dataset.jobId));
});

jobListEl.addEventListener("keydown", (e) => {
  const card = e.target.closest(".job-card");
  if (card && (e.key === "Enter" || e.key === " ")) {
    e.preventDefault();
    openJobDetail(Number(card.dataset.jobId));
  }
});

jobSearchEl.addEventListener("input", renderJobs);

loadJobs();
