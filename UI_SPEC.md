# MPM UI 정의서

> My Portfolio Manager — AI 기반 한국 주식 분석 및 포트폴리오 관리
>
> 작성 기준: 2026-06-04
> 기술 스택: Next.js 14 (App Router) + TypeScript + Tailwind CSS + lucide-react

---

## 1. 디자인 시스템

### 1.1 컬러 팔레트

| 용도 | Tailwind 클래스 | Hex | 적용 예시 |
|------|----------------|-----|---------|
| Primary | `blue-600` | `#2563EB` | 주요 버튼, 활성 탭, 브랜드 로고 |
| Primary Hover | `blue-700` | `#1D4ED8` | Primary 버튼 hover |
| 상승 (한국 관례) | `red-500` | `#EF4444` | 양수 등락률, 수익 |
| 하락 (한국 관례) | `blue-500` | `#3B82F6` | 음수 등락률, 손실 |
| 태그/배지 BG | `blue-50` | `#EFF6FF` | 종목 태그 배경 |
| 태그/배지 Text | `blue-700` | `#1D4ED8` | 종목 태그 텍스트 |
| 즐겨찾기 활성 | `yellow-400` | `#FACC15` | Star 아이콘 fill+stroke |
| 즐겨찾기 비활성 | `gray-300` | `#D1D5DB` | Star 아이콘 (빈 별) |
| ScoreBadge 강함 | `red-100 / red-700` | — | 점수 75–100 |
| ScoreBadge 보통+ | `orange-100 / orange-700` | — | 점수 50–74 |
| ScoreBadge 보통 | `yellow-100 / yellow-700` | — | 점수 25–49 |
| ScoreBadge 약함 | `gray-100 / gray-500` | — | 점수 0–24 |
| 소스 거래대금 | `slate-100 / slate-600` | — | SourceBadge |
| 소스 기관외인 | `violet-100 / violet-700` | — | SourceBadge |
| 소스 거래량 | `sky-100 / sky-700` | — | SourceBadge |
| 소스 신고가 | `amber-100 / amber-700` | — | SourceBadge |
| 소스 VI발동 | `rose-100 / rose-700` | — | SourceBadge |
| 연속 5일+ | `purple-100 / purple-700` | — | ConsecutiveBadge |
| 연속 3–4일 | `indigo-100 / indigo-700` | — | ConsecutiveBadge |
| 연속 2일 | `teal-100 / teal-700` | — | ConsecutiveBadge |
| Engine A (추세 돌파형) | `orange-100 / orange-700` | — | EngineBadge ⬆ 추세 |
| Engine B (역추세 반등형) | `sky-100 / sky-700` | — | EngineBadge ↩ 역추세 |
| Gray 50 | `gray-50` | `#F9FAFB` | 테이블 헤더, 페이지 배경 |
| Gray 100 | `gray-100` | `#F3F4F6` | 비활성 탭, 종목코드 배지 배경 |
| Gray 400 | `gray-400` | `#9CA3AF` | 로딩 텍스트, 보조 텍스트 |
| Gray 500 | `gray-500` | `#6B7280` | 테이블 헤더, 라벨 |
| Gray 600 | `gray-600` | `#4B5563` | 배지 텍스트, Nav 링크 |
| White | `white` | `#FFFFFF` | Nav 배경, 카드 배경 |

---

### 1.2 타이포그래피

| 요소 | Tailwind 클래스 | 용도 |
|------|----------------|------|
| 페이지 제목 | `text-2xl font-bold` | 각 페이지 H1 |
| 섹션 제목 | `font-semibold` | 카드 내 섹션 타이틀 |
| 지표 값 | `text-xl font-semibold` | 종목 상세 지표 카드 |
| 바디 텍스트 | `text-sm` | 테이블 셀, 버튼, 입력 |
| 종목명 | `font-medium` | 테이블 종목명 |
| 캡션/메타 | `text-xs text-gray-400` | 종목코드 부제, 날짜 |
| 레이블 | `text-xs text-gray-500` | 인풋 레이블, 지표 카드 라벨 |
| 해시태그/태그 | `text-xs` | 종목 태그 배지 |
| 소스 배지 | `text-[10px] font-semibold` | SourceBadge (10px) |
| 모노스페이스 | `font-mono` | 현재가, 등락률, 점수 등 숫자 |
| 폰트 패밀리 | `Inter` | 전체 글로벌 (next/font/google) |

---

### 1.3 공통 컴포넌트 스타일

#### 버튼

| 종류 | Tailwind 클래스 |
|------|----------------|
| Primary | `bg-blue-600 text-white px-4 py-2 rounded text-sm flex items-center gap-2 hover:bg-blue-700` |
| Disabled | `disabled:opacity-50 disabled:cursor-not-allowed` |
| Tab 활성 | `bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium` |
| Tab 비활성 | `bg-gray-100 text-gray-700 px-4 py-2 rounded text-sm font-medium` |
| 섹터 버튼 활성 | `bg-blue-600 text-white` |
| 섹터 버튼 비활성 | `bg-gray-100 text-gray-700 hover:bg-gray-200` |

#### 배지/태그

| 종류 | Tailwind 클래스 | 예시 |
|------|----------------|------|
| 종목 태그 | `bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full` | `골든크로스` |
| 엔진 배지 (A) | `text-[10px] font-bold px-1.5 py-0.5 rounded bg-orange-100 text-orange-700` | `⬆ 추세` |
| 엔진 배지 (B) | `text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-100 text-sky-700` | `↩ 역추세` |
| 소스 배지 | `text-[10px] font-semibold px-1.5 py-0.5 rounded` + 조건별 색상 | `거래대금` |
| 점수 배지 | `text-xs font-bold px-2 py-0.5 rounded font-mono` + 점수별 색상 | `82` |
| 연속 배지 | `text-xs font-semibold px-1.5 py-0.5 rounded` + 일수별 색상 | `🔁 3일` |
| 종목코드 배지 | `text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded` | `005930` |
| KOSPI 배지 | `text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded` | `KOSPI` |
| KOSDAQ 배지 | `text-xs bg-green-50 text-green-600 px-1.5 py-0.5 rounded` | `KOSDAQ` |

#### 카드

| 용도 | Tailwind 클래스 |
|------|----------------|
| 일반 카드 | `border rounded-lg p-4` |
| 지표 카드 | `border rounded-lg p-4` |
| 로그인 카드 | `bg-white p-8 rounded-lg shadow-md w-full max-w-sm` |

#### 테이블

