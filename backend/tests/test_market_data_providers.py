"""Market-data provider safety tests."""
import os

from providers.catalog import active_provider_order, default_provider_order, provider_catalog
from price_fetcher import PriceFetcher


def test_provider_catalog_is_browser_safe(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "SENTINEL_TEST_KEY_XYZ")
    data = provider_catalog()
    body = str(data).lower()

    assert "SENTINEL_TEST_KEY_XYZ" not in str(data)
    assert "api_key" not in body
    assert "apikey" not in body
    assert "token" not in body
    assert all("env_var" not in provider for provider in data)
    assert any(provider["key"] == "finnhub" and provider["configured"] for provider in data)


def test_intraday_default_order_excludes_stooq():
    order = default_provider_order()
    assert order[0] == "yfinance"
    assert "stooq" not in order
    assert "twelve_data" in order


def test_price_fetcher_registers_intraday_providers_only(monkeypatch):
    for name in ("FINNHUB_API_KEY", "POLYGON_API_KEY", "ALPHA_VANTAGE_API_KEY", "TWELVE_DATA_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    fetcher = PriceFetcher()
    assert fetcher.provider_order == ["yfinance"]
    assert "alpha_vantage" in fetcher.providers
    assert "finnhub" in fetcher.providers
    assert "polygon" in fetcher.providers
    assert "twelve_data" in fetcher.providers
    assert "stooq" not in fetcher.providers


def test_active_order_uses_only_configured_keyed_providers(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_PROVIDER_ORDER", "yfinance,finnhub,polygon,twelve_data")
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "SENTINEL_TEST_KEY_XYZ")
    assert active_provider_order() == ["yfinance", "twelve_data"]


def test_env_order_filters_eod_only_sources(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_PROVIDER_ORDER", "stooq,yfinance,polygon,unknown")
    assert default_provider_order() == ["yfinance", "polygon"]


def test_env_order_falls_back_to_yfinance_when_invalid(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_PROVIDER_ORDER", "stooq,unknown")
    assert default_provider_order() == ["yfinance"]
