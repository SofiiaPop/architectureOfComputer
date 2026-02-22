import argparse
import threading
import time
import requests

FACADE_URL = "http://127.0.0.1:8000"
NUM_CLIENTS  = 10
NUM_REQUESTS = 10_000


def worker(user_id: str, amount: float, n: int, results: list, idx: int):
    """Send n POST /transaction requests and record total time."""
    ok = 0; errors = 0
    t0 = time.perf_counter()
    for _ in range(n):
        try:
            r = requests.post(f"{FACADE_URL}/transaction",
                              json={"user_id": user_id, "amount": amount},
                              timeout=30)
            if r.status_code == 200:
                ok += 1
            else:
                errors += 1
        except Exception:
            errors += 1
    elapsed = time.perf_counter() - t0
    results[idx] = {"user_id": user_id, "ok": ok, "errors": errors,
                    "elapsed_s": round(elapsed, 3)}


def reset_stats():
    requests.delete(f"{FACADE_URL}/stats", timeout=5)


def get_stats():
    return requests.get(f"{FACADE_URL}/stats", timeout=5).json()


def get_accounts():
    return requests.get(f"{FACADE_URL}/accounts", timeout=5).json()


def run_scenario(scenario: int, n: int):
    print(f"\n{'='*60}")
    print(f"SCENARIO {scenario}  |  {NUM_CLIENTS} clients × {n:,} requests each")
    print(f"{'='*60}")

    if scenario == 1:
        users  = [f"user_{i}" for i in range(1, NUM_CLIENTS + 1)]
        amount = 1.0
        print("Each client credits their OWN account. Expected balance per account: "
              f"{n:,}")
    else:
        users  = ["shared_user"] * NUM_CLIENTS
        amount = 1.0
        print("All clients credit the SAME account. Expected balance: "
              f"{n * NUM_CLIENTS:,}")

    reset_stats()
    results = [None] * NUM_CLIENTS
    threads = [
        threading.Thread(target=worker,
                         args=(users[i], amount, n, results, i))
        for i in range(NUM_CLIENTS)
    ]

    wall_start = time.perf_counter()
    for t in threads: t.start()
    for t in threads: t.join()
    wall_elapsed = time.perf_counter() - wall_start

    total_ok     = sum(r["ok"]     for r in results)
    total_errors = sum(r["errors"] for r in results)
    total_reqs   = total_ok + total_errors
    rps          = total_ok / wall_elapsed

    print(f"\n── Results ──────────────────────────────")
    for r in results:
        print(f"  {r['user_id']:15s}  ok={r['ok']:6d}  errors={r['errors']:4d}  "
              f"time={r['elapsed_s']:.2f}s")

    print(f"\n── Summary ──────────────────────────────")
    print(f"  Total requests : {total_reqs:,}")
    print(f"  Successful     : {total_ok:,}")
    print(f"  Errors         : {total_errors:,}")
    print(f"  Wall time      : {wall_elapsed:.2f}s")
    print(f"  Throughput     : {rps:,.0f} req/s")

    stats = get_stats()
    ls = stats["logging_service"]
    cs = stats["counter_service"]
    print(f"\n── Service timing (accumulated) ─────────")
    print(f"  logging-service : {ls['total_calls']:,} calls  "
          f"total={ls['total_ms']:.0f}ms  avg={ls['avg_ms']:.2f}ms/call")
    print(f"  counter-service : {cs['total_calls']:,} calls  "
          f"total={cs['total_ms']:.0f}ms  avg={cs['avg_ms']:.2f}ms/call")

    print(f"\n── Final balances ───────────────────────")
    accounts = get_accounts().get("balances", {})
    for uid, bal in sorted(accounts.items()):
        print(f"  {uid:15s}  balance = {bal:,.0f}")

    return rps


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, choices=[1, 2], default=1)
    parser.add_argument("--requests", type=int, default=NUM_REQUESTS,
                        help="Requests per client (default 10000)")
    args = parser.parse_args()

    try:
        requests.get(f"{FACADE_URL}/accounts", timeout=3)
    except Exception:
        print(f"ERROR: Cannot reach facade-service at {FACADE_URL}")
        print("Make sure all services are running (docker compose up)")
        exit(1)

    run_scenario(args.scenario, args.requests)