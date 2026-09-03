"""Streamlit demo for 5A: pick a city, pick how the API fails, watch the client cope."""

from __future__ import annotations

import streamlit as st

from mock_api import CITIES, FAIL_MODES
from reliable_client import BREAKER_COOLDOWN, BREAKER_THRESHOLD, breaker, fetch_weather

st.set_page_config(
    page_title="Unreliable weather API",
    page_icon=":material/cloud:",
    layout="centered",
)

FAIL_HELP = {
    "ok": "200 + valid JSON. Happy path.",
    "timeout": "Server sleeps 30s. Client read timeout is 8s — it should leave first.",
    "500": "Always HTTP 500. Client retries, then fails cleanly.",
    "429": "Always HTTP 429. Same retries, waits grow (backoff).",
    "invalid": "200 but missing temp_c. Rejected, NOT retried.",
    "500_then_ok": "500, 500, then 200. Best demo that retry works.",
}


def _init() -> None:
    st.session_state.setdefault("result", None)


_init()

st.title("Unreliable weather API")
st.caption(
    "The mock API is the flaky vendor. The client is the reliable part: "
    "timeout, retry, backoff, circuit breaker, graceful error."
)

with st.sidebar:
    st.subheader("Chaos switch")
    fail = st.selectbox(
        "Fail mode",
        FAIL_MODES,
        index=0,
        help="Sent as ?fail= to the mock. The client does not know the mode in advance.",
    )
    st.info(FAIL_HELP[fail])
    st.metric("Breaker", breaker.state())
    st.caption(f"Opens after {BREAKER_THRESHOLD} failures. Cooldown {int(BREAKER_COOLDOWN)}s.")
    if st.button("Reset breaker", type="secondary"):
        breaker.reset()
        st.rerun()
    st.divider()
    st.caption("Start the mock first: `python mock_api.py` (port 8765).")
    st.caption("Cities: " + ", ".join(sorted({v['city'] for v in CITIES.values()})))

city = st.text_input("City", value="Paris")
clicked = st.button("Get weather", type="primary")

if clicked:
    if not city.strip():
        st.warning("Enter a city.")
    else:
        with st.spinner("Calling weather…"):
            st.session_state.result = fetch_weather(city.strip(), fail=fail)

result = st.session_state.result
if result is None:
    st.info("Pick a fail mode in the sidebar, then Get weather. Watch **Trace**.")
    st.stop()

if result["ok"]:
    w = result["weather"]
    st.badge("OK", icon=":material/check_circle:", color="green")
    st.metric("Temperature", f"{w['temp_c']} °C", delta=w["condition"])
    st.write(f"**{w['city']}** — {w['condition']}")
else:
    st.badge("Graceful failure", icon=":material/error:", color="orange")
    st.write(result["error"])

c1, c2 = st.columns(2)
c1.metric("Breaker after this call", result["breaker"])
c2.metric("Failure count", result["failures"])

trace = result.get("trace") or []
st.subheader("Trace")
st.caption("This is how you check 5A: each row is one attempt or a skipped call.")
if trace:
    st.dataframe(trace, width="stretch")
else:
    st.write("No steps recorded.")

with st.expander("What to try (5A checklist)"):
    st.markdown(
        """
1. **ok** — valid weather.
2. **500_then_ok** — two 500s, then success (retry works).
3. **timeout** — error in ~8s, not 30s. Trace event `timeout`.
4. **500** or **429** — several attempts; `backoff_s` grows (~1s, ~2s, ~4s).
5. **invalid** — one attempt, `invalid_response`, no fake temperature.
6. Unknown city `Atlantis` — `http_404`, no retry.
7. **500** three times in a row until breaker is `open`, then Get again — `circuit_open`, instant, no HTTP.
        """
    )
