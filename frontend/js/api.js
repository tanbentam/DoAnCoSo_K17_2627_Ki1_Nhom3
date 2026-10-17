/**
 * api.js — Centralised API client
 * All fetch() calls go through this module so that the base URL
 * can be changed in one place (e.g. when deploying to production).
 */

const API_BASE = "http://127.0.0.1:8000";

// --- Token đăng nhập HR (lưu trong localStorage) ---
const Auth = {
  TOKEN_KEY: "sr_token",
  EMAIL_KEY: "sr_email",

  getToken() { return localStorage.getItem(this.TOKEN_KEY); },
  getEmail() { return localStorage.getItem(this.EMAIL_KEY); },
  isLoggedIn() { return !!this.getToken(); },

  save(token, email) {
    localStorage.setItem(this.TOKEN_KEY, token);
    localStorage.setItem(this.EMAIL_KEY, email);
  },

  clear() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.EMAIL_KEY);
  },

  // admin.js gán hàm hiện màn hình đăng nhập vào đây; được gọi khi API HR trả 401
  onUnauthorized: null,
};

class ApiError extends Error {
  constructor(message, status, detail = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;   // 0 = không kết nối được máy chủ
    this.detail = detail;   // `detail` gốc từ backend
  }
}

/** Chuyển `detail` của FastAPI thành câu thông báo: chuỗi (400/404) hoặc mảng lỗi (422). */
function formatErrorDetail(detail, status) {
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((e) => {
        const field = Array.isArray(e.loc) ? e.loc.filter((p) => p !== "body" && p !== "query").join(".") : "";
        return field ? `${field}: ${e.msg}` : e.msg;
      })
      .join("; ");
  }
  return `Lỗi máy chủ (HTTP ${status})`;
}

/**
 * Gọi API.
 * - auth: true  → gắn `Authorization: Bearer <token>`; 401 thì xóa token và gọi Auth.onUnauthorized.
 * - raw:  true  → trả về Response gốc (dùng cho blob CV).
 * - body là FormData / URLSearchParams → không đặt Content-Type, trình duyệt tự thêm.
 */
async function apiFetch(path, { auth = false, raw = false, ...options } = {}) {
  const isJsonBody = options.body !== undefined
    && !(options.body instanceof FormData)
    && !(options.body instanceof URLSearchParams);

  const headers = {
    ...(isJsonBody ? { "Content-Type": "application/json" } : {}),
    ...(auth && Auth.getToken() ? { Authorization: `Bearer ${Auth.getToken()}` } : {}),
    ...options.headers,
  };

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new ApiError("Không kết nối được máy chủ. Vui lòng thử lại sau.", 0);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (response.status === 401 && auth) {
      Auth.clear();
      if (typeof Auth.onUnauthorized === "function") Auth.onUnauthorized();
    }
    throw new ApiError(formatErrorDetail(body.detail, response.status), response.status, body.detail ?? null);
  }

  if (raw) return response;
  if (response.status === 204) return null;
  return response.json();
}

/** Tạo query string, bỏ qua tham số rỗng. VD: toQuery({ job_id: 1, status: "" }) → "?job_id=1" */
function toQuery(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.append(k, v);
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

// --- Auth ---
const AuthAPI = {
  /** Đăng nhập HR: gửi form (không phải JSON), lưu token khi thành công. */
  async login(email, password) {
    const body = new URLSearchParams({ username: email, password });
    const data = await apiFetch("/api/auth/login", { method: "POST", body });
    Auth.save(data.access_token, email);
    return data;
  },
  logout() { Auth.clear(); },
};

// --- Jobs ---
const JobAPI = {
  listOpen: ()          => apiFetch("/api/jobs/open"),
  list:     (status)    => apiFetch(`/api/jobs${toQuery({ status })}`),
  get:      (id)        => apiFetch(`/api/jobs/${id}`),
  create:   (data)      => apiFetch("/api/jobs",       { auth: true, method: "POST", body: JSON.stringify(data) }),
  update:   (id, data)  => apiFetch(`/api/jobs/${id}`, { auth: true, method: "PUT",  body: JSON.stringify(data) }),
  close:    (id)        => apiFetch(`/api/jobs/${id}/close`, { auth: true, method: "PATCH" }),
};

// --- Applications ---
const ApplicationAPI = {
  /** params: job_id, status, min_score, max_score, sort_by, skip, limit */
  list:          (params)     => apiFetch(`/api/applications${toQuery(params)}`, { auth: true }),
  getDetail:     (id)         => apiFetch(`/api/applications/${id}`, { auth: true }),
  getAiAnalysis: (id)         => apiFetch(`/api/applications/${id}/ai-analysis`, { auth: true }),
  updateStatus:  (id, status) => apiFetch(`/api/applications/${id}/status`, {
    auth: true,
    method: "PATCH",
    body: JSON.stringify({ status }),
  }),
  /** Tệp CV gốc dạng Blob; dùng với URL.createObjectURL() rồi gán vào <iframe>. */
  getCvBlob: async (id) => (await apiFetch(`/api/applications/${id}/cv`, { auth: true, raw: true })).blob(),
  /** Nộp hồ sơ (multipart): formData gồm job_id, full_name, email, phone, cv_file. */
  apply: (formData) => apiFetch("/api/applications/apply", { method: "POST", body: formData }),
};
