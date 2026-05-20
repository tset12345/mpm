# MPM UI 정의서

> My Portfolio Manager — AI 기반 한국 주식 분석 및 포트폴리오 관리
>
> 작성 기준: 2026-05-15  
> 기술 스택: Next.js 15 (App Router) + Tailwind CSS + lucide-react + lightweight-charts

---

## 1. 디자인 시스템

### 1.1 컬러 팔레트

| 용도 | Tailwind 클래스 | Hex 색상 | 적용 예시 |
|------|----------------|---------|---------|
| Primary | `blue-600` | `#2563EB` | 주요 버튼, 활성 탭, 브랜드 로고, 검색 버튼, 뒤로가기 링크 |
| Primary Hover | `blue-700` | `#1D4ED8` | Primary 버튼 hover 상태 |
| Success | `green-600` | `#16A34A` | 업로드 버튼 배경 |
| Success Hover | `green-700` | `#15803D` | 업로드 버튼 hover 상태 |
| Success BG | `green-50` | `#F0FDF4` | 업로드 성공 메시지 배경 |
| Success Border | `green-200` | `#BBF7D0` | 업로드 성공 메시지 테두리 |
| Success Text | `green-700` | `#15803D` | 업로드 성공 메시지 텍스트 |
| Danger (상승) | `red-500` | `#EF4444` | 양수 등락률 (한국 주식 관례: 상승=빨간색) |
| Danger BG | `red-50` | `#FEF2F2` | 업로드 에러 메시지 배경 |
| Danger Border | `red-200` | `#FECACA` | 업로드 에러 메시지 테두리 |
| Danger Text | `red-600` | `#DC2626` | 업로드 에러 메시지 텍스트 |
| Danger State | `red-400` | `#F87171` | 에러 상태 페이지 텍스트 |
| Blue (하락) | `blue-500` | `#3B82F6` | 음수 등락률 (한국 주식 관례: 하락=파란색) |
| Tag BG | `blue-50` | `#EFF6FF` | 종목 태그 배경, 키워드 해시태그 배경 |
| Tag Text | `blue-700` | `#1D4ED8` | 종목 태그 텍스트, 키워드 해시태그 텍스트 |
| Favorite Active | `yellow-400` | `#FACC15` | 즐겨찾기 활성 Star 아이콘 (fill + stroke) |
| Gray 50 | `gray-50` | `#F9FAFB` | 테이블 헤더 배경, 업로드 섹션 헤더 배경 |
| Gray 100 | `gray-100` | `#F3F4F6` | 비활성 탭 배경, 종목코드 배지 배경 |
| Gray 200 | `gray-200` | `#E5E7EB` | 에러 메시지 테두리 (red-200 사용) |
| Gray 300 | `gray-300` | `#D1D5DB` | 즐겨찾기 비활성 Star 아이콘 |
| Gray 400 | `gray-400` | `#9CA3AF` | 종목코드 부제, 날짜 구분자("~"), 로딩 텍스트 |
| Gray 500 | `gray-500` | `#6B7280` | 테이블 헤더 텍스트, 리포트 메타 텍스트, key_points |
| Gray 600 | `gray-600` | `#4B5563` | 종목코드 배지 텍스트, Nav 링크 |
| Gray 700 | `gray-700` | `#374151` | 비활성 탭 텍스트, one_line AI 요약 텍스트 |
| Gray 900 | `gray-900` | `#111827` | Nav 링크 hover 색상 |
| White | `white` | `#FFFFFF` | 내비게이션 배경, 활성 탭/버튼 텍스트, 차트 배경 |

---

### 1.2 타이포그래피

| 요소 | Tailwind 클래스 | 용도 |
|------|----------------|------|
| 페이지 제목 | `text-2xl font-bold` | 각 페이지의 H1 ("주식 종목", "리포트 검색", "종목 상세 — {code}") |
| 섹션 제목 | `font-semibold` | 일목균형표 섹션 타이틀 |
| 지표 값 | `text-xl font-semibold` | 종목 상세 지표 카드 (PER, PBR, ROE, 구름 위치) |
| 바디 텍스트 | `text-sm` | 테이블 셀, 버튼 텍스트, 인풋, 리포트 카드 제목, one_line 요약 |
| 종목명 | `font-medium` | 테이블 종목명, 리포트 카드 제목 |
| 캡션/메타 | `text-xs text-gray-400` | 종목코드 부제, 리포트 발행사/날짜 |
| 레이블 | `text-xs text-gray-500` | 인풋 필드 레이블, 지표 카드 라벨, 테이블 헤더 |
| 해시태그/태그 | `text-xs` | 종목 태그 배지, 키워드 해시태그 |
| 모노스페이스 | `font-mono` | 현재가, 등락률, 거래량 (숫자 정렬 일관성) |
| 폰트 패밀리 | `Inter` | 전체 글로벌 폰트 (next/font/google) |

---

### 1.3 공통 컴포넌트 스타일

#### 버튼

| 상태 | Tailwind 클래스 | 설명 |
|------|----------------|------|
| Primary (검색) | `bg-blue-600 text-white px-4 py-2 rounded text-sm flex items-center gap-2 hover:bg-blue-700` | 검색 버튼 |
| Success (업로드) | `bg-green-600 text-white px-4 py-2 rounded text-sm flex items-center gap-2 hover:bg-green-700` | 업로드 버튼 |
| Disabled | `disabled:opacity-50 disabled:cursor-not-allowed` | 파일 미선택 또는 업로드 중인 경우 적용 |
| Tab Active | `bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium` | 활성 탭 버튼 |
| Tab Inactive | `bg-gray-100 text-gray-700 px-4 py-2 rounded text-sm font-medium` | 비활성 탭 버튼 |
| Collapsible Header | `w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 text-left font-medium text-sm` | 업로드 섹션 접힘/펼침 토글 버튼 |

