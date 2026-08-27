const EXAMPLES = [
  "How much did I spend on food last month?",
  "What are my spending categories?",
  "Show my largest shopping purchases this year",
  "How much did I spend at Starbucks?",
  "List my latest transactions",
];

const thread = document.getElementById("thread");
const form = document.getElementById("form");
const input = document.getElementById("question");
const ask = document.getElementById("ask");
const chips = document.getElementById("chips");
const metaEl = document.getElementById("meta");
const modeBadge = document.getElementById("mode-badge");

function renderEmpty() {
  thread.innerHTML = `
    <div class="empty">
      <h3>The books are open</h3>
      <p>Try a sample question, or type your own. Every tool the agent uses will show up here before the final answer.</p>
    </div>`;
}

function addBubble(role, text) {
  const empty = thread.querySelector(".empty");
  if (empty) empty.remove();
  const wrap = document.createElement("article");
  wrap.className = `bubble ${role}`;
  wrap.innerHTML = `<div class="label">${role === "user" ? "You" : "Ledger"}</div><div class="body"></div>`;
  wrap.querySelector(".body").textContent = text;
  thread.appendChild(wrap);
  thread.scrollTop = thread.scrollHeight;
  return wrap;
}

function addTrace(trace) {
  if (!trace.length) return;
  const box = document.createElement("section");
  box.className = "trace";
  box.innerHTML = "<h4>Tool trace</h4>";
  for (const step of trace) {
    const row = document.createElement("div");
    row.className = "call";
    if (step.type === "tool_call") {
      row.innerHTML = `<span class="kind">call</span> <span class="name">${step.name}</span>(${JSON.stringify(step.arguments)})`;
    } else {
      const preview = JSON.stringify(summarize(step.result));
      row.innerHTML = `<span class="kind">result</span> <span class="name">${step.name}</span> → ${preview}`;
    }
    box.appendChild(row);
  }
  thread.appendChild(box);
  thread.scrollTop = thread.scrollHeight;
}

function summarize(result) {
  if (!result || typeof result !== "object") return result;
  if (Array.isArray(result.transactions)) {
    return {
      matched: result.matched ?? result.count,
      returned: result.returned,
      sample: result.transactions.slice(0, 3).map((row) => ({
        date: row.date,
        merchant: row.merchant,
        amount: row.amount,
      })),
    };
  }
  if (Array.isArray(result.categories)) {
    return result.categories.map((row) => row.name);
  }
  return result;
}

async function send(question) {
  addBubble("user", question);
  ask.disabled = true;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!response.ok) {
      const detail = await response.text();
      addBubble("assistant", `Request failed (${response.status}): ${detail}`);
      return;
    }
    const data = await response.json();
    addTrace(data.trace || []);
    addBubble("assistant", data.answer);
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

EXAMPLES.forEach((text) => {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = text;
  button.addEventListener("click", () => send(text));
  chips.appendChild(button);
});

async function loadMeta() {
  try {
    const data = await fetch("/api/meta").then((r) => r.json());
    modeBadge.textContent = data.agent_mode === "llm" ? `LLM · ${data.model}` : "Rules mode";
    metaEl.innerHTML = `
      <dl>
        <div><dt>Transactions</dt><dd>${data.transaction_count.toLocaleString()}</dd></div>
        <div><dt>Date range</dt><dd>${data.start_date} → ${data.end_date}</dd></div>
        <div><dt>Today</dt><dd>${data.today}</dd></div>
        <div><dt>Categories</dt><dd>${data.categories.join(" · ")}</dd></div>
      </dl>`;
  } catch {
    metaEl.innerHTML = "<p>Could not load ledger metadata.</p>";
    modeBadge.textContent = "offline";
  }
}

renderEmpty();
loadMeta();
