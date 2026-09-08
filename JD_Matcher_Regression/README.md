# FitMatch — Unit 6C Agent Regression Framework

Small resume ↔ job matcher used to **teach regression**, not to ship an ATS.

The agent is a demo. The assignment is: freeze questions, rescore them when something changes, put that run in CI.

```
question → BM25 jobs + named JOB-id
         → tools get_jd / skill_overlap
         → LLM memo (API key required)
         → eval/cases.json
         → report vs last baseline
         → GitHub Actions
```

## What 6C asks vs this folder

| Requirement | Where |
|---|---|
| Maintain a regression dataset | [`eval/cases.json`](eval/cases.json) — normal / edge / refusal |
| Auto-run on **prompt** change | CI path `JD_Matcher_Regression/prompts/**` |
| Auto-run on **tool** change | CI path `JD_Matcher_Regression/agent.py` |
| Auto-run on **model** change | CI path `JD_Matcher_Regression/model.json` |
| Auto-run on **retrieval** change | CI path `JD_Matcher_Regression/data/**` |
| Eval in CI/CD | [`.github/workflows/jd-matcher-regression.yml`](../.github/workflows/jd-matcher-regression.yml) (repo root; GitHub ignores workflows inside this folder) |

CI prints pass rate vs [`eval/baselines/main.json`](eval/baselines/main.json). A human still decides merge. The job **fails** if a **refusal** case leaks fake-resume help.

## Run locally

```bash
cd JD_Matcher_Regression
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy `.env.example` to `.env` and set `OPENAI_API_KEY` (or `GROQ_API_KEY`).
Model name lives in `model.json` (default `gpt-4o-mini`).

```bash
python eval_runner.py
python -m streamlit run app.py
```

There is **no stub memo**. Tools still run in Python; the written answer always comes from the LLM.

Prove the four 6C triggers:

```bash
python eval_runner.py
python eval_runner.py --too-helpful
python eval_runner.py --polluted
```

`--too-helpful` swaps [`prompts/too_helpful.md`](prompts/too_helpful.md) (prompt change).  
`--polluted` swaps [`data/jobs_polluted.json`](data/jobs_polluted.json) — **JOB-010** `must_have` is no longer Python/PyTorch (retrieval change).  
Edit `get_jd` / `skill_overlap` in [`agent.py`](agent.py) (tool change).  
Edit [`model.json`](model.json) (model change).

## Agent (keep this mental model)

1. **LLM** — OpenAI (or Groq) with an API key; it must call tools.
2. **Tools** — `search_jobs`, `get_jd`, `skill_overlap` run in Python only when the model calls them.
3. **Memo** — written by the LLM from tool JSON. There is no template/stub answer.

Default resume is [`data/resume.json`](data/resume.json) (**RES-001**). The UI can paste text; **eval always uses RES-001** so scores do not jump.

## Dataset

About 20 cases you own: fit questions, “skills to learn for another role”, unknown id, and refusals (“write fake work experience”). Add a case when you find a new bug.

## Interview one-liner

*We freeze ~20 match/learn/refuse questions on one resume and 12 JDs. GitHub Actions re-scores every prompt, tool, model, or index change so a “more helpful” prompt cannot silently start fabricating experience.*
