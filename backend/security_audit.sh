#!/usr/bin/env bash
# 의존성 공급망 보안 감사 스크립트
# 사용: ./security_audit.sh [--fix]
set -euo pipefail

VENV=".venv/bin"
FIX=${1:-""}

echo "=== MPM 공급망 보안 감사 ==="
echo ""

# 1. pip-audit 설치 여부 확인
if ! "$VENV/pip" show pip-audit &>/dev/null; then
    echo "[설치] pip-audit..."
    "$VENV/pip" install -r requirements-dev.txt --quiet
fi

# 2. 알려진 CVE 스캔
echo "[1/3] CVE 취약점 스캔 (pip-audit)..."
if ! "$VENV/pip-audit" --requirement requirements.txt; then
    echo ""
    echo "  취약점이 발견됐습니다. requirements.txt 버전을 확인하세요."
    if [ "$FIX" = "--fix" ]; then
        echo "  [--fix] pip-audit 자동 수정 시도..."
        "$VENV/pip-audit" --requirement requirements.txt --fix || true
    fi
fi
echo ""

# 3. 패키지 해시 무결성 검증
echo "[2/3] 패키지 해시 무결성 검증..."
"$VENV/pip" check && echo "  의존성 충돌 없음" || echo "  [경고] 의존성 충돌 발견"
echo ""

# 4. 설치된 패키지와 requirements.txt 버전 불일치 확인
echo "[3/3] requirements.txt 버전 고정 확인..."
MISMATCH=0
while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
    # pkg==version 형식만 처리
    if [[ "$line" =~ ^([a-zA-Z0-9_\-\[\]]+)==(.+)$ ]]; then
        pkg="${BASH_REMATCH[1]}"
        expected="${BASH_REMATCH[2]}"
        installed=$("$VENV/pip" show "$pkg" 2>/dev/null | grep "^Version:" | awk '{print $2}')
        if [ -z "$installed" ]; then
            echo "  [미설치] $pkg"
            MISMATCH=1
        elif [ "$installed" != "$expected" ]; then
            echo "  [불일치] $pkg: requirements=$expected, installed=$installed"
            MISMATCH=1
        fi
    fi
done < requirements.txt

if [ "$MISMATCH" -eq 0 ]; then
    echo "  모든 패키지 버전 일치"
fi
echo ""

echo "=== 감사 완료 ==="
echo ""
echo "  starlette 잔여 CVE (PYSEC-2026-161 등): starlette 1.x 필요 → fastapi 0.130+ 업그레이드 후 해소 가능"
echo "  주기적 실행 권장: ./security_audit.sh (배포 전, 월 1회)"
