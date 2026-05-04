"""
backtest.py — Backtesting pipeline: converts signals to returns and metrics.

Imports: utils.py (calculate_returns, annualisation_factor).
Exports: run_backtest, parameter_sweep.
"""

import itertools
import numpy as np
import pandas as pd
from typing import Callable, Dict, List, Optional, Any
from utils import calculate_returns, annualisation_factor

TRADING_DAYS_PER_YEAR = 252

# Per-interval SL bounds (min, max) as a fraction of price
_SL_BOUNDS: Dict[str, tuple] = {
    "1d":  (0.005, 0.10),
    "1h":  (0.002, 0.04),
    "4h":  (0.003, 0.06),
    "15m": (0.001, 0.01),
    "5m":  (0.0005, 0.005),
}

# RiskMetrics EWMA decay factors per timeframe
_EWMA_LAMBDA: Dict[str, float] = {
    "1d":  0.94,
    "4h":  0.97,
    "1h":  0.99,
    "15m": 0.999,
    "5m":  0.9995,
}


def _rolling_std_vol(close_arr: np.ndarray, entry_iloc: int, interval: str) -> float:
    """Standard deviation of last 20 bar-to-bar returns, clamped to bounds."""
    min_sl, max_sl = _SL_BOUNDS.get(interval, (0.005, 0.10))
    window = min(20, entry_iloc)
    if window < 2:
        return min_sl
    sl = close_arr[max(0, entry_iloc - window):entry_iloc]
    if len(sl) < 2:
        return min_sl
    pct = np.diff(sl) / sl[:-1]
    if len(pct) < 2:
        return min_sl
    v = float(np.nanstd(pct, ddof=1))
    return float(np.clip(v if not np.isnan(v) else min_sl, min_sl, max_sl))


def _atr_vol(
    close_arr: np.ndarray,
    high_arr: np.ndarray,
    low_arr: np.ndarray,
    entry_iloc: int,
    interval: str,
) -> float:
    """ATR / entry_price as SL distance — captures intraday wicks and gaps."""
    min_sl, max_sl = _SL_BOUNDS.get(interval, (0.005, 0.10))
    window = min(20, entry_iloc)
    if window < 2:
        return min_sl
    start = max(0, entry_iloc - window)
    h = high_arr[start:entry_iloc]
    l = low_arr[start:entry_iloc]
    # prev close for each bar in the window
    if start > 0:
        c_prev = close_arr[start - 1:entry_iloc - 1]
    else:
        c_prev = np.concatenate([[close_arr[0]], close_arr[0:entry_iloc - 1]])
    if len(h) == 0 or len(c_prev) != len(h):
        return min_sl
    tr  = np.maximum(h - l, np.maximum(np.abs(h - c_prev), np.abs(l - c_prev)))
    atr = float(np.mean(tr))
    entry_price = float(close_arr[entry_iloc - 1]) if entry_iloc > 0 else 1.0
    v = atr / entry_price if entry_price > 0 else min_sl
    return float(np.clip(v, min_sl, max_sl))


def _ewma_vol(close_arr: np.ndarray, entry_iloc: int, interval: str) -> float:
    """EWMA volatility using RiskMetrics decay factor, clamped to bounds."""
    min_sl, max_sl = _SL_BOUNDS.get(interval, (0.005, 0.10))
    lam = _EWMA_LAMBDA.get(interval, 0.94)
    window = min(20, entry_iloc)
    if window < 2:
        return min_sl
    sl = close_arr[max(0, entry_iloc - window):entry_iloc]
    if len(sl) < 2:
        return min_sl
    pct = np.diff(sl) / sl[:-1]
    if len(pct) < 1:
        return min_sl
    var = float(pct[0] ** 2)
    for r in pct[1:]:
        var = lam * var + (1.0 - lam) * float(r ** 2)
    v = float(np.sqrt(var)) if var >= 0 else min_sl
    return float(np.clip(v if not np.isnan(v) else min_sl, min_sl, max_sl))


def _vol_to_sl_pct_fast(
    close_arr: np.ndarray,
    entry_iloc: int,
    interval: str = "1d",
    vol_method: str = "Rolling Std",
    high_arr: Optional[np.ndarray] = None,
    low_arr: Optional[np.ndarray] = None,
) -> float:
    """Dispatch to the chosen volatility method and return SL distance fraction."""
    if vol_method == "ATR" and high_arr is not None and low_arr is not None:
        return _atr_vol(close_arr, high_arr, low_arr, entry_iloc, interval)
    if vol_method == "EWMA":
        return _ewma_vol(close_arr, entry_iloc, interval)
    return _rolling_std_vol(close_arr, entry_iloc, interval)


