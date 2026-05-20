from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_account_no: str = ""
    kis_is_mock: bool = True
    gemini_api_key: str = ""
    supabase_url: str = ""
    supabase_service_key: str = ""
    database_url: str = ""
    allowed_origins: str = "http://localhost:3000"
    dart_api_key: str = ""
    supabase_jwt_secret: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
