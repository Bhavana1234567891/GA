# YouTube RAG Chatbot

Ask questions about any YouTube video. The bot answers only from that video’s transcript, cites timestamps, and can jump the player to the cited moment.

Built with **LangChain (LCEL)**, **ChromaDB**, **FastAPI**, and a **Chrome / Edge extension**.

---

## What it does

1. Reads the video ID from the YouTube tab (`watch?v=...`).
2. Fetches captions, splits them into **30-second chunks**, and stores vectors in ChromaDB.
3. When you ask a question, it retrieves the best chunks and generates an answer with citations like `[1] [4:18 - 4:49]`.
4. Clicking a timestamp seeks the YouTube player to that time.

The extension is only the UI. All RAG logic runs on the FastAPI backend.

---

## Architecture (simple)

```
YouTube tab
    │
Chrome / Edge extension (popup + content script)
    │  POST /index   POST /chat
    ▼
FastAPI  (backend/app.py)
    │
    ├─ ingest   → transcript → 30s chunks + timestamps
    ├─ store    → ChromaDB (vectors) + BM25 (keywords)
    ├─ retrieve → rewrite → hybrid search → rerank → compress
    ├─ generate → LCEL prompt | LLM | parser
    └─ guards   → input safety + output grounding (LLM-as-judge)
```

**Paid API used:** OpenAI (`gpt-4o-mini` for chat / routing / guards).  
**Local / free:** embeddings (`all-MiniLM-L6-v2`), reranker (`ms-marco-MiniLM-L-6-v2`), ChromaDB, BM25.

---

## Project layout

```
Youtube_chatbot/
├── .env                          # OPENAI_API_KEY (do not commit)
├── requirements.txt
├── chroma_db/                    # created after first index
├── backend/
│   ├── app.py                    # FastAPI: /health, /index, /chat
│   ├── indexing/ingest.py        # YouTube transcript + 30s chunking
│   ├── vectorstore/store.py      # ChromaDB + BM25
│   ├── retrieval/
│   │   ├── query_transform.py    # rewrite, multi-query, intent router
│   │   └── retriever.py          # hybrid + RRF + rerank + compress
│   ├── chain/
│   │   ├── prompts.py            # all LLM prompts
│   │   ├── memory.py             # last 5 turns per session
│   │   └── rag_chain.py          # QA / summarize / timestamp dispatch
│   ├── guardrails/guards.py      # SAFE / GROUNDED checks
│   └── evaluation/eval.py        # RAGAS faithfulness + answer_relevancy
└── chrome_extension/
    ├── manifest.json
    ├── popup.html / popup.js     # chat UI
    ├── background.js             # reads video_id from the tab
    └── content.js                # seeks <video> on timestamp click
```

---

## Setup

### 1. Python

Use Python 3.10+ (the project was run on 3.14).

```powershell
cd D:\GA\PythonLearning\API\Stylumia\Youtube_chatbot
pip install -r requirements.txt
```

First run downloads HuggingFace models (~few hundred MB). That is expected.

### 2. Environment

Create / edit `.env` in the project root:

```
OPENAI_API_KEY=sk-your-key-here

# Optional — LangSmith free-tier tracing
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=your-langsmith-key
# LANGCHAIN_PROJECT=youtube-chatbot
```

### 3. Start the backend

```powershell
cd D:\GA\PythonLearning\API\Stylumia\Youtube_chatbot
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8002
```

