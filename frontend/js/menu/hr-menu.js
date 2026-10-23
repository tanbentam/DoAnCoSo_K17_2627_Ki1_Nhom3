/**
 * Nạp menu dành riêng cho HR.
 * Menu phải nằm trong khu vực được ẩn trước đăng nhập.
 * Backend vẫn chịu trách nhiệm xác thực quyền truy cập.
 */

"use strict";

(() => {
  const scriptUrl = document.currentScript?.src;
  if (!scriptUrl) return;

  const root = new URL("../../", scriptUrl);
  const templateUrl = new URL("admin/menu/hr-menu.html", root);
  const allowedDirectory = new URL("admin/", root);

  async function loadMenu() {
    const host = document.querySelector('[data-role-menu="hr"]');
    if (!host || host.dataset.menuLoading === "true") return;

    host.dataset.menuLoading = "true";
    host.setAttribute("aria-busy", "true");
    host.textContent = "Đang tải menu…";

    try {
      const response = await fetch(templateUrl);

      if (!response.ok) {
        throw new Error(`Không tải được menu: HTTP ${response.status}`);
      }

      const html = await response.text();
      const parsed = new DOMParser().parseFromString(html, "text/html");
      const template = parsed.querySelector("nav");

      if (!template) {
        throw new Error("File menu HR thiếu thẻ nav.");
      }

      // Chỉ nạp HTML menu tĩnh trong dự án.
      const menu = document.importNode(template, true);
      const links = [...menu.querySelectorAll("[data-menu-page]")];

      links.forEach((link) => {
        const destination = new URL(link.dataset.menuPage, root);

        if (
          destination.origin !== root.origin ||
          !destination.pathname.startsWith(allowedDirectory.pathname)
        ) {
          throw new Error("Menu HR chứa đường dẫn sai vai trò.");
        }

        if (link.dataset.menuTarget) {
          destination.hash = link.dataset.menuTarget;
        }

        link.href = destination.href;
      });

      function updateActive() {
        const currentPageLinks = links.filter(
          (link) => new URL(link.href).pathname === location.pathname
        );

        const selected = currentPageLinks.find(
          (link) => new URL(link.href).hash === location.hash
        ) || currentPageLinks[0];

        links.forEach((link) => {
          if (link === selected) {
            link.setAttribute("aria-current", "location");
          } else {
            link.removeAttribute("aria-current");
          }
        });
      }

      host.replaceChildren(menu);
      updateActive();
      window.addEventListener("hashchange", updateActive);
    } catch (error) {
      console.error("Lỗi menu HR:", error);

      const message = document.createElement("p");
      message.textContent = "Chưa tải được menu HR.";

      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "btn btn-outline-primary btn-sm";
      retry.textContent = "Thử lại";
      retry.addEventListener("click", loadMenu);

      host.replaceChildren(message, retry);
    } finally {
      host.dataset.menuLoading = "false";
      host.setAttribute("aria-busy", "false");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadMenu, { once: true });
  } else {
    loadMenu();
  }
})();