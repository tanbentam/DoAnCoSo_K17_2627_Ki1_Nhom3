/**
 * SmartRecruit AI — Tài khoản ứng viên.
 *
 * Đăng ký → xác minh OTP → đăng nhập → xem hồ sơ.
 *
 * Phụ thuộc api.js:
 * - CandidateAuthAPI
 * - CandidateSession
 *
 * Không thay đổi menu, logo hoặc phiên HR.
 */

"use strict";

(() => {
  let ui;
  let busy = false;
  let loadingApplications = false;
  let loadedCount = 0;
  let generation = 0;

  let cooldownTimer = null;
  const resendDeadlines = new Map();

  const STATUS_LABELS = {
    applied: "Đã tiếp nhận hồ sơ",
    screening: "Đang sàng lọc hồ sơ",
    interview: "Đang ở vòng phỏng vấn",
    offer: "Đã có đề nghị tuyển dụng",
    rejected: "Không tiếp tục tuyển dụng",
  };

  function get(id) {
    const node = document.getElementById(id);

    if (!node) {
      throw new Error(`HTML thiếu phần tử #${id}.`);
    }

    return node;
  }

  function createElement(tag, className, text) {
    const node = document.createElement(tag);

    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);

    return node;
  }

  function normalizeEmail(value) {
    return String(value || "").trim().toLowerCase();
  }

  function showMessage(type, text) {
    ui.message.className = `alert alert-${type}`;
    ui.message.textContent = text;
    ui.message.hidden = false;
    ui.message.focus({ preventScroll: true });

    ui.message.scrollIntoView({
      behavior: "auto",
      block: "nearest",
    });
  }

  // ==================== CHỜ GỬI LẠI OTP ====================

  function cooldownSeconds(email) {
    const deadline = resendDeadlines.get(
      normalizeEmail(email)
    ) || 0;

    return Math.max(
      0,
      Math.ceil((deadline - Date.now()) / 1000)
    );
  }

  function updateCooldown() {
    if (!ui) return;

    const otpSeconds = cooldownSeconds(ui.otpEmail.value);
    const resendSeconds = cooldownSeconds(ui.resendEmail.value);

    ui.otpResend.disabled = busy || otpSeconds > 0;
    ui.resendSubmit.disabled = busy || resendSeconds > 0;

    ui.otpResend.textContent = otpSeconds > 0
      ? `Gửi lại sau ${otpSeconds}s`
      : "Gửi lại OTP";

    ui.resendSubmit.textContent = resendSeconds > 0
      ? `Chờ ${resendSeconds}s`
      : "Gửi OTP";

    const now = Date.now();

    for (const [email, deadline] of resendDeadlines) {
      if (deadline <= now) {
        resendDeadlines.delete(email);
      }
    }

    if (resendDeadlines.size === 0 && cooldownTimer) {
      window.clearInterval(cooldownTimer);
      cooldownTimer = null;
    }
  }

  function startCooldown(email, seconds = 60) {
    const duration = Number(seconds);

    const safeSeconds = Number.isFinite(duration)
      ? Math.max(60, Math.min(3600, duration))
      : 60;

    resendDeadlines.set(
      normalizeEmail(email),
      Date.now() + safeSeconds * 1000
    );

    if (!cooldownTimer) {
      cooldownTimer = window.setInterval(
        updateCooldown,
        1000
      );
    }

    updateCooldown();
  }

  // ==================== ĐIỀU KHIỂN GIAO DIỆN ====================

  function setBusy(value, action = "") {
    busy = value;

    ui.auth.querySelectorAll("input, button").forEach((node) => {
      node.disabled = value;
    });

    ui.logout.disabled = value;
    ui.auth.setAttribute("aria-busy", String(value));

    ui.loginSubmit.textContent =
      value && action === "login"
        ? "Đang đăng nhập…"
        : "Đăng nhập";

    ui.registerSubmit.textContent =
      value && action === "register"
        ? "Đang tạo tài khoản…"
        : "Tạo tài khoản";

    ui.otpSubmit.textContent =
      value && action === "verify"
        ? "Đang xác minh…"
        : "Xác minh email";

    updateCooldown();
  }

  function switchForm(register) {
    if (busy) return;

    ui.otpForm.hidden = true;
    ui.loginForm.hidden = register;
    ui.registerForm.hidden = !register;

    ui.showLogin.classList.toggle("is-active", !register);
    ui.showRegister.classList.toggle("is-active", register);

    ui.showLogin.setAttribute(
      "aria-pressed",
      String(!register)
    );

    ui.showRegister.setAttribute(
      "aria-pressed",
      String(register)
    );
  }

  function showOtpForm(email) {
    ui.loginForm.hidden = true;
    ui.registerForm.hidden = true;
    ui.otpForm.hidden = false;

    ui.showLogin.classList.remove("is-active");
    ui.showRegister.classList.remove("is-active");

    ui.showLogin.setAttribute("aria-pressed", "false");
    ui.showRegister.setAttribute("aria-pressed", "false");

    ui.otpEmail.value = normalizeEmail(email);
    ui.resendEmail.value = ui.otpEmail.value;
    ui.otpCode.value = "";

    updateCooldown();
  }

  function showSignedOut() {
    generation += 1;
    loadingApplications = false;
    loadedCount = 0;

    ui.auth.hidden = false;
    ui.profile.hidden = true;

    ui.applications.replaceChildren();
    ui.applications.setAttribute("aria-busy", "false");

    ui.more.hidden = true;
    ui.refresh.disabled = false;

    ui.loginPassword.value = "";
    ui.otpCode.value = "";
  }

  async function showSignedIn(account) {
    if (account?.role !== "candidate") {
      CandidateSession.clear();

      const error = new Error(
        "Tài khoản này không phải tài khoản ứng viên."
      );

      error.status = 403;
      throw error;
    }

    ui.auth.hidden = true;
    ui.profile.hidden = false;

    ui.name.textContent = account.full_name;
    ui.email.textContent = account.email;

    await loadApplications();
  }

  // ==================== HỒ SƠ ĐÃ NỘP ====================

  function formatDate(value) {
    if (!value) return "Chưa cập nhật";

    let raw = String(value);

    if (
      /^\d{4}-\d{2}-\d{2}[T ]/.test(raw) &&
      !/(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw)
    ) {
      raw = raw.replace(" ", "T") + "Z";
    }

    const date = new Date(raw);

    return Number.isNaN(date.getTime())
      ? "Chưa cập nhật"
      : date.toLocaleString("vi-VN", {
          timeZone: "Asia/Ho_Chi_Minh",
        });
  }

  function createApplicationCard(application) {
    const card = createElement("article", "ca-application");

    const badge = createElement(
      "span",
      "ca-status",
      STATUS_LABELS[application.status] ||
        "Trạng thái chưa xác định"
    );

    badge.dataset.status = application.status;

    const link = createElement(
      "a",
      "btn btn-outline-primary btn-sm mt-2",
      "Xem công việc"
    );

    const url = new URL(
      "../job/job-detail.html",
      location.href
    );

    url.searchParams.set("id", String(application.job_id));
    link.href = url.href;

    card.append(
      createElement(
        "h3",
        "",
        application.job_title || "Tin tuyển dụng"
      ),
      badge,
      createElement(
        "p",
        "small text-secondary",
        `Mã hồ sơ: #${application.application_id}`
      ),
      createElement(
        "p",
        "small text-secondary",
        `Ngày nộp: ${formatDate(application.created_at)}`
      ),
      createElement(
        "p",
        "small text-secondary",
        `Hồ sơ cập nhật: ${formatDate(application.updated_at)}`
      ),
      link
    );

    return card;
  }

  async function loadApplications(append = false) {
    if (loadingApplications || ui.profile.hidden) return;

    const version = generation;

    loadingApplications = true;
    ui.refresh.disabled = true;
    ui.more.disabled = true;

    ui.applications.setAttribute("aria-busy", "true");
    ui.listStatus.textContent = "Đang tải hồ sơ…";

    try {
      const result = await CandidateAuthAPI.applications(
        append ? loadedCount : 0
      );

      if (version !== generation) return;

      if (
        !Array.isArray(result?.items) ||
        !Number.isInteger(result.total) ||
        result.total < 0
      ) {
        throw new Error("Dữ liệu hồ sơ trả về không hợp lệ.");
      }

      if (!append) {
        ui.applications.replaceChildren();
        loadedCount = 0;
      }

      result.items.forEach((application) => {
        ui.applications.append(
          createApplicationCard(application)
        );
      });

      loadedCount += result.items.length;

      ui.more.hidden =
        loadedCount >= result.total ||
        result.items.length === 0;

      ui.listStatus.textContent = result.total === 0
        ? "Chưa có hồ sơ ứng tuyển liên kết với tài khoản này."
        : `Đang hiển thị ${loadedCount}/${result.total} hồ sơ.`;
    } catch (error) {
      if (version !== generation) return;

      if (error.status === 401) {
        showSignedOut();

        showMessage(
          "warning",
          "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại."
        );
      } else {
        ui.listStatus.textContent =
          "Chưa cập nhật được danh sách. Dữ liệu đang hiển thị có thể chưa mới nhất.";

        showMessage(
          "danger",
          error.message || "Không tải được hồ sơ."
        );
      }
    } finally {
      if (version === generation) {
        loadingApplications = false;

        ui.refresh.disabled = false;
        ui.more.disabled = false;
        ui.applications.setAttribute("aria-busy", "false");
      }
    }
  }

  // ==================== ĐĂNG NHẬP ====================

  async function handleLogin(event) {
    event.preventDefault();

    if (busy) return;

    ui.loginEmail.value = normalizeEmail(
      ui.loginEmail.value
    );

    if (!ui.loginForm.reportValidity()) return;

    ui.message.hidden = true;
    setBusy(true, "login");

    try {
      const account = await CandidateAuthAPI.login(
        ui.loginEmail.value,
        ui.loginPassword.value
      );

      ui.loginPassword.value = "";

      await showSignedIn(account);
    } catch (error) {
      showMessage(
        "danger",
        error.message || "Không đăng nhập được."
      );

      if (error.status === 403) {
        ui.resendEmail.value = ui.loginEmail.value;
      }
    } finally {
      setBusy(false);
    }
  }

  // ==================== ĐĂNG KÝ ====================

  async function handleRegister(event) {
    event.preventDefault();

    if (busy) return;

    ui.registerName.value = ui.registerName.value.trim();

    ui.registerEmail.value = normalizeEmail(
      ui.registerEmail.value
    );

    ui.registerConfirm.setCustomValidity(
      ui.registerPassword.value === ui.registerConfirm.value
        ? ""
        : "Mật khẩu nhập lại chưa khớp."
    );

    if (!ui.registerForm.reportValidity()) return;

    ui.message.hidden = true;
    setBusy(true, "register");

    try {
      const email = ui.registerEmail.value;

      const result = await CandidateAuthAPI.register({
        full_name: ui.registerName.value,
        email,
        password: ui.registerPassword.value,
      });

      ui.loginEmail.value = email;
      ui.registerPassword.value = "";
      ui.registerConfirm.value = "";

      showOtpForm(email);
startCooldown(email, result.resend_after || 60);

showMessage(
  "info",
  result.message || "Vui lòng nhập OTP được gửi đến email."
);
    } catch (error) {
      showMessage(
        "danger",
        error.message || "Không tạo được tài khoản."
      );
    } finally {
      setBusy(false);

      if (!ui.otpForm.hidden) {
        ui.otpCode.focus();
      }
    }
  }

  // ==================== GỬI LẠI OTP ====================

  async function requestOtp(email) {
    email = normalizeEmail(email);

    const remaining = cooldownSeconds(email);

    if (remaining > 0) {
      showMessage(
        "info",
        `Vui lòng chờ ${remaining} giây trước khi gửi lại OTP.`
      );
      return;
    }

    setBusy(true);

    try {
      const result =
        await CandidateAuthAPI.resendVerification(email);

      showOtpForm(email);
      startCooldown(email, result.resend_after || 60);

      showMessage(
        "info",
        result.message ||
          "Vui lòng kiểm tra email để nhận OTP."
      );
    } catch (error) {
      showMessage(
        "danger",
        error.message || "Không gửi lại được OTP."
      );
    } finally {
      setBusy(false);

      if (!ui.otpForm.hidden) {
        ui.otpCode.focus();
      }
    }
  }

  async function handleResend(event) {
    event.preventDefault();

    if (busy) return;

    ui.resendEmail.value = normalizeEmail(
      ui.resendEmail.value
    );

    if (!ui.resendForm.reportValidity()) return;

    await requestOtp(ui.resendEmail.value);
  }

  // ==================== XÁC MINH OTP ====================

  async function handleVerifyOtp(event) {
  event.preventDefault();

  if (busy) return;

  ui.otpEmail.value = normalizeEmail(
    ui.otpEmail.value
  );

  ui.otpCode.value = ui.otpCode.value.trim();

  if (!ui.otpForm.reportValidity()) return;

  ui.message.hidden = true;
  setBusy(true, "verify");

  let navigating = false;

  try {
    await CandidateAuthAPI.verifyEmail(
      ui.otpEmail.value,
      ui.otpCode.value
    );

    ui.otpCode.value = "";

    resendDeadlines.delete(ui.otpEmail.value);
    updateCooldown();

    showMessage(
      "success",
      "Tạo tài khoản thành công. Đang vào trang chủ…"
    );

    // Dùng hàm chuyển trang đã thêm ở bước trước nếu có.
    if (typeof redirectAfterLogin === "function") {
      redirectAfterLogin();
    } else {
      location.replace(
        new URL("../index.html", location.href).href
      );
    }

    navigating = true;
  } catch (error) {
    showMessage(
      "danger",
      error.message || "Không xác minh được OTP."
    );
  } finally {
    if (!navigating) {
      setBusy(false);
    }
  }
}

  // ==================== ĐĂNG XUẤT ====================

  async function handleLogout() {
    if (busy) return;

    setBusy(true);

    try {
      await CandidateAuthAPI.logout();

      showSignedOut();

      setBusy(false);
      switchForm(false);

      showMessage(
        "success",
        "Đã đăng xuất tài khoản ứng viên."
      );
    } catch (error) {
      if (error.status === 401) {
        CandidateSession.clear();
        showSignedOut();

        setBusy(false);
        switchForm(false);

        showMessage(
          "info",
          "Phiên đăng nhập đã kết thúc."
        );
      } else {
        showMessage(
          "danger",
          "Chưa xác nhận được đăng xuất trên máy chủ. Vui lòng thử lại."
        );
      }
    } finally {
      setBusy(false);
    }
  }

  // ==================== KHỞI TẠO ====================

  async function initialize() {
    ui = {
      message: get("account-message"),
      auth: get("auth-section"),
      profile: get("profile-section"),

      showLogin: get("show-login"),
      showRegister: get("show-register"),

      loginForm: get("candidate-login-form"),
      loginEmail: get("login-email"),
      loginPassword: get("login-password"),
      loginSubmit: get("login-submit"),

      registerForm: get("candidate-register-form"),
      registerName: get("register-name"),
      registerEmail: get("register-email"),
      registerPassword: get("register-password"),
      registerConfirm: get("register-confirm"),
      registerSubmit: get("register-submit"),

      otpForm: get("otp-form"),
      otpEmail: get("otp-email"),
      otpCode: get("otp-code"),
      otpSubmit: get("otp-submit"),
      otpResend: get("otp-resend"),
      otpBack: get("otp-back"),

      resendForm: get("resend-form"),
      resendEmail: get("resend-email"),
      resendSubmit: get("resend-submit"),

      name: get("account-name"),
      email: get("account-email"),
      logout: get("candidate-logout"),

      applications: get("candidate-applications"),
      listStatus: get("applications-status"),
      refresh: get("refresh-applications"),
      more: get("more-applications"),
    };

    if (
      typeof CandidateAuthAPI === "undefined" ||
      typeof CandidateSession === "undefined"
    ) {
      throw new Error(
        "Chưa tải được API tài khoản. Hãy kiểm tra api.js."
      );
    }

    ui.showLogin.addEventListener("click", () => {
      switchForm(false);
    });

    ui.showRegister.addEventListener("click", () => {
      switchForm(true);
    });

    ui.loginForm.addEventListener("submit", handleLogin);
    ui.registerForm.addEventListener("submit", handleRegister);
    ui.otpForm.addEventListener("submit", handleVerifyOtp);
    ui.resendForm.addEventListener("submit", handleResend);

    ui.logout.addEventListener("click", handleLogout);

    ui.refresh.addEventListener("click", () => {
      void loadApplications();
    });

    ui.more.addEventListener("click", () => {
      void loadApplications(true);
    });

    [ui.registerPassword, ui.registerConfirm].forEach((input) => {
      input.addEventListener("input", () => {
        ui.registerConfirm.setCustomValidity("");
      });
    });

    ui.otpCode.addEventListener("input", () => {
      ui.otpCode.value = ui.otpCode.value
        .replace(/[^0-9]/g, "")
        .slice(0, 6);
    });

    ui.otpEmail.addEventListener("input", updateCooldown);
    ui.resendEmail.addEventListener("input", updateCooldown);

    ui.otpResend.addEventListener("click", async () => {
      if (busy) return;

      ui.otpEmail.value = normalizeEmail(
        ui.otpEmail.value
      );

      if (!ui.otpEmail.reportValidity()) return;

      await requestOtp(ui.otpEmail.value);
    });

    ui.otpBack.addEventListener("click", () => {
      switchForm(false);
    });

    showSignedOut();
    switchForm(false);
    updateCooldown();

    // Không sử dụng liên kết xác minh cũ nữa.
    const oldVerification = new URLSearchParams(
      location.hash.slice(1)
    ).has("verify");

    if (oldVerification) {
      history.replaceState(
        null,
        "",
        location.pathname + location.search
      );

      showMessage(
        "info",
        "Hệ thống đã chuyển sang OTP. " +
        "Hãy dùng mục “Đã đăng ký nhưng chưa xác minh email?” để nhận mã mới."
      );
    }

    if (CandidateSession.getToken()) {
      setBusy(true);

      try {
        const account = await CandidateAuthAPI.me();
        await showSignedIn(account);
      } catch (error) {
        if (error.status === 401) {
          CandidateSession.clear();
        }

        showMessage(
          error.status === 401 ? "warning" : "danger",
          error.message ||
            "Không kiểm tra được phiên đăng nhập."
        );
      } finally {
        setBusy(false);
      }
    }
  }

  function start() {
    initialize().catch((error) => {
      console.error(
        "Không khởi tạo được trang tài khoản:",
        error
      );

      const box = document.getElementById("account-message");

      if (box) {
        box.className = "alert alert-danger";
        box.textContent = error.message;
        box.hidden = false;
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {
      once: true,
    });
  } else {
    start();
  }
})();