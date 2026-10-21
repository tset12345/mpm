# MPM — 개발 이력

> 이 문서: "어떻게 지금 상태에 이르렀는가" — append-only 의사결정 기록, 단계별 구현 이력, 버그 수정, 성능 현황.  
> "현재 무엇이 맞다"는 이 문서에서 다루지 않음 — 스펙은 `FEATURES.md`, `ALGORITHM.md`, `backend/API.md` 참조.

---

## 단계별 구현 이력

### Phase 0 — 초기 기획
- MPM.md 기획서 작성: 단일 앱에 리포트 수집·요약 + 포트폴리오 관리 통합 구상
- 인프라 선정: KIS Open API(무료) + Gemini 1.5 Flash(무료 쿼터) + Supabase Free Tier(500MB) + Render Free
- 초기 DB 설계: `stock_recommendations`, `stock_ohlcv`, `reports` 테이블
- 초기 기획서는 `archive/MPM_INITIAL_SPEC.md`로 이관 (현재 구현과 불일치 — ARA 분리 전, Gemini 1.5 Flash 기재)

### Phase 1 — 핵심 기능 구현
- KIS Open API 연동: 실시간 주가·OHLCV·거래량 순위 수집
- 듀얼 엔진 기술 분석 설계 및 구현 (Engine A: 추세 돌파 / Engine B: 역추세 반등, 0–100점)
- APScheduler로 평일 4회 자동 수집 파이프라인 구축 (08:50 / 11:00 / 14:00 / 16:10 KST)
- Supabase 마이그레이션 001~009 적용 (기본 테이블·프로필·포트폴리오 분석)
- Gemini 모델 업그레이드: 1.5 Flash → 2.5 Flash Lite

### Phase 2 — ARA 분리
**결정**: 리포트 수집·PDF 업로드·네이버 금융 스크래핑 기능을 별도 ARA 프로젝트로 분리

- **이유**: MPM은 포트폴리오·종목 추천에 집중, 리포트 수집은 독립 서비스로 분리하여 관심사 분리
- MPM DB의 `reports`, `keyword_subscriptions` 테이블은 ARA 전용으로 이관 (Supabase DB는 공유)
- ARA FE 포트 3001, BE 포트 8001 — `check.sh`에서 3001 종료 금지 규칙 추가

### Phase 3 — 가상 거래 시스템 (마이그레이션 019~021)
- `virtual_accounts`, `virtual_positions`, `virtual_trades` 테이블 설계
- Engine A 청산: ATR 하드 스탑, ATR 트레일링 스탑, RSI 모멘텀 소멸
- Engine B 청산: 진입 저점 이탈, 보유기간 초과+손실, MA20 분할 익절, 목표 도달
- `both_and` 전략 추가 (Engine A AND B 동시 조건 충족 필요)
- `score_filter_type` (gte/lte/range), `max_hold_days`, `filter_excl_*` 계좌 설정 추가
- `extract_loss_trades.py` 작성하여 손실 패턴 분석

### Phase 4 — 시장 현황·수급 기능
- `market.py` 라우터 신규: 8개 지수 카드, 주도주 랭킹(52주 신고가·신저가 포함), 트리맵 히트맵, 지수 차트, 수급, ADR, 스파크라인
- 섹터 주도주 20개 테마 + 기술 점수(`tech_score`, `engine_a/b_score`, `tech_tags`) 추가
- `sector_leaders` 테이블, 마이그레이션 017 적용

### Phase 5 — 보안 강화 (2026-07-16)
- `backend/app/core/auth.py` 전면 재설계
  - Supabase JWKS(ES256) 자동 조회 + 1시간 캐싱, fallback HS256
  - `kid` 존재 여부로 알고리즘 분기 (algorithm confusion 방지)
  - AMPM Android 앱용 `X-AMPM-Key` 헤더 인증 추가 (읽기 전용, GET/HEAD/OPTIONS만 허용)
  - `ALLOWED_USER_EMAIL` 단일 사용자 화이트리스트
