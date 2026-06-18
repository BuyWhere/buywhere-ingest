"""Centralized BrightData proxy zone configuration.

Defines proxy zones and provides helpers for building proxy URLs,
Playwright config, and zone lookups. All credentials come from
environment variables so zones can be reconfigured without code changes.

Zones:
    DATACENTER_PROXY1 — datacenter proxy (fast, shared IPs)
    RESIDENTIAL_PROXY1 — residential proxy (rotating IPs, anti-bot)
    LEGACY_RESIDENTIAL — compat alias for the pre-BUY-10682 zone
    BUYWHERE_RESI — buywhere residential zone (us-focused, rotating)
    BUYWHERE_DC — buywhere datacenter zone
"""

import os
import urllib.parse
from dataclasses import dataclass
from enum import Enum


class Zone(str, Enum):
    DATACENTER_PROXY1 = "datacenter_proxy1"
    RESIDENTIAL_PROXY1 = "residential_proxy1"
    LEGACY_RESIDENTIAL = "residential"
    BUYWHERE_RESI = "buywhere_resi"
    BUYWHERE_DC = "buywhere_dc"


@dataclass(frozen=True)
class ZoneConfig:
    name: str
    username: str
    password: str
    host: str
    port: int


# env var tuples: (username_key, password_key, host_key, port_key)
ENV_MAP = {
    Zone.DATACENTER_PROXY1: (
        "BRIGHTDATA_DATACENTER_USERNAME",
        "BRIGHTDATA_DATACENTER_PASSWORD",
        "BRIGHTDATA_DATACENTER_HOST",
        "BRIGHTDATA_DATACENTER_PORT",
    ),
    Zone.RESIDENTIAL_PROXY1: (
        "BRIGHTDATA_RESIDENTIAL_USERNAME",
        "BRIGHTDATA_RESIDENTIAL_PASSWORD",
        "BRIGHTDATA_RESIDENTIAL_HOST",
        "BRIGHTDATA_RESIDENTIAL_PORT",
    ),
    Zone.LEGACY_RESIDENTIAL: (
        "BRIGHTDATA_USERNAME",
        "BRIGHTDATA_PASSWORD",
        "BRIGHTDATA_PROXY_HOST",
        "BRIGHTDATA_PROXY_PORT",
    ),
    Zone.BUYWHERE_RESI: (
        "BRIGHTDATA_BUYWHERE_RESI_USERNAME",
        "BRIGHTDATA_BUYWHERE_RESI_PASSWORD",
        "BRIGHTDATA_BUYWHERE_RESI_HOST",
        "BRIGHTDATA_BUYWHERE_RESI_PORT",
    ),
    Zone.BUYWHERE_DC: (
        "BRIGHTDATA_BUYWHERE_DC_USERNAME",
        "BRIGHTDATA_BUYWHERE_DC_PASSWORD",
        "BRIGHTDATA_BUYWHERE_DC_HOST",
        "BRIGHTDATA_BUYWHERE_DC_PORT",
    ),
}

DEFAULT_USERNAME = {
    Zone.DATACENTER_PROXY1: "brd-customer-hl_3ab737be-zone-datacenter_proxy1",
    Zone.RESIDENTIAL_PROXY1: "brd-customer-hl_3ab737be-zone-residential",
    Zone.LEGACY_RESIDENTIAL: "brd-customer-hl_3ab737be-zone-residential",
    Zone.BUYWHERE_RESI: "brd-customer-hl_3ab737be-zone-buywhere_resi",
    Zone.BUYWHERE_DC: "brd-customer-hl_3ab737be-zone-buywhere_dc",
}

DEFAULT_HOST = "brd.superproxy.io"

DEFAULT_PORT = {
    Zone.DATACENTER_PROXY1: 30000,
    Zone.RESIDENTIAL_PROXY1: 22225,
    Zone.LEGACY_RESIDENTIAL: 33335,
    Zone.BUYWHERE_RESI: 22225,
    Zone.BUYWHERE_DC: 30000,
}

# Passwords for newly created zones (set from env or use these defaults)
DEFAULT_PASSWORD = {
    Zone.BUYWHERE_RESI: "bcq0uudpb5c4",
    Zone.BUYWHERE_DC: "yxv40huirw9v",
}

_zone_cache: dict[Zone, ZoneConfig] = {}


def _load_zone_config(zone: Zone) -> ZoneConfig:
    """Build ZoneConfig from environment variables (cached per zone)."""
    if zone in _zone_cache:
        return _zone_cache[zone]

    user_key, pass_key, host_key, port_key = ENV_MAP[zone]
    username = os.environ.get(user_key) or DEFAULT_USERNAME[zone]
    password = os.environ.get(pass_key) or DEFAULT_PASSWORD.get(zone, "")
    host = os.environ.get(host_key) or DEFAULT_HOST
    port = int(os.environ.get(port_key, str(DEFAULT_PORT[zone])))

    config = ZoneConfig(name=zone.value, username=username, password=password, host=host, port=port)
    _zone_cache[zone] = config
    return config


def get_zone_config(zone: Zone) -> ZoneConfig:
    """Return the full ZoneConfig for the given zone."""
    return _load_zone_config(zone)


def proxy_url(zone: Zone) -> str:
    """Build a proxy URL for use with HTTPX, aiohttp, or curl -x."""
    cfg = _load_zone_config(zone)
    encoded_user = urllib.parse.quote(cfg.username, safe="")
    encoded_pass = urllib.parse.quote(cfg.password, safe="")
    return f"http://{encoded_user}:{encoded_pass}@{cfg.host}:{cfg.port}"


def proxy_config_for_httpx(zone: Zone) -> str:
    """Return proxy URL string suitable for httpx.AsyncClient(proxy=...)."""
    return proxy_url(zone)


def proxy_config_for_playwright(zone: Zone) -> dict:
    """Return a Playwright browser launch proxy config dict."""
    cfg = _load_zone_config(zone)
    return {
        "server": f"http://{cfg.host}:{cfg.port}",
        "username": cfg.username,
        "password": cfg.password,
    }


def list_zones() -> list[Zone]:
    """Return all available zone identifiers."""
    return list(Zone)


def clear_cache() -> None:
    """Clear the zone config cache (useful in tests)."""
    global _zone_cache
    _zone_cache = {}
