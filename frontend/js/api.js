/**
 * SmartRecruit AI — API client dùng chung.
 *
 * Đăng nhập: POST /api/auth/login
 * Xác minh OTP: POST /api/auth/verify-email
 *
 * HR và ứng viên dùng chung API nhưng lưu phiên riêng.
 * Tải file này trước các script chức năng.
 */

"use strict";

const API_BASE = "http://127.0.0.1:8000";

const FRONTEND_ROOT_URL = document.currentScript?.src
  ? new URL("../", document.currentScript.src)
  : new URL("/", location.href);

const AUTH_TOKEN_KEY = "smartrecruit_token";
const AUTH_EMAIL_KEY = "smartrecruit_email";
const AUTH_ROLE_KEY = "smartrecruit_role";

// ==================== PHIÊN HR / ADMIN ====================

const AuthSession = {
  getToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  },

  getEmail() {
    return localStorage.getItem(AUTH_EMAIL_KEY);
  },

  getRole() {
    return localStorage.getItem(AUTH_ROLE_KEY);
  },

  save(token, email, role) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    localStorage.setItem(AUTH_EMAIL_KEY, email);
    localStorage.setItem(AUTH_ROLE_KEY, role);
  },

  clear() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_EMAIL_KEY);
    localStorage.removeItem(AUTH_ROLE_KEY);
  },
};

// ==================== PHIÊN ỨNG VIÊN ====================

const CandidateSession = {
  key: "smartrecruit_candidate_session_v1",

  get() {
    try {
      const data = JSON.parse(
        sessionStorage.getItem(this.key)
      );

      return data && typeof data === "object"
        ? data
        : null;
    } catch {
      return null;
    }
  },

  getToken() {
    const token = this.get()?.access_token;

    return typeof token === "string" && token
      ? token
      : null;
  },

  save(data) {
    sessionStorage.setItem(
      this.key,
      JSON.stringify(data)
    );
  },

  clear() {
    sessionStorage.removeItem(this.key);
  },
};

// ==================== XỬ LÝ LỖI ====================

function createClientError(message, status = 422) {
  const error = new Error(message);
  error.status = status;

  return error;
}

function getErrorMessage(data, status) {
  const detail = data?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter((message) => typeof message === "string");

    if (messages.length) {
      return messages.join("; ");
    }
  }

  const messages = {
    400: "Yêu cầu chưa hợp lệ. Vui lòng kiểm tra lại.",
    401: "Phiên đăng nhập đã hết hạn hoặc không hợp lệ.",
    403: "Bạn không có quyền thực hiện thao tác này.",
    404: "Không tìm thấy dữ liệu yêu cầu.",
    409: "Dữ liệu bị trùng hoặc vừa thay đổi. Vui lòng kiểm tra lại.",
    413: "Tệp tải lên vượt quá dung lượng cho phép.",
    422: "Thông tin gửi lên chưa hợp lệ.",
    429: "Có quá nhiều yêu cầu. Vui lòng thử lại sau.",
  };

  return messages[status] || (
    status >= 500
      ? "Máy chủ đang gặp sự cố. Vui lòng thử lại sau."
      : `Yêu cầu thất bại (HTTP ${status}).`
  );
}

// ==================== REQUEST DÙNG CHUNG ====================

