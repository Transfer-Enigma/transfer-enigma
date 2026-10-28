#!/bin/bash
# Cache test for the post-removal API:
# no default policies are seeded, creation/deletion endpoints are removed,
# only invalidation (+ entries) remain.
set -uo pipefail

BASE="http://localhost"
PASS_COUNT=0
FAIL_COUNT=0

TOKEN=$(curl -s -X POST "$BASE/api/user/login" -H "Content-Type: application/json" \
  -d '{"login":"ADMIN","password":"PASS"}' -D - 2>/dev/null \
  | grep -oP 'access_token_cookie=\K[^;]+' | head -1)

if [ -z "$TOKEN" ]; then
  echo "FAIL: cannot authenticate"
  exit 1
fi
AUTH="Cookie: access_token_cookie=$TOKEN"

check() {
  local name="$1" actual="$2" expected="$3"
  if [ "$actual" = "$expected" ]; then
    PASS_COUNT=$((PASS_COUNT + 1))
    echo "  PASS: $name ($actual)"
  else
    FAIL_COUNT=$((FAIL_COUNT + 1))
    echo "  FAIL: $name — expected '$expected', got '$actual'"
  fi
}

echo "=================================================================="
echo "1. Default cache policies: none seeded (pre-branch state)"
echo "=================================================================="
POLICIES=$(curl -s -X GET "$BASE/admin/api/cache/policies" -H "$AUTH")
COUNT=$(echo "$POLICES" | jq -r 'length // 0' 2>/dev/null)
check "default policies count" "$COUNT" "0"
echo "  policies: $POLICIES"

echo "=================================================================="
echo "2. Invalidation endpoints respond (nothing to invalidate)"
echo "=================================================================="
DELETED_ALL=$(curl -s -X POST "$BASE/admin/api/cache/policies/invalidate" -H "$AUTH" \
  | jq -r '.deleted // 0' 2>/dev/null)
check "invalidate all deleted" "$DELETED_ALL" "0"

DELETED_ONE=$(curl -s -o /tmp/inv_one.out -w "%{http_code}" -X POST \
  "$BASE/admin/api/cache/policies/999999/invalidate" -H "$AUTH")
check "invalidate missing policy 404" "$DELETED_ONE" "404"

ENTRIES=$(curl -s -o /tmp/entries.out -w "%{http_code}" -X GET \
  "$BASE/admin/api/cache/policies/999999/entries?limit=5" -H "$AUTH")
check "entries missing policy 404" "$ENTRIES" "404"

echo ""
echo "=================================================================="
echo "RESULT: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "=================================================================="
[ "$FAIL_COUNT" -eq 0 ]
