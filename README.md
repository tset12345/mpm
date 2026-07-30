# MPM — My Portfolio Manager

AI 기반 한국 주식 포트폴리오 관리 시스템. 실시간 KIS API 데이터 + 듀얼 엔진 기술 분석으로 종목을 추천하고, Gemini AI로 포트폴리오를 분석한다.

---

## 문서

| 파일 | 내용 |
|------|------|
| [00_OVERVIEW.md](00_OVERVIEW.md) | 프로젝트 소개, 기술스택, 빠른시작, 환경변수 |
| [01_HISTORY.md](01_HISTORY.md) | 개발 이력, 의사결정 기록, 알고리즘 성능 현황 |
| [FEATURES.md](FEATURES.md) | 화면별 기능 명세 (최신 상태 유지) |
| [ALGORITHM.md](ALGORITHM.md) | 듀얼 엔진 기술 분석 알고리즘 상세 |
| [UI_SPEC.md](UI_SPEC.md) | 프론트엔드 컴포넌트 상세 |
| [backend/API.md](backend/API.md) | API 공식 레퍼런스 (전 엔드포인트) |
| [06_PLANS.md](06_PLANS.md) | 미구현 기능 계획 |

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI (Python 3.11), APScheduler |
| Database | Supabase (PostgreSQL) |
| AI | Google Gemini 2.5 Flash Lite |
| 증권 API | 한국투자증권 KIS Open API |

---

## 빠른 시작

```bash
cp backend/.env.example backend/.env  # 환경변수 설정
./dev.sh                              # 백엔드 + 프론트엔드 실행
```

상세 설치 가이드 → [00_OVERVIEW.md](00_OVERVIEW.md)

> **리포트 기능**은 [ARA](../ara) 프로젝트로 분리되었습니다.

---

## 보안

| 계층 | 조치 |
|------|------|
| API 인증 | Supabase JWT(Bearer) 검증, ES256/HS256 알고리즘 고정 |
| 사용자 화이트리스트 | `ALLOWED_USER_EMAIL` 설정 시 해당 계정만 허용 |
| AMPM 앱 | X-AMPM-Key 헤더 읽기 전용 (GET/HEAD/OPTIONS) |
| Rate Limiting | SlowAPI 120 req/min |
| CORS | `ALLOWED_ORIGINS` 설정 도메인만 허용 |
| RLS | 모든 Supabase 테이블 RLS 활성화 (`020_enable_rls.sql`) |
