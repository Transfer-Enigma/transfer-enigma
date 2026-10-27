#!/bin/bash
# Full cache test: wipe data -> wipe policies -> load Google Sheets ->
# cold calculate with real points -> enable policies -> re-send -> verify cache
set -uo pipefail

BASE="http://localhost"
TODAY=$(date +%F)
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

check_gt() {
  local name="$1" actual="$2" expected="$3"
  if [ "$actual" -gt "$expected" ] 2>/dev/null; then
    PASS_COUNT=$((PASS_COUNT + 1))
    echo "  PASS: $name ($actual > $expected)"
  else
    FAIL_COUNT=$((FAIL_COUNT + 1))
    echo "  FAIL: $name — expected > $expected, got '$actual'"
  fi
}

policy_ids() {
  curl -s -X GET "$BASE/admin/api/cache/policies" -H "$AUTH" | jq -r '.[].id' 2>/dev/null
}

delete_all_policies() {
  for id in $(policy_ids); do
    curl -s -X DELETE "$BASE/admin/api/cache/policies/$id" -H "$AUTH" >/dev/null 2>&1
  done
}

create_policy() {
  local body="$1"
  curl -s -X POST "$BASE/admin/api/cache/policies" -H "$AUTH" \
    -H "Content-Type: application/json" -d "$body" | jq -r '.id' 2>/dev/null
}

entries_count() {
  local pid="$1"
  curl -s -X GET "$BASE/admin/api/cache/policies/$pid/entries" -H "$AUTH" \
    | jq -r '.count // 0' 2>/dev/null
}

redis_keys() {
  docker compose -f docker-compose.hot-dev.yml exec -T redis redis-cli KEYS "$1" 2>/dev/null | sed '/^$/d'
}

echo "=================================================================="
echo "1. Delete all cache policies"
echo "=================================================================="
BEFORE=$(policy_ids | wc -l | tr -d ' ')
delete_all_policies
AFTER=$(policy_ids | wc -l | tr -d ' ')
check "policies removed" "$AFTER" "0"
echo "  (was $BEFORE policies)"

echo "=================================================================="
echo "2. Erase all business data"
echo "=================================================================="
HTTP=$(curl -s -o /tmp/erase.out -w "%{http_code}" -X DELETE "$BASE/admin/api/db/data" -H "$AUTH")
check "erase data HTTP" "$HTTP" "204"

echo "=================================================================="
echo "3. Clean load from Google Sheets"
echo "=================================================================="
HTTP=$(curl -s -o /tmp/gsheets.out -w "%{http_code}" --max-time 900 \
  -X POST "$BASE/admin/api/data/update-from-gsheets" -H "$AUTH")
check "gsheets import HTTP" "$HTTP" "200"
ROUTES=$(jq -r '.routesInsertedCount // 0' /tmp/gsheets.out 2>/dev/null)
check_gt "routes imported" "$ROUTES" "0"
echo "  imported routes: $ROUTES"

echo "=================================================================="
echo "4. Fetch real points (departures + destinations)"
echo "=================================================================="
curl -s "$BASE/api/v2/points/departures?date=$TODAY" -o /tmp/dep.json
DEP_EXT=$(jq -r '[.data[] | .external_ids[]?] | first // empty' /tmp/dep.json)
DEP_INT=$(jq -r '[.data[] | .ids[]?] | first // empty' /tmp/dep.json)
DEP_COUNT=$(jq -r '[.data[] | .external_ids[]?] | length' /tmp/dep.json)
check_gt "departure points available" "$DEP_COUNT" "0"
echo "  dep external=$DEP_EXT internal=$DEP_INT"

curl -s "$BASE/api/v2/points/destinations?date=$TODAY&departure_point_ids=E$DEP_EXT" -o /tmp/dst.json
DST_EXT=$(jq -r '[.data[] | .external_ids[]?] | first // empty' /tmp/dst.json)
DST_INT=$(jq -r '[.data[] | .ids[]?] | first // empty' /tmp/dst.json)
DST_COUNT=$(jq -r '[.data[] | .external_ids[]?] | length' /tmp/dst.json)
check_gt "destination points available" "$DST_COUNT" "0"
echo "  dst external=$DST_EXT internal=$DST_INT"

cat > /tmp/calc_req.json <<JSON
{
  "dispatchDate": "$TODAY",
  "departureInternalIds": [$DEP_INT],
  "destinationInternalIds": [$DST_INT],
  "departureExternalIds": ["$DEP_EXT"],
  "destinationExternalIds": ["$DST_EXT"],
  "cargoWeight": 15,
  "containerType": 20
}
JSON

echo "=================================================================="
echo "5. Cold calculate (no cache policies configured)"
echo "=================================================================="
HTTP=$(curl -s -o /tmp/calc_cold.json -w "%{http_code}" -X POST "$BASE/api/v2/routes/calculate" \
  -H "Content-Type: application/json" --data @/tmp/calc_req.json)
check "cold calculate HTTP" "$HTTP" "200"
COLD_ROUTES=$(jq -r '.routes | length' /tmp/calc_cold.json 2>/dev/null)
check_gt "cold routes returned" "$COLD_ROUTES" "0"
COLD_ERRORS=$(jq -r '.errors | length' /tmp/calc_cold.json 2>/dev/null)
check "cold errors" "$COLD_ERRORS" "0"
echo "  routes=$COLD_ROUTES errors=$COLD_ERRORS"

