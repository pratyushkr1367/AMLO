"""
Document Ingestion — Phase 6, AMLO

Chunks a text file and embeds each chunk into the pgvector document_chunks table.
Run once per document. Safe to re-run — existing chunks for the same file are deleted first.

Run: python ingest.py sample_manual.txt
"""

import sys
import psycopg2
from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY, EMBEDDING_MODEL,
    CHUNK_SIZE, CHUNK_OVERLAP,
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
)

client = genai.Client(api_key=GEMINI_API_KEY)


def chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if c]


def embed(text: str) -> list[float]:
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", output_dimensionality=768),
    )
    return result.embeddings[0].values


def ingest(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    source_file = file_path.split("/")[-1].split("\\")[-1]
    chunks = chunk_text(text)

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD
    )
    cur = conn.cursor()

    cur.execute("DELETE FROM document_chunks WHERE source_file = %s", (source_file,))
    print(f"Ingesting '{source_file}' — {len(chunks)} chunks")

    for i, chunk in enumerate(chunks):
        embedding = embed(chunk)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        cur.execute(
            """
            INSERT INTO document_chunks (source_file, chunk_index, content, embedding)
            VALUES (%s, %s, %s, %s::vector)
            """,
            (source_file, i, chunk, embedding_str)
        )
        print(f"  [{i+1}/{len(chunks)}] embedded ({len(chunk)} chars)")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nDone — {len(chunks)} chunks stored in pgvector.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_manual.txt"
    ingest(path)
