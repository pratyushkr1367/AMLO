import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = "gemini-embedding-001"
LLM_MODEL       = "gemini-2.0-flash-lite"

# Local LLM via Ollama (https://ollama.com) — run: ollama pull gemma3:4b
LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "local")   # "gemini" or "local"
LOCAL_LLM_URL   = os.getenv("LOCAL_LLM_URL", "http://localhost:11434")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "gemma3:4b")

CHUNK_SIZE = 500      # characters per chunk
CHUNK_OVERLAP = 50    # overlap between consecutive chunks
TOP_K = 5             # number of chunks to retrieve per query

DB_HOST = "127.0.0.1"
DB_PORT = 5433
DB_NAME = "amlo_db"
DB_USER = "amlo"
DB_PASSWORD = "amlo_secret"