| 요소 | Tailwind 클래스 |
|------|----------------|
| 래퍼 | `border rounded-lg overflow-hidden` |
| `<table>` | `w-full text-sm` |
| `<thead>` | `bg-gray-50 text-gray-500 text-xs uppercase` |
| `<th>` | `px-4 py-3 text-left` 또는 `text-right` |
| `<tbody>` | `divide-y` |
| `<tr>` (일반) | `hover:bg-gray-50 cursor-pointer` |
| `<td>` | `px-4 py-3` |

---

## 2. 레이아웃

### 2.1 글로벌 레이아웃

```
┌──────────────────────────────────────────────────────────────┐
│  MPM   종목   히스토리   포트폴리오   가상거래   (sticky Nav) │
│  [blue-600]   [gray-600] ...                  h-14, z-50    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│              <Page Content>                                  │
│         max-w-7xl mx-auto px-4 py-6                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**내비게이션 바**

| 요소 | 클래스 | 설명 |
|------|--------|------|
| `<nav>` | `border-b bg-white sticky top-0 z-50` | 상단 고정 |
| 내부 컨테이너 | `max-w-7xl mx-auto px-4 h-14 flex items-center gap-6` | 높이 56px |
| "MPM" 로고 | `font-bold text-lg text-blue-600` | `/`로 링크 |
| "종목" | `text-sm text-gray-600 hover:text-gray-900` | `/stocks` |
| "히스토리" | `text-sm text-gray-600 hover:text-gray-900` | `/stocks/history` |
| "포트폴리오" | `text-sm text-gray-600 hover:text-gray-900` | `/portfolio` |
| "가상거래" | `text-sm text-gray-600 hover:text-gray-900` | `/virtual` |

**인증 래퍼**: `AuthProvider`가 전체 앱을 감싸며, 미인증 상태에서 `/login`으로 redirect.

---

### 2.2 라우팅 구조

```
/                  → redirect → /stocks
/login             → 로그인 페이지 (인증 불필요)
/stocks            → 종목 목록 (추천/섹터/즐겨찾기 탭)
/stocks/history    → 추천 히스토리 (일/주/월 탭)
/stocks/[code]     → 종목 상세 페이지
/portfolio         → 포트폴리오 관리
/virtual           → 가상 거래 (계좌·포지션·체결 내역)
```

모든 페이지는 `"use client"` 클라이언트 컴포넌트. 인증 필요 페이지는 `AuthProvider`가 처리.

---

## 3. 페이지별 UI 정의

### 3.1 로그인 페이지 (`/login`)

**파일**: `frontend/src/app/login/page.tsx`

#### ASCII 와이어프레임

```
        (전체 화면 중앙, min-h-screen bg-gray-50)

                ┌──────────────────────────┐
                │           MPM            │  ← text-2xl font-bold text-blue-600
                │                          │
                │  [이메일              ]  │
                │  [비밀번호            ]  │
                │                          │
                │  ✗ 오류 메시지 (조건부)  │  ← text-red-500 text-sm
                │                          │
                │  [        로그인        ] │  ← bg-blue-600
                └──────────────────────────┘
                  bg-white p-8 rounded-lg shadow-md max-w-sm
```

#### 상태 관리

| 상태 | 타입 | 설명 |
|------|------|------|
| `email` | `string` | 이메일 입력값 |
| `password` | `string` | 비밀번호 입력값 |
| `error` | `string` | 인증 오류 메시지 |
| `loading` | `boolean` | 로그인 요청 진행 중 |

#### 동작

- `handleLogin()`: Supabase `signInWithPassword()` 호출
- 성공 시 `/stocks`로 `router.replace()`
- 실패 시 `error` 표시
- `loading` 중 버튼 비활성화 + 텍스트 "로그인 중..."

---

### 3.2 종목 목록 페이지 (`/stocks`)

**파일**: `frontend/src/app/stocks/page.tsx`

#### ASCII 와이어프레임

```
주식 종목
기준일: 2026-05-28  생성: 05/28 16:10  가격 갱신: 05/28 16:40

[🔍 종목명 검색...        ] ← debounce 300ms, 결과 드롭다운

[오늘의 추천▌] [섹터 주도주] [즐겨찾기 (3)]

─── 오늘의 추천 탭 ────────────────────────────────────────────
┌──────────┬──────────┬────────┬──────────┬──────┬──────┬──────────────┬──┐
│ 종목명   │  현재가  │ 등락률 │  추천가  │ 거래량│ 점수 │     태그     │  │
├──────────┼──────────┼────────┼──────────┼──────┼──────┼──────────────┼──┤
│ 삼성전자 │  74,200  │ +2.35% │ 73,000   │14.2M │  82  │ [골든크로스] │★│
│ 005930   │          │(red)   │  +1.6%   │      │ +5📄 │ [신고가근접] │  │
│[거래대금][기관외인] [🔁3일]                                              │
├──────────┼──────────┼────────┼──────────┼──────┼──────┼──────────────┼──┤
│ SK하이닉스│182,500  │ -1.20% │ 185,000  │ 5.1M │  65  │ [HBM]        │☆│
│ 000660   │          │(blue)  │  -1.3%   │      │      │              │  │
│[거래량]                                                                  │
└──────────┴──────────┴────────┴──────────┴──────┴──────┴──────────────┴──┘

─── 섹터 주도주 탭 ────────────────────────────────────────────
[전체▌] [반도체(AI/HBM)] [온디바이스 AI] [2차전지 소재·장비] ...
         (20개 섹터 버튼, flex-wrap)

         [↺ 새로 불러오기]   ← force refresh

┌──────┬──────────┬──────────┬────────┬───────┬────────┬──────┬──────────┐
│ 순위 │  종목명  │  현재가  │ 등락률 │ 거래대금│ 시총  │ 점수 │ 구성     │
├──────┼──────────┼──────────┼────────┼───────┼────────┼──────┼──────────┤
│  👑  │ 삼성전자 │  74,200  │ +2.35% │ 1.2조  │450조   │  95  │거30상30정│
│  🥈  │ SK하이닉스│182,500  │ -1.20% │ 3,200억│120조   │  72  │거22상18  │
│  🥉  │ ...      │          │        │        │        │      │          │
└──────┴──────────┴──────────┴────────┴───────┴────────┴──────┴──────────┘

