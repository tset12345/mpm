#!/usr/bin/env bash
# MPM FE/BE 동작 확인 스크립트
#
# Usage:
#   ./check.sh             # 전체 확인
#   ./check.sh --be        # 백엔드만 확인
#   ./check.sh --fe        # 프론트엔드만 확인
#   ./check.sh --reboot    # BE+FE 재시작 후 확인
#   ./check.sh --reboot --be  # 백엔드만 재시작 후 확인
#   ./check.sh --reboot --fe  # 프론트엔드만 재시작 후 확인

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BE_URL="${BE_URL:-http://localhost:8000}"
FE_URL="${FE_URL:-http://localhost:3000}"

PASS=0
FAIL=0

# ── 색상 ────────────────────────────────────────────────────────────────────
GREEN="\033[1;32m"; RED="\033[1;31m"; YELLOW="\033[1;33m"
CYAN="\033[1;36m";  BOLD="\033[1m";   RESET="\033[0m"

ok()   { echo -e "  ${GREEN}✓${RESET}  $*"; ((PASS++)); }
fail() { echo -e "  ${RED}✗${RESET}  $*"; ((FAIL++)); }
info() { echo -e "  ${YELLOW}·${RESET}  $*"; }
hdr()  { echo -e "\n${CYAN}${BOLD}$*${RESET}"; }

# ── 헬퍼 ────────────────────────────────────────────────────────────────────
check_port() {
    local port=$1 label=$2
    if lsof -i :"$port" -sTCP:LISTEN &>/dev/null; then
        ok "$label 포트 $port LISTEN"
    else
        fail "$label 포트 $port 응답 없음"
    fi
}

# check_api <label> <url> [jq_expr]  → HTTP 2xx/3xx + 선택적 값 출력
check_api() {
    local label=$1 url=$2 jq_expr=${3:-}
    local http_code body
    body=$(curl -s -o /tmp/_mpm_body -w "%{http_code}" --max-time 10 "$url" 2>/dev/null)
    http_code=$body

    if [[ "$http_code" =~ ^[23] ]]; then
        if [ -n "$jq_expr" ] && command -v python3 &>/dev/null; then
            local detail
            detail=$(python3 -c "
import json, sys
try:
    d = json.load(open('/tmp/_mpm_body'))
    print($jq_expr)
except Exception as e:
    print('parse error:', e)
" 2>/dev/null)
            ok "$label  ${YELLOW}${detail}${RESET}"
        else
            ok "$label"
        fi
    else
        local err
        err=$(cat /tmp/_mpm_body 2>/dev/null | head -c 120)
        fail "$label  (HTTP $http_code) $err"
    fi
}

# check_route <label> <method> <url>  → 401/403=라우트 등록됨, 404=없음, 기타=오류
check_route() {
    local label=$1 method=$2 url=$3
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -X "$method" "$url" 2>/dev/null)

    if [[ "$http_code" =~ ^[23] ]]; then
        ok "$label  ${YELLOW}(HTTP $http_code)${RESET}"
    elif [[ "$http_code" == "401" || "$http_code" == "403" ]]; then
        ok "$label  ${YELLOW}(HTTP $http_code — 인증 필요, 라우트 등록됨)${RESET}"
    elif [[ "$http_code" == "404" ]]; then
        fail "$label  (HTTP 404 — 라우트 없음)"
    else
        local err
        err=$(cat /tmp/_mpm_body 2>/dev/null | head -c 80)
        fail "$label  (HTTP $http_code) $err"
    fi
}

# ── 재시작 함수 ──────────────────────────────────────────────────────────────
reboot_be() {
    hdr "[Backend 재시작]"
    local pid
    pid=$(lsof -ti :8000 2>/dev/null) || true
    if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null && info "기존 프로세스 종료 (PID $pid)"
        sleep 1
    fi

    local uvicorn="$BACKEND_DIR/.venv/bin/uvicorn"
    if [ ! -x "$uvicorn" ]; then
        fail "uvicorn 없음: $uvicorn"
        return 1
    fi

    (cd "$BACKEND_DIR" && nohup "$uvicorn" app.main:app --host 0.0.0.0 --port 8000 \
        > /tmp/mpm_backend.log 2>&1 &)
    info "백엔드 시작 중..."

    local i=0
    while [ $i -lt 15 ]; do
        sleep 1; ((i++))
        if lsof -i :8000 -sTCP:LISTEN &>/dev/null; then
            ok "백엔드 기동 완료 (${i}s)"
            return 0
        fi
    done
    fail "백엔드 기동 타임아웃 (15s)  →  tail /tmp/mpm_backend.log"
    return 1
}

reboot_fe() {
    hdr "[Frontend 재시작]"
    local pid
    pid=$(lsof -ti :3000 2>/dev/null) || true
    if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null && info "기존 프로세스 종료 (PID $pid)"
        sleep 1
    fi

    nohup npm --prefix "$FRONTEND_DIR" run dev \
        > /tmp/mpm_frontend.log 2>&1 &
    info "프론트엔드 시작 중 (PID $!)..."

    local i=0
    while [ $i -lt 30 ]; do
        sleep 1; ((i++))
        if lsof -i :3000 -sTCP:LISTEN &>/dev/null; then
            ok "프론트엔드 기동 완료 (${i}s)"
            return 0
        fi
    done
    fail "프론트엔드 기동 타임아웃 (30s)  →  tail /tmp/mpm_frontend.log"
    return 1
}

