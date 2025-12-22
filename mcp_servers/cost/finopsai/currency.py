"""
Currency conversion utilities for OCI cost normalization.

Provides conversion from various tenancy currencies to USD for consistent
cross-tenancy cost comparison and reporting.
"""
from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

# Default exchange rates to USD (fallback when API is unavailable)
# These are approximate rates and should be updated periodically
# Last updated: 2024-12
DEFAULT_RATES_TO_USD: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,      # Euro
    "GBP": 1.27,      # British Pound
    "JPY": 0.0067,    # Japanese Yen
    "AUD": 0.65,      # Australian Dollar
    "CAD": 0.74,      # Canadian Dollar
    "CHF": 1.13,      # Swiss Franc
    "CNY": 0.14,      # Chinese Yuan
    "INR": 0.012,     # Indian Rupee
    "KRW": 0.00076,   # South Korean Won
    "SGD": 0.74,      # Singapore Dollar
    "HKD": 0.13,      # Hong Kong Dollar
    "MXN": 0.058,     # Mexican Peso
    "BRL": 0.20,      # Brazilian Real
    "ZAR": 0.055,     # South African Rand
    "SAR": 0.27,      # Saudi Riyal
    "AED": 0.27,      # UAE Dirham
    "NZD": 0.62,      # New Zealand Dollar
    "SEK": 0.095,     # Swedish Krona
    "NOK": 0.091,     # Norwegian Krone
    "DKK": 0.14,      # Danish Krone
    "PLN": 0.25,      # Polish Zloty
    "THB": 0.029,     # Thai Baht
    "MYR": 0.22,      # Malaysian Ringgit
    "IDR": 0.000063,  # Indonesian Rupiah
    "PHP": 0.018,     # Philippine Peso
    "TWD": 0.031,     # Taiwan Dollar
    "ILS": 0.27,      # Israeli Shekel
    "TRY": 0.029,     # Turkish Lira
    "RUB": 0.011,     # Russian Ruble
    "CZK": 0.043,     # Czech Koruna
    "HUF": 0.0027,    # Hungarian Forint
    "CLP": 0.0011,    # Chilean Peso
    "COP": 0.00024,   # Colombian Peso
    "PEN": 0.27,      # Peruvian Sol
    "ARS": 0.0010,    # Argentine Peso
}

# Cache for live exchange rates
_rate_cache: Dict[str, Tuple[float, datetime]] = {}
_CACHE_TTL_HOURS = 24

def get_exchange_rate(from_currency: str, to_currency: str = "USD") -> float:
    """
    Get exchange rate from one currency to another.

    Args:
        from_currency: Source currency code (e.g., "EUR", "GBP")
        to_currency: Target currency code (default: "USD")

    Returns:
        Exchange rate multiplier (amount in from_currency * rate = amount in to_currency)
    """
    if not from_currency:
        return 1.0

    from_currency = from_currency.upper().strip()
    to_currency = to_currency.upper().strip()

    if from_currency == to_currency:
        return 1.0

    # Try to get live rates if enabled
    live_rates_enabled = os.getenv("COST_LIVE_EXCHANGE_RATES", "false").lower() in ("true", "1", "yes")
    if live_rates_enabled:
        rate = _get_live_rate(from_currency, to_currency)
        if rate is not None:
            return rate

    # Fall back to default rates
    if to_currency == "USD":
        return DEFAULT_RATES_TO_USD.get(from_currency, 1.0)
    elif from_currency == "USD":
        to_rate = DEFAULT_RATES_TO_USD.get(to_currency, 1.0)
        return 1.0 / to_rate if to_rate != 0 else 1.0
    else:
        # Convert via USD
        from_to_usd = DEFAULT_RATES_TO_USD.get(from_currency, 1.0)
        usd_to_target = DEFAULT_RATES_TO_USD.get(to_currency, 1.0)
        return from_to_usd / usd_to_target if usd_to_target != 0 else from_to_usd


def _get_live_rate(from_currency: str, to_currency: str) -> Optional[float]:
    """
    Attempt to get live exchange rate from external API.
    Returns None if unavailable.
    """
    cache_key = f"{from_currency}_{to_currency}"

    # Check cache first
    if cache_key in _rate_cache:
        rate, timestamp = _rate_cache[cache_key]
        if datetime.utcnow() - timestamp < timedelta(hours=_CACHE_TTL_HOURS):
            return rate

    # Try to fetch from API (placeholder - implement if needed)
    # For now, return None to use default rates
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    if not api_key:
        return None

    try:
        import requests
        # Example using exchangerate-api.com (free tier)
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("result") == "success":
                rate = data.get("conversion_rate", 1.0)
                _rate_cache[cache_key] = (rate, datetime.utcnow())
                return rate
    except Exception as e:
        logger.debug(f"Failed to fetch live exchange rate: {e}")

    return None


