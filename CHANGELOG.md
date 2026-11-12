# Changelog

버전 규칙과 고도화 계획은 `ENHANCEMENT_V2.md` 참조.

## [Unreleased] — v2.0.0 (브랜치 `release/v2.0.0`)

### 화면 버전 표시 (2026-11-12)

- 추가: 상단 메뉴 오른쪽에 프론트엔드 버전과 빌드 커밋 표시(`v2.0.0-dev · abc1234`). 버전은 `package.json`, 커밋은 Vercel 빌드 커밋(로컬은 git)에서 빌드 시 주입. 좁은 화면에서는 숨김

### 보안 패치 — Next 메이저 업그레이드 (2026-11-12, 미배포)

- 보안: Next 14.2.35→15.5.29, React 18→19, lucide-react 0.379→1.72. Next 14 계열에 남아 있던 critical(Image Optimization API RCE 등) 해소. 남은 high는 Next 내부 고정 postcss 1건(빌드 시 CSS 처리용)
- 변경: `/stocks/[code]`가 `params` prop 대신 `useParams()` 사용 (Next 15에서 `params`가 Promise로 바뀜)
- 검증: `tsc --noEmit`, `next build`, vitest 25개 통과. 브라우저 동작 확인은 아직

### 2.0.0-alpha.2 — 2단계: 단일 인스턴스 최적화 (2026-10-21)

- 성능: KIS 호출 단일 진입점 + 전역 속도·동시성 제한 + 재시도(`KIS_MAX_RPS`, `KIS_MAX_CONCURRENCY`)
- 성능: `AsyncTTLCache`(동시 요청 병합·장애 시 만료 값 대체)로 시장 지표·추천·현재가·종목 상세 캐시. `/stocks/recommend` 캐시 후 3.3s → 0.1ms
- 성능: 비동기 핸들러·스케줄러의 동기 DB 호출을 스레드풀로 이동(이벤트 루프 차단 해소). 매매 트리거 중 헬스체크가 멈추던 문제 해소
- 성능: 포지션 조회 쿼리 일괄화, ADR 계산 이차 복잡도 제거
- 변경: 레이트리밋을 IP 300/분·사용자 600/분·게스트(IP별) 120/분·고비용 작업 6/분으로 재설계, `RATE_LIMIT_*`·`TRUSTED_PROXY_HOPS` 환경변수 추가, `slowapi` 제거, 429에 `Retry-After`
- 추가: 프론트 SWR 훅(폴링·탭 숨김 시 중단·재시도 정책), `ApiError`, `ErrorNotice`·`Skeleton`, vitest 25개
- 수정: 추천 목록 조회 실패가 빈 화면으로 보이던 문제(오류 안내 + 다시 시도), 추천 표가 렌더링마다 재마운트되던 문제
- 수정: 처리되지 않은 500 응답에 CORS 헤더가 없어 브라우저가 막던 문제, `Retry-After`·`X-Request-ID` CORS 노출
- 수정: 매매 트리거가 스레드에서 돌 때 텔레그램 알림이 유실될 수 있던 문제
- 테스트: 백엔드 185개(커버리지 50%), 프론트 25개, Chrome E2E 12개

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