def _record_mae_mfe(
    trade_entry: Dict,
    direction: int,
    trade_min_low: float,
    trade_max_high: float,
) -> None:
    """Compute MAE/MFE for a closed trade and write into the trade_entry dict in-place."""
    entry_px = trade_entry.get("Entry Price", 0.0)
    if entry_px and entry_px > 0:
        if direction == 1:  # Long: adverse = price fell, favourable = price rose
            trade_entry["MAE (%)"] = round((entry_px - trade_min_low)  / entry_px * 100, 3)
            trade_entry["MFE (%)"] = round((trade_max_high - entry_px) / entry_px * 100, 3)
        else:               # Short: adverse = price rose, favourable = price fell
            trade_entry["MAE (%)"] = round((trade_max_high - entry_px) / entry_px * 100, 3)
            trade_entry["MFE (%)"] = round((entry_px - trade_min_low)  / entry_px * 100, 3)


def run_backtest(
    signals: pd.Series,
    prices: pd.DataFrame,
    interval: str = "1d",
    risk_per_trade: float = 0.02,
    commission_pct: float = 0.0,
    slippage_pct: float = 0.0,
    vol_target: Optional[float] = None,
    close_on_neutral: bool = False,
    max_bars_held: Optional[int] = None,
    use_sltp: bool = True,
    sl_pct_fixed: Optional[float] = None,
    tp_ratio: float = 2.0,
    exit_ma_period: Optional[int] = None,
    trailing_sl: bool = False,
    trail_atr_mult: float = 1.0,
    long_only: bool = False,
    short_only: bool = False,
    vol_method: str = "Rolling Std",
) -> Dict[str, Any]:
    """
    Convert a signal Series into positions, compute returns and metrics.

    Parameters
    ----------
    signals          : Signal Series (1, -1, 0), indexed to match prices.
    prices           : OHLCV DataFrame from data.py.
    interval         : yfinance interval string used to determine annualisation factor.
    risk_per_trade   : Fraction of capital to risk per trade (default 2%).
    commission_pct   : Round-trip commission as a fraction of position value (e.g. 0.001 = 0.1%).
    slippage_pct     : Round-trip slippage estimate added on top of commission.
    vol_target       : If set, size positions to target this annualised portfolio volatility
                       (e.g. 0.15 = 15%/year). Overrides risk_per_trade when provided.
    close_on_neutral : If True, exit any open trade when signal returns to 0.
    max_bars_held    : If set, force-exit any trade that has been open for this many bars.
    use_sltp         : If False, disable SL/TP exits entirely — position is managed only by
                       the signal (neutral, maxbars, or flip). Recommended for mean-reversion
                       strategies where the signal itself defines the risk via exit threshold.
    sl_pct_fixed     : If set, use this fixed fraction as the SL distance instead of the
                       volatility-sized stop (e.g. 0.02 = 2% stop).
    tp_ratio         : TP distance as a multiple of SL distance (default 2.0 = 2:1 R:R).
    exit_ma_period   : If set, exit any open long when close crosses below this MA, and any
                       open short when close crosses above it. Checked every bar during a trade.
    trailing_sl      : If True, the SL price ratchets up (long) or down (short) as price
                       moves in favour — locks in profit. Requires use_sltp=True.
    trail_atr_mult   : Multiplier applied to the SL distance when trailing_sl is True.
    vol_method       : Volatility model for stop sizing — "Rolling Std", "ATR", or "EWMA".

    Returns
    -------
    dict with keys:
        metrics      — performance metric dict
        equity_curve — pd.Series of cumulative returns
        trade_log    — pd.DataFrame of individual trades
        returns      — pd.Series of per-bar strategy returns
    """
    return _run_with_sltp(
        signals, prices, interval, risk_per_trade,
        commission_pct, slippage_pct, vol_target,
        close_on_neutral=close_on_neutral,
        max_bars_held=max_bars_held,
        use_sltp=use_sltp,
        sl_pct_fixed=sl_pct_fixed,
        tp_ratio=tp_ratio,
        exit_ma_period=exit_ma_period,
        trailing_sl=trailing_sl,
        trail_atr_mult=trail_atr_mult,
        long_only=long_only,
        short_only=short_only,
        vol_method=vol_method,
    )


