import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

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
    ampm_api_key: str = ""           # AMPM 앱 전용 API 키 (X-AMPM-Key 헤더)

    class Config:
        env_file = ".env"

settings = Settings()

# ALLOWED_USER_EMAIL 미설정 시 경고 — 유효한 Supabase 토큰이면 누구든 접근 가능
if not settings.allowed_user_email:
    logger.warning("ALLOWED_USER_EMAIL 미설정 — 인증된 모든 사용자가 API에 접근 가능합니다.")
