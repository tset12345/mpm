-- 섹터 주도주 캐시 테이블
CREATE TABLE IF NOT EXISTS sector_leaders (
    sector      TEXT        PRIMARY KEY,
    data        JSONB       NOT NULL DEFAULT '[]',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
