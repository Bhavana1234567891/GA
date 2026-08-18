import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import streamlit as st

from backend.pdf_loader import PDFLoader
from backend.rag import RAGPipeline
from config.settings import PDF_DIR

st.set_page_config(
    page_title="Leave Policy Chatbot",
    page_icon=":material/chat:",
    layout="centered",
)

st.session_state.setdefault("messages", [])
st.session_state.setdefault("vector_store", None)
st.session_state.setdefault("pdf_name", None)


@st.cache_resource
def get_pipeline():
    return RAGPipeline()


def index_pdf(uploaded_file):
    save_path = PDF_DIR / uploaded_file.name
    save_path.write_bytes(uploaded_file.getbuffer())

    loader = PDFLoader()
    text = loader.load_pdf(str(save_path))
    pipeline = get_pipeline()
    chunks = pipeline.split_text(text)
    return pipeline.create_vector_store(chunks)


st.title("Leave Policy Chatbot")
st.caption("Ask questions about your uploaded leave policy.")

with st.sidebar:
    st.header("Policy PDF")
    uploaded = st.file_uploader("Upload a leave policy PDF", type=["pdf"])

    if uploaded is not None and st.button("Index PDF"):
        with st.spinner("Indexing PDF..."):
            try:
                st.session_state.vector_store = index_pdf(uploaded)
                st.session_state.pdf_name = uploaded.name
                st.session_state.messages = []
                st.success(f"Indexed {uploaded.name}")
            except Exception as error:
                st.error(str(error))

    if st.session_state.pdf_name:
        st.badge("Ready", icon=":material/check:", color="green")
        st.caption(st.session_state.pdf_name)
    else:
        st.badge("No PDF", icon=":material/info:", color="orange")

    if st.session_state.messages and st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

if not os.getenv("OPENAI_API_KEY"):
    st.error("Missing OPENAI_API_KEY. Add it to leave_policy_chatbot/.env")
    st.stop()

if st.session_state.vector_store is None:
    st.info("Upload and index a leave policy PDF in the sidebar to start chatting.")
    st.stop()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input(
    "Ask about the leave policy",
    submit_mode="disable",
):
    history = list(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            response = get_pipeline().generate_answer(
                st.session_state.vector_store,
                prompt,
                history,
            )
        except Exception as error:
            response = f"Could not answer that: {error}"
        st.write(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
