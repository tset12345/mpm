"""
KOSPI/KOSDAQ 업종별 평균 PER 테이블.
KIS API inquire-price 응답의 bstp_kor_isnm(업종명) 기준.
출처: KRX 업종 PER 통계 (2024~2025 평균 기준)
"""

# KIS API가 반환하는 실제 업종명 → 평균 PER
_SECTOR_PER: dict[str, float] = {
    "전기·전자":       16.0,
    "IT 서비스":       22.0,
    "화학":            12.0,
    "금융":             8.0,
    "은행":             7.0,
    "증권":             9.0,
    "보험":             8.0,
    "철강·금속":        9.0,
    "음식료·담배":     18.0,
    "제약":            28.0,
    "바이오":          35.0,
    "건설":            10.0,
    "기계·장비":       13.0,
    "섬유·의복":       12.0,
    "유통":            16.0,
    "통신":            12.0,
    "전기·가스":       15.0,
    "종이·목재":       11.0,
    "비금속광물":      10.0,
    "의료·정밀기기":   25.0,
    "운송장비·부품":   11.0,
    "운수·창고":       12.0,
    "농업·임업·어업":  15.0,
    "기타금융":        10.0,
    "기타서비스":      18.0,
    "기타제조":        13.0,
    "소프트웨어":      25.0,
    "반도체":          18.0,
    "디스플레이":      14.0,
    "게임":            20.0,
    "엔터테인먼트":    25.0,
}

DEFAULT_SECTOR_PER = 14.0


def get_sector_per(sector_name: str | None) -> tuple[str | None, float]:
    """
    업종명으로 섹터 평균 PER를 반환한다.

    Returns:
        (matched_sector_name, per)
        matched_sector_name: 입력된 sector_name 그대로 반환 (매칭 여부 무관).
        per: 섹터 평균 PER (매칭 실패 시 DEFAULT_SECTOR_PER)
    """
    if not sector_name:
        return None, DEFAULT_SECTOR_PER

    # 완전 매칭
    if sector_name in _SECTOR_PER:
        return sector_name, _SECTOR_PER[sector_name]

    # 부분 매칭 — KIS 업종명이 약간 다를 수 있음
    for key, per in _SECTOR_PER.items():
        if key in sector_name or sector_name in key:
            return sector_name, per

    return sector_name, DEFAULT_SECTOR_PER
