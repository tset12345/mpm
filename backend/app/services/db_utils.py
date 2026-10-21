PAGE_SIZE = 1000  # Supabase(PostgREST) 기본 max_rows — 한 요청이 돌려주는 상한


def fetch_all(make_query, page_size: int = PAGE_SIZE) -> list[dict]:
    """1,000행 상한을 넘는 조회를 페이지 단위로 모두 가져온다.

    make_query: 호출할 때마다 새 쿼리 빌더를 돌려주는 함수.
    페이지 경계에서 행이 누락·중복되지 않도록 정렬 키가 유일해야 한다
    (예: .order("trade_date").order("stock_code")).
    """
    rows: list[dict] = []
    offset = 0
    while True:
        batch = make_query().range(offset, offset + page_size - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < page_size:
            return rows
        offset += page_size
