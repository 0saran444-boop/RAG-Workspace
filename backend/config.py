import os
from pathlib import Path
from dotenv import load_dotenv

# Search and load .env from backend directory and root workspace directory
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

# Load from backend/.env first, then root .env if present
load_dotenv(dotenv_path=BASE_DIR / ".env")
load_dotenv(dotenv_path=ROOT_DIR / ".env")
load_dotenv()  # Fallback to default search

class Config:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME = os.getenv("DB_NAME", "student_db")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    GEMINI_API_KEY = GOOGLE_API_KEY

    # Ensure os.environ has GOOGLE_API_KEY for downstream libraries
    if GOOGLE_API_KEY and not os.getenv("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

    DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR", str(ROOT_DIR / "documents"))
    VECTORSTORE_DIR = os.getenv("VECTORSTORE_DIR", str(ROOT_DIR / "vectorstore"))