#### 인풋 필드

| 종류 | Tailwind 클래스 | 크기 | 설명 |
|------|----------------|------|------|
| 키워드 검색 | `border rounded px-3 py-2 text-sm w-64` | 256px | Enter 키로 검색 실행 |
| 날짜 인풋 | `border rounded px-3 py-2 text-sm` | auto | type=date |
| 발행사 | `border rounded px-3 py-1.5 text-sm w-36` | 144px | placeholder="예: 미래에셋" |
| 종목코드 | `border rounded px-3 py-1.5 text-sm w-28` | 112px | placeholder="예: 005930" |
| 파일 인풋 | `text-sm border rounded px-2 py-1.5` | auto | type=file accept=".pdf" |

#### 배지/태그

| 종류 | Tailwind 클래스 | 예시 |
|------|----------------|------|
| 종목 태그 | `bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full` | `거래량급증`, `신고가` |
| 키워드 해시태그 | `text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full` | `#반도체`, `#HBM` |
| 종목코드 배지 | `text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded` | `005930` |

> 종목 태그와 키워드 해시태그는 동일한 스타일이나, 키워드 앞에 `#` 기호를 명시적으로 렌더링한다.

#### 카드

| 용도 | Tailwind 클래스 | 설명 |
|------|----------------|------|
| 리포트 카드 | `border rounded-lg p-4` | 리포트 검색 결과 카드 |
| 지표 카드 | `border rounded-lg p-4` | 종목 상세 PER/PBR/ROE/구름위치 |
| 일목균형표 섹션 | `border rounded-lg p-4 mb-6` | 종목 상세 일목균형표 |
| 업로드 섹션 | `border rounded-lg mb-6 overflow-hidden` | 접힘/펼침 가능한 업로드 패널 |

#### 테이블

| 요소 | Tailwind 클래스 | 설명 |
|------|----------------|------|
| 래퍼 | `border rounded-lg overflow-hidden` | 테이블 외곽 컨테이너 |
| table | `w-full text-sm` | 전체 너비 |
| thead | `bg-gray-50 text-gray-500 text-xs uppercase` | 헤더 행 스타일 |
| th | `px-4 py-3 text-left` 또는 `text-right` | 열 정렬은 내용에 따라 좌/우 |
| tbody | `divide-y` | 행 사이 구분선 |
| tr (일반) | `hover:bg-gray-50 cursor-pointer` | 행 hover 효과 및 클릭 커서 |
| td | `px-4 py-3` | 셀 패딩 |

---

## 2. 레이아웃

### 2.1 글로벌 레이아웃

```
┌─────────────────────────────────────────────────────────────────┐
│  MPM        종목        리포트                     (Nav Bar)    │
│  [blue-600] [gray-600]  [gray-600]    sticky top, h-14, z-50   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    <Page Content>                               │
│               max-w-7xl mx-auto px-4 py-6                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**내비게이션 바 상세**

| 요소 | 클래스 | 설명 |
|------|--------|------|
| `<nav>` | `border-b bg-white sticky top-0 z-50` | 상단 고정, 하단 구분선 |
| 내부 컨테이너 | `max-w-7xl mx-auto px-4 h-14 flex items-center gap-6` | 최대 너비 제한, 높이 56px |
| 로고 "MPM" | `font-bold text-lg text-blue-600` | 홈("/")으로 링크 |
| "종목" 링크 | `text-sm text-gray-600 hover:text-gray-900` | /stocks로 링크 |
| "리포트" 링크 | `text-sm text-gray-600 hover:text-gray-900` | /reports로 링크 |

**페이지 콘텐츠 영역**

```html
<main className="max-w-7xl mx-auto px-4 py-6">
  {children}
</main>
```

---

### 2.2 라우팅 구조

```
/               → redirect → /stocks         (page.tsx: redirect)
/stocks         → 종목 목록 페이지           (app/stocks/page.tsx)
/stocks/[code]  → 종목 상세 페이지           (app/stocks/[code]/page.tsx)
/reports        → 리포트 검색 페이지         (app/reports/page.tsx)
```

모든 페이지는 `"use client"` 지시어를 사용하는 클라이언트 컴포넌트이다 (데이터 fetching 및 상태 관리 포함).

---

## 3. 페이지별 UI 정의

### 3.1 종목 목록 페이지 (`/stocks`)

**파일**: `frontend/src/app/stocks/page.tsx`  
**컴포넌트**: `StockTable` (`components/stocks/StockTable.tsx`), `StockRow` (`components/stocks/StockRow.tsx`), `FavoriteButton` (`components/stocks/FavoriteButton.tsx`)

#### 화면 구성 요소

1. 페이지 제목: "주식 종목" (`text-2xl font-bold mb-4`)
2. 탭 바: "오늘의 추천" / "즐겨찾기 (N)"
3. 종목 테이블: 종목명, 현재가, 등락률, 거래량, 태그, 즐겨찾기

#### ASCII 와이어프레임

```
주식 종목

[오늘의 추천▌] [즐겨찾기 (3)]

