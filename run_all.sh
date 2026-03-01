#!/usr/bin/env bash
# ===========================================================
# Hazelcast Task 2 — Full Demo Runner
# ===========================================================
# Prerequisites:
#   - Docker & Docker Compose installed
#   - Java 17+ and Maven installed
#   - Internet access to pull Docker images
# ===========================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCKER_DIR="$PROJECT_DIR/docker"

echo "============================================"
echo " Hazelcast Task 2 — Demo Runner"
echo "============================================"

# ---- Step 1: Start cluster ----
echo ""
echo "[1/6] Starting 3-node Hazelcast cluster + Management Center..."
cd "$DOCKER_DIR"
docker compose up -d

echo "Waiting 15s for cluster to form..."
sleep 15
echo "Cluster should be up. Check: http://localhost:8080 (Management Center)"
echo "  Default login: admin / hazelcast"

# ---- Step 2: Build Java project ----
echo ""
echo "[2/6] Building Java project..."
cd "$PROJECT_DIR"
mvn package -q -DskipTests

JAR="$PROJECT_DIR/target/hazelcast-task-1.0-SNAPSHOT.jar"

run_class() {
    local CLASS=$1
    echo ""
    echo "Running: $CLASS"
    echo "-------------------------------------------"
    java -cp "$JAR" "com.task.hazelcast.$CLASS"
    echo "-------------------------------------------"
    echo ""
}

# ---- Step 3: Distributed Map (1000 entries) ----
echo ""
echo "[3/6] Task 3 — Distributed Map (1000 entries)"
echo ">>> After this runs, check Management Center -> Storage -> Maps -> 'entries' -> Partitions"
echo ">>> Press ENTER inside the app to continue after inspecting MC."
run_class DistributedMapDemo

# ---- Step 4: Node failure simulation ----
echo ""
echo "[4/6] Demonstrating node failure (killing hazelcast3)..."
docker stop hazelcast3
echo "hazelcast3 stopped. Check MC for partition redistribution (wait ~10s)."
sleep 10
echo "Restarting hazelcast3..."
docker start hazelcast3
sleep 10

echo "Now stopping hazelcast2 and hazelcast3 SEQUENTIALLY..."
docker stop hazelcast2
sleep 5
docker stop hazelcast3
sleep 5
echo "Two nodes down. Data accessible? Try reading the map with 1 remaining node..."
echo "  With backup-count=1, losing 2 nodes out of 3 may cause partition data loss!"
echo "  With backup-count=2, all data would survive."
docker start hazelcast2 hazelcast3
sleep 10

echo "Now stopping hazelcast2 and hazelcast3 SIMULTANEOUSLY (simulating crash)..."
docker kill hazelcast2 hazelcast3
sleep 5
echo "Two nodes killed. Single-node cluster may have lost some partitions."
docker start hazelcast2 hazelcast3
sleep 15

# ---- Step 5: Lock benchmark ----
echo ""
echo "[5/6] Tasks 4-7 — Lock Benchmark (No Lock / Pessimistic / Optimistic)"
run_class LockBenchmark

# ---- Step 6: Bounded Queue ----
echo ""
echo "[6/6] Task 8 — Bounded Queue Demo (1 producer + 2 consumers)"
run_class BoundedQueueDemo

echo ""
echo "Task 8b — Queue Full Demo (producer with no consumers)"
run_class QueueFullDemo

echo ""
echo "============================================"
echo " All demos complete!"
echo " Management Center: http://localhost:8080"
echo "============================================"

echo ""
read -p "Tear down cluster? (y/N) " TEAR
if [[ "$TEAR" == "y" || "$TEAR" == "Y" ]]; then
    cd "$DOCKER_DIR"
    docker compose down -v
    echo "Cluster removed."
fi