─── 즐겨찾기 탭 ────────────────────────────────────────────────
(추천 목록에 있는 즐겨찾기 → 기존 데이터 사용)
(추천 목록에 없는 즐겨찾기 → KIS API 실시간 조회 후 동일 테이블로 표시)
```

#### 인라인 컴포넌트

**ScoreBadge**

```tsx
// 기술점수 + 리포트 보너스를 합산 표시
<span className={`text-xs font-bold px-2 py-0.5 rounded font-mono ${color}`}>{점수}</span>
{fund > 0 && <span className="text-xs text-emerald-600 font-semibold">+{fund}📄</span>}
```

| 점수 범위 | 색상 |
|---------|------|
| 75–100 | `bg-red-100 text-red-700` |
| 50–74 | `bg-orange-100 text-orange-700` |
| 25–49 | `bg-yellow-100 text-yellow-700` |
| 0–24 | `bg-gray-100 text-gray-500` |

**SourceBadges** — 종목이 선정된 조건 표시 (거래대금/기관외인/거래량/신고가/VI발동)

**ConsecutiveBadge** — 연속 2일 이상 추천 시 `🔁 N일` 표시

**EntryPriceBadge** — 추천가 + 현재가 대비 수익률 (연속 추천이면 "최초"로 표시)

**NaverLink (N ↗)** — 종목명 셀 하단에 네이버 증권 바로가기 링크 표시

```tsx
<a
  href={`https://finance.naver.com/item/main.naver?code=${stock_code}`}
  target="_blank"
  rel="noopener noreferrer"
  onClick={e => e.stopPropagation()}  // 행 클릭(상세 이동) 버블링 방지
  className="inline-flex items-center gap-0.5 text-[10px] font-bold
             text-green-700 bg-green-50 hover:bg-green-100 px-1.5 py-0.5 rounded"
>
  N <ExternalLink className="w-2.5 h-2.5" />
</a>
```

- StockTable(오늘의 추천·즐겨찾기): 종목코드·시장 배지 옆에 표시
- SectorLeaderTable(섹터 주도주): 종목코드·시장·태그 행 끝에 표시, 점수 구성 하단에 분석 점수(tech_score / A / B / tech_tags) 배지 추가 표시
- 포트폴리오 보유 종목: `<Link>` 바깥에 배치 (중첩 `<a>` 금지)

**SectorLeaderTable 순위 아이콘**

| 순위 | 아이콘 |
|------|--------|
| 1 | 👑 |
| 2 | 🥈 |
| 3 | 🥉 |

#### 상태 관리

| 상태 | 타입 | 설명 |
|------|------|------|
| `tab` | `"recommend" \| "favorites" \| "sector"` | 활성 탭 (URL `?tab=` 파라미터와 동기화) |
| `stocks` | `StockSummary[]` | 오늘의 추천 종목 |
| `loading` | `boolean` | 추천 종목 로딩 |
| `generatedAt` | `string \| null` | 추천 생성 시각 |
| `pricesUpdatedAt` | `string \| null` | 가격 갱신 시각 |
| `searchQuery` | `string` | 검색어 |
| `searchResults` | `StockMaster[]` | 검색 결과 (stock_master 기반) |
| `selectedSector` | `string` | 선택된 섹터 ("전체" 포함) |
| `sectorData` | `Record<string, SectorLeaderStock[]>` | 섹터별 주도주 캐시 |
| `sectorLoading` | `boolean` | 섹터 데이터 로딩 |
| `favoriteStocks` | `StockSummary[]` | 즐겨찾기 종목 (비추천 종목 실시간 조회 포함) |

#### 실시간 갱신

- 마운트 시 `GET /api/v1/stocks/recommend/prices` 즉시 호출
- **30초 인터벌** `setInterval`로 현재가/등락률 자동 갱신
- 탭 비활성화 시에도 갱신 계속됨

#### 검색 동작

- 입력 시 debounce 300ms → `GET /api/v1/stocks/search?q=...` 호출
- 결과 드롭다운 표시 (stock_master 기반, KOSPI/KOSDAQ 배지)
- 항목 클릭 시 `/stocks/{code}` 이동, 검색창 초기화

---

### 3.3 종목 상세 페이지 (`/stocks/[code]`)

**파일**: `frontend/src/app/stocks/[code]/page.tsx`

#### ASCII 와이어프레임

```
← 목록으로              ★ 즐겨찾기 추가

종목 상세 — 삼성전자 (005930) [KOSPI]
74,200원  ▲ +1,700 (+2.35%)    조회: 05/28 16:40

┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
│ 기준가│ 시가 │ 고가 │ 저가 │상한가│하한가│52주高│52주低│
│73,000│73,500│75,100│73,200│94,900│51,100│87,800│55,700│
└──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘

┌──────────────┬──────────────┬──────────────┬──────────────┐
│ 시가총액     │ 거래대금     │ 외국인보유율  │              │
│ 442.9조      │ 1.2조        │ 54.3%        │              │
├──────────────┼──────────────┼──────────────┼──────────────┤
│   PER        │   PBR        │   ROE        │ 구름 위치    │
│   15.4배     │   1.20배     │   8.5%       │ above_cloud  │
├──────────────┴──────────────┴──────────────┴──────────────┤
│    EPS: 4,821원         BPS: 61,834원                     │
└──────────────────────────────────────────────────────────┘

┌─ 기술적 분석 (종합 점수) ────────────────────────────────┐
│  점수: 82점  ████████░░  [매우 강함]                      │
│                                                           │
│  [추세 A: 8/10] [모멘텀 B: 7/10]                         │
│  [변동성 C: 5/10] [거래량 D: 6/10]                        │
│                                                           │
│  [골든크로스] [MACD 상향돌파] [거래량 급증] [전고점 돌파] │
└───────────────────────────────────────────────────────────┘

┌─ 일목균형표 ─────────────────────────────────────────────┐
│  전환선   73,500   │   기준선   72,000                    │
│  선행스팬A 71,500  │   선행스팬B 70,000                   │
│  현재 위치: 구름대 위 (above_cloud)                       │
└───────────────────────────────────────────────────────────┘

┌─ 기대 수익률 분석 ──────────────────────────────────────┐
│  섹터: 반도체  │  섹터 PER: 18.5  │  COE: 8.2%          │
│  목표가(PER): 89,200원  │  목표가(PBR): 74,800원         │
│  목표가: 89,200원  (+20.2%)  손절가: 70,500원 (-5%)       │
│  기대가치: +12.5%  │  리스크/리워드: 2.4                  │
│  ┌────────────────────────────────┐                      │
│  │  판정: 진입 승인 ✅             │                      │
│  │  사유: 목표가 대비 충분한 상승  │                      │
│  └────────────────────────────────┘                      │
└───────────────────────────────────────────────────────────┘

