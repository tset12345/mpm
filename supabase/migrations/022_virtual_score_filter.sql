-- 가상거래 계좌: 매수 점수 필터 타입 및 최대 점수 컬럼 추가
ALTER TABLE virtual_accounts
  ADD COLUMN IF NOT EXISTS score_filter_type text NOT NULL DEFAULT 'gte',
  ADD COLUMN IF NOT EXISTS max_score integer;

-- 기존 계좌는 min_score ≥ 기존값 유지 (score_filter_type 기본값 'gte' 자동 적용)
