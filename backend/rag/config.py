import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = "gemini-embedding-001"
LLM_MODEL = "gemini-2.5-flash"

CHUNK_SIZE = 500      # characters per chunk
CHUNK_OVERLAP = 50    # overlap between consecutive chunks
TOP_K = 5             # number of chunks to retrieve per query

DB_HOST = "127.0.0.1"
DB_PORT = 5433
DB_NAME = "amlo_db"
DB_USER = "amlo"
DB_PASSWORD = "amlo_secret"