- SlowAPI Rate Limiting: 120 req/min 글로벌 적용
- 공급망 감사 스크립트: `backend/security_audit.sh` (pip-audit CVE 스캔)
- IDOR 방어: 리소스 수정·삭제 시 소유권(user_id) 검증

### Phase 6 — Render OOM 수정 (2026-07)
- **증상**: Render Free Tier 512MB RSS 한도 초과로 인스턴스 반복 재시작
- **원인 분석**:
  - `httpx.AsyncClient` per-request 생성 → KIS API 호출마다 새 SSL context → RSS 단조 증가
  - Yahoo Finance도 동일 패턴
  - 스케줄러 재시작 시 `run_daily_sync()` 중복 실행
- **수정 내용**:
  - `KISApiClient._get_http()` 공유 싱글턴 도입 (`kis_api.py`)
  - `_get_yahoo_client()` 모듈 레벨 싱글턴 (`market.py`)
  - `_sync_running` 플래그 + `misfire_grace_time=30` (`scheduler.py`)
  - sync 완료 후 `gc.collect()` + `malloc_trim(0)` 호출

---

### Phase 7 — v2.0.0 고도화 1단계: 품질 기반 (2026-10)

v1.0.0(`4103060`) 태그 이후 `release/v2.0.0` 브랜치에서 진행. 계획·진행 상태는 `ENHANCEMENT_V2.md`.

- **테스트·CI (A1):** 백엔드 단위 테스트 119개(기술 분석·매도 신호·일목균형표·기대수익률·인증·가상거래·페이지네이션·에러 처리). 가상거래는 메모리 가짜 Supabase로 DB 없이 검증. GitHub Actions에서 pytest + 프론트 `tsc` + 의존성 감사 실행
- **로깅·에러 (A2):** 요청 ID 컨텍스트 로깅, `LOG_FORMAT=json` 지원, 표준 500 응답. 라우터 25곳이 `str(e)`로 내부 예외 메시지를 응답에 노출하던 것을 고정 문구로 교체하고 원인은 로그로 이동. 로그 없이 예외를 삼키던 20곳에 로깅 추가
- **데이터 정확성 (A3):** Supabase(PostgREST)가 한 요청에 1,000행까지만 돌려주는데 `stock_ohlcv` 다종목 조회 6곳이 이를 고려하지 않았다. 실측으로 최근 70일 5,131행 중 1,000행만 반환되어 `/market/adr`이 오래된 5일치로만 계산됨을 확인. `fetch_all()` 페이지네이션으로 수정(ADR 4개 → 44개 지점). 추천 알고리즘·섹터 주도주의 OHLCV 캐시 조회도 같은 원인으로 최근 데이터가 빠졌을 가능성이 있어 함께 수정
- **인덱스 (A3):** `025_query_indexes.sql` 추가 (Dashboard 수동 적용 필요)
- **모니터링·보안 (G2):** 인증 필요 `/api/v1/health/detail`(DB·데이터 최신성·스케줄러·메모리). PyJWT 2.13.0→2.15.0(인증 경로 취약점 14건), Next 14.2.3→14.2.35

### Phase 8 — v2.0.0 고도화 2단계: 단일 인스턴스 최적화 (2026-10)

- **KIS 호출(B3):** 모듈마다 따로 있던 `Semaphore(5)`로는 전체 한도를 지킬 수 없어 `KISApiClient._get()` 한 곳에서 속도(실전 15/s)·동시성(8)을 제한하고 429/5xx/네트워크 오류를 재시도
- **캐시(B1):** `AsyncTTLCache` 도입. 같은 키의 동시 요청은 로더를 한 번만 실행하고, 로더가 실패하면 만료된 값을 대신 돌려주며, 키 수에 상한을 둬 메모리를 고정한다. 클라이언트 폴링 비용이 접속자 수가 아니라 종목 수에 비례하게 됨
- **이벤트 루프(B2):** 비동기 핸들러 안의 동기 Supabase 호출 약 30곳을 `run_blocking`(스레드풀)으로 이동. 특히 일일 동기화의 가상 매매 트리거(순차 DB 호출 수십 회)가 서버 전체를 멈추던 것을 해소. 스레드에서 텔레그램 알림이 사라지지 않도록 메인 루프 전달을 추가
- **레이트리밋(D2):** SlowAPI의 IP 단일 한도를 IP·사용자·게스트·고비용 작업 단계로 교체
- **프론트(F1):** SWR·`ApiError`·공용 오류 안내. 추천 표 재마운트 제거. CORS 노출 헤더와 500 응답 CORS 헤더 수정

