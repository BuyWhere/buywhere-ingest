#!/usr/bin/env python3
"""
BUY-32954 basket verification — 300-query REST + MCP rerun.

Adopts the canonical 300-query basket (100 (query, country) pairs x 3 limits)
that was the source of the stale June 1 baseline (REST 0% / MCP 2.67%).

Surfaces:
  REST: GET /v1/products/search (api.buywhere.ai)
  MCP : POST /mcp on mcp.buywhere.ai, method tools/call, name=search_products
        protocolVersion=2024-11-05 (JSON-RPC 2.0 over HTTP)

Per-query success criterion: HTTP 200 (REST) / JSON-RPC ok (MCP) AND result_count > 0.

Outputs (relative to repo root):
  data/basket32954/rest_results.jsonl   # one JSON per query, append-only
  data/basket32954/mcp_results.jsonl    # one JSON per query, append-only
  data/basket32954/rest_summary.json    # written at end
  data/basket32954/mcp_summary.json     # written at end

The script is idempotent: a second invocation skips queries already recorded
in the corresponding jsonl file. The basket hash is identical across runs.
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data", "basket32954")
os.makedirs(DATA_DIR, exist_ok=True)

# Same key constants as the original BUY-31312 basket script.
# BUY-37423: default to the canonical public API host for both surfaces so the
# harness matches the current live path mounted in api/src/server.ts. The
# legacy mcp.buywhere.ai hostname still exists, but api.buywhere.ai/mcp is the
# source-of-truth route used by the current API service and docs.
REST_BASE = os.environ.get("BUYWHERE_REST_BASE", "https://api.buywhere.ai/v1/products/search")
MCP_BASE = os.environ.get("BUYWHERE_MCP_BASE", "https://api.buywhere.ai/mcp")
MCP_PROTOCOL = "2024-11-05"
TIMEOUT = 30

# 100 unique (query, country) pairs — 3 limit values = 300 basket items.
# This is the same basket BUY-31312 ran on 2026-06-05 with REST only,
# and the same basket that produced the stale June 1 baseline (REST 0% / MCP 2.67%).
QUERIES = [
    # SG — premium devices
    ("iPhone 15 Pro", "SG"), ("iPhone 15 Pro Max", "SG"), ("iPhone 14 Pro", "SG"),
    ("iPhone 13", "SG"), ("Samsung Galaxy S24", "SG"), ("Samsung Galaxy S24 Ultra", "SG"),
    ("MacBook Air M3", "SG"), ("MacBook Pro M3", "SG"), ("iPad Pro M4", "SG"),
    ("iPad Air M2", "SG"), ("AirPods Pro 2", "SG"), ("Sony WH-1000XM5", "SG"),
    ("Sony WF-1000XM5", "SG"), ("Bose QuietComfort 45", "SG"), ("Dyson V15 Detect", "SG"),
    ("Dyson Airwrap", "SG"), ("Nintendo Switch OLED", "SG"), ("PS5 Digital", "SG"),
    ("Xbox Series X", "SG"), ("Pixel 8 Pro", "SG"), ("OnePlus 12", "SG"),
    ("Xiaomi 14 Ultra", "SG"), ("ASUS ROG Phone 8", "SG"), ("Oppo Find X7 Pro", "SG"),
    ("Razer Blade 15", "SG"), ("LG OLED C3 55", "SG"), ("Samsung QLED 65", "SG"),
    ("Roborock S8 Pro Ultra", "SG"), ("Ecovacs Deebot X2", "SG"), ("Philips Hue Starter", "SG"),
    # SG — general categories
    ("laptop", "SG"), ("gaming laptop", "SG"), ("ultrabook", "SG"),
    ("wireless earbuds", "SG"), ("true wireless earphones", "SG"),
    ("smartwatch", "SG"), ("fitness tracker", "SG"), ("4K TV", "SG"),
    ("air purifier", "SG"), ("robot vacuum", "SG"), ("espresso machine", "SG"),
    ("coffee maker", "SG"), ("standing desk", "SG"), ("ergonomic chair", "SG"),
    ("gaming chair", "SG"), ("monitor arm", "SG"), ("webcam 4K", "SG"),
    ("microphone USB", "SG"), ("mechanical keyboard", "SG"), ("gaming mouse", "SG"),
    # US — premium devices
    ("iPhone 15 Pro", "US"), ("iPhone 15 Pro Max", "US"), ("iPhone 14 Pro", "US"),
    ("Samsung Galaxy S24", "US"), ("Samsung Galaxy S24 Ultra", "US"),
    ("MacBook Air M3", "US"), ("MacBook Pro 14 M3", "US"), ("iPad Pro M4", "US"),
    ("AirPods Pro 2", "US"), ("Sony WH-1000XM5", "US"), ("Bose QuietComfort 45", "US"),
    ("Dell XPS 15", "US"), ("Surface Pro 9", "US"), ("ThinkPad X1 Carbon", "US"),
    ("ASUS ZenBook 14", "US"), ("Canon EOS R6 Mark II", "US"), ("GoPro Hero 12 Black", "US"),
    ("Kindle Paperwhite 2023", "US"), ("Pixel 8 Pro", "US"), ("Pixel Watch 2", "US"),
    ("Herman Miller Aeron", "US"), ("Logitech MX Master 3S", "US"),
    ("Razer DeathAdder V3", "US"), ("SteelSeries Arctis Nova Pro", "US"),
    ("LG UltraGear 27", "US"), ("Samsung Odyssey G7", "US"),
    ("Nest Thermostat", "US"), ("Ring Video Doorbell", "US"), ("Philips Hue Bridge", "US"),
    # US — general categories
    ("laptop", "US"), ("gaming laptop", "US"), ("wireless earbuds", "US"),
    ("smartwatch", "US"), ("4K TV", "US"), ("air purifier", "US"),
    ("robot vacuum", "US"), ("coffee machine", "US"), ("standing desk", "US"),
    ("monitor", "US"), ("webcam", "US"), ("microphone", "US"),
    ("mechanical keyboard", "US"), ("gaming mouse", "US"), ("gaming headset", "US"),
    ("graphics card", "US"), ("CPU processor", "US"), ("SSD 1TB", "US"),
    ("RAM 32GB", "US"), ("gaming PC", "US"), ("noise cancelling headphones", "US"),
]

assert len(QUERIES) == 100, f"Need 100 (query, country) pairs, got {len(QUERIES)}"

BASKET = []
for limit in [5, 10, 20]:
    for query, country in QUERIES:
        BASKET.append({"query": query, "country": country, "limit": limit})
BASKET = BASKET[:300]
assert len(BASKET) == 300, f"Expected 300, got {len(BASKET)}"


def basket_hash():
    canonical = json.dumps(BASKET, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# 2026-06-15: The hard-coded `bw_live_*` fallback was invalidated (HTTP 401) and
# the live run had to override BUYWHERE_REST_KEY / BUYWHERE_MCP_KEY to use the
# working `bw_265c38…864` key from the agent env. See BUY-32954 acceptance
# rerun. Going forward: never hard-code API keys in the script; read from env
# only and abort with a clear error if neither is set.
REST_KEY_FALLBACK = None  # was "bw_live_4AeojSmUExdazRv1z6EZIb3GGgvOlLzP" — REVOKED 2026-06-08
MCP_KEY_FALLBACK = None  # was the same key — REVOKED 2026-06-08


def _pick_key(explicit_env, fallback, env_var_name):
    # Explicit override always wins. Then env BUYWHERE_API_KEY (any tier).
    # Hard-coded fallback is deprecated — fail loudly if no key is configured
    # so a silent 401 loop on a stale key is impossible.
    if explicit_env:
        return explicit_env
    env = os.environ.get("BUYWHERE_API_KEY", "")
    if env:
        return env
    if fallback:
        return fallback
    raise RuntimeError(
        f"basket_verify_32954: no API key configured. Set BUYWHERE_API_KEY "
        f"in the environment, or pass --rest-key / --mcp-key explicitly. "
        f"({env_var_name} hard-coded fallback was removed on 2026-06-15 after "
        f"the bw_live_* key was revoked; see BUY-32954.)"
    )


def rest_key():
    return _pick_key(os.environ.get("BUYWHERE_REST_KEY"), REST_KEY_FALLBACK, "REST_KEY_FALLBACK")


def mcp_key():
    return _pick_key(os.environ.get("BUYWHERE_MCP_KEY"), MCP_KEY_FALLBACK, "MCP_KEY_FALLBACK")


def run_rest(q, country, limit, retries=2):
    url = f"{REST_BASE}?q={urllib.parse.quote(q)}&country={country}&region={country}&limit={limit}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {rest_key()}"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.loads(resp.read())
                results = len(data.get("results", data.get("products", [])))
                return {
                    "status": resp.status,
                    "result_count": results,
                    "error": None,
                    "latency_ms": None,
                }
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            return {"status": e.code, "result_count": 0, "error": body, "latency_ms": None}
        except Exception as ex:
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            return {"status": 0, "result_count": 0, "error": str(ex)[:200], "latency_ms": None}


def run_mcp(q, country, limit, retries=2):
    """POST JSON-RPC 2.0 to /mcp, method tools/call, name=search_products."""
    payload = {
        "jsonrpc": "2.0",
        "id": "basket",
        "method": "tools/call",
        "params": {
            "name": "search_products",
            "arguments": {
                "q": q,
                "country_code": country,
                "region": country,
                "limit": limit,
            },
        },
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        MCP_BASE,
        data=body,
        headers={
            "Authorization": f"Bearer {mcp_key()}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    for attempt in range(retries + 1):
        try:
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                latency_ms = int((time.time() - t0) * 1000)
                try:
                    data = json.loads(raw)
                except Exception as ex:
                    return {"status": resp.status, "result_count": 0, "error": f"json:{ex}", "latency_ms": latency_ms}
                if "error" in data:
                    return {"status": resp.status, "result_count": 0, "error": f"rpc:{data['error']}", "latency_ms": latency_ms}
                content = data.get("result", {}).get("content", [])
                if not content:
                    return {"status": resp.status, "result_count": 0, "error": "rpc:empty_content", "latency_ms": latency_ms}
                try:
                    parsed = json.loads(content[0]["text"])
                except Exception as ex:
                    return {"status": resp.status, "result_count": 0, "error": f"content_json:{ex}", "latency_ms": latency_ms}
                results = len(parsed.get("results", []))
                return {"status": resp.status, "result_count": results, "error": None, "latency_ms": latency_ms}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()[:200]
            return {"status": e.code, "result_count": 0, "error": err_body, "latency_ms": None}
        except Exception as ex:
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            return {"status": 0, "result_count": 0, "error": str(ex)[:200], "latency_ms": None}


def load_done(path):
    done = set()
    if not os.path.exists(path):
        return done
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                key = (rec["query"], rec["country"], rec["limit"])
                done.add(key)
            except Exception:
                continue
    return done


def append_jsonl(path, record):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def summarize(path):
    by_status = {}
    by_error = {}
    successes = 0
    total = 0
    if not os.path.exists(path):
        return {
            "total": 0, "successes": 0, "success_rate": 0.0,
            "by_status": {}, "top_errors": [],
        }
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            total += 1
            status = rec.get("status", 0)
            by_status[status] = by_status.get(status, 0) + 1
            err = rec.get("error") or ""
            ok = rec.get("result_count", 0) > 0 and status in (200,)
            if ok:
                successes += 1
            if not ok and err:
                key = err[:60]
                by_error[key] = by_error.get(key, 0) + 1
    top = sorted(by_error.items(), key=lambda x: -x[1])[:5]
    return {
        "total": total,
        "successes": successes,
        "success_rate": (successes / total * 100.0) if total else 0.0,
        "by_status": dict(sorted(by_status.items(), key=lambda x: -x[1])),
        "top_errors": [{"error": k, "count": v} for k, v in top],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--surface", choices=["rest", "mcp", "both"], default="both")
    ap.add_argument("--limit-rpm", type=int, default=40, help="Throttle target, requests/min")
    ap.add_argument("--max-queries", type=int, default=0, help="Optional cap for incremental runs (0 = all)")
    args = ap.parse_args()

    print(f"BUY-32954 Basket Verification — 300 queries × {args.surface}")
    print(f"basket_hash: {basket_hash()}")
    print(f"started: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print(f"rest_base: {REST_BASE}")
    print(f"mcp_base: {MCP_BASE}")
    print()

    surfaces = []
    if args.surface in ("rest", "both"):
        surfaces.append(("rest", rest_key(), 1.0, run_rest, os.path.join(DATA_DIR, "rest_results.jsonl")))
    if args.surface in ("mcp", "both"):
        # MCP daily limit is hit for both candidate keys on 2026-06-06; detect 429/daily-limit and abort cleanly.
        surfaces.append(("mcp", mcp_key(), 0.4, run_mcp, os.path.join(DATA_DIR, "mcp_results.jsonl")))

    for name, key, inter, runner, path in surfaces:
        done = load_done(path)
        todo = [b for b in BASKET if (b["query"], b["country"], b["limit"]) not in done]
        if args.max_queries:
            todo = todo[: args.max_queries]
        print(f"=== {name.upper()} surface — {len(todo)} to run ({len(done)} already done) ===")
        if not todo:
            print(f"  (no queries to run for {name})")
            continue
        successes = errors = rate_limited = timeouts = 0
        error_samples = []
        start = time.time()
        last_request = start
        abort_reason = None
        for i, b in enumerate(todo, 1):
            wait = inter - (time.time() - last_request)
            if wait > 0:
                time.sleep(wait)
            last_request = time.time()
            r = runner(b["query"], b["country"], b["limit"])
            record = {
                "query": b["query"], "country": b["country"], "limit": b["limit"],
                "status": r["status"], "result_count": r["result_count"],
                "error": r["error"], "latency_ms": r["latency_ms"],
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            append_jsonl(path, record)
            if r["status"] == 200 and r["result_count"] > 0:
                successes += 1
            else:
                errors += 1
                if r["status"] == 429 or "rate_limit" in (r["error"] or "") or "Daily limit" in (r["error"] or ""):
                    rate_limited += 1
                    if not abort_reason:
                        abort_reason = r["error"]
                elif r["status"] == 0:
                    timeouts += 1
                if len(error_samples) < 3:
                    error_samples.append(f"HTTP {r['status']} q={b['query']!r} country={b['country']} limit={b['limit']} err={(r['error'] or '')[:60]!r}")
            if i % 25 == 0 or i == len(todo):
                elapsed = time.time() - start
                print(f"  [{i}/{len(todo)}] successes={successes} errors={errors} 429s={rate_limited} timeouts={timeouts} elapsed={elapsed:.0f}s")
            if rate_limited >= 3 and abort_reason:
                print(f"  aborting {name}: 3+ rate-limit hits, last error: {abort_reason[:120]}")
                break
        summary = summarize(path)
        summary["base_url"] = REST_BASE if name == "rest" else MCP_BASE
        summary_path = os.path.join(DATA_DIR, f"{name}_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"  {name.upper()} summary: successes={summary['successes']}/{summary['total']} ({summary['success_rate']:.2f}%) — {summary_path}")
        if error_samples:
            print(f"  error samples:")
            for s in error_samples:
                print(f"    {s}")
        print()

    print(f"finished: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")


if __name__ == "__main__":
    main()
