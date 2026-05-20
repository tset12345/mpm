"""
수익률 분석 전략 기반 추상 클래스 (Strategy 패턴).

모든 알고리즘은 BaseStrategy를 상속하여
  - REQUIRED_KEYS: 필수 입력 키 목록 선언
  - calculate_expected_return(data): 분석 결과 dict 반환
를 구현해야 한다.
"""

from abc import ABC, abstractmethod


class StrategyValidationError(ValueError):
    """입력 데이터 유효성 검사 실패."""
    pass


class BaseStrategy(ABC):
    """기대 수익률 분석 전략 공통 인터페이스."""

    # 서브클래스에서 필수 키를 선언한다
    REQUIRED_KEYS: list[str] = []

    def validate(self, data: dict) -> None:
        """
        REQUIRED_KEYS의 모든 키가 data에 존재하고 None이 아닌지 검사한다.
        실패 시 StrategyValidationError를 raise한다.
        """
        missing = [k for k in self.REQUIRED_KEYS if data.get(k) is None]
        if missing:
            raise StrategyValidationError(
                f"[{self.__class__.__name__}] 필수 입력 데이터 누락: {missing}"
            )

    @abstractmethod
    def calculate_expected_return(self, data: dict) -> dict:
        """
        분석을 수행하고 결과를 dict로 반환한다.

        Args:
            data: 분석에 필요한 재무·시세 데이터 dict

        Returns:
            분석 결과 dict (JSON 직렬화 가능해야 함)
        """
        ...
