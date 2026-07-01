import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Athena AI"
    PROJECT_VERSION: str = "0.1.0"
    
    # Ollama Configuration
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "qwen2.5:7b")
    
    # Database Configuration (fallback to SQLite locally if POSTGRES_URL not provided)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./athena.db"
    )

    # Qdrant Configuration
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

settings = Settings()
