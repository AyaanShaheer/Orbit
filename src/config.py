import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    # FalkorDB / Redis Settings
    falkordb_host: str = Field(default_factory=lambda: os.getenv("FALKORDB_HOST", "127.0.0.1"))
    falkordb_port: int = Field(default_factory=lambda: int(os.getenv("FALKORDB_PORT", "6379")))
    graph_name: str = Field(default_factory=lambda: os.getenv("GRAPH_NAME", "orbit_memory"))
    
    # LLM Settings
    use_mock_llm: bool = Field(default_factory=lambda: os.getenv("USE_MOCK_LLM", "true").lower() in ("true", "1", "yes"))
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "mock"))
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    
    # API Settings
    api_host: str = Field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    
    # Replay & Event Persistence
    sqlite_db_path: str = Field(default_factory=lambda: os.getenv("SQLITE_DB_PATH", "orbit_events.db"))

settings = Settings()