┌──────────────┬──────────┬─────────┬────────────┬──────────────────────┬──┐
│ 종목명       │  현재가  │  등락률 │   거래량   │         태그         │  │
├──────────────┼──────────┼─────────┼────────────┼──────────────────────┼──┤
│ 삼성전자     │  74,200  │ +2.35%  │ 14,250,300 │ [거래량급증] [신고가] │★│
│ 005930       │          │ (red)   │            │                      │  │
├──────────────┼──────────┼─────────┼────────────┼──────────────────────┼──┤
│ SK하이닉스   │ 182,500  │ -1.20%  │  5,120,400 │ [HBM] [반도체]       │☆│
│ 000660       │          │ (blue)  │            │                      │  │
├──────────────┼──────────┼─────────┼────────────┼──────────────────────┼──┤
│ NAVER        │ 225,000  │ +0.45%  │  1,830,200 │ [AI] [플랫폼]        │☆│
│ 035420       │          │ (red)   │            │                      │  │
└──────────────┴──────────┴─────────┴────────────┴──────────────────────┴──┘

(로딩 중 상태)
              불러오는 중...          ← py-20 text-center text-gray-400

(빈 상태)
          표시할 종목이 없습니다.    ← colspan=6, py-12 text-gray-400
```

#### 컴포넌트 상세

**탭 바**

```
flex gap-2 mb-4
```

| 탭 | 활성 상태 클래스 | 비활성 상태 클래스 |
|----|----------------|----------------|
| 오늘의 추천 | `bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium` | `bg-gray-100 text-gray-700 px-4 py-2 rounded text-sm font-medium` |
| 즐겨찾기 (N) | 동일 | 동일 |

즐겨찾기 탭 레이블: `즐겨찾기 ({favorites.length})` — N은 현재 즐겨찾기에 등록된 종목 수.

**종목 테이블** (`StockTable` 컴포넌트)

래퍼: `border rounded-lg overflow-hidden`

헤더 열 구성:

| 열 | th 클래스 | 내용 |
|----|----------|------|
| 종목명 | `px-4 py-3 text-left` | "종목명" |
| 현재가 | `px-4 py-3 text-right` | "현재가" |
| 등락률 | `px-4 py-3 text-right` | "등락률" |
| 거래량 | `px-4 py-3 text-right` | "거래량" |
| 태그 | `px-4 py-3 text-left` | "태그" |
| 즐겨찾기 | `px-4 py-3` | (빈 헤더) |

**종목 행** (`StockRow` 컴포넌트)

행 전체: `hover:bg-gray-50 cursor-pointer` / 클릭 시 `/stocks/{stock_code}`로 라우팅

| 셀 | td 클래스 | 렌더링 |
|----|----------|--------|
| 종목명 | `px-4 py-3` | `<div className="font-medium">{stock_name}</div>` + `<div className="text-gray-400 text-xs">{stock_code}</div>` |
| 현재가 | `px-4 py-3 text-right font-mono` | `current_price.toLocaleString()` (천단위 콤마) |
| 등락률 | `px-4 py-3 text-right font-mono` + 조건부 색상 | `change_rate >= 0` → `text-red-500` / `change_rate < 0` → `text-blue-500` / 형식: `+2.35%` or `-1.20%` |
| 거래량 | `px-4 py-3 text-right font-mono text-gray-500` | `volume.toLocaleString()` |
| 태그 | `px-4 py-3` | `flex gap-1 flex-wrap` 내 각 태그: `bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full` |
| 즐겨찾기 | `px-4 py-3` + `e.stopPropagation()` | `FavoriteButton` 컴포넌트 |

**FavoriteButton 컴포넌트**

```tsx
// components/stocks/FavoriteButton.tsx
<Star className={`w-4 h-4 ${isFavorite ? "fill-yellow-400 text-yellow-400" : "text-gray-300"}`} />
```

| 상태 | 아이콘 클래스 |
|------|-------------|
| 즐겨찾기 활성 | `fill-yellow-400 text-yellow-400` (노란 별) |
| 즐겨찾기 비활성 | `text-gray-300` (빈 별) |

> 중요: 즐겨찾기 셀(`<td>`)의 onClick에서 `e.stopPropagation()`을 호출하여 행 클릭 이벤트(페이지 이동)가 버블링되지 않도록 방지한다.

#### 상태 관리

| 상태명 | 타입 | 초기값 | 설명 |
|--------|------|--------|------|
| `tab` | `"recommend" \| "favorites"` | `"recommend"` | 현재 활성 탭 |
| `stocks` | `StockSummary[]` | `[]` | API에서 가져온 전체 종목 데이터 |
| `loading` | `boolean` | `true` | API 로딩 여부 |
| `favorites` | `string[]` | `[]` | useFavorites 훅 (localStorage 기반) |

표시 데이터 계산:
```ts
const displayed = tab === "recommend"
  ? stocks
  : stocks.filter((s) => isFavorite(s.stock_code));
```

#### 데이터 흐름

1. 컴포넌트 마운트 시 `api.getRecommendations()` 호출 (`GET /api/v1/stocks/recommend`)
2. 성공 시 `stocks` 상태에 `res.data` 저장, `loading = false`
3. `tab === "recommend"`: 전체 `stocks` 표시
4. `tab === "favorites"`: `isFavorite(s.stock_code)`가 true인 종목만 필터링하여 표시
5. 즐겨찾기 토글: `toggle(code)` 호출 → localStorage 즉시 업데이트 → UI 즉시 반영 (서버 왕복 없음)

---

### 3.2 종목 상세 페이지 (`/stocks/[code]`)

**파일**: `frontend/src/app/stocks/[code]/page.tsx`

> 참고: `CandleChart` 컴포넌트(`components/charts/CandleChart.tsx`)가 구현되어 있으나 현재 상세 페이지에 통합되지 않은 상태이다. 향후 차트 기능 추가를 위한 컴포넌트로 준비되어 있다.

#### ASCII 와이어프레임

```
← 목록으로

