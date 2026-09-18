/**
 * Side panel: chat UI that talks to the FastAPI backend.
 * Renders answers with clickable timestamps.
 */

const API_BASE = "http://localhost:8002";

const chatEl = document.getElementById("chat");
const inputEl = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const statusEl = document.getElementById("status");
const welcomeEl = document.getElementById("welcome");

let currentVideoId = null;
let sessionId = "session_" + Date.now();

// ── Init ──────────────────────────────────────────────────────────────────

async function init() {
  setStatus("loading", "Detecting video...");

  // Get video ID from background
  chrome.runtime.sendMessage({ type: "GET_VIDEO_ID" }, async (response) => {
    if (!response || !response.videoId) {
      setStatus("error", "No video detected");
      return;
    }

    currentVideoId = response.videoId;
    setStatus("loading", "Indexing transcript...");

    try {
      // Index the video (backend skips if already done)
      const res = await fetch(`${API_BASE}/index`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_id: currentVideoId }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Indexing failed");
      }

      const data = await res.json();
      setStatus("ready", `Ready (${data.message})`);
      inputEl.disabled = false;
      sendBtn.disabled = false;
      inputEl.focus();

      if (welcomeEl) {
        welcomeEl.textContent = `Video ${currentVideoId} loaded. Ask me anything!`;
      }
    } catch (err) {
      setStatus("error", err.message);
    }
  });
}

// ── Chat ──────────────────────────────────────────────────────────────────

async function sendMessage() {
  const question = inputEl.value.trim();
  if (!question || !currentVideoId) return;

  inputEl.value = "";
  addMessage(question, "user");
  sendBtn.disabled = true;
  inputEl.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        video_id: currentVideoId,
        question: question,
        session_id: sessionId,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Chat failed");
    }

    const data = await res.json();
    addBotMessage(data);
  } catch (err) {
    addMessage(`Error: ${err.message}`, "bot");
  } finally {
    sendBtn.disabled = false;
    inputEl.disabled = false;
    inputEl.focus();
  }
}

// ── UI helpers ────────────────────────────────────────────────────────────

function setStatus(type, text) {
  statusEl.className = `status ${type}`;
  statusEl.textContent = text;
}

function addMessage(text, role) {
  if (welcomeEl) welcomeEl.remove();
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function addBotMessage(data) {
  if (welcomeEl) welcomeEl.remove();
  const div = document.createElement("div");
  div.className = "message bot";

  // Answer text with clickable timestamps
  const answerHtml = makeTimestampsClickable(data.answer);
  div.innerHTML = answerHtml;

  // Grounding badge
  const badge = document.createElement("span");
  badge.className = `grounding-badge ${data.is_grounded ? "grounded" : "ungrounded"}`;
  badge.textContent = data.is_grounded ? "✓ Grounded" : "⚠ Ungrounded";
  div.appendChild(document.createElement("br"));
  div.appendChild(badge);

  // Sources accordion
  if (data.sources && data.sources.length > 0) {
    const toggle = document.createElement("div");
    toggle.className = "sources-toggle";
    toggle.textContent = `▸ ${data.sources.length} source(s)`;

    const list = document.createElement("div");
    list.className = "sources-list";

    data.sources.forEach((s, i) => {
      const item = document.createElement("div");
      item.style.marginBottom = "6px";
      const link = document.createElement("span");
      link.className = "timestamp-link";
      link.textContent = `[${i + 1}] ${s.t_start_display} - ${s.t_end_display}`;
      link.addEventListener("click", () => seekVideo(s.t_start));
      item.appendChild(link);
      item.appendChild(document.createTextNode(` ${s.text.substring(0, 120)}...`));
      list.appendChild(item);
    });

    toggle.addEventListener("click", () => {
      list.classList.toggle("open");
      toggle.textContent = list.classList.contains("open")
        ? `▾ ${data.sources.length} source(s)`
        : `▸ ${data.sources.length} source(s)`;
    });

    div.appendChild(toggle);
    div.appendChild(list);
  }

  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function makeTimestampsClickable(text) {
  // Match patterns like [0:42 - 1:12] or [12:40] or [1:23 - 2:45]
  return text.replace(
    /\[(\d{1,2}:\d{2})\s*-?\s*(\d{1,2}:\d{2})?\]/g,
    (match, start, end) => {
      const seconds = mmssToSeconds(start);
      return `<span class="timestamp-link" onclick="seekVideo(${seconds})">${match}</span>`;
    }
  );
}

function mmssToSeconds(mmss) {
  const parts = mmss.split(":");
  return parseInt(parts[0]) * 60 + parseInt(parts[1]);
}

function seekVideo(seconds) {
  chrome.runtime.sendMessage({ type: "SEEK_VIDEO", seconds: seconds });
}

// Make seekVideo available to inline onclick handlers
window.seekVideo = seekVideo;

// ── Event listeners ───────────────────────────────────────────────────────

sendBtn.addEventListener("click", sendMessage);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});

init();
