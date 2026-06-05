#!/usr/bin/env python3

import json
import os
import sys
    from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("requests module required. Install with: pip install requests")
    sys.exit(1)


def fetch_agents(api_url: str, api_key: str, company_id: str, run_id: str) -> list:
    """Fetch all agents from Paperclip API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Paperclip-Run-Id": run_id,
    }
    response = requests.get(
        f"{api_url}/api/companies/{company_id}/agents",
        headers=headers
    )
    response.raise_for_status()
    return response.json()


def count_api_keys(agents: list) -> dict:
    """Count occurrences of each API key across agent configs."""
    key_counts = {}
    total_agents = len(agents)

    for agent in agents:
        env = agent.get("adapterConfig", {}).get("env", {})
        if env:
            for key in env.keys():
                if "API_KEY" in key or "TOKEN" in key or "PAT" in key:
                    key_counts[key] = key_counts.get(key, 0) + 1

    return key_counts, total_agents


def update_ledger(
    ledger_path: Path,
    key_counts: dict,
    total_agents: int,
    company_id: str,
    run_id: str
):
    """Update the API keys ledger file."""
    ledger = {
        "lastUpdated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "companyId": company_id,
        "totalAgents": total_agents,
        "apiKeys": key_counts,
        "notes": "This ledger aggregates API key counts from agent configurations. The BUYWHERE_API_KEY count represents the company-wide developer API key inventory. Updated by BUY-31183."
    }
    
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=2)
    
    print(f"Ledger updated: {ledger_path}")
    print(f"Total agents: {total_agents}")
    print(f"API keys tracked: {len(key_counts)}")


def main():
    api_url = os.environ.get("PAPERCLIP_API_URL")
    api_key = os.environ.get("PAPERCLIP_API_KEY")
    company_id = os.environ.get("PAPERCLIP_COMPANY_ID")
    run_id = os.environ.get("PAPERCLIP_RUN_ID", "manual")
    
    if not all([api_url, api_key, company_id]):
        print("Missing required environment variables:")
        for var in ["PAPERCLIP_API_URL", "PAPERCLIP_API_KEY", "PAPERCLIP_COMPANY_ID"]:
            if not os.environ.get(var):
                print(f"  - {var}")
        sys.exit(1)
    
    ledger_path = Path("data/api_keys_ledger.json")
    
    try:
        agents = fetch_agents(api_url, api_key, company_id, run_id)
        key_counts, total_agents = count_api_keys(agents)
        update_ledger(ledger_path, key_counts, total_agents, company_id, run_id)
    except Exception as e:
        print(f"Error updating ledger: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()