def _compute_metrics(
    returns: pd.Series,
    equity_curve: pd.Series,
    periods_per_year: float,
) -> Dict[str, float]:
    """
    Compute standard performance metrics from a returns series.
    """
    total_return = float(equity_curve.iloc[-1] - 1) if len(equity_curve) else 0.0
    n_bars = len(returns.dropna())
    years  = n_bars / periods_per_year

    ann_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

    rolling_max  = equity_curve.cummax()
    drawdown     = (equity_curve - rolling_max) / rolling_max.replace(0, np.nan)
    max_drawdown = float(drawdown.min()) if len(drawdown) else 0.0

    # Longest continuous period below a prior peak (in bars)
    in_dd = (equity_curve < rolling_max).values
    dd_run, dd_lengths = 0, []
    for v in in_dd:
        if v:
            dd_run += 1
        elif dd_run:
            dd_lengths.append(dd_run)
            dd_run = 0
    if dd_run:
        dd_lengths.append(dd_run)
    max_dd_bars = max(dd_lengths) if dd_lengths else 0

    std    = returns.std()
    sharpe = float(returns.mean() / std * np.sqrt(periods_per_year)) if std > 0 else 0.0

    # Sortino: penalises only downside volatility
    downside     = returns[returns < 0]
    downside_std = float(downside.std()) if len(downside) > 1 else 0.0
    sortino      = float(returns.mean() / downside_std * np.sqrt(periods_per_year)) if downside_std > 0 else 0.0

    calmar = float(ann_return / abs(max_drawdown)) if max_drawdown != 0 else 0.0

    active   = returns[returns != 0].dropna()
    win_rate = float((active > 0).sum() / len(active)) if len(active) > 0 else 0.0

    # Exposure: fraction of bars where the strategy held a position
    exposure = round(float((returns != 0).sum() / len(returns) * 100), 2) if len(returns) > 0 else 0.0

    return {
        "Total Return (%)":      round(total_return * 100, 2),
        "Annualised Return (%)": round(ann_return * 100, 2),
        "Max Drawdown (%)":      round(max_drawdown * 100, 2),
        "Max DD Duration (bars)": max_dd_bars,
        "Sharpe Ratio":          round(sharpe, 3),
        "Sortino Ratio":         round(sortino, 3),
        "Calmar Ratio":          round(calmar, 3),
        "Win Rate (%)":          round(win_rate * 100, 2),
        "Exposure (%)":          exposure,
        "Number of Trades":      0,  # patched after trade log is built
    }