종목 상세 — 005930

┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────┐
│    PER    │  │    PBR    │  │    ROE    │  │  구름 위치   │
│   15.4    │  │    1.2    │  │   8.5%    │  │ above_cloud  │
└───────────┘  └───────────┘  └───────────┘  └──────────────┘

┌─ 일목균형표 ──────────────────────────────────────────────────┐
│                                                               │
│   전환선     73,500        기준선     72,000                  │
│   선행스팬A  71,500        선행스팬B  70,000                  │
│                                                               │
└───────────────────────────────────────────────────────────────┘

(로딩 중 상태)
              불러오는 중...          ← py-20 text-center text-gray-400

(에러 상태)
         데이터를 가져올 수 없습니다. ← py-20 text-center text-red-400
```

#### 컴포넌트 상세

**뒤로가기 링크**

```tsx
<Link href="/stocks" className="text-sm text-blue-600 hover:underline mb-4 inline-block">
  ← 목록으로
</Link>
```

**페이지 제목**

```tsx
<h1 className="text-2xl font-bold mb-6">종목 상세 — {code}</h1>
```

**지표 카드 그리드**

레이아웃: `grid grid-cols-2 md:grid-cols-4 gap-4 mb-8`

| 브레이크포인트 | 열 수 | 설명 |
|-------------|------|------|
| 기본 (mobile) | 2열 | `grid-cols-2` |
| md (768px+) | 4열 | `md:grid-cols-4` |

카드 내부 구조:

```tsx
<div className="border rounded-lg p-4">
  <div className="text-xs text-gray-500 mb-1">{label}</div>
  <div className="text-xl font-semibold">{value}</div>
</div>
```

지표 카드 데이터 및 포맷:

| 라벨 | 원본 필드 | 포맷 | null 처리 |
|------|---------|------|---------|
| PER | `metrics.per` | `per.toFixed(1)` | `"N/A"` |
| PBR | `metrics.pbr` | `pbr.toFixed(2)` | `"N/A"` |
| ROE | `metrics.roe` | `` `${roe.toFixed(1)}%` `` | `"N/A"` |
| 구름 위치 | `ichimoku.position` | raw string (예: `above_cloud`) | 항상 값 존재 |

**일목균형표 섹션**

```tsx
<div className="border rounded-lg p-4 mb-6">
  <h2 className="font-semibold mb-3">일목균형표</h2>
  <div className="grid grid-cols-2 gap-2 text-sm">
    {/* 각 항목 */}
    <div className="flex justify-between">
      <span className="text-gray-500">전환선</span>
      <span>{ichimoku.conversion_line.toLocaleString()}</span>
    </div>
    ...
  </div>
</div>
```

일목균형표 항목:

| 라벨 | 원본 필드 | 포맷 |
|------|---------|------|
| 전환선 | `ichimoku.conversion_line` | `toLocaleString()` |
| 기준선 | `ichimoku.base_line` | `toLocaleString()` |
| 선행스팬A | `ichimoku.span_a` | `toLocaleString()` |
| 선행스팬B | `ichimoku.span_b` | `toLocaleString()` |

그리드 배치: `grid-cols-2`로 전환선/기준선이 첫 행, 선행스팬A/B가 두 번째 행에 각각 좌우 배치.

#### 상태 관리

| 상태명 | 타입 | 초기값 | 설명 |
|--------|------|--------|------|
| `detail` | `StockDetail \| null` | `null` | API에서 가져온 종목 상세 데이터 |
| `loading` | `boolean` | `true` | API 로딩 여부 |

#### 데이터 흐름

1. URL 파라미터 `code`를 `use(params)`로 추출 (Next.js 15 Promise params 방식)
2. 컴포넌트 마운트 시 `api.getStockDetail(code)` 호출 (`GET /api/v1/stocks/{code}/detail`)
3. `loading === true`: 로딩 텍스트 렌더링
4. `loading === false && detail === null`: 에러 텍스트 렌더링
5. 성공 시 `detail.metrics`, `detail.ichimoku`를 구조 분해하여 지표 카드 및 일목균형표 렌더링

#### CandleChart 컴포넌트 (미사용 준비 상태)

**파일**: `frontend/src/components/charts/CandleChart.tsx`  
**라이브러리**: `lightweight-charts`

```tsx
// Props
interface CandleChartProps {
  data: OHLCVData[];  // { time: string; open: number; high: number; low: number; close: number }[]
  height?: number;    // 기본값: 300
}
```

차트 색상 설정:

| 항목 | 값 | 설명 |
|------|-----|------|
| `upColor` | `#ef4444` (red-500) | 상승 캔들 몸통 |
| `downColor` | `#3b82f6` (blue-500) | 하락 캔들 몸통 |
| `wickUpColor` | `#ef4444` (red-500) | 상승 캔들 심지 |
| `wickDownColor` | `#3b82f6` (blue-500) | 하락 캔들 심지 |
| `borderVisible` | `false` | 캔들 테두리 숨김 |
| 배경색 | `#ffffff` (white) | 차트 배경 |
| 격자선 색 | `#f0f0f0` (gray-100) | 수평/수직 격자 |

> 현재 종목 상세 페이지에 렌더링되지 않지만, 컴포넌트 자체는 완성된 상태이다. 향후 `detail` API 응답에 OHLCV 데이터가 포함될 경우 즉시 통합 가능하다.

---

### 3.3 리포트 검색 페이지 (`/reports`)

