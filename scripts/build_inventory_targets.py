"""Build a target list of product URLs for deep-page inventory enrichment.

Reads merchant NDJSON files and outputs a deduplicated list of URLs
suitable for the deep_page_inventory scraper.
"""

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merchants-dir", required=True, help="Directory with merchant NDJSON files")
    parser.add_argument("--output", required=True, help="Output NDJSON target list")
    parser.add_argument("--limit", type=int, default=20, help="Max records to include")
    args = parser.parse_args()

    seen: set[str] = set()
    targets: list[dict[str, Any]] = []
    merchants_dir = Path(args.merchants_dir)
    for ndjson_path in sorted(merchants_dir.glob("*.ndjson")):
        with open(ndjson_path, "r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                url = row.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                targets.append({
                    "sku": row.get("sku"),
                    "url": url,
                    "name": row.get("name"),
                    "source_merchant": ndjson_path.stem,
                })
                if len(targets) >= args.limit:
                    break
        if len(targets) >= args.limit:
            break

    with open(args.output, "w", encoding="utf-8") as fh:
        for row in targets:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"target_count={len(targets)} output={args.output}")


if __name__ == "__main__":
    main()