def _run_with_sltp(
    signals: pd.Series,
    prices: pd.DataFrame,
    interval: str,
    risk_per_trade: float,
    commission_pct: float = 0.0,
    slippage_pct: float = 0.0,
    vol_target: Optional[float] = None,
    close_on_neutral: bool = False,
    max_bars_held: Optional[int] = None,
    use_sltp: bool = True,
    sl_pct_fixed: Optional[float] = None,
    tp_ratio: float = 2.0,
    exit_ma_period: Optional[int] = None,
    trailing_sl: bool = False,
    trail_atr_mult: float = 1.0,
    long_only: bool = False,
    short_only: bool = False,
    vol_method: str = "Rolling Std",
) -> Dict[str, Any]:
    """
    Bar-by-bar backtest with explicit SL/TP exits and volatility-scaled position sizing.

    SL is derived from the chosen vol_method ("Rolling Std", "ATR", or "EWMA").
    Position size = risk_per_trade / sl_pct (capped at 100%, no leverage).
    TP = tp_ratio × SL distance.
    When vol_target is set, position size targets the given annualised portfolio volatility.
    """
    close            = prices["Close"]
    bar_returns      = calculate_returns(close, log=False)
    shifted_signals  = signals.shift(1).reindex(prices.index).fillna(0)
    periods_per_year = annualisation_factor(interval)

    # Pre-extract numpy arrays — eliminates per-iteration pandas .iloc overhead
    open_arr  = prices["Open"].values
    high_arr  = prices["High"].values
    low_arr   = prices["Low"].values
    close_arr = prices["Close"].values
    sig_arr   = shifted_signals.values.astype(np.int8)
    ret_arr   = bar_returns.values
    idx       = prices.index
    n         = len(prices)

    strat_ret_arr = np.zeros(n, dtype=np.float64)
    pos_arr       = np.zeros(n, dtype=np.float64)

    # Precompute exit MA if requested (NaN for the warm-up period)
    exit_ma_arr: Optional[np.ndarray] = None
    if exit_ma_period is not None and exit_ma_period > 0:
        exit_ma_arr = (
            pd.Series(close_arr).rolling(exit_ma_period).mean().values
        )

    in_trade          = False
    direction         = 0
    entry_price       = 0.0
    sl_price          = 0.0
    tp_price          = 0.0
    sl_pct_val        = 0.02
    tp_pct_val        = 0.04
    pos_fraction      = 1.0
    current_entry_idx = None
    pending_entry     = 0    # direction queued after a signal-flip exit
    trade_min_low     = float("inf")
    trade_max_high    = float("-inf")
    bars_in_trade     = 0
    blocked_after_sltp  = False  # prevent re-entry after SL/TP until signal genuinely resets
    blocked_direction   = 0     # direction of the stopped-out trade
    last_non_zero_sig   = 0     # last non-zero signal (ignores ADX-filtered 0s)
    trade_sltp: Dict   = {}   # entry_bar_index → trade detail dict

    for i in range(1, n):
        sig      = int(sig_arr[i])

        if sig != 0:
            last_non_zero_sig = sig

        # Unblock re-entry once the underlying signal direction has genuinely changed.
        # last_non_zero_sig ignores ADX-filtered 0s so a state signal that is temporarily
        # zeroed by the ADX filter doesn't look like a reversal.
        # Because long_only/short_only no longer zero out -1/+1 at the signal level,
        # the opposite-direction signal is preserved and naturally triggers this unblock.
        if blocked_after_sltp and last_non_zero_sig != blocked_direction:
            blocked_after_sltp = False
            blocked_direction  = 0

        bar_high = float(high_arr[i])
        bar_low  = float(low_arr[i])
        r        = ret_arr[i]
        bar_ret  = float(r) if not np.isnan(r) else 0.0
        just_exited = False

        if in_trade:
            bars_in_trade += 1
            trade_min_low  = min(trade_min_low,  bar_low)
            trade_max_high = max(trade_max_high, bar_high)

            # Ratchet the stop up (long) or down (short) as price moves in favour.
            # sl_price only ever moves in the profitable direction — never backwards.
            # sl_pct_val already has trail_atr_mult baked in from entry.
            if use_sltp and trailing_sl:
                if direction == 1:
                    sl_price = max(sl_price, trade_max_high * (1.0 - sl_pct_val))
                else:
                    sl_price = min(sl_price, trade_min_low  * (1.0 + sl_pct_val))



            sl_hit       = use_sltp and (
                               (direction ==  1 and bar_low  <= sl_price) or
                               (direction == -1 and bar_high >= sl_price)
                           )
            tp_hit       = use_sltp and tp_ratio is not None and (
                               (direction ==  1 and bar_high >= tp_price) or
                               (direction == -1 and bar_low  <= tp_price)
                           )
            ma_exit_hit  = (
                exit_ma_arr is not None
                and not np.isnan(exit_ma_arr[i])
                and (
                    (direction ==  1 and close_arr[i] < exit_ma_arr[i]) or
                    (direction == -1 and close_arr[i] > exit_ma_arr[i])
                )
            )
            neutral_exit = (close_on_neutral and sig == 0) or ma_exit_hit
            maxbar_exit  = max_bars_held is not None and bars_in_trade >= max_bars_held

            # Combined entry+exit cost covering both commission and slippage
            rt_cost = (2.0 * commission_pct + 2.0 * slippage_pct) * pos_fraction

            if sl_hit:
                if trailing_sl:
                    # Bar return: from previous close to stop price.
                    # Holding-bar returns were already accumulated in strat_ret_arr,
                    # so this bar contributes only the move from last close → stop.
                    prev_close = float(close_arr[i - 1]) if i > 0 else entry_price
                    sl_ret = (sl_price / prev_close - 1.0) * direction if prev_close > 0 else -sl_pct_val
                else:
                    sl_ret = -sl_pct_val
                strat_ret_arr[i] = pos_fraction * sl_ret - rt_cost
                if current_entry_idx is not None:
                    trade_sltp[current_entry_idx]["Exit Price"]  = round(sl_price, 6)
                    trade_sltp[current_entry_idx]["Exit Reason"] = "Trail SL" if trailing_sl else "SL"
                    _record_mae_mfe(trade_sltp[current_entry_idx], direction,
                                    trade_min_low, trade_max_high)
                in_trade          = False
                just_exited       = True
                current_entry_idx = None
                blocked_after_sltp = True
                blocked_direction  = direction
            elif tp_hit:
                strat_ret_arr[i] = pos_fraction * tp_pct_val - rt_cost
                if current_entry_idx is not None:
                    trade_sltp[current_entry_idx]["Exit Price"]  = round(tp_price, 6)
                    trade_sltp[current_entry_idx]["Exit Reason"] = "TP"
                    _record_mae_mfe(trade_sltp[current_entry_idx], direction,
                                    trade_min_low, trade_max_high)
                in_trade          = False
                just_exited       = True
                current_entry_idx = None
                blocked_after_sltp = True
                blocked_direction  = direction
            elif neutral_exit or maxbar_exit:
                reason = "MA" if ma_exit_hit else ("Neutral" if neutral_exit else "MaxBars")
                strat_ret_arr[i] = pos_fraction * direction * bar_ret - rt_cost
                if current_entry_idx is not None:
                    trade_sltp[current_entry_idx]["Exit Price"]  = round(float(close_arr[i]), 6)
                    trade_sltp[current_entry_idx]["Exit Reason"] = reason
                    _record_mae_mfe(trade_sltp[current_entry_idx], direction,
                                    trade_min_low, trade_max_high)
                in_trade = False
                just_exited = True
                current_entry_idx = None
            elif sig != 0 and sig != direction:
                # Signal flipped — exit this bar, open opposite direction next bar.
                strat_ret_arr[i] = pos_fraction * direction * bar_ret - rt_cost
                if current_entry_idx is not None:
                    trade_sltp[current_entry_idx]["Exit Price"]  = round(float(close_arr[i]), 6)
                    trade_sltp[current_entry_idx]["Exit Reason"] = "Signal"
                    _record_mae_mfe(trade_sltp[current_entry_idx], direction,
                                    trade_min_low, trade_max_high)
                in_trade = False
                just_exited = True
                pending_entry = sig
                current_entry_idx = None
            else:
                strat_ret_arr[i] = pos_fraction * direction * bar_ret
                pos_arr[i]       = pos_fraction * direction

        # Resolve which signal to act on this bar
        if not just_exited:
            if sig != 0:
                effective_sig = sig
                pending_entry = 0
            else:
                effective_sig = pending_entry
                pending_entry = 0
        else:
            effective_sig = 0  # blocked; pending_entry is preserved for next bar

        # Directional filter: skip entry if the signal direction is not allowed.
        # The signal itself is not modified (so exits still fire on -1 for long_only),
        # only new trade entries are suppressed here.
        _dir_allowed = not (
            (long_only  and effective_sig == -1) or
            (short_only and effective_sig ==  1)
        )

        if not in_trade and not just_exited and effective_sig != 0 and not blocked_after_sltp and _dir_allowed:
            direction   = effective_sig
            entry_price = float(open_arr[i])
            bar_idx     = idx[i]

            sl_pct_val = (
                sl_pct_fixed
                if sl_pct_fixed is not None
                else _vol_to_sl_pct_fast(close_arr, i, interval, vol_method, high_arr, low_arr)
            )
            if trailing_sl:
                sl_pct_val *= trail_atr_mult
            tp_pct_val = (tp_ratio * sl_pct_val) if tp_ratio is not None else 0.0
            sl_price   = entry_price * (1 - sl_pct_val * direction)
            tp_price   = entry_price * (1 + tp_pct_val * direction) if tp_ratio is not None else (
                float("inf") if direction == 1 else float("-inf")
            )

            if vol_target is not None:
                per_bar_vol  = _vol_to_sl_pct_fast(close_arr, i, interval, vol_method, high_arr, low_arr)
                ann_vol      = per_bar_vol * np.sqrt(periods_per_year)
                pos_fraction = min(vol_target / ann_vol, 1.0) if ann_vol > 0 else 1.0
            else:
                pos_fraction = min(risk_per_trade / sl_pct_val, 1.0)

            in_trade          = True
            current_entry_idx = bar_idx
            trade_min_low     = bar_low
            trade_max_high    = bar_high
            bars_in_trade     = 0
            trade_sltp[bar_idx] = {
                "Entry Price": round(entry_price, 6),
                "SL Price":    round(sl_price, 6) if use_sltp else None,
                "TP Price":    round(tp_price, 6) if (use_sltp and tp_ratio is not None) else None,
                "Exit Price":  None,
                "Exit Reason": "End",  # default; overwritten if SL/TP/Signal fires
                "MAE (%)":     None,
                "MFE (%)":     None,
            }

            # Check SL/TP on the very first bar of the trade
            sl_hit = use_sltp and (
                         (direction ==  1 and bar_low  <= sl_price) or
                         (direction == -1 and bar_high >= sl_price)
                     )
            tp_hit = use_sltp and tp_ratio is not None and (
                         (direction ==  1 and bar_high >= tp_price) or
                         (direction == -1 and bar_low  <= tp_price)
                     )

            rt_cost = (2.0 * commission_pct + 2.0 * slippage_pct) * pos_fraction

            if sl_hit:
                strat_ret_arr[i] = pos_fraction * (-sl_pct_val) - rt_cost
                trade_sltp[bar_idx]["Exit Price"]  = round(sl_price, 6)
                trade_sltp[bar_idx]["Exit Reason"] = "SL"
                _record_mae_mfe(trade_sltp[bar_idx], direction, trade_min_low, trade_max_high)
                in_trade = False
                current_entry_idx = None
            elif tp_hit:
                strat_ret_arr[i] = pos_fraction * tp_pct_val - rt_cost
                trade_sltp[bar_idx]["Exit Price"]  = round(tp_price, 6)
                trade_sltp[bar_idx]["Exit Reason"] = "TP"
                _record_mae_mfe(trade_sltp[bar_idx], direction, trade_min_low, trade_max_high)
                in_trade = False
                current_entry_idx = None
            else:
                # Return from entry price (Open[i]) to close of the same bar
                entry_bar_ret = (float(close_arr[i]) - entry_price) / entry_price
                strat_ret_arr[i] = pos_fraction * direction * entry_bar_ret
                pos_arr[i]       = pos_fraction * direction

    # Close any trade that's still open at end of data
    if in_trade and current_entry_idx is not None and current_entry_idx in trade_sltp:
        trade_sltp[current_entry_idx]["Exit Price"]  = round(float(close_arr[-1]), 6)
        trade_sltp[current_entry_idx]["Exit Reason"] = "End"
        _record_mae_mfe(trade_sltp[current_entry_idx], direction, trade_min_low, trade_max_high)

    strategy_returns = pd.Series(strat_ret_arr, index=prices.index)
    position_series  = pd.Series(pos_arr, index=prices.index)

    equity_curve = (1 + strategy_returns).cumprod()
    metrics      = _compute_metrics(strategy_returns, equity_curve, periods_per_year)
    trade_log    = _build_trade_log(position_series, bar_returns, prices, actual_returns=strategy_returns)
    metrics["Number of Trades"] = len(trade_log)

    if not trade_log.empty and "Return (%)" in trade_log.columns:
        metrics["Win Rate (%)"] = round(
            (trade_log["Return (%)"] > 0).sum() / len(trade_log) * 100, 2
        )
        long_trades  = trade_log[trade_log["Direction"] == "Long"]
        short_trades = trade_log[trade_log["Direction"] == "Short"]
        if not long_trades.empty:
            metrics["Long Win Rate (%)"]  = round(
                (long_trades["Return (%)"]  > 0).sum() / len(long_trades)  * 100, 2
            )
        if not short_trades.empty:
            metrics["Short Win Rate (%)"] = round(
                (short_trades["Return (%)"] > 0).sum() / len(short_trades) * 100, 2
            )

    if trade_sltp and not trade_log.empty:
        sltp_df = pd.DataFrame.from_dict(trade_sltp, orient="index")
        sltp_df.index.name = "Entry Date"
        sltp_df = sltp_df.reset_index()
        trade_log = trade_log.drop(columns=["Entry Price", "Exit Price"], errors="ignore")
        trade_log = trade_log.merge(sltp_df, on="Entry Date", how="left")
        cols = [
            "Entry Date", "Exit Date", "Entry Price", "SL Price", "TP Price",
            "Exit Price", "Exit Reason", "Direction", "Return (%)", "Bars Held",
            "MAE (%)", "MFE (%)",
        ]
        trade_log = trade_log[[c for c in cols if c in trade_log.columns]]

    return {
        "metrics":      metrics,
        "equity_curve": equity_curve,
        "trade_log":    trade_log,
        "returns":      strategy_returns,
    }