**파일**: `frontend/src/app/reports/page.tsx`  
**컴포넌트**: `ReportList` (`components/reports/ReportList.tsx`), `ReportCard` (`components/reports/ReportCard.tsx`)  
**아이콘**: `Upload`, `ChevronDown`, `ChevronUp`, `Search` (lucide-react)

#### ASCII 와이어프레임

```
리포트 검색

┌─ [▲] 리포트 업로드                        [∧] ──────────────────┐
│  PDF 파일*     발행사        발행일        종목코드              │
│  [파일선택]    [미래에셋]    [2026-05-01]  [005930]             │
│                                                                  │
│  [▲ 업로드]                                                      │
│                                                                  │
│  ✓ 업로드 완료 — AI 요약                                        │
│  HBM 공급 확대로 하반기 역대 최대 실적 기대.                    │
│                                                                  │
│  ✗ 업로드 실패 메시지 (에러 시)                                 │
└─────────────────────────────────────────────────────────────────┘

[키워드 검색 (예: HBM, 반도체)    ] [2026-01-01] ~ [2026-05-15] [🔍 검색]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(검색 중)
                      검색 중...             ← py-20 text-gray-400

(결과 없음)
              검색 결과가 없습니다.          ← py-20 text-gray-500 (message 텍스트)

(결과 있음)
┌─────────────────────────────────────────────────────────────────┐
│ 2026년 반도체 사이클 전망                                       │
│ 미래에셋 · 2026-05-10    [005930]                               │
│ ─────────────────────────────────────────────────────────────── │
│ HBM 공급 확대로 하반기 역대 최대 실적 기대.                     │
│ • HBM3E 12단 양산 경쟁사 대비 6개월 선행                        │
│ • DRAM 가격 상승 기존 예상치 상회                               │
│ • 단기 설비투자 비중 확대로 재무 부담 증가                      │
│ #반도체  #HBM  #이머징마켓                                      │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ ...                                                             │
└─────────────────────────────────────────────────────────────────┘
```

#### 컴포넌트 상세

**PDF 업로드 섹션 (접힘/펼침 패널)**

컨테이너: `border rounded-lg mb-6 overflow-hidden`

헤더 버튼:
```tsx
<button className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 text-left font-medium text-sm">
  <span className="flex items-center gap-2">
    <Upload className="w-4 h-4" />
    리포트 업로드
  </span>
  {uploadOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
</button>
```

| 상태 | 동작 |
|------|------|
| `uploadOpen === false` | 헤더만 표시, `ChevronDown` 아이콘 |
| `uploadOpen === true` | 헤더 + 폼 영역 표시, `ChevronUp` 아이콘 |

> 헤더 버튼 클릭 시 `uploadSuccess`와 `uploadError`도 함께 초기화된다.

펼쳐진 폼 영역: `p-4 space-y-3`

입력 필드 행: `flex flex-wrap gap-3`

| 필드 | label | 클래스 | 비고 |
|------|-------|--------|------|
| PDF 파일 | "PDF 파일 *" | `text-sm border rounded px-2 py-1.5` | type=file, accept=".pdf", `useRef`로 참조 (성공 후 `.value = ""` 리셋) |
| 발행사 | "발행사" | `border rounded px-3 py-1.5 text-sm w-36` | placeholder="예: 미래에셋" |
| 발행일 | "발행일" | `border rounded px-3 py-1.5 text-sm` | type=date |
| 종목코드 | "종목코드" | `border rounded px-3 py-1.5 text-sm w-28` | placeholder="예: 005930" |

label 공통 클래스: `text-xs text-gray-500`  
각 필드 래퍼: `flex flex-col gap-1`

업로드 버튼:
```tsx
<button
  disabled={!uploadFile || uploading}
  className="bg-green-600 text-white px-4 py-2 rounded text-sm flex items-center gap-2 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
>
  <Upload className="w-4 h-4" />
  {uploading ? "업로드 중..." : "업로드"}
</button>
```

| 버튼 상태 | 조건 | 텍스트 |
|---------|------|--------|
| 활성 | `uploadFile !== null && !uploading` | "업로드" |
| 업로드 중 | `uploading === true` | "업로드 중..." |
| Disabled | `uploadFile === null` 또는 `uploading === true` | opacity-50, cursor-not-allowed |

에러 박스:
```tsx
<div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
  {uploadError}
</div>
```

성공 박스:
```tsx
<div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">
  <p className="font-medium mb-1">업로드 완료 — AI 요약</p>
  <p>{uploadSuccess.one_line}</p>
</div>
```

> 업로드 성공 후 동작: 파일(`fileInputRef.current.value = ""`), 발행사, 발행일, 종목코드 상태 초기화. `searched === true`이면 자동으로 기존 검색 조건으로 재검색 실행.

**검색 바**

컨테이너: `flex flex-wrap gap-3 mb-6`

| 요소 | 클래스 | 기능 |
|------|--------|------|
| 키워드 인풋 | `border rounded px-3 py-2 text-sm w-64` | `onKeyDown`: Enter 키로 검색 실행 |
| 시작일 인풋 | `border rounded px-3 py-2 text-sm` | type=date |
| 구분자 "~" | `self-center text-gray-400` | 시각적 구분 |
| 종료일 인풋 | `border rounded px-3 py-2 text-sm` | type=date |
| 검색 버튼 | `bg-blue-600 text-white px-4 py-2 rounded text-sm flex items-center gap-2 hover:bg-blue-700` | `<Search className="w-4 h-4" />` 아이콘 + "검색" 텍스트 |

**리포트 카드** (`ReportCard` 컴포넌트)

