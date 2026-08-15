#!/usr/bin/env python3
"""Backward-compatible hourly recovery entrypoint for BUY-54233.

This file is now a thin wrapper around :mod:`hourly_throughput_dispatcher`, which
implements the active BUY-29861 parented failure filing behavior:

- evaluate the just-completed UTC hour
- use canonical catalog data from ``data/.catalog_db_url``
- create a child issue under BUY-29861 only when real rows are below 150,000
  (assigned to ``MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6``)
"""

from __future__ import annotations

from hourly_throughput_dispatcher import main as _throughput_main


def main() -> int:
    return _throughput_main()


if __name__ == "__main__":
    raise SystemExit(main())
