"""
utils.py — Shared helper functions used across all modules.

Imports: nothing from this project (standalone helpers).
Exports: calculate_returns, annualisation_factor, plot_equity_curve,
         plot_drawdown, plot_signals_on_price, plot_signals_chart.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional

# Named constants — avoids magic numbers scattered through the codebase
TRADING_DAYS_PER_YEAR = 252
US_TRADING_HOURS_PER_DAY = 6.5  # approximate NYSE/NASDAQ session length


def calculate_returns(prices: pd.Series, log: bool = True) -> pd.Series:
    """
    Compute per-bar returns from a price series.

    Parameters
    ----------
    prices : pd.Series
        Close price series.
    log : bool
        If True, return log returns (additive, better statistical properties).
        If False, return simple percentage returns.
        # Why log: log returns are time-additive (sum over period = total return)
        # and are approximately normally distributed, which suits the Sharpe calc.

    Returns
    -------
    pd.Series of returns, same index as prices.
    """
    if log:
        return np.log(prices / prices.shift(1))
    return prices.pct_change()


def annualisation_factor(interval: str) -> float:
    """
    Return the number of bars per year for a given yfinance interval string.

    Parameters
    ----------
    interval : str
        yfinance interval, e.g. '1d', '1h', '4h'.

    Returns
    -------
    float — periods per year used to annualise Sharpe and returns.
    """
    mapping = {
        "1d": float(TRADING_DAYS_PER_YEAR),
        "1h": TRADING_DAYS_PER_YEAR * US_TRADING_HOURS_PER_DAY,
        "4h": TRADING_DAYS_PER_YEAR * (US_TRADING_HOURS_PER_DAY / 4),
        "15m": TRADING_DAYS_PER_YEAR * US_TRADING_HOURS_PER_DAY * 4,
        "5m": TRADING_DAYS_PER_YEAR * US_TRADING_HOURS_PER_DAY * 12,
    }
    return mapping.get(interval, float(TRADING_DAYS_PER_YEAR))


def plot_equity_curve(
    equity_curve: pd.Series,
    benchmark: Optional[pd.Series] = None,
    title: str = "Equity Curve",
) -> go.Figure:
    """
    Plot cumulative strategy returns, optionally alongside a benchmark.

    Parameters
    ----------
    equity_curve : pd.Series
        Cumulative return series (starts at 1.0 or 0.0).
    benchmark : pd.Series, optional
        Buy-and-hold benchmark for comparison.
    title : str
        Chart title.

    Returns
    -------
    plotly Figure.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=equity_curve.index,
            y=equity_curve.values,
            mode="lines",
            name="Strategy",
            line=dict(color="#00b4d8", width=2),
        )
    )

    if benchmark is not None:
        fig.add_trace(
            go.Scatter(
                x=benchmark.index,
                y=benchmark.values,
                mode="lines",
                name="Buy & Hold",
                line=dict(color="#adb5bd", width=1.5, dash="dash"),
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Cumulative Return",
        template="plotly_dark",
        hovermode="x unified",
    )
    return fig


def plot_drawdown(equity_curve: pd.Series) -> go.Figure:
    """
    Plot the rolling drawdown (peak-to-trough decline) over time.

    Parameters
    ----------
    equity_curve : pd.Series
        Cumulative return series.

    Returns
    -------
    plotly Figure with drawdown shaded in red.
    """
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max.replace(0, np.nan)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=drawdown.index,
            y=drawdown.values * 100,
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(239,68,68,0.25)",
            line=dict(color="#ef4444", width=1.5),
            name="Drawdown %",
        )
    )
    fig.update_layout(
        title="Drawdown",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        template="plotly_dark",
        hovermode="x unified",
    )
    return fig