┌─ 수익률 분석 ───────────────────────────────────────────┐
│  [퀀트 분석▌]  [배당 분석]                               │
│                                                           │
│  [분석 실행]  or  [새로고침]                             │
│                                                           │
│  종합 점수: 78점   방향: 중립                            │
│  모멘텀: 8/10  가치: 6/10  변동성: 5/10                  │
│  판정: 진입 승인 / 사유: ...                             │
└───────────────────────────────────────────────────────────┘
```

#### 상태 관리

| 상태 | 타입 | 설명 |
|------|------|------|
| `detail` | `StockDetail \| null` | 종목 상세 데이터 |
| `loading` | `boolean` | 로딩 여부 |
| `strategyType` | `"quant" \| "dividend"` | 수익률 분석 탭 선택 |
| `analysis` | `StrategyAnalysisData \| null` | 분석 결과 |
| `analysisLoading` | `boolean` | 분석 실행 중 |

#### 주요 섹션 상세

**가격 정보 그리드** (`grid grid-cols-4 md:grid-cols-8`)

| 항목 | 필드 |
|------|------|
| 기준가 | `price_info.ref_price` |
| 시가 | `price_info.open` |
| 고가 | `price_info.high` |
| 저가 | `price_info.low` |
| 상한가 | `price_info.upper_limit` |
| 하한가 | `price_info.lower_limit` |
| 52주 최고 | `price_info.w52_high` |
| 52주 최저 | `price_info.w52_low` |

**기본 지표 카드** (`grid grid-cols-2 md:grid-cols-4`)

| 라벨 | 필드 | null/음수 처리 |
|------|------|--------------|
| PER | `metrics.per` | ≤ 0 또는 null → `"N/A"` |
| PBR | `metrics.pbr` | null → `"N/A"` |
| ROE | `metrics.roe` | null → `"N/A"` |
| 구름 위치 | `ichimoku.position` | — |

**기술적 분석 패널**

- 종합 점수 프로그레스 바 (0–100)
- 강도 등급: 매우 강함(75+) / 강함(50+) / 보통(25+) / 약함
- 카테고리 4개 점수: 추세 A / 모멘텀 B / 변동성 C / 거래량 D (각 0–10점)
- 매수 신호 태그 배지 목록

**기대 수익률 분석 패널**

| 항목 | 필드 |
|------|------|
| 목표가(PER) | `expected_return.target_price_per` |
| 목표가(PBR) | `expected_return.target_price_pbr` |
| 최종 목표가 | `expected_return.target_price` |
| 상승 여력 | `expected_return.target_upside` |
| 손절가 | `expected_return.stop_loss` |
| 기대가치 | `expected_return.expected_value` |
| 리스크/리워드 | `expected_return.risk_reward` |
| 판정 | `expected_return.verdict` (진입 승인 ✅ / 진입 보류 ⚠️) |

**수익률 분석 (퀀트/배당 탭)**

- `GET /api/v1/analysis/{code}?strategy_type=quant|dividend`
- 퀀트: 종합 점수, 방향 힌트, 모멘텀/가치/변동성 3개 팩터
- 배당: GGM 기대수익률, 배당수익률, D0/D1, 성장률, 안정성 점수/등급

---

### 3.4 추천 히스토리 페이지 (`/stocks/history`)

**파일**: `frontend/src/app/stocks/history/page.tsx`

#### ASCII 와이어프레임

```
추천 종목 히스토리

[일별▌]  [주별]  [월별]

─── 일별 탭 ─────────────────────────────────────────────────
▼ 2026-05-28 (10개)           ← 클릭으로 접기/펼치기
  1  삼성전자  005930  +2.35%  [골든크로스] [신고가근접]
  2  SK하이닉스 000660 -1.20%  [HBM]
  ...

▶ 2026-05-27 (10개)           ← 접힘 상태

▼ 2026-05-26 (10개)
  ...

─── 주별 탭 ─────────────────────────────────────────────────
▼ 2026-W21 (10개)
  (주간 빈도 집계 상위 10종목)

─── 월별 탭 ─────────────────────────────────────────────────
▼ 2026-05 (10개)
  (월간 빈도 집계 상위 10종목)
```

#### PeriodCard 컴포넌트

- 헤더: 기간 키 + 종목 수 + 펼침/접힘 아이콘
- 기본 상태: 최신 1개는 펼침, 나머지는 접힘
- 종목 행: 순위 번호 | 종목명/코드 | 등락률 | 태그 상위 2개

#### 탭별 데이터

| 탭 | API 파라미터 | 최대 표시 |
|----|------------|---------|
| 일별 | `period_type=daily` | 최근 7일 |
| 주별 | `period_type=weekly` | 최근 4주 |
| 월별 | `period_type=monthly` | 최근 6개월 |

---

### 3.5 포트폴리오 페이지 (`/portfolio`)

**파일**: `frontend/src/app/portfolio/page.tsx`

#### ASCII 와이어프레임

```
포트폴리오                              [+ 종목 추가]

── 프로필 선택기 ─────────────────────────────────────────────
[전체] [📊 퀀트 프로필 ✎ ✕] [💰 배당 프로필 ✎ ✕] [+ 새 프로필]

── 요약 카드 (4열 그리드) ────────────────────────────────────
┌──────────────┬──────────────┬──────────────┬──────────────┐
│  총 매입금액  │  총 평가금액  │  총 평가손익  │   총 수익률  │
│  10,500,000  │  11,200,000  │  +700,000    │   +6.67%     │
│              │              │  (red)       │   (red)      │
└──────────────┴──────────────┴──────────────┴──────────────┘

── 보유 비중 차트 ─────────────────────────────────────────────
     ┌─────────────────────────────────────────────┐
     │  [Donut Chart (SVG)]  │ ■ 삼성전자  45.2%   │
     │                       │ ■ SK하이닉스 30.1%  │
     │                       │ ■ NAVER     24.7%   │
     └─────────────────────────────────────────────┘

── AI 포트폴리오 분석 ──────────────────────────────────────────
▼ AI 포트폴리오 분석  [갱신 필요 배지]  [분석 시작 / 새로고침]

  (분석 텍스트 마크다운 렌더링)
  **📊 퀀트 프로필의 포트폴리오 분석 보고서**
  ...

── 종목 추가 폼 (토글) ──────────────────────────────────────────
▼ 종목 추가
  [종목코드] [종목명] [평균단가] [수량] [메모] [프로필 선택▼]
                                                [추가]

