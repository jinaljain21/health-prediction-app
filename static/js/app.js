const API_URL = "/api/patients";
const FIELDS = ["full_name", "date_of_birth", "email", "glucose", "haemoglobin", "cholesterol"];
const RISK_BADGES = { Low: "text-bg-success", Moderate: "text-bg-warning", High: "text-bg-danger" };

const form = document.getElementById("patient-form");
const formTitle = document.getElementById("form-title");
const formAlert = document.getElementById("form-alert");
const cancelEditButton = document.getElementById("cancel-edit");
const submitButton = document.getElementById("submit-btn");
const submitLabel = document.getElementById("submit-label");
const submitSpinner = document.getElementById("submit-spinner");
const rows = document.getElementById("patient-rows");
const recordCount = document.getElementById("record-count");
const searchInput = document.getElementById("search");
const deleteModal = new bootstrap.Modal(document.getElementById("delete-modal"));
const summaryCards = document.querySelectorAll(".summary-card");

let patients = [];
let editingId = null;
let pendingDeleteId = null;
let riskFilter = "";

// ---------- API ----------

async function callApi(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  return { ok: response.ok, body };
}

async function loadPatients() {
  try {
    const { body } = await callApi(API_URL);
    patients = body.patients || [];
    renderTable();
  } catch {
    showToast("Could not load records. Is the server running?", "danger");
  }
}

// ---------- Summary cards ----------

function renderSummary() {
  document.getElementById("count-total").textContent = patients.length;
  ["High", "Moderate", "Low"].forEach((level) => {
    const count = patients.filter((p) => p.risk_level === level).length;
    document.getElementById(`count-${level}`).textContent = count;
  });
}

summaryCards.forEach((card) =>
  card.addEventListener("click", () => {
    riskFilter = card.dataset.risk;
    summaryCards.forEach((c) => c.classList.toggle("active", c === card));
    renderTable();
  })
);

// ---------- Table ----------

function renderTable() {
  renderSummary();
  const term = searchInput.value.trim().toLowerCase();
  const visible = patients.filter(
    (p) =>
      (!riskFilter || p.risk_level === riskFilter) &&
      (p.full_name.toLowerCase().includes(term) || p.email.toLowerCase().includes(term))
  );
  recordCount.textContent = patients.length;

  if (visible.length === 0) {
    const message = patients.length ? "No records match your filter." : "No records yet. Add a patient above.";
    rows.innerHTML = `<tr><td colspan="9" class="text-center text-body-secondary empty-state">${message}</td></tr>`;
    return;
  }

  rows.innerHTML = visible
    .map(
      (p) => `
      <tr class="${p.id === editingId ? "table-primary" : ""}">
        <td>${p.id}</td>
        <td class="fw-semibold">${escapeHtml(p.full_name)}</td>
        <td class="text-nowrap">${p.date_of_birth}</td>
        <td>${escapeHtml(p.email)}</td>
        <td class="text-end text-nowrap">${renderValue(p, "glucose")}</td>
        <td class="text-end text-nowrap">${renderValue(p, "haemoglobin")}</td>
        <td class="text-end text-nowrap">${renderValue(p, "cholesterol")}</td>
        <td class="remarks-cell">${renderRemarks(p)}</td>
        <td class="text-end text-nowrap">
          <button class="btn btn-sm btn-outline-primary" data-action="edit" data-id="${p.id}" title="Edit">
            <i class="bi bi-pencil"></i>
          </button>
          <button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="${p.id}" title="Delete">
            <i class="bi bi-trash"></i>
          </button>
        </td>
      </tr>`
    )
    .join("");
}

// Flags ("low" / "normal" / "high") are calculated on the server from reference_ranges.py
function renderValue(patient, field) {
  const flag = patient.flags[field];
  if (flag === "high") {
    return `<span class="value-high" title="Above normal range">${patient[field]} <i class="bi bi-arrow-up"></i></span>`;
  }
  if (flag === "low") {
    return `<span class="value-low" title="Below normal range">${patient[field]} <i class="bi bi-arrow-down"></i></span>`;
  }
  return patient[field];
}

function renderRemarks(patient) {
  if (patient.risk_level) {
    const badge = RISK_BADGES[patient.risk_level] || "text-bg-secondary";
    return `<span class="badge ${badge} me-1">${patient.risk_level} risk</span>${escapeHtml(patient.remarks)}`;
  }
  return `
    <span class="badge text-bg-secondary me-1">No prediction</span>
    <span class="text-body-secondary">${escapeHtml(patient.remarks || "")}</span>
    <button class="btn btn-link btn-sm p-0 ms-1" data-action="retry" data-id="${patient.id}">Retry AI</button>`;
}

