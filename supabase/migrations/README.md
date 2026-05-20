# Supabase 마이그레이션 관리

Supabase Dashboard → SQL Editor에서 순서대로 실행한 DDL을 파일로 관리합니다.

## 적용 방법

1. Supabase Dashboard > SQL Editor 열기
2. 해당 파일 내용을 붙여넣고 **Run** 실행
3. 적용 완료 후 아래 이력표에 날짜 기록

## 파일 네이밍 규칙

```
NNN_설명.sql
```
- `NNN`: 3자리 순번 (001, 002, ...)
- 설명: 변경 내용을 snake_case로 요약
- 새 마이그레이션 추가 시 반드시 파일 생성 후 이 README에 이력 추가

## 적용 이력

| 파일 | 내용 | 적용일 |
|------|------|--------|
| 001_initial_schema.sql | stock_recommendations, stock_ohlcv, reports 테이블 생성 | - |
| 002_keyword_subscriptions.sql | keyword_subscriptions 테이블 생성 | - |
| 003_reports_matched_keywords.sql | reports.matched_keywords 컬럼 추가 | - |
| 004_keyword_subscriptions_source_url.sql | keyword_subscriptions.source_url 컬럼 추가 | - |
| 005_recommendation_history.sql | recommendation_history 테이블 생성 | - |
| 006_holdings.sql | holdings 테이블 생성 | - |
| 007_tech_score.sql | stock_recommendations.tech_score 컬럼 추가 + 인덱스 | 2026-05-18 |
| 008_profiles.sql | profiles 테이블 생성, holdings.profile_id 컬럼 추가 | 2026-05-18 |
| 009_portfolio_analysis.sql | portfolio_analyses 테이블 생성 (AI 분석 캐시) | - |
| 010_profile_analysis_type.sql | profiles.analysis_type 컬럼 추가 ('quant' \| 'dividend') | - |
| 011_stock_master.sql | stock_master 테이블 생성 (KOSPI·KOSDAQ 전체 종목 마스터) | - |

> **주의**: Supabase는 직접 DB 연결(psycopg2)이 차단되어 있어 코드에서 DDL 자동 실행 불가. 반드시 Dashboard에서 수동 실행.
