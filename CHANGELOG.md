# Changelog

버전 규칙과 고도화 계획은 `ENHANCEMENT_V2.md` 참조.

## [Unreleased] — v2.0.0 (브랜치 `release/v2.0.0`)

### 2.0.0-alpha.1 — 1단계: 품질 기반 (2026-10-21)

- 추가: 백엔드 단위 테스트 119개, GitHub Actions CI(pytest·tsc·의존성 감사)
- 추가: 요청 ID(`X-Request-ID`) 로깅, `LOG_LEVEL`/`LOG_FORMAT=json`, 표준 500 응답
- 추가: 인증 필요 `GET /api/v1/health/detail` (DB·데이터 최신성·스케줄러·메모리)
- 추가: `supabase/migrations/025_query_indexes.sql` (Dashboard 수동 적용 필요)
- 수정: Supabase 1,000행 상한으로 시세 조회가 잘리던 문제(`/market/adr`, 추천·섹터 주도주 OHLCV 캐시 등 6곳)
- 수정: 500 응답이 내부 예외 메시지를 노출하던 25곳을 고정 문구로 교체, 삼켜진 예외 20곳에 로깅
- 보안: PyJWT 2.13.0→2.15.0, Next 14.2.3→14.2.35. Starlette·Next 메이저 업그레이드는 보류
- 문서: `ENHANCEMENT_V2.md`, `CHANGELOG.md` 추가, 버전 표기 `2.0.0-dev`

## [1.0.0] — 2026-09-03 (태그 `v1.0.0`, 커밋 `4103060`)

고도화 착수 전 기준 버전.

- KIS API 시세·수급 수집, 듀얼 엔진 기술 분석 기반 종목 추천
- 알고리즘 가상 거래(계좌 설정, 최대 보유일 청산, 텔레그램 체결 알림)
- 시장 현황(지수 카드·트리맵·주도주 랭킹), 포트폴리오·AI 분석
- 스케줄러: 전체 동기화 4회, 09:05 섹터주도주, 09:10 추천 갱신, 09:20 텔레그램 리포트(로컬), 장중 10분 가상매매
- 보안: JWT(JWKS/ES256), 단일 사용자 화이트리스트, SlowAPI 120/min, AMPM 읽기 키, 게스트 로그인(`X-Guest-Key`)
- 운영 안정화: Render OOM 대응(httpx 싱글턴, malloc_trim, 스케줄러 중복 차단)
