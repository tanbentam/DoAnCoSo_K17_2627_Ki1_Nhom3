/**
 * SmartRecruit AI — API client dùng chung.
 * Giữ dạng script thông thường để tương thích code hiện tại.
 * Tải trước user/index.js và admin/admin.js.
 */

"use strict";

const API_BASE = "http://127.0.0.1:8000";

const AUTH_TOKEN_KEY = "smartrecruit_token";
const AUTH_EMAIL_KEY = "smartrecruit_email";

// --- Phiên đăng nhập ---

const AuthSession = {
  getToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  },

  getEmail() {
    return localStorage.getItem(AUTH_EMAIL_KEY);
  },

  save(token, email) {
    localStorage.setItem(AUTH_EMAIL_KEY, email);
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  },

  clear() {
    localStorage.removeItem(AUTH_EMAIL_KEY);
    localStorage.removeItem(AUTH_TOKEN_KEY);
  },
};

// --- Xử lý lỗi ---

function getErrorMessage(data, status) {
  const detail = data?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter(Boolean);

    if (messages.length) {
      return messages.join("; ");
    }
  }

  switch (status) {
    case 401:
      return "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.";
    case 403:
      return "Bạn không có quyền thực hiện thao tác này.";
    case 404:
      return "Không tìm thấy dữ liệu yêu cầu.";
    case 413:
      return "Tệp tải lên vượt quá dung lượng cho phép.";
    case 422:
      return "Thông tin gửi lên chưa hợp lệ. Vui lòng kiểm tra lại.";
    case 429:
      return "Có quá nhiều yêu cầu. Vui lòng chờ rồi thử lại.";
    default:
      if (status >= 500) {
        return (
          "Máy chủ đang gặp sự cố. Vui lòng thử lại sau " +
          "hoặc liên hệ người quản trị."
        );
      }

      return `Yêu cầu thất bại (HTTP ${status}).`;
  }
}

// --- Request dùng chung ---

async function apiFetch(path, options = {}) {
  const {
    auth = false,
    responseType = "json",
    ...fetchOptions
  } = options;

  const headers = new Headers(fetchOptions.headers);
  const body = fetchOptions.body;
  const requestToken = auth ? AuthSession.getToken() : null;

  if (body instanceof FormData || body instanceof URLSearchParams) {
    // Trình duyệt tự tạo Content-Type và multipart boundary.
    headers.delete("Content-Type");
  } else if (body != null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (responseType === "json" && !headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  if (auth && requestToken) {
    headers.set("Authorization", `Bearer ${requestToken}`);
  }

  let response;

  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      headers,
    });
  } catch (cause) {
    if (cause?.name === "AbortError") {
      throw cause;
    }

    const error = new Error(
      "Không thể kết nối máy chủ. Hãy kiểm tra mạng và backend."
    );

    error.status = 0;
    throw error;
  }

  if (!response.ok) {
    // Backend có thể trả HTML/text khi gặp lỗi nội bộ.
    const data = await response.json().catch(() => null);

    if (
      response.status === 401 &&
      auth &&
      AuthSession.getToken() === requestToken
    ) {
      AuthSession.clear();
      window.dispatchEvent(new Event("auth:required"));
    }

    const error = new Error(
      getErrorMessage(data, response.status)
    );

    error.status = response.status;
    error.detail = data?.detail;
    throw error;
  }

  if (response.status === 204 || response.status === 205) {
    return null;
  }

  if (responseType === "blob") {
    return response.blob();
  }

  const text = await response.text();

  if (!text.trim()) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    const error = new Error(
      "Máy chủ trả về dữ liệu không hợp lệ. Vui lòng thử lại."
    );

    error.status = response.status;
    throw error;
  }
}

// --- Đăng nhập / đăng xuất ---

const AuthAPI = {
  async login(email, password) {
    const cleanEmail = email.trim();

    const body = new URLSearchParams({
      username: cleanEmail,
      password,
    });

    const result = await apiFetch("/api/auth/login", {
      method: "POST",
      body,
    });

    if (
      typeof result?.access_token !== "string" ||
      !result.access_token
    ) {
      throw new Error("Máy chủ không trả về token đăng nhập hợp lệ.");
    }

    AuthSession.save(result.access_token, cleanEmail);
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
    return apiFetch(
      `/api/jobs/${encodeURIComponent(id)}/close`,
      {
        method: "PATCH",
        auth: true,
      }
    );
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