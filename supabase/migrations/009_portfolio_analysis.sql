-- 포트폴리오 AI 분석 결과 캐시
CREATE TABLE IF NOT EXISTS portfolio_analyses (
    id           SERIAL PRIMARY KEY,
    profile_id   INTEGER REFERENCES profiles(id) ON DELETE CASCADE,  -- NULL = 전체
    analysis_text TEXT NOT NULL,
    holdings_hash VARCHAR(32) NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- NULL-safe unique: profile_id=NULL 을 0으로 처리 (SERIAL은 1부터 시작)
CREATE UNIQUE INDEX IF NOT EXISTS idx_portfolio_analyses_profile
ON portfolio_analyses (COALESCE(profile_id, 0));

ALTER TABLE portfolio_analyses DISABLE ROW LEVEL SECURITY;
