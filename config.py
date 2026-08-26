import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
env_file_path = BASE_DIR / ".env"
load_dotenv(env_file_path, override=True)

class Settings:
    def __init__(self):
        load_dotenv(env_file_path, override=True)
        self.NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
        self.NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        
        self.FAST_MODEL: str = os.getenv("FAST_MODEL", "meta/llama-3.2-11b-vision-instruct")
        self.STRONG_MODEL: str = os.getenv("STRONG_MODEL", "meta/llama-3.2-11b-vision-instruct")
        
        self.PRIMARY_SEARCH: str = os.getenv("PRIMARY_SEARCH", "ddgs")
        self.SEARXNG_URL: str = os.getenv("SEARXNG_URL", "http://localhost:8080")
        self.TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
        
        self.MAX_ROUNDS: int = int(os.getenv("MAX_ROUNDS", "2"))
        self.MAX_SOURCES: int = int(os.getenv("MAX_SOURCES", "15"))
        self.DUPLICATE_CLAIM_THRESHOLD: float = float(os.getenv("DUPLICATE_CLAIM_THRESHOLD", "0.70"))
        self.DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "research_agent.db"))

settings = Settings()
