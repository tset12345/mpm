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
