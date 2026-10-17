/**
 * utils.js — Hàm dùng chung cho index.html và admin.html
 * Nạp trước api.js và các file logic trang.
 */

/** Escape chuỗi trước khi chèn vào innerHTML (chống XSS). Dữ liệu từ API luôn phải qua hàm này. */
function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Bỏ dấu tiếng Việt + chữ thường, để tìm "lap trinh" vẫn ra "Lập trình". */
function normalizeText(text) {
  return String(text ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

/**
 * Định dạng ngày giờ từ API (giờ UTC, không kèm múi giờ) sang giờ Việt Nam.
 * withTime = false → chỉ hiện ngày.
 */
function formatDate(value, withTime = true) {
  if (!value) return "";
  const hasZone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(value);
  const date = new Date(hasZone ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return "";
  return withTime
    ? date.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/** Làm tròn điểm để hiển thị; null nếu chưa có điểm. */
function formatScore(score) {
  return score === null || score === undefined ? null : Math.round(score);
}

/** Class huy hiệu điểm: ≥ 80 xanh, 50–79 vàng, < 50 đỏ (định nghĩa trong style.css). */
function scoreClass(score) {
  const s = Math.round(score ?? 0);
  if (s >= 80) return "badge-high";
  if (s >= 50) return "badge-medium";
  return "badge-low";
}

/**
 * Hiện thông báo nhỏ ở góc màn hình.
 * type: "success" | "danger" | "warning" | "info"
 */
function showToast(message, type = "success") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container position-fixed bottom-0 end-0 p-3";
    container.style.zIndex = "1100";
    document.body.appendChild(container);
  }

  const icons = { success: "bi-check-circle-fill", danger: "bi-x-circle-fill", warning: "bi-exclamation-triangle-fill", info: "bi-info-circle-fill" };
  const toast = document.createElement("div");
  toast.className = `toast align-items-center text-bg-${type} border-0`;
  toast.setAttribute("role", type === "danger" ? "alert" : "status");
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body d-flex align-items-center gap-2"><i class="bi ${icons[type] ?? icons.info}"></i><span></span></div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Đóng"></button>
    </div>`;
  toast.querySelector(".toast-body span").textContent = message;
  container.appendChild(toast);

  toast.addEventListener("hidden.bs.toast", () => toast.remove());
  new bootstrap.Toast(toast, { delay: type === "danger" ? 6000 : 4000 }).show();
}

/**
 * Hiển thị 1 trong 3 trạng thái bắt buộc vào container (thường là một .row):
 * - "loading": spinner
 * - "empty":   icon + thông báo thân thiện
 * - "error":   icon + thông báo + nút "Thử lại" (nếu có onRetry)
 */
function renderState(container, state, { message, hint, onRetry } = {}) {
  const presets = {
    loading: { icon: "", text: "Đang tải dữ liệu…" },
    empty:   { icon: "bi-inbox text-primary", text: "Chưa có dữ liệu" },
    error:   { icon: "bi-wifi-off text-danger", text: "Đã xảy ra lỗi" },
  };
  const p = presets[state] ?? presets.empty;

  container.innerHTML = `
    <div class="col-12">
      <div class="text-center text-muted py-5">
        ${state === "loading"
          ? '<div class="spinner-border text-primary" role="status"></div>'
          : `<i class="bi ${p.icon} fs-1"></i>`}
        <p class="fw-semibold mt-2 mb-1 state-message"></p>
        <p class="small mb-0 state-hint"></p>
        ${state === "error" && onRetry
          ? '<button type="button" class="btn btn-outline-primary btn-sm mt-3 state-retry"><i class="bi bi-arrow-clockwise me-1"></i>Thử lại</button>'
          : ""}
      </div>
    </div>`;

  container.querySelector(".state-message").textContent = message ?? p.text;
  container.querySelector(".state-hint").textContent = hint ?? "";
  container.querySelector(".state-retry")?.addEventListener("click", onRetry);
}
