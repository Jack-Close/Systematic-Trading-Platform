"""
data.py — Market data ingestion via yfinance.

Imports: nothing from this project.
Exports: fetch_data, ASSET_CLASS_EXAMPLES.
"""

import yfinance as yf
import pandas as pd
import streamlit as st
from typing import Optional
from datetime import date, timedelta

# Session-level cache key prefix — avoids name collisions in st.session_state
_CACHE_PREFIX = "data_cache_"

# yfinance hard limits on how far back intraday data goes
_INTERVAL_MAX_DAYS = {
    "5m":  60,
    "15m": 60,
    "1h":  730,
    "4h":  730,
}

# Reference examples shown in the UI to help users pick tickers
ASSET_CLASS_EXAMPLES = {
    "Equity": "AAPL, MSFT, TSLA, SPY",
    "FX": "EURUSD=X, GBPUSD=X, USDJPY=X",
    "Crypto": "BTC-USD, ETH-USD, SOL-USD",
    "Commodity": "GC=F (Gold), CL=F (Crude Oil), SI=F (Silver)",
}


def fetch_data(
    ticker: str,
    interval: str,
    start: date,
    end: date,
) -> Optional[pd.DataFrame]:
    """
    Download OHLCV data for a ticker and cache it in the Streamlit session.

    Parameters
    ----------
    ticker   : yfinance ticker symbol, e.g. 'AAPL', 'BTC-USD', 'EURUSD=X'.
    interval : yfinance interval string, e.g. '1d', '1h'.
    start    : start date (inclusive).
    end      : end date (inclusive).

    Returns
    -------
    pd.DataFrame with columns [Open, High, Low, Close, Volume] and a
    DatetimeIndex, or None if the download failed.

    Notes
    -----
    auto_adjust=True means Close prices are already adjusted for splits and
    dividends — price history is internally consistent, which is essential for
    accurate backtesting (a split would otherwise look like a crash).
    """
    if end <= start:
        st.error("End date must be after start date.")
        return None

    max_days = _INTERVAL_MAX_DAYS.get(interval)
    if max_days is not None:
        range_days = (end - start).days
        if range_days > max_days:
            cutoff = end - timedelta(days=max_days)
            st.error(
                f"'{interval}' data is limited to {max_days} days by Yahoo Finance. "
                f"Your range spans {range_days} days — move the start date to {cutoff} or later."
            )
            return None

    cache_key = f"{_CACHE_PREFIX}{ticker}_{interval}_{start}_{end}"

    # Return cached copy if available — avoids redundant network requests
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    try:
        raw = yf.download(
            ticker,
            start=str(start),
            end=str(end),
            interval=interval,
            auto_adjust=True,
            progress=False,
        )

        if raw is None or raw.empty:
            st.error(f"No data returned for '{ticker}'. Check the ticker symbol.")
            return None

        # yfinance may return a MultiIndex when downloading a single ticker;
        # flatten it to simple column names.
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        # Keep only standard OHLCV columns
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in raw.columns]
        df = raw[cols].copy()

        # Drop any rows where Close is missing — can occur at end of data range
        df.dropna(subset=["Close"], inplace=True)

        st.session_state[cache_key] = df
        return df

    except Exception as exc:
        st.error(f"Failed to download data for '{ticker}': {exc}")
        return None
