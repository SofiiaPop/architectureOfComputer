#!/usr/bin/env bash
# perf_test.sh — performance test using curl timing
# Sends N requests and measures avg response time
BASE="${1:-http://localhost:8000}"
N="${2:-100}"

echo "=== Performance Test: $N POST requests to $BASE ==="
START=$(date +%s%N)

for i in $(seq 1 $N); do
  curl -s -o /dev/null -X POST "$BASE/" \
    -H "Content-Type: application/json" \
    -d "{\"msg\": \"perf_msg_$i\"}"
done

END=$(date +%s%N)
ELAPSED=$(( (END - START) / 1000000 ))  # ms
echo "Total time: ${ELAPSED}ms for $N requests"
echo "Avg per request: $(echo "scale=2; $ELAPSED / $N" | bc)ms"
echo "Throughput: $(echo "scale=2; $N * 1000 / $ELAPSED" | bc) req/s"

echo ""
echo "=== GET performance ==="
time curl -s "$BASE/" > /dev/null
