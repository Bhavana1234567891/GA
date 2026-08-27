import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ==========================================================
# Project Paths
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

PDF_DIR = DATA_DIR / "pdfs"

CHROMA_DB_DIR = DATA_DIR / "chroma_db"

LOG_DIR = BASE_DIR / "logs"

# Create folders automatically if they don't exist
PDF_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# PDF Configuration
# ==========================================================

SUPPORTED_EXTENSIONS = [".pdf"]

MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# ==========================================================
# Model Configuration
# ==========================================================

CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")