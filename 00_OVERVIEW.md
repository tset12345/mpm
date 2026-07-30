# MPM — 프로젝트 개요

> 이 문서: 한줄 소개, 기술스택, 빠른시작, 환경변수, 비용 최적화, 문서 색인.  
> 상세 기능 명세 → `FEATURES.md` | API 레퍼런스 → `backend/API.md` | 알고리즘 → `ALGORITHM.md`

---

## 한줄 소개

AI 기반 한국 주식 포트폴리오 관리 시스템. 실시간 KIS API 데이터 + 듀얼 엔진 기술 분석으로 종목을 추천하고, Gemini AI로 포트폴리오를 분석한다.

- 매일 장 마감 후(16:10 KST) 4개 카테고리 기술적 분석(0–100점)으로 거래량 상위 종목을 자동 스코어링·선별
- 보유 종목을 Gemini AI로 퀀트·배당 전략별 맞춤 분석 제공
- Supabase(PostgreSQL)에 결과를 캐싱해 불필요한 API 호출 최소화
- 알고리즘 가상 거래 시뮬레이션 (Engine A 추세 돌파 / Engine B 역추세 반등)

> **리포트 기능(PDF 업로드·네이버 금융 스크래핑)은 [ARA](../ara) 프로젝트로 분리되었습니다.**

---

## 기술 스택

| 구분 | 기술 | 용도 |
|------|------|------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS | 웹 UI |
| Backend | FastAPI (Python 3.11), APScheduler | REST API, 스케줄러 |
| Database | Supabase (PostgreSQL) | 데이터 저장·캐싱 |
| AI | Google Gemini 2.5 Flash Lite | 포트폴리오 분석 |
| 증권 API | 한국투자증권 KIS Open API | 주가·OHLCV·거래량 |
| 알림 | Telegram Bot API | 추천 리포트·가상 거래 알림 (로컬 전용) |

---

## 문서 색인

| 파일 | 내용 |
|------|------|
| `00_OVERVIEW.md` (이 파일) | 프로젝트 소개, 기술스택, 빠른시작, 환경변수 |
| `01_HISTORY.md` | 개발 이력, 의사결정 기록, 알고리즘 성능 현황 |
| `FEATURES.md` | 화면별 기능 명세 (최신 상태 유지) |
| `ALGORITHM.md` | 듀얼 엔진 기술 분석 알고리즘 상세 |
| `UI_SPEC.md` | 프론트엔드 컴포넌트 상세 |
| `backend/API.md` | API 공식 레퍼런스 (전 엔드포인트·응답 예시) |
| `06_PLANS.md` | 미구현 기능 계획 (양방향 텔레그램 봇 등) |
| `archive/MPM_INITIAL_SPEC.md` | 초기 기획서 (참고용, 현재 구현과 불일치) |

---

## 빠른 시작 (Quick Start)

### 사전 준비

