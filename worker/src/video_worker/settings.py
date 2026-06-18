from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    worker_secret: str = "change-me-in-dev"
    ffmpeg_path: str = "ffmpeg"
    ffmpeg_timeout_seconds: int = 3600
    pipeline_mode: str = "stub"  # stub | real

    openai_base_url: str = "https://api.deepseek.com"
    openai_api_key: str = ""
    openai_model: str = "deepseek-chat"

    whisper_model: str = "tiny"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    edge_tts_voice: str = "vi-VN-HoaiMyNeural"


def get_settings() -> Settings:
    return Settings()
