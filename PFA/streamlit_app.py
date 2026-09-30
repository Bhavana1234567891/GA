import httpx
import streamlit as st

st.title("Personal finance")

if "chat" not in st.session_state:
    st.session_state.chat = []

for item in st.session_state.chat:
    with st.chat_message("user"):
        st.write(item["question"])
    if item["answer"] is not None:
        with st.chat_message("assistant"):
            st.write(item["answer"])
            for tool in item["tools"]:
                st.write(f"{tool['name']}: {tool['args']}")

if st.session_state.chat and st.session_state.chat[-1]["answer"] is None:
    question = st.session_state.chat[-1]["question"]
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = httpx.post(
                    "http://127.0.0.1:8000/ask",
                    json={"question": question},
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                answer = data["answer"]
                tools = data["tools"]
            except httpx.HTTPError:
                answer = "Could not get an answer. Is FastAPI running on port 8000?"
                tools = []
        st.write(answer)
        for tool in tools:
            st.write(f"{tool['name']}: {tool['args']}")
    st.session_state.chat[-1]["answer"] = answer
    st.session_state.chat[-1]["tools"] = tools
    st.rerun()

question = st.chat_input("Ask about your transactions")
if question:
    st.session_state.chat.append(
        {"question": question, "answer": None, "tools": []}
    )
    st.rerun()
