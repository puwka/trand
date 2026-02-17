"""Main application configuration."""

from dotenv import load_dotenv

load_dotenv()

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings  # pydantic<2

class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_key: str = ""
    openai_api_key: str = ""
    neuroapi_base_url: str = "https://neuroapi.host/v1"
    yt_cookies_from_browser: str = ""
    yt_cookies_file: str = ""
    neuroapi_model: str = "gpt-3.5-turbo"
    openai_ssl_verify: str = "true"
    google_sheet_id: str = ""
    google_credentials_json: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
