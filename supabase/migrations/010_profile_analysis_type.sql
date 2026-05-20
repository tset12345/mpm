-- 프로필별 AI 분석 유형 선택 ('quant' | 'dividend')
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS analysis_type VARCHAR(20) DEFAULT 'quant';
