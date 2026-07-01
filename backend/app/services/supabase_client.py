from supabase import create_client, Client
from app.core.config import settings
from postgrest._sync.client import SyncPostgrestClient
from postgrest.utils import SyncClient


def _create_session_http1(self, base_url, headers, timeout, verify=True, proxy=None):
    """HTTP/2 비활성화 — sync client + async FastAPI 조합에서 [Errno 11] EAGAIN 방지."""
    return SyncClient(
        base_url=base_url,
        headers=headers,
        timeout=timeout,
        verify=verify,
        proxy=proxy,
        follow_redirects=True,
        http2=False,
    )


SyncPostgrestClient.create_session = _create_session_http1

supabase: Client = create_client(settings.supabase_url, settings.supabase_service_key)
