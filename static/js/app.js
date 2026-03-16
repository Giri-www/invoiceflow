(function () {
  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  // 1) Sidebar toggle (mobile)
  function setupSidebar() {
    const sidebar = qs(".sidebar");
    const toggleBtn = qs("#sidebar-toggle");
    if (!sidebar || !toggleBtn) return;

    toggleBtn.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });

    document.addEventListener("click", function (e) {
      if (window.innerWidth > 768) return;
      if (!sidebar.classList.contains("open")) return;
      const withinSidebar = sidebar.contains(e.target);
      const withinToggle = toggleBtn.contains(e.target);
      if (!withinSidebar && !withinToggle) sidebar.classList.remove("open");
    });
  }

  // 2) Toast system
  window.showToast = function showToast(message, type = "success") {
    const container = qs("#toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type === "error" ? "error" : "success"}`;
    toast.innerHTML = `<div style="flex:1; color: var(--text-primary);">${escapeHtml(
      message
    )}</div>
    <button class="btn btn-secondary btn-sm" type="button" style="margin-left:auto;" aria-label="Close">Close</button>`;

    const closeBtn = toast.querySelector("button");
    closeBtn.addEventListener("click", function () {
      toast.remove();
    });

    container.appendChild(toast);
    setTimeout(function () {
      toast.remove();
    }, 4500);
  };

  function escapeHtml(str) {
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  // 3) Modal open/close
  window.openModal = function openModal(id) {
  const overlay = qs(`#${id}`);
  if (!overlay) return;
  overlay.classList.add("open");
  // Prevent background scrolling
  document.body.style.overflow = "hidden"; 
};

window.closeModal = function closeModal(id) {
  const overlay = qs(`#${id}`);
  if (!overlay) return;
  overlay.classList.remove("open");
  // Restore background scrolling
  document.body.style.overflow = ""; 
};
function setupModalCloseOnBackdrop() {
  document.addEventListener("click", function (e) {
    // Check if the clicked element IS a modal overlay
    if (e.target.classList.contains("modal-overlay")) {
      closeModal(e.target.id);
    }
  });
}
  // 4) Invoice line items
  function setupInvoiceBuilder() {
    const builder = qs("[data-invoice-builder]");
    if (!builder) return;

    const prefix = builder.getAttribute("data-formset-prefix") || "items";
    const addBtn = qs("[data-add-line-item]", builder);
    const template = qs("#line-item-template");
    const totalFormsInput = qs(`#id_${prefix}-TOTAL_FORMS`);

    function parseMoney(value) {
      const n = Number(String(value || "").replace(/[^\d.-]/g, ""));
      return Number.isFinite(n) ? n : 0;
    }

    function money(value) {
      return (Math.round((value + Number.EPSILON) * 100) / 100).toFixed(2);
    }

    function rowIsDeleted(row) {
      const del = qs(`input[name^="${prefix}-"][name$="-DELETE"]`, row);
      return del && del.checked;
    }

    function updateRowAmount(row) {
      if (!row || rowIsDeleted(row)) return;
      const qty = qs(`input[name^="${prefix}-"][name$="-quantity"]`, row);
      const unit = qs(`input[name^="${prefix}-"][name$="-unit_price"]`, row);
      const amount = qs(`input[name^="${prefix}-"][name$="-amount"]`, row);
      if (!qty || !unit || !amount) return;
      const a = parseMoney(qty.value) * parseMoney(unit.value);
      amount.value = money(a);
    }

    function updateTotals() {
      const rows = qsa("[data-line-item-row]", builder);
      let subtotal = 0;
      rows.forEach(function (row) {
        if (rowIsDeleted(row)) return;
        const amount = qs(`input[name^="${prefix}-"][name$="-amount"]`, row);
        subtotal += parseMoney(amount ? amount.value : 0);
      });

      const taxRateInput = qs("#id_tax_rate");
      const discountInput = qs("#id_discount");
      const taxRate = parseMoney(taxRateInput ? taxRateInput.value : 0);
      const discount = parseMoney(discountInput ? discountInput.value : 0);

      const tax = subtotal * (taxRate / 100);
      const total = subtotal + tax - discount;

      setText("#summary-subtotal", money(subtotal));
      setText("#summary-tax", money(tax));
      setText("#summary-discount", money(discount));
      setText("#summary-total", money(total));
    }

    function setText(selector, value) {
      const el = qs(selector);
      if (el) el.textContent = value;
    }

    function bindRow(row) {
      const qty = qs(`input[name^="${prefix}-"][name$="-quantity"]`, row);
      const unit = qs(`input[name^="${prefix}-"][name$="-unit_price"]`, row);
      const delBtn = qs("[data-remove-line-item]", row);
      const del = qs(`input[name^="${prefix}-"][name$="-DELETE"]`, row);

      [qty, unit].forEach(function (input) {
        if (!input) return;
        input.addEventListener("input", function () {
          updateRowAmount(row);
          updateTotals();
        });
      });

      if (delBtn) {
        delBtn.addEventListener("click", function () {
          if (del) {
            del.checked = true;
            row.style.display = "none";
          } else {
            row.remove();
            const currentTotal = parseInt(totalFormsInput.value, 10) || 0;
            totalFormsInput.value = Math.max(0, currentTotal - 1);
          }
          updateTotals();
        });
      }

      updateRowAmount(row);
    }

    qsa("[data-line-item-row]", builder).forEach(bindRow);

    const taxRateInput = qs("#id_tax_rate");
    const discountInput = qs("#id_discount");
    [taxRateInput, discountInput].forEach(function (input) {
      if (!input) return;
      input.addEventListener("input", updateTotals);
    });

    if (addBtn && template && totalFormsInput) {
      addBtn.addEventListener("click", function () {
        const index = parseInt(totalFormsInput.value, 10) || 0;
        const html = template.innerHTML.replaceAll("__prefix__", String(index));
        const tbody = qs("[data-line-items-body]", builder);
        if (!tbody) return;
        const temp = document.createElement("tbody");
        temp.innerHTML = html.trim();
        const row = temp.querySelector("tr");
        if (!row) return;
        tbody.appendChild(row);
        totalFormsInput.value = index + 1;
        bindRow(row);
        updateTotals();
      });
    }

    updateTotals();
  }

  // 5) Confirm delete dialogs
  function setupConfirmDelete() {
    qsa("[data-confirm]").forEach(function (el) {
      el.addEventListener("click", function (e) {
        const msg = el.getAttribute("data-confirm") || "Are you sure?";
        if (!window.confirm(msg)) e.preventDefault();
      });
    });

    qsa("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        const msg = form.getAttribute("data-confirm") || "Are you sure?";
        if (!window.confirm(msg)) e.preventDefault();
      });
    });
  }

  // 6) Active nav highlight
  function setupActiveNav() {
    const path = window.location.pathname || "/";
    qsa(".nav-item").forEach(function (item) {
      const href = item.getAttribute("href") || "";
      if (!href || href === "#") return;
      if (href === "/" && path === "/") item.classList.add("active");
      if (href !== "/" && path.startsWith(href)) item.classList.add("active");
    });
  }

  // 7) HTMX listeners for toasts
  function setupHtmxToasts() {
    document.body.addEventListener("toast", function (e) {
      const detail = e.detail || {};
      showToast(detail.message || "Done.", detail.type || "success");
    });

    document.body.addEventListener("modalClose", function (e) {
      const detail = e.detail || {};
      if (detail.id) closeModal(detail.id);
    });

    document.body.addEventListener("htmx:responseError", function () {
      showToast("Something went wrong. Please try again.", "error");
    });
  }

  function showDjangoMessagesOnLoad() {
    const container = qs("#server-messages");
    if (!container) return;
    qsa("[data-message]", container).forEach(function (node) {
      const message = node.getAttribute("data-message") || "";
      const level = node.getAttribute("data-level") || "";
      const type = level.includes("error") ? "error" : "success";
      showToast(message, type);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupSidebar();
    setupModalCloseOnBackdrop();
    setupConfirmDelete();
    setupActiveNav();
    setupInvoiceBuilder();
    setupHtmxToasts();
    showDjangoMessagesOnLoad();
  });
})();
