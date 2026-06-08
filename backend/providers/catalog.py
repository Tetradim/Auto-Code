"""Market-data provider catalog and configuration helpers.

This module is intentionally metadata-only: it describes supported public or
freemium data sources without reading or returning API-key values. Runtime
credentials are supplied by environment variables, keeping secrets out of logs,
browser localStorage, API responses, and git.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ProviderInfo:
    """User-facing description of a market-data source."""

    key: str
    label: str
    quote: bool
    ohlcv: bool
    requires_key: bool
    env_var: Optional[str]
    free_tier: str
    notes: str
    enabled: bool = False
    intraday: bool = False
    eod: bool = False

    def public_dict(self) -> Dict[str, object]:
        """Return metadata safe for the browser.

        Never include secret values. For keyed providers, expose only whether
        the relevant environment variable is present.
        """
        data = asdict(self)
        data.pop("env_var", None)
        data["configured"] = bool(self.env_var and os.getenv(self.env_var)) if self.requires_key else True
        return data


PROVIDER_CATALOG: List[ProviderInfo] = [
    ProviderInfo(
        key="yfinance",
        label="Yahoo/yfinance",
        quote=True,
        ohlcv=True,
        requires_key=False,
        env_var=None,
        free_tier="No key; unofficial delayed feed",
        notes="Existing default. Useful fallback, but not an official exchange data API.",
        enabled=True,
        intraday=True,
        eod=True,
    ),
    ProviderInfo(
        key="finnhub",
        label="Finnhub",
        quote=True,
        ohlcv=True,
        requires_key=True,
        env_var="FINNHUB_API_KEY",
        free_tier="Free account tier with rate limits",
        notes="Existing provider. Free tier is useful for quotes; paid tiers improve limits/coverage.",
        enabled=True,
        intraday=True,
        eod=True,
    ),
    ProviderInfo(
        key="polygon",
        label="Polygon.io",
        quote=True,
        ohlcv=True,
        requires_key=True,
        env_var="POLYGON_API_KEY",
        free_tier="Account tier; real-time/historical depth depends on plan",
        notes="Existing provider. Strong paid upgrade path for US equities.",
        enabled=True,
        intraday=True,
        eod=True,
    ),
    ProviderInfo(
        key="alpha_vantage",
        label="Alpha Vantage",
        quote=True,
        ohlcv=True,
        requires_key=True,
        env_var="ALPHA_VANTAGE_API_KEY",
        free_tier="Free account tier with strict per-minute/day limits",
        notes="Optional fallback. Handle 'Note'/'Information' rate-limit responses explicitly.",
        enabled=False,
        intraday=True,
        eod=True,
    ),
    ProviderInfo(
        key="twelve_data",
        label="Twelve Data",
        quote=True,
        ohlcv=True,
        requires_key=True,
        env_var="TWELVE_DATA_API_KEY",
        free_tier="Free account tier with symbol/credit limits",
        notes="Optional fallback when configured; broad asset coverage.",
        enabled=False,
        intraday=True,
        eod=True,
    ),
    ProviderInfo(
        key="stooq",
        label="Stooq CSV",
        quote=False,
        ohlcv=True,
        requires_key=False,
        env_var=None,
        free_tier="No key; public daily CSV endpoint",
        notes="EOD/backfill only. Do not use for live intraday scheduler ticks.",
        enabled=True,
        intraday=False,
        eod=True,
    ),
    ProviderInfo(
        key="financial_modeling_prep",
        label="Financial Modeling Prep",
        quote=True,
        ohlcv=True,
        requires_key=True,
        env_var="FMP_API_KEY",
        free_tier="Free account tier with limited requests/data",
        notes="Useful for fundamentals plus price endpoints; optional future provider.",
        enabled=False,
        intraday=False,
        eod=True,
    ),
    ProviderInfo(
        key="marketstack",
        label="Marketstack",
        quote=False,
        ohlcv=True,
        requires_key=True,
        env_var="MARKETSTACK_API_KEY",
        free_tier="Free account tier, usually EOD-focused",
        notes="Good end-of-day fallback, not an intraday default.",
        enabled=False,
        intraday=False,
        eod=True,
    ),
    ProviderInfo(
        key="tiingo",
        label="Tiingo",
        quote=True,
        ohlcv=True,
        requires_key=True,
        env_var="TIINGO_API_KEY",
        free_tier="Free/dev account tier with attribution/limits",
        notes="Documented API; optional future provider.",
        enabled=False,
        intraday=False,
        eod=True,
    ),
    ProviderInfo(
        key="eodhd",
        label="EODHD",
        quote=True,
        ohlcv=True,
        requires_key=True,
        env_var="EODHD_API_KEY",
        free_tier="Free/demo account tier; paid tiers expand coverage",
        notes="Useful optional EOD/intraday provider depending on subscription.",
        enabled=False,
        intraday=False,
        eod=True,
    ),
    ProviderInfo(
        key="nasdaq_data_link",
        label="Nasdaq Data Link",
        quote=False,
        ohlcv=True,
        requires_key=True,
        env_var="NASDAQ_DATA_LINK_API_KEY",
        free_tier="Free datasets plus paid datasets",
        notes="Best for slower research datasets, not live quote refresh.",
        enabled=False,
        intraday=False,
        eod=True,
    ),
]


def _provider_keys(*, intraday: Optional[bool] = None) -> set[str]:
    if intraday is None:
        return {provider.key for provider in PROVIDER_CATALOG}
    return {provider.key for provider in PROVIDER_CATALOG if provider.intraday is intraday or provider.intraday == intraday}


def provider_catalog() -> List[Dict[str, object]]:
    """Return browser-safe provider metadata."""
    return [provider.public_dict() for provider in PROVIDER_CATALOG]


def default_provider_order() -> List[str]:
    """Return intraday fallback order, preserving yfinance as safe default.

    Daily/EOD-only providers such as Stooq are intentionally excluded from the
    intraday order because Edge's scheduler expects 1-minute bars.
    """
    raw = os.getenv("MARKET_DATA_PROVIDER_ORDER", "yfinance,finnhub,polygon,alpha_vantage,twelve_data")
    known = {provider.key for provider in PROVIDER_CATALOG if provider.intraday}
    ordered = [item.strip().lower() for item in raw.split(",") if item.strip()]
    filtered = [item for item in ordered if item in known]
    return filtered or ["yfinance"]


def active_provider_order() -> List[str]:
    """Return the intraday providers Edge may call right now.

    Keyed providers are active only when their backend environment variable is
    present. This avoids noisy failures, accidental paid/API calls, and browser
    configuration drift. No-key providers such as yfinance remain available.
    """
    by_key = {provider.key: provider for provider in PROVIDER_CATALOG}
    active: List[str] = []
    for key in default_provider_order():
        provider = by_key.get(key)
        if provider is None:
            continue
        if provider.requires_key and not (provider.env_var and os.getenv(provider.env_var)):
            continue
        active.append(key)
    return active or ["yfinance"]


def configured_key_sources() -> Dict[str, bool]:
    """Expose only key presence, never key values."""
    return {
        provider.key: bool(provider.env_var and os.getenv(provider.env_var))
        for provider in PROVIDER_CATALOG
        if provider.requires_key
    }
