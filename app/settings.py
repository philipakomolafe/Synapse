from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_tutor_model: str = Field(default="gpt-4.1-mini", env="OPENAI_TUTOR_MODEL")
    openai_stt_model: str = Field(default="gpt-4o-mini-transcribe", env="OPENAI_STT_MODEL")
    openai_tts_model: str = Field(default="gpt-4o-mini-tts", env="OPENAI_TTS_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")
    openai_embedding_dims: int = Field(default=1536, env="OPENAI_EMBEDDING_DIMS")

    openai_guard_enabled: bool = Field(default=True, env="OPENAI_GUARD_ENABLED")
    openai_guard_model: str = Field(default="gpt-4.1-mini", env="OPENAI_GUARD_MODEL")
    openai_guard_max_retries: int = Field(default=1, env="OPENAI_GUARD_MAX_RETRIES")

    supabase_url: str = Field(default="", env="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", env="SUPABASE_SERVICE_ROLE_KEY")
    supabase_anon_key: str = Field(default="", env="SUPABASE_ANON_KEY")
    supabase_schema: str = Field(default="public", env="SUPABASE_SCHEMA")

    cors_allow_origins: str = Field(default="*", env="CORS_ALLOW_ORIGINS")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
