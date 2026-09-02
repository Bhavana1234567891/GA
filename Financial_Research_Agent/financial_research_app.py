import json

import streamlit as st

from grounded_agent import ask, llm_ready
from report_tools import get_store, list_filings

st.set_page_config(
    page_title="Financial research agent",
    page_icon=":material/account_balance:",
    layout="centered",
)

SUGGESTIONS = {
    ":green[:material/check_circle:] Sales in 2018": "What was Nestlé India's sales in 2018?",
    ":blue[:material/recycling:] Plastic waste": "Tell me about the plastic waste management that was introduced.",
    ":red[:material/cancel:] Sales in 2025": "What was Nestlé India's revenue in 2025?",
    ":orange[:material/domain:] Tesla revenue": "What was Tesla's revenue in 2018?",
    ":violet[:material/block:] Buy the stock?": "Should I buy Nestlé India stock?",
}


def _init_state() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("memory", None)


def _filings() -> list[dict]:
    try:
        return json.loads(list_filings.invoke({}))
    except Exception as exc:  # noqa: BLE001 — show ingest status in the sidebar
        return [{"error": str(exc)}]


def _render_result(result: dict) -> None:
    if result.get("grounded"):
        st.badge("Grounded", icon=":material/verified:", color="green")
        st.write(result["answer"])
        src = result.get("source") or ""
        page = result.get("page")
        if src:
            st.caption(f"Source: `{src}`, page {page}")
        span = result.get("evidence_span") or ""
        if span:
            st.markdown("**Quoted span**")
            st.code(span, language=None)
    else:
        st.badge("Refused", icon=":material/gpp_maybe:", color="orange")
        st.write(result.get("answer") or "Unsupported.")
        reason = result.get("refuse_reason") or ""
        if reason:
            st.caption(reason)

    followup = result.get("followup") or {}
    if followup:
        with st.expander("Follow-up rewrite"):
            reused = followup.get("reused_evidence")
            st.caption(
                "LLM rewrite of the question. Chunks reused."
                if reused
                else "LLM rewrite of the question. New search."
            )
            st.json(
                {
                    "is_followup": followup.get("is_followup"),
                    "same_evidence": followup.get("same_evidence"),
                    "intent_changed": followup.get("intent_changed"),
                    "reused_evidence": reused,
                    "rewrite": followup.get("rewrite"),
                }
            )

    trace = result.get("trace") or []
    if trace:
        with st.expander("Tool calls"):
            for step in trace:
                st.markdown(f"`{step.get('tool')}`")
                st.json(step.get("args") or {})

    evidence = result.get("evidence") or []
    if evidence:
        with st.expander("Retrieved evidence"):
            for hit in evidence:
                st.markdown(
                    f"`{hit.get('source')}` · page {hit.get('page')} · {hit.get('company')}"
                )
                st.text((hit.get("text") or "")[:600])


_init_state()

with st.sidebar:
    st.header("Indexed filings")
    try:
        store = get_store()
        st.metric("Chunks", store._collection.count())
    except Exception as exc:  # noqa: BLE001
        st.warning(str(exc))
    for row in _filings():
        if "error" in row:
            st.error(row["error"])
        else:
            st.markdown(
                f"**{row.get('company') or row.get('source')}**  \n"
                f"{row.get('fiscal_year') or '—'} · `{row.get('source')}`"
            )
    st.divider()
    mem = st.session_state.get("memory") or {}
    if mem.get("company") or mem.get("topic"):
        st.caption(
            f"Memory: {mem.get('company') or '—'} · "
            f"{mem.get('fiscal_year') or '—'} · {mem.get('topic') or '—'}"
        )
        with st.expander("Memory slots"):
            st.json(
                {
                    "company": mem.get("company"),
                    "fiscal_year": mem.get("fiscal_year"),
                    "topic": mem.get("topic"),
                    "source": mem.get("source"),
                    "page": mem.get("page"),
                    "summary": mem.get("summary"),
                    "evidence_pages": [
                        h.get("page")
                        for h in (mem.get("last_evidence") or [])
                        if isinstance(h, dict)
                    ],
                }
            )
    else:
        st.caption("Memory: empty (next question starts a new topic).")
    if llm_ready():
        st.caption("Chat LLM ready. Embeddings are local MiniLM.")
    else:
        st.warning("Add OPENAI_API_KEY to `.env` for answers. Retrieval still works after ingest.")
    if st.button("Clear chat", icon=":material/delete:"):
        st.session_state.messages = []
        st.session_state.memory = None
        st.rerun()

st.title("Financial research agent")
st.caption(
    "Answers come only from indexed annual reports. Follow-ups use slot memory "
    "(not the full chat). Unsupported questions are refused."
)

typed = st.chat_input("Ask about the indexed annual report", submit_mode="disable")

prompt = typed
if not st.session_state.messages:
    selected = st.pills(
        "Try asking:",
        list(SUGGESTIONS.keys()),
        label_visibility="collapsed",
    )
    if selected and not prompt:
        prompt = SUGGESTIONS[selected]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and isinstance(msg.get("result"), dict):
            _render_result(msg["result"])
        else:
            st.write(msg["content"])

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.status(":shimmer[Retrieving evidence]", type="compact") as status:
            with st.status("Calling report tools", type="step"):
                st.write("search_reports · get_page · list_filings")
            result = ask(prompt, memory=st.session_state.get("memory"))
            status.update(label="Done", state="complete")
        _render_result(result)

    st.session_state.memory = result.get("memory")
    st.session_state.messages.append(
        {"role": "assistant", "content": result.get("answer") or "", "result": result}
    )
