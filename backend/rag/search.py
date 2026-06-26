"""
Semantic Search — Phase 6, AMLO

Embeds a query and retrieves the top-K most relevant chunks from pgvector
using cosine similarity. Used by the LLM layer to build context.
"""

import psycopg2
from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY, EMBEDDING_MODEL, TOP_K,
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
)

client = genai.Client(api_key=GEMINI_API_KEY)


def _embed_query(query: str) -> list[float]:
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY", output_dimensionality=768),
    )
    return result.embeddings[0].values


def search(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Returns the top-K most semantically similar chunks to the query.
    Each result: {"content": str, "source_file": str, "similarity": float}
    """
    embedding = _embed_query(query)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD
    )
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source_file, content,
               1 - (embedding <=> %s::vector) AS similarity
        FROM document_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (embedding_str, embedding_str, top_k)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"source_file": row[0], "content": row[1], "similarity": round(row[2], 4)}
        for row in rows
    ]


def format_context(chunks: list[dict]) -> str:
    """Concatenate retrieved chunks into a single context string for the LLM."""
    return "\n\n---\n\n".join(
        f"[Source: {c['source_file']} | Similarity: {c['similarity']}]\n{c['content']}"
        for c in chunks
    )
