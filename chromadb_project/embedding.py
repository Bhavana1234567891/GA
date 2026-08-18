from sentence_transformers import SentenceTransformer
import chromadb


# --------------------------------------------------
# 1. Load the embedding model
# --------------------------------------------------

model = SentenceTransformer("all-MiniLM-L6-v2")


# --------------------------------------------------
# 2. Sentences
# --------------------------------------------------

sentences = [
    "I love playing football",
    "Football is my favorite sport",
    "I like eating pizza",
    "The car is very fast"
]


# --------------------------------------------------
# 3. Generate embeddings
# --------------------------------------------------

embeddings = model.encode(sentences)


# --------------------------------------------------
# 4. Create ChromaDB client
# --------------------------------------------------

client = chromadb.PersistentClient(path="./chroma_db")


# --------------------------------------------------
# 5. Delete old collection if it exists
#    This avoids duplicate ID errors
# --------------------------------------------------

try:
    client.delete_collection(name="sentence_embeddings")
except Exception:
    pass


# --------------------------------------------------
# 6. Create a new collection
# --------------------------------------------------

collection = client.get_or_create_collection(
    name="sentence_embeddings"
)


# --------------------------------------------------
# 7. Metadata for each sentence
# --------------------------------------------------

metadatas = [
    {
        "category": "sports",
        "type": "activity"
    },
    {
        "category": "sports",
        "type": "preference"
    },
    {
        "category": "food",
        "type": "preference"
    },
    {
        "category": "vehicle",
        "type": "description"
    }
]


# --------------------------------------------------
# 8. Store sentences, embeddings and metadata
# --------------------------------------------------

collection.add(
    ids=[
        "sentence_1",
        "sentence_2",
        "sentence_3",
        "sentence_4"
    ],

    documents=sentences,

    embeddings=embeddings.tolist(),

    metadatas=metadatas
)

print("Embeddings and metadata stored successfully!")


# --------------------------------------------------
# 9. Check stored data
# --------------------------------------------------

data = collection.get(
    include=[
        "documents",
        "embeddings",
        "metadatas"
    ]
)

for doc, vector, metadata in zip(
    data["documents"],
    data["embeddings"],
    data["metadatas"]
):

    print("\nSentence:", doc)
    print("Metadata:", metadata)
    print("Vector dimensions:", len(vector))
    print("First 5 values:", vector[:5])


# --------------------------------------------------
# 10. Take user query
# --------------------------------------------------

query = input("\nEnter your query: ")


# --------------------------------------------------
# 11. Convert query into embedding
# --------------------------------------------------

query_embedding = model.encode(query).tolist()


# --------------------------------------------------
# 12. Search ChromaDB
#     ONLY search documents where
#     category = sports
# --------------------------------------------------

results = collection.query(
    query_embeddings=[query_embedding],

    where={
        "category": "sports"
    },

    n_results=2
)


# --------------------------------------------------
# 13. Display relevant results
# --------------------------------------------------

print("\nRelevant sports results:")

for i, document in enumerate(results["documents"][0]):

    distance = results["distances"][0][i]
    metadata = results["metadatas"][0][i]

    print(f"\nResult {i + 1}:")
    print("Sentence:", document)
    print("Metadata:", metadata)
    print("Distance:", distance)