## 알고리즘 성능 현황 (2026-06-25 기준)

`extract_loss_trades.py` 실행 결과:

| 지표 | 값 |
|------|-----|
| 손실 건수 | 74건 |
| 총 손실금액 | -4,387,012원 |
| 평균 손익률 | -9.01% |
| 최대 손실률 | -42.51% |
| trigger_type | **전체 100% stop_loss** (Engine A/B 조기청산 미발동 또는 미기록) |

### 개선 검토 포인트

1. stop_loss 기준 10% 도달 전 Engine 청산 조건이 충분히 먼저 작동하는지 확인
2. 74건의 매수점수 분포로 최적 min_score 재산정
3. 단기 손절(1~3일) vs 장기 보유 후 손절 패턴 분석
4. Engine A vs Engine B 손실률 비교

> 알고리즘 상세 (배점 테이블·진입/청산 조건) → `ALGORITHM.md`

---

## 주요 의사결정 기록

| 시점 | 결정 | 이유 |
|------|------|------|
| Phase 0 | Gemini 1.5 Flash 선정 | 무료 쿼터(RPM 15, RPD 1,500) 내 운용 가능 |
| Phase 1 | Gemini 2.5 Flash Lite로 업그레이드 | 성능 개선, 무료 쿼터 유지 |
| Phase 2 | ARA 분리 | MPM은 포트폴리오 집중, 리포트는 독립 서비스 |
| Phase 3 | Engine B `time_limit_stop` 5봉 설정 | 장기 보유 기회비용 방지 |
| Phase 3 | `both_and` 전략 추가 | 신호 필터링 강화 요구 |
| Phase 5 | ES256 JWKS 검증 채택 | Supabase 기본 알고리즘, algorithm confusion 방지 |
| Phase 5 | X-AMPM-Key 읽기 전용 제한 | AMPM 앱은 조회만 필요, 쓰기 노출 최소화 |
| Phase 6 | httpx 싱글턴 도입 | per-request SSL context 누적 → OOM 방지 |
| Phase 7 | 다종목 시세 조회를 `fetch_all()` 페이지네이션으로 통일 | PostgREST 1,000행 상한으로 조용히 잘림. 정렬 키가 유일해야 페이지 경계 누락이 없음 |
| Phase 7 | 500 응답 `detail`을 고정 문구로 변경 | 내부 예외 메시지(DB 오류 등) 노출 방지. 프론트는 `detail`을 쓰지 않아 영향 없음 |
| Phase 8 | 캐시 로더 실패 시 만료 값을 일정 시간 대신 사용 | KIS·외부 API 장애 중에도 화면이 빈 값으로 바뀌지 않게 함. 빈 결과는 캐시하지 않음 |
| Phase 8 | 레이트리밋을 앱 전역 의존성 + 인증 후 사용자별 한도로 분리 | 인증 전에는 IP, 인증 후에는 신원 기준. 게스트 키는 공유되므로 IP를 키에 포함 |
| Phase 8 | 레이트리밋·캐시는 프로세스 메모리 유지 | 현재 단일 인스턴스. 다중 인스턴스는 Redis(E1) 단계에서 |
| Phase 7 | Starlette 1.x·Next 16.x 메이저 업그레이드는 보류 | FastAPI 0.118이 Starlette <0.49로 고정, Next는 App Router 전반 영향. 별도 항목으로 분리 |
