"""Unit Project 3A — Personal Shopping Assistant

LangChain shopping agent with three kinds of memory in one SQLite file:
conversation (messages), task (shown products + current hunt), long-term (profile).

Run from this folder:

    python -m venv .venv
    .venv\\Scripts\\activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Open http://localhost:8000

Optional LLM: copy .env.example to .env and set OPENAI_API_KEY.
Without a key the same tools run in rules mode.
"""

"""# Memory concepts for projects

## User

TRACK 3 — MEMORY

Memory should cover conversation state, task state and longer-term information, including when information should be updated or invalidated. 

---

## Unit Project 3A — Personal Shopping Assistant

### Problem

Remember a user's:

* Preferred brands
* Categories
* Colours
* Budget
* Sizes

### Example

User initially says:

> "I normally buy running shoes below ₹10,000."

Later:

> "Show me some new options."

### Data Preparation

**SELF**

Create synthetic user profiles and interactions.

### Owner

**Member 1**

---

## Unit Project 3B — Research Project Memory Agent

### Problem

Maintain memory of an ongoing research project.

### Memory

* Previous questions
* Findings
* Sources
* Open questions
* Decisions

### Data Preparation

**SELF**

Create synthetic research projects.

### Owner

**Member 2**

---

## Unit Project 3C — Customer Support Memory Agent

### Problem

Remember previous customer interactions.

### Memory

```text
Customer profile
Previous issues
Previous resolutions
Open tickets
Preferences
```

### Data Preparation

**SELF**

Synthetic support tickets.

### Important Exercise

Change customer information and verify that stale memory is updated/invalidated.

### Owner

**Member 3**

---  can you explain the concept of memory wrt to these mentioned projects and emphasized concepts of memory in this content

## Assistant

I'll look at the project materials and how memory is framed for these three unit projects, then explain the concept in that context.

### Tool Read File V2

```
{"path":"C:\\Users\\bhava\\.agents\\skills\\developing-with-streamlit\\SKILL.md"}
```

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant","globPattern":"**/*"}
```

### Tool Ripgrep Raw Search

```
{"pattern":"memory|Memory|invalidate|stale","path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory","glob":"*.{md,py,txt,json}","caseInsensitive":false,"multiline":false,"toolCallId":"call-81e81c58-474c-4f65-8d83-c728430069eb-2\nfc_34e031ab-0155-9686-a6cd-9a1c0059d38f_2","offset":0}
```

### Tool Get Mcp Tools

```
{"server":"cursor-app-control","toolName":"rename_chat","toolCallId":"call-81e81c58-474c-4f65-8d83-c728430069eb-3\nfc_34e031ab-0155-9686-a6cd-9a1c0059d38f_3"}
```

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia","globPattern":"**/*.{md,py,txt,pdf}"}
```

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory","globPattern":"**/*"}
```

### Tool Ripgrep Raw Search

```
{}
```

## Assistant

**Memory** here is the agent’s ability to keep useful facts across turns and sessions, then use them later without the user repeating themselves. The brief also says that memory is incomplete unless the agent knows **when to update or throw away** what it stored.

The track is not “save the chat log.” It is three kinds of state plus a lifecycle rule.

---

## The three layers the brief is teaching

| Layer | What it is | Typical lifetime | Example |
|---|---|---|---|
| **Conversation state** | What is happening *right now* in this chat | This session | “You asked for running shoes, I showed 3 options” |
| **Task state** | Progress on a job that may span several messages | Until the task is done | “Still looking for shoes under ₹10,000; 2 options rejected” |
| **Longer-term information** | Who the user is / what this project or ticket is | Across sessions | “Budget is ₹10,000; size 9; prefers Nike” |

**Update / invalidation** sits on top of all three. Facts go stale. If the user later says “my budget is now ₹15,000,” the old ₹10,000 must be **replaced**, not kept as a second competing fact.

Without that last piece, the agent looks like it “has memory” but recommends the wrong things.

---

## Why “Show me some new options” is the whole point

First message:

> “I normally buy running shoes below ₹10,000.”

That one line should be extracted into **longer-term memory**:

- **Category:** running shoes  
- **Budget:** below ₹10,000  

Later:

> “Show me some new options.”

There is no category and no budget in that sentence. A stateless chatbot would ask “options for what?” A memory agent should:

1. Pull conversation/task state: last search was running shoes.  
2. Pull long-term profile: budget &lt; ₹10,000.  
3. Return **new** items (not the same three again — that is task state: what was already shown).

That is the difference between a chat UI and a **memory agent**.

---

## Project 3A — Personal Shopping Assistant

**Job:** remember a shopper as a **profile**, not as a transcript.

| Memory slot | Kind of memory | Why it matters |
|---|---|---|
| Preferred brands | Long-term preference | Filter / rank products |
| Categories | Long-term + conversation (current browse) | “shoes” vs “shirts” |
| Colours | Preference | Style matching |
| Budget | Constraint (must stay current) | Hard filter |
| Sizes | Relatively stable fact | Inventory matching |

How the three layers show up:

- **Conversation:** “those look too loud” → this turn’s reaction.  
- **Task:** current shopping mission — running shoes, already shown SKUs A/B/C, waiting for a pick.  
- **Long-term:** brands, colours, budget, sizes that should still apply next week.

**Invalidation in 3A:**  
“I normally buy below ₹10,000” then later “I can go up to ₹15,000” → **overwrite budget**.  
“I don’t wear Nike anymore” → **remove brand**, don’t keep recommending Nike because an older memory still lists it.

Synthetic profiles exist so you can test: *does turn 5 still respect turn 1, and does a later correction actually replace turn 1?*

---

## Project 3B — Research Project Memory Agent

**Job:** remember a **project**, not a person. Memory is the research notebook.

| Slot | Role |
|---|---|
| Previous questions | What was already asked (avoid repeating work) |
| Findings | What we believe we know |
| Sources | Where a finding came from (so it can be checked or dropped) |
| Open questions | Unfinished work — **task state** |
| Decisions | Locked choices (“we will use method X”) |

Layers:

- **Conversation:** this chat’s latest question and answer.  
- **Task:** the living research thread — open questions, next experiment, “we still need a source for claim Y.”  
- **Long-term:** decisions and confirmed findings that should survive a new session.

**Invalidation in 3B is different from shopping.** A finding can become wrong when a better source appears. A decision can be reversed. An open question should **close** when answered, not sit forever as “open.” Sources matter because they let you **invalidate a finding** without deleting the whole project.

This project trains **structured, evolving knowledge**, not a user profile.

---

## Project 3C — Customer Support Memory Agent

**Job:** remember a **customer relationship** over many tickets.

| Slot | Role |
|---|---|
| Customer profile | Identity, plan, account facts |
| Previous issues | History (what went wrong before) |
| Previous resolutions | What already worked (or failed) |
| Open tickets | **Task state** — still in progress |
| Preferences | Contact channel, language, etc. |

The **important exercise** is the core of Track 3:

> Change customer information and verify that stale memory is updated/invalidated.

Example: profile says “email: old@mail.com” and “plan: Basic.” Customer says they upgraded to Pro and changed email. If the agent later says “as a Basic customer we’ll email old@mail.com,” memory failed even if the chat log still contains the new facts.

Support-specific invalidation:

- Open ticket → resolved → must **leave open tickets** and move into **previous resolutions**.  
- Old issue “can’t log in” resolved by password reset → don’t keep treating login as an open problem.  
- Address / plan / phone change → **overwrite**, don’t append conflicting copies.

3C is where “memory” is proven: not storage, but **correct current state**.

---

## One mental model for all three

Think of memory as a small database the agent **reads before answering** and **writes after each turn**:

```text
User message
    → retrieve relevant memory (profile / project / tickets)
    → answer using that + current message
    → write back:
         - new facts
         - updates to old facts
         - deletions / closures (invalidation)
```

If you only **append** (“user once said budget is 10k” and later “user said 15k”), you have a log, not memory. Retrieval will surface **both**, and the model may pick the wrong one.

So the emphasized operations are:

1. **Extract** — turn natural language into slots (budget, finding, ticket status).  
2. **Store** — conversation vs task vs long-term (different TTLs and scopes).  
3. **Retrieve** — on “show me new options” / “where did we leave off?” / “this customer again.”  
4. **Update** — same slot, new value.  
5. **Invalidate** — fact is no longer true; ticket closed; finding superseded.

---

## How the three projects split the same idea

| | 3A Shopping | 3B Research | 3C Support |
|---|---|---|---|
| **Who/what is remembered** | Shopper profile | Research project | Customer + tickets |
| **Conversation state** | This browse session | This Q&A | This support call |
| **Task state** | Current hunt (category, already shown items) | Open questions, in-progress inquiry | Open tickets |
| **Long-term** | Brands, sizes, colours, budget | Findings, sources, decisions | Profile, past issues, preferences |
| **Main invalidation test** | Budget/brand/size change | Finding or decision reversed | Profile change + ticket close (explicit exercise) |

They are the same memory system applied to **preference memory**, **knowledge/work memory**, and **relationship/ops memory**.

---

## What “good memory” looks like in grading terms

An agent that only concatenates chat history can *sometimes* look smart in one session. Track 3 is asking for more:

- After “show me some new options,” it still knows **running shoes** and **&lt; ₹10,000** (3A).  
- It can summarize a project: what we asked, what we found, what’s still open, what we decided (3B).  
- After you **change** a customer’s plan or contact info, later answers use the **new** facts, and closed tickets are no longer treated as open (3C).

That last check — **stale memory must not win** — is the concept the brief is emphasizing hardest, even though only 3C names it as an exercise. It applies to all three projects.

## User

do we need to maintain 3 separate memory for each of these storage

## Assistant

I’ll check whether this project already splits those stores, then answer whether you need three physical memories or just three kinds of state.

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant","globPattern":"**/*.{py,md,json,yml,yaml}"}
```

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory","globPattern":"**/*"}
```

## Assistant

**No — you do not need three separate memory systems.** You need **three kinds of state**, which you can keep in one store (or two). What must stay separate is **lifetime, scope, and update rules**, not the number of databases.

---

## What the brief is asking for

“Conversation state, task state and longer-term information” means:

| Kind | Question it answers | Lifetime | If you mix it blindly |
|---|---|---|---|
| **Conversation** | What are we talking about *this turn / this chat*? | This session | Old chit-chat pollutes later answers |
| **Task** | What job is in progress? | Until the task ends | Closed searches/tickets stay “open” |
| **Long-term** | Who is this user / project / customer? | Across sessions | Preferences get lost when the chat ends |

That is a **design split**, not a “spin up 3 vector DBs” requirement.

---

## Practical setup (what teams actually do)

For these unit projects, **two layers** is usually enough:

**1. Short-term (session)**  
Chat history + current task  
- Conversation state lives here naturally (recent messages).  
- Task state can live here *or* in a small structured object next to the session (`current_goal`, `already_shown_ids`, `open_questions`).

**2. Long-term (durable)**  
A **profile / project / customer record**  
- Brands, budget, sizes (3A)  
- Findings, sources, decisions (3B)  
- Profile, past tickets, preferences (3C)

So: **one session memory + one durable store**, not three products.

You *can* put all three in one JSON/SQLite/dict keyed by `user_id` (or `project_id` / `customer_id`):

```text
memory[user_id] = {
  "conversation": { ... },   # optional if you already keep chat history
  "task": { ... },
  "long_term": { ... }
}
```

That is **one memory system with three fields**, which is the right mental model for this course.

---

## When a third store is worth it

Add a dedicated conversation store only if:

- You drop raw chat from the LLM context and still need a summary, or  
- Sessions are long and you summarize/archive turns separately.

For 3A/3B/3C, **chat history already is conversation state**. Duplicating it into another memory often adds noise.

---

## What you must not collapse

Do **not** dump everything into one undifferentiated blob (one vector of “stuff the user said”). Then:

- “I like blue” (long-term) and “not this pair” (this task) look the same.  
- “Budget ₹10,000” never gets overwritten by “now ₹15,000.”  
- “Show me some new options” cannot tell **profile** from **already shown items**.

So: **separate slots / schemas**, even if they sit in the same file.

---

## Mapping to the three projects

| Project | Conversation | Task | Long-term | Typical storage |
|---|---|---|---|---|
| **3A Shopping** | This chat’s browse | Current hunt + products already shown | Brands, colours, budget, sizes | Session + user profile |
| **3B Research** | This Q&A | Open questions, in-progress thread | Findings, sources, decisions | Session + project record |
| **3C Support** | This call | Open tickets | Profile, past issues, preferences | Session + customer record |

3C’s “change info and invalidate” is easiest if long-term is a **structured profile** (fields you can overwrite), not a third chat log.

---

## Rule of thumb

- **One agent / one app** → one memory module.  
- **Three concepts** → three sections (or session vs durable).  
- **Three physical memories** → only if lifetimes or access patterns really diverge (usually they don’t at this scale).

For Unit Project 3A, a single `UserMemory` with `preferences` (long-term) and `current_shop` (task), plus the message list (conversation), is enough.

## User

what exactly do you mean by 3 different sessions

## Assistant

I did **not** mean three chat sessions, and I did not mean three separate logins.

If that phrase stuck, it was probably from mixing up two different words: **session** vs **three kinds of memory**.

---

## What “a session” means here

A **session** is one sitting with the agent: from “hello” until the chat is closed or times out.

Example:

- You open the shopping assistant at 7pm, talk for 10 minutes, close the tab → **one session**.
- Tomorrow you open it again → **a new session**.

Chat history from session 1 is **conversation state**. It often disappears (or is no longer in the prompt) when session 2 starts, unless you saved something on purpose.

That is all “session” means. It is **not** “session 1 = brands, session 2 = budget, session 3 = sizes.”

---

## The “3” is three *kinds of memory*, not three sessions

| Kind | Lives where | Survives closing the tab? |
|---|---|---|
| **Conversation state** | This chat | Usually **no** |
| **Task state** | Current job (this hunt / this ticket / this research thread) | **Maybe** — if the task is still open |
| **Long-term** | User / project / customer profile | **Yes** — that is the point |

Same user, **one** ongoing relationship. Different facts just **expire at different times**.

---

## Same user, one session vs next session (shopping)

**Session 1**

> “I normally buy running shoes below ₹10,000.”  
> Agent shows 3 pairs.  
> “The second one is too bright.”

At this moment:

- **Conversation:** we are talking about those 3 pairs; pair 2 was rejected.  
- **Task:** “find running shoes under ₹10k”; already shown IDs A, B, C.  
- **Long-term:** category = running shoes, budget &lt; ₹10,000.

You close the app.

**Session 2 (next day)**

> “Show me some new options.”

- Conversation from yesterday is **gone** (new session).  
- Long-term should **still** say: running shoes, budget ₹10,000.  
- Task: either a **new** hunt (show new products) or continue if you saved “already shown A, B, C” so you don’t repeat them.

You did **not** start “three sessions.” You had **two visits**, and memory is what makes visit 2 still know visit 1’s preferences.

---

## The three *projects* are also not three sessions

3A, 3B, 3C are **three different apps** (shopper / research / support). Each app has its own users and its own memory store.

Inside **one** app (e.g. only 3A), you still use **one** session at a time per user, with those three kinds of state inside it.

---

## Short version

- **Session** = one chat sitting.  
- **Three things** = conversation / task / long-term **fields**, usually in **one** memory object.  
- You do **not** run three parallel sessions to store brands, budget, and sizes.

If you meant something else by “3 different sessions” (for example three users, or three test chats), say which and we can map it onto this.

## User

then we will be implementing all 3 kinds of memory storage in single project itself

## Assistant

**Yes — for the shopping assistant (3A), all three kinds of memory live in that one project.** You are not building three apps, and you are not building 3A + 3B + 3C together.

---

## What goes in *this* project (3A)

One Personal Shopping Assistant that, internally, tracks:

| Kind | In the shopping app, that means |
|---|---|
| **Conversation** | This chat: last messages, what you just showed, “too bright,” “show cheaper ones” |
| **Task** | Current hunt: running shoes, budget filter, products already shown so “new options” are actually new |
| **Long-term** | Profile: brands, categories, colours, budget, sizes — still there next session |

Same codebase, same user, **one** memory module (e.g. one JSON/SQLite record per user) with those three parts.

---

## What does *not* go in this project

**3B** (research notebook) and **3C** (support tickets) are **other members’ unit projects**. They also each implement the same three *kinds* of memory, but for a different domain.

| Project | One app | Three kinds of memory inside it |
|---|---|---|
| **3A (you)** | Shopping assistant | Conversation + task + long-term **shopper** memory |
| **3B** | Research agent | Same three kinds, as questions / findings / decisions |
| **3C** | Support agent | Same three kinds, as profile / tickets / preferences |

So: **three kinds of memory ≠ three projects.**  
Each project implements the three kinds **for its own problem**.

---

## How to think about storage in 3A

```text
Personal Shopping Assistant  (single project)
└── memory for user_id
    ├── conversation   ← this session’s chat
    ├── task           ← current shopping job
    └── long_term      ← brands, colours, budget, sizes
```

That is the intended design for Unit Project 3A.

## User

can you explain me the project impementation for this one ## Unit Project 3A — Personal Shopping Assistant

### Problem

Remember a user's:

* Preferred brands
* Categories
* Colours
* Budget
* Sizes

### Example

User initially says:

> "I normally buy running shoes below ₹10,000."

Later:

> "Show me some new options."

### Data Preparation

**SELF**

Create synthetic user profiles and interactions.

### Owner

**Member 1**  i want to understand it in a practical way i mean more related to the technical context of it can you make it simple along with explaining the tools that you will be going to use for this setup give me the complete flow for this project

## Assistant

I’ll look at how your other Stylumia day projects are built so the 3A flow matches the stack you’re already using.

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia","globPattern":"**/README.md"}
```

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia","globPattern":"**/{requirements.txt,app.py,main.py,config.py}"}
```

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory","globPattern":"**/*.{md,txt}"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\README.md"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\requirements.txt"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Company_knowledge_assistant_rag\\requirements.txt"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\main.py","limit":80}
```

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app","globPattern":"**/*.{py,md}"}
```

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia\\Company_knowledge_assistant_rag\\app","globPattern":"**/*.{py,md}"}
```

## Assistant

**Yes.** For 3A you build **one** shopping assistant. Inside it you keep **three kinds of memory** (conversation, task, long-term). You do not build the research or support apps.

Below is a practical build that matches how your other Stylumia days already work: **FastAPI + SQLite + OpenAI tool calling + synthetic seed data + a simple chat UI**.

---

## What the app must do

The model is not “a chatbot that talks about shoes.” It is an agent that:

1. **Reads** what it already knows about this user.  
2. **Searches** a product catalog with those constraints.  
3. **Writes back** new or changed preferences.  
4. On “Show me some new options,” **does not ask** category or budget again, and **does not repeat** products it already showed.

That last line is the acceptance test.

---

## Tools / stack (keep it the same family as Tool Calling)

| Piece | Use | Why |
|---|---|---|
| **Python 3** | Whole app | Same as your other days |
| **FastAPI + Uvicorn** | `POST /api/chat` | Same pattern as Ledger |
| **SQLAlchemy + SQLite** | Catalog + memory tables | No Docker; easy to inspect |
| **Pydantic** | Profile schema, request/response | Validate budget, sizes, etc. |
| **OpenAI SDK** (or Groq via `LLM_BASE_URL`) | Extract prefs + pick tools + write the reply | Same as tool-calling day |
| **Function calling (tools)** | Agent may only change memory / search catalog through tools | Memory stays structured, not a blob of chat |
| **A few JSON/CSV seed files** | Synthetic users + products + sample chats | Brief says **SELF** data prep |
| **Simple HTML chat** (or Streamlit) | Talk to the agent | Show profile + “already shown” in a sidebar so memory is visible |

You do **not** need a vector database for 3A. Preferences are slots (`budget=10000`), not paragraphs. RAG was Day 2; this day is **structured memory**.

Optional later: LangChain `RunnableWithMessageHistory` for conversation only. The important part is still **your** profile + task tables.

---

## Data you create (synthetic)

**1. Product catalog** (fake shop)

| id | name | brand | category | colour | price | size |
|---|---|---|---|---|---|---|
| P1 | Nike Pegasus 41 | Nike | running shoes | black | 8999 | 8,9,10 |
| P2 | Adidas Adizero | Adidas | running shoes | blue | 12999 | 9,10 |
| … | … | … | … | … | … | … |

Include items **over and under** ₹10,000 so budget filtering is testable.

**2. User profiles** (starting long-term memory)

```json
{
  "user_id": "u_riya",
  "brands": ["Nike", "Asics"],
  "categories": ["running shoes"],
  "colours": ["black", "navy"],
  "budget_max": 10000,
  "sizes": { "shoes": 9 }
}
```

Also seed a **blank** user so the first message *creates* memory (the brief’s example).

**3. Scripted interactions** (for demo / tests)

- Turn 1: `"I normally buy running shoes below ₹10,000."`  
- Turn 2: `"Show me some new options."`  
- Turn 3: `"My budget is now ₹15,000."` → old 10k must be **replaced**.

---

## How the three memories look in code (one DB, three tables/fields)

Think of **one `user_id`**, three buckets:

```text
users.user_id
├── conversation   messages table          (this chat)
├── task           current_search JSON     (this hunt)
└── long_term      profile columns         (survives new chat)
```

**Conversation** — `messages`: `role`, `content`, `created_at`.  
You send the last N turns to the LLM each request.

**Task** — `shopping_tasks` (one open task per user):

```text
category: running shoes
budget_max: 10000
shown_product_ids: ["P1", "P3"]
status: open
```

“New options” = search catalog **excluding** `shown_product_ids`, then append the new ids.

**Long-term** — `user_profiles`:

```text
preferred_brands, categories, colours, budget_max, sizes
```

Updated only via a tool like `update_profile`, so `"now ₹15,000"` **overwrites** `budget_max`, it does not append a second budget.

---

## Agent tools (the LLM is only allowed to do these)

Same idea as your Ledger’s four tools. For shopping, four is enough:

| Tool | Does | Memory it touches |
|---|---|---|
| `get_memory(user_id)` | Return profile + open task + last shown ids | Read all three |
| `update_profile(...)` | Set/overwrite brands, category, colour, budget, size | **Long-term** (invalidate old value) |
| `search_products(...)` | Filter catalog by category, max price, colour, size, brand; skip `exclude_ids` | Uses long-term + task |
| `record_shown(product_ids)` | Append ids to the open task | **Task** |

Conversation is not a tool: the API just stores each user/assistant message.

The model should **not** invent products. It calls `search_products`, then talks about the JSON that came back.

---

## Complete flow of the brief’s example

### Turn 1 — “I normally buy running shoes below ₹10,000.”

```text
Browser
  → POST /api/chat { user_id, message }
  → FastAPI loads messages (empty) + profile (empty) + task (none)
  → LLM sees: user text + tool schemas
  → LLM calls update_profile(category="running shoes", budget_max=10000)
  → DB writes long-term profile
  → LLM calls search_products(category="running shoes", max_price=10000, exclude_ids=[])
  → DB returns e.g. P1, P3, P5 (all ≤ 10k)
  → LLM calls record_shown(["P1","P3","P5"])
  → Task: shown = P1,P3,P5
  → LLM replies with those three options
  → API saves user + assistant messages (conversation)
```

After this, SQLite already has:

- long-term: running shoes, ₹10,000  
- task: shown P1, P3, P5  
- conversation: two messages  

### Turn 2 — “Show me some new options.”

The sentence has **no** category and **no** budget. Memory has to fill that in.

```text
POST /api/chat
  → load profile: category=running shoes, budget=10000
  → load task: shown=[P1,P3,P5]
  → LLM calls get_memory() (or you inject memory into the prompt — both work)
  → LLM calls search_products(..., exclude_ids=[P1,P3,P5])
  → returns P7, P8, P9 (still running shoes, still ≤ 10k, not repeats)
  → record_shown those ids
  → reply: “Here are some new running shoes under ₹10,000 …”
```

If memory is broken, the bot asks “options for what?” or shows P1 again.

### Turn 3 (invalidation) — “I can spend up to ₹15,000 now.”

```text
update_profile(budget_max=15000)   # overwrites 10000
search_products(max_price=15000, exclude_ids=[...])
```

Next search may include the ₹12,999 Adidas. The old cap is gone.

### Next day (new session)

Conversation table can be empty (or a new `session_id`).  
Profile row is **unchanged**.  
Task: either reset `shown_ids` for a fresh hunt, or keep them if you still want “don’t repeat.”

“Show me some new options” still works because **long-term** survived.

---

## End-to-end picture

```text
You type a message
        │
        ▼
┌───────────────────┐
│  FastAPI /chat    │  attach user_id
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Load memory      │  conversation (last N msgs)
│                   │  task (shown ids, current hunt)
│                   │  long-term (brands, budget, …)
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  LLM + tools      │  update_profile / search_products / record_shown
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  SQLite           │  catalog  |  profiles  |  tasks  |  messages
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Reply + sidebar  │  “Memory: running shoes, ₹10k, size 9”
└───────────────────┘
```

---

## Suggested folder layout (same shape as Ledger)

```text
Personal_shopping_assistant/
  app/
    main.py          FastAPI, create tables, seed
    api.py           POST /api/chat
    database.py      SQLite engine
    models.py        Product, UserProfile, ShoppingTask, Message
    seed.py          Fake catalog + 2–3 users
    agent/
      tools.py       get_memory, update_profile, search_products, record_shown
      schemas.py     JSON tool contracts
      loop.py        function-calling loop
      prompts.py     “You are a shopping assistant. Always use memory. Overwrite on change.”
    static/          chat UI + memory panel
  data/              optional JSON for products/profiles
  requirements.txt
```

---

## What to demo so it is clearly “memory,” not just chat

1. Blank user → first sentence fills profile.  
2. Second sentence has no constraints → still filters correctly.  
3. Sidebar shows profile + shown product ids updating live.  
4. Change budget → recommendations change; old budget is gone.  
5. Refresh / new session → preferences still there; “new options” still works.

That is the whole project: **synthetic shop + synthetic users + one agent that reads/writes three kinds of state through tools**, with the two-line dialogue as the main proof.

## User

i want to understad this flowchart in a detailed manner along with covering the technical aspects of it in detail

## Assistant

I’ll map that flowchart onto the same FastAPI + tools + SQLite pattern you already used, then walk through each box in technical detail.

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\api.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\agent\\loop.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\agent\\tools.py","limit":80}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\models.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\database.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\agent\\schemas.py","limit":60}
```

## Assistant

That flowchart is **one HTTP request** moving through the same kind of stack as your Ledger app — with one extra job: **load and save memory** before/after the LLM.

Ledger was **stateless**: `{ "question": "..." }` in, answer out, nothing remembered. This project is **stateful**: every request is tied to a `user_id`, and SQLite is both the **shop catalog** and the **memory**.

---

## The flowchart (expanded)

```text
1. Browser
      POST /api/chat  { user_id, message }
              │
              ▼
2. FastAPI
      validate JSON, open SQLite session, attach user_id
              │
              ▼
3. Load memory (READ)
      conversation  ← last N rows from messages
      task          ← open shopping_tasks row (shown ids, current hunt)
      long-term     ← user_profiles row (brands, budget, sizes, …)
              │
              ▼
4. Agent loop (LLM + tools)   ← same pattern as app/agent/loop.py
      round 1: model may call update_profile / search_products / record_shown
      Python runs the tool against SQLite
      JSON tool result goes back into `messages`
      round 2, 3, … until the model returns plain text (no tool_calls)
              │
              ▼
5. Persist conversation (WRITE)
      INSERT user message + assistant answer into messages
              │
              ▼
6. Response JSON
      answer + updated profile + shown ids + tool trace
              │
              ▼
7. UI
      chat bubble + sidebar “Memory: running shoes, ₹10k”
```

Boxes 4 and 5 both touch SQLite. Tools **write** profile/task **during** the loop; the API **writes** chat history **after** the loop.

---

## Box 1 — You type a message (client)

The UI is still a normal chat box. The important part is it always sends **who** is talking.

```http
POST /api/chat
Content-Type: application/json

{
  "user_id": "u_riya",
  "message": "I normally buy running shoes below ₹10,000."
}
```

| Field | Why it exists |
|---|---|
| `user_id` | Primary key for all three memories. Without it you cannot load “Riya’s budget.” |
| `message` | This turn’s text. Not the whole history — the **server** reloads history from DB. |

That is the first technical difference from Ledger’s `ChatRequest`, which only had `question`.

Optional later: `session_id` if you want conversation to reset while long-term stays. For the unit project, `user_id` alone is enough.

---

## Box 2 — FastAPI `/api/chat` (HTTP + DB session)

Same wiring as your Ledger `api.py`:

```text
router.post("/chat")
  → Pydantic validates the body
  → Depends(get_db) opens a SQLAlchemy Session
  → call run_agent(...)
  → return JSON
```

`get_db` is the same idea as in `database.py`: create session, `yield`, close.

What this box **must** do that Ledger did not:

1. **Identify the user** — `user_id` on every query (`WHERE user_id = :id`).
2. **Not trust the client** to send the full profile. The client only sends the new sentence; memory lives in SQLite.
3. **Commit after tools run** so `update_profile` is not lost if the process crashes mid-reply.

Typical handler shape:

```text
payload.user_id + payload.message
        │
        ▼
load_memory(db, user_id)     # box 3
        │
        ▼
run_agent(db, user_id, memory, new_message)   # box 4
        │
        ▼
save_message(db, user_id, "user", message)
save_message(db, user_id, "assistant", answer)
db.commit()
        │
        ▼
return { answer, profile, task, trace }
```

HTTP status: `422` if body is invalid, `200` with `answer` even if tools returned “no products” (that is a successful agent run, not a crash).

---

## Box 3 — Load memory (the READ path)

This is the box that makes “Show me some new options” work. **Before** the LLM sees the new sentence, you hydrate three structures in Python.

### 3a. Conversation state — `messages` table

```text
SELECT role, content FROM messages
WHERE user_id = 'u_riya'
ORDER BY id DESC
LIMIT 20
```

You reverse them so the LLM gets chronological order:

```python
[
  {"role": "user",      "content": "I normally buy running shoes below ₹10,000."},
  {"role": "assistant", "content": "Here are 3 options under ₹10,000: ..."},
  {"role": "user",      "content": "Show me some new options."},  # this turn
]
```

**Why last N, not the whole table:** OpenAI charges by tokens. Old “too bright / too expensive” chatter is useful for a while, then it is noise. N ≈ 10–20 turns is typical.

**Technical type:** this is **not** a tool. It is just the `messages=` array you already build in `run_llm_agent`. Ledger started that array from scratch every time (`system` + one `user`). Here you **preload** past rows so the model has session context.

### 3b. Task state — `shopping_tasks` table

One **open** row per user (or per session):

| column | example | job |
|---|---|---|
| `category` | `running shoes` | current hunt |
| `budget_max` | `10000` | can copy from profile or be tighter for this hunt |
| `shown_product_ids` | `["P1","P3","P5"]` | JSON array — exclusion list |
| `status` | `open` | so you don’t mix two hunts |

This is how “new options” means **new SKUs**, not “say the same three again.”

If there is no open task, `shown_product_ids = []`.

### 3c. Long-term — `user_profiles` table

| column | example |
|---|---|
| `preferred_brands` | `["Nike","Asics"]` |
| `categories` | `["running shoes"]` |
| `colours` | `["black"]` |
| `budget_max` | `10000` |
| `sizes` | `{"shoes": 9}` |

First-ever message: this row may not exist. Box 4’s `update_profile` **creates** it.

### How the LLM actually *sees* this

Two equivalent designs:

**A. Inject into the system prompt** (simple, good for the course)

```text
SYSTEM: You are a shopping assistant.
Known profile: category=running shoes, budget_max=10000, size=9
Open task: shown_ids=["P1","P3","P5"]
Always call search_products with those filters. Overwrite profile fields when the user changes them.
```

**B. Force a `get_memory` tool call first** (stricter, more like Ledger)

The model cannot “guess” the budget; it must call `get_memory(user_id)` and read JSON.

For 3A, **A + tools for write/search** is enough. You still load memory in FastAPI so the sidebar can show it even before the model answers.

After box 3, Python holds something like:

```json
{
  "profile": { "categories": ["running shoes"], "budget_max": 10000, "sizes": { "shoes": 9 } },
  "task": { "shown_product_ids": ["P1", "P3", "P5"], "status": "open" },
  "history": [ /* last N messages */ ]
}
```

---

## Box 4 — LLM + tools (the same loop as Ledger, different tools)

This **is** your `run_llm_agent` in `loop.py`. Same loop, new tool names.

### 4.1 What you send to the model

```python
client.chat.completions.create(
    model=settings.llm_model,
    messages=[
        {"role": "system", "content": system_prompt + injected_profile_and_task},
        ...history from DB...,
        {"role": "user", "content": current_message},
    ],
    tools=TOOL_SCHEMAS,      # JSON contracts, not Python source
    tool_choice="auto",
)
```

`TOOL_SCHEMAS` is the same idea as in `schemas.py`: name, description, parameter types. The model **never** runs SQL. It only returns:

```json
{
  "tool_calls": [
    {
      "id": "call_abc",
      "function": {
        "name": "update_profile",
        "arguments": "{\"category\":\"running shoes\",\"budget_max\":10000}"
      }
    }
  ]
}
```

That is **function calling**: structured side effects instead of “the model hallucinated three Nike shoes.”

### 4.2 The loop (identical control flow to Ledger)

```text
for step in 1..max_agent_steps:          # you already cap this (e.g. 8)
    response = LLM(messages, tools)
    if no tool_calls:
        return response.content          # final English reply
    for each tool_call:
        args = json.loads(arguments)
        result = execute_tool(name, args, db)   # Python + SQLAlchemy
        append { role: "tool", tool_call_id, content: json.dumps(result) }
        # loop again so the model can call the next tool or answer
```

Why a loop, not one call: Turn 1 needs **several** tools in sequence:

1. `update_profile` — write long-term  
2. `search_products` — read catalog using those fields  
3. `record_shown` — write task  

The model cannot search until profile is set; it cannot record ids until search returns them. That is the same “multiple tool calls” idea as `get_categories` then `calculate_total` in Ledger.

### 4.3 What each tool does in SQL (technical contracts)

**`update_profile`** — long-term write + invalidation

```text
INSERT INTO user_profiles (user_id, categories, budget_max, ...)
VALUES ('u_riya', '["running shoes"]', 10000, ...)
ON CONFLICT (user_id) DO UPDATE
  SET budget_max = excluded.budget_max,   -- OVERWRITE, do not append
      categories = ...,
      updated_at = now()
```

If the user later says “budget is ₹15,000”, this tool sets `budget_max = 15000`. The old 10000 is gone. That **is** invalidation. Do not store `budget_history = [10000, 15000]` as the live filter.

**`search_products`** — catalog read, using memory as WHERE clauses

```text
SELECT * FROM products
WHERE category ILIKE '%running%'
  AND price <= 10000
  AND id NOT IN ('P1','P3','P5')     -- from task.shown_product_ids
  -- optional: brand IN (...), colour, size
LIMIT 3
```

Returns JSON the model is allowed to talk about:

```json
{
  "products": [
    { "id": "P7", "name": "Asics Gel-Pulse", "brand": "Asics", "price": 8499, "colour": "black", "size": 9 }
  ]
}
```

If the model ignores `exclude_ids`, “new options” fails. So either:

- the tool **always** applies `shown_product_ids` from DB itself (safer), or  
- the LLM must pass `exclude_ids` (fragile).

**Safer:** `search_products(db, user_id, extra_filters)` loads shown ids internally. The model cannot “forget” to exclude them.

**`record_shown`** — task write

```text
UPDATE shopping_tasks
SET shown_product_ids = shown_product_ids || '["P7","P8"]'  -- merge, unique
WHERE user_id = 'u_riya' AND status = 'open'
```

**`get_memory`** (optional) — dump profile + task as JSON for the model.

### 4.4 Executor

Same as Ledger `executor.py`: a dict `{"update_profile": fn, "search_products": fn, ...}`. Unknown name → `ToolError`. The LLM cannot invent `drop_table`.

### 4.5 What is **not** a tool

- Saving the chat line (API does that after the loop).  
- Opening the SQLite file (SQLAlchemy session).  
- Rendering the sidebar (frontend).

Tools are **only** the operations you want the model to choose: mutate profile, query catalog, mark items as shown.

---

## Box 5 — SQLite (four tables, one file)

One file, e.g. `shopping.db`, same `create_engine("sqlite:///...")` + `check_same_thread=False` as Ledger.

| Table | Rows mean | Memory kind |
|---|---|---|
| `products` | Fake catalog (seeded once) | Not memory — **world data** |
| `user_profiles` | One row per user | **Long-term** |
| `shopping_tasks` | Open (and maybe closed) hunts | **Task** |
| `messages` | Every user/assistant line | **Conversation** |

```text
products          user_profiles         shopping_tasks          messages
─────────         ─────────────         ──────────────          ────────
id PK             user_id PK            id PK                   id PK
name              brands JSON           user_id FK              user_id FK
brand             categories JSON       category                role
category          colours JSON          budget_max              content
colour            budget_max            shown_ids JSON          created_at
price             sizes JSON            status
sizes JSON        updated_at            session_id?
```

**Why SQLite instead of a vector DB:** these fields are **structured**. `budget_max <= 10000` is a number comparison. Embeddings would retrieve “user once said 10,000” *and* “user said 15,000” as similar text — exactly the stale-memory bug.

**Transactions:** all tool writes in the same `Session` as the request. `commit()` once at the end of `/chat` so you don’t persist `record_shown` if `update_profile` failed (or commit after each tool if you prefer durability over atomicity — for a demo, one commit at the end is fine).

**Seed:** `seed.py` inserts ~30 products (some &lt; 10k, some &gt; 10k) and maybe one pre-filled profile so you can demo a returning user.

---

## Box 6–7 — Reply + sidebar (API contract + UI)

Response should expose memory so you can **see** it, not only chat:

```json
{
  "answer": "Here are some new running shoes under ₹10,000: ...",
  "mode": "llm",
  "trace": [
    { "type": "tool_call", "name": "search_products", "arguments": { "max_price": 10000 } },
    { "type": "tool_result", "name": "search_products", "result": { "products": [ ... ] } },
    { "type": "tool_call", "name": "record_shown", "arguments": { "ids": ["P7","P8"] } }
  ],
  "memory": {
    "profile": { "categories": ["running shoes"], "budget_max": 10000, "sizes": { "shoes": 9 } },
    "task": { "shown_product_ids": ["P1","P3","P5","P7","P8"] }
  }
}
```

- **Chat panel** ← `answer`  
- **Sidebar** ← `memory.profile` + `memory.task.shown_product_ids`  
- **Debug** ← `trace` (same teaching trick as Ledger)

After refresh, `GET /api/memory?user_id=u_riya` can reload the sidebar from DB without chatting. That proves long-term storage independently of the LLM.

---

## One request, fully traced (Turn 1)

Message: `"I normally buy running shoes below ₹10,000."`  
Profile empty, no task, no history.

| Step | What runs | Data change |
|---|---|---|
| HTTP | Parse body, `user_id=u_riya` | — |
| Load | 3 empty reads | `profile=None`, `shown=[]`, `history=[]` |
| LLM round 1 | `update_profile(categories=["running shoes"], budget_max=10000)` | **INSERT** profile |
| LLM round 2 | `search_products` → P1, P3, P5 | catalog **SELECT** |
| LLM round 3 | `record_shown(["P1","P3","P5"])` | **INSERT/UPDATE** task |
| LLM round 4 | no tools, English answer | — |
| Persist | two `INSERT` into `messages` | conversation |
| JSON | answer + memory + trace | UI |

Token-level: after round 1, `messages` on the OpenAI call includes a `role: "tool"` object with `{"ok": true, "budget_max": 10000}`. The model’s next completion can then legally call `search_products` with `max_price=10000`.

---

## Turn 2 on the same flowchart (why box 3 matters)

Message: `"Show me some new options."`

| Step | Difference from Turn 1 |
|---|---|
| Load | Profile **already** has running shoes / 10000. Task **already** has P1,P3,P5. History has Turn 1. |
| LLM | Usually **skips** `update_profile`. Calls `search_products` with `price <= 10000` and `id NOT IN (P1,P3,P5)`. |
| Write | `record_shown` appends P7,P8. Messages append two more rows. |
| User-visible | Reply never asked “options for what?” |

If you skip box 3 and only send the new sentence (Ledger-style), the model has no budget and no exclusion list. The flowchart **fails** even if box 4 still “works.”

---

## How this maps onto files you already know

| Ledger (tool calling) | Shopping assistant (this flowchart) |
|---|---|
| `POST { question }` | `POST { user_id, message }` |
| No load-memory step | **New box** — 3 SELECTs |
| Tools: `get_categories`, `filter_transactions`, … | Tools: `update_profile`, `search_products`, `record_shown` |
| `transactions` table | `products` + `user_profiles` + `shopping_tasks` + `messages` |
| `loop.py` until no `tool_calls` | Same loop |
| Trace in the UI | Trace **plus** memory sidebar |
| One-shot question | Multi-turn, same `user_id` |

The new technical idea is not a new LLM API. It is **read state → tool loop → write state** on every `/chat` call.

---

## Mental model in one sentence

**FastAPI** is the door, **load memory** fills the model’s context from SQLite, **the Ledger-style tool loop** lets the model update that SQLite and query the catalog, **then** you save the chat and show both the answer and the stored profile.

If you want, next we can walk the same diagram using only the OpenAI `messages` array (system / user / assistant / tool) for those two example sentences, line by line.

## User

the flow i have unerstood here is suppose user asks the llm a question like i want a dress in the price range 1k-2k for women llm will take the useful info from this and save them inside the table by inserting a row with the user id as a primary key and while returning the user some rows it will only return the rows by referring to the user preferences from the saved memory here i think that the memory will be stored in the memory by extracting the user parameters and storing them inside the tabel

## Assistant

Your picture is **mostly right**. One important correction: the memory table does **not** store dresses. It stores **preferences**. The dresses come from a **separate catalog table**, filtered using those preferences.

---

## What you got right

For:

> “I want a dress in the price range 1k–2k for women”

the agent should:

1. **Extract** structured fields from the sentence  
2. **Save** them on that user’s row (`user_id` is the key)  
3. **Search products** using those saved fields  
4. **Reply** only with items that match

That *is* memory: parameters in a table, not “hope the chat history still contains the sentence.”

---

## The one mix-up

There are **two** tables involved, not one.

| Table | What a row is | Example |
|---|---|---|
| **`user_profiles`** (memory) | This person’s prefs | `user_id=u_riya`, category=`dress`, min=1000, max=2000, audience=`women` |
| **`products`** (catalog) | Items in the fake shop | dozens of dresses, shoes, etc. |

Flow:

```text
sentence
  → extract prefs
  → UPSERT user_profiles   (memory WRITE)
  → SELECT products WHERE they match those prefs   (catalog READ)
  → return matching product rows (not the memory row)
```

The UI shows **product rows**. Memory is the **filter** used to pick them.

If you only inserted into memory and “returned that row,” the user would see `"dress, 1000–2000, women"` — preferences — not actual dresses.

---

## Your sentence → extracted parameters

The LLM (via `update_profile`) turns English into columns:

| Spoken | Stored |
|---|---|
| dress | `categories = ["dress"]` |
| 1k–2k | `budget_min = 1000`, `budget_max = 2000` |
| for women | `audience = "women"` (or a department/gender column on products) |

`user_id` does **not** come from the sentence. It comes from the request (`POST /api/chat { "user_id": "u_riya", "message": "..." }`). Same person, same row, every time.

---

## Insert vs update (same primary key)

- **First message** from `u_riya` → **INSERT** one profile row.  
- **Later** “make it 2k–3k” → **UPDATE that same row** (`budget_min=2000`, `budget_max=3000`). Old 1k–2k is overwritten.

You never add a second profile row for the same user. That would be two budgets and stale memory.

SQLAlchemy-style: `INSERT ... ON CONFLICT (user_id) DO UPDATE`.

---

## How products are actually chosen

After memory is saved:

```text
SELECT * FROM products
WHERE category ILIKE '%dress%'
  AND department = 'women'          -- or gender / audience
  AND price >= 1000
  AND price <= 2000
  AND id NOT IN (...already shown...)   -- task memory
LIMIT 3
```

Those **product** rows go back to the LLM, which writes the reply.

So: **memory = WHERE clause**, **catalog = FROM products**.

---

## What the LLM actually does (not raw SQL)

It does not “talk to the table” in English. It calls tools, same as Ledger:

1. `update_profile(category="dress", budget_min=1000, budget_max=2000, audience="women")`  
   → writes `user_profiles`  
2. `search_products(...)`  
   → reads `products` using that profile (or using args the model copied from memory)  
3. `record_shown(["D1","D2","D3"])`  
   → task table, so “show more” does not repeat the same three

---

## Next message (this is the point of memory)

> “Show me some new options.”

No dress, no price, no “women” in the text.

Server loads `u_riya`’s row → still `dress`, `1000–2000`, `women` → `search_products` with the same filters, excluding already shown ids.

If extraction/storage never happened, this second line would be useless.

---

## Short version

Yes: **extract parameters → store on the user’s profile row → filter the catalog with that row.**

No: you do **not** return the memory row as the shopping results. You return **products** that match it.

## User

## Unit Project 3A — Personal Shopping Assistant

### Problem

Remember a user's:

* Preferred brands
* Categories
* Colours
* Budget
* Sizes

### Example

User initially says:

> "I normally buy running shoes below ₹10,000."

Later:

> "Show me some new options."

### Data Preparation

**SELF**

Create synthetic user profiles and interactions.

### Owner

**Member 1**

---              can you implement this project in most efficient way  using the tools and the database as defined in this info . use the langchain for this implementation whereever possible and give the most efficient implementation for it

## Assistant

I'll implement the shopping assistant with LangChain tools, SQLite memory, and the FastAPI flow we mapped. First I'm checking your existing project patterns so this stays consistent.

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\config.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\agent\\prompts.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\agent\\executor.py"}
```

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\static","globPattern":"**/*"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Company_knowledge_assistant_rag\\app\\config.py"}
```

### Tool Read File V2

```
{"path":"C:\\Users\\bhava\\.agents\\skills\\developing-with-streamlit\\SKILL.md","limit":30}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\static\\index.html"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\static\\styles.css"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\static\\app.js"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Tool_calling\\app\\seed.py","limit":80}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Company_knowledge_assistant_rag\\app\\generate.py","limit":80}
```

### Tool Todo Write

### Tool Get Mcp Tools

```
{"server":"cursor-app-control","toolName":"rename_chat","toolCallId":"call-621268d6-a579-44a1-b241-622ab9d11207-36\nfc_b945002d-0a27-9ee4-88b7-4e0c7e752886_1"}
```

## Assistant

Building the core database, memory store, and seed data first, then wiring LangChain tools on top.

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\memory.py","offset":200,"limit":130}
```

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Edit File V2

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\agent\\planner.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\agent\\extract.py","offset":1,"limit":40}
```

### Tool Todo Write

### Tool Edit File V2

### Tool Run Terminal Command V2

### Tool Run Terminal Command V2

### Tool Await

```
{"taskId":"828499","blockUntilMs":120000,"regex":"Successfully installed|ERROR|error:"}
```

### Tool Read File V2

```
{"path":"C:\\Users\\bhava\\.cursor\\projects\\d-GA-PythonLearning-API-Stylumia-Day3-Memory-Personal-shopping-assistant\\terminals\\828499.txt","offset":-30}
```

## Assistant

Dependencies installed. Next I’ll run the brief’s two-turn dialogue against the API to confirm memory actually sticks.

### Tool Run Terminal Command V2

### Tool Run Terminal Command V2

### Tool Run Terminal Command V2

### Tool Run Terminal Command V2

### Tool Run Terminal Command V2

### Tool Edit File V2

### Tool Run Terminal Command V2

### Tool Run Terminal Command V2

### Tool Read Lints

```
{"paths":["D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app"]}
```

### Tool Todo Write

## Assistant

The Personal Shopping Assistant is in `Personal_shopping_assistant`. One FastAPI app, one SQLite file, three kinds of memory, LangChain tools for the LLM path.

I verified the brief dialogue in rules mode (no API key): turn 1 stores running shoes + ₹10,000; turn 2 returns **new** SKUs without asking again; raising the budget overwrites ₹10,000.

---

## How to run

```powershell
cd D:\GA\PythonLearning\API\Stylumia\Day3_Memory\Personal_shopping_assistant
.\.venv\Scripts\activate
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

Optional LLM: copy `.env.example` to `.env` and set `OPENAI_API_KEY`. Same tools either way.

---

## What to click in the UI

1. Shopper: **New shopper**
2. `I normally buy running shoes below ₹10,000.`
3. `Show me some new options.`
4. Watch the left rail: long-term profile vs already-shown product ids

**Riya** / **Meera** are pre-filled synthetic profiles. **New session** clears chat + shown items; **Wipe profile** also clears preferences (stale-memory demo).

---

## Architecture (efficient on purpose)

| Piece | Role |
|---|---|
| SQLite `user_profiles` | Long-term: brands, categories, colours, budget, sizes |
| SQLite `shopping_tasks` | Task: current hunt + `shown_product_ids` |
| SQLite `messages` | Conversation: last N turns into LangChain messages |
| SQLite `products` | Synthetic catalog (not memory) |
| LangChain `StructuredTool` | `get_memory`, `update_profile`, `search_products` |
| `ChatOpenAI.bind_tools` | LLM loop (same idea as Ledger) |

`search_products` reads **live** memory, applies the filters, **skips already shown ids**, and records the new ones. “Show me some new options” is one tool call, not a second memory system.

Budget changes **overwrite** the column (`₹10,000` → `₹15,000`). That is invalidation.

---

## Files that matter

- `app/memory.py` — all reads/writes
- `app/agent/tools.py` — LangChain tool wrappers
- `app/agent/loop.py` — LLM tool-calling loop
- `app/agent/planner.py` — rules fallback when no key
- `app/seed.py` + `data/interactions.json` — synthetic users, catalog, demo script

The agent never invents products: it can only recommend rows `search_products` returned.

## User

<timestamp>Saturday, Aug 29, 2026, 12:22 PM (UTC+5:30)</timestamp>
<system_notification>
The following task has finished. If you were already aware, ignore this notification and do not restate prior responses.

<task>
kind: shell
status: success
task_id: 828499
title: Create venv and install dependencies
tool_call_id: call-f2a97135-cc64-4ea2-a066-09ccbe750ea1-71
fc_00ca8e8f-11b9-923f-b2e9-2aab7f34b03c_0
output_path: C:\Users\bhava\.cursor\projects\d-GA-PythonLearning-API-Stylumia-Day3-Memory-Personal-shopping-assistant\terminals\828499.txt
</task>
</system_notification>
<user_query>Briefly inform the user about the task result and perform any follow-up actions (if needed). If there's no follow-ups needed, don't explicitly say that.</user_query>

## Assistant

The virtual environment is ready and the dependencies are installed, including FastAPI, SQLAlchemy, and LangChain.

The shopping assistant is already wired up on top of that. From the project folder:

```powershell
.\.venv\Scripts\activate
uvicorn app.main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000).

## User

{"status":"error","message":"Not Found","error_code":"HTTP_ERROR","details":null}  showing this output

## Assistant

I'll check how the app is running and which URL is returning that 404.

### Tool Glob File Search

```
{"targetDirectory":"C:\\Users\\bhava\\.cursor\\projects\\d-GA-PythonLearning-API-Stylumia-Day3-Memory-Personal-shopping-assistant\\terminals","globPattern":"*.txt"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\main.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\api.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\static\\app.js","limit":50}
```

## Assistant

That JSON is not from our FastAPI app — I’ll check whether the server is up and which URL is 404ing.

### Tool Get Mcp Tools

```
{"server":"cursor-ide-browser","toolName":"browser_tabs","toolCallId":"call-ad877d0c-09ee-457a-9336-21b97515b5a2-88\nfc_f434f956-610f-9c54-9604-85a62759b767_0"}
```

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant","globPattern":"**/*.{py,html}"}
```

### Tool Ripgrep Raw Search

```
{"pattern":"HTTP_ERROR|Not Found","path":"C:\\Users\\bhava\\.cursor\\projects\\d-GA-PythonLearning-API-Stylumia-Day3-Memory-Personal-shopping-assistant\\agent-transcripts","caseInsensitive":false,"headLimit":20,"multiline":false,"toolCallId":"call-ad877d0c-09ee-457a-9336-21b97515b5a2-90\nfc_f434f956-610f-9c54-9604-85a62759b767_2","offset":0}
```

### Tool Mcp

```
{"name":"cursor-ide-browser-browser_tabs","args":{"action":"list"},"toolCallId":"call-6b567be3-f256-4f10-97e2-ceb9faee9195-91\nfc_0ef85a4b-24f9-9a8a-a16d-de670148489b_0","providerIdentifier":"cursor-ide-browser","toolName":"browser_tabs","smartModeApprovalOnly":false,"skipApproval":true,"serverIdentifier":"cursor-ide-browser"}
```

### Tool Run Terminal Command V2

### Tool Run Terminal Command V2

## Assistant

Port 8000 is Docker, not this app — that 404 is from Docker. I'll start the shopping assistant on a free port.

### Tool Run Terminal Command V2

### Tool Run Terminal Command V2

### Tool Await

```
{"taskId":"828500","blockUntilMs":25000,"regex":"Application startup complete|Uvicorn running|Error"}
```

### Tool Run Terminal Command V2

## Assistant

That JSON is **not from the shopping assistant**. Something else is already bound to **port 8000** (Docker), and that service returns:

```json
{"status":"error","message":"Not Found","error_code":"HTTP_ERROR","details":null}
```

The assistant is running on **port 8001** instead.

Open this in your browser: [http://127.0.0.1:8001](http://127.0.0.1:8001)

You should see the Atelier chat UI. Pick **New shopper**, then try:

1. `I normally buy running shoes below ₹10,000.`
2. `Show me some new options.`

If you start it yourself later, skip 8000:

```powershell
cd D:\GA\PythonLearning\API\Stylumia\Day3_Memory\Personal_shopping_assistant
.\.venv\Scripts\activate
uvicorn app.main:app --reload --port 8001
```

## User

what info is eing stored in the conversation memory, long term and the task memory how are they different

## Assistant

I'll read the models and memory store so the three kinds match what the app actually saves.

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\models.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\memory.py","limit":180}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\memory.py","offset":304,"limit":55}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\agent\\loop.py","limit":50}
```

## Assistant

They are **three different tables for the same shopper**, not three copies of the chat. Each answers a different question.

---

## Long-term memory — `user_profiles`

**Question it answers:** Who is this shopper, in general?

| Stored | Example after *“I normally buy running shoes below ₹10,000.”* |
|---|---|
| Preferred brands | `[]` until they name Nike, etc. |
| Categories | `["running shoes"]` |
| Colours | `["black", "navy"]` if they said that |
| Budget | `budget_max = 10000` (and `budget_min` if they gave a range) |
| Sizes | `{"shoes": "9"}` |
| Audience | `"women"` / `"men"` / `"unisex"` |

This is the **profile**. One row per `user_id`. Budget/size/audience are **overwritten** when they change (“my budget is now ₹15,000” replaces 10,000). Brands/colours/categories are **merged** unless they say to forget a brand.

**Survives “New session.”** Cleared only by **Wipe profile**.

---

## Task memory — `shopping_tasks`

**Question it answers:** What hunt is in progress *right now*, and what did we already show?

| Stored | Role |
|---|---|
| `category` | Current hunt (`running shoes` this search, `dress` after they switch) |
| `budget_min` / `budget_max` | Filters for this hunt (copied from the profile when they update budget) |
| `shown_product_ids` | e.g. `["P09", "P06", "P03"]` so the next search skips them |
| `status` | `open` |

This is **not** “I like Nike.” It is **progress**: don’t repeat P09, and if they switch from shoes to dresses, shown ids are **reset**.

**Cleared by “New session”** (`shown_product_ids` emptied). Profile stays.

---

## Conversation memory — `messages`

**Question it answers:** What did we say in this chat?

Each row is only:

- `role` — `user` or `assistant`
- `content` — the sentence / reply
- `created_at`

The last ~20 turns are sent back to the LLM as chat history. **Tool traces are not stored** (no `update_profile` JSON in this table).

This is the **transcript**. Useful for tone and “you said the second pair was too bright.” It is a **poor** place to look up budget, because two different budgets can both appear in old messages. The profile column is the source of truth for that.

**Cleared by “New session.”**

---

## How they differ (same sentence)

> “I normally buy running shoes below ₹10,000.”

| Kind | What gets written |
|---|---|
| **Long-term** | category = running shoes, budget_max = 10000 |
| **Task** | hunt category = running shoes, then after search: shown ids of the 3 products |
| **Conversation** | user text + assistant “here are 3 options…” |

> “Show me some new options.”

| Kind | What is used |
|---|---|
| **Long-term** | still running shoes, still ₹10,000 — sentence has neither |
| **Task** | exclude already shown ids; append the new ones |
| **Conversation** | this new line + previous chat (context, not the filter) |

If you only kept conversation, the model *might* remember the budget from the first message. If you only kept long-term, “new options” would still know the budget but **could show the same three shoes again**. Task memory is what makes them **new**.

---

## One-line distinction

- **Long-term** = stable preferences (who they are).  
- **Task** = this shopping job (what’s in progress, what was already shown).  
- **Conversation** = the chat log (what was said), not the structured filters.

The left rail in the UI is long-term + task. The thread is conversation.

## User

by using the info in the Task = this shopping job (what’s in progress, what was already shown). it want show the info not shown before

## Assistant

Yes — that’s exactly what task memory is for. I’ll point to the code that skips already-shown products.

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\memory.py","offset":202,"limit":100}
```

## Assistant

Yes. **Task memory is the “already shown” list.** The next search is forced to pick products that are **not** on that list.

---

## What happens

**Turn 1** — “I normally buy running shoes below ₹10,000.”

1. Search the catalog (running shoes, price ≤ 10000).
2. Return 3 items, e.g. `P09`, `P06`, `P03`.
3. Save those ids on the task:

```text
shown_product_ids = ["P09", "P06", "P03"]
```

**Turn 2** — “Show me some new options.”

Long-term memory still says running shoes + ₹10,000. Task memory adds:

```text
AND product.id NOT IN ("P09", "P06", "P03")
```

So you get a **new** 3, e.g. `P08`, `P07`, `P04`. Those ids are **appended**:

```text
shown_product_ids = ["P09", "P06", "P03", "P08", "P07", "P04"]
```

That is the whole trick: **exclude old ids, then record the new ones.**

---

## Where that is in code

Skip anything already on the task:

```255:256:app/memory.py
    if shown:
        query = query.where(Product.id.notin_(shown))
```

After a successful search, merge the new ids onto the task:

```279:283:app/memory.py
    if record_shown and payload:
        merged = _uniq([*(task.shown_product_ids or []), *[item["id"] for item in payload]])
        task.shown_product_ids = merged
```

The LLM does not have to remember SKUs. `search_products` always reads `shopping_tasks.shown_product_ids` from SQLite.

---

## When it will show “old” items again

- **New session** — shown list is cleared; the same shoes can appear again.
- **Category change** (shoes → dress) — shown list is reset for the new hunt.
- **Catalog exhausted** — every matching item is already in `shown_product_ids`; you get “no new catalog items…” instead of repeats.

So: long-term = *what* to search; task = *which ids not to show again*.

## User

and what does this project do with the long term memory

## Assistant

**Long-term memory is the shopper profile.** The project **saves** it from what they say, **reuses** it on later turns (and later sessions), and **overwrites** it when they change their mind.

---

## What it stores

One row in `user_profiles` per shopper:

- preferred brands  
- categories  
- colours  
- budget (`budget_min` / `budget_max`)  
- sizes (`shoes: 9`, `clothing: M`)  
- audience (women / men / unisex)

That is the brief: *remember brands, categories, colours, budget, sizes*.

---

## What the app *does* with it

**1. Write — extract from English, save as fields**

“I normally buy running shoes below ₹10,000.”  
→ `categories = ["running shoes"]`, `budget_max = 10000`

Not the raw sentence. Structured columns, via `update_profile`.

**2. Read — fill in a vague later request**

“Show me some new options.” has no category and no budget.

Search still uses the profile:

- category = running shoes  
- price ≤ 10000  
- plus colours / size / brands if those were saved  

Without long-term memory, that second line would be “options for what?”

**3. Filter and rank the catalog**

| Profile field | Effect on search |
|---|---|
| category | `WHERE category` matches |
| budget | `WHERE price` between min and max |
| audience | women’s vs unisex, etc. |
| size | keep items that include that size |
| colours | *prefer* those colours (not a hard wall) |
| brands | *prefer* those brands first |

So long-term memory is the **default WHERE clause**. Task memory only adds “don’t show these ids again.”

**4. Invalidate — replace stale facts**

“My budget is now ₹15,000.” **overwrites** 10000. It does not keep both.

“Forget Nike…” **removes** Nike from `preferred_brands`.

That is why it is a profile table, not a chat log: the live value is whatever is in the row *now*.

**5. Survive a new session**

**New session** clears chat + shown ids. The profile stays.

Next day, “show me some new options” can still mean running shoes under ₹10,000.

**Wipe profile** is the only UI action that empties long-term memory.

---

## What it does *not* do

It does **not** store product lists. Products live in `products`.  
It does **not** store “already shown.” That is task memory.  
It does **not** store the transcript. That is conversation memory.

Long-term = **who they are as a shopper**, used every time you search until they update it.

## User

i need every thing in the range above 15000  when i put this message in the chatbot it did not change the budget info stored in the long term memory

## Assistant

The phrase likely isn’t matching the budget extractor, so `update_profile` never runs. I’ll check how that sentence is parsed.

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\agent\\extract.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\agent\\planner.py","limit":90}
```

## Assistant

The profile did not update because **that sentence is not one the rules extractor understands**, so `update_profile` never runs. The old budget stays.

---

## Why `"i need every thing in the range above 15000"` is ignored

In **Rules mode** (no API key), budget is parsed only in `extract.py`. Your line matches **none** of those patterns.

| Pattern | What it looks for | Your message |
|---|---|---|
| **Range** | two numbers with `-` or `to` (`1k-2k`) | only one number |
| **Below** | `below` / `under` / `up to` / `<` | you said **above** |
| **Budget now** | the word `budget` (e.g. “my budget is now ₹15,000”) | no “budget” |
| **₹ fallback** | a **₹** sign | you wrote `15000` with no ₹ |

So `has_slots` stays false → planner **does not** call `update_profile` → it only searches with the **old** profile. The left rail looks unchanged.

Phrases that **do** update today:

- `My budget is now ₹15,000.`
- `I normally buy running shoes below ₹10,000.`
- `I want a dress in the price range 1k-2k`

---

## Even after parsing, “above 15000” is a different kind of budget

The app was built around a **ceiling** (`budget_max`: “below ₹10,000”).

“Above 15000” is a **floor**: `budget_min = 15000`, and the old **max must be cleared**.

If you only set min to 15000 and leave max at 10000, search becomes:

```text
price >= 15000 AND price <= 10000  → no products
```

So a proper fix is:

1. Match `above` / `over` / `more than` / `greater than`.
2. Set `budget_min = 15000`.
3. Clear `budget_max` (same idea as `clear_budget`, but only the max).

---

## What you can do right now (no code)

Say it in a form the extractor already knows, for example:

> My budget is now ₹15,000.

That overwrites `budget_max` to 15000. It still means “up to 15k”, **not** “only items above 15k”.

To mean **only above 15k**, the extractor has to be extended. Switch to **Agent mode** and ask to add an `above` / `over` / `more than` parser that sets `budget_min` and clears `budget_max`.

## User

how may kurtas have you stored here

### Tool Ripgrep Raw Search

```
{"pattern":"kurta","path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant","glob":"*.{py,json}","caseInsensitive":false,"multiline":false,"toolCallId":"call-1aae92fd-a78b-49cc-bcff-2f895f0a29df-105\nfc_07fb9dcc-56c7-994e-b88b-7796b68e5b77_0","offset":0}
```

## Assistant

**One.** The synthetic catalog has a single kurta:

- **K01** — Manyavar Silk Kurta, maroon, ₹3,499, men’s sizes XS–XL

It is seeded in `app/seed.py`. The word “kurta” also appears in the category parser, but that is not extra products.

## User

in the session if the user asks kurts the assistant will show 1 kurta and then task memory will show k01 as already shown and if the user asks for one more kurta the assistant will replay as No new catalog items match the current memory. Try a wider budget or a new category.  what does this mean is it telling that there are no more kurtas available every thing is already shown

## Assistant

Yes. That message means: **there is nothing left in the catalog that still matches this hunt and has not already been shown.**

For kurtas that is almost always **“the only kurta is K01, and you already saw it.”**

---

## What happened

1. First ask for kurtas → search finds **K01** → it is shown → task memory records `shown_product_ids = ["K01"]`.
2. “One more kurta” → search again with the same filters (kurta, budget, size, …) **and** `id NOT IN ("K01")`.
3. The catalog only has **one** kurta, so the result set is empty.
4. The assistant then uses this note from `search_products`:

> No new catalog items match the current memory. Try a wider budget or a new category.

“Current memory” here is **task + long-term together**: still looking for kurtas, and K01 is already on the shown list.

It is **not** saying the shop is empty of all clothes. It is saying **no new kurtas (under your saved filters) are left to show.**

---

## How you could see a kurta again

- **New session** — clears `shown_product_ids`, so K01 can appear again.
- **More kurtas in `seed.py`** — a second ask could return K02, K03, …
- **Widen filters** — if budget/size had excluded items; with only one kurta, that usually does not help.
- **New category** — e.g. dresses; that resets shown ids for the new hunt.

So your reading is right: with one kurta in the catalog, the second request correctly means **everything matching that hunt has already been shown.**

## User

and this will show the product for the users only if they menton the products among the already existing category right if the user asks the other categories then the one mentioned in this then the user will get no result right as thesea are the only available categories Categories
dress · jeans · kurta · running shoes · shirt · t-shirt

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\seed.py","limit":50}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\agent\\extract.py","limit":20}
```

## Assistant

Mostly yes. The shop only has those **six** product categories. Ask for something that isn’t in the catalog (and isn’t treated as an alias of one of them) and you will not get new items of that type.

---

## What is actually in the catalog

| Category | How many items |
|---|---|
| running shoes | 13 |
| dress | 8 |
| shirt | 2 |
| t-shirt | 1 |
| jeans | 1 |
| kurta | 1 |

Those are the only `category` values on product rows. Search is `category ILIKE '%…%'`, so it only hits these.

---

## Three different outcomes

**1. User names a real category (or an alias of one)** → products can appear.

Examples that **do** map onto stock:

- “sneakers” / “trainers” → **running shoes**
- “gown” → **dress**
- “tee” → **t-shirt**
- “kurtas” → **kurta**

**2. User names a category the parser knows but seed data does not** → empty search.

The extractor also understands **formal shoes** and **sandals**, but **no products** use those categories. Search runs, finds 0 rows, you get:

> No new catalog items match the current memory…

**3. User names something unknown** (laptop, saree, phone, jacket) → **not always** a “no kurtas” empty search.

Rules mode **does not extract** “saree” as a category. Then:

- **New shopper, no hunt yet** → “Tell me what you usually buy…” (no search).
- **Already shopping kurtas** → it may **keep the old hunt** and show more kurtas (or “no new items” if K01 is already shown). It does **not** switch to sarees.

So: unknown category ≠ guaranteed “no products.” It can mean “I ignored that word and used long-term/task memory instead.”

---

## Also: budget / shown ids can hide stock

Even for **dress** or **running shoes**, you can get zero rows if:

- budget still says below ₹10,000 and they asked for something that doesn’t fit, or  
- every matching SKU is already in task `shown_product_ids`.

That is the same “no new catalog items” line, not “this category doesn’t exist.”

---

**Short version:** Yes — recommendations only come from those six seeded categories (plus a few nicknames). Other product types are not in the shop. If they say a word the parser doesn’t know, you might get **no switch** rather than a clean “we don’t sell that.”

## User

in this project as you are getting the preferences of the user may be color and using it as a preference for every product they would choose right ....don't you think it is wrong the user might need that preference only for the product that they are currently searching for later they might need different color for the other product that they will be looking next what do you say

## Assistant

You’re right to question that. Treating **this hunt’s colour** as **every future product’s colour** is too strong. The brief listed colour as a long-term slot, and this app **does** save it on the profile — that is a design tradeoff, not a law of shopping.

---

## What the project does today

If they say “I prefer black” (or black shows up while extracting), it is **merged into long-term** `user_profiles.colours`.

On later searches, that colour is used as a **preference boost** (not a hard filter): matching colours are ranked first; other colours can still appear.

Category **does** switch (shoes → dress) and shown ids reset. **Colour does not reset.** So a later dress hunt can still prefer black because of an earlier shoe comment.

That is exactly the bug you’re describing, if they only meant black **for these shoes**.

---

## Why it feels wrong

Colour (and often brand) is often **per hunt**, not identity:

| They said | Sensible memory |
|---|---|
| “Black running shoes under ₹10k” | Task: this search is black shoes |
| “Now show me dresses” | New hunt; black should **not** be assumed |
| “I usually wear navy and beige” | Long-term taste; OK to keep |

Budget and shoe size are closer to **stable**. “Black today” is often **task**.

The three-memory split was meant for this:

- **Task** = filters for *this* job (colour, current category, already shown)  
- **Long-term** = what tends to stay true (size 9, budget cap, “I like Nike”)

This implementation put colour (and brands) in **long-term** because the assignment listed colour next to brands and budget. That matches the spec; it does **not** always match real shopping.

---

## A better rule (if you change it later)

- Default: colour on **task only** (`shopping_tasks`), cleared when category changes.  
- Promote to **profile** only if they say “I usually / I normally / I always prefer black,” or they repeat it across hunts.  
- Explicit this-turn colour (“make this one red”) should override task colour and **not** rewrite the profile.

Same idea for “I want a pink dress” vs “I like pink.”

---

**Bottom line:** Yes — blindly reusing one colour for every later product is the wrong default. The app does it because colour was modeled as a long-term preference. For a more realistic assistant, colour (and sometimes brand) should live on the **current hunt**, and only stay on the profile when the user clearly means a lasting taste.

## User

i couldn't see the conversational memory in the display that yu have been showing

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\static\\index.html","limit":80}
```

### Tool Ripgrep Raw Search

```
{"pattern":"memory|history|conversation|thread","path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\static","caseInsensitive":false,"multiline":false,"toolCallId":"call-24896709-2aa8-4bd7-8afc-94d97a21c641-109\nfc_8744be76-b407-98b2-a31d-fea5e78193cb_1","offset":0}
```

## Assistant

You’re looking in the right place for **long-term** and **task** — those are the only two boxes in the **left rail**. **Conversation memory was never given its own panel.**

---

## Where it actually is

The **chat thread on the right** *is* conversation memory: each You / Atelier bubble is a row in the `messages` table (`role` + `content`).

The left rail is labeled on purpose:

- **Long-term memory** — profile fields  
- **Task memory** — current hunt + already shown ids  

There is no third heading “Conversation memory,” so it feels like it’s missing. The subtitle under the title only hints: “Conversation is stored per shopper.”

On load or when you change shopper, the UI calls `/api/history` and **replays those messages into the thread**. That is the stored conversation, not a live-only view.

---

## How to see that it’s stored

1. Send two messages.  
2. Switch shopper (e.g. Riya) and back to **New shopper**.  
3. The same bubbles should come back — they were loaded from SQLite, not from RAM.

**New session** deletes those rows, so the thread goes empty. Profile/task (except shown ids) behave as we described before.

Tool traces (the dashed “Tool trace” blocks) are **not** saved in conversation memory. Refresh and they disappear; only the user and assistant text remain.

---

If you want a left-rail card like “Conversation memory: 4 turns stored” so all three kinds look the same, switch to **Agent mode** and that can be added.

## User

how many dresses are there in the database i think 8

### Tool Ripgrep Raw Search

```
{"pattern":"\"category\": \"dress\"","path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\seed.py","caseInsensitive":false,"multiline":false,"toolCallId":"call-8853afa8-1f05-4db7-8753-9755fcaf94fc-110\nfc_c258ad33-affd-97b9-ab45-c6beebf1aba8_0","offset":0}
```

## Assistant

Yes — **8 dresses** (D01–D08), all women’s.

| Id | Name | Price |
|---|---|---|
| D01 | Zara Linen Midi Dress | ₹1,890 |
| D02 | H&M Floral A-Line | ₹1,499 |
| D03 | Forever 21 Shirt Dress | ₹1,299 |
| D04 | Westside Cotton Day Dress | ₹1,699 |
| D05 | AND Wrap Dress | ₹1,999 |
| D06 | Global Desi Printed Dress | ₹1,799 |
| D07 | Zara Satin Slip Dress | ₹3,290 |
| D08 | Mango Structured Midi | ₹4,590 |

A search with budget **1k–2k** only returns D01–D06. D07 and D08 show up if the max is raised (or there is no ceiling that low). The assistant still only shows **3 at a time**, then uses task memory so “new options” can continue until those 8 (that match the filters) are exhausted.

## User

there is no option for saving the profile right

### Tool Ripgrep Raw Search

```
{"pattern":"wipe|reset|save|commit|update_profile","path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app","glob":"*.{py,html,js}","caseInsensitive":false,"multiline":false,"toolCallId":"call-fd393ccf-ef58-4463-b63b-092fef82e39c-111\nfc_53eba21f-07fe-9ec0-bf19-b66a7332914f_0","offset":0}
```

## Assistant

Correct: **there is no “Save profile” button.** The profile is saved **automatically**.

---

## How saving works

Whenever the assistant extracts preferences from a message, it calls `update_profile` and FastAPI **`commit()`s** to SQLite (`shopping.db`). That **is** the save.

The left rail is reading that stored row, not a draft waiting for you to click Save.

The only profile-related buttons are:

| Button | What it does |
|---|---|
| **New session** | Clears chat + already-shown ids. **Keeps** the profile. |
| **Wipe profile** | Clears long-term prefs (brands, budget, sizes, …) as well. |

There is no “Save,” “Export,” or “Create new shopper” form. Shoppers are the dropdown (**New shopper**, **Riya**, **Meera**) plus any `user_id` created by chatting.

---

## How to check it persisted

1. Set a budget/category in chat.  
2. Refresh the page or switch shopper and switch back.  
3. Long-term memory should still show those fields.

If the rail does not update, the extractor never wrote the field (as with “above 15000”), not because Save was skipped.

So: **no manual save option** — **yes, the profile is stored** on every successful preference update.

## User

you have set a fixed number of user and only one new user option where will it save the current user preferences when the another user will change the current preferernces for the old user

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\static\\app.js","offset":210,"limit":50}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\api.py","limit":40}
```

## Assistant

Yes. **“New shopper” is one shared account, not a blank slot for unlimited people.** A second person using that option **writes on top of the same profile.**

---

## How users actually work

Memory is keyed by **`user_id`**, not by “whoever is at the keyboard.”

Seeded shoppers:

| Dropdown label | `user_id` | Meaning |
|---|---|---|
| New shopper | `fresh` | Empty starter **row** — still only **one** row |
| Riya (pre-filled runner) | `riya` | Separate profile |
| Meera (pre-filled dresses) | `meera` | Separate profile |

The UI has **no “Add user” / login**. The dropdown is just every row already in `user_profiles`. You cannot type a new name in the chat UI.

Chat always sends the **currently selected** id:

```json
{ "user_id": "fresh", "message": "..." }
```

So preferences go to **that row only**.

---

## What happens if “another user” uses New shopper

They are **not** a new person in the database. They are still `fresh`.

Example:

1. You, as **New shopper**, say running shoes below ₹10,000.  
   → Saved on **`fresh`**.
2. Someone else (or you later) also picks **New shopper** and says “I want dresses, budget 2k.”  
   → **Same `fresh` row** is updated: categories merge, budget **overwrites**, chat is the same thread.

Riya’s and Meera’s data are **not** overwritten by that, because those are different `user_id`s. Only **`fresh`** is shared.

**Wipe profile** on New shopper clears `fresh` for everyone who uses that option.

---

## Where it is saved

SQLite table `user_profiles`, one row per `user_id`. There is no extra “current user” draft. The selected dropdown value **is** the save target.

The API *could* create more people (`ensure_user` will INSERT a new id if you `POST /api/chat` with `user_id: "arjun"`), but the **screen never offers that**.

---

## For a real multi-user app

You would add something like: login, or “New shopper” that generates `user_123`, or a name field. Until then, this is a **demo with three (or a few) named rows**, and **New shopper = the shared `fresh` profile.**

## User

what if the 10 new users want to use this site

## Assistant

With the **current UI**, they cannot each have their own private profile. The site is a **demo with a few named shoppers**, not a 10-user product.

---

## What happens today if 10 people “use the site”

All of them open the same page and, by default, pick **New shopper**.

Every chat is stored as `user_id = "fresh"`. So you get **one shared cart of memory**:

- Person 1: running shoes, ₹10,000  
- Person 2: dresses, ₹2,000 → **same `fresh` row** is updated  
- Person 3 sees person 2’s budget, mixed categories, one chat history  

The other 9 do **not** get new rows. Riya / Meera are only extra **demo identities**, still just 2 more shared accounts if people pick those.

So 10 visitors ≠ 10 users in the database.

---

## What “10 users” actually requires

Each person needs a **unique `user_id`**. The backend already supports that: `POST /api/chat` with a new id creates a row (`ensure_user`). The **dropdown never creates ids**.

For 10 people you would add one of these:

| Approach | How it works |
|---|---|
| **Sign-up / login** | After login, `user_id` = their account id. Each has own profile, task, messages. |
| **“Add shopper”** | Button creates `user_04` … `user_13` and adds them to the list. |
| **Name / email on first visit** | “Your name” → `user_id` derived from that (must be unique). |
| **Browser cookie / guest id** | First visit generates `guest_a8f3…` and keeps it in `localStorage`. Each browser = one user (not 10 people on one PC). |

Then 10 users = 10 rows in `user_profiles` (plus 10 tasks and 10 message threads). Catalog stays shared; **memory does not**.

---

## What you would *not* do

Do not give all 10 the **New shopper** option and expect isolation. That option is **one** slot.

**Wipe profile** on `fresh` would wipe that shared demo user for everyone using it.

---

**Short answer:** This project can **store** many users in SQLite; it does **not** let 10 newcomers each get an account. For that you need identity (login, add-user, or a generated guest id) so each person has their own `user_id`.

## User

you can not save all of them at once right

## Assistant

Right. **You cannot save 10 new people at once** with this project as it is.

---

## What “save” can do today

- **One chat request** updates **one** `user_id` (whoever is selected).
- There is **no** “save all users” / “import 10 shoppers” / “create 10 accounts” action.
- **New shopper** is still a **single** row (`fresh`). Ten people using it = ten writes onto **that same row**, not ten saved people.

Riya and Meera are already in the database from **seed**, not from a “save everyone” button.

---

## What the database *could* do (but the site doesn’t)

SQLite can hold many profile rows. The API can create a new row **if** you send a **new** `user_id` on `/api/chat`. The UI never does that in bulk, and never for 10 names at once.

---

So: **not all at once, and not 10 new users at all** from the current screen — only one selected shopper, saved automatically on each of *their* messages.

## User

u mean even if 10 users use this then all of them has to try this with the new shopper id right and is the id being set by you earlier only

## Assistant

Two separate things:

---

## 1. Do all 10 have to use New shopper?

**No — but they also don’t each get their own id.**

On the site they can only pick **ids that already exist** in the dropdown, for example:

- `fresh` → labeled **New shopper**
- `riya` → Riya
- `meera` → Meera

If all 10 pick **New shopper**, they all share **`fresh`**.  
If some pick Riya, they all share **`riya`**.

There is no 11th choice like “User 4 / User 5.” So 10 people still collapse onto **2–3 shared accounts**, not 10.

They are not *required* to use New shopper; that is just the default. It is still **one shared id**.

---

## 2. Who set those ids? Only earlier, by the project?

**Yes.** Those ids were **fixed in code when the catalog was seeded**, not chosen by people on the website.

In `app/seed.py` they are hardcoded:

- `fresh`
- `riya`
- `meera`

The UI never asks “what is your user id?” It only **sends the selected dropdown value**.

Extra names like `demo_brief` only appear if something (e.g. a test script) called the API with a **new** `user_id`. Shoppers on the page cannot invent that.

---

**Short version:** Ids are **preset by the project** (`fresh` / `riya` / `meera`). Ten visitors do not get ten new ids. They reuse those few ids, and **New shopper = `fresh` for everyone who picks it.**

## User

so if we want to make this reliastic then we have have to do just 1 change right like insted of hard coding we will create new users if required using the sign up and use the existing user using the login right

## Assistant

The **idea** is right: stop using hardcoded `fresh` / `riya` / `meera`, and give each person an identity.

It is **not** literally one line of code. It is **one design change** — **who `user_id` is** — plus a small auth layer. The memory tables can stay as they are.

---

## What you already have

`user_profiles`, `shopping_tasks`, and `messages` are already **per `user_id`**.  
Signup/login only has to produce a **unique id** and send it on `/api/chat`. You do not rebuild memory.

---

## What “signup + login” actually adds

| Piece | Why |
|---|---|
| **Sign up** | New row: email/username + password hash + new `user_id` |
| **Log in** | Check password, start a **session** (cookie or token) |
| **Chat API** | Use `user_id` from the session, **not** from a dropdown anyone can switch |
| **UI** | Remove (or hide) the shopper picker; show “Logged in as …” |

Without the session step, signup is useless: anyone could still `POST` `{ "user_id": "someone_else" }` and overwrite their profile.

So: **signup creates users, login selects the existing user**, and **the server** decides the id.

---

## What you can drop

- Hardcoded `USERS` in `seed.py` as the only people who can shop (keep them as **demo accounts** if you want).
- The shared **New shopper** / `fresh` slot as the main path.

---

## Realistic, but still extra (optional)

Passwords, unique email, log out, “forgot password,” one laptop / many people (login required). Guest cookie without signup is a lighter alternative if you do not want accounts yet.

---

**Short version:** Yes — **identity** is the change that makes 10 people realistic. Signup + login is the usual way. Memory already works once each person has their **own** `user_id` that the **server** sets after login. It is one *feature*, not one *edit*.

## User

now i want to understand the implementation for this project so i want to understand the source code in detail so can you please explain me in what order should i study this code so that i will understand the required concepts in detail

### Tool Glob File Search

```
{"targetDirectory":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant","globPattern":"**/*.{py,html,js,json}"}
```

## Assistant

Study it **outside-in by concept**, not alphabetically. Each step adds one idea. Skip `.venv` entirely.

---

## Suggested order (about 10 sittings)

```text
1. models + seed          → what exists in the world
2. config + database      → how the app connects
3. memory.py              → the whole point of Day 3
4. extract.py             → English → slots (rules mode)
5. planner.py             → same tools, no LLM
6. tools.py + prompts     → LangChain contracts
7. loop.py                → LLM tool-calling loop
8. api.py + main.py       → one HTTP request
9. static (html/js)       → what you see
10. data/interactions.json → the brief’s demo script
```

Do **not** start with `loop.py` or LangChain. Memory first, then “who calls memory.”

---

### 1. `app/models.py` then `app/seed.py`

**Concept:** tables vs catalog vs users.

- Four tables: `Product` (not memory), `UserProfile`, `ShoppingTask`, `Message`
- Seed: 26 products, hardcoded `fresh` / `riya` / `meera`

**Ask yourself:** Which columns are long-term vs task vs chat? Why is `shown_product_ids` not on the profile?

---

### 2. `app/config.py` then `app/database.py`

**Concept:** settings + one SQLite session per request.

- `llm_enabled` if `OPENAI_API_KEY` is set  
- `get_db()` open → yield → close  
- `history_limit`, `search_limit`

Short files. Just know every request gets a `Session`.

---

### 3. `app/memory.py` (most important)

**Concept:** read/write the three memories + search.

Read in this order inside the file:

| Function | Concept |
|---|---|
| `ensure_user` | create profile + task if missing |
| `snapshot` | what the sidebar shows |
| `update_profile` | merge lists, **overwrite** budget, invalidate brands |
| `search_products` | profile filters + `id NOT IN shown` + append shown |
| `history` / `add_message` | conversation |
| `reset_session` | New session vs Wipe profile |

**Trace on paper:**  
“running shoes below ₹10,000” → `update_profile` → `search_products` → shown ids.  
“new options” → search only, exclude those ids.

If this file is clear, the rest is wiring.

---

### 4. `app/agent/extract.py`

**Concept:** rules mode does **not** use the LLM to fill slots.

- Category aliases, budget regexes (`below`, `1k-2k`, `budget is now`)
- Why **“above 15000”** does not update the profile
- `has_slots` decides whether `update_profile` runs

**Try:** run the phrases from the brief through `extract_preferences` in your head.

---

### 5. `app/agent/planner.py`

**Concept:** the **same** `memory.py` functions, no LangChain.

Flow: extract → maybe `update_profile` → `search_products` → format a reply + `trace`.

This is the path you used in the UI (**Rules mode**). Understand this **before** the LLM loop. Same tools, simpler control flow.

---

### 6. `app/agent/tools.py` then `app/agent/prompts.py`

**Concept:** the model is not allowed to invent SQL or products.

- `build_tools(db, user_id)` — closures so tools don’t take `user_id` from the model  
- Three tools: `get_memory`, `update_profile`, `search_products`  
- Prompt: overwrite stale budget, only recommend tool results  

Compare each tool body to the function you already read in `memory.py`.

---

### 7. `app/agent/loop.py`

**Concept:** Ledger-style loop, plus **history + snapshot** in the prompt.

- No key → `run_rules_agent`  
- Key → `ChatOpenAI.bind_tools` → invoke → if `tool_calls`, run tool, append `ToolMessage`, repeat  
- History = last N **user/assistant** lines only (no tool traces)

**Ask:** why inject `snapshot` into the system prompt *and* still call `search_products` (live DB)?

---

### 8. `app/api.py` then `app/main.py`

**Concept:** one request = load is inside the agent, write chat after.

- `POST /api/chat` `{ user_id, message }` → `run_agent` → save two messages → `commit` → return `answer` + `memory` + `trace`  
- `GET /api/memory`, `/history`, `POST /api/reset`  
- `main.py` lifespan: `create_all` + `seed_if_empty`

**Ask:** why is `user_id` taken from the client (dropdown), and why that is not real login?

---

### 9. `app/static/index.html` + `app.js` (then CSS if you care)

**Concept:** sidebar = long-term + task; thread = conversation.

- Chips call the same `/api/chat`  
- After each reply, `renderMemory(data.memory)`  
- Switch shopper → `/api/memory` + `/api/history`  
- No “Save profile”; no “Add user”

---

### 10. `data/interactions.json` + `README.md`

**Concept:** what the assignment asked you to prove.

The two-turn brief + budget invalidation + dress range. Map each turn to functions from step 3.

---

## How to study each file (same method)

1. Read the **docstring / first comment**.  
2. List **inputs and outputs** (what table changes).  
3. Walk **one real sentence** through it.  
4. Only then read the next file.

Example sentence to reuse everywhere:

> “I normally buy running shoes below ₹10,000.”  
> then “Show me some new options.”

---

## What *not* to study yet

- `.venv/`  
- LangChain/LangGraph source  
- Colour-as-global-preference / signup — those are design notes, not required to read the current code  

---

## One-page map after you’re done

```text
Browser  →  api.chat(user_id, message)
                → loop.run_agent
                     → extract + planner    (no key)
                     → tools + ChatOpenAI   (key)
                → memory.update_profile / search_products / add_message
                → SQLite
         ←  answer + memory sidebar + tool trace
```

Start tomorrow at **`models.py` → `memory.py`**. Everything else is “who calls `memory`.”

## User

what you have built is ai agent right and you have used the langchain for all the purpose

## Assistant

It **is an agent** in the usual course sense: it **chooses tools** (`update_profile`, `search_products`, `get_memory`) instead of only writing a paragraph. It is **not** “LangChain for everything.”

---

## Is it an AI agent?

**LLM mode (API key set):** yes.  
`ChatOpenAI.bind_tools` → model may call tools → Python runs them → results go back → final answer. That is a **tool-calling agent**.

**Rules mode (no key — what you used in the UI):** it **behaves like** the same agent (same tools, same SQLite), but **you** (regex in `extract.py` + `planner.py`) decide the tool calls. No model in the loop. So: **agent-shaped app**, not a live LLM agent.

---

## Was LangChain used for all of it?

**No.** LangChain is only the LLM tool layer.

| Part | What actually runs it |
|---|---|
| HTTP + UI | FastAPI, HTML/JS |
| Database | SQLAlchemy + SQLite |
| Memory + catalog search | `memory.py` (plain Python) |
| “below ₹10,000” parsing | `extract.py` (regex) |
| Demo without a key | `planner.py` (calls `memory.py` directly) |
| LLM tools + chat messages | **LangChain** (`StructuredTool`, `ChatOpenAI`, `HumanMessage` / `ToolMessage`) |

So LangChain does **not** store memory, seed products, or draw the sidebar. Those are independent. The prompt asked to use LangChain **where it fits**; that is the `tools.py` + `loop.py` path.

---

**Short version:** Shopping assistant + **tools + memory** = agent-style system. LangChain = **optional brain** when a key is set. Without a key, same tools, no LangChain in the request.

## User

does it have llm based and also rule based approach as it is running even if i don't provide any key

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\config.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\agent\\loop.py","offset":85,"limit":15}
```

## Assistant

Yes. That is why it works with **no API key**.

---

## Two modes, same tools and same database

| Mode | When | Who decides the tools |
|---|---|---|
| **Rules** | `OPENAI_API_KEY` is empty | `extract.py` + `planner.py` (regex) |
| **LLM** | key is set in `.env` | LangChain `ChatOpenAI` + tools |

Switch is in `run_agent`:

```89:93:app/agent/loop.py
def run_agent(message: str, db: Session, user_id: str) -> dict[str, Any]:
    store.ensure_user(db, user_id)
    if settings.llm_enabled:
        return run_llm_agent(message, db, user_id)
    return run_rules_agent(message, db, user_id)
```

`llm_enabled` is just “is the key non-empty?”

The UI badge **Rules mode** vs **LLM · gpt-4o-mini** comes from `GET /api/meta`.

---

## What stays the same

Both modes call **`update_profile` / `search_products` / `get_memory`** on SQLite. Memory, catalog, and the sidebar do not depend on a key.

---

## What changes

- **Rules:** only phrases the regex knows (e.g. “below ₹10,000”, “budget is now ₹15,000”). “Above 15000” is ignored.  
- **LLM:** can interpret messier English, but still must use tools and not invent products.

Same pattern as your Ledger project: rules so it runs locally, LLM when you add a key.

## User

how is the messages being used in this project and do you send all the msg for the perticular user everytime

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\config.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\memory.py","offset":305,"limit":50}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\agent\\loop.py"}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\api.py","limit":50}
```

### Tool Read File V2

```
{"path":"D:\\GA\\PythonLearning\\API\\Stylumia\\Day3_Memory\\Personal_shopping_assistant\\app\\agent\\planner.py","limit":50}
```

## Assistant

Messages are **stored for that shopper**, but they are **not all sent to the model on every request**. And in **Rules mode** they are not sent to an LLM at all.

---

## What gets saved

After each `/api/chat`, two rows go into `messages` for that `user_id`:

- `role=user` — what they typed  
- `role=assistant` — the final reply  

**Not saved:** tool calls, tool JSON, traces. Only the visible chat text.

That is **conversation memory**. It is per `user_id` (`fresh` vs `riya` are separate threads).

---

## Do you send all of them every time?

**No.** Load is capped at **`history_limit = 20`** (last 20 rows, then reversed to chronological order).

```305:317:app/memory.py
def history(db: Session, user_id: str, limit: int | None = None) -> list[dict[str, str]]:
    ...
    cap = limit or settings.history_limit
    ...
    .order_by(Message.id.desc())
    .limit(cap)
```

Older turns **stay in SQLite** but are **not** loaded after you pass 20.

The UI `/api/history` uses the **same** helper, so a refresh also shows at most the last 20 bubbles, even if the table has more.

---

## How those 20 are used — depends on mode

**LLM mode (API key set)**  
Each request builds:

1. System prompt (includes **profile + task snapshot**, not the full chat)  
2. Last ≤20 user/assistant messages  
3. **This turn’s** new sentence  

That list is what `ChatOpenAI.invoke` sees. During the tool loop, extra `ToolMessage`s exist **only in memory for this request**; they are not written to `messages`.

So the model gets **recent chat + current line**, not the entire lifetime of the user.

**Rules mode (no key — typical for you)**  
`planner.py` uses **only the current sentence** (`extract_preferences`) plus **profile/task** from SQLite.  
It does **not** feed past chat into a model. History is still **saved** so the thread can reload, and so LLM mode would have context later if you add a key.

“Show me some new options” works in rules mode because of **profile + shown ids**, not because the first sentence is re-sent as chat.

---

## One request, picture

```text
DB messages for this user_id  (may be 50 rows)
        │
        ▼
   last 20 only  ──►  LLM  (if key)
   ignored by rules extractor

New user + assistant lines  ──►  INSERT (always)
```

---

**Short version:** Chat is stored per user. You do **not** send every historical message every time — **up to 20** go to the LLM. Rules mode does not send chat history to an LLM; it uses the new message plus long-term/task tables."""
