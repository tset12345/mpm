#!/usr/bin/env bash
# MPM 개발 환경 실행 스크립트
#
# Usage:
#   ./dev.sh                  # 전체 실행 (db + backend + frontend)
#   ./dev.sh --backend        # 백엔드만
#   ./dev.sh --frontend       # 프론트엔드만
#   ./dev.sh --db             # DB 마이그레이션만
#   ./dev.sh -b -f            # 백엔드 + 프론트엔드
#
# Options:
#   -d, --db          Supabase DB 마이그레이션 실행
#   -b, --backend     FastAPI 백엔드 서버 시작 (포트 8000)
#   -f, --frontend    Next.js 프론트엔드 서버 시작 (포트 3000)
#   -h, --help        도움말 출력

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
MIGRATION_FILE="$ROOT_DIR/supabase/migrations/001_initial_schema.sql"

RUN_DB=false
RUN_BACKEND=false
RUN_FRONTEND=false

BACKEND_PID=""
FRONTEND_PID=""

# ── 색상 출력 헬퍼 ──────────────────────────────────────────────────────────
info()    { echo -e "\033[1;34m[MPM]\033[0m $*"; }
success() { echo -e "\033[1;32m[MPM]\033[0m $*"; }
warn()    { echo -e "\033[1;33m[MPM]\033[0m $*"; }
error()   { echo -e "\033[1;31m[MPM]\033[0m $*" >&2; }

# ── 인자 파싱 ───────────────────────────────────────────────────────────────
if [ $# -eq 0 ]; then
    RUN_DB=true
    RUN_BACKEND=true
    RUN_FRONTEND=true
else
    for arg in "$@"; do
        case $arg in
            -d|--db)       RUN_DB=true ;;
            -b|--backend)  RUN_BACKEND=true ;;
            -f|--frontend) RUN_FRONTEND=true ;;
            -h|--help)
                sed -n '/^# Usage:/,/^[^#]/{ /^[^#]/d; s/^# \{0,2\}//; p }' "$0"
                exit 0
                ;;
            *)
                error "알 수 없는 옵션: $arg"
                error "사용법: ./dev.sh [-d] [-b] [-f]  또는  --help"
                exit 1
                ;;
        esac
    done
fi

# ── 종료 시 백그라운드 프로세스 정리 ─────────────────────────────────────────
cleanup() {
    echo ""
    info "종료 중..."
    [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null && info "백엔드 종료 (PID $BACKEND_PID)"
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && info "프론트엔드 종료 (PID $FRONTEND_PID)"
    exit 0
}
trap cleanup INT TERM

# ── .env 로드 ────────────────────────────────────────────────────────────────
ENV_FILE="$BACKEND_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
    info ".env 로드 완료"
else
    warn "backend/.env 파일이 없습니다."
    warn "  cp $BACKEND_DIR/.env.example $ENV_FILE  후 값을 채워주세요."
    if [ "$RUN_DB" = true ] || [ "$RUN_BACKEND" = true ]; then
        error "백엔드/DB 실행에 .env가 필요합니다. 중단합니다."
        exit 1
    fi
fi

# ── 2. DB 마이그레이션 ────────────────────────────────────────────────────────
run_db() {
    info "DB 마이그레이션 실행 중..."

    if command -v psql &>/dev/null && [ -n "${DATABASE_URL:-}" ]; then
        psql "$DATABASE_URL" -f "$MIGRATION_FILE"
        success "마이그레이션 완료 (psql)"

    elif command -v supabase &>/dev/null; then
        supabase db push --db-url "${DATABASE_URL:-}"
        success "마이그레이션 완료 (supabase CLI)"

    else
        warn "psql 또는 supabase CLI가 설치되어 있지 않습니다."
        warn "Supabase 대시보드 > SQL Editor 에서 아래 파일을 직접 실행하세요:"
        warn "  $MIGRATION_FILE"
        warn "또는: brew install postgresql  후 재실행"
    fi
}

# ── 3. 백엔드 ────────────────────────────────────────────────────────────────
run_backend() {
    info "백엔드 준비 중..."
    cd "$BACKEND_DIR"

    VENV_DIR="$BACKEND_DIR/.venv"
    if [ ! -d "$VENV_DIR" ]; then
        info "가상환경 생성 중..."
        python3 -m venv "$VENV_DIR"
    fi

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    info "의존성 설치 중..."
    pip install -q -r requirements.txt

    info "FastAPI 서버 시작 → http://localhost:8000"
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    success "백엔드 실행 중 (PID $BACKEND_PID)"

    cd "$ROOT_DIR"
}

# ── 4. 프론트엔드 ────────────────────────────────────────────────────────────
run_frontend() {
    info "프론트엔드 준비 중..."
    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        info "패키지 설치 중..."
        npm install
    fi

    # NEXT_PUBLIC_API_URL 기본값 설정
    export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"

    info "Next.js 서버 시작 → http://localhost:3000"
    npm run dev &
    FRONTEND_PID=$!
    success "프론트엔드 실행 중 (PID $FRONTEND_PID)"

    cd "$ROOT_DIR"
}

# ── 실행 ─────────────────────────────────────────────────────────────────────
echo ""
info "========================================"
info "  MPM 개발 환경"
info "========================================"
echo ""

[ "$RUN_DB" = true ]       && run_db
[ "$RUN_BACKEND" = true ]  && run_backend
[ "$RUN_FRONTEND" = true ] && run_frontend

if [ "$RUN_BACKEND" = true ] || [ "$RUN_FRONTEND" = true ]; then
    echo ""
    success "서버가 실행 중입니다. 종료하려면 Ctrl+C 를 누르세요."
    wait
fi
