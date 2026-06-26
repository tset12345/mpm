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
    allowed_origins: str = "http://localhost:3000,https://mpm-fe.vercel.app"
    allowed_user_email: str = ""
    dart_api_key: str = ""
    supabase_jwt_secret: str = ""
    enable_scheduler: bool = False   # 일일 동기화 + 섹터주도주 (Render)
    enable_intraday: bool = False    # 장중 10분 매매 트리거 (Local only)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    enable_telegram: bool = False    # 텔레그램 알림 (Local only, Render 배포 제외)

    class Config:
        env_file = ".env"

settings = Settings()
