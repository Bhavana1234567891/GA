const EXAMPLES = [
  "I normally buy running shoes below ₹10,000.",
  "Show me some new options.",
  "My budget is now ₹15,000.",
  "I want a dress in the price range 1k-2k for women",
  "I prefer black or navy, size 9",
  "Forget Nike, I don't buy that brand anymore",
];

const thread = document.getElementById("thread");
const form = document.getElementById("form");
const input = document.getElementById("question");
const ask = document.getElementById("ask");
const chips = document.getElementById("chips");
const metaEl = document.getElementById("meta");
const modeBadge = document.getElementById("mode-badge");
const userSelect = document.getElementById("user-select");
const memoryPanel = document.getElementById("memory-panel");
const taskPanel = document.getElementById("task-panel");

function currentUser() {
  return userSelect.value || "fresh";
}

function listText(value) {
  if (value == null || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
  if (typeof value === "object") {
    const entries = Object.entries(value);
    return entries.length ? entries.map(([k, v]) => `${k} ${v}`).join(", ") : "—";
  }
  return String(value);
}

function rupees(value) {
  if (value == null) return "—";
  return `₹${Number(value).toLocaleString("en-IN")}`;
}

function renderMemory(snapshot) {
  const profile = snapshot?.profile || {};
  const task = snapshot?.task || {};
  const budget =
    profile.budget_min != null && profile.budget_max != null
      ? `${rupees(profile.budget_min)} – ${rupees(profile.budget_max)}`
      : rupees(profile.budget_max);
  memoryPanel.innerHTML = `
    <h3>Long-term memory</h3>
    <dl>
      <div><dt>Categories</dt><dd>${listText(profile.categories)}</dd></div>
      <div><dt>Brands</dt><dd>${listText(profile.preferred_brands)}</dd></div>
      <div><dt>Colours</dt><dd>${listText(profile.colours)}</dd></div>
      <div><dt>Budget</dt><dd>${budget}</dd></div>
      <div><dt>Sizes</dt><dd>${listText(profile.sizes)}</dd></div>
      <div><dt>Audience</dt><dd>${listText(profile.audience)}</dd></div>
    </dl>`;
  const shown = task.shown_product_ids || [];
  taskPanel.innerHTML = `
    <h3>Task memory</h3>
    <dl>
      <div><dt>Current hunt</dt><dd>${listText(task.category)}</dd></div>
      <div><dt>Already shown</dt><dd class="ids">${shown.length ? shown.join(", ") : "none yet"}</dd></div>
    </dl>`;
}

function renderEmpty() {
  thread.innerHTML = `
    <div class="empty">
      <h3>Memory is empty until you speak</h3>
      <p>Start with the running-shoes line from the brief, then ask for new options without repeating the budget.</p>
    </div>`;
}

function addBubble(role, text) {
  const empty = thread.querySelector(".empty");
  if (empty) empty.remove();
  const wrap = document.createElement("article");
  wrap.className = `bubble ${role}`;
  wrap.innerHTML = `<div class="label">${role === "user" ? "You" : "Atelier"}</div><div class="body"></div>`;
  wrap.querySelector(".body").textContent = text;
  thread.appendChild(wrap);
  thread.scrollTop = thread.scrollHeight;
}

function addTrace(trace) {
  if (!trace?.length) return;
  const box = document.createElement("section");
  box.className = "trace";
  box.innerHTML = "<h4>Tool trace</h4>";
  for (const step of trace) {
    const row = document.createElement("div");
    row.className = "call";
    if (step.type === "tool_call") {
      row.innerHTML = `<span class="kind">call</span> <span class="name">${step.name}</span>(${JSON.stringify(step.arguments)})`;
    } else {
      row.innerHTML = `<span class="kind">result</span> <span class="name">${step.name}</span> → ${JSON.stringify(summarize(step.result))}`;
    }
    box.appendChild(row);
  }
  thread.appendChild(box);
  thread.scrollTop = thread.scrollHeight;
}

function summarize(result) {
  if (!result || typeof result !== "object") return result;
  if (Array.isArray(result.products)) {
    return {
      count: result.count,
      filters: result.filters,
      products: result.products.map((row) => ({
        id: row.id,
        name: row.name,
        price: row.price,
      })),
    };
  }
  if (result.profile) {
    return {
      brands: result.profile.preferred_brands,
      categories: result.profile.categories,
      budget_max: result.profile.budget_max,
      shown: result.task?.shown_product_ids,
    };
  }
  return result;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.json();
}

async function loadMemory() {
  const data = await fetchJson(`/api/memory?user_id=${encodeURIComponent(currentUser())}`);
  renderMemory(data);
}

async function loadHistory() {
  const data = await fetchJson(`/api/history?user_id=${encodeURIComponent(currentUser())}`);
  thread.innerHTML = "";
  if (!data.messages?.length) {
    renderEmpty();
    return;
  }
  for (const row of data.messages) {
    addBubble(row.role === "user" ? "user" : "assistant", row.content);
  }
}

async function send(question) {
  addBubble("user", question);
  ask.disabled = true;
  try {
    const data = await fetchJson("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: currentUser(), message: question }),
    });
    addTrace(data.trace || []);
    addBubble("assistant", data.answer);
    renderMemory(data.memory);
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

userSelect.addEventListener("change", async () => {
  await loadMemory();
  await loadHistory();
});

document.getElementById("reset-session").addEventListener("click", async () => {
  await fetchJson("/api/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: currentUser(), clear_profile: false }),
  });
  await loadMemory();
  renderEmpty();
});

document.getElementById("wipe-profile").addEventListener("click", async () => {
  await fetchJson("/api/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: currentUser(), clear_profile: true }),
  });
  await loadMemory();
  renderEmpty();
});

async function loadMeta() {
  try {
    const data = await fetchJson("/api/meta");
    modeBadge.textContent = data.agent_mode === "llm" ? `LLM · ${data.model}` : "Rules mode";
    userSelect.innerHTML = "";
    for (const user of data.users || []) {
      const option = document.createElement("option");
      option.value = user.user_id;
      option.textContent = user.display_name || user.user_id;
      userSelect.appendChild(option);
    }
    if (![...userSelect.options].some((opt) => opt.value === "fresh")) {
      userSelect.value = userSelect.options[0]?.value || "fresh";
    } else {
      userSelect.value = "fresh";
    }
    metaEl.innerHTML = `
      <dl>
        <div><dt>Catalog</dt><dd>${data.product_count} products</dd></div>
        <div><dt>Categories</dt><dd>${(data.categories || []).join(" · ")}</dd></div>
        <div><dt>Memory</dt><dd>SQLite profile + task + chat</dd></div>
      </dl>`;
    await loadMemory();
    await loadHistory();
  } catch {
    metaEl.innerHTML = "<p>Could not load catalog metadata.</p>";
    modeBadge.textContent = "offline";
    renderEmpty();
  }
}

loadMeta();
