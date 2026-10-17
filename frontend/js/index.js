/**
 * js/index.js — Candidate portal logic
 * Mục 5: Candidate Portal (5.1 danh sách việc làm)
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

/** Mở chi tiết JD — sẽ làm ở mục 5.2. */
function openJobDetail(jobId) {
  showToast(`Chi tiết tin #${jobId} sẽ có ở mục 5.2`, "info");
}

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