def _bars_held(position: pd.Series, current_i: int, entry_date) -> int:
    loc = position.index.get_loc(entry_date)
    entry_i = loc.start if isinstance(loc, slice) else int(loc)
    return current_i - entry_i


def _build_trade_log(
    position: pd.Series,
    bar_returns: pd.Series,
    prices: pd.DataFrame,
    actual_returns: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Build a trade log DataFrame — one row per discrete trade.

    A trade starts when position changes from 0 to ±1 (or flips direction)
    and ends when it changes back to 0 or flips.
    """
    trades = []
    in_trade        = False
    entry_date      = None
    entry_price_val = 0.0
    direction       = 0
    trade_return    = 1.0

    for i in range(len(position)):
        pos     = position.iloc[i]
        ret     = bar_returns.iloc[i]
        dt      = position.index[i]
        new_dir = 0 if (pd.isna(pos) or pos == 0) else int(np.sign(pos))

        if in_trade:
            if new_dir == direction:
                if actual_returns is not None:
                    bar_contrib = float(actual_returns.iloc[i])
                else:
                    bar_contrib = float(pos * ret) if not np.isnan(ret) else 0.0
                trade_return *= (1 + bar_contrib)

                if i == len(position) - 1:
                    trades.append({
                        "Entry Date":  entry_date,
                        "Exit Date":   dt,
                        "Entry Price": round(entry_price_val, 4),
                        "Exit Price":  round(float(prices["Close"].iloc[i]), 4),
                        "Direction":   "Long" if direction == 1 else "Short",
                        "Return (%)":  round((trade_return - 1) * 100, 3),
                        "Bars Held":   _bars_held(position, i, entry_date),
                    })
                    in_trade = False
            else:
                # In SL/TP mode the exit bar holds the SL/TP payoff — include it.
                if actual_returns is not None:
                    trade_return *= (1 + float(actual_returns.iloc[i]))
                prev_close = float(prices["Close"].iloc[i - 1]) if i > 0 else float(prices["Close"].iloc[i])
                trades.append({
                    "Entry Date":  entry_date,
                    "Exit Date":   dt,
                    "Entry Price": round(entry_price_val, 4),
                    "Exit Price":  round(prev_close, 4),
                    "Direction":   "Long" if direction == 1 else "Short",
                    "Return (%)":  round((trade_return - 1) * 100, 3),
                    "Bars Held":   _bars_held(position, i, entry_date),
                })
                in_trade = False

                if new_dir != 0:
                    in_trade        = True
                    entry_date      = dt
                    entry_price_val = prev_close
                    direction       = new_dir
                    trade_return    = 1.0
                    if actual_returns is not None:
                        bar_contrib = float(actual_returns.iloc[i])
                    else:
                        bar_contrib = float(pos * ret) if not np.isnan(ret) else 0.0
                    trade_return *= (1 + bar_contrib)

        elif new_dir != 0:
            in_trade        = True
            entry_date      = dt
            entry_price_val = float(prices["Close"].iloc[i - 1]) if i > 0 else float(prices["Close"].iloc[i])
            direction       = new_dir
            trade_return    = 1.0
            if actual_returns is not None:
                bar_contrib = float(actual_returns.iloc[i])
            else:
                bar_contrib = float(pos * ret) if not np.isnan(ret) else 0.0
            trade_return *= (1 + bar_contrib)

    return pd.DataFrame(trades)


def parameter_sweep(
    strategy_fn: Callable,
    param_grid: Dict[str, List],
    prices: pd.DataFrame,
    interval: str = "1d",
    commission_pct: float = 0.0,
    min_trades: int = 0,
) -> pd.DataFrame:
    """
    Run a backtest for every combination of parameters in the grid.

    Parameters
    ----------
    strategy_fn   : A strategy function from strategies.py.
    param_grid    : Dict mapping parameter name → list of values to try.
    prices        : OHLCV DataFrame.
    interval      : Bar frequency for annualisation.
    commission_pct: Round-trip commission fraction passed to each backtest.
    min_trades    : Skip combinations that produce fewer than this many trades.

    Returns
    -------
    pd.DataFrame of results sorted by Sharpe ratio (descending).
    """
    keys   = list(param_grid.keys())
    values = list(param_grid.values())
    rows   = []

    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        try:
            signals = strategy_fn(prices, **params)
            result  = run_backtest(
                signals, prices, interval,
                commission_pct=commission_pct,
            )
            if result["metrics"]["Number of Trades"] < min_trades:
                continue
            row = {**params, **result["metrics"]}
            rows.append(row)
        except Exception:
            pass

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("Sharpe Ratio", ascending=False)
    return df.reset_index(drop=True)


def walk_forward(
    strategy_fn: Callable,
    param_grid: Dict[str, List],
    prices: pd.DataFrame,
    interval: str = "1d",
    train_bars: int = 252,
    test_bars: int = 63,
    commission_pct: float = 0.0,
    min_trades: int = 3,
) -> Dict[str, Any]:
    """
    Walk-forward optimisation.

    For each rolling window:
      1. Run parameter_sweep on the training portion to find the best params.
      2. Generate signals on the full data up to the end of the test window
         (ensures indicator warm-up is correct), then backtest on the test portion.
      3. Stitch all test-period returns into one out-of-sample equity curve.

    Parameters
    ----------
    strategy_fn   : Strategy function from strategies.py.
    param_grid    : Same format as parameter_sweep — keys are param names, values
                    are lists of values to test.
    prices        : Full OHLCV DataFrame.
    interval      : Bar frequency string for annualisation.
    train_bars    : Bars in each training window.
    test_bars     : Bars in each test window. Window rolls forward by test_bars each step.
    commission_pct: Commission fraction passed to every backtest.
    min_trades    : Minimum trades a sweep combo must produce to be considered.

    Returns
    -------
    dict with keys:
        oos_equity_curve : pd.Series — stitched out-of-sample equity curve.
        oos_metrics      : dict — metrics on the stitched OOS returns.
        windows          : pd.DataFrame — one row per window with IS and OOS stats.
        n_windows        : int — windows that produced valid results.
        error            : str or None — set if setup failed before any windows ran.
    """
    n = len(prices)
    if n < train_bars + test_bars:
        return {
            "error": (
                f"Need at least {train_bars + test_bars} bars "
                f"(train={train_bars} + test={test_bars}), "
                f"but only {n} available."
            ),
            "oos_equity_curve": None, "oos_metrics": {}, "windows": pd.DataFrame(), "n_windows": 0,
        }

    # Build window index list — roll forward by test_bars each step
    windows = []
    pos = 0
    while pos + train_bars + test_bars <= n:
        windows.append((pos, pos + train_bars, pos + train_bars + test_bars))
        pos += test_bars

    if len(windows) < 2:
        return {
            "error": (
                f"Only {len(windows)} window fits. Reduce train/test window sizes "
                f"or extend the date range."
            ),
            "oos_equity_curve": None, "oos_metrics": {}, "windows": pd.DataFrame(), "n_windows": 0,
        }

    param_keys    = list(param_grid.keys())
    window_rows   = []
    oos_ret_parts = []
    oos_tl_parts  = []

    for win_start, win_train_end, win_test_end in windows:
        prices_train = prices.iloc[win_start:win_train_end]
        prices_test  = prices.iloc[win_train_end:win_test_end]

        # Sweep on training window only
        sweep_df = parameter_sweep(
            strategy_fn, param_grid, prices_train, interval,
            commission_pct=commission_pct, min_trades=min_trades,
        )
        if sweep_df.empty:
            continue

        best = sweep_df.iloc[0]
        # pandas stores param values as float64 in the DataFrame; restore
        # to the correct Python type by matching against the original grid.
        best_params = {}
        for k in param_keys:
            if k not in best:
                continue
            ref_type = type(param_grid[k][0])
            best_params[k] = int(round(best[k])) if ref_type is int else float(best[k])

        # Generate signals on data up to test_end so indicator lookbacks are valid,
        # then slice to the test window — no look-ahead (all indicators are causal).
        try:
            signals_full = strategy_fn(prices.iloc[:win_test_end], **best_params)
            signals_test = signals_full.iloc[win_train_end:win_test_end]
            oos_result   = run_backtest(
                signals_test, prices_test, interval,
                commission_pct=commission_pct,
            )
        except Exception:
            continue

        oos_m = oos_result["metrics"]
        row = {
            "Train Start": str(prices_train.index[0])[:10],
            "Train End":   str(prices_train.index[-1])[:10],
            "Test Start":  str(prices_test.index[0])[:10],
            "Test End":    str(prices_test.index[-1])[:10],
        }
        row.update({f"Best {k}": best_params[k] for k in param_keys})
        row.update({
            "IS Sharpe":        round(float(best["Sharpe Ratio"]), 3),
            "OOS Sharpe":       oos_m["Sharpe Ratio"],
            "OOS Return (%)":   oos_m["Total Return (%)"],
            "OOS Max DD (%)":   oos_m["Max Drawdown (%)"],
            "OOS Trades":       oos_m["Number of Trades"],
            "OOS Win Rate (%)": oos_m.get("Win Rate (%)", 0),
        })
        window_rows.append(row)
        oos_ret_parts.append(oos_result["returns"])
        if not oos_result["trade_log"].empty:
            oos_tl_parts.append(oos_result["trade_log"])

    if not window_rows:
        return {
            "error": "No walk-forward windows produced valid results. "
                     "Try reducing min_trades or adjusting window sizes.",
            "oos_equity_curve": None, "oos_metrics": {}, "windows": pd.DataFrame(), "n_windows": 0,
        }

    # Stitch OOS returns and compute aggregate metrics
    oos_returns  = pd.concat(oos_ret_parts)
    oos_equity   = (1 + oos_returns).cumprod()
    oos_metrics  = _compute_metrics(oos_returns, oos_equity, annualisation_factor(interval))

    # Patch Number of Trades and Win Rate from the stitched trade log
    oos_metrics["Number of Trades"] = sum(r["OOS Trades"] for r in window_rows)
    if oos_tl_parts:
        all_tl = pd.concat(oos_tl_parts, ignore_index=True)
        if "Return (%)" in all_tl.columns and not all_tl.empty:
            oos_metrics["Win Rate (%)"] = round(
                (all_tl["Return (%)"] > 0).sum() / len(all_tl) * 100, 2
            )

    return {
        "oos_equity_curve": oos_equity,
        "oos_metrics":      oos_metrics,
        "windows":          pd.DataFrame(window_rows),
        "n_windows":        len(window_rows),
        "error":            None,
    }