def convert_to_usd(amount: float, from_currency: Optional[str]) -> Tuple[float, float]:
    """
    Convert an amount to USD.

    Args:
        amount: The amount in the source currency
        from_currency: The source currency code

    Returns:
        Tuple of (usd_amount, exchange_rate_used)
    """
    if not from_currency or from_currency.upper() == "USD":
        return amount, 1.0

    rate = get_exchange_rate(from_currency, "USD")
    return amount * rate, rate


def add_usd_conversion(cost_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add USD conversion fields to a cost data dictionary.

    This function takes a cost response and adds USD equivalents for
    consistent cross-tenancy comparison.

    Args:
        cost_data: Dictionary containing cost information with 'currency' field

    Returns:
        Updated dictionary with USD conversion fields added
    """
    if not isinstance(cost_data, dict):
        return cost_data

    currency = cost_data.get("currency")
    if not currency:
        return cost_data

    result = cost_data.copy()
    rate = get_exchange_rate(currency, "USD")

    # Add conversion metadata
    result["usd_conversion"] = {
        "original_currency": currency,
        "exchange_rate": rate,
        "rate_type": "live" if os.getenv("COST_LIVE_EXCHANGE_RATES", "false").lower() in ("true", "1", "yes") else "default"
    }

    # Convert common cost fields
    cost_fields = [
        "total_cost", "total", "cost", "amount", "computed_amount",
        "forecast", "next_month", "budget", "actual", "overage",
        "computeSpend", "spendToDate", "projected"
    ]

    for field in cost_fields:
        if field in result and isinstance(result[field], (int, float)):
            result[f"{field}_usd"] = round(result[field] * rate, 2)

    # Handle nested items
    if "items" in result and isinstance(result["items"], list):
        result["items"] = [_convert_item_to_usd(item, rate) for item in result["items"]]

    # Handle forecast data
    if "forecast" in result and isinstance(result["forecast"], dict):
        result["forecast"] = _convert_item_to_usd(result["forecast"], rate)

    # Handle series/trend data
    if "series" in result and isinstance(result["series"], list):
        result["series"] = [_convert_item_to_usd(item, rate) for item in result["series"]]

    # Handle services breakdown
    if "services" in result and isinstance(result["services"], list):
        result["services"] = [_convert_item_to_usd(item, rate) for item in result["services"]]

    # Handle FinOpsAI rows format (CostByCompartment, UnitCostOut, CostByResourceOut)
    if "rows" in result and isinstance(result["rows"], list):
        result["rows"] = [_convert_item_to_usd(item, rate) for item in result["rows"]]

    # Handle ServiceDrilldown top services
    if "top" in result and isinstance(result["top"], list):
        result["top"] = [_convert_top_service(item, rate) for item in result["top"]]

    # Handle budgets list
    if "budgets" in result and isinstance(result["budgets"], list):
        result["budgets"] = [_convert_item_to_usd(item, rate) for item in result["budgets"]]

    # Handle spikes
    if "spikes" in result and isinstance(result["spikes"], list):
        result["spikes"] = [_convert_item_to_usd(item, rate) for item in result["spikes"]]

    # Handle buckets (ObjectStorageOut)
    if "buckets" in result and isinstance(result["buckets"], list):
        result["buckets"] = [_convert_item_to_usd(item, rate) for item in result["buckets"]]

    return result


def _convert_top_service(item: Any, rate: float) -> Any:
    """Convert cost fields in a top service entry (ServiceDrilldown) to USD."""
    if not isinstance(item, dict):
        return item

    result = item.copy()

    # Convert main total field
    if "total" in result and isinstance(result["total"], (int, float)):
        result["total_usd"] = round(result["total"] * rate, 2)

    # Convert nested compartments
    if "compartments" in result and isinstance(result["compartments"], list):
        result["compartments"] = [_convert_item_to_usd(comp, rate) for comp in result["compartments"]]

    return result


def _convert_item_to_usd(item: Any, rate: float) -> Any:
    """Convert cost fields in an individual item to USD."""
    if not isinstance(item, dict):
        return item

    result = item.copy()
    cost_fields = [
        "cost", "amount", "total", "computed_amount", "computedAmount",
        "forecast", "budget", "actual", "next_month",
        "unitCost", "spendToDate", "projected", "delta"
    ]

    for field in cost_fields:
        if field in result and isinstance(result[field], (int, float)):
            result[f"{field}_usd"] = round(result[field] * rate, 2)

    return result


def format_cost_with_usd(
    amount: float,
    currency: Optional[str],
    include_original: bool = True
) -> str:
    """
    Format a cost amount with USD conversion for display.

    Args:
        amount: The cost amount
        currency: The original currency
        include_original: Whether to include the original currency amount

    Returns:
        Formatted string like "$1,234.56 USD (€1,143.11 EUR)"
    """
    if not currency or currency.upper() == "USD":
        return f"${amount:,.2f} USD"

    usd_amount, rate = convert_to_usd(amount, currency)

    if include_original:
        return f"${usd_amount:,.2f} USD ({amount:,.2f} {currency})"
    else:
        return f"${usd_amount:,.2f} USD"
