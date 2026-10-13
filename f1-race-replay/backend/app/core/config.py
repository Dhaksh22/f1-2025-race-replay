import os
from pathlib import Path
from typing import List


class Settings:
    """Application settings for the web-facing migration layer."""

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "F1 Race Replay 2025 Web API")
        self.app_version: str = os.getenv("APP_VERSION", "1.0.0")
        self.supported_season: int = 2025
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = int(os.getenv("PORT", "8000"))
        self.frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

        extra_origins = os.getenv("CORS_EXTRA_ORIGINS", "")
        origins: List[str] = [
            self.frontend_origin,

            # Vercel production and preview deployments
            "https://f1-2025-race-replay-lwny.vercel.app",
            "https://f1-2025-race-replay-lwny-m6bhyseuu-dks19.vercel.app",

            # Local development
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:4173",
        ]
        if extra_origins:
            origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])
        self.cors_origins: List[str] = list(dict.fromkeys(origins))

        repo_root = Path(__file__).resolve().parents[3]
        self.cache_dir: Path = Path(
            os.getenv("CACHE_DIR", str(repo_root / ".fastf1-cache"))
        )
        self.computed_data_dir: Path = Path(
            os.getenv("COMPUTED_DATA_DIR", str(repo_root / "computed_data"))
        )
        self.processed_data_dir: Path = Path(
            os.getenv("PROCESSED_DATA_DIR", str(repo_root / "data" / "processed"))
        )
        self.cache_version: str = os.getenv("PROCESSED_CACHE_VERSION", "v1")
        self.allow_demo_fallback: bool = (
            os.getenv("ALLOW_DEMO_FALLBACK", "true").lower() in ("1", "true", "yes")
        )
        self.prefer_live_fastf1: bool = (
            os.getenv("PREFER_LIVE_FASTF1", "false").lower() in ("1", "true", "yes")
        )

        # Optional LLM configuration (kept strictly on backend)
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "openai").lower()
        self.llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.llm_api_key: str = os.getenv("LLM_API_KEY", "")
        self.llm_base_url: str = os.getenv(
            "LLM_BASE_URL", "https://api.openai.com/v1"
        )
        self.llm_timeout_seconds: float = float(
            os.getenv("LLM_TIMEOUT_SECONDS", "15.0")
        )
        self.max_chat_input_chars: int = int(
            os.getenv("MAX_CHAT_INPUT_CHARS", "2000")
        )

    @property
    def is_llm_configured(self) -> bool:
        key = (self.llm_api_key or "").strip()
        return bool(key and key != "replace-with-your-key" and not key.startswith("your-"))


settings = Settings()
