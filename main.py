from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import (
    init_db,
    insert_document,
    insert_query,
    get_connection,
    get_document_filename
)

from vector_store import (
    add_document,
    search
)

import pdfplumber
from docx import Document
import io

from dotenv import load_dotenv
import os

from openai import OpenAI


# ==================================================
# LOAD ENV
# ==================================================

load_dotenv()

API_KEY = os.getenv("AICREDITS_API_KEY")

print("API Loaded:", API_KEY is not None)

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.aicredits.in/v1"
)


# ==================================================
# FASTAPI APP
# ==================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ==================================================
# DATABASE INIT
# ==================================================

init_db()


# ==================================================
# LOAD EXISTING DOCUMENTS INTO FAISS
# ==================================================

@app.on_event("startup")
def load_existing_documents():
    print("Skipping FAISS preload")
# ==================================================
# REQUEST MODEL
# ==================================================

class AskRequest(BaseModel):

    
    question: str


# ==================================================
# HEALTH CHECK
# ==================================================

@app.get("/ping")
def ping():

    return {
        "status": "Backend OK"
    }


# ==================================================
# DOCUMENT UPLOAD
# ==================================================

@app.post("/upload")
async def upload_doc(
    files: list[UploadFile] = File(...)
):

    uploaded_docs = []

    for file in files:

        filename = file.filename.lower()

        raw_content = await file.read()

        extracted_text = ""

        try:

            # TXT
            if filename.endswith(".txt"):

                extracted_text = raw_content.decode(
                    "utf-8"
                )

            # PDF
            elif filename.endswith(".pdf"):

                with pdfplumber.open(
                    io.BytesIO(raw_content)
                ) as pdf:

                    for page in pdf.pages:

                        text = page.extract_text()

                        if text:

                            extracted_text += (
                                text + "\n"
                            )

            # DOCX
            elif filename.endswith(".docx"):

                doc = Document(
                    io.BytesIO(raw_content)
                )

                for para in doc.paragraphs:

                    extracted_text += (
                        para.text + "\n"
                    )

            else:

                continue

        except Exception as e:

            print(
                "DOCUMENT ERROR:",
                e
            )

            continue

        if not extracted_text.strip():

            continue

        doc_id = insert_document(

            filename,

            extracted_text

        )

        add_document(

            doc_id,

            extracted_text

        )

        uploaded_docs.append({

            "document_id":
            doc_id,

            "filename":
            filename

        })

        print(
            f"Document {doc_id} indexed."
        )

    return {

        "message":
        "Documents uploaded successfully",

        "documents":
        uploaded_docs

    }




# ==================================================
# ASK QUESTION
# ==================================================

@app.post("/ask")
def ask_doc(
    data: AskRequest
):

    print("\n========== NEW REQUEST ==========")

    

    print(
        "Question:",
        data.question
    )

    # Retrieve relevant chunks
    chunks = search(

        query=data.question,

        document_id=None

    )

    print(
        "Chunks retrieved:",
        len(chunks)
    )

    # No chunks found
    if not chunks:

        return {
            "answer":
            "No relevant information found in the document.",
            "sources": []
        }

    context = ""

    sources = []

    for chunk in chunks:

        context += chunk["content"] + "\n"

        source = {
            "file": get_document_filename(
                chunk["doc_id"]
            ),
            "chunk": chunk["chunk_id"]
        }

        if source not in sources:
            sources.append(source)

    # ==================================================
    # PROMPT
    # ==================================================

    prompt = f"""

You are an AI document assistant.

Answer ONLY using the provided document context.

DOCUMENT:

{context}


QUESTION:

{data.question}


RULES:

- Answer naturally
- Use complete sentences
- Do NOT invent information
- Keep answers concise
- If answer missing, say:

"The information was not found in the document."


EXAMPLE:

Question:
What is the total amount?

Answer:
The total amount is 1200 Rupees.


Now answer the question.

"""

    try:

        response = client.chat.completions.create(

            model="anthropic/claude-3-haiku",

            messages=[

                {
                    "role": "system",
                    "content":
                    "You answer questions based only on uploaded documents."
                },

                {
                    "role": "user",
                    "content": prompt
                }

            ],

            temperature=0.3,

            max_tokens=300

        )

        answer = (
            response
            .choices[0]
            .message
            .content
        )

    except Exception as e:

        print("LLM ERROR:", e)

        if "401" in str(e):

            answer = (
                "⚠️ Invalid API key configuration."
            )

        elif "429" in str(e):

            answer = (
                "⚠️ AI service is busy right now. Please try again shortly."
            )

        else:

            answer = (
                "⚠️ Error generating answer."
            )

    # Save query history
    insert_query(

        0,

        data.question,

        answer

    )

    return {
        "answer": answer,
        "sources": sources
    }


# ==================================================
# HISTORY
# ==================================================

@app.get("/history/{document_id}")
def get_history(
    document_id: int
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(

        """
        SELECT
        question,
        answer,
        asked_at

        FROM queries

        WHERE document_id = ?

        ORDER BY asked_at DESC
        """,

        (document_id,)

    )

    rows = cursor.fetchall()

    conn.close()

    if not rows:

        return {
            "message":
            "No history found"
        }

    return [

        {
            "question":
            row["question"],

            "answer":
            row["answer"],

            "asked_at":
            row["asked_at"]
        }

        for row in rows

    ]