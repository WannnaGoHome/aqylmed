import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

# Ориентировочные тарифы, USD. Перед пилотом сверить с прайсами провайдеров —
# их можно переопределить в .env (STT_PRICES_PER_MINUTE / LLM_PRICES_PER_MILLION, JSON).
DEFAULT_STT_PRICES_PER_MINUTE: dict[str, float] = {
    "whisper-large-v3": 0.00185,          # Groq, $0.111/час
    "whisper-large-v3-turbo": 0.00067,    # Groq, $0.04/час
    "gpt-4o-mini-transcribe": 0.003,      # OpenAI (по техотчёту)
    "gpt-4o-transcribe": 0.006,           # OpenAI (по техотчёту)
    "whisper-1": 0.006,                   # OpenAI
}

# (input, output) USD за 1 млн токенов. Для thinking-моделей токены рассуждений входят в output.
DEFAULT_LLM_PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "gemini-3.8-flash": (1.50, 9.00),
    "gemini-3.8-flash-lite": (0.30, 2.50),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-2.5-flash": (0.30, 2.50),
}
FALLBACK_LLM_PRICE: tuple[float, float] = (0.30, 2.50)

_EPHEMERAL_SECRET = secrets.token_urlsafe(48)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"  # development | production
    database_url: str

    # --- Авторизация ---
    secret_key: str | None = None
    access_token_expire_minutes: int = 480
    min_password_length: int = 10
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    cors_origins: str = ""  # через запятую; пусто = только тот же origin

    # --- Хранение аудио ---
    upload_dir: Path = BASE_DIR / "storage" / "audio"
    max_upload_mb: int = 100
    audio_retention_days: int = 30  # 0 = не удалять автоматически
    delete_audio_after_processing: bool = False

    # --- Распознавание речи ---
    stt_provider: str = "groq"  # groq | openai
    groq_api_key: str | None = None
    groq_stt_model: str = "whisper-large-v3"
    groq_stt_language: str = "ru"  # пустая строка = автоопределение языка
    openai_api_key: str | None = None
    openai_stt_model: str = "gpt-4o-mini-transcribe"
    openai_stt_language: str = ""

    # --- Диаризация ---
    diarization_enabled: bool = True
    hf_token: str | None = None
    pyannote_model: str = "pyannote/speaker-diarization-community-1"
    num_speakers: int = 2

    # --- Языковая модель ---
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    llm_max_attempts: int = 3

    # --- Расходы ---
    monthly_api_budget_usd: float = 0.0  # 0 = без лимита
    stt_prices_per_minute: dict[str, float] = DEFAULT_STT_PRICES_PER_MINUTE
    llm_prices_per_million: dict[str, tuple[float, float]] = DEFAULT_LLM_PRICES_PER_MILLION

    max_concurrent_processing: int = 2

    @property
    def jwt_secret(self) -> str:
        if self.secret_key:
            return self.secret_key
        if self.environment == "production":
            raise RuntimeError("SECRET_KEY обязателен при ENVIRONMENT=production")
        return _EPHEMERAL_SECRET

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def prompts_dir(self) -> Path:
        return BASE_DIR / "app" / "prompts"

    @property
    def static_dir(self) -> Path:
        return BASE_DIR / "app" / "static"


settings = Settings()
