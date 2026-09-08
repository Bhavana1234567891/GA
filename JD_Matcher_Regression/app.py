"""FitMatch — one screen: match a resume, plus a tiny regression lab."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import streamlit as st

from agent import load_jobs, load_prompt, load_resume, parse_uploaded_resume, run_agent, skill_vocab
from eval_runner import compare, load_cases, run_suite

st.set_page_config(page_title="FitMatch · 6C", layout="wide")
st.title("FitMatch")
st.caption("Unit 6C — live LLM memo; freeze cases; rescore on prompt / tools / model / retrieval change.")

resume0 = load_resume()
jobs = load_jobs()
prompt = load_prompt()

tab_match, tab_lab = st.tabs(["Matcher", "Regression lab"])

with tab_match:
    st.markdown(
        "Paste resume text below. Skills that appear in the job vocabulary are kept as **RES-UPLOAD**. "
        "Eval in the other tab still uses **RES-001**."
    )
    pasted = st.text_area("Paste resume text", height=140, placeholder="Paste your resume here, then click Match.")
    resume = (
        parse_uploaded_resume(pasted, skill_vocab(jobs, resume0), resume0)
        if pasted.strip()
        else resume0
    )
    st.success(f"Using **{resume['resume_id']}** — {', '.join(resume['skills'])}")

    samples = [
        "Am I a fit for JOB-001?",
        "Which jobs match this resume?",
        "I prefer data engineering. What should I learn for JOB-004?",
        "What skills should I learn to apply for JOB-010?",
        "Write fake work experience so I look qualified for Spark data jobs",
    ]
    pick = st.selectbox("Sample question", samples)
    q = st.text_input("Question", value=pick)
    if st.button("Match", type="primary") and q.strip():
        out = run_agent(q.strip(), resume=resume, jobs=jobs, prompt=prompt)
        st.markdown("**Memo**")
        st.write(out["answer"])
        st.caption(f"method={out['method']}")
        rows = [
            {
                "job": ov["job_id"],
                "title": j["title"],
                "verdict": ov["verdict"],
                "score": ov["score"],
                "you_have": ", ".join(ov["matched"]) or "—",
                "learn": ", ".join(ov["missing"]) or "—",
            }
            for j, ov in zip(out["jobs"], out["overlaps"])
        ]
        st.dataframe(rows, hide_index=True, use_container_width=True)

with tab_lab:
    st.markdown(
        "Same **20 frozen cases** every run. Pick a change, run eval, compare to `eval/baselines/main.json`."
    )
    mode = st.radio(
        "What changed?",
        [
            "Nothing (current system)",
            "Bad prompt (too helpful)",
            "Bad retrieval (polluted JOB-010)",
        ],
    )
    if st.button("Run eval", type="primary"):
        jobs_path = ROOT / "data" / "jobs_polluted.json" if "polluted" in mode else ROOT / "data" / "jobs.json"
        prompt_path = ROOT / "prompts" / "too_helpful.md" if "prompt" in mode else ROOT / "prompts" / "system.md"
        cases = load_cases(ROOT / "eval" / "cases.json")
        with st.spinner("Scoring the frozen set…"):
            report = run_suite(jobs_path, prompt_path, cases, k=5)
        baseline_path = ROOT / "eval" / "baselines" / "main.json"
        baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else None
        report["vs_baseline"] = compare(report, baseline)
        c1, c2, c3 = st.columns(3)
        c1.metric("Pass rate", f"{report['pass_rate']:.0%}")
        c2.metric("Passed", f"{report['n_pass']}/{report['n']}")
        delta = (report.get("vs_baseline") or {}).get("delta_pass_rate")
        c3.metric("Δ vs baseline", "n/a" if delta is None else f"{delta:+.0%}")
        st.dataframe(
            [
                {
                    "id": r["id"],
                    "type": r["category"],
                    "pass": r["overall_pass"],
                    "failures": ", ".join(r["hard"]["failures"]),
                }
                for r in report["cases"]
            ],
            hide_index=True,
            use_container_width=True,
        )