async function apiFetch(path, options = {}) {
  const {
    auth = false,
    responseType = "json",
    ...fetchOptions
  } = options;

  const candidateRequest = auth === "candidate";

  const session = candidateRequest
    ? CandidateSession
    : AuthSession;

  const requestToken = auth
    ? session.getToken()
    : null;

  const headers = new Headers(fetchOptions.headers);
  const body = fetchOptions.body;

  if (
    body instanceof FormData ||
    body instanceof URLSearchParams
  ) {
    // Trình duyệt tự thiết lập Content-Type phù hợp.
    headers.delete("Content-Type");
  } else if (
    body != null &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  if (
    responseType === "json" &&
    !headers.has("Accept")
  ) {
    headers.set("Accept", "application/json");
  }

  if (requestToken) {
    headers.set(
      "Authorization",
      `Bearer ${requestToken}`
    );
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

    throw createClientError(
      "Không thể kết nối máy chủ. Hãy kiểm tra mạng và backend.",
      0
    );
  }

  if (!response.ok) {
    const data = await response.json().catch(() => null);

    // Không xóa nhầm phiên mới khi request cũ trả về muộn.
    if (
      response.status === 401 &&
      auth &&
      session.getToken() === requestToken
    ) {
      session.clear();

      window.dispatchEvent(
        new Event(
          candidateRequest
            ? "candidate:auth-required"
            : "auth:required"
        )
      );
    }

    const error = createClientError(
      getErrorMessage(data, response.status),
      response.status
    );

    error.detail = data?.detail;

    const retryAfter = response.headers.get("Retry-After");

    if (retryAfter != null) {
      error.retryAfter = retryAfter;
    }

    throw error;
  }

  if (
    response.status === 204 ||
    response.status === 205
  ) {
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
    throw createClientError(
      "Máy chủ trả về dữ liệu không hợp lệ.",
      response.status
    );
  }
}

// ==================== XÁC THỰC DÙNG CHUNG ====================

const AuthAPI = {
  async login(email, password, expectedRole = "hr") {
    if (!["hr", "candidate"].includes(expectedRole)) {
      throw createClientError(
        "Loại đăng nhập không hợp lệ."
      );
    }

    if (
      typeof email !== "string" ||
      typeof password !== "string" ||
      !email.trim() ||
      !password
    ) {
      throw createClientError(
        "Vui lòng nhập email và mật khẩu."
      );
    }

    const body = new URLSearchParams({
      username: email.trim().toLowerCase(),
      password,
    });

    const result = await apiFetch("/api/auth/login", {
      method: "POST",
      body,
    });

    if (
      typeof result?.access_token !== "string" ||
      !result.access_token ||
      !result.account ||
      typeof result.account.email !== "string" ||
      !["admin", "hr", "candidate"].includes(result.role) ||
      result.account.role !== result.role
    ) {
      throw new Error(
        "Phản hồi đăng nhập không hợp lệ."
      );
    }

    const candidate = expectedRole === "candidate";

    const permitted = candidate
      ? result.role === "candidate"
      : ["hr", "admin"].includes(result.role);

    if (!permitted) {
      throw createClientError(
        candidate
          ? "Tài khoản này không phải tài khoản ứng viên."
          : "Tài khoản này không có quyền truy cập trang HR.",
        403
      );
    }

    if (
      candidate &&
      result.account.email_verified !== true
    ) {
      throw createClientError(
        "Vui lòng xác minh email bằng OTP trước khi đăng nhập.",
        403
      );
    }

    if (candidate) {
      CandidateSession.save(result);
    } else {
      AuthSession.save(
        result.access_token,
        result.account.email,
        result.role
      );
    }

    return result;
  },

  async register(data) {
    if (
      !data ||
      typeof data.full_name !== "string" ||
      typeof data.email !== "string" ||
      typeof data.password !== "string"
    ) {
      throw createClientError(
        "Vui lòng nhập đầy đủ thông tin đăng ký."
      );
    }

    return apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        full_name: data.full_name.trim(),
        email: data.email.trim().toLowerCase(),
        password: data.password,
      }),
    });
  },

  // Chỉ gọi API, không gọi lại chính hàm này.
  async verifyEmail(email, otp) {
    if (
      typeof email !== "string" ||
      !email.trim()
    ) {
      throw createClientError(
        "Vui lòng nhập email cần xác minh."
      );
    }

    // OTP là chuỗi để giữ số 0 ở đầu.
    if (
      typeof otp !== "string" ||
      !/^[0-9]{6}$/.test(otp.trim())
    ) {
      throw createClientError(
        "Mã OTP phải gồm đúng 6 chữ số."
      );
    }

    return apiFetch("/api/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
        otp: otp.trim(),
      }),
    });
  },

  async resendVerification(email) {
    if (
      typeof email !== "string" ||
      !email.trim()
    ) {
      throw createClientError(
        "Vui lòng nhập email đã đăng ký."
      );
    }

    return apiFetch("/api/auth/resend-verification", {
      method: "POST",
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
      }),
    });
  },

  me(role = "hr") {
    return apiFetch("/api/auth/me", {
      auth: role === "candidate" ? "candidate" : true,
    });
  },

  // Giữ tương thích với admin.js hiện tại.
  logout() {
    const token = AuthSession.getToken();

    AuthSession.clear();

    window.dispatchEvent(
      new Event("auth:required")
    );

    if (token) {
      void apiFetch("/api/auth/logout", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }).catch(() => {
        // Đã xóa phiên cục bộ.
        // Nếu không thu hồi được trên máy chủ, JWT hết hạn theo exp.
      });
    }
  },
};

