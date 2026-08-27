const thread = document.getElementById("thread");
const form = document.getElementById("form");
const input = document.getElementById("question");
const ask = document.getElementById("ask");
const metaEl = document.getElementById("meta");
const docList = document.getElementById("doc-list");
const uploadForm = document.getElementById("upload-form");
const pdfInput = document.getElementById("pdf");
const fileLabel = document.getElementById("file-label");
const ingestBtn = document.getElementById("ingest");
const ingestStatus = document.getElementById("ingest-status");
const rerankToggle = document.getElementById("rerank");

function renderEmpty() {
  thread.innerHTML = `
    <div class="empty">
      <h3>The cabinet is empty until you index a PDF</h3>
      <p>Upload a policy handbook, then ask about leave, FAQs, or IT rules in that file.</p>
    </div>`;
}

function addBubble(role, text) {
  const empty = thread.querySelector(".empty");
  if (empty) empty.remove();
  const wrap = document.createElement("article");
  wrap.className = `bubble ${role}`;
  wrap.innerHTML = `<div class="label">${role === "user" ? "You" : "Docket"}</div><div class="body"></div>`;
  wrap.querySelector(".body").textContent = text;
  thread.appendChild(wrap);
  thread.scrollTop = thread.scrollHeight;
  return wrap;
}

function addCitations(citations) {
  if (!citations || !citations.length) return;
  const row = document.createElement("div");
  row.className = "cites";
  for (const cite of citations) {
    const pill = document.createElement("span");
    pill.className = "cite";
    const page = cite.page != null ? ` p.${cite.page}` : "";
    const score = cite.score != null ? ` · ${Number(cite.score).toFixed(2)}` : "";
    pill.textContent = `${cite.source || "pdf"}${page}${score}`;
    row.appendChild(pill);
  }
  thread.appendChild(row);
}

function addTrace(data) {
  const box = document.createElement("section");
  box.className = "trace";
  const retrieved = (data.retrieved || []).length;
  const used = (data.used || []).length;
  const first = (data.used || [])
    .slice(0, 3)
    .map((item) => item.section || item.source)
    .join(" · ");
  box.innerHTML = `
    <h4>Retrieval</h4>
    <p>vector hits: ${retrieved} · after ${data.rerank ? "rerank" : "top-3"}: ${used} · mode: ${data.mode}</p>
    <p>${first || "no chunks"}</p>`;
  thread.appendChild(box);
  thread.scrollTop = thread.scrollHeight;
}

async function loadMeta() {
  try {
    const response = await fetch("/api/meta");
    const data = await response.json();
    metaEl.innerHTML = `
      <div>${data.embedding_model}</div>
      <div>${data.chunks} chunks · ${data.documents} file(s)</div>
      <div>answer: ${data.answer_mode}</div>`;
    if (data.sources && data.sources.length) {
      docList.innerHTML = data.sources.map((name) => `<li>${name}</li>`).join("");
    } else {
      docList.innerHTML = `<li class="muted">None yet</li>`;
    }
  } catch (err) {
    metaEl.textContent = `API offline: ${err.message}`;
  }
}

pdfInput.addEventListener("change", () => {
  const file = pdfInput.files[0];
  fileLabel.textContent = file ? file.name : "Choose a PDF";
  ingestBtn.disabled = !file;
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = pdfInput.files[0];
  if (!file) return;
  ingestBtn.disabled = true;
  ingestStatus.className = "status";
  ingestStatus.textContent = "Indexing (embed + store)…";
  const body = new FormData();
  body.append("file", file);
  try {
    const response = await fetch("/api/ingest", { method: "POST", body });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || response.statusText);
    }
    ingestStatus.className = "status ok";
    ingestStatus.textContent = data.skipped
      ? `${data.source} already indexed (${data.chunks} chunks)`
      : `${data.source}: ${data.pages} pages → ${data.chunks} chunks`;
    await loadMeta();
  } catch (err) {
    ingestStatus.className = "status err";
    ingestStatus.textContent = err.message;
  } finally {
    ingestBtn.disabled = !pdfInput.files[0];
  }
});

async function send(question) {
  addBubble("user", question);
  ask.disabled = true;
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, rerank: rerankToggle.checked }),
    });
    const data = await response.json();
    if (!response.ok) {
      addBubble("assistant", data.detail || `Request failed (${response.status})`);
      return;
    }
    addTrace(data);
    addBubble("assistant", data.answer);
    addCitations(data.citations);
  } catch (err) {
    addBubble("assistant", `Could not reach the API: ${err.message}`);
  } finally {
    ask.disabled = false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  send(question);
});

renderEmpty();
loadMeta();
