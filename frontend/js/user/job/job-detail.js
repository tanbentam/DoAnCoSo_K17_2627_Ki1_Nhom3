/**
 * SmartRecruit AI — Chi tiết công việc và ứng tuyển.
 *
 * Phụ thuộc: api.js phải được tải trước.
 *
 * URL:
 *   job-detail.html?id=123
 *   job-detail.html?id=123#application
 *
 * Tiến độ chỉ phản ánh thao tác và phản hồi API thực tế.
 * Không tự suy đoán trạng thái xét tuyển của HR.
 * Không thay đổi menu hoặc logo.
 */

"use strict";

(() => {
  const MAX_CV_SIZE = 5 * 1024 * 1024;
  const LOAD_TIMEOUT = 20000;

  const state = {
    job: null,
    loading: false,
    validating: false,
    submitting: false,
    submitted: false,
    progress: "prepare",
    applicationId: null,
  };

  let ui;
  let progressUI;

  function get(id) {
    const element = document.getElementById(id);

    if (!element) {
      throw new Error(`HTML thiếu phần tử #${id}.`);
    }

    return element;
  }

  function createElement(tag, className, text) {
    const element = document.createElement(tag);

    if (className) element.className = className;
    if (text !== undefined) element.textContent = String(text);

    return element;
  }

  function isOpen() {
    return state.job?.status === "open";
  }

  function isBusy() {
    return state.validating || state.submitting;
  }

  function scrollToElement(element) {
    if (!element) return;

    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    element.scrollIntoView({
      behavior: reducedMotion ? "auto" : "smooth",
      block: "start",
    });
  }

  function formatDate(value) {
    if (!value) return "Chưa cập nhật";

    let raw = String(value).trim();

    if (
      /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(raw) &&
      !/(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw)
    ) {
      raw = raw.replace(" ", "T") + "Z";
    }

    const date = new Date(raw);

    return Number.isNaN(date.getTime())
      ? "Chưa cập nhật"
      : date.toLocaleDateString("vi-VN", {
          timeZone: "Asia/Ho_Chi_Minh",
        });
  }

  function experienceText(value) {
    if (value == null || value === "") {
      return "Kinh nghiệm chưa cập nhật";
    }

    const years = Number(value);

    if (!Number.isFinite(years) || years < 0) {
      return "Kinh nghiệm chưa cập nhật";
    }

    return years === 0
      ? "Không yêu cầu kinh nghiệm"
      : `Kinh nghiệm tối thiểu: ${years} năm`;
  }

  async function getWithTimeout(path) {
    const controller = new AbortController();

    const timer = window.setTimeout(
      () => controller.abort(),
      LOAD_TIMEOUT
    );

    try {
      return await apiFetch(path, {
        signal: controller.signal,
      });
    } finally {
      window.clearTimeout(timer);
    }
  }

  // ==================== TIẾN ĐỘ HỒ SƠ ====================

  function initializeProgress() {
    const heading = document.getElementById("process-heading");

    if (!heading) {
      console.warn("Thiếu #process-heading để hiển thị tiến độ hồ sơ.");
      return;
    }

    const section = heading.closest("section");
    if (!section) return;

    heading.textContent = "↗ Tiến độ hồ sơ của bạn";

    let list = document.getElementById("application-progress");

    // Chuyển phần quy trình tĩnh cũ thành tiến độ.
    if (!list) {
      list = createElement("ol", "application-progress");
      list.id = "application-progress";

      const oldList = section.querySelector(".process-list");

      if (oldList) {
        oldList.replaceWith(list);
      } else {
        section.append(list);
      }
    }

    let description = document.getElementById(
      "application-progress-message"
    );

    if (!description) {
      description = createElement("p", "muted");
      description.id = "application-progress-message";
      list.before(description);
    }

    description.setAttribute("role", "status");
    description.setAttribute("aria-live", "polite");
    description.setAttribute("aria-atomic", "true");

    let reference = document.getElementById("application-reference");

    if (!reference) {
      reference = createElement("p", "muted");
      reference.id = "application-reference";
      list.after(reference);
    }

    reference.hidden = true;
    list.setAttribute("aria-label", "Tiến độ gửi hồ sơ");

    const definitions = [
      {
        key: "prepare",
        number: "01",
        title: "Chuẩn bị hồ sơ",
        description: "Điền thông tin liên hệ và chọn CV PDF hợp lệ.",
      },
      {
        key: "send",
        number: "02",
        title: "Gửi hồ sơ",
        description: "Chờ xác nhận tiếp nhận từ máy chủ.",
      },
      {
        key: "received",
        number: "03",
        title: "Hệ thống tiếp nhận",
        description:
          "Bước này chưa xác nhận HR đã xem hoặc AI đã phân tích xong.",
      },
    ];

    list.replaceChildren();

    const steps = definitions.map((definition) => {
      const item = createElement("li");
      item.dataset.progressStep = definition.key;

      const number = createElement(
        "span",
        "progress-number",
        definition.number
      );
      number.setAttribute("aria-hidden", "true");

      const content = createElement("div");
      const label = createElement("span", "progress-label");

      content.append(
        createElement("h3", "", definition.title),
        createElement("p", "", definition.description),
        label
      );

      item.append(number, content);
      list.append(item);

      return { key: definition.key, item, label };
    });

    progressUI = { description, reference, steps };
  }

  function updateProgress(stage, applicationId = null) {
    state.progress = stage;
    state.applicationId = applicationId;

    if (!progressUI) return;

    const configurations = {
      prepare: {
        current: "prepare",
        completed: [],
        labels: ["Bước hiện tại", "Chưa thực hiện", "Chưa xác nhận"],
        text:
          "Bạn chưa gửi hồ sơ trong phiên hiện tại. " +
          "Hãy hoàn thiện thông tin và chọn CV.",
      },
      validating: {
        current: "prepare",
        completed: [],
        labels: ["Đang kiểm tra", "Chưa gửi", "Chưa xác nhận"],
        text: "Đang kiểm tra thông tin liên hệ và tệp CV trên thiết bị.",
      },
      sending: {
        current: "send",
        completed: ["prepare"],
        labels: ["Đã kiểm tra", "Đang gửi…", "Chờ xác nhận"],
        text:
          "Đang gửi hồ sơ đến máy chủ. " +
          "Vui lòng giữ trang mở để nhận kết quả.",
      },
      received: {
        current: null,
        completed: ["prepare", "send", "received"],
        labels: ["Hoàn tất", "Đã gửi", "Đã tiếp nhận"],
        text:
          "Máy chủ đã xác nhận tiếp nhận hồ sơ. " +
          "Bộ phận tuyển dụng sẽ xem xét và liên hệ khi phù hợp.",
      },
      duplicate: {
        current: null,
        completed: [],
        labels: [
          "Không cần gửi lại",
          "Đã nộp trước đó",
          "Đã có hồ sơ trong hệ thống",
        ],
        text:
          "Bạn đã nộp hồ sơ vào vị trí này rồi. " +
          "Hiện chưa tra cứu được trạng thái xét tuyển mới nhất.",
      },
      uncertain: {
        current: "send",
        completed: ["prepare"],
        labels: ["Đã kiểm tra", "Chưa rõ kết quả", "Chưa xác nhận"],
        text:
          "Chưa xác nhận được kết quả gửi. Bạn có thể thử lại; " +
          "hệ thống sẽ thông báo nếu hồ sơ đã được tiếp nhận.",
      },
      error: {
        current: "prepare",
        completed: [],
        labels: ["Kiểm tra lại", "Gửi chưa thành công", "Chưa xác nhận"],
        text:
          "Lần gửi vừa rồi chưa thành công. " +
          "Hãy kiểm tra thông báo lỗi trong biểu mẫu.",
      },
      closed: {
        current: null,
        completed: [],
        labels: ["Không khả dụng", "Đã đóng tuyển dụng", "Chưa xác nhận"],
        text: "Vị trí này đã ngừng nhận hồ sơ mới.",
      },
    };

    const config = configurations[stage];
    if (!config) return;

    progressUI.steps.forEach((step, index) => {
      step.item.removeAttribute("aria-current");

      step.item.classList.toggle(
        "is-complete",
        config.completed.includes(step.key)
      );

      step.item.classList.toggle(
        "is-warning",
        ["error", "uncertain", "duplicate"].includes(stage) &&
          step.key === "send"
      );

      if (step.key === config.current) {
        step.item.setAttribute("aria-current", "step");
      }

      step.label.textContent = config.labels[index];
    });

    progressUI.description.textContent = config.text;
    progressUI.reference.hidden = applicationId == null;

    progressUI.reference.textContent =
      applicationId == null ? "" : `Mã hồ sơ: #${applicationId}`;
  }

  // ==================== GIAO DIỆN ====================

  function updateControls() {
    ui.fields.disabled =
      state.loading ||
      isBusy() ||
      state.submitted ||
      !isOpen();

    ui.form.setAttribute("aria-busy", String(isBusy()));
    ui.apply.hidden = !isOpen() || state.submitted;
    ui.closed.hidden = !state.job || isOpen();

    ui.submit.textContent = state.submitting
      ? "Đang gửi hồ sơ…"
      : state.validating
        ? "Đang kiểm tra CV…"
        : state.submitted
          ? "Đã gửi hồ sơ"
          : state.loading
            ? "Đang tải công việc…"
            : !isOpen()
              ? "Đã ngừng nhận hồ sơ"
              : "Nộp hồ sơ";
  }

  function showPageState(title, description, allowRetry = false) {
    ui.pageState.hidden = false;
    ui.content.hidden = true;

    ui.stateTitle.textContent = title;
    ui.stateDescription.textContent = description;
    ui.spinner.hidden = !state.loading;
    ui.retry.hidden = !allowRetry;

    ui.pageState.setAttribute("aria-busy", String(state.loading));
  }

  function renderSkills(container, values, preferred = false) {
    container.replaceChildren();

    const skills = Array.isArray(values)
      ? [
          ...new Set(
            values
              .filter((value) => typeof value === "string")
              .map((value) => value.trim())
              .filter(Boolean)
          ),
        ]
      : [];

    if (!skills.length) {
      container.append(createElement("p", "muted", "Chưa cập nhật"));
      return;
    }

    skills.forEach((skill) => {
      container.append(
        createElement(
          "span",
          preferred ? "badge badge-green" : "badge badge-purple",
          skill
        )
      );
    });
  }

  function focusApplication() {
    if (ui.content.hidden) return;

    scrollToElement(ui.application);

    if (
      isOpen() &&
      !state.loading &&
      !isBusy() &&
      !state.submitted
    ) {
      ui.name.focus({ preventScroll: true });
    }
  }

  function renderJob() {
    const job = state.job;

    const title =
      typeof job.title === "string" && job.title.trim()
        ? job.title
        : "Vị trí tuyển dụng";

    document.title = `${title} | SmartRecruit AI`;
    ui.title.textContent = title;

    ui.status.textContent = isOpen() ? "Đang tuyển" : "Đã ngừng tuyển";
    ui.status.className = isOpen()
      ? "badge badge-green"
      : "badge badge-purple";

    const experience = experienceText(job.experience_years_min);

    ui.experience.textContent = experience;
    ui.experienceDescription.textContent = experience;
    ui.date.textContent = `Ngày đăng: ${formatDate(job.created_at)}`;

    ui.description.textContent =
      typeof job.description === "string" && job.description.trim()
        ? job.description
        : "Mô tả công việc chưa được cập nhật.";

    ui.requirements.textContent =
      typeof job.requirements === "string" && job.requirements.trim()
        ? job.requirements
        : "Yêu cầu ứng viên chưa được cập nhật.";

    [ui.description, ui.requirements].forEach((element) => {
      element.style.whiteSpace = "pre-wrap";
      element.style.overflowWrap = "anywhere";
    });

    renderSkills(ui.requiredSkills, job.required_skills);
    renderSkills(ui.preferredSkills, job.preferred_skills, true);

    ui.pageState.hidden = true;
    ui.content.hidden = false;

    updateProgress(isOpen() ? "prepare" : "closed");
  }

  async function loadRelatedJobs(currentJobId) {
    if (!ui.related) return;

    ui.related.setAttribute("aria-busy", "true");

    try {
      const jobs = await getWithTimeout("/api/jobs/open");

      if (!Array.isArray(jobs)) {
        throw new Error("Danh sách việc làm không hợp lệ.");
      }

      const items = jobs
        .filter(
          (item) =>
            item &&
            item.id != null &&
            item.status === "open" &&
            String(item.id) !== String(currentJobId)
        )
        .slice(0, 3);

      ui.related.replaceChildren();

      if (!items.length) {
        ui.related.append(
          createElement("p", "muted", "Chưa có vị trí khác đang tuyển.")
        );
        return;
      }

      items.forEach((item) => {
        const url = new URL("./job-detail.html", location.href);
        url.searchParams.set("id", String(item.id));

        const link = createElement("a", "related-job");
        link.href = url.href;

        link.append(
          createElement("strong", "", item.title || "Vị trí tuyển dụng"),
          createElement(
            "span",
            "",
            experienceText(item.experience_years_min)
          )
        );

        ui.related.append(link);
      });
    } catch {
      ui.related.replaceChildren(
        createElement(
          "p",
          "muted",
          "Chưa tải được các vị trí khác. Chọn “Xem tất cả” để xem danh sách."
        )
      );
    } finally {
      ui.related.setAttribute("aria-busy", "false");
    }
  }

  async function loadJob() {
    if (state.loading || isBusy() || state.submitted) return;

    const id = new URLSearchParams(location.search).get("id");

    if (!id || !/^[1-9]\d*$/.test(id)) {
      showPageState(
        "Đường dẫn công việc chưa hợp lệ",
        "Hãy quay lại danh sách việc làm và chọn “Xem chi tiết”."
      );
      return;
    }

    state.loading = true;
    state.job = null;
    updateControls();

    showPageState("Đang tải công việc", "Vui lòng chờ trong giây lát.");

    try {
      const result = await getWithTimeout(
        `/api/jobs/${encodeURIComponent(id)}`
      );

      if (
        !result ||
        typeof result !== "object" ||
        Array.isArray(result) ||
        String(result.id) !== id
      ) {
        throw new Error("Thông tin công việc trả về không hợp lệ.");
      }

      state.job = result;
      renderJob();

      void loadRelatedJobs(result.id);
    } catch (error) {
      state.job = null;
      state.loading = false;

      const notFound = error.status === 404;

      showPageState(
        notFound
          ? "Không tìm thấy công việc"
          : "Không tải được công việc",
        error.name === "AbortError"
          ? "Máy chủ phản hồi quá lâu. Vui lòng thử lại."
          : notFound
            ? "Tin tuyển dụng không tồn tại hoặc đã bị xóa."
            : error.message || "Vui lòng kiểm tra kết nối và thử lại.",
        !notFound
      );
    } finally {
      state.loading = false;
      ui.spinner.hidden = true;
      ui.pageState.setAttribute("aria-busy", "false");
      updateControls();
    }

    if (
      state.job &&
      ["#application", "#application-form"].includes(location.hash)
    ) {
      requestAnimationFrame(focusApplication);
    }
  }

  // ==================== KIỂM TRA HỒ SƠ ====================

  function setFieldError(input, text = "") {
    input.setAttribute("aria-invalid", String(Boolean(text)));
    input.classList.toggle("is-invalid", Boolean(text));

    get(`${input.id}-error`).textContent = text;
  }

  function showMessage(type, text) {
    ui.message.className = `notice notice-${type}`;
    ui.message.textContent = text;
    ui.message.hidden = false;

    ui.message.focus({ preventScroll: true });
    scrollToElement(ui.message);
  }

  async function getCVError(file) {
    if (!file) return "Vui lòng chọn CV định dạng PDF.";

    if (!/\.pdf$/i.test(file.name)) {
      return "Chỉ chấp nhận tệp có đuôi .pdf.";
    }

    if (file.size === 0) {
      return "Tệp CV đang rỗng. Vui lòng chọn tệp khác.";
    }

    if (file.size >= MAX_CV_SIZE) {
      return "Dung lượng CV phải nhỏ hơn 5 MB.";
    }

    try {
      const bytes = new Uint8Array(
        await file.slice(0, 5).arrayBuffer()
      );

      if (String.fromCharCode(...bytes) !== "%PDF-") {
        return "Tệp đã chọn không có định dạng PDF hợp lệ.";
      }
    } catch {
      return "Không đọc được CV. Vui lòng chọn lại tệp.";
    }

    return "";
  }

  async function validateForm() {
    [ui.name, ui.email, ui.phone, ui.cv].forEach((input) => {
      setFieldError(input);
    });

    ui.name.value = ui.name.value.trim();
    ui.email.value = ui.email.value.trim();
    ui.phone.value = ui.phone.value.trim();

    let firstInvalid = null;

    function invalid(input, text) {
      setFieldError(input, text);
      firstInvalid ||= input;
    }

    if (ui.name.value.length < 2 || ui.name.value.length > 150) {
      invalid(ui.name, "Họ và tên phải có từ 2 đến 150 ký tự.");
    }

    const emailChecker = document.createElement("input");
    emailChecker.type = "email";
    emailChecker.required = true;
    emailChecker.value = ui.email.value;

    if (
      ui.email.value.length > 255 ||
      !emailChecker.checkValidity()
    ) {
      invalid(ui.email, "Nhập email hợp lệ, tối đa 255 ký tự.");
    }

    if (
      ui.phone.value &&
      (
        ui.phone.value.length > 30 ||
        !/^[0-9+\s.-]+$/.test(ui.phone.value) ||
        !/\d/.test(ui.phone.value)
      )
    ) {
      invalid(
        ui.phone,
        "Số điện thoại tối đa 30 ký tự, chỉ gồm số, khoảng trắng, +, - hoặc dấu chấm."
      );
    }

    const cvError = await getCVError(ui.cv.files?.[0]);

    if (cvError) {
      invalid(ui.cv, cvError);
    }

    return firstInvalid;
  }

  // ==================== GỬI HỒ SƠ ====================

  async function submitApplication(event) {
    event.preventDefault();

    if (state.loading || isBusy() || state.submitted) return;

    if (!isOpen()) {
      updateProgress("closed");
      showMessage("warning", "Vị trí này hiện không nhận hồ sơ.");
      return;
    }

    ui.message.hidden = true;
    state.validating = true;

    updateProgress("validating");
    updateControls();

    try {
      const firstInvalid = await validateForm();

      if (firstInvalid) {
        state.validating = false;

        updateProgress("prepare");
        updateControls();

        firstInvalid.focus();
        scrollToElement(firstInvalid);
        return;
      }

      const formData = new FormData();

      formData.append("job_id", String(state.job.id));
      formData.append("full_name", ui.name.value);
      formData.append("email", ui.email.value);
      formData.append("cv_file", ui.cv.files[0]);

      if (ui.phone.value) {
        formData.append("phone", ui.phone.value);
      }

      state.validating = false;
      state.submitting = true;

      updateProgress("sending");
      updateControls();

      // Không tự đặt Content-Type cho FormData.
      const result = await ApplicationAPI.apply(formData);

      // Chỉ xác nhận tiếp nhận khi phản hồi khớp hồ sơ vừa gửi.
      if (
        !result ||
        !Number.isSafeInteger(result.application_id) ||
        result.application_id <= 0 ||
        String(result.job_id) !== String(state.job.id)
      ) {
        updateProgress("uncertain");

        showMessage(
          "warning",
          "Máy chủ đã phản hồi nhưng chưa xác nhận được mã hồ sơ. " +
          "Bạn có thể thử lại; hệ thống sẽ thông báo nếu đã có hồ sơ."
        );

        return;
      }

      state.submitted = true;

      updateProgress("received", result.application_id);

      showMessage(
        "success",
        `Hồ sơ #${result.application_id} đã được tiếp nhận. ` +
        "Bộ phận tuyển dụng sẽ xem xét và liên hệ khi phù hợp."
      );
    } catch (error) {
      const text =
        error.message || "Không gửi được hồ sơ. Vui lòng thử lại.";

      if (/đã nộp hồ sơ|already applied|already submitted/i.test(text)) {
        updateProgress("duplicate");

        showMessage(
          "warning",
          "Bạn đã nộp hồ sơ ứng tuyển vào vị trí này rồi."
        );
      } else if (
        error.status === 0 ||
        error.name === "AbortError" ||
        error.status >= 500 ||
        (error.status >= 200 && error.status < 300)
      ) {
        // Lỗi kết nối hoặc phản hồi không hợp lệ có thể xảy ra
        // sau khi máy chủ đã lưu hồ sơ.
        updateProgress("uncertain");

        showMessage(
          "warning",
          "Chưa xác nhận được kết quả gửi do lỗi kết nối hoặc phản hồi máy chủ. " +
          "Bạn có thể thử lại; hệ thống sẽ báo nếu hồ sơ đã được tiếp nhận."
        );
      } else {
        updateProgress("error");
        showMessage("error", text);
      }
    } finally {
      state.validating = false;
      state.submitting = false;
      updateControls();
    }
  }

  // ==================== KHỞI TẠO ====================

  function initialize() {
    try {
      ui = {
        pageState: get("page-state"),
        spinner: get("page-spinner"),
        stateTitle: get("state-title"),
        stateDescription: get("state-description"),
        retry: get("retry-button"),
        content: get("job-content"),

        title: get("job-title"),
        status: get("job-status"),
        experience: get("job-experience"),
        experienceDescription: get("experience-description"),
        date: get("job-date"),
        description: get("job-description"),
        requirements: get("job-requirements"),
        requiredSkills: get("required-skills"),
        preferredSkills: get("preferred-skills"),

        apply: get("apply-link"),
        closed: get("closed-notice"),
        application: get("application"),
        form: get("application-form"),
        fields: get("application-fields"),
        name: get("full-name"),
        email: get("email"),
        phone: get("phone"),
        cv: get("cv-file"),
        fileName: get("file-name"),
        submit: get("submit-button"),
        message: get("application-message"),

        related: document.getElementById("related-jobs"),
      };

      if (
        typeof apiFetch !== "function" ||
        typeof ApplicationAPI === "undefined" ||
        typeof ApplicationAPI.apply !== "function"
      ) {
        throw new Error(
          "Không tải được API client. Kiểm tra script ../../js/api.js."
        );
      }

      initializeProgress();

      ui.retry.addEventListener("click", loadJob);
      ui.form.addEventListener("submit", submitApplication);

      ui.apply.addEventListener("click", (event) => {
        event.preventDefault();
        history.replaceState(null, "", "#application");
        focusApplication();
      });

      [ui.name, ui.email, ui.phone].forEach((input) => {
        input.addEventListener("input", () => {
          setFieldError(input);
        });
      });

      ui.cv.addEventListener("change", async () => {
        const file = ui.cv.files?.[0];

        ui.fileName.textContent = file
          ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB`
          : "Chưa chọn tệp";

        setFieldError(ui.cv);

        const error = await getCVError(file);

        if (ui.cv.files?.[0] === file) {
          setFieldError(ui.cv, error);
        }
      });

      window.addEventListener("hashchange", () => {
        if (
          ["#application", "#application-form"].includes(location.hash)
        ) {
          focusApplication();
        }
      });

      window.addEventListener("beforeunload", (event) => {
        if (!state.submitting) return;

        event.preventDefault();
        event.returnValue = "";
      });

      updateControls();
      void loadJob();
    } catch (error) {
      console.error("Không khởi tạo được trang chi tiết:", error);

      const title = document.getElementById("state-title");
      const description = document.getElementById("state-description");
      const spinner = document.getElementById("page-spinner");
      const pageState = document.getElementById("page-state");

      if (title) title.textContent = "Chưa khởi tạo được trang";
      if (description) description.textContent = error.message;
      if (spinner) spinner.hidden = true;

      if (pageState) {
        pageState.hidden = false;
        pageState.setAttribute("aria-busy", "false");
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, {
      once: true,
    });
  } else {
    initialize();
  }
})();