# Lab 3 — Microservices with Hazelcast Distributed Map

## Architecture

```
Client (curl / Postman)
        │
        ▼  HTTP POST/GET
  ┌───────────┐          randomly picks 1 of 3       ┌───────────────────┐
  │  facade   │─────────────────────────────────────► │  logging-svc :1   │
  │  :8000    │   (falls back on unavailable)          │  logging-svc :2   │
  └─────┬─────┘                                        │  logging-svc :3   │
        │                                              └────────┬──────────┘
        │ HTTP GET                                              │ Hazelcast
        ▼                                                       │ Python Client
  ┌──────────────┐                              ┌──────────────▼─────────────┐
  │ counter-svc  │                              │  Hazelcast cluster (3 nodes)│
  │   :8010      │                              │  HZ1:5701  HZ2:5701         │
  └──────┬───────┘                              │  HZ3:5701                   │
         │ asyncpg                              │  Distributed Map "messages" │
         ▼                                      └─────────────────────────────┘
  ┌──────────────┐
  │  PostgreSQL  │
  │    :5432     │
  └──────────────┘
```

## Services & Ports

| Container       | Host Port | Description                              |
|-----------------|-----------|------------------------------------------|
| facade          | 8000      | Entry point — random routes to logging   |
| logging1        | 8001      | Logging instance 1 — Hazelcast client    |
| logging2        | 8002      | Logging instance 2 — Hazelcast client    |
| logging3        | 8003      | Logging instance 3 — Hazelcast client    |
| counter         | 8010      | Counter service — PostgreSQL backend     |
| hazelcast1      | 5701      | Hazelcast node 1                         |
| hazelcast2      | 5702      | Hazelcast node 2                         |
| hazelcast3      | 5703      | Hazelcast node 3                         |
| hazelcast-mc    | 8080      | Hazelcast Management Center (UI)         |
| postgres        | 5432      | PostgreSQL 16                            |

## Quick Start

```bash
# Build images and start the whole stack
docker-compose up --build -d

# Watch startup — Hazelcast cluster forms, then logging services connect
docker-compose logs -f hazelcast1 hazelcast2 hazelcast3

# Wait until facade is healthy (~40-60s total)
docker-compose ps
```

## Functional Test — 10 Transactions

```bash
# POST msg1 through msg10
for i in $(seq 1 10); do
  curl -s -X POST http://localhost:8000/ \
    -H "Content-Type: application/json" \
    -d "{\"msg\": \"msg$i\"}" | python3 -m json.tool
done

# GET all messages back
curl -s http://localhost:8000/ | python3 -m json.tool

# See which instance handled each write (instance ID is in every log line)
docker logs logging1 | grep Stored
docker logs logging2 | grep Stored
docker logs logging3 | grep Stored
```

Or use the automated script:
```bash
chmod +x test.sh && ./test.sh
```

## Fault Tolerance Tests

### Stop 2 logging-service instances

```bash
docker stop logging2 logging3
# facade falls back to logging1 automatically
curl -X POST http://localhost:8000/ -H "Content-Type: application/json" -d '{"msg":"after_stop"}'
curl -s http://localhost:8000/ | python3 -m json.tool
docker start logging2 logging3
```

### Stop 2 Hazelcast nodes (data survives on remaining node)

```bash
docker stop hazelcast2 hazelcast3
# Data is still accessible — backup-count=1 in hazelcast.xml
curl -s http://localhost:8000/ | python3 -m json.tool
docker start hazelcast2 hazelcast3
```

### Automated fault tolerance test
```bash
chmod +x fault_tolerance_test.sh && ./fault_tolerance_test.sh
```

## Performance Test

```bash
chmod +x perf_test.sh
./perf_test.sh http://localhost:8000 100
```

## Management Center (UI)

Open **http://localhost:8080** in your browser after startup.
It shows: cluster members, map sizes, throughput graphs — great for screenshots.

## Key Design Notes

**Hazelcast Distributed Map** — all 3 logging instances share a single logical map `"messages"`.
Data is partitioned + replicated (`backup-count=1`) across nodes, so losing 1 node loses no data.
The `hazelcast.xml` config uses **TCP-IP member discovery** (explicit member list) instead of
multicast, which is required in Docker environments.

**Random routing with sequential fallback** — facade shuffles the logging URL list on every request
and walks through it until one responds. This gives ~uniform distribution during normal operation
and automatic failover when instances are down.

**PostgreSQL** — counter-service uses `asyncpg` for non-blocking Postgres access. The `messages`
table is created automatically on startup. Connection retries handle the race between the Python
process starting and Postgres becoming ready.

## Stop Everything

```bash
docker-compose down -v   # -v also removes the pgdata volume
```