echo "=================================================================="
echo "6. Enable cache policies"
echo "=================================================================="
PID_RATES=$(create_policy '{"source":null,"entity":"rates","enabled":true,"ttl":300}')
PID_DEP=$(create_policy "{\"source\":\"fesco\",\"entity\":\"departures_today\",\"enabled\":true,\"ttl\":300}")
PID_DST=$(create_policy "{\"source\":\"fesco\",\"entity\":\"destinations_today\",\"enabled\":true,\"ttl\":300}")
PID_CONT=$(create_policy "{\"source\":\"fesco\",\"entity\":\"containers_today\",\"enabled\":true,\"ttl\":300}")
PID_ROUTES=$(create_policy "{\"source\":\"fesco\",\"entity\":\"routes_today\",\"enabled\":true,\"ttl\":300}")
PID_DEP_PLAIN=$(create_policy "{\"source\":\"fesco\",\"entity\":\"departures\",\"enabled\":true,\"ttl\":300}")
PID_ROUTES_PLAIN=$(create_policy "{\"source\":\"fesco\",\"entity\":\"routes\",\"enabled\":true,\"ttl\":300}")
PID_CONT_PLAIN=$(create_policy "{\"source\":\"fesco\",\"entity\":\"containers\",\"enabled\":true,\"ttl\":300}")

for v in "$PID_RATES" "$PID_DEP" "$PID_DST" "$PID_CONT" "$PID_ROUTES" \
         "$PID_DEP_PLAIN" "$PID_ROUTES_PLAIN" "$PID_CONT_PLAIN"; do
  case "$v" in ''|*[!0-9]*) FAIL_COUNT=$((FAIL_COUNT + 1)); echo "  FAIL: policy id '$v'";; esac
done
POLICY_COUNT=$(policy_ids | wc -l | tr -d ' ')
check "policy count" "$POLICY_COUNT" "8"
echo "  rates=$PID_RATES dep=$PID_DEP dst=$PID_DST cont=$PID_CONT routes=$PID_ROUTES"

echo "  waiting for policy sync between processes (15s)..."
sleep 15

echo "=================================================================="
echo "7. Re-send requests to fill the cache"
echo "=================================================================="
curl -s "$BASE/api/v2/rates" >/dev/null
curl -s "$BASE/api/v2/points/departures?date=$TODAY" >/dev/null
curl -s "$BASE/api/v2/points/destinations?date=$TODAY&departure_point_ids=E$DEP_EXT" >/dev/null
curl -s -o /tmp/calc_warm1.json -X POST "$BASE/api/v2/routes/calculate" \
  -H "Content-Type: application/json" --data @/tmp/calc_req.json
sleep 5

WARM_ROUTES=$(jq -r '.routes | length' /tmp/calc_warm1.json 2>/dev/null)
check "warm calculate routes" "$WARM_ROUTES" "$COLD_ROUTES"

echo "=================================================================="
echo "8. Verify cache entries per policy"
echo "=================================================================="
for pair in "rates:$PID_RATES" "departures_today:$PID_DEP" "destinations_today:$PID_DST" \
            "containers_today:$PID_CONT" "routes_today:$PID_ROUTES"; do
  name="${pair%%:*}"
  pid="${pair##*:}"
  count=$(entries_count "$pid")
  check_gt "$name entries" "$count" "0"
done

echo "  -- non-today policies (no data expected on today's date):"
for pair in "departures:$PID_DEP_PLAIN" "routes:$PID_ROUTES_PLAIN" "containers:$PID_CONT_PLAIN"; do
  name="${pair%%:*}"
  pid="${pair##*:}"
  count=$(entries_count "$pid")
  echo "     $name entries=$count (expected 0: date is today, *_today entity used)"
done

echo "=================================================================="
echo "9. Cache stays warm, Google Sheets re-import"
echo "=================================================================="
BEFORE_KEYS=$(docker compose -f docker-compose.hot-dev.yml exec -T redis redis-cli DBSIZE 2>/dev/null | tr -d '\r')
echo "  redis keys before re-import: $BEFORE_KEYS"
HTTP=$(curl -s -o /tmp/gsheets2.out -w "%{http_code}" --max-time 900 \
  -X POST "$BASE/admin/api/data/update-from-gsheets" -H "$AUTH")
check "gsheets re-import HTTP" "$HTTP" "200"
ROUTES2=$(jq -r '.routesInsertedCount // 0' /tmp/gsheets2.out 2>/dev/null)
check_gt "re-imported routes" "$ROUTES2" "0"

AFTER_KEYS=$(docker compose -f docker-compose.hot-dev.yml exec -T redis redis-cli DBSIZE 2>/dev/null | tr -d '\r')
echo "  redis keys after re-import: $AFTER_KEYS"
echo "  note: internal DB data (routes/points/companies) is read straight from"
echo "        the database and is never cached, so an import needs no invalidation."

curl -s -o /tmp/calc_after.json -X POST "$BASE/api/v2/routes/calculate" \
  -H "Content-Type: application/json" --data @/tmp/calc_req.json
AFTER_ROUTES=$(jq -r '.routes | length' /tmp/calc_after.json 2>/dev/null)
check "calculate after re-import" "$AFTER_ROUTES" "$COLD_ROUTES"

echo "=================================================================="
echo "10. Invalidation still works after the whole flow"
echo "=================================================================="
DELETED=$(curl -s -X POST "$BASE/admin/api/cache/policies/$PID_ROUTES/invalidate" -H "$AUTH" | jq -r '.deleted')
check_gt "invalidate routes_today" "$DELETED" "0"
COUNT=$(entries_count "$PID_ROUTES")
check "routes_today emptied" "$COUNT" "0"
LEFT=$(entries_count "$PID_CONT")
check_gt "containers untouched" "$LEFT" "0"

echo "=================================================================="
echo "11. Cleanup"
echo "=================================================================="
delete_all_policies
check "policies removed" "$(policy_ids | wc -l | tr -d ' ')" "0"

echo ""
echo "=================================================================="
echo "RESULT: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "=================================================================="
[ "$FAIL_COUNT" -eq 0 ]
