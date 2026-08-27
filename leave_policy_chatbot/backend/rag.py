from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from langchain_chroma import Chroma

from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

from config.settings import CHAT_MODEL, CHROMA_DB_DIR
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()


class LocalMiniLMEmbeddings(Embeddings):
    """Local all-MiniLM-L6-v2 embeddings (no OpenAI embedding access required)."""

    def __init__(self):
        self._model = ONNXMiniLM_L6_V2()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, vector)) for vector in self._model(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class RAGPipeline:

    def __init__(self):

        self.text_splitter = RecursiveCharacterTextSplitter(

            chunk_size=800,

            chunk_overlap=200,

            length_function=len,

            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                ""
            ]
        )
        self.embedding_model = LocalMiniLMEmbeddings()

    def split_text(self, text: str):

        if not text.strip():

            raise ValueError(
                "Text is empty."
            )

        chunks = self.text_splitter.split_text(text)

        print(f"Total Chunks : {len(chunks)}")

        return chunks
    
    def create_vector_store(self, chunks: list[str]):
        """
        Create a ChromaDB vector store from text chunks.

        Parameters
        ----------
        chunks : list[str]
            List of text chunks.

        Returns
            -------
        Chroma
            Chroma vector database instance.
        """

        if not chunks:
            raise ValueError("Chunk list is empty.")

        vector_store = Chroma.from_texts(
            texts=chunks,
            embedding=self.embedding_model,
            persist_directory=str(CHROMA_DB_DIR)
        )

        print("Vector store created successfully.")

        return vector_store
    

    def retrieve_context(
    self,
    vector_store: Chroma,
    query: str,
    k: int = 3
):
        """
        Retrieve the most relevant chunks for a user query.

        Parameters
        ----------
        vector_store : Chroma
            Chroma vector database.

        query : str
            User's question.

        k : int
            Number of similar chunks to retrieve.

        Returns
        -------
        str
            Combined relevant context.
        """

        if not query.strip():
            raise ValueError("Query cannot be empty.")

        # Perform similarity search
        documents = vector_store.similarity_search(
            query=query,
            k=k
        )

        if not documents:
            raise ValueError("No relevant context found.")

        # Combine retrieved chunks
        context = "\n\n".join(
            document.page_content
            for document in documents
        )

        print(f"Retrieved {len(documents)} relevant chunks.")

        return context

    def generate_answer(
        self,
        vector_store: Chroma,
        query: str,
        chat_history: list[dict] | None = None,
        k: int = 3
    ):
        """
        Answer a question using retrieved policy context and conversation history.
        """

        if chat_history is None:
            chat_history = []

        context = self.retrieve_context(
            vector_store,
            query,
            k=k
        )

        llm = ChatOpenAI(model=CHAT_MODEL)

        system_prompt = (
            "You are a leave policy assistant. Answer using ONLY the policy "
            "context below. If the answer is not in the context, say you cannot "
            "find it in the leave policy. Use conversation history to stay "
            "consistent with earlier questions.\n\n"
            f"Leave policy context:\n{context}"
        )

        messages = [SystemMessage(content=system_prompt)]

        for turn in chat_history:
            role = turn.get("role")
            content = turn.get("content", "")

            if not content:
                continue

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=query))

        response = llm.invoke(messages)

        return response.content