| 항목 | 버전 / 링크 |
|------|------------|
| Python | 3.11 이상 |
| Node.js | 18 이상 |
| Supabase 프로젝트 | [supabase.com](https://supabase.com) |
| KIS Developers 앱키 | [apiportal.koreainvestment.com](https://apiportal.koreainvestment.com) |
| Google AI Studio API 키 | [aistudio.google.com](https://aistudio.google.com) |

### 설치 및 실행

```bash
# 1. 저장소 클론 후 프로젝트 루트로 이동
cd /path/to/mpm

# 2. 백엔드 환경 변수 파일 복사 후 값 채우기
cp backend/.env.example backend/.env
# → backend/.env를 편집기로 열어 각 값 입력 (아래 환경 변수 섹션 참고)

# 3. DB 스키마 적용 — Supabase Dashboard > SQL Editor에서
#    supabase/migrations/ 폴더의 SQL 파일을 001부터 번호 순서대로 실행

# 4. 개발 서버 전체 실행
./dev.sh
```

실행 후:
- 백엔드 API: http://localhost:8000
- 프론트엔드: http://localhost:3000
- API 문서 (Swagger): http://localhost:8000/docs

### dev.sh / check.sh 명령어

| 명령어 | 설명 |
|--------|------|
| `./dev.sh` | 백엔드 + 프론트엔드 전체 실행 |
| `./dev.sh -b` | 백엔드만 실행 (포트 8000) |
| `./dev.sh -f` | 프론트엔드만 실행 (포트 3000) |
| `./check.sh` | FE + BE 상태 확인 |
| `./check.sh --reboot --be` | 백엔드 재시작 (caffeinate -si 슬립 방지 포함) |
| `./check.sh --reboot --fe` | 프론트엔드만 재시작 (PORT=3000 고정) |
| `./check.sh --close` | FE + BE 전체 종료 |

> **포트 3001 주의**: `check.sh`는 포트 3001을 절대 종료하지 않음 (ARA 프로젝트 전용).

---

## 환경 변수

### 백엔드 (`backend/.env`)

| 변수명 | 설명 | 발급처 |
|--------|------|--------|
| `KIS_APP_KEY` | KIS Open API 앱키 | [KIS Developers](https://apiportal.koreainvestment.com) > 앱 등록 |
| `KIS_APP_SECRET` | KIS Open API 앱 시크릿 | 동일 (앱키와 함께 발급) |
| `KIS_ACCOUNT_NO` | 증권 계좌번호 (8자리-2자리) | 한국투자증권 계좌 |
| `KIS_IS_MOCK` | `false` 권장 (true 시 거래량 순위 미지원 → 폴백 동작) | — |
| `GEMINI_API_KEY` | Google Gemini API 키 | [Google AI Studio](https://aistudio.google.com) > Get API Key |
| `SUPABASE_URL` | Supabase 프로젝트 URL | Supabase > Project Settings > API |
| `SUPABASE_SERVICE_KEY` | Supabase service_role 키 (비공개 유지) | 동일 > service_role |
| `SUPABASE_JWT_SECRET` | JWT 서명 시크릿 (인증 검증용) | Supabase > Settings > API > JWT Secret |
| `DATABASE_URL` | PostgreSQL 직접 연결 URL (참고용) | Supabase > Database > Connection string |
| `ALLOWED_ORIGINS` | CORS 허용 출처 (쉼표 구분) | 기본값: `http://localhost:3000` |
| `ALLOWED_USER_EMAIL` | 허용할 사용자 이메일 (단일 화이트리스트) | — |
| `AMPM_API_KEY` | AMPM Android 앱 전용 읽기 키 (X-AMPM-Key 헤더) | — |
| `ENABLE_SCHEDULER` | 일일 동기화 스케줄러 | 기본값: `false` |
| `ENABLE_INTRADAY` | 장중 10분 매매 트리거 (로컬 전용) | 기본값: `false` |
| `ENABLE_TELEGRAM` | 텔레그램 알림 (로컬 전용, Render 미설정) | 기본값: `false` |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 API 토큰 | `@BotFather`에서 발급 |
| `TELEGRAM_CHAT_ID` | 메시지 수신 chat_id | 봇에 메시지 전송 후 `getUpdates`로 확인 |

### 프론트엔드 (`frontend/.env.local`)

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `NEXT_PUBLIC_API_URL` | 백엔드 API 주소 | `http://localhost:8000` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase 프로젝트 URL | Supabase > Project Settings > API |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon 키 | 동일 > anon public |

### 환경별 플래그 요약

| 변수 | 로컬 | Render |
|------|------|--------|
| `ENABLE_SCHEDULER` | `false` | `true` |
| `ENABLE_INTRADAY` | `true` | `false` |
| `ENABLE_TELEGRAM` | `true` | 미설정 (자동 비활성) |
| `KIS_IS_MOCK` | `false` | `false` |

---

## 비용 최적화

| 항목 | 전략 |
|------|------|
| **Gemini API** | holdings_hash 일치 시 DB 캐시 반환 — 보유 구성 변경 시만 호출 |
| **KIS API** | 장 마감 후 1회만 수집 (16:10 KST), 이후 요청은 DB에서 제공 |
| **Supabase** | OHLCV 2년치만 보관, `delete_old_ohlcv()` 함수로 자동 정리 |
| **Rate limit** | OHLCV 종목 간 0.5초 딜레이로 KIS API 속도 제한 준수 |
| **Render OOM** | httpx·Yahoo Finance 공유 싱글턴 + `gc.collect()` + `malloc_trim(0)` |