카드 컨테이너: `border rounded-lg p-4`

```
┌──────────────────────────────────────────────────────────────────┐
│ [font-medium] 리포트 제목                                        │
│ [text-xs text-gray-400 mt-1] 발행사 · YYYY-MM-DD                │
│ [text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded mt-1    │
│  inline-block] 005930                  ← 종목코드 배지 (조건부) │
├──────────────────────────────────────────────────────────────────┤
│ (ai_summary 있을 때만 렌더링)                                    │
│ mt-3 border-t pt-3                                               │
│                                                                  │
│ [text-sm text-gray-700 mb-2] one_line 한 줄 요약                │
│                                                                  │
│ • [text-xs text-gray-500] key_point_1                           │
│ • key_point_2                                                   │
│ • key_point_3                                                   │
│                                                                  │
│ [text-xs bg-blue-50 text-blue-700 rounded-full] #반도체 #HBM   │
└──────────────────────────────────────────────────────────────────┘
```

AI 요약 영역 세부:

| 요소 | 클래스 | 설명 |
|------|--------|------|
| AI 요약 래퍼 | `mt-3 border-t pt-3` | `ai_summary !== null`일 때만 렌더링 |
| one_line | `text-sm text-gray-700 mb-2` | 한 줄 요약 텍스트 |
| key_points | `text-xs text-gray-500 list-disc list-inside space-y-1 mb-2` | `<ul>` + `<li>` 목록 |
| keywords | `flex gap-1 flex-wrap` | 키워드 해시태그 컨테이너 |
| 각 키워드 | `text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full` | `#{keyword}` 형식 |

**리포트 목록** (`ReportList` 컴포넌트)

목록 컨테이너: `space-y-3` (카드 간 12px 간격)

빈 상태 (컴포넌트 내부): `text-center py-20 text-gray-400 "표시할 리포트가 없습니다."` ← 단, 페이지에서는 `message` 상태로 처리

**검색 결과 상태별 렌더링**

| 상태 | 조건 | 표시 내용 |
|------|------|---------|
| 검색 전 | `!searched` | 아무것도 표시 안 함 |
| 검색 중 | `loading === true` | `"검색 중..."` (text-center py-20 text-gray-400) |
| 결과 없음 | `!loading && searched && message !== null` | `message` 텍스트 (text-center py-20 text-gray-500) |
| 결과 있음 | `!loading && searched && message === null` | `ReportCard` 목록 |

#### 상태 관리

| 상태명 | 타입 | 초기값 | 설명 |
|--------|------|--------|------|
| `keyword` | `string` | `""` | 키워드 검색 입력값 |
| `startDate` | `string` | `""` | 시작 날짜 (YYYY-MM-DD) |
| `endDate` | `string` | `""` | 종료 날짜 (YYYY-MM-DD) |
| `results` | `ReportSummary[]` | `[]` | 검색 결과 리포트 목록 |
| `message` | `string \| null` | `null` | 빈 결과 메시지 (API 응답의 `message` 필드) |
| `searched` | `boolean` | `false` | 검색 실행 여부 (결과 영역 표시 조건) |
| `loading` | `boolean` | `false` | 검색 중 여부 |
| `uploadOpen` | `boolean` | `false` | 업로드 섹션 펼침/접힘 상태 |
| `uploadFile` | `File \| null` | `null` | 선택된 PDF 파일 |
| `uploadPublisher` | `string` | `""` | 발행사 입력값 |
| `uploadDate` | `string` | `""` | 발행일 입력값 |
| `uploadStockCode` | `string` | `""` | 종목코드 입력값 |
| `uploading` | `boolean` | `false` | 업로드 진행 중 여부 |
| `uploadSuccess` | `{ one_line: string } \| null` | `null` | 업로드 성공 시 AI 요약 데이터 |
| `uploadError` | `string \| null` | `null` | 업로드 실패 시 에러 메시지 |
| `fileInputRef` | `React.RefObject<HTMLInputElement>` | `useRef(null)` | 파일 인풋 DOM 참조 (성공 후 리셋용) |

#### 데이터 흐름

**검색 흐름:**
1. 키워드 인풋 Enter 또는 검색 버튼 클릭 → `handleSearch()` 실행
2. `loading = true`, `searched = true`
3. `api.searchReports({ keyword?, start_date?, end_date? })` 호출
4. 성공: `results = res.data`, `message = res.message ?? null`, `loading = false`
5. `message !== null`이면 빈 결과 메시지 표시, `message === null`이면 카드 목록 표시

**업로드 흐름:**
1. PDF 파일 선택 후 업로드 버튼 클릭 → `handleUpload()` 실행
2. `uploading = true`, `uploadSuccess = null`, `uploadError = null`
3. `FormData` 구성: `file`(필수), `publisher`/`publish_date`/`target_stock_code`(선택, 값이 있을 때만 추가)
4. `api.uploadReport(formData)` 호출 (`POST /api/v1/reports/upload`)
5. 성공: `uploadSuccess = res.data.ai_summary`, 폼 전체 초기화, `searched === true`이면 자동 재검색
6. 실패: `uploadError = err.message ?? "업로드 실패"`
7. `uploading = false`

---

## 4. 전역 상태 & 훅

### 4.1 `useFavorites` 훅

**파일**: `frontend/src/hooks/useFavorites.ts`

**저장소**: `localStorage` (키: `"mpm_favorites"`)  
**저장 형식**: JSON 직렬화된 `string[]` (종목코드 배열)

**API**:

