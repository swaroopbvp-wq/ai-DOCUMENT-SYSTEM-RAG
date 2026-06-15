import sqlite3

DB_NAME = "documents.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_connection()
    cursor = conn.cursor()

    # Documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        content TEXT NOT NULL,
        uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Queries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        asked_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def insert_document(filename, content):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO documents (filename, content)
        VALUES (?, ?)
        """,
        (filename, content)
    )

    doc_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return doc_id


def insert_query(document_id, question, answer):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO queries (
            document_id,
            question,
            answer
        )
        VALUES (?, ?, ?)
        """,
        (
            document_id,
            question,
            answer
        )
    )

    conn.commit()
    conn.close()


# ==================================
# CITATIONS SUPPORT
# ==================================

def get_document_filename(document_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT filename
        FROM documents
        WHERE id = ?
        """,
        (document_id,)
    )

    row = cursor.fetchone()

    conn.close()

    if row:

        return row["filename"]

    return "Unknown Document"


# ==================================
# OPTIONAL HELPER
# Useful later for multi-document support
# ==================================

def get_all_documents():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, filename
        FROM documents
        ORDER BY uploaded_at DESC
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return rows