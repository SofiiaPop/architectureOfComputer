#!/usr/bin/env bash
# test.sh — sends 10 POST requests, then GETs all messages
# Usage: ./test.sh [BASE_URL]
# Default BASE_URL: http://localhost:8000

BASE="${1:-http://localhost:8000}"
echo "=== Testing against $BASE ==="

echo ""
echo "--- Sending 10 POST requests ---"
for i in $(seq 1 10); do
  MSG="msg$i"
  RESP=$(curl -s -X POST "$BASE/" \
    -H "Content-Type: application/json" \
    -d "{\"msg\": \"$MSG\"}")
  echo "POST $MSG → $RESP"
  sleep 0.2
done

echo ""
echo "--- GET all messages ---"
curl -s "$BASE/" | python3 -m json.tool

echo ""
echo "--- Checking logging instance logs ---"
echo "(Run: docker logs logging1 | tail -20)"
echo "(Run: docker logs logging2 | tail -20)"
echo "(Run: docker logs logging3 | tail -20)"
