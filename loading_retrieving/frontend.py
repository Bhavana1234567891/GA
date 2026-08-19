import streamlit as st

from parsers import SUPPORTED_EXTENSIONS
from pipeline import ingest_file
from store import chunk_count, clear_all, list_sources, query_chunks

st.set_page_config(page_title="Document ingest", layout="wide")
st.title("Document ingest")
st.caption("Search only looks at files you ingested. Unrelated files will not answer a different question.")

if "ingest_log" not in st.session_state:
    st.session_state.ingest_log = []

types = sorted(ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS)

left, right = st.columns(2)

with left:
    st.subheader("Upload")
    files = st.file_uploader(
        "Choose files",
        type=types,
        accept_multiple_files=True,
        help="Supported: " + ", ".join(f".{t}" for t in types),
    )
    ingest = st.button(
        "Ingest",
        type="primary",
        icon=":material/upload_file:",
        disabled=not files,
    )

    if ingest and files:
        st.session_state.ingest_log = []
        with st.spinner("Parsing, cleaning, chunking, and storing..."):
            for uploaded in files:
                try:
                    result = ingest_file(uploaded.name, uploaded.getvalue())
                    st.session_state.ingest_log.append(("ok", result))
                except Exception as exc:
                    st.session_state.ingest_log.append(("error", uploaded.name, str(exc)))

    st.metric("Chunks in Chroma", chunk_count())
    sources = list_sources()
    if sources:
        st.caption(
            "Indexed files: "
            + ", ".join(f"{item['source']} ({item['chunks']})" for item in sources)
        )
    else:
        st.caption("No files indexed yet.")

    if sources and st.button("Clear all", icon=":material/delete:"):
        clear_all()
        st.session_state.ingest_log = []
        st.rerun()

    for entry in st.session_state.ingest_log:
        if entry[0] == "ok":
            result = entry[1]
            st.success(
                f"{result['source']}: {result['parsed_parts']} parsed part(s) → "
                f"{result['chunks']} chunk(s)"
            )
        else:
            _, name, message = entry
            st.error(f"{name}: {message}")

with right:
    st.subheader("Search")
    with st.form("search"):
        query = st.text_input("Find similar chunks")
        n_results = st.slider("Results", min_value=1, max_value=10, value=5)
        submitted = st.form_submit_button("Search", icon=":material/search:")

    if submitted:
        if not query.strip():
            st.warning("Enter a search query.")
        else:
            results = query_chunks(query.strip(), n_results=n_results)
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            indexed = list_sources()
            names = ", ".join(item["source"] for item in indexed) or "none"

            if not indexed:
                st.info("No chunks stored yet. Ingest a file first.")
            elif not documents:
                st.warning(
                    "No close matches for that query. Search only uses indexed files: "
                    f"{names}. Ingest a document that actually contains this topic, "
                    "then search again."
                )
            else:
                for i, text in enumerate(documents):
                    meta = metadatas[i] if i < len(metadatas) else {}
                    distance = distances[i] if i < len(distances) else None
                    source = meta.get("source", "unknown")
                    page = meta.get("page")
                    chunk_index = meta.get("chunk_index")
                    label = source
                    if page is not None:
                        label += f" · page {page}"
                    if chunk_index is not None:
                        label += f" · chunk {chunk_index}"
                    if distance is not None:
                        label += f" · distance {distance:.3f}"
                    with st.container(border=True):
                        st.caption(label)
                        st.write(text)