# ── 인자 파싱 ─────────────────────────────────────────────────────────────────
CHECK_BE=true
CHECK_FE=true
REBOOT=false

for arg in "${@:-}"; do
    case $arg in
        --reboot)  REBOOT=true ;;
        --be)      CHECK_FE=false ;;
        --fe)      CHECK_BE=false ;;
        -h|--help)
            sed -n '2,9p' "$0" | sed 's/^# \{0,2\}//'
            exit 0 ;;
    esac
done

# ── 출력 헤더 ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}========================================${RESET}"
echo -e "${BOLD}  MPM 동작 확인${RESET}"
echo -e "${BOLD}========================================${RESET}"

# ── 재시작 ────────────────────────────────────────────────────────────────────
if [ "$REBOOT" = true ]; then
    [ "$CHECK_BE" = true ] && reboot_be
    [ "$CHECK_FE" = true ] && reboot_fe
fi

# ════════════════════════════════════════
# 백엔드
# ════════════════════════════════════════
if [ "$CHECK_BE" = true ]; then
    hdr "[Backend]  $BE_URL"

    check_port 8000 "FastAPI"

    check_route "GET  /api/v1/stocks/recommend"        GET    "$BE_URL/api/v1/stocks/recommend"
    check_route "GET  /api/v1/stocks/recommend/prices"  GET    "$BE_URL/api/v1/stocks/recommend/prices"
    check_route "GET  /api/v1/stocks/search?q=삼성"     GET    "$BE_URL/api/v1/stocks/search?q=%EC%82%BC%EC%84%B1"
    check_route "GET  /api/v1/holdings"                 GET    "$BE_URL/api/v1/holdings"
    check_route "GET  /api/v1/profiles"                 GET    "$BE_URL/api/v1/profiles"
    check_route "GET  /api/v1/stocks/history?type=daily" GET   "$BE_URL/api/v1/stocks/history?type=daily"
    check_route "GET  /api/v1/stocks/favorites"         GET    "$BE_URL/api/v1/stocks/favorites"
    check_route "POST /api/v1/stocks/favorites"         POST   "$BE_URL/api/v1/stocks/favorites"
    check_route "DEL  /api/v1/stocks/favorites/000000"  DELETE "$BE_URL/api/v1/stocks/favorites/000000"
    check_route "GET  /api/v1/stocks/sector-leader/all" GET    "$BE_URL/api/v1/stocks/sector-leader/all"

    # 가상 거래
    check_route "GET  /api/v1/virtual/accounts"         GET    "$BE_URL/api/v1/virtual/accounts"
    check_route "POST /api/v1/virtual/accounts"         POST   "$BE_URL/api/v1/virtual/accounts"

    # 시장 현황
    check_route "GET  /api/v1/market/treemap"           GET    "$BE_URL/api/v1/market/treemap?sort=change_rate"
    check_route "GET  /api/v1/market/index-chart"       GET    "$BE_URL/api/v1/market/index-chart?market=KOSPI&period=D"
    check_route "GET  /api/v1/market/investor-trend"    GET    "$BE_URL/api/v1/market/investor-trend"
    check_route "GET  /api/v1/market/adr"               GET    "$BE_URL/api/v1/market/adr?days=60"
    check_route "GET  /api/v1/market/sparkline/005930"  GET    "$BE_URL/api/v1/market/sparkline/005930?days=5"

    # entry_price / source_conditions 필드 검증
    echo ""
    info "추천 종목 상세 필드 확인:"
    python3 - <<'PY' 2>/dev/null || info "(python3 파싱 생략)"
import json, os
try:
    body = json.load(open('/tmp/_mpm_body'))   # /recommend response still cached? re-fetch
except:
    body = {}
# re-fetch recommend
import urllib.request
body = json.loads(urllib.request.urlopen("http://localhost:8000/api/v1/stocks/recommend", timeout=10).read())
data = body.get("data", [])
green  = "\033[1;32m"; red = "\033[1;31m"; reset = "\033[0m"; yellow = "\033[1;33m"
for s in data:
    code   = s.get("stock_code","?")
    name   = s.get("stock_name","?")
    ep     = s.get("entry_price")
    fep    = s.get("first_entry_price")
    days   = s.get("consecutive_days", 1)
    srcs   = s.get("source_conditions", [])
    cp     = s.get("current_price")
    cr     = s.get("change_rate")
    color  = green if (cr or 0) >= 0 else "\033[1;34m"
    print(f"    {name}({code})  현재가={cp}  {color}{cr:+.2f}%{reset}  "
          f"entry={ep}  first={fep}  days={days}  sources={srcs}")
PY
fi

# ════════════════════════════════════════
# 프론트엔드
# ════════════════════════════════════════
if [ "$CHECK_FE" = true ]; then
    hdr "[Frontend]  $FE_URL"

    check_port 3000 "Next.js"

    check_api "GET / (홈)"      "$FE_URL/"           ""   # 307 리다이렉트도 정상
    check_api "GET /stocks"     "$FE_URL/stocks"
    check_api "GET /portfolio"  "$FE_URL/portfolio"
    check_api "GET /virtual"    "$FE_URL/virtual"
    check_api "GET /market"     "$FE_URL/market"
fi

# ── 결과 요약 ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}========================================${RESET}"
total=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}  전체 통과: $PASS / $total${RESET}"
else
    echo -e "${RED}${BOLD}  실패: $FAIL / $total${RESET}  (통과: $PASS)"
fi
echo -e "${BOLD}========================================${RESET}"
echo ""

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
