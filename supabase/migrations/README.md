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
| 012_reports_source_url.sql | reports.source_url 컬럼 추가 | - |
| 013_reports_related_stocks.sql | reports.related_stocks 컬럼 추가 | - |
| 014_recommendations_fund_score.sql | stock_recommendations.fund_score 컬럼 추가 | - |
| 015_recommendations_entry_price.sql | stock_recommendations.entry_price 컬럼 추가 | - |
| 016_recommendations_source_conditions.sql | stock_recommendations.source_conditions 컬럼 추가 | - |
| 017_sector_leaders.sql | sector_leaders 테이블 생성 (섹터 주도주 캐시) | - |
| 018_favorites.sql | favorites 테이블 생성 | - |
| 019_virtual_trading.sql | virtual_accounts, virtual_positions, virtual_trades 테이블 생성 | 2026-06-04 |
| 020_enable_rls.sql | 전체 14개 테이블 RLS 활성화 (anon 키 기본 거부) | 2026-06-04 |
| 021_virtual_position_tracking.sql | virtual_positions에 entry_atr·highest_price·half_exited·entry_low 컬럼 추가 | 2026-06-09 |

> **주의**: Supabase는 직접 DB 연결(psycopg2)이 차단되어 있어 코드에서 DDL 자동 실행 불가. 반드시 Dashboard에서 수동 실행.
