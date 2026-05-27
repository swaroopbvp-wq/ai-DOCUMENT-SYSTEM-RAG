from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db, insert_document, insert_query, get_connection
from vector_store import add_document, search

import pdfplumber
from docx import Document
import io

from dotenv import load_dotenv
import os
from openai import OpenAI


# ===================== LOAD ENV =====================

load_dotenv()

client = OpenAI(
    api_key=os.getenv("SAMBANOVA_API_KEY"),
    base_url="https://api.sambanova.ai/v1"
)

print(
    "API loaded:",
    os.getenv("SAMBANOVA_API_KEY") is not None
)


# ===================== FASTAPI =====================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ===================== INIT DATABASE =====================

init_db()


# ===================== LOAD OLD DOCS =====================

@app.on_event("startup")
def load_existing_documents():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, content FROM documents"
    )

    rows = cursor.fetchall()

    conn.close()

    for row in rows:

        if row["content"]:

            add_document(

                row["id"],

                row["content"]

            )

    print(
        f"Loaded {len(rows)} documents into FAISS."
    )


# ===================== REQUEST MODEL =====================

class AskRequest(BaseModel):

    document_id: int

    question: str


# ===================== HEALTH =====================

@app.get("/ping")
def ping():

    return {

        "status":

        "Backend OK"

    }


# ===================== UPLOAD =====================

@app.post("/upload")
async def upload_doc(
        file: UploadFile = File(...)
):

    filename = file.filename.lower()

    raw_content = await file.read()

    extracted_text = ""


    try:

        if filename.endswith(".txt"):

            extracted_text = raw_content.decode(
                "utf-8"
            )


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


        elif filename.endswith(".docx"):

            doc = Document(
                io.BytesIO(raw_content)
            )

            for para in doc.paragraphs:

                extracted_text += (

                    para.text + "\n"

                )


        else:

            return {

                "message":

                "Unsupported format"

            }


    except Exception as e:

        print(

            "Extraction error:",

            e

        )

        return {

            "message":

            "Parsing failed"

        }



    if not extracted_text.strip():

        return {

            "message":

            "No readable text"

        }



    doc_id = insert_document(

        filename,

        extracted_text

    )


    add_document(

        doc_id,

        extracted_text

    )


    return {

        "message":

        "Uploaded successfully",

        "document_id":

        doc_id

    }


# ===================== ASK =====================

@app.post("/ask")
def ask_doc(
        data: AskRequest
):

    print(
        "\n----- NEW REQUEST -----"
    )

    print(
        "Document:",

        data.document_id
    )

    print(
        "Question:",

        data.question
    )


    chunks = search(

        query=data.question,

        document_id=data.document_id

    )


    print(

        "Retrieved chunks:",

        chunks

    )


    if not chunks:

        return {

            "answer":

            "No relevant information found in document."

        }



    context = "\n".join(

        chunks

    )


    # ========= IMPROVED PROMPT =========

    prompt = f"""

You are an intelligent AI document assistant.

Answer ONLY using information from the document.

Document:

{context}


Question:

{data.question}


Instructions:

- Answer in complete sentences.
- Sound natural and professional.
- Explain briefly.
- Do NOT invent information.
- If answer missing, say:

"The information was not found in the document."


Examples:

Question:
What is the total amount?

Answer:
The total amount is 1200 Rupees.


Question:
Who is the customer?

Answer:
The customer name is Rahul.


Now answer:

"""


    try:

        response = (

            client.chat.completions.create(

                model="DeepSeek-V3.1",

                messages=[

                    {

                        "role":

                        "system",

                        "content":

                        "You answer questions from uploaded documents."

                    },

                    {

                        "role":

                        "user",

                        "content":

                        prompt

                    }

                ],

                temperature=0.3

            )

        )


        answer = (

            response

            .choices[0]

            .message

            .content

        )


    except Exception as e:

        print(

            "LLM ERROR:",

            e

        )


        answer = (

            "Error generating answer: "

            + str(e)

        )



    insert_query(

        data.document_id,

        data.question,

        answer

    )


    return {

        "answer":

        answer

    }


# ===================== HISTORY =====================

@app.get(
    "/history/{document_id}"
)

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

        WHERE document_id=?

        ORDER BY asked_at DESC

        """,

        (

            document_id,

        )

    )


    rows = cursor.fetchall()

    conn.close()


    if not rows:

        return {

            "message":

            "No history"

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