| 반환값 | 타입 | 설명 |
|--------|------|------|
| `favorites` | `string[]` | 현재 즐겨찾기 종목코드 배열 |
| `toggle(code: string)` | `() => void` | 코드가 있으면 제거, 없으면 추가 |
| `isFavorite(code: string)` | `boolean` | 해당 코드가 즐겨찾기에 포함되어 있는지 여부 |

**동작 방식**:
- 마운트 시 `useEffect`에서 `localStorage.getItem("mpm_favorites")` → JSON.parse → `favorites` 상태 초기화
- `toggle` 호출 시 `setFavorites` 내부에서 prev 기반으로 next 계산 → `localStorage.setItem("mpm_favorites", JSON.stringify(next))` → 즉시 UI 반영
- 서버 API 호출 없음 (완전히 클라이언트 사이드 로컬 저장)

```ts
// 구현 요약
export function useFavorites() {
  const [favorites, setFavorites] = useState<string[]>([]);

  useEffect(() => {
    const stored = localStorage.getItem("mpm_favorites");
    if (stored) setFavorites(JSON.parse(stored));
  }, []);

  const toggle = (code: string) => {
    setFavorites((prev) => {
      const next = prev.includes(code)
        ? prev.filter((c) => c !== code)
        : [...prev, code];
      localStorage.setItem("mpm_favorites", JSON.stringify(next));
      return next;
    });
  };

  const isFavorite = (code: string) => favorites.includes(code);

  return { favorites, toggle, isFavorite };
}
```

---

## 5. API 연동 (`frontend/src/lib/api.ts`)

**Base URL 설정**:
```ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

환경변수 `NEXT_PUBLIC_API_URL`을 `.env.local`에 설정하여 개발/운영 환경 전환. 미설정 시 `http://localhost:8000` 사용.

**공통 fetch 래퍼**:
```ts
async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
```

**API 함수 목록**:

| 함수명 | HTTP | 엔드포인트 | 반환 타입 | 설명 |
|--------|------|-----------|---------|------|
| `api.getRecommendations()` | GET | `/api/v1/stocks/recommend` | `{ status: string; data: StockSummary[] }` | 오늘의 추천 종목 목록 |
| `api.getStockDetail(code)` | GET | `/api/v1/stocks/{code}/detail` | `{ status: string; data: StockDetail }` | 종목 상세 (지표 + 일목균형표) |
| `api.searchReports(params)` | GET | `/api/v1/reports/summary?{qs}` | `{ status: string; count: number; data: ReportSummary[]; message?: string }` | 리포트 키워드/날짜 검색 |
| `api.uploadReport(formData)` | POST | `/api/v1/reports/upload` | `{ status: string; data: { ai_summary: AISummary; ... } }` | PDF 리포트 업로드 및 AI 분석 |

**`searchReports` 쿼리스트링 구성**:
```ts
const qs = new URLSearchParams(
  Object.entries(params).filter(([, v]) => v) as [string, string][]
).toString();
// 값이 있는 파라미터만 포함: keyword, start_date, end_date
```

**`uploadReport` 특이사항**: `fetchAPI` 래퍼 미사용, `Content-Type` 자동 설정을 위해 `FormData`를 직접 `fetch`에 전달. HTTP 4xx/5xx 시 에러 throw.

---

## 6. 타입 정의 (`frontend/src/lib/types.ts`)

```ts
export interface StockSummary {
  stock_code: string;    // 종목코드 (예: "005930")
  stock_name: string;    // 종목명 (예: "삼성전자")
  current_price: number; // 현재가 (원)
  change_rate: number;   // 등락률 (%, 양수=상승 음수=하락)
  volume: number;        // 거래량
  tags: string[];        // 추천 태그 (예: ["거래량급증", "신고가"])
}
```

```ts
export interface StockDetail {
  stock_code: string;
  metrics: {
    per: number | null;  // PER (Price-Earnings Ratio), null 가능
    pbr: number | null;  // PBR (Price-Book Ratio), null 가능
    roe: number | null;  // ROE (Return on Equity, %), null 가능
  };
  ichimoku: {
    conversion_line: number; // 전환선
    base_line: number;       // 기준선
    span_a: number;          // 선행스팬A
    span_b: number;          // 선행스팬B
    position: string;        // 구름 위치 (예: "above_cloud", "below_cloud")
  };
}
```

```ts
export interface AISummary {
  one_line: string;    // 한 줄 요약
  key_points: string[]; // 핵심 포인트 목록 (불릿 리스트로 표시)
  keywords: string[];  // 키워드 목록 (해시태그로 표시)
}
```

```ts
export interface ReportSummary {
  report_id: number;                // 리포트 고유 ID
  title: string;                    // 리포트 제목
  publisher: string;                // 발행사명
  publish_date: string;             // 발행일 (YYYY-MM-DD 형식)
  target_stock_code: string | null; // 관련 종목코드 (없으면 null)
  ai_summary: AISummary | null;     // AI 분석 결과 (없으면 null)
}
```

---

## 7. 반응형 대응

| 브레이크포인트 | 클래스 | 적용 요소 | 설명 |
|-------------|--------|---------|------|
| 기본 (< 768px) | `grid-cols-2` | 종목 상세 지표 카드 그리드 | 2열 레이아웃 |
| md (≥ 768px) | `md:grid-cols-4` | 종목 상세 지표 카드 그리드 | 4열 레이아웃 |
| 기본 | `flex-wrap` | 검색 바, 태그 영역, 업로드 입력 필드 | 모바일에서 자동 줄바꿈 |
| 기본 | `overflow-hidden` | 종목 테이블 래퍼 | 모바일에서 가로 스크롤 방지 |
| 기본 | `w-full` | 테이블 | 컨테이너 전체 너비 |
| 기본 | `max-w-7xl mx-auto px-4` | Nav 내부, main 콘텐츠 | 최대 너비 제한 + 좌우 패딩 |

