# Personal Shopping Assistant

A FastAPI + LangChain shopping agent that remembers a shopper across turns.

The interesting part is not the catalog. It is **memory**: what the user likes, what they are shopping for right now, and what they already said.

## Quick start

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

An `OPENAI_API_KEY` in `.env` is optional. Without it the same tools run in **rules mode** (regex, no LLM cost).

```env
OPENAI_API_KEY=           # empty = rules mode
LLM_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///./shopping.db
MAX_AGENT_STEPS=8
HISTORY_LIMIT=20
```

On first boot the app creates `shopping.db`, seeds products, and seeds three demo shoppers.

## What this app does

1. User says: *I normally buy running shoes below ₹10,000.*
2. Agent writes that into **long-term memory**.
3. Later: *Show me some new options.*
4. Agent reuses the saved budget/category and skips products already shown.

That second message is the whole point. The user should not have to repeat preferences.

## Three memories (one SQLite file)

| Kind | Table | Stores | Survives “New session”? |
|---|---|---|---|
| **Long-term** | `user_profiles` | Brands, categories, colours, budget, sizes, audience | Yes |
| **Task** | `shopping_tasks` | Current hunt + product IDs already shown | No |
| **Conversation** | `messages` | Chat turns (last 20 fed to the LLM) | No |

All three live in `shopping.db`. Reads and writes go through `app/memory.py`.

### Long-term (who the shopper is)

Written when the user states a preference (`update_profile`).

- Brands / colours / categories **merge** by default (a shopper can like Nike *and* Asics).
- Budget, size, and audience **overwrite**. A new max budget replaces a stale one.
- Brands can be dropped: *Forget Nike, I don't buy that brand anymore.*

### Task (what they are doing now)

Written on every search.

- `shown_product_ids` stops the same products repeating.
- Switching category clears that list (a dress hunt should not inherit shoe exclusions).
- Task budget/category mirror the profile for the **active hunt**, but can be reset without wiping the profile.

### Conversation (what was said)

Every chat turn is stored after the agent replies. In LLM mode the last `HISTORY_LIMIT` messages are injected into the model so it can follow “that one” / “show more”.

## How a request flows

```
Browser  POST /api/chat
   →  run_agent()                app/agent/loop.py
        ├─ LLM mode: GPT decides which tools to call
        └─ rules mode: extract.py parses the sentence, then calls the same tools
   →  tools (get_memory / update_profile / search_products)
   →  memory.py reads/writes SQLite
   →  user + assistant messages saved
   →  JSON: answer + tool trace + memory snapshot
```

`search_products` applies filters in this order:

1. Filters from the current message
2. Task memory (active hunt)
3. Long-term profile (fallback)
4. Exclude already-shown IDs
5. Soft-boost preferred colour/brand (sort first, do not hide the rest)

## Project layout

```
app/
  main.py              FastAPI app, seeds DB on startup
  api.py               /api/chat, /memory, /history, /reset, /meta
  config.py            Settings from .env
  database.py          SQLAlchemy engine
  models.py            Product, UserProfile, ShoppingTask, Message
  memory.py            Read/write all three memories + catalog search
  seed.py              Synthetic catalog + demo users
  agent/
    loop.py            LLM tool-calling loop, or fallback to rules
    tools.py           LangChain tools bound to one request's db + user
    planner.py         Rules-mode agent (no API key)
    extract.py         Regex slot-filling for rules mode
    prompts.py         System prompt (includes a memory snapshot)
  static/              Chat UI
```

Change catalog or demo users in `app/seed.py`. Delete `shopping.db` if you want a clean reseed.

## Agent modes

| | LLM | Rules |
|---|---|---|
| Trigger | `OPENAI_API_KEY` set | key empty |
| Who picks tools | `gpt-4o-mini` | `extract.py` + `planner.py` |
| Tools | same three | same three |
| Best for | messy / natural language | free, deterministic demos |

The UI badge shows which mode is active.

## Demo shoppers

| `user_id` | Starting memory |
|---|---|
| `fresh` | Empty. Use this to watch memory fill in. |
| `riya` | Nike/Asics, running shoes, black/navy, size 9, max ₹10,000 |
| `meera` | Zara/H&M, dresses, beige/pink, size M, ₹1,000–₹2,000 |

Try this sequence on **fresh**:

1. `I normally buy running shoes below ₹10,000.`
2. `Show me some new options.`
3. `My budget is now ₹15,000.`
4. `Forget Nike, I don't buy that brand anymore`

Watch the left rail: long-term slots update, `already shown` grows, then budget overwrite and brand removal.

**New session** clears chat + shown IDs. **Wipe profile** also clears long-term prefs.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/chat` | `{ "user_id", "message" }` — run the agent |
| `GET` | `/api/memory?user_id=` | Profile + task snapshot |
| `GET` | `/api/history?user_id=` | Chat turns |
| `POST` | `/api/reset` | `{ "user_id", "clear_profile": false }` |
| `GET` | `/api/meta` | Catalog size, users, agent mode |
| `GET` | `/api/health` | Liveness |

## Memory rules worth knowing

These are the design choices interviewers (and future you) will ask about:

- **Merge vs overwrite** — lists of likes merge; a single constraint (budget) overwrites so stale values cannot linger.
- **Invalidation** — category change clears shown IDs; `remove_brands` drops a preference; sliding window drops old chat.
- **Soft vs hard filters** — an explicit colour is a hard filter; a saved colour preference only boosts ranking.
- **Same tools, two brains** — LLM and rules share `memory.py`. Memory is the source of truth, not the model.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Empty catalog / missing users | Delete `shopping.db` and restart (seed only runs if tables are empty) |
| Always in rules mode | Set `OPENAI_API_KEY` in `.env` at the project root |
| Python / venv path errors | Recreate `.venv` with the Python you actually have installed |
| Same products keep showing | Reset the session, or switch category (shown IDs persist until then) |
