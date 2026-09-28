"""Site performance benchmark (v82) — auto-stress-test."""
import time
import httpx


def benchmark_url(url: str, concurrent: int = 10, total: int = 100) -> dict:
    """Benchmark a URL with concurrent requests."""
    import concurrent.futures
    results = {"success": 0, "failed": 0, "latencies": []}
    
    def make_request():
        t0 = time.time()
        try:
            r = httpx.get(url, timeout=30)
            return r.status_code, (time.time() - t0) * 1000
        except Exception:
            return 0, (time.time() - t0) * 1000
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent) as pool:
        futures = [pool.submit(make_request) for _ in range(total)]
        for f in concurrent.futures.as_completed(futures):
            status, latency = f.result()
            if status == 200:
                results["success"] += 1
                results["latencies"].append(latency)
            else:
                results["failed"] += 1
    
    latencies = sorted(results["latencies"])
    return {
        "url": url, "total": total, "concurrent": concurrent,
        "success": results["success"], "failed": results["failed"],
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
        "p50_ms": round(latencies[len(latencies)//2], 1) if latencies else 0,
        "p95_ms": round(latencies[int(len(latencies)*0.95)], 1) if latencies else 0,
        "p99_ms": round(latencies[int(len(latencies)*0.99)], 1) if latencies else 0,
    }