// ==================== TÀI KHOẢN ỨNG VIÊN ====================

const CandidateAuthAPI = {
  guardInstalled: false,

  register(data) {
    return AuthAPI.register(data);
  },

  // OTP đúng → kiểm tra phản hồi → lưu phiên → trả thông tin tài khoản.
  async verifyEmail(email, otp) {
    const result = await AuthAPI.verifyEmail(email, otp);

    const valid =
      typeof result?.access_token === "string" &&
      result.access_token.length > 0 &&
      result.role === "candidate" &&
      result.account?.role === "candidate" &&
      result.account.email_verified === true &&
      typeof result.account.email === "string" &&
      result.account.email.toLowerCase() ===
        email.trim().toLowerCase();

    if (!valid) {
      throw new Error(
        "Chưa xác nhận được phiên đăng nhập. " +
        "Nếu email đã được xác minh, hãy đăng nhập bằng mật khẩu đã đăng ký."
      );
    }

    CandidateSession.save(result);

    return result.account;
  },

  resendVerification(email) {
    return AuthAPI.resendVerification(email);
  },

  async login(email, password) {
    const result = await AuthAPI.login(
      email,
      password,
      "candidate"
    );

    return result.account;
  },

  me() {
    return AuthAPI.me("candidate");
  },

  applications(skip = 0, jobId = null) {
    const query = new URLSearchParams({
      skip: String(skip),
      limit: "50",
    });

    if (jobId != null) {
      query.set("job_id", String(jobId));
    }

    return apiFetch(
      `/api/auth/me/applications?${query}`,
      { auth: "candidate" }
    );
  },

  redirectToLogin() {
    const url = new URL(
      "user/account/account.html",
      FRONTEND_ROOT_URL
    );

    if (location.pathname !== url.pathname) {
      url.searchParams.set(
        "next",
        location.pathname + location.search + location.hash
      );

      location.replace(url.href);
    }
  },

  async requireLogin() {
    if (!CandidateSession.getToken()) {
      this.redirectToLogin();
      return null;
    }

    try {
      const account = await this.me();

      if (
        account.role !== "candidate" ||
        account.email_verified !== true
      ) {
        CandidateSession.clear();
        this.redirectToLogin();
        return null;
      }

      if (!this.guardInstalled) {
        window.addEventListener(
          "candidate:auth-required",
          () => this.redirectToLogin()
        );

        this.guardInstalled = true;
      }

      return account;
    } catch (error) {
      if (
        error.status === 401 ||
        error.status === 403
      ) {
        CandidateSession.clear();
        this.redirectToLogin();
        return null;
      }

      // Lỗi mạng không đồng nghĩa với chưa đăng nhập.
      throw error;
    }
  },

  async logout() {
    const token = CandidateSession.getToken();

    await apiFetch("/api/auth/logout", {
      method: "POST",
      auth: "candidate",
    });

    if (CandidateSession.getToken() === token) {
      CandidateSession.clear();
    }
  },
};

// ==================== TIN TUYỂN DỤNG ====================

const JobAPI = {
  // Danh sách quản lý dành cho HR.
  list() {
    return apiFetch("/api/jobs", {
      auth: true,
    });
  },

  // Danh sách việc làm dành cho ứng viên.
  listOpen() {
    return apiFetch("/api/jobs/open", {
      auth: "candidate",
    });
  },

  // Mặc định phục vụ các lời gọi hiện tại trong admin.js.
  // Trang ứng viên có thể gọi JobAPI.get(id, "candidate").
  get(id, role = "hr") {
    return apiFetch(
      `/api/jobs/${encodeURIComponent(id)}`,
      {
        auth: role === "candidate"
          ? "candidate"
          : true,
      }
    );
  },

  create(data) {
    return apiFetch("/api/jobs", {
      method: "POST",
      auth: true,
      body: JSON.stringify(data),
    });
  },

  update(id, data) {
    return apiFetch(
      `/api/jobs/${encodeURIComponent(id)}`,
      {
        method: "PUT",
        auth: true,
        body: JSON.stringify(data),
      }
    );
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

// ==================== HỒ SƠ ỨNG TUYỂN ====================

const ApplicationAPI = {
  listByJob(jobId) {
    const query = new URLSearchParams({
      job_id: String(jobId),
      sort_by: "score_desc",
      limit: "500",
    });

    return apiFetch(
      `/api/applications?${query}`,
      { auth: true }
    );
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
      auth: "candidate",
      body: formData,
    });
  },
};