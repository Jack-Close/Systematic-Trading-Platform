"""
strategies.py — Individual trading signal generators and signal combination.

Imports: nothing from this project.
Exports: sma_crossover, rsi_strategy, stoch_rsi_strategy, macd_strategy,
         bollinger_strategy, donchian_strategy, adx_strategy,
         ichimoku_strategy, combine_signals, apply_trend_filter, STRATEGY_REGISTRY.

Signal convention:  1 = long,  -1 = short,  0 = flat.
Signals are generated at the *close* of bar N; the position is entered at
the *open* of bar N+1 (enforced in backtest.py via shift(1)).  This one-bar
delay is the standard way to eliminate look-ahead bias.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import ta
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_signal(s: pd.Series) -> pd.Series:
    """Fill NaN signal values with 0. No forward-fill — signals are event-only."""
    return s.fillna(0).astype(int)


# ---------------------------------------------------------------------------
# Part A — Individual strategies
# ---------------------------------------------------------------------------

def sma_crossover(
    df: pd.DataFrame,
    fast_period: int = 10,
    slow_period: int = 50,
    buffer_pct: float = 0.0,
) -> pd.Series:
    """
    Simple Moving Average crossover strategy.

    Goes long when the fast SMA crosses above the slow SMA,
    short when it crosses below.

    When buffer_pct > 0, outputs a three-state signal: 1 when fast is at least
    buffer_pct above slow, -1 when at least buffer_pct below, 0 in the neutral
    zone between. This prevents whipsaws around the crossover level.

    Parameters
    ----------
    df          : OHLCV DataFrame.
    fast_period : Lookback bars for the fast SMA.
    slow_period : Lookback bars for the slow SMA.
    buffer_pct  : Minimum separation (as fraction of slow MA) before confirming
                  direction. 0.005 = 0.5%. Default 0 = standard crossover event.
    """
    if fast_period >= slow_period:
        raise ValueError(f"fast_period ({fast_period}) must be less than slow_period ({slow_period}).")
    if len(df) < slow_period:
        raise ValueError(f"Need at least {slow_period} bars for slow_period={slow_period}, but only {len(df)} available.")

    fast = df["Close"].rolling(fast_period).mean()
    slow = df["Close"].rolling(slow_period).mean()
    signal = pd.Series(0, index=df.index, dtype=int)

    if buffer_pct > 0:
        sep = (fast - slow) / slow.abs().clip(lower=1e-10)
        signal[sep >=  buffer_pct] =  1
        signal[sep <= -buffer_pct] = -1
    else:
        signal[(fast > slow) & (fast.shift(1) <= slow.shift(1))] =  1
        signal[(fast < slow) & (fast.shift(1) >= slow.shift(1))] = -1

    return _clean_signal(signal)


def rsi_strategy(
    df: pd.DataFrame,
    period: int = 14,
    oversold: int = 30,
    overbought: int = 70,
) -> pd.Series:
    """
    RSI mean-reversion strategy.

    Buys when RSI crosses back *above* the oversold level (reversal confirmation),
    sells when it crosses back *below* the overbought level.

    Parameters
    ----------
    df         : OHLCV DataFrame.
    period     : RSI lookback window.
    oversold   : Lower RSI threshold (long trigger).
    overbought : Upper RSI threshold (short trigger).

    Returns
    -------
    pd.Series of signals (1, -1, 0).
    """
    rsi = ta.momentum.RSIIndicator(df["Close"], window=period).rsi()

    # Use shift(1) to get the *previous* bar's RSI — detects crossover
    prev_rsi = rsi.shift(1)

    signal = pd.Series(0, index=df.index, dtype=int)
    # Cross up through oversold → long
    signal[(prev_rsi < oversold) & (rsi >= oversold)] = 1
    # Cross down through overbought → short
    signal[(prev_rsi > overbought) & (rsi <= overbought)] = -1
    return _clean_signal(signal)


def stoch_rsi_strategy(
    df: pd.DataFrame,
    period: int = 14,
    smooth_k: int = 3,
    smooth_d: int = 3,
    oversold: float = 20.0,
    overbought: float = 80.0,
) -> pd.Series:
    """
    Stochastic RSI strategy — same crossover logic as RSI but more sensitive.

    Parameters
    ----------
    df         : OHLCV DataFrame.
    period     : RSI and Stochastic lookback window.
    smooth_k   : Smoothing periods for %K line.
    smooth_d   : Smoothing periods for %D (signal) line.
    oversold   : Lower threshold for long signal.
    overbought : Upper threshold for short signal.

    Returns
    -------
    pd.Series of signals (1, -1, 0).
    """
    stoch = ta.momentum.StochRSIIndicator(
        df["Close"],
        window=period,
        smooth1=smooth_k,
        smooth2=smooth_d,
    )
    k = stoch.stochrsi_k() * 100  # scale to 0–100 to match standard convention
    prev_k = k.shift(1)

    signal = pd.Series(0, index=df.index, dtype=int)
    signal[(prev_k < oversold) & (k >= oversold)] = 1
    signal[(prev_k > overbought) & (k <= overbought)] = -1
    return _clean_signal(signal)


def macd_strategy(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> pd.Series:
    """
    MACD line / signal line crossover strategy.

    Goes long when MACD line crosses above the signal line,
    short when it crosses below.

    Parameters
    ----------
    df            : OHLCV DataFrame.
    fast          : Fast EMA window.
    slow          : Slow EMA window.
    signal_period : Signal line (EMA of MACD) window.

    Returns
    -------
    pd.Series of signals (1, -1, 0).
    """
    if fast >= slow:
        raise ValueError(f"fast ({fast}) must be less than slow ({slow}).")

    macd_ind = ta.trend.MACD(df["Close"], window_fast=fast, window_slow=slow, window_sign=signal_period)
    macd_line = macd_ind.macd()
    signal_line = macd_ind.macd_signal()

    prev_macd = macd_line.shift(1)
    prev_sig = signal_line.shift(1)

    sig = pd.Series(0, index=df.index, dtype=int)
    sig[(prev_macd < prev_sig) & (macd_line >= signal_line)] = 1
    sig[(prev_macd > prev_sig) & (macd_line <= signal_line)] = -1
    return _clean_signal(sig)


def bollinger_strategy(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
) -> pd.Series:
    """
    Bollinger Band mean-reversion strategy.

    Buys when price touches the lower band (oversold),
    sells when price touches the upper band (overbought).

    Parameters
    ----------
    df      : OHLCV DataFrame.
    period  : Rolling window for the middle band (SMA).
    std_dev : Number of standard deviations for the bands.

    Returns
    -------
    pd.Series of signals (1, -1, 0).
    """
    bb    = ta.volatility.BollingerBands(df["Close"], window=period, window_dev=std_dev)
    lower = bb.bollinger_lband()
    upper = bb.bollinger_hband()
    prev  = df["Close"].shift(1)

    sig = pd.Series(0, index=df.index, dtype=int)
    # Signal only on the bar price first crosses the band, not while it stays there
    sig[(df["Close"] <= lower) & (prev > lower)] = 1
    sig[(df["Close"] >= upper) & (prev < upper)] = -1
    return _clean_signal(sig)


def donchian_strategy(
    df: pd.DataFrame,
    period: int = 20,
    buffer_pct: float = 0.0,
) -> pd.Series:
    """
    Donchian Channel breakout (momentum) strategy.

    Buys when price breaks above the highest high of the last N bars,
    sells when price breaks below the lowest low.

    When buffer_pct > 0, price must close at least buffer_pct beyond the channel
    edge before the breakout signal fires. Filters out marginal/false breakouts.

    Parameters
    ----------
    df         : OHLCV DataFrame.
    period     : Lookback window for channel calculation.
    buffer_pct : Minimum excess beyond channel edge as a fraction of channel edge
                 price (e.g. 0.002 = 0.2%). Default 0 = standard breakout.
    """
    dc    = ta.volatility.DonchianChannel(df["High"], df["Low"], df["Close"], window=period)
    upper = dc.donchian_channel_hband().shift(1)
    lower = dc.donchian_channel_lband().shift(1)

    above_upper = df["Close"] > upper * (1 + buffer_pct)
    below_lower = df["Close"] < lower * (1 - buffer_pct)

    sig = pd.Series(0, index=df.index, dtype=int)
    sig[above_upper & ~above_upper.shift(1).fillna(False)] =  1
    sig[below_lower & ~below_lower.shift(1).fillna(False)] = -1
    return _clean_signal(sig)


def adx_strategy(
    df: pd.DataFrame,
    period: int = 14,
    threshold: float = 25.0,
) -> pd.Series:
    """
    ADX trend-filter strategy.

    Uses the SMA crossover direction but only takes a position when
    ADX is above `threshold`, indicating a trending market.
    Flat (0) when ADX says the market is ranging.

    Parameters
    ----------
    df        : OHLCV DataFrame.
    period    : ADX and SMA lookback window.
    threshold : Minimum ADX value to enter a trade.

    Returns
    -------
    pd.Series of signals (1, -1, 0).
    """
    adx_ind  = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"], window=period)
    adx      = adx_ind.adx()
    di_plus  = adx_ind.adx_pos()
    di_minus = adx_ind.adx_neg()
    trending = adx > threshold

    # Signal only when DI lines cross while the market is trending
    sig = pd.Series(0, index=df.index, dtype=int)
    sig[trending & (di_plus.shift(1) <= di_minus.shift(1)) & (di_plus > di_minus)] = 1
    sig[trending & (di_minus.shift(1) <= di_plus.shift(1)) & (di_minus > di_plus)] = -1
    return _clean_signal(sig)


def tsmom(
    df: pd.DataFrame,
    lookback: int = 12,
    threshold: float = 0.0,
) -> pd.Series:
    """
    Time-Series Momentum (TSMOM).

    Signal is the sign of the rolling return over the lookback period.
    Long if return > threshold, Short if return < -threshold.

    Parameters
    ----------
    df        : OHLCV DataFrame.
    lookback  : Rolling return window in bars.
    threshold : Minimum fractional return to trigger a signal (default 0 = any).

    Returns
    -------
    pd.Series of signals (1, -1, 0).
    """
    rolling_ret = df["Close"].pct_change(lookback)
    sig = pd.Series(0, index=df.index, dtype=int)
    sig[rolling_ret >  threshold] = 1
    sig[rolling_ret < -threshold] = -1
    return _clean_signal(sig)


def zscore_mean_reversion(
    df: pd.DataFrame,
    lookback: int = 20,
    threshold: float = 2.0,
) -> pd.Series:
    """
    Z-Score mean-reversion strategy.

    Computes z = (Close - rolling_mean) / rolling_std.
    Long when z crosses below -threshold (price is statistically cheap).
    Short when z crosses above +threshold (price is statistically expensive).

    Parameters
    ----------
    df        : OHLCV DataFrame.
    lookback  : Rolling window for mean and std.
    threshold : Z-score magnitude that triggers a signal.

    Returns
    -------
    pd.Series of signals (1, -1, 0).
    """
    close = df["Close"]
    z     = (close - close.rolling(lookback).mean()) / close.rolling(lookback).std()
    prev_z = z.shift(1)

    sig = pd.Series(0, index=df.index, dtype=int)
    sig[(prev_z >= -threshold) & (z < -threshold)] = 1
    sig[(prev_z <= threshold)  & (z > threshold)]  = -1
    return _clean_signal(sig)


def ichimoku_strategy(
    df: pd.DataFrame,
    tenkan: int = 9,
    kijun: int = 26,
    senkou_b: int = 52,
) -> pd.Series:
    """
    Ichimoku Cloud strategy — Tenkan/Kijun cross filtered by Cloud position.

    Goes long when Tenkan crosses above Kijun AND price is above the Cloud.
    Goes short when Tenkan crosses below Kijun AND price is below the Cloud.

    Parameters
    ----------
    df       : OHLCV DataFrame.
    tenkan   : Tenkan-sen (conversion line) period.
    kijun    : Kijun-sen (base line) period.
    senkou_b : Senkou Span B period.

    Returns
    -------
    pd.Series of signals (1, -1, 0).
    """
    if tenkan >= kijun:
        raise ValueError(f"tenkan ({tenkan}) must be less than kijun ({kijun}).")
    if kijun >= senkou_b:
        raise ValueError(f"kijun ({kijun}) must be less than senkou_b ({senkou_b}).")

    ichi = ta.trend.IchimokuIndicator(
        df["High"],
        df["Low"],
        window1=tenkan,
        window2=kijun,
        window3=senkou_b,
    )
    tenkan_line = ichi.ichimoku_conversion_line()
    kijun_line = ichi.ichimoku_base_line()
    span_a = ichi.ichimoku_a()
    span_b = ichi.ichimoku_b()

    # Span A/B from ta are calculated at bar T but conventionally displayed at T+kijun.
    # Shift forward by kijun so cloud_top[T] = the cloud visible at bar T (not future values).
    cloud_top    = pd.concat([span_a.shift(kijun), span_b.shift(kijun)], axis=1).max(axis=1)
    cloud_bottom = pd.concat([span_a.shift(kijun), span_b.shift(kijun)], axis=1).min(axis=1)

    prev_tenkan = tenkan_line.shift(1)
    prev_kijun = kijun_line.shift(1)

    sig = pd.Series(0, index=df.index, dtype=int)

    bull_cross = (prev_tenkan <= prev_kijun) & (tenkan_line > kijun_line)
    bear_cross = (prev_tenkan >= prev_kijun) & (tenkan_line < kijun_line)

    sig[bull_cross & (df["Close"] > cloud_top)] = 1
    sig[bear_cross & (df["Close"] < cloud_bottom)] = -1
    return _clean_signal(sig)


def ema_crossover(
    df: pd.DataFrame,
    fast_period: int = 10,
    slow_period: int = 50,
    buffer_pct: float = 0.0,
) -> pd.Series:
    """EMA crossover — long when fast EMA crosses above slow EMA.

    When buffer_pct > 0, outputs a three-state signal using the same separation
    logic as sma_crossover: neutral zone between -buffer_pct and +buffer_pct.
    """
    if fast_period >= slow_period:
        raise ValueError(f"fast_period ({fast_period}) must be less than slow_period ({slow_period}).")
    fast = df["Close"].ewm(span=fast_period, adjust=False).mean()
    slow = df["Close"].ewm(span=slow_period, adjust=False).mean()
    sig  = pd.Series(0, index=df.index, dtype=int)

    if buffer_pct > 0:
        sep = (fast - slow) / slow.abs().clip(lower=1e-10)
        sig[sep >=  buffer_pct] =  1
        sig[sep <= -buffer_pct] = -1
    else:
        sig[(fast > slow) & (fast.shift(1) <= slow.shift(1))] =  1
        sig[(fast < slow) & (fast.shift(1) >= slow.shift(1))] = -1

    return _clean_signal(sig)


def price_vs_ma(
    df: pd.DataFrame,
    period: int = 50,
    ma_type: str = "SMA",
    buffer_pct: float = 0.0,
) -> pd.Series:
    """State signal — long while price is above the MA, short while below.

    When buffer_pct > 0, price must be at least buffer_pct beyond the MA to
    confirm a direction. Price within buffer_pct of the MA produces a 0 signal
    (neutral zone), avoiding flips on marginal crossings.
    """
    ma = (
        df["Close"].ewm(span=period, adjust=False).mean()
        if ma_type == "EMA"
        else df["Close"].rolling(period).mean()
    )
    sig = pd.Series(0, index=df.index, dtype=int)
    sig[df["Close"] > ma * (1 + buffer_pct)] =  1
    sig[df["Close"] < ma * (1 - buffer_pct)] = -1
    return _clean_signal(sig)


def ma_slope(
    df: pd.DataFrame,
    period: int = 20,
    slope_threshold: float = 0.0,
) -> pd.Series:
    """State signal — long while MA slopes up by more than threshold, short while sloping down."""
    ma    = df["Close"].rolling(period).mean()
    slope = ma.diff()
    sig   = pd.Series(0, index=df.index, dtype=int)
    sig[slope >  slope_threshold] = 1
    sig[slope < -slope_threshold] = -1
    return _clean_signal(sig)


def macd_histogram_strategy(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> pd.Series:
    """State signal — long while MACD histogram is positive (momentum accelerating up)."""
    if fast >= slow:
        raise ValueError(f"fast ({fast}) must be less than slow ({slow}).")
    hist = ta.trend.MACD(
        df["Close"], window_fast=fast, window_slow=slow, window_sign=signal_period
    ).macd_diff()
    sig = pd.Series(0, index=df.index, dtype=int)
    sig[hist > 0] = 1
    sig[hist < 0] = -1
    return _clean_signal(sig)


def turtle_breakout(
    df: pd.DataFrame,
    entry_period: int = 20,
    exit_period: int = 10,
) -> pd.Series:
    """
    Classic Turtle system — enter on N-bar channel breakout, exit on shorter channel reversal.
    Uses a state machine: position persists until exit channel is breached or direction reverses.
    """
    if exit_period >= entry_period:
        exit_period = max(2, entry_period - 1)

    entry_h = df["High"].rolling(entry_period).max().shift(1).values
    entry_l = df["Low"].rolling(entry_period).min().shift(1).values
    exit_h  = df["High"].rolling(exit_period).max().shift(1).values
    exit_l  = df["Low"].rolling(exit_period).min().shift(1).values
    close   = df["Close"].values
    n       = len(close)
    sig     = np.zeros(n, dtype=np.int8)
    d       = 0

    for i in range(entry_period, n):
        if np.isnan(entry_h[i]) or np.isnan(entry_l[i]):
            continue
        if d == 0:
            if close[i] > entry_h[i]:
                d = 1
            elif close[i] < entry_l[i]:
                d = -1
        elif d == 1:
            if not np.isnan(exit_l[i]) and close[i] < exit_l[i]:
                d = 0
            elif close[i] < entry_l[i]:
                d = -1
        else:
            if not np.isnan(exit_h[i]) and close[i] > exit_h[i]:
                d = 0
            elif close[i] > entry_h[i]:
                d = 1
        sig[i] = d

    return _clean_signal(pd.Series(sig, index=df.index))


def supertrend(
    df: pd.DataFrame,
    period: int = 10,
    multiplier: float = 3.0,
) -> pd.Series:
    """
    SuperTrend — ATR-based trailing bands with a direction state machine.
    Long while price is above the lower band, short while below the upper band.
    """
    high  = df["High"]
    low   = df["Low"]
    close = df["Close"]

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    hl2       = (high + low) / 2
    upper_arr = (hl2 + multiplier * atr).values.copy()
    lower_arr = (hl2 - multiplier * atr).values.copy()
    close_arr = close.values
    n         = len(close_arr)

    for i in range(1, n):
        if np.isnan(upper_arr[i]) or np.isnan(upper_arr[i - 1]):
            continue
        upper_arr[i] = (
            upper_arr[i]
            if upper_arr[i] < upper_arr[i - 1] or close_arr[i - 1] > upper_arr[i - 1]
            else upper_arr[i - 1]
        )
        lower_arr[i] = (
            lower_arr[i]
            if lower_arr[i] > lower_arr[i - 1] or close_arr[i - 1] < lower_arr[i - 1]
            else lower_arr[i - 1]
        )

    direction_arr = np.zeros(n, dtype=np.int8)
    d = 1
    for i in range(1, n):
        if np.isnan(upper_arr[i]) or np.isnan(lower_arr[i]):
            continue
        if d == 1:
            if close_arr[i] < lower_arr[i]:
                d = -1
        else:
            if close_arr[i] > upper_arr[i]:
                d = 1
        direction_arr[i] = d

    return _clean_signal(pd.Series(direction_arr, index=df.index))


def psar_strategy(
    df: pd.DataFrame,
    step: float = 0.02,
    max_step: float = 0.2,
) -> pd.Series:
    """Parabolic SAR — long while price is above the SAR dot, short while below."""
    psar = ta.trend.PSARIndicator(
        df["High"], df["Low"], df["Close"], step=step, max_step=max_step
    ).psar()
    sig = pd.Series(0, index=df.index, dtype=int)
    sig[df["Close"] > psar] = 1
    sig[df["Close"] < psar] = -1
    return _clean_signal(sig)


# ---------------------------------------------------------------------------
# Part B — Signal combination
# ---------------------------------------------------------------------------

def combine_signals(
    signal_dict: Dict[str, pd.Series],
    method: str = "majority_vote",
    weights: Optional[Dict[str, float]] = None,
    threshold: float = 0.5,
) -> pd.Series:
    """
    Combine multiple strategy signals into a single composite signal.

    Parameters
    ----------
    signal_dict : Mapping of strategy name → signal Series (1, -1, 0).
    method      : One of 'majority_vote', 'weighted', 'threshold'.
    weights     : Required when method='weighted'. Dict of strategy → weight.
                  Weights are normalised internally so they needn't sum to 1.
    threshold   : Used when method='threshold'. Long if avg > +threshold,
                  short if avg < -threshold, else flat.

    Returns
    -------
    pd.Series of combined signals (1, -1, 0).

    Methods explained
    -----------------
    majority_vote : sign(sum of signals) — majority of strategies wins.
    weighted      : weighted average → sign() for direction.
    threshold     : average signal must exceed ±threshold to take a position;
                    useful for requiring stronger consensus before trading.
    """
    if not signal_dict:
        raise ValueError("signal_dict is empty — no signals to combine.")

    df = pd.DataFrame(signal_dict)

    if method == "majority_vote":
        combined = df.sum(axis=1).apply(np.sign)

    elif method == "weighted":
        if weights is None:
            # Equal weight fallback
            weights = {k: 1.0 for k in signal_dict}
        w = pd.Series(weights)
        w = w / w.sum()  # normalise
        combined = df[w.index].mul(w, axis=1).sum(axis=1).apply(np.sign)

    elif method == "threshold":
        avg = df.mean(axis=1)
        combined = pd.Series(0, index=df.index, dtype=float)
        combined[avg > threshold] = 1.0
        combined[avg < -threshold] = -1.0

    else:
        raise ValueError(f"Unknown combination method: '{method}'")

    return combined.astype(int)


# ---------------------------------------------------------------------------
# Indicator overlay builders — return data for plot_signals_on_price
# Each returns a list of {"panel": "price"|"oscillator", "traces": [...],
#                         "yaxis_title": str, "yaxis_range": [lo, hi]}
# ---------------------------------------------------------------------------

def _sma_indicators(df: pd.DataFrame, fast_period: int = 10, slow_period: int = 50, **_) -> list:
    fast = df["Close"].rolling(fast_period).mean()
    slow = df["Close"].rolling(slow_period).mean()
    return [{"panel": "price", "traces": [
        go.Scatter(x=df.index, y=fast, name=f"SMA {fast_period}",  line=dict(color="#f59e0b", width=1.5)),
        go.Scatter(x=df.index, y=slow, name=f"SMA {slow_period}", line=dict(color="#60a5fa", width=1.5)),
    ]}]


def _rsi_indicators(df: pd.DataFrame, period: int = 14, oversold: int = 30, overbought: int = 70) -> list:
    rsi = ta.momentum.RSIIndicator(df["Close"], window=period).rsi()
    n   = len(df)
    return [{"panel": "oscillator", "yaxis_title": "RSI", "yaxis_range": [0, 100], "traces": [
        go.Scatter(x=df.index, y=rsi, name=f"RSI({period})", line=dict(color="#a78bfa", width=1.5)),
        go.Scatter(x=df.index, y=[oversold]  * n, name="Oversold",   line=dict(color="#22c55e", width=1, dash="dash"), showlegend=False),
        go.Scatter(x=df.index, y=[overbought] * n, name="Overbought", line=dict(color="#ef4444", width=1, dash="dash"), showlegend=False),
    ]}]


def _stoch_rsi_indicators(df: pd.DataFrame, period: int = 14, smooth_k: int = 3, smooth_d: int = 3,
                           oversold: float = 20.0, overbought: float = 80.0) -> list:
    stoch = ta.momentum.StochRSIIndicator(df["Close"], window=period, smooth1=smooth_k, smooth2=smooth_d)
    k = stoch.stochrsi_k() * 100
    d = stoch.stochrsi_d() * 100
    n = len(df)
    return [{"panel": "oscillator", "yaxis_title": "StochRSI", "yaxis_range": [0, 100], "traces": [
        go.Scatter(x=df.index, y=k, name="%K", line=dict(color="#a78bfa", width=1.5)),
        go.Scatter(x=df.index, y=d, name="%D", line=dict(color="#fb923c", width=1.5)),
        go.Scatter(x=df.index, y=[oversold]  * n, name="Oversold",   line=dict(color="#22c55e", width=1, dash="dash"), showlegend=False),
        go.Scatter(x=df.index, y=[overbought] * n, name="Overbought", line=dict(color="#ef4444", width=1, dash="dash"), showlegend=False),
    ]}]


def _macd_indicators(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal_period: int = 9) -> list:
    macd_ind  = ta.trend.MACD(df["Close"], window_fast=fast, window_slow=slow, window_sign=signal_period)
    macd_line = macd_ind.macd()
    sig_line  = macd_ind.macd_signal()
    hist      = macd_ind.macd_diff()
    colors    = ["#22c55e" if (v == v and v >= 0) else "#ef4444" for v in hist.fillna(0)]
    return [{"panel": "oscillator", "yaxis_title": "MACD", "traces": [
        go.Bar(x=df.index, y=hist, name="Histogram", marker_color=colors, opacity=0.5),
        go.Scatter(x=df.index, y=macd_line, name=f"MACD({fast},{slow})",    line=dict(color="#60a5fa", width=1.5)),
        go.Scatter(x=df.index, y=sig_line,  name=f"Signal({signal_period})", line=dict(color="#f59e0b", width=1.5)),
    ]}]


def _bollinger_indicators(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> list:
    bb    = ta.volatility.BollingerBands(df["Close"], window=period, window_dev=std_dev)
    upper = bb.bollinger_hband()
    lower = bb.bollinger_lband()
    mid   = bb.bollinger_mavg()
    return [{"panel": "price", "traces": [
        go.Scatter(x=df.index, y=upper, name=f"BB Upper ({std_dev}σ)",
                   line=dict(color="rgba(148,163,184,0.7)", width=1)),
        go.Scatter(x=df.index, y=lower, name=f"BB Lower ({std_dev}σ)",
                   line=dict(color="rgba(148,163,184,0.7)", width=1),
                   fill="tonexty", fillcolor="rgba(148,163,184,0.08)"),
        go.Scatter(x=df.index, y=mid, name=f"BB Mid ({period})",
                   line=dict(color="rgba(148,163,184,0.4)", width=1, dash="dot"), showlegend=False),
    ]}]


def _donchian_indicators(df: pd.DataFrame, period: int = 20, **_) -> list:
    dc    = ta.volatility.DonchianChannel(df["High"], df["Low"], df["Close"], window=period)
    upper = dc.donchian_channel_hband()
    lower = dc.donchian_channel_lband()
    mid   = dc.donchian_channel_mband()
    return [{"panel": "price", "traces": [
        go.Scatter(x=df.index, y=upper, name=f"DC Upper ({period})",
                   line=dict(color="rgba(96,165,250,0.7)", width=1)),
        go.Scatter(x=df.index, y=lower, name=f"DC Lower ({period})",
                   line=dict(color="rgba(96,165,250,0.7)", width=1),
                   fill="tonexty", fillcolor="rgba(96,165,250,0.08)"),
        go.Scatter(x=df.index, y=mid, name=f"DC Mid ({period})",
                   line=dict(color="rgba(96,165,250,0.4)", width=1, dash="dot"), showlegend=False),
    ]}]


def _adx_indicators(df: pd.DataFrame, period: int = 14, threshold: float = 25.0) -> list:
    adx_ind  = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"], window=period)
    adx      = adx_ind.adx()
    di_plus  = adx_ind.adx_pos()
    di_minus = adx_ind.adx_neg()
    n        = len(df)
    return [{"panel": "oscillator", "yaxis_title": "ADX", "traces": [
        go.Scatter(x=df.index, y=adx,      name=f"ADX({period})", line=dict(color="#f59e0b", width=2)),
        go.Scatter(x=df.index, y=di_plus,  name="+DI",            line=dict(color="#22c55e", width=1.5)),
        go.Scatter(x=df.index, y=di_minus, name="-DI",            line=dict(color="#ef4444", width=1.5)),
        go.Scatter(x=df.index, y=[threshold] * n, name="Threshold",
                   line=dict(color="#94a3b8", width=1, dash="dash"), showlegend=False),
    ]}]


def _tsmom_indicators(df: pd.DataFrame, lookback: int = 12) -> list:
    rolling_ret = df["Close"].pct_change(lookback) * 100
    return [{"panel": "oscillator", "yaxis_title": f"Return({lookback}b) %", "traces": [
        go.Scatter(x=df.index, y=rolling_ret, name=f"TSMOM({lookback}b)",
                   line=dict(color="#60a5fa", width=1.5)),
        go.Scatter(x=df.index, y=[0] * len(df), name="Zero",
                   line=dict(color="#94a3b8", width=1, dash="dash"), showlegend=False),
    ]}]


def _zscore_indicators(df: pd.DataFrame, lookback: int = 20, threshold: float = 2.0) -> list:
    close = df["Close"]
    z = (close - close.rolling(lookback).mean()) / close.rolling(lookback).std()
    n = len(df)
    return [{"panel": "oscillator", "yaxis_title": "Z-Score", "traces": [
        go.Scatter(x=df.index, y=z, name=f"Z-Score({lookback})",
                   line=dict(color="#a78bfa", width=1.5)),
        go.Scatter(x=df.index, y=[ threshold] * n, name=f"+{threshold}σ",
                   line=dict(color="#ef4444", width=1, dash="dash"), showlegend=False),
        go.Scatter(x=df.index, y=[-threshold] * n, name=f"-{threshold}σ",
                   line=dict(color="#22c55e", width=1, dash="dash"), showlegend=False),
        go.Scatter(x=df.index, y=[0] * n, name="Zero",
                   line=dict(color="#94a3b8", width=0.8, dash="dot"), showlegend=False),
    ]}]


def _ichimoku_indicators(df: pd.DataFrame, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52) -> list:
    ichi        = ta.trend.IchimokuIndicator(df["High"], df["Low"], window1=tenkan, window2=kijun, window3=senkou_b)
    tenkan_line = ichi.ichimoku_conversion_line()
    kijun_line  = ichi.ichimoku_base_line()
    span_a      = ichi.ichimoku_a()
    span_b      = ichi.ichimoku_b()
    return [{"panel": "price", "traces": [
        go.Scatter(x=df.index, y=tenkan_line, name=f"Tenkan ({tenkan})", line=dict(color="#ef4444", width=1.5)),
        go.Scatter(x=df.index, y=kijun_line,  name=f"Kijun ({kijun})",  line=dict(color="#60a5fa", width=1.5)),
        go.Scatter(x=df.index, y=span_a, name="Span A (Cloud)",
                   line=dict(color="rgba(34,197,94,0.6)",  width=1)),
        go.Scatter(x=df.index, y=span_b, name="Span B (Cloud)",
                   line=dict(color="rgba(239,68,68,0.6)", width=1),
                   fill="tonexty", fillcolor="rgba(148,163,184,0.1)"),
    ]}]


def _ema_indicators(df: pd.DataFrame, fast_period: int = 10, slow_period: int = 50, **_) -> list:
    fast = df["Close"].ewm(span=fast_period, adjust=False).mean()
    slow = df["Close"].ewm(span=slow_period, adjust=False).mean()
    return [{"panel": "price", "traces": [
        go.Scatter(x=df.index, y=fast, name=f"EMA {fast_period}", line=dict(color="#f59e0b", width=1.5)),
        go.Scatter(x=df.index, y=slow, name=f"EMA {slow_period}", line=dict(color="#60a5fa", width=1.5)),
    ]}]


def _price_vs_ma_indicators(df: pd.DataFrame, period: int = 50, ma_type: str = "SMA", **_) -> list:
    ma = (
        df["Close"].ewm(span=period, adjust=False).mean()
        if ma_type == "EMA"
        else df["Close"].rolling(period).mean()
    )
    return [{"panel": "price", "traces": [
        go.Scatter(x=df.index, y=ma, name=f"{ma_type}({period})", line=dict(color="#f59e0b", width=1.5)),
    ]}]


def _ma_slope_indicators(df: pd.DataFrame, period: int = 20, slope_threshold: float = 0.0) -> list:
    ma    = df["Close"].rolling(period).mean()
    slope = ma.diff()
    n     = len(df)
    return [
        {"panel": "price", "traces": [
            go.Scatter(x=df.index, y=ma, name=f"SMA({period})", line=dict(color="#f59e0b", width=1.5)),
        ]},
        {"panel": "oscillator", "yaxis_title": "MA Slope", "traces": [
            go.Scatter(x=df.index, y=slope, name="Slope", line=dict(color="#a78bfa", width=1.5)),
            go.Scatter(x=df.index, y=[ slope_threshold] * n, name="+threshold",
                       line=dict(color="#22c55e", width=1, dash="dash"), showlegend=False),
            go.Scatter(x=df.index, y=[-slope_threshold] * n, name="-threshold",
                       line=dict(color="#ef4444", width=1, dash="dash"), showlegend=False),
        ]},
    ]


def _macd_histogram_indicators(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal_period: int = 9) -> list:
    return _macd_indicators(df, fast=fast, slow=slow, signal_period=signal_period)


def _turtle_breakout_indicators(df: pd.DataFrame, entry_period: int = 20, exit_period: int = 10) -> list:
    eh = df["High"].rolling(entry_period).max()
    el = df["Low"].rolling(entry_period).min()
    xh = df["High"].rolling(exit_period).max()
    xl = df["Low"].rolling(exit_period).min()
    return [{"panel": "price", "traces": [
        go.Scatter(x=df.index, y=eh, name=f"Entry Hi ({entry_period})",
                   line=dict(color="rgba(96,165,250,0.8)", width=1.5)),
        go.Scatter(x=df.index, y=el, name=f"Entry Lo ({entry_period})",
                   line=dict(color="rgba(96,165,250,0.8)", width=1.5)),
        go.Scatter(x=df.index, y=xh, name=f"Exit Hi ({exit_period})",
                   line=dict(color="rgba(245,158,11,0.6)", width=1, dash="dot")),
        go.Scatter(x=df.index, y=xl, name=f"Exit Lo ({exit_period})",
                   line=dict(color="rgba(245,158,11,0.6)", width=1, dash="dot")),
    ]}]


def _supertrend_indicators(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> list:
    high  = df["High"]
    low   = df["Low"]
    close = df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr       = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    hl2       = (high + low) / 2
    upper_arr = (hl2 + multiplier * atr).values.copy()
    lower_arr = (hl2 - multiplier * atr).values.copy()
    close_arr = close.values
    n         = len(close_arr)

    for i in range(1, n):
        if np.isnan(upper_arr[i]) or np.isnan(upper_arr[i - 1]):
            continue
        upper_arr[i] = upper_arr[i] if (upper_arr[i] < upper_arr[i - 1] or close_arr[i - 1] > upper_arr[i - 1]) else upper_arr[i - 1]
        lower_arr[i] = lower_arr[i] if (lower_arr[i] > lower_arr[i - 1] or close_arr[i - 1] < lower_arr[i - 1]) else lower_arr[i - 1]

    direction_arr = np.zeros(n, dtype=np.int8)
    d = 1
    for i in range(1, n):
        if np.isnan(upper_arr[i]) or np.isnan(lower_arr[i]):
            continue
        if d == 1:
            if close_arr[i] < lower_arr[i]:
                d = -1
        else:
            if close_arr[i] > upper_arr[i]:
                d = 1
        direction_arr[i] = d

    bull = np.where(direction_arr == 1,  lower_arr, np.nan)
    bear = np.where(direction_arr == -1, upper_arr, np.nan)
    return [{"panel": "price", "traces": [
        go.Scatter(x=df.index, y=pd.Series(bull, index=df.index),
                   name=f"ST Bull({period},{multiplier})", line=dict(color="#22c55e", width=2)),
        go.Scatter(x=df.index, y=pd.Series(bear, index=df.index),
                   name=f"ST Bear({period},{multiplier})", line=dict(color="#ef4444", width=2)),
    ]}]


def _psar_indicators(df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2) -> list:
    psar_vals = ta.trend.PSARIndicator(
        df["High"], df["Low"], df["Close"], step=step, max_step=max_step
    ).psar()
    return [{"panel": "price", "traces": [
        go.Scatter(
            x=df.index, y=psar_vals,
            name=f"PSAR({step},{max_step})",
            mode="markers",
            marker=dict(size=3, color="#f472b6", symbol="circle"),
        ),
    ]}]


# ---------------------------------------------------------------------------
# Strategy registry — used by the UI to discover available strategies
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY = {
    # ── Trend / Momentum ──────────────────────────────────────────────────────
    "SMA Crossover": {
        "family":     "Trend / Momentum",
        "fn":         sma_crossover,
        "indicators": _sma_indicators,
        "params": {
            "fast_period": {"type": int, "default": 10, "min": 2,  "max": 100},
            "slow_period": {"type": int, "default": 50, "min": 5,  "max": 300},
        },
    },
    "MACD": {
        "family":     "Trend / Momentum",
        "fn":         macd_strategy,
        "indicators": _macd_indicators,
        "params": {
            "fast":          {"type": int, "default": 12, "min": 2,  "max": 50},
            "slow":          {"type": int, "default": 26, "min": 5,  "max": 100},
            "signal_period": {"type": int, "default": 9,  "min": 2,  "max": 30},
        },
    },
    "Donchian Channels": {
        "family":     "Trend / Momentum",
        "fn":         donchian_strategy,
        "indicators": _donchian_indicators,
        "params": {
            "period": {"type": int, "default": 20, "min": 5, "max": 100},
        },
    },
    "ADX": {
        "family":     "Trend / Momentum",
        "fn":         adx_strategy,
        "indicators": _adx_indicators,
        "params": {
            "period":    {"type": int,   "default": 14,   "min": 2,    "max": 50},
            "threshold": {"type": float, "default": 25.0, "min": 10.0, "max": 50.0},
        },
    },
    "Ichimoku": {
        "family":     "Trend / Momentum",
        "fn":         ichimoku_strategy,
        "indicators": _ichimoku_indicators,
        "params": {
            "tenkan":   {"type": int, "default": 9,  "min": 5,  "max": 30},
            "kijun":    {"type": int, "default": 26, "min": 10, "max": 60},
            "senkou_b": {"type": int, "default": 52, "min": 20, "max": 120},
        },
    },
    "Time-Series Momentum": {
        "family":     "Trend / Momentum",
        "fn":         tsmom,
        "indicators": _tsmom_indicators,
        "params": {
            "lookback": {"type": int, "default": 12, "min": 2, "max": 252},
        },
    },
    # ── Mean Reversion ────────────────────────────────────────────────────────
    "RSI": {
        "family":     "Mean Reversion",
        "fn":         rsi_strategy,
        "indicators": _rsi_indicators,
        "params": {
            "period":     {"type": int, "default": 14, "min": 2,  "max": 100},
            "oversold":   {"type": int, "default": 30, "min": 10, "max": 45},
            "overbought": {"type": int, "default": 70, "min": 55, "max": 90},
        },
    },
    "Stochastic RSI": {
        "family":     "Mean Reversion",
        "fn":         stoch_rsi_strategy,
        "indicators": _stoch_rsi_indicators,
        "params": {
            "period":     {"type": int,   "default": 14,   "min": 2,    "max": 100},
            "smooth_k":   {"type": int,   "default": 3,    "min": 1,    "max": 10},
            "smooth_d":   {"type": int,   "default": 3,    "min": 1,    "max": 10},
            "oversold":   {"type": float, "default": 20.0, "min": 5.0,  "max": 40.0},
            "overbought": {"type": float, "default": 80.0, "min": 60.0, "max": 95.0},
        },
    },
    "Bollinger Bands": {
        "family":     "Mean Reversion",
        "fn":         bollinger_strategy,
        "indicators": _bollinger_indicators,
        "params": {
            "period":  {"type": int,   "default": 20,  "min": 5,   "max": 100},
            "std_dev": {"type": float, "default": 2.0, "min": 0.5, "max": 4.0},
        },
    },
    "Z-Score Mean Reversion": {
        "family":     "Mean Reversion",
        "fn":         zscore_mean_reversion,
        "indicators": _zscore_indicators,
        "params": {
            "lookback":  {"type": int,   "default": 20,  "min": 5,   "max": 200},
            "threshold": {"type": float, "default": 2.0, "min": 0.5, "max": 4.0},
        },
    },
}


# ---------------------------------------------------------------------------
# Trend/Momentum builder registry
# natural_mode: "state" = persistent signal every bar; "event" = crossover only
# ---------------------------------------------------------------------------

TREND_SIGNAL_REGISTRY: Dict[str, Dict] = {
    "TSMOM": {
        "fn":           tsmom,
        "indicators":   _tsmom_indicators,
        "natural_mode": "state",
        "description":  "Long when N-bar return > threshold, short when < −threshold.",
        "params": {
            "lookback":  {"type": int,   "default": 12,  "min": 2,   "max": 252, "label": "Lookback (bars)"},
            "threshold": {"type": float, "default": 0.0, "min": 0.0, "max": 0.1, "label": "Return threshold (fraction, e.g. 0.02 = 2%)"},
        },
    },
    "SMA Cross": {
        "fn":           sma_crossover,
        "indicators":   _sma_indicators,
        "natural_mode": "event",
        "description":  "Long when fast SMA crosses above slow SMA, short on cross below. Buffer > 0 creates a neutral zone — use State entry mode with it.",
        "params": {
            "fast_period": {"type": int,   "default": 10,  "min": 2,   "max": 100, "label": "Fast period"},
            "slow_period": {"type": int,   "default": 50,  "min": 5,   "max": 300, "label": "Slow period"},
            "buffer_pct":  {"type": float, "default": 0.0, "min": 0.0, "max": 0.05, "label": "Buffer zone (e.g. 0.005 = 0.5%)", "widget": "number_input", "step": 0.001, "format": "%.3f"},
        },
    },
    "EMA Cross": {
        "fn":           ema_crossover,
        "indicators":   _ema_indicators,
        "natural_mode": "event",
        "description":  "Like SMA Cross but uses exponential MAs — reacts faster to recent price. Buffer > 0 creates a neutral zone — use State entry mode with it.",
        "params": {
            "fast_period": {"type": int,   "default": 10,  "min": 2,   "max": 100, "label": "Fast period"},
            "slow_period": {"type": int,   "default": 50,  "min": 5,   "max": 300, "label": "Slow period"},
            "buffer_pct":  {"type": float, "default": 0.0, "min": 0.0, "max": 0.05, "label": "Buffer zone (e.g. 0.005 = 0.5%)", "widget": "number_input", "step": 0.001, "format": "%.3f"},
        },
    },
    "Price vs MA": {
        "fn":           price_vs_ma,
        "indicators":   _price_vs_ma_indicators,
        "natural_mode": "state",
        "description":  "Long while price is above the moving average, short while below. Buffer creates a neutral zone around the MA so marginal crossings do not trigger a flip.",
        "params": {
            "period":     {"type": int,   "default": 50,  "min": 5,   "max": 300,  "label": "MA period"},
            "ma_type":    {"type": str,   "default": "SMA", "options": ["SMA", "EMA"], "label": "MA type"},
            "buffer_pct": {"type": float, "default": 0.0, "min": 0.0, "max": 0.05, "label": "Buffer zone (e.g. 0.005 = 0.5%)", "widget": "number_input", "step": 0.001, "format": "%.3f"},
        },
    },
    "MA Slope": {
        "fn":           ma_slope,
        "indicators":   _ma_slope_indicators,
        "natural_mode": "state",
        "description":  "Long while the moving average is sloping up, short while sloping down.",
        "params": {
            "period":          {"type": int,   "default": 20,  "min": 5,  "max": 200, "label": "MA period"},
            "slope_threshold": {"type": float, "default": 0.0, "min": 0.0, "max": 1.0, "label": "Min slope magnitude"},
        },
    },
    "MACD Cross": {
        "fn":           macd_strategy,
        "indicators":   _macd_indicators,
        "natural_mode": "event",
        "description":  "Long when MACD line crosses above signal line, short on cross below.",
        "params": {
            "fast":          {"type": int, "default": 12, "min": 2,  "max": 50,  "label": "Fast EMA"},
            "slow":          {"type": int, "default": 26, "min": 5,  "max": 100, "label": "Slow EMA"},
            "signal_period": {"type": int, "default": 9,  "min": 2,  "max": 30,  "label": "Signal period"},
        },
    },
    "MACD Histogram": {
        "fn":           macd_histogram_strategy,
        "indicators":   _macd_histogram_indicators,
        "natural_mode": "state",
        "description":  "Long while MACD histogram is positive (momentum accelerating upward).",
        "params": {
            "fast":          {"type": int, "default": 12, "min": 2,  "max": 50,  "label": "Fast EMA"},
            "slow":          {"type": int, "default": 26, "min": 5,  "max": 100, "label": "Slow EMA"},
            "signal_period": {"type": int, "default": 9,  "min": 2,  "max": 30,  "label": "Signal period"},
        },
    },
    "Donchian": {
        "fn":           donchian_strategy,
        "indicators":   _donchian_indicators,
        "natural_mode": "event",
        "description":  "Long on N-bar high breakout, short on N-bar low breakout. Buffer filters marginal breakouts that barely exceed the channel edge.",
        "params": {
            "period":     {"type": int,   "default": 20,  "min": 5,   "max": 100,  "label": "Channel period"},
            "buffer_pct": {"type": float, "default": 0.0, "min": 0.0, "max": 0.02, "label": "Buffer zone (e.g. 0.002 = 0.2%)", "widget": "number_input", "step": 0.001, "format": "%.3f"},
        },
    },
    "Turtle Breakout": {
        "fn":           turtle_breakout,
        "indicators":   _turtle_breakout_indicators,
        "natural_mode": "state",
        "description":  "Enter on long-period channel breakout, exit when shorter channel is breached.",
        "params": {
            "entry_period": {"type": int, "default": 20, "min": 5,  "max": 100, "label": "Entry channel"},
            "exit_period":  {"type": int, "default": 10, "min": 2,  "max": 50,  "label": "Exit channel"},
        },
    },
    "ADX + DI": {
        "fn":           adx_strategy,
        "indicators":   _adx_indicators,
        "natural_mode": "event",
        "description":  "+DI/−DI crossover signal, only triggered when ADX > threshold (market is trending).",
        "params": {
            "period":    {"type": int,   "default": 14,   "min": 2,    "max": 50,   "label": "ADX period"},
            "threshold": {"type": float, "default": 25.0, "min": 10.0, "max": 50.0, "label": "Min ADX"},
        },
    },
    "SuperTrend": {
        "fn":           supertrend,
        "indicators":   _supertrend_indicators,
        "natural_mode": "state",
        "description":  "ATR-based trailing band — long above the lower band, short below the upper band.",
        "params": {
            "period":     {"type": int,   "default": 10,  "min": 3,   "max": 50,   "label": "ATR period"},
            "multiplier": {"type": float, "default": 3.0, "min": 0.5, "max": 10.0, "label": "ATR multiplier"},
        },
    },
    "PSAR": {
        "fn":           psar_strategy,
        "indicators":   _psar_indicators,
        "natural_mode": "state",
        "description":  "Parabolic SAR — position flips when price crosses the trailing dot.",
        "params": {
            "step":     {"type": float, "default": 0.02, "min": 0.005, "max": 0.1,  "label": "Step"},
            "max_step": {"type": float, "default": 0.2,  "min": 0.05,  "max": 0.5,  "label": "Max step"},
        },
    },
}


# ---------------------------------------------------------------------------
# Higher-timeframe trend filter
# ---------------------------------------------------------------------------

# Maps each trading interval to the next timeframe up.
# Resampling the existing price data avoids an extra API call.
_HIGHER_TF_RULE: Dict[str, str] = {
    "5m":  "1h",
    "15m": "4h",
    "1h":  "D",
    "4h":  "D",
    "1d":  "W-FRI",
}


def apply_trend_filter(
    signals: pd.Series,
    prices: pd.DataFrame,
    interval: str = "1d",
    ma_period: int = 50,
) -> pd.Series:
    """
    Zero out any signal that opposes the higher-timeframe trend.

    The higher TF is derived by resampling the existing OHLCV data, so no
    extra network request is needed.  Trend direction = price above/below its
    ma_period simple moving average on the higher TF.

    A long signal (1) is kept only when the higher-TF close is above its MA.
    A short signal (-1) is kept only when the higher-TF close is below its MA.
    Flat signals (0) are unchanged.
    If there is not enough data to compute the MA, the signals are returned
    unchanged rather than raising an error.
    """
    rule = _HIGHER_TF_RULE.get(interval)
    if rule is None:
        return signals

    htf_close = prices["Close"].resample(rule).last().dropna()
    if len(htf_close) < ma_period:
        return signals

    ma = htf_close.rolling(ma_period).mean()
    trend = pd.Series(
        np.where(htf_close >= ma, 1, -1),
        index=htf_close.index,
    )

    # Forward-fill higher-TF trend value onto every lower-TF bar
    trend_aligned = trend.reindex(signals.index).ffill()

    filtered = signals.copy()
    filtered[(signals == 1)  & (trend_aligned == -1)] = 0
    filtered[(signals == -1) & (trend_aligned ==  1)] = 0
    return filtered


# ---------------------------------------------------------------------------
# Trend builder — entry / exit / filter helpers
# ---------------------------------------------------------------------------

def _event_to_state(signal: pd.Series) -> pd.Series:
    """Forward-fill event signals — hold direction until an opposite event fires."""
    return signal.replace(0, np.nan).ffill().fillna(0).astype(int)


def _state_to_event(signal: pd.Series) -> pd.Series:
    """Keep only bars where the signal changes direction."""
    prev   = signal.shift(1).fillna(0).astype(int)
    result = signal.copy()
    result[signal == prev] = 0
    return _clean_signal(result)


def apply_entry_logic(
    signal: pd.Series,
    mode: str = "state",
    confirmation_bars: int = 1,
) -> pd.Series:
    """
    Transform a raw signal according to the chosen entry mode.

    state        — hold position while condition holds (forward-fill events).
    event        — enter only on direction transitions (strip held states).
    confirmation — require K consecutive same-direction bars before entry.
    """
    if mode == "state":
        return _event_to_state(signal)
    if mode == "event":
        return _state_to_event(signal)
    if mode == "confirmation":
        if confirmation_bars <= 1:
            return signal
        vals   = signal.values
        n      = len(vals)
        result = np.zeros(n, dtype=int)
        for i in range(confirmation_bars - 1, n):
            window = vals[i - confirmation_bars + 1 : i + 1]
            if np.all(window == 1):
                result[i] = 1
            elif np.all(window == -1):
                result[i] = -1
        return pd.Series(result, index=signal.index)
    return signal


def apply_exit_logic(
    signal: pd.Series,
    prices: pd.DataFrame,
    exit_type: str,
    params: Optional[Dict] = None,
) -> pd.Series:
    """
    Modify signal to encode MA-exit conditions.
    neutral and fixed_bars exits are handled via run_backtest parameters instead.
    """
    if exit_type != "ma_exit":
        return signal
    params    = params or {}
    ma_period = int(params.get("ma_period", 20))
    ma        = prices["Close"].rolling(ma_period).mean()
    result    = signal.copy()
    result[(signal == 1)  & (prices["Close"] < ma)] = 0
    result[(signal == -1) & (prices["Close"] > ma)] = 0
    return result


def apply_signal_filters(
    signal: pd.Series,
    prices: pd.DataFrame,
    filter_config: Optional[Dict] = None,
) -> pd.Series:
    """Zero out signals that fail direction or regime filters."""
    if not filter_config:
        return signal
    result = signal.copy()

    # long_only / short_only: directional filter applied at the backtest entry stage,
    # not here, so that exits on the opposite-direction signal still fire correctly.

    adx_min = filter_config.get("adx_min")
    if adx_min and adx_min > 0:
        adx_period = int(filter_config.get("adx_period", 14))
        adx        = ta.trend.ADXIndicator(
            prices["High"], prices["Low"], prices["Close"], window=adx_period
        ).adx()
        result[adx < adx_min] = 0

    adx_max = filter_config.get("adx_max")
    if adx_max and adx_max > 0:
        adx_period = int(filter_config.get("adx_period", 14))
        adx        = ta.trend.ADXIndicator(
            prices["High"], prices["Low"], prices["Close"], window=adx_period
        ).adx()
        result[adx > adx_max] = 0  # MR: only trade in ranging markets (low ADX)

    vol_min = filter_config.get("vol_min")
    vol_max = filter_config.get("vol_max")
    if vol_min is not None or vol_max is not None:
        ann_vol = prices["Close"].pct_change().rolling(20).std() * np.sqrt(252)
        if vol_min is not None:
            result[ann_vol < vol_min] = 0
        if vol_max is not None:
            result[ann_vol > vol_max] = 0

    return result


def generate_trend_signal(
    prices: pd.DataFrame,
    signal_type: str,
    params: Dict,
) -> pd.Series:
    """Generate a raw signal using TREND_SIGNAL_REGISTRY."""
    return TREND_SIGNAL_REGISTRY[signal_type]["fn"](prices, **params)


def build_trend_indicators(
    prices: pd.DataFrame,
    signal_type: str,
    params: Dict,
) -> list:
    """Return indicator overlay data for the given signal type."""
    reg    = TREND_SIGNAL_REGISTRY.get(signal_type, {})
    ind_fn = reg.get("indicators")
    if ind_fn is None:
        return []
    try:
        return ind_fn(prices, **params)
    except Exception:
        return []


def build_strategy_summary(
    signal_type: str,
    exit_type: str,
    filter_config: Dict,
    risk_config: Dict,
    signal_params: Optional[Dict] = None,
    exit_params: Optional[Dict] = None,
    confirmation_bars: int = 1,
) -> str:
    """Produce a plain-English summary of the configured strategy."""
    signal_params = signal_params or {}
    exit_params   = exit_params   or {}

    param_str = ", ".join(f"{k}={v}" for k, v in signal_params.items()) if signal_params else "default"

    entry_desc = (
        "Enter immediately on signal"
        if confirmation_bars <= 1
        else f"Enter after {confirmation_bars} consecutive confirming bars"
    )

    exit_desc = {
        "signal":     "Exit on signal reversal",
        "fixed_bars": f"Exit after {exit_params.get('max_bars', 20)} bars",
    }.get(exit_type, exit_type)

    filters = []
    if filter_config.get("long_only"):    filters.append("Long only")
    if filter_config.get("short_only"):   filters.append("Short only")
    if filter_config.get("adx_min"):      filters.append(f"ADX > {filter_config['adx_min']}")
    if filter_config.get("trend_filter"): filters.append("Higher-TF trend filter")

    risk_parts = []
    if risk_config.get("commission_pct", 0) > 0:
        risk_parts.append(f"commission {risk_config['commission_pct'] * 100:.2f}%")
    if risk_config.get("slippage_pct", 0) > 0:
        risk_parts.append(f"slippage {risk_config['slippage_pct'] * 100:.2f}%")
    risk_parts.append(
        f"vol target {risk_config['vol_target'] * 100:.0f}%/yr"
        if risk_config.get("vol_target")
        else "risk 2%/trade (volatility-sized SL)"
    )

    return "\n".join([
        f"Signal:  {signal_type} ({param_str})",
        f"Entry:   {entry_desc}",
        f"Exit:    {exit_desc} + SL/TP",
        f"Filters: {', '.join(filters) if filters else 'None'}",
        f"Risk:    {', '.join(risk_parts)}",
    ])


# ---------------------------------------------------------------------------
# Mean Reversion builder — signal generators
# ---------------------------------------------------------------------------

def zscore_mr_builder(
    df: pd.DataFrame,
    lookback: int = 20,
    entry_threshold: float = 2.0,
    exit_threshold: float = 0.5,
) -> pd.Series:
    """
    Z-Score mean reversion with both entry and exit thresholds.
    State machine: enters when z is extreme, exits when z reverts past exit_threshold.
    exit_threshold=0 means exit at the mean; exit_threshold<entry means partial reversion.
    """
    close = df["Close"]
    z     = (close - close.rolling(lookback).mean()) / close.rolling(lookback).std()
    z_arr = z.values
    n     = len(z_arr)
    sig   = np.zeros(n, dtype=np.int8)
    pos   = 0

    for i in range(1, n):
        v = z_arr[i]
        if np.isnan(v):
            continue
        if pos == 0:
            if v < -entry_threshold:
                pos = 1
            elif v > entry_threshold:
                pos = -1
        elif pos == 1:
            if v > -exit_threshold:
                pos = 0
        else:
            if v < exit_threshold:
                pos = 0
        sig[i] = pos

    return _clean_signal(pd.Series(sig, index=df.index))


def short_term_reversal(
    df: pd.DataFrame,
    lookback: int = 5,
    threshold: float = 0.02,
) -> pd.Series:
    """
    Contrarian signal — fades recent price moves.
    Long after a sharp N-bar drop, short after a sharp N-bar rise.
    State-based: persists while the N-bar return remains extreme.
    """
    ret = df["Close"].pct_change(lookback)
    sig = pd.Series(0, index=df.index, dtype=int)
    sig[ret < -threshold] = 1
    sig[ret >  threshold] = -1
    return _clean_signal(sig)


def ma_deviation(
    df: pd.DataFrame,
    period: int = 20,
    ma_type: str = "SMA",
    threshold: float = 0.02,
) -> pd.Series:
    """
    State signal — long while price is more than threshold% below its MA,
    short while more than threshold% above.
    """
    ma = (
        df["Close"].ewm(span=period, adjust=False).mean()
        if ma_type == "EMA"
        else df["Close"].rolling(period).mean()
    )
    dev = (df["Close"] - ma) / ma
    sig = pd.Series(0, index=df.index, dtype=int)
    sig[dev < -threshold] = 1
    sig[dev >  threshold] = -1
    return _clean_signal(sig)


def range_reversion(
    df: pd.DataFrame,
    lookback: int = 20,
    threshold: float = 0.2,
) -> pd.Series:
    """
    State signal — long when price is in the bottom X% of its rolling range,
    short when in the top X%.
    threshold: 0.2 = bottom/top 20% of range triggers a signal.
    """
    high    = df["High"].rolling(lookback).max()
    low     = df["Low"].rolling(lookback).min()
    rng     = (high - low).replace(0, np.nan)
    rng_pct = (df["Close"] - low) / rng
    sig     = pd.Series(0, index=df.index, dtype=int)
    sig[rng_pct <  threshold]       = 1
    sig[rng_pct > (1 - threshold)]  = -1
    return _clean_signal(sig)


# ---------------------------------------------------------------------------
# Mean Reversion builder — indicator overlay builders
# ---------------------------------------------------------------------------

def _zscore_mr_indicators(
    df: pd.DataFrame,
    lookback: int = 20,
    entry_threshold: float = 2.0,
    exit_threshold: float = 0.5,
) -> list:
    close = df["Close"]
    z     = (close - close.rolling(lookback).mean()) / close.rolling(lookback).std()
    n     = len(df)
    return [{"panel": "oscillator", "yaxis_title": "Z-Score", "traces": [
        go.Scatter(x=df.index, y=z, name=f"Z-Score({lookback})", line=dict(color="#a78bfa", width=1.5)),
        go.Scatter(x=df.index, y=[ entry_threshold] * n, name=f"Entry +{entry_threshold}σ",
                   line=dict(color="#ef4444", width=1,   dash="dash"), showlegend=False),
        go.Scatter(x=df.index, y=[-entry_threshold] * n, name=f"Entry -{entry_threshold}σ",
                   line=dict(color="#22c55e", width=1,   dash="dash"), showlegend=False),
        go.Scatter(x=df.index, y=[ exit_threshold]  * n, name=f"Exit +{exit_threshold}σ",
                   line=dict(color="#ef4444", width=0.8, dash="dot"),  showlegend=False),
        go.Scatter(x=df.index, y=[-exit_threshold]  * n, name=f"Exit -{exit_threshold}σ",
                   line=dict(color="#22c55e", width=0.8, dash="dot"),  showlegend=False),
        go.Scatter(x=df.index, y=[0] * n, name="Zero",
                   line=dict(color="#94a3b8", width=0.8, dash="dot"),  showlegend=False),
    ]}]


def _str_indicators(df: pd.DataFrame, lookback: int = 5, threshold: float = 0.02) -> list:
    ret = df["Close"].pct_change(lookback) * 100
    thr = threshold * 100
    n   = len(df)
    return [{"panel": "oscillator", "yaxis_title": f"Return({lookback}b) %", "traces": [
        go.Scatter(x=df.index, y=ret, name=f"Return({lookback}b)", line=dict(color="#60a5fa", width=1.5)),
        go.Scatter(x=df.index, y=[ thr] * n, name=f"+{thr:.1f}%",
                   line=dict(color="#ef4444", width=1, dash="dash"), showlegend=False),
        go.Scatter(x=df.index, y=[-thr] * n, name=f"-{thr:.1f}%",
                   line=dict(color="#22c55e", width=1, dash="dash"), showlegend=False),
        go.Scatter(x=df.index, y=[0] * n, name="Zero",
                   line=dict(color="#94a3b8", width=0.8, dash="dot"), showlegend=False),
    ]}]


def _ma_deviation_indicators(
    df: pd.DataFrame, period: int = 20, ma_type: str = "SMA", threshold: float = 0.02,
) -> list:
    ma  = (
        df["Close"].ewm(span=period, adjust=False).mean()
        if ma_type == "EMA"
        else df["Close"].rolling(period).mean()
    )
    dev = (df["Close"] - ma) / ma * 100
    thr = threshold * 100
    n   = len(df)
    return [
        {"panel": "price", "traces": [
            go.Scatter(x=df.index, y=ma, name=f"{ma_type}({period})", line=dict(color="#f59e0b", width=1.5)),
        ]},
        {"panel": "oscillator", "yaxis_title": "Deviation %", "traces": [
            go.Scatter(x=df.index, y=dev, name="Deviation %", line=dict(color="#a78bfa", width=1.5)),
            go.Scatter(x=df.index, y=[ thr] * n, name=f"+{thr:.1f}%",
                       line=dict(color="#ef4444", width=1,   dash="dash"), showlegend=False),
            go.Scatter(x=df.index, y=[-thr] * n, name=f"-{thr:.1f}%",
                       line=dict(color="#22c55e", width=1,   dash="dash"), showlegend=False),
            go.Scatter(x=df.index, y=[0] * n, name="Zero",
                       line=dict(color="#94a3b8", width=0.8, dash="dot"), showlegend=False),
        ]},
    ]


def _range_indicators(df: pd.DataFrame, lookback: int = 20, threshold: float = 0.2) -> list:
    high    = df["High"].rolling(lookback).max()
    low     = df["Low"].rolling(lookback).min()
    rng     = (high - low).replace(0, np.nan)
    rng_pct = ((df["Close"] - low) / rng) * 100
    top     = (1 - threshold) * 100
    bot     = threshold * 100
    n       = len(df)
    return [
        {"panel": "price", "traces": [
            go.Scatter(x=df.index, y=high, name=f"Range Hi ({lookback})",
                       line=dict(color="rgba(96,165,250,0.7)", width=1)),
            go.Scatter(x=df.index, y=low, name=f"Range Lo ({lookback})",
                       line=dict(color="rgba(96,165,250,0.7)", width=1)),
        ]},
        {"panel": "oscillator", "yaxis_title": "Range %", "yaxis_range": [0, 100], "traces": [
            go.Scatter(x=df.index, y=rng_pct, name="Range %", line=dict(color="#a78bfa", width=1.5)),
            go.Scatter(x=df.index, y=[top] * n, name=f"Upper ({top:.0f}%)",
                       line=dict(color="#ef4444", width=1, dash="dash"), showlegend=False),
            go.Scatter(x=df.index, y=[bot] * n, name=f"Lower ({bot:.0f}%)",
                       line=dict(color="#22c55e", width=1, dash="dash"), showlegend=False),
        ]},
    ]


# ---------------------------------------------------------------------------
# Mean Reversion builder registry
# ---------------------------------------------------------------------------

MEAN_REVERSION_SIGNAL_REGISTRY: Dict[str, Dict] = {
    "Z-Score": {
        "fn":           zscore_mr_builder,
        "indicators":   _zscore_mr_indicators,
        "natural_mode": "state",
        "description":  (
            "Long when price falls more than entry_threshold standard deviations below its "
            "rolling mean; exits when z-score reverts past exit_threshold. "
            "Best all-round mean-reversion signal — fully configurable entry and exit."
        ),
        "params": {
            "lookback":         {"type": int,   "default": 20,  "min": 5,   "max": 200, "label": "Lookback"},
            "entry_threshold":  {"type": float, "default": 2.0, "min": 0.5, "max": 4.0, "label": "Entry threshold (σ)"},
            "exit_threshold":   {"type": float, "default": 0.5, "min": 0.0, "max": 2.0, "label": "Exit threshold (σ)"},
        },
    },
    "Bollinger Bands": {
        "fn":           bollinger_strategy,
        "indicators":   _bollinger_indicators,
        "natural_mode": "event",
        "description":  (
            "Long when price touches or crosses the lower Bollinger Band, "
            "short when it touches the upper band. Event-based — fires only on the touch bar."
        ),
        "params": {
            "period":  {"type": int,   "default": 20,  "min": 5,   "max": 100, "label": "Period"},
            "std_dev": {"type": float, "default": 2.0, "min": 0.5, "max": 4.0, "label": "Std devs"},
        },
    },
    "RSI": {
        "fn":           rsi_strategy,
        "indicators":   _rsi_indicators,
        "natural_mode": "event",
        "description":  (
            "Long when RSI crosses back above the oversold level (reversal confirmation), "
            "short when it crosses below overbought. "
            "Event-based — fires only on the crossover bar."
        ),
        "params": {
            "period":     {"type": int, "default": 14, "min": 2,  "max": 100, "label": "RSI period"},
            "oversold":   {"type": int, "default": 30, "min": 10, "max": 45,  "label": "Oversold level"},
            "overbought": {"type": int, "default": 70, "min": 55, "max": 90,  "label": "Overbought level"},
        },
    },
    "Short-Term Reversal": {
        "fn":           short_term_reversal,
        "indicators":   _str_indicators,
        "natural_mode": "state",
        "description":  (
            "Contrarian signal — fades recent price moves. "
            "Long after a sharp N-bar drop, short after a sharp N-bar rise. "
            "State-based: holds while the return remains extreme."
        ),
        "params": {
            "lookback":  {"type": int,   "default": 5,    "min": 1,   "max": 60,  "label": "Lookback (bars)"},
            "threshold": {"type": float, "default": 0.02, "min": 0.0, "max": 0.2, "label": "Minimum move (fraction, e.g. 0.02 = 2%)"},
        },
    },
    "MA Deviation": {
        "fn":           ma_deviation,
        "indicators":   _ma_deviation_indicators,
        "natural_mode": "state",
        "description":  (
            "Long while price is significantly below its moving average (deviation < −threshold), "
            "short while significantly above. Tracks the strength of the deviation continuously."
        ),
        "params": {
            "period":    {"type": int,   "default": 20,    "min": 5,    "max": 200,  "label": "MA period"},
            "ma_type":   {"type": str,   "default": "SMA", "options": ["SMA", "EMA"], "label": "MA type"},
            "threshold": {"type": float, "default": 0.02,  "min": 0.001, "max": 0.2, "label": "Deviation threshold (fraction)"},
        },
    },
    "Range Reversion": {
        "fn":           range_reversion,
        "indicators":   _range_indicators,
        "natural_mode": "state",
        "description":  (
            "Buys when price is in the bottom X% of its rolling range, "
            "sells when near the top. "
            "Effective in sideways, range-bound markets."
        ),
        "params": {
            "lookback":  {"type": int,   "default": 20,  "min": 5,    "max": 100,  "label": "Range lookback"},
            "threshold": {"type": float, "default": 0.2, "min": 0.05, "max": 0.45, "label": "Range band (0–0.5, e.g. 0.2 = bottom/top 20%)"},
        },
    },
}


# ---------------------------------------------------------------------------
# Mean Reversion builder — helpers
# ---------------------------------------------------------------------------

def apply_mr_reversal_confirmation(
    signal: pd.Series,
    indicator: pd.Series,
) -> pd.Series:
    """
    Filter entries to fire only after the primary indicator starts reverting from extreme.
    Long: requires indicator to be increasing (recovering from oversold extreme).
    Short: requires indicator to be decreasing (recovering from overbought extreme).
    """
    ind_diff  = indicator.diff()
    result    = signal.copy()
    result[(signal == 1)  & (ind_diff <= 0)] = 0
    result[(signal == -1) & (ind_diff >= 0)] = 0
    return result


def get_mr_indicator_series(
    prices: pd.DataFrame,
    signal_type: str,
    params: Dict,
) -> pd.Series:
    """Return the primary continuous indicator series used for reversal confirmation."""
    close = prices["Close"]
    if signal_type == "Z-Score":
        lb = params.get("lookback", 20)
        return (close - close.rolling(lb).mean()) / close.rolling(lb).std()
    if signal_type == "RSI":
        return ta.momentum.RSIIndicator(close, window=params.get("period", 14)).rsi()
    if signal_type == "Bollinger Bands":
        bb  = ta.volatility.BollingerBands(close, window=params.get("period", 20),
                                            window_dev=params.get("std_dev", 2.0))
        mid = bb.bollinger_mavg()
        return (close - mid) / mid.replace(0, np.nan)
    if signal_type == "Short-Term Reversal":
        return close.pct_change(params.get("lookback", 5))
    if signal_type == "MA Deviation":
        ma_type = params.get("ma_type", "SMA")
        ma = (
            close.ewm(span=params.get("period", 20), adjust=False).mean()
            if ma_type == "EMA"
            else close.rolling(params.get("period", 20)).mean()
        )
        return (close - ma) / ma.replace(0, np.nan)
    if signal_type == "Range Reversion":
        lb   = params.get("lookback", 20)
        high = prices["High"].rolling(lb).max()
        low  = prices["Low"].rolling(lb).min()
        rng  = (high - low).replace(0, np.nan)
        return (close - low) / rng
    return pd.Series(0.0, index=prices.index)


def generate_mr_signal(
    prices: pd.DataFrame,
    signal_type: str,
    params: Dict,
) -> pd.Series:
    """Generate a raw signal using MEAN_REVERSION_SIGNAL_REGISTRY."""
    return MEAN_REVERSION_SIGNAL_REGISTRY[signal_type]["fn"](prices, **params)


def build_mr_indicators(
    prices: pd.DataFrame,
    signal_type: str,
    params: Dict,
) -> list:
    """Return indicator overlay data for the given MR signal type."""
    reg    = MEAN_REVERSION_SIGNAL_REGISTRY.get(signal_type, {})
    ind_fn = reg.get("indicators")
    if ind_fn is None:
        return []
    try:
        return ind_fn(prices, **params)
    except Exception:
        return []


def build_mr_strategy_summary(
    signal_type: str,
    exit_type: str,
    filter_config: Dict,
    risk_config: Dict,
    signal_params: Optional[Dict] = None,
    exit_params: Optional[Dict] = None,
    confirmation_bars: int = 1,
    wait_for_reversal: bool = False,
) -> str:
    """Produce a plain-English prose summary of the configured MR strategy."""
    signal_params = signal_params or {}
    exit_params   = exit_params   or {}

    # ── Signal description ──────────────────────────────────────────────────
    if signal_type == "Z-Score":
        lb  = signal_params.get("lookback", 20)
        en  = signal_params.get("entry_threshold", 2.0)
        ex  = signal_params.get("exit_threshold", 0.5)
        sig_line = (
            f"Z-Score on a {lb}-bar window. "
            f"Enters long when z < −{en}σ and short when z > +{en}σ. "
            f"Exits when z reverts past ±{ex}σ."
        )
    elif signal_type == "Bollinger Bands":
        p  = signal_params.get("period", 20)
        sd = signal_params.get("std_dev", 2.0)
        sig_line = f"Bollinger Bands ({p} bars, {sd}σ). Enters on band touches."
    elif signal_type == "RSI":
        p   = signal_params.get("period", 14)
        os_ = signal_params.get("oversold", 30)
        ob  = signal_params.get("overbought", 70)
        sig_line = f"RSI({p}). Long when RSI crosses above {os_}, short when it crosses below {ob}."
    elif signal_type == "Short-Term Reversal":
        lb  = signal_params.get("lookback", 5)
        thr = signal_params.get("threshold", 0.02) * 100
        sig_line = f"Short-Term Reversal: fades {lb}-bar returns exceeding ±{thr:.1f}%."
    elif signal_type == "MA Deviation":
        p   = signal_params.get("period", 20)
        mt  = signal_params.get("ma_type", "SMA")
        thr = signal_params.get("threshold", 0.02) * 100
        sig_line = f"MA Deviation: trades when price deviates more than {thr:.1f}% from {mt}({p})."
    elif signal_type == "Range Reversion":
        lb  = signal_params.get("lookback", 20)
        thr = signal_params.get("threshold", 0.2) * 100
        sig_line = f"Range Reversion ({lb} bars): enters in the bottom/top {thr:.0f}% of the range."
    else:
        sig_line = signal_type

    # ── Entry description ───────────────────────────────────────────────────
    entry_parts = []
    if confirmation_bars > 1:
        entry_parts.append(f"requires {confirmation_bars} consecutive confirming bars")
    if wait_for_reversal:
        entry_parts.append("waits for indicator to start reversing")
    entry_line = "Entry: " + ("; ".join(entry_parts) if entry_parts else "enters immediately on signal") + "."

    # ── Exit description ────────────────────────────────────────────────────
    exit_map = {
        "mean":        "exits when signal reverts to neutral (mean-reversion complete)",
        "opposite":    "exits on a signal reversal",
        "fixed_bars":  f"exits after {exit_params.get('max_bars', 20)} bars",
    }
    exit_line = f"Exit: {exit_map.get(exit_type, exit_type)}. SL/TP (volatility-sized) always active."

    # ── Filters ─────────────────────────────────────────────────────────────
    filter_parts = []
    if filter_config.get("adx_max"):
        filter_parts.append(f"ADX must be below {filter_config['adx_max']} (ranging market required)")
    if filter_config.get("long_only"):
        filter_parts.append("long trades only")
    if filter_config.get("short_only"):
        filter_parts.append("short trades only")
    if filter_config.get("vol_max"):
        filter_parts.append(f"annualised vol below {filter_config['vol_max']*100:.0f}%")
    filter_line = ("Filters: " + "; ".join(filter_parts) + ".") if filter_parts else "Filters: none."

    # ── Risk ─────────────────────────────────────────────────────────────────
    risk_parts = []
    if risk_config.get("commission_pct", 0) > 0:
        risk_parts.append(f"commission {risk_config['commission_pct']*100:.2f}%")
    if risk_config.get("slippage_pct", 0) > 0:
        risk_parts.append(f"slippage {risk_config['slippage_pct']*100:.2f}%")
    risk_parts.append(
        f"vol target {risk_config['vol_target']*100:.0f}%/yr"
        if risk_config.get("vol_target")
        else "risk 2%/trade (volatility-sized SL)"
    )
    risk_line = f"Risk: {', '.join(risk_parts)}."

    return "\n".join([sig_line, entry_line, exit_line, filter_line, risk_line])


# ---------------------------------------------------------------------------
# MR signal sanity-check / diagnostic helper
# ---------------------------------------------------------------------------

def debug_mr_signal(
    prices: pd.DataFrame,
    signal_type: str,
    params: Dict,
    n_rows: int = 50,
) -> pd.DataFrame:
    """
    Return first n_rows non-zero signal bars with diagnostic columns.

    Use this to verify:
    - Long signals (signal=+1) appear when price is BELOW the rolling mean
    - Short signals (signal=-1) appear when price is ABOVE the rolling mean
    - Signal 0s appear when z-score is between the entry/exit thresholds (reversion complete)

    Example usage:
        debug_mr_signal(prices, "Z-Score", {"lookback": 20, "entry_threshold": 2.0, "exit_threshold": 0.5})
    """
    close  = prices["Close"]
    lb     = params.get("lookback", 20)
    rm     = close.rolling(lb).mean()
    rs     = close.rolling(lb).std()
    z      = (close - rm) / rs

    raw    = generate_mr_signal(prices, signal_type, params)

    diag = pd.DataFrame({
        "Close":        close,
        "RollingMean":  rm,
        "RollingStd":   rs,
        "Z":            z.round(3),
        "Signal":       raw,
        "PrevSignal":   raw.shift(1).fillna(0).astype(int),
        "AboveMean":    (close > rm).astype(int),  # 1=above, 0=below
    })
    diag["Direction OK"] = (
        ((diag["Signal"] == 1)  & (diag["AboveMean"] == 0)) |  # long when below mean ✓
        ((diag["Signal"] == -1) & (diag["AboveMean"] == 1)) |  # short when above mean ✓
        (diag["Signal"] == 0)
    )
    return diag[diag["Signal"] != 0].head(n_rows)


# ---------------------------------------------------------------------------
# Part D — Price Action / Candlestick patterns
# ---------------------------------------------------------------------------

def engulfing_pattern(df: pd.DataFrame) -> pd.Series:
    """
    Bullish/bearish engulfing.
    Bullish: current bullish bar body fully engulfs previous bearish bar body.
    Bearish: mirror image.
    """
    o, c   = df["Open"], df["Close"]
    po, pc = o.shift(1), c.shift(1)
    bull   = (pc < po) & (c > o) & (o <= pc) & (c >= po)
    bear   = (pc > po) & (c < o) & (o >= pc) & (c <= po)
    signal = pd.Series(0, index=df.index, dtype=int)
    signal[bull] = 1
    signal[bear] = -1
    return _clean_signal(signal)


def pin_bar(df: pd.DataFrame, wick_ratio: float = 2.5) -> pd.Series:
    """
    Hammer (bullish) / Shooting Star (bearish).
    Requires: long wick ≥ wick_ratio × body, small body ≤ 35% of total range,
    and the prominent wick at least 2× the opposite wick.
    """
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    body      = (c - o).abs().clip(lower=1e-10)
    low_wick  = pd.concat([o, c], axis=1).min(axis=1) - l
    high_wick = h - pd.concat([o, c], axis=1).max(axis=1)
    total     = (h - l).clip(lower=1e-10)
    body_frac = body / total
    bull_pin  = (body_frac <= 0.35) & (low_wick  >= wick_ratio * body) & (low_wick  >= 2 * high_wick)
    bear_pin  = (body_frac <= 0.35) & (high_wick >= wick_ratio * body) & (high_wick >= 2 * low_wick)
    signal    = pd.Series(0, index=df.index, dtype=int)
    signal[bull_pin] = 1
    signal[bear_pin] = -1
    return _clean_signal(signal)


def inside_bar(df: pd.DataFrame) -> pd.Series:
    """
    Inside bar: current bar's high/low fully contained within the previous bar's range.
    Signal direction follows the mother (containing) bar.
    """
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    is_inside   = (h < h.shift(1)) & (l > l.shift(1))
    mother_bull = c.shift(1) > o.shift(1)
    signal      = pd.Series(0, index=df.index, dtype=int)
    signal[is_inside &  mother_bull] = 1
    signal[is_inside & ~mother_bull] = -1
    return _clean_signal(signal)


def opening_range_breakout(df: pd.DataFrame, range_bars: int = 6) -> pd.Series:
    """
    Session opening range breakout (intraday only).
    Fires +1 on the first bar closing above the session's opening range high,
    -1 on the first bar closing below the opening range low.
    Returns all zeros on daily data (detected when each bar is on a unique date).
    """
    signal = pd.Series(0, index=df.index, dtype=int)
    if not isinstance(df.index, pd.DatetimeIndex):
        return signal

    dates = df.index.normalize()
    if dates.nunique() >= len(df) * 0.9:
        return signal

    close, high, low = df["Close"], df["High"], df["Low"]

    for date_val in dates.unique():
        locs = np.where(dates == date_val)[0]
        if len(locs) <= range_bars:
            continue
        rng_h = high.iloc[locs[:range_bars]].max()
        rng_l = low.iloc[locs[:range_bars]].min()
        if rng_h <= rng_l:
            continue
        trade_locs = locs[range_bars:]
        bull = (close.iloc[trade_locs] > rng_h).values
        if bull.any():
            signal.iloc[trade_locs[bull.argmax()]] = 1
        bear = (close.iloc[trade_locs] < rng_l).values
        if bear.any():
            signal.iloc[trade_locs[bear.argmax()]] = -1

    return _clean_signal(signal)


# Indicator helpers — price action patterns are visible directly on the candle chart
def _engulfing_indicators(df: pd.DataFrame, **kwargs) -> list: return []
def _pin_bar_indicators(df: pd.DataFrame, **kwargs)    -> list: return []
def _inside_bar_indicators(df: pd.DataFrame, **kwargs) -> list: return []
def _orb_indicators(df: pd.DataFrame, **kwargs)        -> list: return []


# ---------------------------------------------------------------------------
# Price Action signal registry
# ---------------------------------------------------------------------------

PRICE_ACTION_SIGNAL_REGISTRY: Dict[str, Dict] = {
    "Engulfing": {
        "fn":           engulfing_pattern,
        "indicators":   _engulfing_indicators,
        "natural_mode": "event",
        "description":  (
            "Bullish: a bullish candle body that fully engulfs the previous bearish candle body — "
            "signals potential reversal of a downtrend. Bearish is the mirror image. "
            "One of the most widely studied price action reversals."
        ),
        "params": {},
    },
    "Pin Bar": {
        "fn":           pin_bar,
        "indicators":   _pin_bar_indicators,
        "natural_mode": "event",
        "description":  (
            "Hammer (bullish) / Shooting Star (bearish). "
            "A bar with a long wick and small body — signals rejection of a price level "
            "and potential reversal. Wick ratio controls how pronounced the wick must be."
        ),
        "params": {
            "wick_ratio": {
                "type": float, "default": 2.5, "min": 1.5, "max": 6.0,
                "label": "Min wick : body ratio",
                "widget": "number_input", "step": 0.5, "format": "%.1f",
            },
        },
    },
    "Inside Bar": {
        "fn":           inside_bar,
        "indicators":   _inside_bar_indicators,
        "natural_mode": "event",
        "description":  (
            "A bar whose high/low is completely contained within the prior bar's range — "
            "signals consolidation and indecision. "
            "Fires in the direction of the mother (containing) bar, anticipating a continuation breakout."
        ),
        "params": {},
    },
    "Opening Range Breakout": {
        "fn":           opening_range_breakout,
        "indicators":   _orb_indicators,
        "natural_mode": "event",
        "description":  (
            "Fires long on the first bar that closes above the session's opening range high, "
            "short below the opening range low. "
            "Only one signal per direction per session. "
            "Requires intraday data — returns no signals on daily bars."
        ),
        "params": {
            "range_bars": {
                "type": int, "default": 6, "min": 1, "max": 48,
                "label": "Opening range (bars)",
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Price Action builder — helpers
# ---------------------------------------------------------------------------

def generate_pa_signal(
    prices: pd.DataFrame,
    signal_type: str,
    params: Dict,
) -> pd.Series:
    """Generate a raw signal using PRICE_ACTION_SIGNAL_REGISTRY."""
    return PRICE_ACTION_SIGNAL_REGISTRY[signal_type]["fn"](prices, **params)


def build_pa_indicators(
    prices: pd.DataFrame,
    signal_type: str,
    params: Dict,
) -> list:
    """Return indicator overlay data for the given price action signal type."""
    reg    = PRICE_ACTION_SIGNAL_REGISTRY.get(signal_type, {})
    ind_fn = reg.get("indicators")
    if ind_fn is None:
        return []
    try:
        return ind_fn(prices, **params)
    except Exception:
        return []


def build_pa_strategy_summary(
    signal_type: str,
    exit_type: str,
    filter_config: Dict,
    risk_config: Dict,
    signal_params: Optional[Dict] = None,
    exit_params: Optional[Dict] = None,
    confirmation_bars: int = 1,
) -> str:
    """Produce a plain-English prose summary of the configured price action strategy."""
    signal_params = signal_params or {}
    exit_params   = exit_params   or {}

    # ── Signal description ──────────────────────────────────────────────────
    if signal_type == "Pin Bar":
        wr       = signal_params.get("wick_ratio", 2.5)
        sig_line = f"Pin Bar (wick:body ≥ {wr:.1f}×). Long on hammers, short on shooting stars."
    elif signal_type == "Engulfing":
        sig_line = "Engulfing pattern. Long on bullish engulfing bars, short on bearish engulfing bars."
    elif signal_type == "Inside Bar":
        sig_line = "Inside Bar. Enters in the direction of the mother (containing) bar."
    elif signal_type == "Opening Range Breakout":
        rb       = signal_params.get("range_bars", 6)
        sig_line = f"Opening Range Breakout ({rb}-bar range). Long on range-high break, short on range-low break."
    else:
        sig_line = signal_type

    # ── Entry description ───────────────────────────────────────────────────
    entry_line = "Entry: " + (
        f"after {confirmation_bars} consecutive confirming bars."
        if confirmation_bars > 1
        else "enters immediately on signal."
    )

    # ── Exit description ────────────────────────────────────────────────────
    exit_map = {
        "signal":     "exits on signal reversal",
        "fixed_bars": f"exits after {exit_params.get('max_bars', 20)} bars",
    }
    exit_line = f"Exit: {exit_map.get(exit_type, exit_type)}."

    # ── Filters ─────────────────────────────────────────────────────────────
    filter_parts = []
    if filter_config.get("long_only"):  filter_parts.append("long trades only")
    if filter_config.get("short_only"): filter_parts.append("short trades only")
    filter_line = ("Filters: " + "; ".join(filter_parts) + ".") if filter_parts else "Filters: none."

    # ── Risk ─────────────────────────────────────────────────────────────────
    risk_parts = []
    if risk_config.get("commission_pct", 0) > 0:
        risk_parts.append(f"commission {risk_config['commission_pct']*100:.2f}%")
    if risk_config.get("slippage_pct", 0) > 0:
        risk_parts.append(f"slippage {risk_config['slippage_pct']*100:.2f}%")
    risk_parts.append(
        f"vol target {risk_config['vol_target']*100:.0f}%/yr"
        if risk_config.get("vol_target")
        else "risk 2%/trade (volatility-sized SL)"
    )
    risk_line = f"Risk: {', '.join(risk_parts)}."

    return "\n".join([sig_line, entry_line, exit_line, filter_line, risk_line])
