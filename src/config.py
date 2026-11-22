"""Environment-driven application configuration.

No secrets are stored in code. Sensitive values must be provided via environment
variables or a local `.env` file (never committed).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency/runtime fallback
    load_dotenv = None  # type: ignore[assignment]


def _load_env() -> None:
    """Load local .env if python-dotenv is available (no-op in production envs)."""
    if load_dotenv is None:
        return
    # Load from project root when invoked from package context; do not override existing env.
    project_root = Path(__file__).resolve().parents[1]
    dotenv_path = project_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class ProviderConfig:
    """LLM/embedding provider settings (OpenRouter-first)."""

    llm_provider: str = "openrouter"
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct"
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.1-8b-instant"
    request_timeout_seconds: float = 30.0
    max_retries: int = 3


@dataclass(frozen=True)
class ModelConfig:
    """Model and retrieval/generation defaults (tunable via env/config)."""

    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    llm_temperature: float = 0.0
    classification_top_k_alternatives: int = 3


@dataclass(frozen=True)
class PathConfig:
    """Filesystem paths used by the application and evaluation harness."""

    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1])
    data_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1] / "data")
    storage_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1] / "storage")
    chroma_persist_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[1] / "storage" / "chroma"
    )
    decision_log_db_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[1] / "storage" / "decision_log.db"
    )
    cache_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1] / "storage" / "cache")
    evaluation_results_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[1] / "evaluation" / "results"
    )


@dataclass(frozen=True)
class ThresholdConfig:
    """Decision thresholds/placeholders (final values set via calibration)."""

    route_auto_min_confidence: float = 0.85
    route_assist_min_confidence: float = 0.60
    retrieval_relevance_threshold: float = 0.30
    min_support_score: float = 0.50


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime and observability settings."""

    environment: str = "development"
    log_level: str = "INFO"
    log_format: str = "json"  # json|text
    enable_cache: bool = True
    provider_simulation_mode: str = "off"  # off|timeout|rate_limit|unavailable|server_error
    max_concurrency: int = 4


@dataclass(frozen=True)
class AppConfig:
    provider: ProviderConfig
    models: ModelConfig
    paths: PathConfig
    thresholds: ThresholdConfig
    runtime: RuntimeConfig

    @property
    def active_llm_api_key(self) -> Optional[str]:
        provider = self.provider.llm_provider.lower()
        if provider == "openrouter":
            return self.provider.openrouter_api_key
        if provider == "groq":
            return self.provider.groq_api_key
        return None


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Load and cache application configuration from environment variables."""
    _load_env()

    paths = PathConfig(
        project_root=Path(os.getenv("PROJECT_ROOT", str(Path(__file__).resolve().parents[1]))),
        data_dir=Path(os.getenv("DATA_DIR", str(Path(__file__).resolve().parents[1] / "data"))),
        storage_dir=Path(os.getenv("STORAGE_DIR", str(Path(__file__).resolve().parents[1] / "storage"))),
        chroma_persist_dir=Path(
            os.getenv("CHROMA_PERSIST_DIR", str(Path(__file__).resolve().parents[1] / "storage" / "chroma"))
        ),
        decision_log_db_path=Path(
            os.getenv(
                "DECISION_LOG_DB_PATH",
                str(Path(__file__).resolve().parents[1] / "storage" / "decision_log.db"),
            )
        ),
        cache_dir=Path(os.getenv("CACHE_DIR", str(Path(__file__).resolve().parents[1] / "storage" / "cache"))),
        evaluation_results_dir=Path(
            os.getenv(
                "EVALUATION_RESULTS_DIR",
                str(Path(__file__).resolve().parents[1] / "evaluation" / "results"),
            )
        ),
    )

    provider = ProviderConfig(
        llm_provider=os.getenv("LLM_PROVIDER", "openrouter").strip().lower(),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct"),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        request_timeout_seconds=_get_float("LLM_REQUEST_TIMEOUT_SECONDS", 30.0),
        max_retries=_get_int("LLM_MAX_RETRIES", 3),
    )

    models = ModelConfig(
        embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"),
        embedding_dimension=_get_int("EMBEDDING_DIMENSION", 384),
        llm_temperature=_get_float("LLM_TEMPERATURE", 0.0),
        classification_top_k_alternatives=_get_int("CLASSIFICATION_TOP_K_ALTERNATIVES", 3),
    )

    thresholds = ThresholdConfig(
        route_auto_min_confidence=_get_float("ROUTE_AUTO_MIN_CONFIDENCE", 0.85),
        route_assist_min_confidence=_get_float("ROUTE_ASSIST_MIN_CONFIDENCE", 0.60),
        retrieval_relevance_threshold=_get_float("RETRIEVAL_RELEVANCE_THRESHOLD", 0.30),
        min_support_score=_get_float("MIN_SUPPORT_SCORE", 0.50),
    )

    runtime = RuntimeConfig(
        environment=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        log_format=os.getenv("LOG_FORMAT", "json").lower(),
        enable_cache=_get_bool("ENABLE_LLM_CACHE", True),
        provider_simulation_mode=os.getenv("PROVIDER_SIMULATION_MODE", "off").lower(),
        max_concurrency=_get_int("MAX_CONCURRENCY", 4),
    )

    return AppConfig(provider=provider, models=models, paths=paths, thresholds=thresholds, runtime=runtime)


def reset_config_cache() -> None:
    """Clear cached config (useful for tests)."""
    get_config.cache_clear()
