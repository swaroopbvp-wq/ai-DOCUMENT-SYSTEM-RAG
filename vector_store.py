import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

def get_model():

    global model

    if model is None:

        print("Loading embedding model...")

        model = SentenceTransformer(
            "paraphrase-MiniLM-L3-v2"
        )

    return model


# ==================================================
# LOAD EMBEDDING MODEL
# ==================================================

model = None
dimension = 384

index = faiss.IndexFlatL2(
    dimension
)

# Stores metadata for every chunk
documents = []


# ==================================================
# CHUNKING
# ==================================================

def chunk_text(
        text: str,
        chunk_size: int = 300,
        overlap: int = 50
):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:

            chunks.append(chunk)

        start += (
            chunk_size - overlap
        )

    return chunks


# ==================================================
# EMBEDDING
# ==================================================

def embed_text(text: str):

    embedding = get_model().encode(
    [text],
    convert_to_numpy=True,
    show_progress_bar=False
)[0]
    return np.array(
        embedding
    ).astype(
        "float32"
    )

# ==================================================
# ADD DOCUMENT
# ==================================================

def add_document(
        doc_id: int,
        content: str
):

    chunks = chunk_text(
        content
    )

    if not chunks:

        print(
            f"No chunks created for document {doc_id}"
        )

        return

    for chunk_no, chunk in enumerate(
            chunks,
            start=1
    ):

        embedding = embed_text(
            chunk
        )

        index.add(
            np.array(
                [embedding],
                dtype="float32"
            )
        )

        documents.append({

            "doc_id":
            int(doc_id),

            "chunk_id":
            chunk_no,

            "content":
            chunk

        })

    print(
        f"Indexed {len(chunks)} chunks "
        f"for document {doc_id}"
    )

    print(
        f"Total vectors in FAISS: "
        f"{index.ntotal}"
    )


# ==================================================
# SEARCH
# ==================================================

def search(
        query: str,
        document_id: int = None,
        top_k: int = 5
):

    if index.ntotal == 0:

        print(
            "FAISS index empty"
        )

        return []

    query_vector = embed_text(
        query
    ).reshape(
        1,
        -1
    )

    search_limit = min(
        50,
        index.ntotal
    )

    D, I = index.search(
        query_vector,
        search_limit
    )

    print(
        "\n========== SEARCH DEBUG =========="
    )

    print(
        "Query:",
        query
    )

    print(
        "Requested Document ID:",
        document_id
    )

    print(
        "FAISS distances:",
        D
    )

    print(
        "FAISS indexes:",
        I
    )

    print(
        "Total stored chunks:",
        len(documents)
    )

    results = []

    for idx in I[0]:

        if idx < 0:

            continue

        if idx >= len(documents):

            continue

        doc = documents[idx]

        print(
            f"Found chunk -> "
            f"doc_id={doc['doc_id']} "
            f"chunk_id={doc['chunk_id']}"
        )

        if document_id is not None:

            if int(doc["doc_id"]) != int(document_id):

                continue

        results.append({

            "content":
            doc["content"],

            "doc_id":
            doc["doc_id"],

            "chunk_id":
            doc["chunk_id"]

        })

        if len(results) >= top_k:

            break

    print(
        "Final retrieved results:",
        len(results)
    )

    print(
        "=================================\n"
    )

    return results