── 보유 종목 테이블 ─────────────────────────────────────────────
┌──────────┬──────────┬────────┬──────────┬──────┬──────────┬──────────┬──────────┬──────────┬────┐
│ 종목명   │  현재가  │ 등락률 │ 평균단가 │  수량│  매입금액│  평가금액│  평가손익│  수익률  │    │
├──────────┼──────────┼────────┼──────────┼──────┼──────────┼──────────┼──────────┼──────────┼────┤
│삼성전자  │  74,200  │ +2.35% │  73,000  │  100 │7,300,000 │7,420,000 │ +120,000 │  +1.6%   │✎ ✕│
│005930    │          │ (red)  │          │      │          │          │  (red)   │  (red)   │[매도]│
│[반도체]  │  KOSPI   │        │          │      │          │          │          │          │    │
├──────────┼──────────┴────────┴──────────┴──────┴──────────┴──────────┴──────────┴──────────┴────┤
│  (매도 분석 패널 - 펼침 시)                                                                      │
│  매도 점수: 32점  ████░░░░░░  [주의]                                                            │
│  수익률: +1.6%  │  비중: 66.2%                                                                  │
│  활성 신호: [PBR 고평가] [포트폴리오 과중]                                                       │
│  매도 가격대: 손절 69,350 / 67,160 / 65,000 │ 목표 109,500 / 146,000 │ 52주高 87,800           │
├──────────┼──────────┬────────┬──────────┬──────┬──────────┬──────────┬──────────┬──────────┬────┤
│ ...      │          │        │          │      │          │          │          │          │    │
├──────────┼──────────┼────────┼──────────┼──────┼──────────┼──────────┼──────────┼──────────┼────┤
│ 합계     │          │        │          │      │10,500,000│11,200,000│ +700,000 │  +6.67%  │    │
└──────────┴──────────┴────────┴──────────┴──────┴──────────┴──────────┴──────────┴──────────┴────┘
```

#### 프로필 선택기

| 요소 | 설명 |
|------|------|
| "전체" 버튼 | `profile_id` 필터 없이 전체 보유 종목 조회 |
| 프로필 버튼 | 이름 + 분석 유형 아이콘 (퀀트: 📊, 배당: 💰) |
| 편집 아이콘 | hover 시 표시, 이름 인라인 편집 |
| 삭제 아이콘 | hover 시 표시, 확인 없이 즉시 삭제 |
| "+ 새 프로필" | 인라인 폼 토글 (이름 + 분석 유형 선택) |

#### 요약 카드

```
grid grid-cols-2 md:grid-cols-4 gap-4
```

| 항목 | 필드 | 색상 조건 |
|------|------|---------|
| 총 매입금액 | `HoldingSummary.total_purchase` | — |
| 총 평가금액 | `HoldingSummary.total_eval` | — |
| 총 평가손익 | `HoldingSummary.total_profit_loss` | 양수: red, 음수: blue |
| 총 수익률 | `HoldingSummary.total_profit_rate` | 양수: red, 음수: blue |

#### 보유 비중 차트 (Donut Chart)

- SVG로 직접 구현 (외부 라이브러리 미사용)
- 호버 시 종목명 + 비중 % 툴팁
- 우측 범례: 색상 블록 + 종목명 + 비중%
- 기준: `eval_amount` (평가금액) 기반 비중 계산

#### AI 포트폴리오 분석 패널

| 상태 | 표시 |
|------|------|
| 미분석 | "분석 시작" 버튼 |
| 분석 있음 + 최신 | "새로고침" 버튼 |
| 분석 있음 + 구버전 | "갱신 필요" 배지 + "새로고침" 버튼 |
| 분석 중 | 로딩 스피너 |

- 갱신 조건: 보유 종목 변경(hash 불일치) 또는 날짜 변경
- 분석 텍스트는 마크다운 형식으로 렌더링 (굵기, 이모지 등)
- 프로필 `analysis_type`에 따라 퀀트/배당 프롬프트 분기

#### 보유 종목 테이블

**헤더 열**

| 열 | 정렬 | 설명 |
|----|------|------|
| 종목명 | left | 이름 + 코드 + 섹터/유형 배지 |
| 현재가 | right | `font-mono` |
| 등락률 | right | 색상 조건부 (red/blue) |
| 평균단가 | right | `font-mono` |
| 수량 | right | — |
| 매입금액 | right | — |
| 평가금액 | right | — |
| 평가손익 | right | 색상 조건부 |
| 수익률 | right | 색상 조건부 |
| 액션 | — | 편집/삭제/매도분석 버튼 |

**인라인 편집**: 편집 아이콘 클릭 시 평균단가, 수량, 메모, 프로필 셀이 인풋으로 전환

**합계 행** (`<tfoot>`): 매입금액, 평가금액, 평가손익, 수익률 합계

#### 매도 분석 패널 (SellAnalysisPanel)

각 종목 행 아래 토글형 패널:

```
매도 점수: 32점  ██████░░░░  [주의]
수익률: +1.6%  │  비중: 66.2%

활성 매도 신호:
  기술적  [MA 데드크로스]
  기본적  [PBR 고평가]
  자산관리 [포트폴리오 비중 초과]

매도 가격대:
  손절가    -5%: 69,350원   -10%: 67,160원   -15%: 65,000원
  트레일링  고점: 87,800원  -7%: 81,654원    -10%: 79,020원
  목표가    PER×15: 72,315원  PER×20: 96,420원  PER×25: 120,525원
  참고      52주 최고: 87,800원
```

**매도 등급**

| 점수 | 등급 | 색상 |
|------|------|------|
| 0–20 | 관망 | green |
| 21–40 | 주의 | yellow |
| 41–65 | 매도 검토 | orange |
| 66–100 | 즉시 매도 | red |

**신호 카테고리 색상**

| 카테고리 | 배지 색상 |
|---------|---------|
| 기술적 | `blue-100 text-blue-700` |
| 기본적 | `purple-100 text-purple-700` |
| 자산관리 | `orange-100 text-orange-700` |

---

### 3.6 가상 거래 페이지 (`/virtual`)

**파일**: `frontend/src/app/virtual/page.tsx`

#### ASCII 와이어프레임

```
가상 거래

[+ 새 계좌]

