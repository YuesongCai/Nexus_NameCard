"""Runtime configuration. Everything is env-driven; no secrets in code."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PKG_ROOT = Path(__file__).resolve().parent
_API_ROOT = _PKG_ROOT.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEXUS_CARD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- service ---
    env: str = "dev"
    log_level: str = "INFO"
    public_base_url: str = "https://card.noahnexus.ai"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- content roots ---
    kb_dir: Path = _API_ROOT / "kb"
    cards_dir: Path = _API_ROOT / "data" / "cards"
    index_path: Path = _API_ROOT / "data" / "kb_index.json"
    web_dist_dir: Path = _API_ROOT.parent / "web" / "dist"
    default_card_slug: str = "grantpan"

    # --- LLM provider: bedrock | anthropic | echo ---
    llm_provider: str = "bedrock"
    llm_max_tokens: int = 700
    llm_temperature: float = 0.2

    # Bedrock (matches the AgentCore runtime region/account setup)
    aws_region: str = "ap-southeast-1"
    bedrock_model_id: str = "apac.anthropic.claude-sonnet-4-5-20250929-v1:0"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"

    # Anthropic direct API (fallback / local dev)
    anthropic_api_key: str = ""
    anthropic_model_id: str = "claude-sonnet-4-5"

    # --- retrieval ---
    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.02
    embeddings_enabled: bool = True

    # --- abuse control ---
    rate_limit_per_min: int = 12
    rate_limit_burst: int = 4
    max_question_chars: int = 600
    max_history_turns: int = 8

    @property
    def is_prod(self) -> bool:
        return self.env.lower() in {"prod", "production"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