Check: [http://127.0.0.1:8002/health](http://127.0.0.1:8002/health) → `{"status":"ok"}`  
Interactive docs: [http://127.0.0.1:8002/docs](http://127.0.0.1:8002/docs)

The extension is hardcoded to **port 8002** in `chrome_extension/popup.js`. If you change the port, update that file too.

---

## Install the browser extension

Works in **Chrome** and **Edge** (Manifest V3 popup).

1. Open `chrome://extensions` or `edge://extensions`.
2. Turn on **Developer mode**.
3. Click **Load unpacked**.
4. Select the folder: `chrome_extension` (this repo, not the parent).
5. Pin **YouTube RAG Chatbot** from the puzzle-piece menu.

### Use it

1. Keep the FastAPI server running.
2. Open a YouTube watch page, for example:  
   `https://www.youtube.com/watch?v=LPZh9BOjkQs`
3. Click the extension icon.
4. Wait until status is **Ready** (first time indexes the transcript).
5. Ask questions. Expand sources and click timestamps to jump in the video.

If the popup says “No YouTube video detected”, you are not on a `youtube.com/watch?v=...` page.

---

## API (for Postman / curl / docs)

| Method | Path | Body | Purpose |
|--------|------|------|---------|
| GET | `/health` | — | Liveness |
| POST | `/index` | `{ "video_id": "LPZh9BOjkQs", "title": "" }` | Ingest + embed |
| POST | `/chat` | `{ "video_id": "...", "question": "...", "session_id": "s1" }` | Ask |

`session_id` keeps short-term chat memory (last 5 turns).

---

## How a question is answered

Not every question uses the same path. An LLM **router** picks one:

| Intent | When | What runs |
|--------|------|-----------|
| `qa` | Normal question | Hybrid retrieve top chunks → QA prompt with citations |
| `summarize` | “Summarize this video” | **All** chunks, summarize prompt (not top-k) |
| `timestamp` | “Find the part about GPUs” | Retrieve → timestamp prompt |
| `refuse` | Unsafe / injection | Fixed refusal, no retrieval |

**QA retrieval pipeline**

1. Rewrite follow-ups using chat history (`what about that?` → standalone query).
2. Multi-query: LLM writes extra phrasings of the question.
3. Hybrid search: **MMR vectors** (Chroma) + **BM25** keywords.
4. Reciprocal Rank Fusion merges ranked lists.
5. Local cross-encoder reranks → top 5.
6. LLM compression drops filler if needed; token budget keeps most relevant first.
7. Prompt + `gpt-4o-mini` + citation format.
8. Second LLM checks if the answer is **grounded** in those chunks.

Metadata on each chunk (`video_id`, `t_start`, `t_end`, display times) is attached **in Python during ingest**, not by the LLM. YouTube captions already include `start` and `duration`.

---

## Evaluation (RAGAS)

Scores **faithfulness** and **answer_relevancy** only (no ground-truth answers required).

Index a video first, then:

```powershell
cd D:\GA\PythonLearning\API\Stylumia\Youtube_chatbot
python -m backend.evaluation.eval --video_id LPZh9BOjkQs --output results.json
```

This calls the live chain for a fixed question list, then RAGAS. It uses your OpenAI key (LLM-as-judge) and takes a few minutes.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `{"detail":"Not Found"}` on `/` | Root has no page. Use `/health` or `/docs`. |
| Extension: Server offline | Start uvicorn on **8002**. |
| Extension: No video detected | Open a watch URL with `?v=`. |
| Index 400 / no captions | Video has transcripts disabled, or try another video. |
| Port already in use | Kill the old process or change port **and** `API_BASE` in `popup.js`. |
| First `/index` is slow | Embedding model download + embed. Later calls for the same `video_id` skip re-index. |
| Chat is slow | Multi-query, rerank, compression, and grounding each call models. First rerank also loads the cross-encoder. |

---

## Notes for new developers

- Start reading `backend/app.py`, then `backend/chain/rag_chain.py`, then `backend/retrieval/retriever.py`.
- Do not put API keys in the extension. Keys stay in `.env` on the server.
- `sidepanel.html` / `sidepanel.js` are leftover from an earlier Chrome-only side panel. The live UI is the **popup**.
- Grounding checks are **LLM classifiers**, not regex. Retrieval quality is hybrid search, not the grounding judge.

---

## License

Internal / learning project.
