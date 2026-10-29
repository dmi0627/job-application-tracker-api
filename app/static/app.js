const STATUSES = [
  ["wishlist", "Wishlist"],
  ["applied", "Applied"],
  ["oa", "OA"],
  ["interview", "Interview"],
  ["offer", "Offer"],
  ["rejected", "Rejected"],
  ["withdrawn", "Withdrawn"],
];

const statusLabels = Object.fromEntries(STATUSES);
const state = {
  page: 1,
  pageSize: 12,
  total: 0,
  company: "",
  status: "",
  sort: "date_desc",
};

const elements = {
  applicationGrid: document.querySelector("#application-grid"),
  companyFilter: document.querySelector("#company-filter"),
  emptyState: document.querySelector("#empty-state"),
  form: document.querySelector("#application-form"),
  formError: document.querySelector("#form-error"),
  formPanel: document.querySelector("#application-form-panel"),
  funnel: document.querySelector("#funnel"),
  funnelTotal: document.querySelector("#funnel-total"),
  loadingState: document.querySelector("#loading-state"),
  nextPage: document.querySelector("#next-page"),
  pageSummary: document.querySelector("#page-summary"),
  previousPage: document.querySelector("#previous-page"),
  responseRate: document.querySelector("#response-rate"),
  sortFilter: document.querySelector("#sort-filter"),
  statActive: document.querySelector("#stat-active"),
  statInterviews: document.querySelector("#stat-interviews"),
  statRecent: document.querySelector("#stat-recent"),
  statTotal: document.querySelector("#stat-total"),
  statusFilter: document.querySelector("#status-filter"),
  toast: document.querySelector("#toast"),
};

function populateStatusSelects() {
  const formStatus = elements.form.querySelector('select[name="status"]');
  formStatus.innerHTML = "";
  elements.statusFilter.innerHTML = '<option value="">All statuses</option>';
  for (const [value, label] of STATUSES) {
    formStatus.add(new Option(label, value));
    if (value) elements.statusFilter.add(new Option(label, value));
  }
  formStatus.value = "applied";
  elements.form.querySelector('input[name="date_applied"]').valueAsDate = new Date();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "No date";
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function formatSalary(application) {
  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
  if (application.salary_min && application.salary_max) {
    return `${formatter.format(application.salary_min)} – ${formatter.format(application.salary_max)}`;
  }
  if (application.salary_max) return `Up to ${formatter.format(application.salary_max)}`;
  if (application.salary_min) return `From ${formatter.format(application.salary_min)}`;
  return null;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      if (Array.isArray(body.detail)) message = "Please check the highlighted form fields.";
    } catch (_) {
      // Keep the status-based message when the response is not JSON.
    }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    elements.toast.hidden = true;
  }, 3200);
}

function renderStats(stats) {
  const active =
    (stats.by_status.wishlist || 0) +
    (stats.by_status.applied || 0) +
    (stats.by_status.oa || 0) +
    (stats.by_status.interview || 0);

  elements.statTotal.textContent = stats.total;
  elements.statActive.textContent = active;
  elements.statInterviews.textContent = stats.by_status.interview || 0;
  elements.statRecent.textContent = stats.applied_last_30_days;
  elements.responseRate.textContent = `${Math.round(stats.response_rate * 100)}%`;
  elements.funnelTotal.textContent = `${stats.total} total`;

  elements.funnel.innerHTML = STATUSES.map(([status, label]) => {
    const count = stats.by_status[status] || 0;
    const width = stats.total ? Math.max(2, Math.round((count / stats.total) * 100)) : 0;
    return `
      <div class="funnel-row" data-status="${status}">
        <label>${label}</label>
        <div class="funnel-track" aria-hidden="true">
          <div class="funnel-fill" style="width: ${count ? width : 0}%"></div>
        </div>
        <strong>${count}</strong>
      </div>`;
  }).join("");
}

function statusOptions(selected) {
  return STATUSES.map(
    ([value, label]) => `<option value="${value}" ${value === selected ? "selected" : ""}>${label}</option>`,
  ).join("");
}

