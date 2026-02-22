# architectureOfComputer
# Microservices

## Running with Docker Compose

```bash
docker compose up --build
```

## API Reference

### POST /transaction
```bash
curl -X POST http://localhost:8000/transaction \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "amount": 100.0}'
# {"transaction_id": "...", "balance": 100.0}

curl -X POST http://localhost:8000/transaction \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "amount": -30.0}'
# {"transaction_id": "...", "balance": 70.0}
```

### GET /user/{user_id}
```bash
curl http://localhost:8000/user/alice
# {"user_id": "alice", "balance": 70.0, "transactions": [...]}
```

### GET /accounts
```bash
curl http://localhost:8000/accounts
# {"balances": {"alice": 70.0, "bob": 200.0}}
```

### GET /stats — service call timing
```bash
curl http://localhost:8000/stats
# {"logging_service": {"total_calls": 5, "total_ms": 12.3, "avg_ms": 2.46},
#  "counter_service":  {"total_calls": 5, "total_ms": 9.1,  "avg_ms": 1.82}}
```

### DELETE /stats — reset timing accumulators
```bash
curl -X DELETE http://localhost:8000/stats
```

## Performance Testing

```bash
# Quick test
python3 perf_test.py --scenario 1 --requests 100
python3 perf_test.py --scenario 2 --requests 100

# Full test
python3 perf_test.py --scenario 1
python3 perf_test.py --scenario 2
```