def plot_signals_on_price(
    prices: pd.DataFrame,
    signals: pd.Series,
    title: str = "Price with Signals",
    trade_log: Optional[pd.DataFrame] = None,
    indicator_overlays: Optional[list] = None,
    interval: str = "1d",
) -> go.Figure:
    """
    Candlestick chart with trade entry markers, optional SL/TP levels,
    and optional strategy indicator overlays.

    indicator_overlays is a list of dicts produced by each strategy's
    _indicators() function:
        {"panel": "price"|"oscillator", "traces": [plotly_trace, ...],
         "yaxis_title": str, "yaxis_range": [lo, hi]}
    Price overlays are drawn on the main candle panel.
    Oscillators each get their own sub-panel below.

    Trade markers are coloured by outcome: green = winning trade, red = losing trade.
    split_date adds a vertical dashed line dividing the train and test periods.

    dragmode="pan" — left-click drags; pass config={"scrollZoom": True}
    to st.plotly_chart to enable scroll-wheel zoom.
    """
    price_overlays = [o for o in (indicator_overlays or []) if o["panel"] == "price"]
    osc_panels     = [o for o in (indicator_overlays or []) if o["panel"] == "oscillator"]

    n_rows = 1 + len(osc_panels)
    if osc_panels:
        osc_h       = 0.4 / len(osc_panels)
        row_heights = [0.6] + [osc_h] * len(osc_panels)
    else:
        row_heights = [1.0]

    fig = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        vertical_spacing=0.03,
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=prices.index,
        open=prices["Open"],
        high=prices["High"],
        low=prices["Low"],
        close=prices["Close"],
        name="Price",
        increasing_line_color="#22c55e",
        decreasing_line_color="#ef4444",
        whiskerwidth=0.3,
    ), row=1, col=1)

    # Price-panel indicator overlays
    for overlay in price_overlays:
        for trace in overlay["traces"]:
            fig.add_trace(trace, row=1, col=1)

    # Trade markers, SL/TP zones, and background shading
    has_trades = trade_log is not None and not trade_log.empty
    has_sltp   = (
        has_trades
        and {"SL Price", "TP Price", "Entry Price"}.issubset(trade_log.columns)
        and trade_log["SL Price"].notna().any()
    )
    has_return = has_trades and "Return (%)" in trade_log.columns

    price_lo = float(prices["Low"].min())
    price_hi = float(prices["High"].max())

    # All rect shapes collected here and set in one fig.update_layout call at the end.
    # fig.add_shape() rebuilds the internal tuple on every call → O(n²) with many trades.
    _shapes: list = []
    # Above ~500 trades the rectangles become too narrow to be useful; skip them and rely
    # on the entry/exit markers only.
    _show_rects = has_trades and len(trade_log) <= 500

    if has_trades:
        # Direction strip: thin colored ribbon at the bottom of the price panel
        # Sits in the margin gap below the lowest candle so it doesn't overlap price action
        _strip_h   = (price_hi - price_lo) * 0.015
        _strip_bot = price_lo - (price_hi - price_lo) * 0.03
        _strip_top = _strip_bot + _strip_h
        if _show_rects:
            for _, trade in trade_log.iterrows():
                if pd.isna(trade.get("Entry Date")) or pd.isna(trade.get("Exit Date")):
                    continue
                is_long     = trade["Direction"] == "Long"
                strip_color = "rgba(34,197,94,0.8)"  if is_long else "rgba(239,68,68,0.8)"
                shade_color = "rgba(34,197,94,0.06)" if is_long else "rgba(239,68,68,0.06)"

                # Full-height background shading for the trade duration
                _shapes.append(dict(
                    type="rect",
                    x0=trade["Entry Date"], x1=trade["Exit Date"],
                    y0=price_lo, y1=price_hi,
                    fillcolor=shade_color, line=dict(width=0), layer="below",
                    xref="x", yref="y",
                ))
                # Direction strip at the bottom
                _shapes.append(dict(
                    type="rect",
                    x0=trade["Entry Date"], x1=trade["Exit Date"],
                    y0=_strip_bot, y1=_strip_top,
                    fillcolor=strip_color, line=dict(width=0), layer="above",
                    xref="x", yref="y",
                ))

        # Color = direction (green Long, red Short); filled = win, hollow = loss
        for direction_label, color, symbol_filled, symbol_open in [
            ("Long",  "#22c55e", "triangle-up",   "triangle-up-open"),
            ("Short", "#ef4444", "triangle-down", "triangle-down-open"),
        ]:
            dir_subset = trade_log[trade_log["Direction"] == direction_label]
            if dir_subset.empty:
                continue

            for symbol, outcome_label, is_win in [
                (symbol_filled, "Win",  True),
                (symbol_open,   "Loss", False),
            ]:
                if has_return:
                    subset = dir_subset[dir_subset["Return (%)"] > 0] if is_win else dir_subset[dir_subset["Return (%)"] <= 0]
                else:
                    subset = dir_subset if is_win else dir_subset.iloc[0:0]
                if subset.empty:
                    continue

                if has_sltp:
                    y_vals = subset["Entry Price"].values
                else:
                    valid_dates = [d for d in subset["Entry Date"].values if d in prices.index]
                    subset = subset[subset["Entry Date"].isin(valid_dates)]
                    rows_px = prices.loc[valid_dates]
                    if direction_label == "Long":
                        y_vals = [float(rows_px["Low"].iloc[k]) * 0.997 for k in range(len(rows_px))]
                    else:
                        y_vals = [float(rows_px["High"].iloc[k]) * 1.003 for k in range(len(rows_px))]

                label = f"{direction_label} {outcome_label}" if has_return else f"{direction_label} Entry"
                fig.add_trace(go.Scatter(
                    x=subset["Entry Date"].values,
                    y=y_vals,
                    mode="markers",
                    name=label,
                    marker=dict(symbol=symbol, color=color, size=13,
                                line=dict(width=1.5, color=color)),
                ), row=1, col=1)

        # SL/TP zones: shaded rectangles from entry price to each level
        if has_sltp and _show_rects:
            for _, trade in trade_log.iterrows():
                entry_dt = trade["Entry Date"]
                exit_dt  = trade["Exit Date"]
                entry_px = float(trade["Entry Price"]) if pd.notna(trade.get("Entry Price")) else None
                if entry_px is None:
                    continue
                for price_col, fill_color in [
                    ("TP Price", "rgba(34,197,94,0.15)"),
                    ("SL Price", "rgba(239,68,68,0.15)"),
                ]:
                    level = trade.get(price_col)
                    if pd.notna(level):
                        level = float(level)
                        _shapes.append(dict(
                            type="rect",
                            x0=entry_dt, x1=exit_dt,
                            y0=min(entry_px, level), y1=max(entry_px, level),
                            fillcolor=fill_color, line=dict(width=0), layer="below",
                            xref="x", yref="y",
                        ))

        # Exit markers: X at the exit price for each closed trade
        if "Exit Date" in trade_log.columns:
            _has_exit_px = "Exit Price" in trade_log.columns
            for direction_label, color in [("Long", "#22c55e"), ("Short", "#ef4444")]:
                ex_sub = trade_log[
                    (trade_log["Direction"] == direction_label) &
                    trade_log["Exit Date"].notna()
                ]
                if ex_sub.empty:
                    continue
                if _has_exit_px:
                    y_ex = ex_sub["Exit Price"].values
                else:
                    y_ex = [
                        float(prices.loc[d, "Close"]) if d in prices.index else np.nan
                        for d in ex_sub["Exit Date"].values
                    ]
                fig.add_trace(go.Scatter(
                    x=ex_sub["Exit Date"].values,
                    y=y_ex,
                    mode="markers",
                    name=f"{direction_label} Exit",
                    marker=dict(symbol="x", color=color, size=11,
                                line=dict(width=2.5, color=color)),
                ), row=1, col=1)
    else:
        # Fallback — mark every signal bar when no trade log is available
        for sig_val, symbol, color, offset_fn in [
            ( 1, "triangle-up",   "#22c55e", lambda lo, _:  lo * 0.997),
            (-1, "triangle-down", "#ef4444", lambda _, hi: hi * 1.003),
        ]:
            idx = signals[signals == sig_val].index
            if len(idx) == 0:
                continue
            y_vals = [
                offset_fn(float(prices.loc[d, "Low"]), float(prices.loc[d, "High"]))
                for d in idx
            ]
            fig.add_trace(go.Scatter(
                x=idx, y=y_vals,
                mode="markers",
                name="Long Signal" if sig_val == 1 else "Short Signal",
                marker=dict(symbol=symbol, color=color, size=10),
            ), row=1, col=1)

    # Oscillator sub-panels
    for i, panel in enumerate(osc_panels):
        row = i + 2
        for trace in panel["traces"]:
            fig.add_trace(trace, row=row, col=1)
        fig.update_yaxes(title_text=panel.get("yaxis_title", ""), row=row, col=1)
        if panel.get("yaxis_range"):
            fig.update_yaxes(range=panel["yaxis_range"], row=row, col=1)

    y_margin = (price_hi - price_lo) * 0.03
    fig.update_yaxes(
        title_text="Price",
        range=[price_lo - y_margin, price_hi + y_margin],
        minallowed=price_lo - y_margin,
        maxallowed=price_hi + y_margin,
        row=1, col=1,
    )

    # For intraday intervals: hide weekends AND overnight gaps.
    # We derive the actual trading hours from the data's own timestamps so this
    # works regardless of timezone (Yahoo Finance returns UTC for sub-daily data).
    rangebreaks = []
    if interval != "1d":
        rangebreaks.append(dict(bounds=["sat", "mon"]))  # weekends
        idx = prices.index
        if hasattr(idx, "hour") and len(idx) > 0:
            min_h = int(idx.hour.min())
            max_h = int(idx.hour.max()) + 1  # +1 so the last bar's full hour is visible
            if max_h - min_h < 23:           # sanity check — skip if data spans near-24h
                rangebreaks.append(dict(bounds=[max_h, min_h], pattern="hour"))

    fig.update_layout(
        title=title,
        template="plotly_dark",
        hovermode="x unified",
        dragmode="pan",
        showlegend=True,
        shapes=_shapes,  # set all rect shapes in one call — avoids O(n²) per-call tuple rebuilds
        xaxis=dict(
            rangeslider=dict(visible=False),
            rangebreaks=rangebreaks,
            range=[prices.index[0], prices.index[-1]],
            minallowed=prices.index[0],
            maxallowed=prices.index[-1],
            rangeselector=dict(
                bgcolor="#1e293b",
                buttons=[
                    dict(count=1,  label="1M", step="month", stepmode="backward"),
                    dict(count=3,  label="3M", step="month", stepmode="backward"),
                    dict(count=6,  label="6M", step="month", stepmode="backward"),
                    dict(count=1,  label="1Y", step="year",  stepmode="backward"),
                    dict(step="all", label="All"),
                ],
            ),
        ),
    )
    return fig


def plot_signals_chart(
    signals,
    title: str = "Signals",
    split_date=None,
) -> go.Figure:
    """
    Line chart for one or more signal series, with an optional train/test split line.

    signals : pd.Series or pd.DataFrame of signal values.
    """
    if isinstance(signals, pd.Series):
        signals = signals.to_frame()

    colors = ["#60a5fa", "#f59e0b", "#a78bfa", "#22c55e", "#ef4444", "#fb923c", "#38bdf8"]
    fig = go.Figure()
    for k, col in enumerate(signals.columns):
        fig.add_trace(go.Scatter(
            x=signals.index, y=signals[col],
            mode="lines", name=col,
            line=dict(color=colors[k % len(colors)], width=1.5),
        ))

    if split_date is not None:
        split_str = str(split_date)
        fig.add_shape(
            type="line",
            x0=split_str, x1=split_str,
            y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color="#94a3b8", width=1.5, dash="dot"),
        )
        fig.add_annotation(
            x=split_str, y=0.99,
            xref="x", yref="paper",
            text="Train | Test",
            showarrow=False,
            font=dict(color="#94a3b8", size=11),
            xanchor="left",
            bgcolor="rgba(30,41,59,0.7)",
        )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Signal",
    )
    return fig