── 계좌 목록 ─────────────────────────────────────────────
┌──────────────────────────────────────────────────────────────┐
│  📈 성장형 계좌  [both · 최소 50점 · 최대 5종목]  ✎  ✕      │
│                                                              │
│  잔고: 8,420,000원  │  평가금액: 10,200,000원  │  +21.5%    │
│  보유: 3종목  │  승률: 66.7%                               │
│                                                              │
│  [포지션 보기▌]  [체결 내역]  [성과]                        │
│                                                              │
│  ─ 포지션 탭 ──────────────────────────────────────────────│
│  ┌──────────┬──────────┬────────┬──────────┬──────────────┐│
│  │ 종목명   │  현재가  │ 수익률 │  평가금액 │    매입가    ││
│  ├──────────┼──────────┼────────┼──────────┼──────────────┤│
│  │삼성전자  │  74,200  │ +8.2%  │2,226,000 │  68,600      ││
│  │ Engine A │ 매수일:05/20 │ 진입점수:82 │        │        ││
│  └──────────┴──────────┴────────┴──────────┴──────────────┘│
│                                                              │
│  ─ 체결 내역 탭 ────────────────────────────────────────────│
│  ┌────────┬──────────┬──────┬────────┬──────┬─────────────┐│
│  │ 날짜   │ 종목명   │ 구분 │  체결가 │ 수량 │ 손익        ││
│  ├────────┼──────────┼──────┼────────┼──────┼─────────────┤│
│  │05/28   │삼성전자  │ 매도 │ 78,000 │  30  │ +282,000    ││
│  │        │          │      │        │      │ (take_profit)││
│  │05/20   │삼성전자  │ 매수 │ 68,600 │  30  │  —          ││
│  └────────┴──────────┴──────┴────────┴──────┴─────────────┘│
└──────────────────────────────────────────────────────────────┘
```

#### 계좌 설정 폼 (인라인 토글)

| 필드 | 타입 | 기본값 |
|------|------|--------|
| 계좌명 | text | "가상 계좌" |
| 전략 | select (engine_a / engine_b / both / both_and) | both |
| 초기 자금 | number | 10,000,000 |
| 점수 필터 유형 | select (gte / lte / range) | gte |
| 최소 점수 | number | 50 |
| 최대 점수 | number \| null | — |
| 최대 종목 수 | number | 5 |
| 종목당 투자 비율(%) | number | 20 |
| 손절 기준(%) | number | 10 |
| 익절 기준(%) | number | 20 |
| 최대 보유 일수 | number \| null | — |
| 대형주 제외 | boolean | false |
| 대형주 시총 임계값(억) | number \| null | — |
| 고유동성 제외 | boolean | false |
| 거래대금 임계값(억) | number \| null | — |

#### 체결 내역 trigger_type 표시

| trigger_type | 표시 |
|---|---|
| `algo_buy` | 알고리즘 매수 |
| `stop_loss` | 손절 |
| `take_profit` | 익절 |
| `sell_signal` | 매도신호 |
| `manual` | 수동 |
| `atr_hard_stop` | ATR 하드스탑 |
| `atr_trailing_stop` | ATR 트레일링 |
| `rsi_exhaustion` | RSI 모멘텀소멸 |
| `entry_low_breach` | 진입저점이탈 |
| `time_limit_stop` | 보유기간초과 |
| `ma20_half_exit` | MA20 분할익절 |
| `target_reached` | 목표도달 |
| `max_hold_exit` | 최대보유일 청산 |

#### 날짜·시간 표시

체결 내역 날짜 셀: `created_at`(UTC) → KST 변환 후 `YYYY-MM-DD`(상단) + `HH:MM`(하단 회색) 2행 표시.

#### 상태 관리

| 상태 | 타입 | 설명 |
|------|------|------|
| `accounts` | `VirtualAccount[]` | 가상 계좌 목록 |
| `selectedAccount` | `number \| null` | 선택된 계좌 ID |
| `activeTab` | `"positions" \| "trades" \| "performance"` | 서브탭 |
| `positions` | `VirtualPosition[]` | 보유 포지션 |
| `trades` | `VirtualTrade[]` | 체결 내역 |

---

### 3.7 시장 현황 페이지 (`/market`)

**파일**: `frontend/src/app/market/page.tsx`

#### 탭 구조

```
[대시보드▌] [주도주 랭킹] [히트맵]
```

모든 탭은 `next/dynamic`으로 지연 로딩.

---

#### 대시보드 탭 (`MarketDashboard.tsx`)

```
기준: 09:30:15          [새로고침]
──────────────────────────────────────
국내 지수
┌──────────┐ ┌──────────┐
│  KOSPI   │ │  KOSDAQ  │
│ 2,850.12 │ │  840.55  │
│▲ 12.34(+0.44%)│ │▼ 2.10(-0.25%)│
└──────────┘ └──────────┘

미국 지수
┌──────────┐ ┌──────────┐ ┌──────────┐
│  NASDAQ  │ │ 다우존스 │ │ S&P 500  │
│19,234.56 │ │42,100.00 │ │ 5,820.10 │
│▲ 88.40   │ │▼ -30.00  │ │▲ 15.20  │
└──────────┘ └──────────┘ └──────────┘

환율·원자재·금리
┌──────────┐ ┌──────────┐ ┌──────────┐
│ USD/KRW  │ │ WTI 유가 │ │미국 10년물│
│ 1,380.50 │ │  $78.45  │ │  4.32%   │
│▲ 2.30    │ │▼ -0.62   │ │▲ 0.05   │
└──────────┘ └──────────┘ └──────────┘

