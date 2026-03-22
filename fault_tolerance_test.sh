#!/usr/bin/env bash
# fault_tolerance_test.sh — demonstrates fault tolerance
BASE="${1:-http://localhost:8000}"

echo "=== Fault Tolerance Test ==="

echo ""
echo "--- [1] Stop logging2 and logging3, keep logging1 ---"
docker stop logging2 logging3
sleep 2
echo "Sending 2 more messages with only logging1 running:"
curl -s -X POST "$BASE/" -H "Content-Type: application/json" -d '{"msg": "fault_test_1"}' | python3 -m json.tool
curl -s -X POST "$BASE/" -H "Content-Type: application/json" -d '{"msg": "fault_test_2"}' | python3 -m json.tool

echo ""
echo "GET messages (only logging1 available):"
curl -s "$BASE/" | python3 -m json.tool

echo ""
echo "--- [2] Restart stopped instances ---"
docker start logging2 logging3
sleep 3

echo ""
echo "--- [3] Stop 2 Hazelcast nodes ---"
docker stop hazelcast2 hazelcast3
sleep 3
echo "GET messages with only hazelcast1 running:"
curl -s "$BASE/" | python3 -m json.tool

echo ""
echo "--- [4] Restore cluster ---"
docker start hazelcast2 hazelcast3
sleep 5
echo "Final GET after full restore:"
curl -s "$BASE/" | python3 -m json.tool

echo ""
echo "=== Fault tolerance test complete ==="
