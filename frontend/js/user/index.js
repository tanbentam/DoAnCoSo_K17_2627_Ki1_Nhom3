/**
 * SmartRecruit AI — Trang chủ ứng viên.
 *
 * - Danh mục đa ngành.
 * - Tìm kiếm, lọc và sắp xếp.
 * - Xem thêm danh mục và việc làm.
 * - Xem JD và gửi CV bằng các modal hiện có.
 *
 * Phụ thuộc: api.js và Bootstrap Modal.
 */

"use strict";

(() => {
  const GROUPS = [
    { id: "all", label: "Tất cả ngành nghề", icon: "▦" },
    { id: "technology", label: "CNTT & Phần mềm", icon: "IT" },
    { id: "marketing", label: "Marketing & Truyền thông", icon: "MK" },
    { id: "finance", label: "Tài chính & Ngân hàng", icon: "TC" },
    { id: "hr", label: "Nhân sự & Tuyển dụng", icon: "NS" },
    { id: "design", label: "Thiết kế & Sáng tạo", icon: "TK" },
    { id: "sales", label: "Kinh doanh & Bán hàng", icon: "KD" },
    { id: "data", label: "Dữ liệu & Trí tuệ nhân tạo", icon: "AI" },
    { id: "logistics", label: "Vận tải & Logistics", icon: "VT" },
    { id: "accounting", label: "Kế toán & Kiểm toán", icon: "KT" },
    { id: "education", label: "Giáo dục & Đào tạo", icon: "GD" },
    { id: "healthcare", label: "Y tế & Dược phẩm", icon: "YT" },
    { id: "engineering", label: "Kỹ thuật & Cơ khí", icon: "CK" },
    { id: "manufacturing", label: "Sản xuất & Chất lượng", icon: "SX" },
    { id: "construction", label: "Xây dựng & Kiến trúc", icon: "XD" },
    { id: "hospitality", label: "Du lịch & Nhà hàng", icon: "DL" },
    { id: "service", label: "Chăm sóc khách hàng", icon: "CS" },
    { id: "legal", label: "Pháp lý & Tuân thủ", icon: "PL" },
    { id: "administration", label: "Hành chính & Văn phòng", icon: "HC" },
    { id: "other", label: "Ngành nghề khác", icon: "…" },
  ];

  // Phân nhóm gần đúng theo tiêu đề; không thay thế trường ngành nghề
  // chính thức khi backend bổ sung trong tương lai.
  const TITLE_RULES = [
    ["accounting", /ke toan|kiem toan|accountant|accounting|auditor|bookkeeper/],
    ["hr", /nhan su|tuyen dung|human resources|recruiter|recruitment|talent acquisition|\bhr\b|\bhrbp\b/],
    ["legal", /phap ly|phap che|luat su|legal|lawyer|compliance|tuan thu/],
    ["healthcare", /bac si|dieu duong|duoc si|y te|duoc pham|ho sinh|doctor|nurse|pharmacist|medical|healthcare/],
    ["education", /giao vien|giang vien|gia su|dao tao|giao duc|teacher|lecturer|tutor|academic|education|trainer/],
    ["logistics", /logistics|van tai|giao nhan|kho van|kho hang|thu mua|xuat nhap khau|lai xe|tai xe|supply chain|warehouse|procurement|purchasing/],
    ["hospitality", /du lich|khach san|nha hang|dau bep|phuc vu|huong dan vien|hotel|hospitality|tourism|travel consultant|chef|waiter|barista/],
    ["construction", /xay dung|kien truc|giam sat cong trinh|ky su cau duong|civil engineer|construction|architect|quantity surveyor|noi that|interior/],
    ["design", /thiet ke|do hoa|sang tao|designer|design|creative|illustrator|animator|motion graphic|ui\/ux|ux\/ui/],
    ["marketing", /marketing|truyen thong|quang cao|noi dung|content|copywriter|seo|social media|public relations|brand manager/],
    ["sales", /kinh doanh|ban hang|sales|business development|account executive|account manager|tu van ban hang|bat dong san|moi gioi/],
    ["finance", /tai chinh|ngan hang|dau tu|tin dung|giao dich vien|finance|financial|banking|investment|credit analyst|insurance|bao hiem/],
    ["data", /du lieu|tri tue nhan tao|machine learning|deep learning|\bdata\b|artificial intelligence|\bai engineer\b|\bml engineer\b/],
    ["technology", /cong nghe thong tin|phan mem|lap trinh|developer|programmer|software|frontend|front-end|backend|back-end|fullstack|full-stack|devops|cybersecurity|an ninh mang|kiem thu phan mem|\bsre\b|\bit support\b/],
    ["manufacturing", /san xuat|nha may|quan ly chat luong|kiem soat chat luong|cong nhan|production|manufacturing|quality control|quality assurance|\bqa\b|\bqc\b/],
    ["engineering", /co khi|dien tu|tu dong hoa|bao tri|co dien|ky thuat vien|ky su dien|mechanical|electrical|electronics|automation|maintenance/],
    ["service", /cham soc khach hang|dich vu khach hang|tong dai|customer service|customer support|customer success|call center/],
    ["administration", /hanh chinh|van phong|thu ky|tro ly|le tan|administration|administrative|secretary|office manager|receptionist|executive assistant/],
  ];

  const SKILL_RULES = [
    ["accounting", /hach toan|bao cao thue|quyet toan|chuan muc ke toan|\bifrs\b|\bmisa\b/],
    ["legal", /luat doanh nghiep|luat lao dong|to tung|legal drafting/],
    ["healthcare", /cham soc benh nhan|kham chua benh|duoc ly|dieu tri/],
    ["logistics", /incoterms|hai quan|freight forwarding|quan ly kho/],
    ["construction", /\brevit\b|\bbim\b|du toan cong trinh|ket cau cong trinh/],
    ["design", /figma|adobe illustrator|photoshop|indesign|after effects/],
    ["marketing", /google ads|facebook ads|tiktok ads|content marketing|search engine optimization/],
    ["data", /pytorch|tensorflow|machine learning|deep learning|power bi|tableau/],
    ["technology", /fastapi|django|react|vuejs|angular|spring boot|laravel|kubernetes|terraform|node\.?js/],
    ["engineering", /solidworks|\bplc\b|\bscada\b|machining|gia cong co khi/],
  ];

  const PAGE_SIZE = 6;

  let ui;
  let modal;
  let jobs = [];
  let activeGroup = "all";
  let visibleLimit = PAGE_SIZE;
  let listLoaded = false;
  let listVersion = 0;
  let detailVersion = 0;
  let selectedJob = null;
  let currentJobId = null;
  let applyAfterLoad = false;
  let submitting = false;
  let submitted = false;
  let closing = false;
  let searchTimer;

  // ==================== HÀM DÙNG CHUNG ====================

  function element(tag, className = "", text) {
    const node = document.createElement(tag);

    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;

    return node;
  }

  function requiredElement(id) {
    const node = document.getElementById(id);

    if (!node) {
      throw new Error(`Thiếu phần tử #${id} trong index.html.`);
    }

    return node;
  }

  function normalize(value) {
    return String(value ?? "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase();
  }

  function timestamp(value) {
    if (!value) return null;

    const raw = String(value);
    const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw);
    const result = Date.parse(hasTimezone ? raw : `${raw}Z`);

    return Number.isNaN(result) ? null : result;
  }

  function formatDate(value) {
    const time = timestamp(value);

    if (time == null) return "Chưa cập nhật";

    return new Date(time).toLocaleDateString("vi-VN", {
      timeZone: "Asia/Ho_Chi_Minh",
    });
  }

  function experience(value) {
    if (value == null || value === "") return null;

    const years = Number(value);

    return Number.isFinite(years) && years >= 0
      ? years
      : null;
  }

  function experienceText(value) {
    const years = experience(value);

    if (years == null) return "Kinh nghiệm: chưa cập nhật";
    if (years === 0) return "Không yêu cầu kinh nghiệm";

    return `Tối thiểu ${years} năm kinh nghiệm`;
  }

  function classify(job) {
    const title = normalize(job.title);

    const titleMatch = TITLE_RULES.find(
      ([, pattern]) => pattern.test(title)
    );

    if (titleMatch) return titleMatch[0];

    const required = Array.isArray(job.required_skills)
      ? job.required_skills
      : [];

    const preferred = Array.isArray(job.preferred_skills)
      ? job.preferred_skills
      : [];

    const skills = normalize([...required, ...preferred].join(" "));

    return SKILL_RULES.find(
      ([, pattern]) => pattern.test(skills)
    )?.[0] || "other";
  }

  function groupLabel(id) {
    return GROUPS.find((group) => group.id === id)?.label ||
      "Ngành nghề khác";
  }

  function scrollTo(node) {
    node?.scrollIntoView({
      behavior: window.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches ? "auto" : "smooth",
      block: "start",
    });
  }

  function renderSkills(container, values, className, emptyText) {
    container.replaceChildren();

    const items = Array.isArray(values) ? values : [];

    if (!items.length) {
      container.append(
        element("span", "small text-muted", emptyText)
      );
      return;
    }

    items.forEach((skill) => {
      container.append(
        element("span", `badge ${className}`, String(skill))
      );
    });
  }

  // ==================== NHÓM NGHỀ ====================

  function initializeIndustrySelect() {
    if (!ui.industrySelect) return;

    ui.industrySelect.replaceChildren();

    GROUPS.forEach((group) => {
      const option = document.createElement("option");

      option.value = group.id;
      option.textContent = group.label;
      ui.industrySelect.append(option);
    });

    ui.industrySelect.value = activeGroup;
    ui.industrySelect.disabled = false;
  }

  function updateGroupSelection() {
    ui.groups.querySelectorAll("[data-group-id]").forEach((button) => {
      const active = button.dataset.groupId === activeGroup;

      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });

    if (ui.industrySelect) {
      ui.industrySelect.value = activeGroup;
    }
  }

  function selectGroup(id) {
    activeGroup = GROUPS.some((group) => group.id === id)
      ? id
      : "all";

    visibleLimit = PAGE_SIZE;
    updateGroupSelection();

    if (listLoaded) renderFeed();
  }

  function renderGroups() {
    const counts = new Map();

    jobs.forEach((job) => {
      const id = classify(job);
      counts.set(id, (counts.get(id) || 0) + 1);
    });

    const fragment = document.createDocumentFragment();

    GROUPS.forEach((group) => {
      const count = group.id === "all"
        ? jobs.length
        : counts.get(group.id) || 0;

      const button = element("button", "group-button");

      button.type = "button";
      button.dataset.groupId = group.id;

      const icon = element("span", "group-icon", group.icon);
      icon.setAttribute("aria-hidden", "true");

      button.append(
        icon,
        element("span", "group-name", group.label),
        element("span", "group-count", listLoaded ? String(count) : "—")
      );

      button.addEventListener("click", () => selectGroup(group.id));

      fragment.append(button);
    });

    ui.groups.replaceChildren(fragment);
    updateGroupSelection();

    if (ui.toggleGroups) {
      ui.toggleGroups.hidden = GROUPS.length <= 8;
    } else {
      // Trên HTML cũ chưa có nút mở rộng, luôn hiện đủ danh mục.
      ui.groups.classList.add("is-expanded");
    }
  }

  function toggleAllGroups() {
    const expanded = ui.groups.classList.toggle("is-expanded");

    ui.toggleGroups.setAttribute(
      "aria-expanded",
      String(expanded)
    );

    ui.toggleGroups.textContent = expanded
      ? "Thu gọn ngành nghề ↑"
      : "Xem tất cả ngành nghề ↗";
  }

  // ==================== TÌM KIẾM VÀ BỘ LỌC ====================

  function matchesExperience(job) {
    const years = experience(job.experience_years_min);

    switch (ui.experienceFilter.value) {
      case "zero":
        return years === 0;
      case "junior":
        return years != null && years > 0 && years <= 1;
      case "middle":
        return years != null && years > 1 && years <= 3;
      case "senior":
        return years != null && years > 3;
      default:
        return true;
    }
  }

  function filteredJobs() {
    const words = normalize(ui.search.value.trim())
      .split(/\s+/)
      .filter(Boolean);

    return jobs.filter((job) => {
      if (
        activeGroup !== "all" &&
        classify(job) !== activeGroup
      ) {
        return false;
      }

      if (!matchesExperience(job)) return false;

      const required = Array.isArray(job.required_skills)
        ? job.required_skills
        : [];

      const preferred = Array.isArray(job.preferred_skills)
        ? job.preferred_skills
        : [];

      const searchable = normalize([
        job.title,
        job.description,
        job.requirements,
        ...required,
        ...preferred,
      ].join(" "));

      return words.every((word) => searchable.includes(word));
    }).sort((a, b) => {
      const difference =
        (timestamp(b.created_at) ?? 0) -
        (timestamp(a.created_at) ?? 0) ||
        Number(b.id) - Number(a.id);

      return ui.sort.value === "oldest"
        ? -difference
        : difference;
    });
  }

  function applyFilters() {
    visibleLimit = PAGE_SIZE;

    if (listLoaded) renderFeed();
  }

  function clearFilters() {
    clearTimeout(searchTimer);

    activeGroup = "all";
    visibleLimit = PAGE_SIZE;

    ui.search.value = "";
    ui.experienceFilter.value = "all";
    ui.sort.value = "newest";

    updateGroupSelection();

    if (listLoaded) renderFeed();
  }

  function updateFilterLabels() {
    const labels = [];

    if (activeGroup !== "all") {
      labels.push(groupLabel(activeGroup));
    }

    if (ui.experienceFilter.value !== "all") {
      labels.push(
        ui.experienceFilter.selectedOptions[0]?.textContent || ""
      );
    }

    if (ui.search.value.trim()) {
      labels.push(`Từ khóa: ${ui.search.value.trim()}`);
    }

    ui.activeFilters.textContent = labels.join(" · ");
    ui.activeFilters.hidden = !labels.length;

    return labels.length > 0;
  }

  // ==================== HIỂN THỊ VIỆC LÀM ====================

  function renderState(title, description, buttonText, action, error = false) {
    const wrapper = element("div", "surface feed-state");
    const icon = element(
      "span",
      `state-icon${error ? " is-error" : ""}`,
      error ? "!" : "⌕"
    );

    icon.setAttribute("aria-hidden", "true");
    wrapper.setAttribute("role", error ? "alert" : "status");

    wrapper.append(
      icon,
      element("h2", "", title),
      element("p", "", description)
    );

    if (buttonText && action) {
      const button = element(
        "button",
        "btn btn-outline-primary",
        buttonText
      );

      button.type = "button";
      button.addEventListener("click", action);
      wrapper.append(button);
    }

    ui.list.replaceChildren(wrapper);
  }

  function createPost(job) {
    const article = element("article", "surface job-post");
    const header = element("div", "post-header");

    const avatar = element("span", "post-avatar", "S");
    avatar.setAttribute("aria-hidden", "true");

    const publisher = element("div", "post-publisher");

    publisher.append(
      element("strong", "", "Tin tuyển dụng"),
      element("span", "", `Đăng ngày ${formatDate(job.created_at)}`)
    );

    header.append(
      avatar,
      publisher,
      element("span", "post-open", "Đang tuyển")
    );

    const content = element("div", "post-content");
    const title = element("h2", "post-title");
    const titleButton = element(
      "button",
      "",
      job.title || "Vị trí tuyển dụng"
    );

    titleButton.type = "button";
    titleButton.addEventListener("click", () => openJob(job.id));
    title.append(titleButton);

    const metadata = element("div", "post-metadata");

    metadata.append(
      element("span", "post-category", groupLabel(classify(job))),
      element(
        "span",
        "",
        experienceText(job.experience_years_min)
      )
    );

    const rawDescription = String(job.description || "").trim();
    const description = rawDescription.length > 300
      ? `${rawDescription.slice(0, 300).trimEnd()}…`
      : rawDescription;

    const skillList = element(
      "div",
      "d-flex flex-wrap gap-2"
    );

    renderSkills(
      skillList,
      job.required_skills,
      "skill-badge",
      "Xem kỹ năng trong mô tả công việc."
    );

    content.append(
      title,
      metadata,
      element(
        "p",
        "post-description",
        description || "Xem chi tiết để tìm hiểu vị trí này."
      ),
      skillList
    );

    const footer = element("div", "post-footer");
    const detail = element(
      "button",
      "btn btn-outline-secondary",
      "Xem chi tiết"
    );
    const apply = element(
      "button",
      "btn btn-primary",
      "Ứng tuyển"
    );

    detail.type = "button";
    apply.type = "button";

    detail.addEventListener("click", () => openJob(job.id));
    apply.addEventListener("click", () => openJob(job.id, true));

    footer.append(
      element("span", "post-footer-note", "Ứng tuyển bằng CV PDF"),
      detail,
      apply
    );

    article.append(header, content, footer);
    return article;
  }

  function renderFeed() {
    const results = filteredJobs();
    const filtering = updateFilterLabels();

    ui.resultCount.textContent =
      `${results.length} việc làm phù hợp`;

    if (ui.moreJobs) ui.moreJobs.hidden = true;

    if (!results.length) {
      renderState(
        filtering
          ? "Chưa tìm thấy vị trí phù hợp"
          : "Chưa có tin tuyển dụng",
        filtering
          ? "Thử từ khóa khác hoặc mở rộng bộ lọc."
          : "Các cơ hội mới sẽ xuất hiện khi có tin đang mở.",
        filtering ? "Xóa bộ lọc" : "Tải lại",
        filtering ? clearFilters : loadJobs
      );
      return;
    }

    // HTML mới có nút Xem thêm: hiển thị theo từng nhóm 6 tin.
    // HTML cũ chưa có nút: hiển thị toàn bộ kết quả đã tải.
    const visibleJobs = ui.moreJobs
      ? results.slice(0, visibleLimit)
      : results;

    const fragment = document.createDocumentFragment();

    visibleJobs.forEach((job) => {
      fragment.append(createPost(job));
    });

    ui.list.replaceChildren(fragment);

    if (ui.moreJobs) {
      const remaining = results.length - visibleJobs.length;
      ui.moreJobs.hidden = remaining <= 0;
      ui.moreJobs.textContent = remaining > 0
        ? `Xem thêm ${Math.min(PAGE_SIZE, remaining)} việc làm`
        : "Đã hiển thị tất cả việc làm";
    }
  }

  async function loadJobs() {
    const version = ++listVersion;

    listLoaded = false;
    ui.list.setAttribute("aria-busy", "true");
    ui.resultCount.textContent = "Đang tải việc làm…";
    ui.activeFilters.hidden = true;

    if (ui.moreJobs) ui.moreJobs.hidden = true;

    const state = element("div", "surface feed-state");
    state.setAttribute("role", "status");

    const spinner = element("div", "spinner-border");
    spinner.setAttribute("aria-hidden", "true");

    state.append(
      spinner,
      element("p", "", "Đang tải cơ hội việc làm…")
    );

    ui.list.replaceChildren(state);

    try {
      const result = await JobAPI.listOpen();

      if (version !== listVersion) return;

      if (!Array.isArray(result)) {
        throw new Error("Dữ liệu việc làm không hợp lệ.");
      }

      jobs = result.filter(
        (job) => job?.id != null && job.status === "open"
      );

      listLoaded = true;
      visibleLimit = PAGE_SIZE;

      renderGroups();
      renderFeed();
    } catch (error) {
      if (version !== listVersion) return;

      ui.resultCount.textContent = "Chưa tải được việc làm";

      renderState(
        "Chưa thể tải bảng tin",
        error.message || "Vui lòng kiểm tra kết nối và thử lại.",
        "Thử lại",
        loadJobs,
        true
      );
    } finally {
      if (version === listVersion) {
        ui.list.setAttribute("aria-busy", "false");
      }
    }
  }

  // ==================== CHI TIẾT JD HIỆN TẠI ====================

  function setDetailState(state, message = "") {
    ui.detailLoading.hidden = state !== "loading";
    ui.detailError.hidden = state !== "error";
    ui.detailEmpty.hidden = state !== "empty";
    ui.detailContent.hidden = state !== "content";
    ui.detailErrorMessage.textContent = message;

    ui.modal.setAttribute(
      "aria-busy",
      String(state === "loading")
    );

    if (state !== "content") {
      ui.applicationSection.hidden = true;
    }

    updateFormControls();
  }

  function renderJob(job) {
    const open = job.status === "open";

    ui.detailTitle.textContent =
      job.title || "Chi tiết công việc";

    ui.detailStatus.textContent =
      open ? "Đang tuyển" : "Tin đã đóng";

    ui.detailStatus.className =
      `badge ${open ? "text-bg-success" : "text-bg-secondary"}`;

    ui.detailExperience.textContent =
      experienceText(job.experience_years_min);

    ui.detailDate.textContent = formatDate(job.created_at);
    ui.detailDescription.textContent =
      job.description || "Chưa cập nhật mô tả.";
    ui.detailRequirements.textContent =
      job.requirements || "Chưa cập nhật yêu cầu.";

    ui.detailClosed.hidden = open;

    renderSkills(
      ui.requiredSkills,
      job.required_skills,
      "skill-badge",
      "Chưa cập nhật kỹ năng bắt buộc."
    );

    renderSkills(
      ui.preferredSkills,
      job.preferred_skills,
      "preferred-badge",
      "Không có kỹ năng ưu tiên."
    );

    setDetailState("content");
  }

  function revealApplication() {
    if (
      selectedJob?.status !== "open" ||
      submitting ||
      submitted
    ) {
      return;
    }

    ui.applicationSection.hidden = false;
    scrollTo(ui.applicationSection);
    ui.name.focus({ preventScroll: true });
  }

  async function openJob(id, applyImmediately = false) {
    if (submitting || closing) return;

    const version = ++detailVersion;

    currentJobId = id;
    applyAfterLoad = applyImmediately;
    selectedJob = null;

    resetApplication();

    ui.detailTitle.textContent = "Chi tiết công việc";
    setDetailState("loading");
    modal.show();

    try {
      const job = await JobAPI.get(id);

      if (version !== detailVersion) return;

      if (!job) {
        setDetailState("empty");
        return;
      }

      if (
        typeof job !== "object" ||
        Array.isArray(job) ||
        job.id == null
      ) {
        throw new Error("Thông tin tuyển dụng không hợp lệ.");
      }

      selectedJob = job;
      renderJob(job);

      if (applyAfterLoad && job.status === "open") {
        revealApplication();
      }
    } catch (error) {
      if (version !== detailVersion) return;

      selectedJob = null;
      setDetailState(
        "error",
        error.message || "Không tải được chi tiết."
      );
    }
  }

  // ==================== GỬI HỒ SƠ HIỆN TẠI ====================

  function fieldError(input, message) {
    input.classList.toggle("is-invalid", Boolean(message));
    input.setAttribute("aria-invalid", String(Boolean(message)));
    requiredElement(`${input.id}-error`).textContent = message;
  }

  function applicationMessage(type, text) {
    ui.applicationMessage.className = `alert alert-${type}`;
    ui.applicationMessage.textContent = text;
    ui.applicationMessage.hidden = false;

    scrollTo(ui.applicationMessage);
  }

  function updateFormControls() {
    const locked = submitting || submitted;
    const open = selectedJob?.status === "open";

    ui.inputs.forEach((input) => {
      input.disabled = locked;
    });

    ui.submit.disabled = locked || !open;
    ui.apply.hidden = !open || submitted;
    ui.apply.disabled = locked || !open;

    ui.form.setAttribute("aria-busy", String(submitting));

    ui.modal.querySelectorAll('[data-bs-dismiss="modal"]')
      .forEach((button) => {
        button.disabled = submitting;
      });

    if (submitting) {
      const spinner = element(
        "span",
        "spinner-border spinner-border-sm me-2"
      );

      spinner.setAttribute("aria-hidden", "true");

      ui.submit.replaceChildren(
        spinner,
        document.createTextNode("Đang gửi…")
      );
    } else {
      ui.submit.textContent =
        submitted ? "Đã gửi hồ sơ" : "Gửi hồ sơ";
    }
  }

  function resetApplication() {
    if (submitting) return;

    submitted = false;
    ui.form.reset();

    ui.applicationSection.hidden = true;
    ui.applicationMessage.hidden = true;
    ui.applicationMessage.textContent = "";

    ui.inputs.forEach((input) => fieldError(input, ""));
    updateFormControls();
  }

  function validateApplication() {
    ui.name.value = ui.name.value.trim();
    ui.email.value = ui.email.value.trim();
    ui.phone.value = ui.phone.value.trim();

    const errors = new Map();

    if (ui.name.value.length < 2 || ui.name.value.length > 150) {
      errors.set(ui.name, "Họ tên phải có từ 2 đến 150 ký tự.");
    }

    if (
      !ui.email.value ||
      ui.email.value.length > 255 ||
      ui.email.validity.typeMismatch
    ) {
      errors.set(
        ui.email,
        "Vui lòng nhập email hợp lệ, tối đa 255 ký tự."
      );
    }

    if (
      ui.phone.value.length > 30 ||
      (ui.phone.value && !/^[0-9 +.\-]+$/.test(ui.phone.value))
    ) {
      errors.set(
        ui.phone,
        "Điện thoại tối đa 30 ký tự, chỉ gồm số, khoảng trắng, +, - và dấu chấm."
      );
    }

    const file = ui.cv.files[0];

    if (!file) {
      errors.set(ui.cv, "Vui lòng chọn CV.");
    } else if (!/\.pdf$/i.test(file.name)) {
      errors.set(ui.cv, "Chỉ chấp nhận PDF.");
    } else if (!file.size) {
      errors.set(ui.cv, "Tệp CV đang rỗng.");
    } else if (file.size >= 5 * 1024 * 1024) {
      errors.set(ui.cv, "CV phải nhỏ hơn 5 MB.");
    }

    ui.inputs.forEach((input) => {
      fieldError(input, errors.get(input) || "");
    });

    if (errors.size) {
      errors.keys().next().value.focus();
      return false;
    }

    return true;
  }

  async function submitApplication(event) {
    event.preventDefault();

    if (submitting || submitted) return;

    ui.applicationMessage.hidden = true;

    if (!validateApplication()) return;

    if (selectedJob?.status !== "open") {
      applicationMessage(
        "warning",
        "Tin tuyển dụng hiện không nhận hồ sơ."
      );
      return;
    }

    const data = new FormData();

    data.append("job_id", String(selectedJob.id));
    data.append("full_name", ui.name.value);
    data.append("email", ui.email.value);
    data.append("cv_file", ui.cv.files[0]);

    if (ui.phone.value) {
      data.append("phone", ui.phone.value);
    }

    submitting = true;
    updateFormControls();

    try {
      await ApplicationAPI.apply(data);

      submitted = true;

      applicationMessage(
        "success",
        "Hồ sơ đã được gửi, bộ phận tuyển dụng sẽ liên hệ với bạn."
      );
    } catch (error) {
      applicationMessage(
        "danger",
        error.message || "Không gửi được hồ sơ."
      );
    } finally {
      submitting = false;
      updateFormControls();
    }
  }

  // ==================== KHỞI TẠO TRANG ====================

  function initialize() {
    try {
      if (
        typeof JobAPI === "undefined" ||
        typeof ApplicationAPI === "undefined"
      ) {
        throw new Error("Không tải được api.js.");
      }

      if (!window.bootstrap?.Modal) {
        throw new Error("Không tải được Bootstrap.");
      }

      const ids = {
        groups: "job-group-list",
        experienceFilter: "experience-filter",
        clearFilters: "clear-filters",
        searchForm: "job-search-form",
        search: "job-search",
        sort: "job-sort",
        resultCount: "job-result-count",
        activeFilters: "active-filter-label",
        list: "job-list",
        modal: "job-detail-modal",
        detailTitle: "job-detail-title",
        detailLoading: "job-detail-loading",
        detailError: "job-detail-error",
        detailErrorMessage: "job-detail-error-message",
        detailRetry: "job-detail-retry",
        detailEmpty: "job-detail-empty",
        detailContent: "job-detail-content",
        detailStatus: "job-detail-status",
        detailExperience: "job-detail-experience",
        detailDate: "job-detail-date",
        detailDescription: "job-detail-description",
        detailRequirements: "job-detail-requirements",
        detailClosed: "job-detail-closed",
        requiredSkills: "job-detail-required-skills",
        preferredSkills: "job-detail-preferred-skills",
        apply: "job-detail-apply",
        applicationSection: "application-section",
        applicationMessage: "application-message",
        form: "application-form",
        name: "candidate-name",
        email: "candidate-email",
        phone: "candidate-phone",
        cv: "candidate-cv",
      };

      ui = {};

      Object.entries(ids).forEach(([key, id]) => {
        ui[key] = requiredElement(id);
      });

      // Các phần bổ sung của giao diện trang chủ mới.
      ui.industrySelect = document.getElementById("home-industry");
      ui.toggleGroups = document.getElementById("home-toggle-industries");
      ui.moreJobs = document.getElementById("home-more-jobs");

      ui.submit = ui.form.querySelector('button[type="submit"]');

      if (!ui.submit) {
        throw new Error("Thiếu nút gửi hồ sơ.");
      }

      ui.inputs = [ui.name, ui.email, ui.phone, ui.cv];

      modal = bootstrap.Modal.getOrCreateInstance(ui.modal);

      ui.searchForm.addEventListener("submit", (event) => {
        event.preventDefault();
        clearTimeout(searchTimer);
        applyFilters();

        scrollTo(
          document.getElementById("home-jobs-heading") ||
          ui.resultCount
        );
      });

      ui.search.addEventListener("input", () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(applyFilters, 180);
      });

      ui.experienceFilter.addEventListener("change", applyFilters);
      ui.sort.addEventListener("change", applyFilters);
      ui.clearFilters.addEventListener("click", clearFilters);

      ui.industrySelect?.addEventListener("change", () => {
        selectGroup(ui.industrySelect.value);
      });

      ui.toggleGroups?.addEventListener("click", toggleAllGroups);

      ui.moreJobs?.addEventListener("click", () => {
        visibleLimit += PAGE_SIZE;
        renderFeed();
      });

      ui.form.addEventListener("submit", submitApplication);
      ui.apply.addEventListener("click", revealApplication);

      ui.detailRetry.addEventListener("click", () => {
        if (currentJobId != null) {
          openJob(currentJobId, applyAfterLoad);
        }
      });

      ui.modal.addEventListener("hide.bs.modal", (event) => {
        if (submitting) {
          event.preventDefault();
          return;
        }

        closing = true;
        detailVersion += 1;
        selectedJob = null;
        ui.apply.disabled = true;
      });

      ui.modal.addEventListener("hidden.bs.modal", () => {
        resetApplication();
        currentJobId = null;
        applyAfterLoad = false;
        closing = false;
      });

      initializeIndustrySelect();
      renderGroups();
      resetApplication();
      loadJobs();
    } catch (error) {
      console.error("Không thể khởi tạo trang:", error);

      const host = document.getElementById("job-list");

      if (host) {
        const message = element(
          "div",
          "alert alert-danger",
          error.message
        );

        message.setAttribute("role", "alert");
        host.replaceChildren(message);
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      initialize,
      { once: true }
    );
  } else {
    initialize();
  }
})();