function renderApplications(data) {
  state.total = data.total;
  elements.loadingState.hidden = true;
  elements.emptyState.hidden = data.items.length !== 0;
  elements.applicationGrid.innerHTML = data.items.map((application) => {
    const salary = formatSalary(application);
    const jobLink = application.job_url
      ? `<span>🔗 <a href="${escapeHtml(application.job_url)}" target="_blank" rel="noreferrer">Open posting</a></span>`
      : "";
    const notes = application.notes
      ? `<p class="notes">${escapeHtml(application.notes)}</p>`
      : "";

    return `
      <article class="application-card">
        <header>
          <div>
            <h3>${escapeHtml(application.company)}</h3>
            <p class="role">${escapeHtml(application.role)}</p>
          </div>
          <span class="status-pill ${escapeHtml(application.status)}">${escapeHtml(statusLabels[application.status])}</span>
        </header>
        <div class="meta-list">
          <span>📍 ${escapeHtml(application.location || "Location not specified")}</span>
          <span>🗓️ Applied ${formatDate(application.date_applied)}</span>
          ${salary ? `<span>💰 ${escapeHtml(salary)}</span>` : ""}
          ${jobLink}
        </div>
        ${notes}
        <div class="card-actions">
          <label>
            Move to
            <select data-status-for="${application.id}" aria-label="Change status for ${escapeHtml(application.company)}">
              ${statusOptions(application.status)}
            </select>
          </label>
          <button class="button button-danger" type="button" data-delete-for="${application.id}">Delete</button>
        </div>
      </article>`;
  }).join("");

  const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
  elements.pageSummary.textContent = `Page ${state.page} of ${totalPages} · ${state.total} applications`;
  elements.previousPage.disabled = state.page <= 1;
  elements.nextPage.disabled = state.page >= totalPages;

  elements.applicationGrid.querySelectorAll("[data-status-for]").forEach((select) => {
    select.addEventListener("change", async (event) => {
      const id = event.target.dataset.statusFor;
      try {
        await api(`/applications/${id}`, {
          method: "PATCH",
          body: JSON.stringify({ status: event.target.value }),
        });
        showToast("Application status updated.");
        await refresh();
      } catch (error) {
        showToast(error.message);
        await loadApplications();
      }
    });
  });

  elements.applicationGrid.querySelectorAll("[data-delete-for]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const id = event.target.dataset.deleteFor;
      if (!window.confirm("Delete this application record?")) return;
      try {
        await api(`/applications/${id}`, { method: "DELETE" });
        showToast("Application deleted.");
        await refresh();
      } catch (error) {
        showToast(error.message);
      }
    });
  });
}

async function loadStats() {
  const stats = await api("/stats");
  renderStats(stats);
}

async function loadApplications() {
  elements.loadingState.hidden = false;
  const params = new URLSearchParams({
    page: state.page,
    page_size: state.pageSize,
    sort: state.sort,
  });
  if (state.company) params.set("company", state.company);
  if (state.status) params.set("status", state.status);

  const data = await api(`/applications?${params.toString()}`);
  renderApplications(data);
}

async function refresh() {
  try {
    await Promise.all([loadStats(), loadApplications()]);
  } catch (error) {
    elements.loadingState.hidden = true;
    showToast(error.message);
  }
}

function openForm() {
  elements.formPanel.hidden = false;
  elements.formPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  elements.form.querySelector('input[name="company"]').focus();
}

function closeForm() {
  elements.formPanel.hidden = true;
  elements.formError.textContent = "";
}

function formPayload(formData) {
  const payload = {};
  for (const field of ["company", "role", "location", "status", "date_applied", "job_url", "notes"]) {
    const value = String(formData.get(field) || "").trim();
    if (value) payload[field] = value;
  }
  for (const field of ["salary_min", "salary_max"]) {
    const value = formData.get(field);
    if (value !== "" && value !== null) payload[field] = Number(value);
  }
  return payload;
}

function wireEvents() {
  document.querySelector("#open-form-button").addEventListener("click", openForm);
  document.querySelector("#close-form-button").addEventListener("click", closeForm);

  let searchTimer;
  elements.companyFilter.addEventListener("input", (event) => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => {
      state.company = event.target.value.trim();
      state.page = 1;
      loadApplications().catch((error) => showToast(error.message));
    }, 220);
  });

  elements.statusFilter.addEventListener("change", (event) => {
    state.status = event.target.value;
    state.page = 1;
    loadApplications().catch((error) => showToast(error.message));
  });

  elements.sortFilter.addEventListener("change", (event) => {
    state.sort = event.target.value;
    state.page = 1;
    loadApplications().catch((error) => showToast(error.message));
  });

  elements.previousPage.addEventListener("click", () => {
    if (state.page > 1) {
      state.page -= 1;
      loadApplications().catch((error) => showToast(error.message));
    }
  });

  elements.nextPage.addEventListener("click", () => {
    state.page += 1;
    loadApplications().catch((error) => showToast(error.message));
  });

  elements.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    elements.formError.textContent = "";
    try {
      await api("/applications", {
        method: "POST",
        body: JSON.stringify(formPayload(new FormData(elements.form))),
      });
      elements.form.reset();
      populateStatusSelects();
      closeForm();
      state.page = 1;
      showToast("Application added.");
      await refresh();
    } catch (error) {
      elements.formError.textContent = error.message;
    }
  });
}

populateStatusSelects();
wireEvents();
refresh();
