#!/usr/bin/env python3
"""
BUY-31312 basket verification — 300-query REST test.
Throttled to 40 rpm to stay under the 60 rpm API key limit.
Success criteria:
  - GET /v1/products/search?q=iPhone%2015%20Pro&country=SG&limit=5 returns 5 results
  - 300-query basket REST >= 50% success (HTTP 200 + result_count > 0)
  - API error rate < 5%
"""
import time
import json
import urllib.request
import urllib.error
import urllib.parse

API_KEY = "bw_live_4AeojSmUExdazRv1z6EZIb3GGgvOlLzP"
BASE_URL = "https://api.buywhere.ai/v1/products/search"
TIMEOUT = 15
MIN_INTERVAL = 1.5  # 40 rpm = 1 req/1.5s, safely under 60 rpm cap

# 100 unique (query, country) pairs — 3 limit values = 300 basket items
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

assert len(QUERIES) >= 100, f"Need 100 queries, got {len(QUERIES)}"

# 3 limit values × 100 queries = 300 basket items
BASKET = []
for limit in [5, 10, 20]:
    for query, country in QUERIES:
        BASKET.append((query, country, limit))
BASKET = BASKET[:300]
assert len(BASKET) == 300, f"Expected 300, got {len(BASKET)}"


def run_query(q, country, limit):
    # Pass region=country to prevent default region="US" from cross-filtering SG queries
    url = f"{BASE_URL}?q={urllib.parse.quote(q)}&country={country}&region={country}&limit={limit}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read())
            results = len(data.get("results", data.get("products", [])))
            return {"status": resp.status, "result_count": results, "error": None}
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:100]
        return {"status": e.code, "result_count": 0, "error": body}
    except Exception as ex:
        return {"status": 0, "result_count": 0, "error": str(ex)[:80]}


def main():
    print(f"BUY-31312 Basket Verification — {len(BASKET)} queries at 40 rpm")
    print(f"API Key: {API_KEY[:24]}...")
    print()

    # Rich's exact criterion first
    print("=== Rich's criterion: iPhone 15 Pro + SG + limit=5 ===")
    r = run_query("iPhone 15 Pro", "SG", 5)
    print(f"  HTTP {r['status']} | result_count={r['result_count']} | time={time.strftime('%H:%M:%S')}")
    rich_pass = r["status"] == 200 and r["result_count"] >= 5
    print(f"  Result: {'PASS' if rich_pass else 'FAIL'}")
    print()

    # Full basket with throttling
    print(f"=== Basket test ({len(BASKET)} queries, throttled to 40 rpm) ===")
    successes, errors, rate_limited, timeouts = 0, 0, 0, 0
    error_samples = []
    start = time.time()
    last_request = start

    for i, (q, country, limit) in enumerate(BASKET, 1):
        # Throttle: ensure MIN_INTERVAL between requests
        now = time.time()
        wait = MIN_INTERVAL - (now - last_request)
        if wait > 0:
            time.sleep(wait)

        last_request = time.time()
        r = run_query(q, country, limit)

        if r["status"] == 200 and r["result_count"] > 0:
            successes += 1
        elif r["status"] == 429:
            rate_limited += 1
            errors += 1
            if len(error_samples) < 3:
                error_samples.append(f"429 rate_limit q={q!r}")
        elif r["status"] == 0:
            timeouts += 1
            errors += 1
            if len(error_samples) < 3:
                error_samples.append(f"timeout q={q!r}")
        else:
            errors += 1
            if len(error_samples) < 3:
                error_samples.append(f"HTTP {r['status']} q={q!r} err={r['error']!r}")

        if i % 50 == 0:
            elapsed = time.time() - start
            pct = successes / i * 100
            eta = (elapsed / i) * (len(BASKET) - i)
            print(f"  [{i}/{len(BASKET)}] Success: {successes} ({pct:.1f}%) | 429s: {rate_limited} | Elapsed: {elapsed:.0f}s | ETA: {eta:.0f}s")

    elapsed = time.time() - start
    success_rate = successes / len(BASKET) * 100
    error_rate = errors / len(BASKET) * 100

    print()
    print("=== RESULTS ===")
    print(f"Total queries:   {len(BASKET)}")
    print(f"Successes:       {successes} ({success_rate:.1f}%)")
    print(f"Errors (total):  {errors} ({error_rate:.1f}%)")
    print(f"  - 429s:        {rate_limited}")
    print(f"  - Timeouts:    {timeouts}")
    print(f"  - Other:       {errors - rate_limited - timeouts}")
    print(f"Elapsed:         {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"Avg interval:    {elapsed/len(BASKET)*1000:.0f}ms")
    if error_samples:
        print(f"Error samples:   {error_samples}")

    print()
    print("=== VERDICT ===")
    basket_pass = success_rate >= 50
    error_pass = error_rate < 5
    print(f"Rich's criterion (5 results iPhone 15 Pro+SG): {'PASS' if rich_pass else 'FAIL'}")
    print(f"Basket ≥50% success ({success_rate:.1f}%):          {'PASS' if basket_pass else 'FAIL'}")
    print(f"Error rate <5% ({error_rate:.1f}%):                 {'PASS' if error_pass else 'FAIL'}")
    overall = rich_pass and basket_pass and error_pass
    print(f"\nOVERALL: {'✓ PASS' if overall else '✗ FAIL'}")
    return overall


if __name__ == "__main__":
    main()
