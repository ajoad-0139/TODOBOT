import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings (BaseSettings) :
    PROJECT_NAME : str = "TODOBOT"
    API_V1_PREFIX : str = "/api/v1"
    DATABASE_URL : str = "sqlite:///./tasks.db"

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    AGENT_TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0"))
    AGENT_HISTORY_MESSAGES: int = int(os.getenv("AGENT_HISTORY_MESSAGES", "30"))

    # Embeddings and Qdrant
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "tasks")
    SEARCH_MIN_SCORE: float = float(os.getenv("SEARCH_MIN_SCORE", "0.25"))
    TARGET_AMBIGUITY_MARGIN: float = float(os.getenv("TARGET_AMBIGUITY_MARGIN", "0.08"))
    INDEX_SYNC_INTERVAL_SECONDS: int = int(os.getenv("INDEX_SYNC_INTERVAL_SECONDS", "30"))

    # Conversation memory lives in its own database, separate from the tasks.
    LANGGRAPH_CHECKPOINT_DATABASE_URL: str = os.getenv(
        "LANGGRAPH_CHECKPOINT_DATABASE_URL", "sqlite:///./checkpoints.db"
    )

    def validate_agent_settings(self) -> None:
        missing = [name for name in ("LLM_PROVIDER", "LLM_MODEL") if not getattr(self, name)]
        if missing:
            raise RuntimeError(
                "Missing required environment variables: " + ", ".join(missing)
                + ". Copy .env.example to .env and fill them in."
            )

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()