#!/usr/bin/env python3
"""Daily competitor intelligence digest for AI-agent commerce space."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


THREAT_SIGNALS: dict[str, list[str]] = {
    "critical": ["product search api", "shopping api", "price comparison api", "merchant catalog"],
    "high": ["ai shopping", "agent commerce", "mcp shopping", "deal finder ai"],
    "medium": ["ai agent", "mcp server", "langchain tool", "product scraper"],
}


def classify_threat(text: str) -> str | None:
    text_lower = text.lower()
    for level in ["critical", "high", "medium"]:
        for signal in THREAT_SIGNALS[level]:
            if signal in text_lower:
                return level
    return "monitor"


def fetch_product_hunt(days_back: int = 1) -> list[dict[str, Any]]:
    token = os.environ.get("PH_API_TOKEN")
    if not token:
        return [{"error": "PH_API_TOKEN not set", "platform": "product_hunt"}]

    try:
        import requests
    except ImportError:
        return [{"error": "requests library not available", "platform": "product_hunt"}]

    cutoff = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    headers = {"Authorization": f"Bearer {token}"}
    competitors = []

    try:
        resp = requests.get(
            "https://api.producthunt.com/v2/api/graphql",
            headers=headers,
            json={
                "query": """
                {
                  posts(postedAfter: "%s", first: 50) {
                    edges {
                      node {
                        name
                        description
                        websiteUrl
                        topics { name }
                        createdAt
                      }
                    }
                  }
                }
                """ % cutoff
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return [{"error": f"PH API returned {resp.status_code}", "platform": "product_hunt"}]

        data = resp.json().get("data", {}).get("posts", {}).get("edges", [])
        for edge in data:
            node = edge.get("node", {})
            name = node.get("name", "")
            desc = node.get("description", "")
            combined = f"{name} {desc} {' '.join(t.get('name', '') for t in node.get('topics', []))}"
            threat = classify_threat(combined)
            competitors.append({
                "name": name,
                "description": desc,
                "url": node.get("websiteUrl"),
                "created_at": node.get("createdAt"),
                "topics": [t.get("name") for t in node.get("topics", [])],
                "threat_level": threat,
                "platform": "product_hunt",
            })
    except Exception as e:
        return [{"error": str(e), "platform": "product_hunt"}]

    return competitors


def fetch_smithery_mcp() -> list[dict[str, Any]]:
    try:
        import requests
    except ImportError:
        return [{"error": "requests library not available", "platform": "smithery"}]

    competitors = []
    try:
        resp = requests.get("https://smithery.ai/api/mcp", timeout=15)
        if resp.status_code != 200:
            return [{"error": f"Smithery API returned {resp.status_code}", "platform": "smithery"}]

        servers = resp.json() if isinstance(resp.json(), list) else resp.json().get("mcpServers", [])
        cutoff = datetime.utcnow() - timedelta(days=7)

        for server in servers[:100]:
            name = server.get("name", "")
            desc = server.get("description", "")
            combined = f"{name} {desc}"
            threat = classify_threat(combined)
            if threat != "monitor":
                competitors.append({
                    "name": name,
                    "description": desc,
                    "url": server.get("github") or server.get("homepage"),
                    "threat_level": threat,
                    "platform": "smithery",
                })
    except Exception as e:
        return [{"error": str(e), "platform": "smithery"}]

    return competitors


def fetch_hackernews(competitor_keywords: list[str], days_back: int = 7) -> list[dict[str, Any]]:
    """Hacker News (Algolia) — public, no auth required.

    Searches story titles + URLs created in the last `days_back` days for any
    of the supplied competitor keywords. Each match is a competitor mention
    from the developer/tech community.
    """
    try:
        import requests
    except ImportError:
        return [{"error": "requests library not available", "platform": "hackernews"}]

    import time as _time

    cutoff_ts = int((datetime.utcnow() - timedelta(days=days_back)).timestamp())
    competitors: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for keyword in competitor_keywords:
        try:
            resp = requests.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "query": keyword,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{cutoff_ts}",
                    "hitsPerPage": 25,
                },
                timeout=15,
            )
            if resp.status_code != 200:
                competitors.append(
                    {"error": f"HN API returned {resp.status_code} for '{keyword}'", "platform": "hackernews"}
                )
                continue

            for hit in resp.json().get("hits", []):
                hit_id = hit.get("objectID", "")
                if hit_id in seen_ids:
                    continue
                seen_ids.add(hit_id)
                title = hit.get("title") or ""
                url = hit.get("url") or hit.get("story_url") or f"https://news.ycombinator.com/item?id={hit_id}"
                combined = f"{title} {url}"
                threat = classify_threat(combined) or "monitor"
                competitors.append({
                    "name": title or "(no title)",
                    "description": f"HN mention for keyword '{keyword}'",
                    "url": url,
                    "hn_id": hit_id,
                    "hn_points": hit.get("points", 0),
                    "hn_comments": hit.get("num_comments", 0),
                    "hn_created_at": hit.get("created_at"),
                    "keyword": keyword,
                    "threat_level": threat,
                    "platform": "hackernews",
                })
            _time.sleep(0.2)  # be polite to public API
        except Exception as e:
            competitors.append({"error": str(e), "platform": "hackernews", "keyword": keyword})
            continue

    return competitors


def fetch_github_trending(keywords: list[str], days_back: int = 1) -> list[dict[str, Any]]:
    token = os.environ.get("GITHUB_TOKEN")
    try:
        import requests
    except ImportError:
        return [{"error": "requests library not available", "platform": "github"}]

    competitors = []
    cutoff = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for keyword in keywords:
        try:
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            resp = requests.get(
                "https://api.github.com/search/repositories",
                headers=headers,
                params={
                    "q": f"{keyword} created:>{cutoff}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 10,
                },
                timeout=15,
            )
            if resp.status_code != 200:
                continue

            items = resp.json().get("items", [])
            for item in items:
                name = item.get("name", "")
                desc = item.get("description", "") or ""
                combined = f"{name} {desc} {keyword}"
                threat = classify_threat(combined)
                if threat != "monitor":
                    competitors.append({
                        "name": name,
                        "description": desc,
                        "url": item.get("html_url"),
                        "stars": item.get("stargazers_count"),
                        "threat_level": threat,
                        "platform": "github",
                    })
        except Exception:
            continue

    return competitors


HN_COMPETITOR_KEYWORDS: list[str] = [
    "Google Shopping",
    "Universal Cart",
    "Klarna AI",
    "Amazon Buy for Me",
    "Perplexity Shopping",
    "Walmart Sparky",
    "ChatGPT Shopping",
    "Shopify UCP",
    "Buy for Me",
    "agentic commerce",
    "x402",
]


def build_digest() -> dict[str, Any]:
    ph_results = fetch_product_hunt()
    smithery_results = fetch_smithery_mcp()
    github_results = fetch_github_trending(
        keywords=["ai shopping", "agent commerce", "product search api", "mcp server"],
    )
    hn_results = fetch_hackernews(HN_COMPETITOR_KEYWORDS, days_back=7)

    all_competitors = ph_results + smithery_results + github_results + hn_results
    errors = [r for r in all_competitors if "error" in r]
    competitors = [r for r in all_competitors if "error" not in r]

    by_threat: dict[str, list] = {"critical": [], "high": [], "medium": [], "monitor": []}
    for c in competitors:
        by_threat[c.get("threat_level", "monitor")].append(c)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "total_found": len(competitors),
        "errors": errors,
        "by_threat_level": {k: len(v) for k, v in by_threat.items()},
        "by_platform": _count_by(competitors, "platform"),
        "competitors": competitors,
        "summary": {
            "critical_count": len(by_threat["critical"]),
            "high_count": len(by_threat["high"]),
            "medium_count": len(by_threat["medium"]),
            "monitor_count": len(by_threat["monitor"]),
        },
    }


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        k = item.get(key, "unknown")
        counts[k] = counts.get(k, 0) + 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily competitor intelligence digest")
    parser.add_argument("--dry-run", action="store_true", help="Print digest without posting")
    args = parser.parse_args()

    digest = build_digest()

    if args.dry_run:
        print(json.dumps(digest, indent=2, default=str))
    else:
        print(json.dumps(digest, indent=2, default=str))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
