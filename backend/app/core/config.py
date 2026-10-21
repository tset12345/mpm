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
    guest_api_key: str = ""          # 웹 게스트 읽기 전용 키 (X-Guest-Key 헤더)
    rate_limit_ip_per_min: int = 300       # IP당 전체 요청 (헬스체크 제외)
    rate_limit_user_per_min: int = 600     # 인증된 사용자(본인·AMPM 키)당
    rate_limit_guest_per_min: int = 120    # 게스트(IP별)
    rate_limit_expensive_per_min: int = 6  # 수동 동기화·AI 분석 등 비용이 큰 작업
    trusted_proxy_hops: int = 0            # 앞단 프록시 수 (0=소켓 IP 사용, N=X-Forwarded-For 뒤에서 N번째)
    kis_max_rps: float = 0           # KIS 초당 요청 상한 (0=자동: 실전 15, 모의 2)
    kis_max_concurrency: int = 8     # KIS 동시 요청 상한

    class Config:
        env_file = ".env"

settings = Settings()

# ALLOWED_USER_EMAIL 미설정 시 경고 — 유효한 Supabase 토큰이면 누구든 접근 가능
if not settings.allowed_user_email:
    logger.warning("ALLOWED_USER_EMAIL 미설정 — 인증된 모든 사용자가 API에 접근 가능합니다.")
