from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    transcription_model: str = Field(
        default="whisper-1", validation_alias="OPENAI_TRANSCRIPTION_MODEL"
    )
    translation_model: str = Field(
        default="gpt-5.4-mini", validation_alias="OPENAI_TRANSLATION_MODEL"
    )
    data_dir: Path = Field(default=Path("var"), validation_alias="SUBTITLE_DATA_DIR")
    audio_chunk_seconds: int = Field(
        default=900, ge=60, le=3600, validation_alias="SUBTITLE_AUDIO_CHUNK_SECONDS"
    )
    translation_batch_size: int = Field(
        default=30, ge=1, le=100, validation_alias="SUBTITLE_TRANSLATION_BATCH_SIZE"
    )

    def require_api_key(self) -> str:
        if self.openai_api_key is None or not self.openai_api_key.get_secret_value().strip():
            raise ValueError("OPENAI_API_KEY is not configured")
        return self.openai_api_key.get_secret_value()

