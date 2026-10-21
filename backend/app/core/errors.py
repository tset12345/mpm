import logging

from fastapi import HTTPException

logger = logging.getLogger("app.errors")


def internal_error(public_message: str) -> HTTPException:
    """except 블록 안에서 `raise internal_error("...")`로 사용한다.

    원인 예외는 스택트레이스와 함께 로그에 남기고, 클라이언트에는 고정 문구만 돌려준다.
    """
    logger.exception(public_message)
    return HTTPException(status_code=500, detail=public_message)
