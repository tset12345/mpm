# MPM — My Portfolio Manager

> AI 기반 한국 주식 포트폴리오 관리 시스템 · 1인 개발 · 개인 이용 중

한국투자증권(KIS) 실시간 API 데이터와 Google Gemini AI를 연동해 종목을 분석하고 포트폴리오를 관리합니다.  
직접 투자 판단에 활용하기 위해 만들었고, 지금도 실제로 사용하고 있습니다.

---

## 왜 만들었나

주식 포트폴리오를 관리하면서 "지금 이 종목을 사도 되는가"를 판단할 때 여러 지표를 일일이 확인해야 했습니다.  
실시간 데이터를 한 화면에서 보고, AI가 분석해주는 툴을 원했는데 맞는 게 없어서 직접 만들었습니다.

---

## 주요 기능

- **실시간 시세 조회** — KIS Open API 연동, 현재가·등락률·거래량
- **듀얼 엔진 기술 분석** — 자체 설계 알고리즘으로 매수·매도 시그널 산출
- **AI 포트폴리오 분석** — Google Gemini 2.5 Flash Lite 기반 자동 분석 리포트
- **종목 추천** — 기술 분석 점수 기반 일일 종목 스크리닝
- **가상 거래 시뮬레이션** — 알고리즘 자동 매수·매도 백테스트
- **텔레그램 알림** — 추천 종목·매매 체결 실시간 알림

---

## 스크린샷

> 추가 예정

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI (Python 3.11), APScheduler |
| Database | Supabase (PostgreSQL) |
| AI | Google Gemini 2.5 Flash Lite |
| 증권 API | 한국투자증권 KIS Open API |
| 인프라 | Render (BE), Vercel (FE) |

---

## 아키텍처

```
KIS Open API ──▶ FastAPI (백엔드)
                    ├── APScheduler (평일 4회 정기 동기화)
                    ├── 듀얼 엔진 기술 분석 알고리즘
                    └── Gemini AI 분석 요청
                         ↓
                    Supabase (PostgreSQL)
                         ↓
                    Next.js 14 (프론트엔드)
                    ├── 대시보드 (차트·위젯)
                    ├── 종목 추천 및 섹터 주도주
                    └── 포트폴리오·가상거래 현황
```

---

## 보안

| 계층 | 조치 |
|------|------|
| API 인증 | Supabase JWT(Bearer) 검증, ES256/HS256 알고리즘 고정 |
| 사용자 화이트리스트 | `ALLOWED_USER_EMAIL` 설정 시 해당 계정만 허용 |
| 외부 앱 인증 | `X-AMPM-Key` / `X-Guest-Key` 헤더 — 읽기 전용(GET 한정) |
| Rate Limiting | SlowAPI 120 req/min |
| CORS | `ALLOWED_ORIGINS` 설정 도메인만 허용 |
| RLS | 모든 Supabase 테이블 RLS 활성화 |

---

## 빠른 시작

```bash
cp backend/.env.example backend/.env  # 환경변수 설정
./dev.sh                              # 백엔드 + 프론트엔드 실행
```

상세 설치 가이드 → [00_OVERVIEW.md](00_OVERVIEW.md)

---

## 문서

| 파일 | 내용 |
|------|------|
| [00_OVERVIEW.md](00_OVERVIEW.md) | 프로젝트 소개, 기술스택, 빠른시작, 환경변수 |
| [01_HISTORY.md](01_HISTORY.md) | 개발 이력, 의사결정 기록, 알고리즘 성능 현황 |
| [FEATURES.md](FEATURES.md) | 화면별 기능 명세 |
| [ALGORITHM.md](ALGORITHM.md) | 듀얼 엔진 기술 분석 알고리즘 상세 |
| [UI_SPEC.md](UI_SPEC.md) | 프론트엔드 컴포넌트 상세 |
| [backend/API.md](backend/API.md) | API 레퍼런스 |

---

> 1인 개발 프로젝트입니다. 실제 투자 판단에 활용 중이며 지속적으로 개선하고 있습니다.