rows.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  const actions = { edit: startEdit, delete: askDelete, retry: retryPrediction };
  actions[button.dataset.action](id, button);
});

searchInput.addEventListener("input", renderTable);

// ---------- Create / update ----------

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearErrors();

  const payload = Object.fromEntries(FIELDS.map((field) => [field, form.elements[field].value.trim()]));
  const url = editingId ? `${API_URL}/${editingId}` : API_URL;
  const method = editingId ? "PUT" : "POST";

  setBusy(true);
  try {
    const { ok, body } = await callApi(url, { method, body: JSON.stringify(payload) });
    if (!ok) {
      showErrors(body.errors || { record: body.error || "The record could not be saved." });
      return;
    }
    showToast(editingId ? "Record updated." : "Record created.", "success");
    if (body.warning) showToast(body.warning, "warning");
    resetForm();
    await loadPatients();
  } catch {
    showToast("Could not reach the server. Is it running?", "danger");
  } finally {
    setBusy(false);
  }
});

function startEdit(id) {
  const patient = patients.find((p) => p.id === id);
  if (!patient) return;

  clearErrors();
  editingId = id;
  FIELDS.forEach((field) => (form.elements[field].value = patient[field]));
  formTitle.textContent = `Edit Patient #${id}`;
  submitLabel.textContent = "Update Record";
  cancelEditButton.classList.remove("d-none");
  renderTable();
  document.getElementById("form-card").scrollIntoView({ behavior: "smooth" });
}

function resetForm() {
  form.reset();
}

// The Clear button and resetForm() both fire "reset", which also leaves edit mode
form.addEventListener("reset", () => {
  clearErrors();
  editingId = null;
  formTitle.textContent = "Add Patient";
  submitLabel.textContent = "Save & Predict";
  cancelEditButton.classList.add("d-none");
  renderTable();
});

cancelEditButton.addEventListener("click", resetForm);

function setBusy(busy) {
  submitButton.disabled = busy;
  submitSpinner.classList.toggle("d-none", !busy);
  if (busy) submitLabel.textContent = "Analysing with AI...";
  else submitLabel.textContent = editingId ? "Update Record" : "Save & Predict";
}

// ---------- Delete ----------

function askDelete(id) {
  const patient = patients.find((p) => p.id === id);
  if (!patient) return;
  pendingDeleteId = id;
  document.getElementById("delete-modal-body").innerHTML =
    `Delete record #${id} for <strong>${escapeHtml(patient.full_name)}</strong>? This cannot be undone.`;
  deleteModal.show();
}

document.getElementById("confirm-delete").addEventListener("click", async () => {
  const id = pendingDeleteId;
  deleteModal.hide();
  try {
    const { ok, body } = await callApi(`${API_URL}/${id}`, { method: "DELETE" });
    showToast(ok ? body.message : body.error || "Delete failed.", ok ? "success" : "danger");
    if (ok && editingId === id) resetForm();
    await loadPatients();
  } catch {
    showToast("Could not reach the server. Is it running?", "danger");
  }
});

// ---------- Retry AI ----------

async function retryPrediction(id, button) {
  button.disabled = true;
  button.textContent = "Retrying...";
  try {
    const { ok, body } = await callApi(`${API_URL}/${id}/remarks`, { method: "POST" });
    showToast(ok ? "AI prediction updated." : body.error, ok ? "success" : "danger");
  } catch {
    showToast("Could not reach the server. Is it running?", "danger");
  }
  await loadPatients();
}

// ---------- Validation messages ----------

function showErrors(errors) {
  const fieldErrors = Object.entries(errors).filter(([field]) => FIELDS.includes(field));

  fieldErrors.forEach(([field, message]) => {
    const input = form.elements[field];
    input.classList.add("is-invalid");
    input.parentElement.querySelector(".invalid-feedback").textContent = message;
  });

  const messages = [];
  if (errors.record) messages.push(escapeHtml(errors.record));
  if (fieldErrors.length) {
    messages.push(`Please correct ${fieldErrors.length} invalid field${fieldErrors.length > 1 ? "s" : ""}.`);
  }
  formAlert.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i>${messages.join(" ")}`;
  formAlert.classList.remove("d-none");
}

function clearErrors() {
  formAlert.classList.add("d-none");
  FIELDS.forEach((field) => form.elements[field].classList.remove("is-invalid"));
}

// ---------- Helpers ----------

function showToast(message, variant) {
  const toast = document.createElement("div");
  toast.className = `toast align-items-center text-bg-${variant} border-0`;
  toast.setAttribute("role", "alert");
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${escapeHtml(message)}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>`;
  document.getElementById("toasts").appendChild(toast);
  toast.addEventListener("hidden.bs.toast", () => toast.remove());
  new bootstrap.Toast(toast, { delay: 6000 }).show();
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

loadPatients();
