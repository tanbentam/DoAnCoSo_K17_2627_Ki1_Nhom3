/**
 * api.js — API client dùng chung cho SmartRecruit AI.
 * Tải file này trước index.js và admin.js.
 */

const API_BASE = "http://127.0.0.1:8000";

const AUTH_TOKEN_KEY = "smartrecruit_token";
const AUTH_EMAIL_KEY = "smartrecruit_email";

// --- Quản lý phiên đăng nhập ---
const AuthSession = {
  getToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  },

  getEmail() {
    return localStorage.getItem(AUTH_EMAIL_KEY);
  },

  save(token, email) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    localStorage.setItem(AUTH_EMAIL_KEY, email);
  },

  clear() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_EMAIL_KEY);
  },
};

// --- Chuẩn hóa lỗi từ backend ---
function getErrorMessage(data, status) {
  const detail = data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => item.msg || "Dữ liệu không hợp lệ")
      .join("; ");
  }

  return `Yêu cầu thất bại (HTTP ${status}).`;
}

// --- Gọi API dùng chung ---
async function apiFetch(path, options = {}) {
  const {
    auth = false,
    responseType = "json",
    ...fetchOptions
  } = options;

  const headers = new Headers(fetchOptions.headers);
  const body = fetchOptions.body;

  // Trình duyệt tự đặt Content-Type cho FormData và URLSearchParams.
  if (body instanceof FormData || body instanceof URLSearchParams) {
    headers.delete("Content-Type");
  } else if (body != null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (auth) {
    const token = AuthSession.getToken();

    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  let response;

  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      headers,
    });
  } catch {
    throw new Error(
      "Không thể kết nối máy chủ. Hãy kiểm tra mạng và backend."
    );
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));

    if (response.status === 401 && auth) {
      AuthSession.clear();

      // admin.js sẽ lắng nghe sự kiện này để hiện lại form đăng nhập.
      window.dispatchEvent(new Event("auth:required"));
    }

    const error = new Error(
      getErrorMessage(data, response.status)
    );

    error.status = response.status;
    error.detail = data.detail;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  if (responseType === "blob") {
    return response.blob();
  }

  return response.json();
}

// --- Đăng nhập / đăng xuất ---
const AuthAPI = {
  async login(email, password) {
    const body = new URLSearchParams({
      username: email,
      password,
    });

    const result = await apiFetch("/api/auth/login", {
      method: "POST",
      body,
    });

    if (!result.access_token) {
      throw new Error("Máy chủ không trả về token đăng nhập.");
    }

    AuthSession.save(result.access_token, email);
    return result;
  },

  logout() {
    AuthSession.clear();
    window.dispatchEvent(new Event("auth:required"));
  },
};

// --- Tin tuyển dụng ---
const JobAPI = {
  list() {
    return apiFetch("/api/jobs");
  },

  listOpen() {
    return apiFetch("/api/jobs/open");
  },

  get(id) {
    return apiFetch(`/api/jobs/${encodeURIComponent(id)}`);
  },

  create(data) {
    return apiFetch("/api/jobs", {
      method: "POST",
      auth: true,
      body: JSON.stringify(data),
    });
  },

  update(id, data) {
    return apiFetch(`/api/jobs/${encodeURIComponent(id)}`, {
      method: "PUT",
      auth: true,
      body: JSON.stringify(data),
    });
  },

  close(id) {
    return apiFetch(`/api/jobs/${encodeURIComponent(id)}/close`, {
      method: "PATCH",
      auth: true,
    });
  },
};

// --- Hồ sơ ứng tuyển ---
const ApplicationAPI = {
  listByJob(jobId) {
    const query = new URLSearchParams({
      job_id: String(jobId),
      sort_by: "score_desc",
      limit: "500",
    });

    return apiFetch(`/api/applications?${query}`, {
      auth: true,
    });
  },

  updateStatus(id, status) {
    return apiFetch(
      `/api/applications/${encodeURIComponent(id)}/status`,
      {
        method: "PATCH",
        auth: true,
        body: JSON.stringify({ status }),
      }
    );
  },

  getDetail(id) {
    return apiFetch(
      `/api/applications/${encodeURIComponent(id)}`,
      { auth: true }
    );
  },

  getAnalysis(id) {
    return apiFetch(
      `/api/applications/${encodeURIComponent(id)}/ai-analysis`,
      { auth: true }
    );
  },

  getCV(id) {
    return apiFetch(
      `/api/applications/${encodeURIComponent(id)}/cv`,
      {
        auth: true,
        responseType: "blob",
      }
    );
  },

  apply(formData) {
    return apiFetch("/api/applications/apply", {
      method: "POST",
      body: formData,
    });
  },
};