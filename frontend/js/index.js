/**
 * js/index.js — Candidate portal logic
 * Mục 5: Candidate Portal (5.1 danh sách việc làm, 5.2 modal chi tiết JD)
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

/** Mở form nộp CV — sẽ làm ở mục 5.3. */
function openApplyForm(job) {
  showToast(`Form ứng tuyển "${job.title}" sẽ có ở mục 5.3`, "info");
}

jobApplyBtn.addEventListener("click", () => {
  if (currentJob) openApplyForm(currentJob);
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
