"""FitMatch: the LLM calls tools; Python only runs those tools. No stub memo."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

JOB_RE = re.compile(r"JOB-\d{3}", re.I)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_resume(path: Path | None = None) -> dict:
    return load_json(path or ROOT / "data" / "resume.json")


def load_jobs(path: Path | None = None) -> list[dict]:
    return load_json(path or ROOT / "data" / "jobs.json")


def load_prompt(path: Path | None = None) -> str:
    return (path or ROOT / "prompts" / "system.md").read_text(encoding="utf-8")


def load_model_config() -> dict:
    p = ROOT / "model.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"provider": "openai", "model": "gpt-4o-mini"}


def job_text(job: dict) -> str:
    must = " ".join(job.get("must_have") or [])
    nice = " ".join(job.get("nice_to_have") or [])
    return f"{job['job_id']} {job['title']} {job['location']} {must} {nice} {job.get('blurb', '')}"


def _tok(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def get_jd(jobs: list[dict], job_id: str) -> dict | None:
    want = (job_id or "").upper()
    for j in jobs:
        if j["job_id"].upper() == want:
            return j
    return None


def skill_overlap(resume: dict, job: dict) -> dict:
    have = {s.lower(): s for s in resume.get("skills") or []}
    must = job.get("must_have") or []
    matched, missing = [], []
    for s in must:
        if s.lower() in have:
            matched.append(s)
        else:
            missing.append(s)
    extras = [s for s in resume.get("skills") or [] if s.lower() not in {m.lower() for m in must}]
    n = len(must) or 1
    score = round(len(matched) / n, 4)
    if score >= 0.67:
        verdict = "strong fit"
    elif score >= 0.34:
        verdict = "weak fit"
    else:
        verdict = "not a fit"
    return {
        "resume_id": resume.get("resume_id"),
        "job_id": job["job_id"],
        "matched": matched,
        "missing": missing,
        "extras": extras,
        "score": score,
        "verdict": verdict,
    }


def retrieve(jobs: list[dict], question: str, k: int = 5) -> list[dict]:
    named = [m.upper() for m in JOB_RE.findall(question or "")]
    picked: list[dict] = []
    seen: set[str] = set()
    for jid in named:
        row = get_jd(jobs, jid)
        if row and row["job_id"] not in seen:
            picked.append(row)
            seen.add(row["job_id"])
    corpus = [j for j in jobs if j["job_id"] not in seen]
    if corpus and (question or "").strip():
        bm25 = BM25Okapi([_tok(job_text(j)) for j in corpus])
        scores = bm25.get_scores(_tok(question))
        ranked = [j for _, j in sorted(zip(scores, corpus), key=lambda x: -x[0])]
        for j in ranked:
            if j["job_id"] not in seen:
                picked.append(j)
                seen.add(j["job_id"])
            if len(picked) >= k:
                break
    elif not picked:
        picked = jobs[:k]
    return picked[:k]


def get_llm():
    cfg = load_model_config()
    provider = (cfg.get("provider") or "openai").lower()
    model = os.environ.get("LLM_MODEL") or cfg.get("model") or "gpt-4o-mini"
    openai_key = os.environ.get("OPENAI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")
    if not openai_key and not groq_key:
        raise RuntimeError(
            "FitMatch requires a live LLM. Set OPENAI_API_KEY or GROQ_API_KEY in .env. "
            "There is no rule-based answer."
        )
    if provider == "groq" and groq_key:
        from langchain_groq import ChatGroq

        name = model if model != "gpt-4o-mini" else "llama-3.1-8b-instant"
        return ChatGroq(model=name, temperature=0)
    if openai_key:
        from langchain_openai import ChatOpenAI

        name = model if not str(model).startswith("llama") else "gpt-4o-mini"
        return ChatOpenAI(model=name, temperature=0)
    from langchain_groq import ChatGroq

    return ChatGroq(model="llama-3.1-8b-instant", temperature=0)


def parse_uploaded_resume(text: str, vocab: list[str], base: dict) -> dict:
    blob = (text or "").lower()
    found = []
    for s in vocab:
        if s.lower() in blob and s not in found:
            found.append(s)
    row = dict(base)
    row["resume_id"] = "RES-UPLOAD"
    row["name"] = "Uploaded resume"
    if found:
        row["skills"] = found
    row["summary"] = "Skills extracted from pasted/uploaded text using the job skill vocabulary."
    return row


def skill_vocab(jobs: list[dict], resume: dict) -> list[str]:
    names: list[str] = []
    for j in jobs:
        for s in (j.get("must_have") or []) + (j.get("nice_to_have") or []):
            if s not in names:
                names.append(s)
    for s in resume.get("skills") or []:
        if s not in names:
            names.append(s)
    return names


def _slim_job(job: dict) -> dict:
    return {
        "job_id": job["job_id"],
        "title": job["title"],
        "location": job.get("location"),
        "must_have": job.get("must_have"),
        "nice_to_have": job.get("nice_to_have"),
        "blurb": job.get("blurb"),
    }


def run_agent(
    question: str,
    resume: dict | None = None,
    jobs: list[dict] | None = None,
    prompt: str | None = None,
    k: int = 5,
) -> dict:
    """LLM chooses tools. Python never writes the user-facing memo."""
    resume = resume or load_resume()
    jobs = jobs if jobs is not None else load_jobs()
    prompt = prompt if prompt is not None else load_prompt()
    hits: list[dict] = []
    overlaps: list[dict] = []

    def remember(job: dict) -> None:
        if job["job_id"] in {h["job_id"] for h in hits}:
            return
        hits.append(job)
        overlaps.append(skill_overlap(resume, job))

    def tool_get_resume() -> str:
        return json.dumps(
            {
                "resume_id": resume.get("resume_id"),
                "name": resume.get("name"),
                "years": resume.get("years"),
                "location": resume.get("location"),
                "skills": resume.get("skills"),
                "summary": resume.get("summary"),
            }
        )

    def tool_search_jobs(query: str) -> str:
        found = retrieve(jobs, query, k=k)
        for row in found:
            remember(row)
        return json.dumps([_slim_job(j) for j in found])

    def tool_get_jd(job_id: str) -> str:
        row = get_jd(jobs, job_id)
        if not row:
            return json.dumps({"error": "cannot find", "job_id": job_id})
        remember(row)
        return json.dumps(_slim_job(row))

    def tool_skill_overlap(job_id: str) -> str:
        row = get_jd(jobs, job_id)
        if not row:
            return json.dumps({"error": "cannot find", "job_id": job_id})
        remember(row)
        ov = skill_overlap(resume, row)
        return json.dumps(ov)

    tools = [
        StructuredTool.from_function(
            func=tool_get_resume,
            name="get_resume",
            description="Return the resume already loaded in this session (id and skills). Do not ask the user for a resume.",
        ),
        StructuredTool.from_function(
            func=tool_search_jobs,
            name="search_jobs",
            description="Retrieve matching JDs with BM25. Pass the user question or role keywords.",
        ),
        StructuredTool.from_function(
            func=tool_get_jd,
            name="get_jd",
            description="Load one job by id, e.g. JOB-001. Returns cannot find if the id is missing.",
        ),
        StructuredTool.from_function(
            func=tool_skill_overlap,
            name="skill_overlap",
            description="Compare the loaded session resume to one job_id. Returns matched, missing, verdict.",
        ),
    ]
    llm = get_llm().bind_tools(tools)
    by_name = {t.name: t for t in tools}
    user_msg = (
        f"Loaded resume id: {resume.get('resume_id')}. "
        f"Skills: {', '.join(resume.get('skills') or [])}. "
        "Do not ask for a resume; call get_resume or skill_overlap.\n\n"
        f"Question: {question}"
    )
    messages = [SystemMessage(content=prompt), HumanMessage(content=user_msg)]
    answer = ""
    for _ in range(8):
        ai = llm.invoke(messages)
        messages.append(ai)
        calls = getattr(ai, "tool_calls", None) or []
        if not calls:
            answer = (ai.content or "").strip() if isinstance(ai.content, str) else str(ai.content or "")
            break
        for tc in calls:
            name = tc.get("name")
            args = tc.get("args") or {}
            tool = by_name[name]
            result = tool.invoke(args)
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
    else:
        raise RuntimeError("LLM kept calling tools and never wrote a final memo.")

    if not answer:
        raise RuntimeError("LLM returned an empty memo.")

    return {
        "answer": answer,
        "jobs": hits,
        "overlaps": overlaps,
        "method": "llm",
        "resume_id": resume.get("resume_id"),
    }
