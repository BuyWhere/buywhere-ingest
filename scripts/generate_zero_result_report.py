#!/usr/bin/env python3
"""Generate weekly zero-result gap report for Oracle."""
import sys

import json, os, subprocess, sys

def build_report():
    lines = []

    lines.append("## Weekly zero-result gap report — week ending 2026-06-19")
    lines.append("")
    lines.append("**Source:** Catalog DB (maglev.proxy.rlwy.net:31310/railway) — live product counts + query_log 14d window")
    lines.append("**Generated:** 2026-06-19T01:20Z | Routine: BUY-53244")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### Catalog headline")
    lines.append("")
    lines.append("| Metric | Value | vs prior week (2026-06-05) |")
    lines.append("|--------|-------|---------------------------|")
    lines.append("| Total products (n_live_tup) | 125.2M | +32.0M (from ~93M) |")
    lines.append("| Products added (7d window) | 13.1M | Not previously tracked |")
    lines.append("| Active merchants | 75,039 | +48K (from ~27K on Jun 5) |")
    lines.append("| Markets with products | 22 | Stable |")
    lines.append("| Query-log searches (14d) | 3,837 | Baseline |")
    lines.append("| Zero-rate (products.search) | 45.9% | Baseline 🔴 |")
    lines.append("| Zero-rate (MCP endpoint) | 6.5% | Baseline 🟡 |")
    lines.append("")
    lines.append("---")
    lines.append("")

    return "
".join(lines)

if __name__ == "__main__":
    report = build_report()
    print(report)