> 현재 테이블은 `overflow-hidden`으로 처리되어 있어 좁은 화면에서 열이 잘릴 수 있다. 향후 모바일 대응 시 `overflow-x-auto`로 변경하거나 카드형 레이아웃으로 전환을 검토할 수 있다.

---

## 8. UX 규칙

| 규칙 | 구현 위치 | 설명 |
|------|---------|------|
| 로딩 표시 | 모든 페이지 | API 호출 시작 시 `loading = true`, 완료/실패 시 `loading = false`. "불러오는 중..." / "검색 중..." 텍스트 표시 (py-20 text-center) |
| 에러 처리 | 종목 상세, 업로드 | API 실패 시 사용자 친화적 메시지 ("데이터를 가져올 수 없습니다.", 에러 박스) 표시 |
| 즉각 피드백 | 즐겨찾기 토글 | 서버 왕복 없이 localStorage만 업데이트하여 UI 즉시 반영 |
| Enter 검색 | 리포트 검색 키워드 인풋 | `onKeyDown`: `e.key === "Enter"` → `handleSearch()` 실행 |
| 클릭 버블링 방지 | 종목 테이블 즐겨찾기 셀 | `e.stopPropagation()` 호출로 행 클릭(페이지 이동) 방지 |
| 업로드 후 폼 초기화 | 리포트 업로드 | 성공 시 `uploadFile`, `uploadPublisher`, `uploadDate`, `uploadStockCode` 초기화 + `fileInputRef.current.value = ""` |
| 자동 재검색 | 리포트 업로드 성공 후 | `searched === true`이면 기존 검색 조건으로 `handleSearch()` 자동 실행하여 목록 갱신 |
| null 값 처리 | 종목 상세 지표 | `metrics.per/pbr/roe`가 `null`이면 `"N/A"` 문자열로 표시 |
| 조건부 렌더링 | 리포트 카드 | `target_stock_code`가 `null`이면 종목코드 배지 미표시, `ai_summary`가 `null`이면 AI 요약 영역 미표시 |
| 숫자 포맷 | 테이블, 상세 페이지 | 현재가·거래량·일목균형표 값은 `.toLocaleString()`으로 천단위 콤마 적용 |
| 등락률 포맷 | 종목 테이블 | `.toFixed(2)%` + 양수면 `"+"` 접두사 추가 |
| 파라미터 필터링 | 리포트 검색 API | 빈 문자열인 검색 파라미터는 쿼리스트링에서 제외 |

---

## 9. 컴포넌트 구조도

```
frontend/src/
├── app/
│   ├── layout.tsx              ← 글로벌 레이아웃 (Nav Bar + main 래퍼)
│   ├── globals.css             ← 전역 CSS (Tailwind 기본 포함)
│   ├── page.tsx                ← / → /stocks redirect
│   ├── stocks/
│   │   ├── page.tsx            ← /stocks 종목 목록 페이지
│   │   └── [code]/
│   │       └── page.tsx        ← /stocks/[code] 종목 상세 페이지
│   └── reports/
│       └── page.tsx            ← /reports 리포트 검색 페이지
├── components/
│   ├── stocks/
│   │   ├── StockTable.tsx      ← 종목 테이블 (thead + tbody 래퍼)
│   │   ├── StockRow.tsx        ← 종목 행 (tr 단위)
│   │   └── FavoriteButton.tsx  ← 즐겨찾기 Star 아이콘
│   ├── charts/
│   │   └── CandleChart.tsx     ← 캔들차트 (lightweight-charts, 미사용 준비 상태)
│   └── reports/
│       ├── ReportList.tsx      ← 리포트 목록 (space-y-3 래퍼)
│       └── ReportCard.tsx      ← 리포트 카드 (단일 카드)
├── hooks/
│   └── useFavorites.ts         ← localStorage 기반 즐겨찾기 훅
└── lib/
    ├── api.ts                  ← API 함수 모음 (fetchAPI 래퍼)
    └── types.ts                ← TypeScript 인터페이스 정의
```

---

## 10. 향후 개선 고려 사항

> 현재 코드베이스에서 발견된 잠재적 개선 포인트 (구현되지 않은 기능 및 구조적 개선)

| 항목 | 현황 | 개선 방향 |
|------|------|---------|
| CandleChart 통합 | 컴포넌트 구현됨, 페이지에 미적용 | 종목 상세 페이지에 OHLCV 차트 추가 |
| 테이블 모바일 대응 | `overflow-hidden`으로 처리 | `overflow-x-auto` 또는 카드형 레이아웃 전환 |
| 에러 경계 | 개별 페이지의 조건부 렌더링에 의존 | React Error Boundary 또는 Next.js error.tsx 추가 |
| 로딩 스피너 | 텍스트 "불러오는 중..." 사용 | 시각적 스피너 또는 스켈레톤 UI 추가 |
| ReportList 컴포넌트 | 구현됨, 리포트 페이지에서 직접 렌더링 사용 | reports/page.tsx가 ReportList 컴포넌트를 사용하도록 리팩토링 |
| 검색 결과 없음 처리 | API `message` 필드에 의존 | `results.length === 0`과 `message` 조합으로 일관된 처리 |
| 즐겨찾기 지속성 | localStorage만 사용 | 로그인 기능 추가 시 서버 사이드 동기화 고려 |
