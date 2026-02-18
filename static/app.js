const API = "";

// ── State ──────────────────────────────────────────
let cases = [];
let activeCase = null;
let documents = [];
let drafts = [];

// ── API helpers ────────────────────────────────────
async function api(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

// ── Toast notifications ────────────────────────────
function toast(message, type = "success") {
  const container = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ── Render: Sidebar case list ──────────────────────
function renderCaseList() {
  const list = document.getElementById("case-list");

  if (cases.length === 0) {
    list.innerHTML = `<div class="case-list-empty">No cases yet.<br>Create one to get started.</div>`;
    return;
  }

  list.innerHTML = cases
    .map(
      (c) => `
    <div class="case-item ${activeCase?.id === c.id ? "active" : ""}"
         onclick="selectCase(${c.id})">
      <div class="case-item-name">${esc(c.name)}</div>
      <div class="case-item-meta">${c.document_count} document${c.document_count !== 1 ? "s" : ""} &middot; ${formatDate(c.created_at)}</div>
    </div>`
    )
    .join("");
}

// ── Render: Main content ───────────────────────────
function renderMain() {
  const main = document.getElementById("main-content");

  if (!activeCase) {
    main.innerHTML = `<div class="main-empty">Select or create a case to begin</div>`;
    return;
  }

  const c = activeCase;
  main.innerHTML = `
    <div class="case-header">
      <div>
        <h2>${esc(c.name)}</h2>
        ${c.description ? `<div class="case-header-desc">${esc(c.description)}</div>` : ""}
      </div>
      <div class="case-header-actions">
        <button class="btn btn-danger btn-sm" onclick="deleteCase(${c.id})">Delete Case</button>
      </div>
    </div>

    <!-- Upload -->
    <div class="section">
      <div class="section-title">Upload Documents</div>
      <div class="upload-zone" id="upload-zone"
           onclick="document.getElementById('file-input').click()">
        <div class="upload-zone-icon">&#128196;</div>
        <div class="upload-zone-text"><strong>Click to upload</strong> or drag and drop</div>
        <div class="upload-zone-hint">PDF, PNG, JPG, TIFF — up to 50 MB</div>
      </div>
      <input type="file" id="file-input" hidden multiple
             accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
             onchange="handleUpload(event)">
    </div>

    <!-- Documents -->
    <div class="section">
      <div class="section-title">Documents (${documents.length})</div>
      ${renderDocTable()}
    </div>

    <!-- Draft Generation -->
    <div class="section">
      <div class="section-title">Generate Drafts</div>
      <div class="draft-actions">
        <button class="btn btn-secondary btn-sm" onclick="generateDraft('summary')">Summary</button>
        <button class="btn btn-secondary btn-sm" onclick="generateDraft('checklist')">Checklist</button>
        <button class="btn btn-secondary btn-sm" onclick="generateDraft('cover_letter')">Cover Letter</button>
      </div>
      ${renderDrafts()}
    </div>
  `;

  setupDragDrop();
}

// ── Render: Document table ─────────────────────────
function renderDocTable() {
  if (documents.length === 0) {
    return `<div class="empty-state">No documents uploaded yet</div>`;
  }

  const rows = documents
    .map(
      (d) => `
    <tr>
      <td><span class="doc-filename" onclick="showDocument(${d.id})">${esc(d.original_filename)}</span></td>
      <td>${d.category ? `<span class="badge badge-category">${esc(d.category)}</span>` : "—"}</td>
      <td><span class="badge badge-${d.status}">${statusIcon(d.status)} ${d.status}</span></td>
      <td>${d.page_count || "—"}</td>
      <td>${formatDate(d.created_at)}</td>
    </tr>`
    )
    .join("");

  return `
    <table class="doc-table">
      <thead>
        <tr>
          <th>File</th>
          <th>Category</th>
          <th>Status</th>
          <th>Pages</th>
          <th>Uploaded</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// ── Render: Drafts ─────────────────────────────────
function renderDrafts() {
  if (drafts.length === 0) {
    return `<div class="empty-state">No drafts generated yet</div>`;
  }

  return drafts
    .map(
      (d) => `
    <div class="draft-card">
      <div class="draft-card-header">
        <div class="draft-card-title">${esc(d.title)}</div>
        <div class="draft-card-date">${formatDate(d.created_at)}</div>
      </div>
      <div class="draft-card-content">${esc(d.content)}</div>
    </div>`
    )
    .join("");
}

// ── Actions ────────────────────────────────────────
async function loadCases() {
  try {
    cases = await api("/cases");
    renderCaseList();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function selectCase(id) {
  activeCase = cases.find((c) => c.id === id) || null;
  renderCaseList();

  if (!activeCase) {
    renderMain();
    return;
  }

  try {
    [documents, drafts] = await Promise.all([
      api(`/cases/${id}/documents`),
      api(`/cases/${id}/drafts`),
    ]);
  } catch (e) {
    documents = [];
    drafts = [];
    toast(e.message, "error");
  }

  renderMain();
}

function showNewCaseModal() {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.onclick = (e) => {
    if (e.target === overlay) overlay.remove();
  };

  overlay.innerHTML = `
    <div class="modal">
      <h3>New Case</h3>
      <div class="form-group">
        <label>Case Name</label>
        <input type="text" id="new-case-name" placeholder="e.g. Smith v. Johnson" autofocus>
      </div>
      <div class="form-group">
        <label>Description (optional)</label>
        <textarea id="new-case-desc" rows="3" placeholder="Brief description of the case..."></textarea>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
        <button class="btn btn-primary" onclick="createCase()">Create Case</button>
      </div>
    </div>`;

  document.body.appendChild(overlay);
  overlay.querySelector("input").focus();
}

async function createCase() {
  const name = document.getElementById("new-case-name").value.trim();
  const desc = document.getElementById("new-case-desc").value.trim();

  if (!name) {
    toast("Case name is required", "error");
    return;
  }

  try {
    const newCase = await api("/cases", {
      method: "POST",
      body: JSON.stringify({ name, description: desc }),
    });
    document.querySelector(".modal-overlay")?.remove();
    toast(`Case "${name}" created`);
    await loadCases();
    selectCase(newCase.id);
  } catch (e) {
    toast(e.message, "error");
  }
}

async function deleteCase(id) {
  if (!confirm("Delete this case and all its documents?")) return;

  try {
    await api(`/cases/${id}`, { method: "DELETE" });
    toast("Case deleted");
    activeCase = null;
    await loadCases();
    renderMain();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function handleUpload(event) {
  const files = event.target.files;
  if (!files.length || !activeCase) return;

  for (const file of files) {
    const form = new FormData();
    form.append("file", file);

    try {
      await fetch(`${API}/cases/${activeCase.id}/documents`, {
        method: "POST",
        body: form,
      }).then(async (res) => {
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail);
        }
        return res.json();
      });
      toast(`Uploaded: ${file.name}`);
    } catch (e) {
      toast(`Failed: ${file.name} — ${e.message}`, "error");
    }
  }

  event.target.value = "";
  await selectCase(activeCase.id);
  startPolling();
}

async function generateDraft(type) {
  if (!activeCase) return;

  const completedDocs = documents.filter((d) => d.status === "completed");
  if (completedDocs.length === 0) {
    toast("No completed documents to generate from", "error");
    return;
  }

  try {
    toast("Generating draft...");
    await api(`/cases/${activeCase.id}/generate`, {
      method: "POST",
      body: JSON.stringify({ draft_type: type }),
    });
    toast(`${type.replace("_", " ")} generated`);
    drafts = await api(`/cases/${activeCase.id}/drafts`);
    renderMain();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function showDocument(id) {
  try {
    const doc = await api(`/documents/${id}`);

    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.onclick = (e) => {
      if (e.target === overlay) overlay.remove();
    };

    overlay.innerHTML = `
      <div class="modal" style="max-width: 640px;">
        <h3>${esc(doc.original_filename)}</h3>
        <div class="modal-body">
          <div class="detail-panel">
            <div class="detail-row">
              <div class="detail-label">Status</div>
              <div class="detail-value"><span class="badge badge-${doc.status}">${statusIcon(doc.status)} ${doc.status}</span></div>
            </div>
            <div class="detail-row">
              <div class="detail-label">Category</div>
              <div class="detail-value">${doc.category ? `<span class="badge badge-category">${esc(doc.category)}</span>` : "—"}</div>
            </div>
            <div class="detail-row">
              <div class="detail-label">Pages</div>
              <div class="detail-value">${doc.page_count || "—"}</div>
            </div>
            <div class="detail-row">
              <div class="detail-label">File Type</div>
              <div class="detail-value">${esc(doc.file_type)}</div>
            </div>
            ${doc.error_message ? `
            <div class="detail-row">
              <div class="detail-label">Error</div>
              <div class="detail-value" style="color: var(--danger)">${esc(doc.error_message)}</div>
            </div>` : ""}
          </div>
          ${doc.raw_text ? `
          <div class="section-title" style="margin-top: 20px;">Extracted Text</div>
          <div class="detail-text">${esc(doc.raw_text)}</div>` : ""}
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Close</button>
        </div>
      </div>`;

    document.body.appendChild(overlay);
  } catch (e) {
    toast(e.message, "error");
  }
}

// ── Drag & Drop ────────────────────────────────────
function setupDragDrop() {
  const zone = document.getElementById("upload-zone");
  if (!zone) return;

  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("dragover");
  });

  zone.addEventListener("dragleave", () => {
    zone.classList.remove("dragover");
  });

  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    const input = document.getElementById("file-input");
    input.files = e.dataTransfer.files;
    input.dispatchEvent(new Event("change"));
  });
}

// ── Polling for processing status ──────────────────
let pollTimer = null;

function startPolling() {
  stopPolling();
  pollTimer = setInterval(async () => {
    if (!activeCase) return stopPolling();

    const hasPending = documents.some(
      (d) => d.status === "pending" || d.status === "processing"
    );
    if (!hasPending) return stopPolling();

    documents = await api(`/cases/${activeCase.id}/documents`);
    renderMain();
  }, 3000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

// ── Helpers ────────────────────────────────────────
function esc(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function statusIcon(status) {
  const icons = {
    pending: "&#9711;",
    processing: "&#8987;",
    completed: "&#10003;",
    failed: "&#10007;",
  };
  return icons[status] || "";
}

// ── Keyboard shortcuts ─────────────────────────────
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    document.querySelector(".modal-overlay")?.remove();
  }
  if (e.key === "n" && (e.metaKey || e.ctrlKey)) {
    e.preventDefault();
    showNewCaseModal();
  }
});

// ── Init ───────────────────────────────────────────
loadCases();
renderMain();