수급 현황 (상위 50종목)
┌──────────┐ ┌──────────┐ ┌──────────┐
│외국인순매수│ │기관 순매수│ │개인 순매수│
│ +1,520천주│ │ +230천주  │ │ -1,750천주│
└──────────┘ └──────────┘ └──────────┘
```

**IndexCard 컴포넌트 props**

| prop | 타입 | 설명 |
|------|------|------|
| `item` | `MarketIndexItem` | 지수 데이터 |
| `prefix` | string | 값 앞 기호 (예: `$`) |
| `suffix` | string | 값 뒤 기호 (예: `%`) |
| `decimals` | number | 소수점 자리수 (기본 2) |

**색상 규칙**

| sign 값 | 의미 | 텍스트 | 배경 |
|---------|------|--------|------|
| `"1"`, `"2"` | 상승 | `text-red-600` | `bg-red-50` |
| `"4"`, `"5"` | 하락 | `text-blue-600` | `bg-blue-50` |
| `"3"` 외 | 보합 | `text-gray-500` | `bg-gray-50` |

**상태 관리**

| 상태 | 타입 | 설명 |
|------|------|------|
| `indices` | `MarketIndices \| null` | 8개 지수 데이터 |
| `investor` | `InvestorTrend \| null` | 수급 집계 |
| `loading` | `boolean` | 로딩 중 여부 |
| `fetchedAt` | `Date \| null` | 마지막 조회 시각 |

---

#### 주도주 랭킹 탭 (`MarketRankings.tsx`)

```
┌────────────────────────┐ ┌────────────────────────┐
│ 📈 상승률 상위          │ │ 📉 하락률 상위          │
│ # 종목명    현재가 등락률 지표│ │ # 종목명    현재가 등락률 지표│
│ 1 한화에어로 1,041,000 +8.2% ...│ │ ...                    │
│ 2 ...       ...      ...  │ │ ...                    │
└────────────────────────┘ └────────────────────────┘
┌────────────────────────┐ ┌────────────────────────┐
│ 📊 거래량 상위          │ │ 💰 거래대금 상위        │
│ ...                    │ │ ...                    │
└────────────────────────┘ └────────────────────────┘
(... 8개 카테고리 2열 그리드)
```

**RankCard 컴포넌트**

- 헤더: 아이콘 + 카테고리명
- 테이블: 순위 · 종목명(코드) · 현재가 · 등락률 · 카테고리 지표
- 등락률 색상: 양수 `text-red-600`, 음수 `text-blue-600`

**SECTIONS 설정 (8개)**

| 키 | 제목 | 지표 컬럼 |
|----|------|-----------|
| `rise` | 상승률 상위 | 거래량 |
| `fall` | 하락률 상위 | 거래량 |
| `volume` | 거래량 상위 | 거래량 |
| `amount` | 거래대금 상위 | 거래대금(억) |
| `foreign_buy` | 외인 순매수 | 순매수(주) |
| `institution_buy` | 기관 순매수 | 순매수(주) |
| `high_52w` | 52주 신고가 | 신고가 |
| `low_52w` | 52주 신저가 | 신저가 |

**상태 관리**

| 상태 | 타입 | 설명 |
|------|------|------|
| `rankings` | `MarketRankings \| null` | 랭킹 데이터 |
| `loading` | `boolean` | 로딩 중 여부 |

---

## 4. 전역 상태 & 훅

### 4.1 `AuthProvider` / `useSession`

**파일**: `frontend/src/components/AuthProvider.tsx`

- Supabase `onAuthStateChange` 구독으로 세션 감지
- 세션 없으면 `/login`으로 redirect (단, `/login` 페이지 자체는 예외)
- `AuthContext`로 세션 정보를 하위 컴포넌트에 제공
- `useSession()` hook으로 세션 접근

### 4.2 `useFavorites` 훅

**파일**: `frontend/src/hooks/useFavorites.ts`  
**저장소**: Supabase `favorites` 테이블 (로컬/배포 환경 공유)

**API**

| 반환값 | 타입 | 설명 |
|--------|------|------|
| `favorites` | `string[]` | 즐겨찾기 종목코드 배열 |
| `favoriteNames` | `Record<string, string>` | 코드 → 종목명 맵 |
| `loaded` | `boolean` | 초기 로드 완료 여부 |
| `toggle(code, name?)` | `void` | 추가/삭제 (Optimistic UI) |
| `isFavorite(code)` | `boolean` | 포함 여부 |

**동작 방식**

- 마운트 시 `api.getFavorites()` → 상태 초기화 → `loaded = true`
- `toggle()`: 상태 즉시 변경(Optimistic) → `api.addFavorite()` / `api.removeFavorite()` 비동기 호출
- API 실패 시 에러 무시 (catch(() => {}))

---

## 5. API 연동 (`frontend/src/lib/api.ts`)

**인증**: 모든 API 요청에 Supabase JWT Bearer 토큰 자동 추가

```ts
const token = (await supabase.auth.getSession()).data.session?.access_token;
headers: { Authorization: `Bearer ${token}` }
```

**API 함수 목록**

| 함수 | HTTP | 엔드포인트 | 설명 |
|------|------|-----------|------|
| `getRecommendations()` | GET | `/api/v1/stocks/recommend` | 오늘의 추천 종목 |
| `getRecommendationPrices()` | GET | `/api/v1/stocks/recommend/prices` | 현재가 갱신 (30초 폴링) |
| `getStockDetail(code)` | GET | `/api/v1/stocks/{code}/detail` | 종목 상세 |
| `searchStocks(q)` | GET | `/api/v1/stocks/search?q=` | 종목명 검색 |
| `getHistory(type)` | GET | `/api/v1/stocks/history?period_type=` | 추천 히스토리 |
| `getFavorites()` | GET | `/api/v1/stocks/favorites` | 즐겨찾기 목록 |
| `addFavorite(code, name)` | POST | `/api/v1/stocks/favorites` | 즐겨찾기 추가 |
| `removeFavorite(code)` | DELETE | `/api/v1/stocks/favorites/{code}` | 즐겨찾기 삭제 |
| `getSectorLeader(sector, force)` | GET | `/api/v1/stocks/sector-leader?sector=&force=` | 섹터 주도주 |
| `getAllSectorLeaders()` | GET | `/api/v1/stocks/sector-leader/all` | 전체 섹터 일괄 조회 |
| `getHoldings(profileId?)` | GET | `/api/v1/holdings?profile_id=` | 보유 종목 |
| `addHolding(body)` | POST | `/api/v1/holdings` | 보유 종목 추가 |
| `updateHolding(id, body)` | PUT | `/api/v1/holdings/{id}` | 보유 종목 수정 |
| `deleteHolding(id)` | DELETE | `/api/v1/holdings/{id}` | 보유 종목 삭제 |
| `getSellAnalysis(id)` | GET | `/api/v1/holdings/{id}/sell-analysis` | 매도 분석 |
| `getProfiles()` | GET | `/api/v1/profiles` | 프로필 목록 |
| `createProfile(body)` | POST | `/api/v1/profiles` | 프로필 생성 |
| `updateProfile(id, body)` | PUT | `/api/v1/profiles/{id}` | 프로필 수정 |
| `deleteProfile(id)` | DELETE | `/api/v1/profiles/{id}` | 프로필 삭제 |
| `getPortfolioAnalysis(profileId)` | GET | `/api/v1/portfolio/analysis?profile_id=` | AI 분석 조회 |
| `requestPortfolioAnalysis(body)` | POST | `/api/v1/portfolio/analysis` | AI 분석 요청 |
| `getStrategyAnalysis(code, type)` | GET | `/api/v1/analysis/{code}?strategy_type=` | 퀀트/배당 분석 |

---

## 6. 타입 정의 주요 인터페이스

| 인터페이스 | 설명 |
|-----------|------|
| `StockSummary` | 종목 요약 (코드, 이름, 가격, 점수, 태그, 연속일, 추천가, 소스 조건) |
| `StockDetail` | 종목 상세 (가격정보, 지표, 기대수익률, 일목균형표, 기술분석) |
| `PriceInfo` | 가격 관련 정보 (OHLC, 상하한가, 52주, 시가총액, EPS/BPS) |
| `ExpectedReturn` | 기대수익률 (목표가, 손절가, 기대가치, R/R, 판정) |
| `TechnicalSignals` | 기술 지표 27개 (MA, MACD, RSI, Stoch, BB, OBV 등) |
| `Profile` | 투자 프로필 (이름, analysis_type: quant\|dividend) |
| `Holding` | 보유 종목 (매입·평가 금액, 손익, 수익률 포함) |
| `SellAnalysis` | 매도 분석 (점수, 등급, 신호 목록, 매도 가격대) |
| `SellLevels` | 매도 가격대 (손절 3단계, 트레일링 2단계, 목표가 3단계, 52주 고가) |
| `HoldingSummary` | 포트폴리오 합계 |
| `HistoryEntry` | 기간별 추천 히스토리 (period_key, stocks 배열) |
| `PortfolioAnalysis` | AI 분석 텍스트 + updated_at |
| `StrategyAnalysisData` | 퀀트/배당 분석 결과 (팩터 점수 또는 배당 지표) |
| `SectorLeaderStock` | 섹터 주도주 (순위, 섹터 점수, 점수 구성, MA 정보, tech_score/engine_a_score/engine_b_score/tech_tags) |
| `StockMaster` | 전체 종목 마스터 (코드, 이름, 시장) |
| `MarketIndexItem` | 지수 카드 1개 (label, price, change, change_rate, sign) |
| `MarketIndices` | 8개 지수 키-값 맵 (kospi/kosdaq/nasdaq/dow/sp500/usd_krw/crude_oil/us10y) |
| `RankingStock` | 랭킹 종목 (stock_code, stock_name, current_price, change_rate + 카테고리별 지표) |
| `MarketRankings` | 8개 카테고리 키-배열 맵 (rise/fall/volume/amount/foreign_buy/institution_buy/high_52w/low_52w) |

---

## 7. 반응형 대응

| 브레이크포인트 | 적용 요소 | 변화 |
|-------------|---------|------|
| 기본 (< 768px) | 지표 카드 그리드 | `grid-cols-2` |
| md (≥ 768px) | 지표 카드 그리드 | `grid-cols-4` |
| 기본 | 요약 카드 | `grid-cols-2` |
| md | 요약 카드 | `grid-cols-4` |
| 기본 | 가격 정보 | `grid-cols-4` |
| md | 가격 정보 | `grid-cols-8` |
| 기본 | 섹터 버튼 | `flex-wrap` (줄바꿈) |
| 기본 | 검색바/태그 | `flex-wrap` |
| — | 테이블 | `overflow-hidden` (모바일 열 잘림 가능성 있음) |

---

## 8. UX 규칙

| 규칙 | 적용 위치 | 설명 |
|------|---------|------|
| 로딩 텍스트 | 모든 페이지 | "불러오는 중..." (py-20 text-center text-gray-400) |
| 실시간 갱신 | 종목 목록 | 30초 인터벌로 현재가/등락률 자동 갱신 |
| Optimistic UI | 즐겨찾기 토글 | 상태 즉시 변경 후 API 비동기 호출 |
| 버블링 방지 | 즐겨찾기 셀 | `e.stopPropagation()`으로 행 클릭(페이지 이동) 차단 |
| URL 상태 동기화 | 종목 탭 | `?tab=` 쿼리 파라미터로 탭 상태 유지 |
| 뒤로가기 상태 유지 | 종목 상세 | 이전 탭·목록 위치 복원 |
| 검색 debounce | 종목 검색 | 300ms 지연 후 API 호출 |
| 숫자 포맷 | 전체 | `.toLocaleString()`으로 천단위 콤마 |
| 음수 PER 처리 | 종목 상세 | `per <= 0` → `"N/A"` 표시 |
| null 값 처리 | 지표 카드 | null → `"N/A"` 문자열 |
| 조건부 색상 | 등락률/손익 | 양수: `text-red-500`, 음수: `text-blue-500` |
| 인증 게이트 | 전체 앱 | AuthProvider가 미인증 사용자를 `/login`으로 redirect |

---

## 9. 컴포넌트 구조도

```
frontend/src/
├── app/
│   ├── layout.tsx              ← 글로벌 레이아웃 (Nav + AuthProvider)
│   ├── globals.css
│   ├── page.tsx                ← / → /stocks redirect
│   ├── login/
│   │   └── page.tsx            ← 로그인 (Supabase auth)
│   ├── stocks/
│   │   ├── page.tsx            ← 종목 목록 (추천/섹터/즐겨찾기 탭)
│   │   ├── history/
│   │   │   └── page.tsx        ← 추천 히스토리 (일/주/월 탭)
│   │   └── [code]/
│   │       └── page.tsx        ← 종목 상세 (지표·기술분석·기대수익·전략분석)
│   └── portfolio/
│       └── page.tsx            ← 포트폴리오 (프로필·차트·AI분석·보유종목·매도분석)
├── components/
│   ├── AuthProvider.tsx         ← Supabase 세션 관리, 인증 redirect
│   ├── stocks/
│   │   ├── StockTable.tsx       ← 종목 테이블 래퍼
│   │   ├── StockRow.tsx         ← 종목 행 (tr 단위)
│   │   └── FavoriteButton.tsx   ← Star 아이콘 즐겨찾기 버튼
│   └── charts/
│       └── CandleChart.tsx      ← 캔들차트 (lightweight-charts, 준비 상태)
├── hooks/
│   ├── useFavorites.ts          ← Supabase DB 기반 즐겨찾기 훅
│   └── useProfile.ts            ← 투자 프로필 상태 관리 훅
└── lib/
    ├── api.ts                   ← API 함수 (JWT 자동 첨부)
    ├── supabase.ts              ← Supabase 클라이언트 싱글턴
    └── types.ts                 ← TypeScript 인터페이스 정의
```

---

## 10. 향후 개선 고려 사항

| 항목 | 현황 | 개선 방향 |
|------|------|---------|
| CandleChart 통합 | 컴포넌트 구현됨, 미적용 | 종목 상세에 OHLCV 캔들차트 추가 |
| 테이블 모바일 대응 | `overflow-hidden` (열 잘림) | `overflow-x-auto` 또는 카드형 레이아웃 |
| 로딩 UI | 텍스트 "불러오는 중..." | 스켈레톤 UI 또는 스피너 |
| 에러 경계 | 조건부 렌더링 의존 | React Error Boundary 또는 Next.js error.tsx |
| 포트폴리오 테이블 모바일 | 열 수 많아 모바일 불편 | 반응형 카드형 레이아웃 전환 |
