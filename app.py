"""
app.py — Streamlit entry point. Wires all modules together into a UI.

Tabs:
  1. Strategy Builder   — define the research idea
  2. Signal Diagnostics — inspect signal quality
  3. Backtest Results   — evaluate performance
  4. Trade Analysis     — understand trade-level behaviour

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import ta
from datetime import date, timedelta
from typing import Dict, Optional

from data import fetch_data, ASSET_CLASS_EXAMPLES
from strategies import (
    STRATEGY_REGISTRY,
    TREND_SIGNAL_REGISTRY,
    MEAN_REVERSION_SIGNAL_REGISTRY,
    PRICE_ACTION_SIGNAL_REGISTRY,
    combine_signals,
    apply_trend_filter,
    generate_trend_signal,
    build_trend_indicators,
    build_strategy_summary,
    apply_entry_logic,
    apply_signal_filters,
    generate_mr_signal,
    build_mr_indicators,
    build_mr_strategy_summary,
    apply_mr_reversal_confirmation,
    get_mr_indicator_series,
    generate_pa_signal,
    build_pa_indicators,
    build_pa_strategy_summary,
)
from backtest import run_backtest
from utils import (
    plot_equity_curve,
    plot_drawdown,
    plot_signals_on_price,
    plot_signals_chart,
    annualisation_factor,
    calculate_returns,
)

st.set_page_config(
    page_title="Trading Research Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Custom CSS — sky-blue / dark-navy theme
# ---------------------------------------------------------------------------

def _inject_css() -> None:
    st.markdown("""
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── App shell ── */
[data-testid="stAppViewContainer"] > .main {
    background-color: #070d1a;
}
[data-testid="stHeader"] {
    background-color: #070d1a;
    border-bottom: 1px solid #0f2340;
}
[data-testid="stToolbar"] { right: 1rem; }
.main .block-container { padding-top: 1.75rem; padding-bottom: 3rem; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #0d1424;
    border-right: 1px solid #0f2340;
}
[data-testid="stSidebar"] .stMarkdown p { color: #64748b; font-size: 0.8rem; }
[data-testid="stSidebarContent"] { padding: 1.5rem 1rem; }

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    gap: 0;
    border-bottom: 1px solid #0f2340;
    background: transparent;
    margin-bottom: 1rem;
}
[data-testid="stTabs"] button[role="tab"] {
    color: #475569;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    padding: 0.6rem 1.4rem;
    font-size: 0.85rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    transition: color 0.2s, border-color 0.2s;
}
[data-testid="stTabs"] button[role="tab"]:hover { color: #7dd3fc; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #38bdf8;
    border-bottom: 2px solid #38bdf8;
    font-weight: 600;
}

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #0d1b2e;
    border: 1px solid #0f2340;
    border-top: 2px solid #1e3a5f;
    border-radius: 8px;
    padding: 1rem 1.25rem;
}
[data-testid="stMetricLabel"] > div {
    color: #64748b !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 500;
}
[data-testid="stMetricValue"] > div {
    color: #f1f5f9 !important;
    font-size: 1.4rem !important;
    font-weight: 700;
    letter-spacing: -0.02em;
}

/* ── Primary button ── */
button[data-testid="baseButton-primary"],
button[kind="primary"] {
    background: linear-gradient(135deg, #0284c7, #38bdf8) !important;
    border: none !important;
    color: #fff !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    border-radius: 6px !important;
    transition: opacity 0.2s !important;
}
button[data-testid="baseButton-primary"]:hover,
button[kind="primary"]:hover { opacity: 0.88 !important; }
button[data-testid="baseButton-primary"]:disabled,
button[kind="primary"]:disabled {
    background: #1e2d3d !important;
    color: #475569 !important;
}

/* ── Secondary button ── */
button[data-testid="baseButton-secondary"],
button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid #1e3a5f !important;
    color: #64748b !important;
    border-radius: 6px !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    background: #0d1b2e;
    border: 1px solid #0f2340 !important;
    border-radius: 8px;
}
[data-testid="stExpander"] summary {
    color: #94a3b8;
    font-weight: 500;
    font-size: 0.875rem;
}
[data-testid="stExpander"] summary:hover { color: #38bdf8; }

/* ── Alert boxes ── */
[data-testid="stInfo"] {
    background: rgba(56, 189, 248, 0.07) !important;
    border: 1px solid rgba(56, 189, 248, 0.25) !important;
    border-radius: 6px;
    color: #7dd3fc !important;
    font-size: 0.875rem;
}
[data-testid="stInfo"] svg { color: #38bdf8 !important; }
[data-testid="stWarning"] {
    background: rgba(245, 158, 11, 0.07) !important;
    border: 1px solid rgba(245, 158, 11, 0.25) !important;
    border-radius: 6px;
    font-size: 0.875rem;
}
[data-testid="stSuccess"] {
    background: rgba(34, 197, 94, 0.07) !important;
    border: 1px solid rgba(34, 197, 94, 0.25) !important;
    border-radius: 6px;
    font-size: 0.875rem;
}
[data-testid="stError"] {
    background: rgba(239, 68, 68, 0.07) !important;
    border: 1px solid rgba(239, 68, 68, 0.25) !important;
    border-radius: 6px;
    font-size: 0.875rem;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input {
    background: #0d1b2e !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 6px !important;
    color: #f1f5f9 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 0 2px rgba(56,189,248,0.15) !important;
}
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
    background: #0d1b2e !important;
    border-color: #1e3a5f !important;
}

/* ── Slider track colours ── */
[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-testid="stTickBarMax"] { color: #334155; }

/* ── Radio (family selector) ── */
[data-testid="stRadio"] label {
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    padding: 0.35rem 0.9rem;
    color: #64748b;
    font-size: 0.8rem;
    font-weight: 500;
    transition: all 0.15s;
    white-space: nowrap;
}
[data-testid="stRadio"] label:hover {
    border-color: #38bdf8;
    color: #7dd3fc;
}

/* ── DataFrames / tables ── */
[data-testid="stDataFrame"] {
    border: 1px solid #0f2340;
    border-radius: 8px;
    overflow: hidden;
}

/* ── Dividers ── */
hr { border-color: #0f2340 !important; opacity: 1 !important; }

/* ── Headings ── */
h1 { color: #f1f5f9 !important; font-weight: 700; letter-spacing: -0.03em; }
h2 { color: #e2e8f0 !important; font-weight: 700; letter-spacing: -0.02em; }
h3 {
    color: #cbd5e1 !important;
    font-weight: 600;
    font-size: 1rem !important;
    letter-spacing: 0.01em;
    text-transform: uppercase;
}

/* ── Caption / helper text ── */
[data-testid="stCaptionContainer"] p,
.stCaption { color: #334155 !important; font-size: 0.78rem !important; }

/* ── Sidebar title ── */
[data-testid="stSidebar"] h1 {
    font-size: 1rem !important;
    color: #38bdf8 !important;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* ── Spinner ── */
[data-testid="stSpinner"] { color: #38bdf8; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Strategy family definitions
# ---------------------------------------------------------------------------

_FAMILIES_META: Dict[str, Dict] = {
    "Trend / Momentum": {
        "description": (
            "Exploits price persistence — assets that have risen tend to continue rising. "
            "Edge comes from slow belief revision and herding among market participants. "
            "Performs well in sustained directional markets; generates frequent whipsaws "
            "in choppy, range-bound conditions. Requires wide stops to survive retracements."
        ),
        "coming_soon": False,
    },
    "Mean Reversion": {
        "description": (
            "Fades overextended moves, betting on return to a statistical equilibrium. "
            "Edge is strongest in liquid markets with mean-reverting microstructure. "
            "Fails during persistent trends driven by fundamental re-pricing — "
            "the strategy will repeatedly fade a move that never reverses."
        ),
        "coming_soon": False,
    },
    "Price Action": {
        "description": (
            "Trades directly from candle structure — no lagging indicators. "
            "Includes reversal patterns (Engulfing, Pin Bar), consolidation breakouts (Inside Bar), "
            "and session-based strategies (Opening Range Breakout). "
            "Signals fire on the bar they form; positions enter at the next open."
        ),
        "coming_soon": False,
    },
    "Volatility": {
        "description": (
            "Trades volatility directly — long vol during uncertainty, short vol in calm regimes. "
            "Typical instruments include options straddles and VIX futures. "
            "Requires derivatives pricing data beyond standard OHLCV feeds. "
            "Volatility-adjusted position sizing is already available for all signal strategies "
            "via the Execution Settings below."
        ),
        "coming_soon": True,
    },
    "Cross-Sectional / Relative Value": {
        "description": (
            "Ranks a universe of assets and goes long the strongest while shorting the weakest, "
            "regardless of absolute direction. Edge comes from diversification across many "
            "uncorrelated pair-wise bets. "
            "Requires simultaneous pricing of multiple assets — not yet supported in single-asset mode."
        ),
        "coming_soon": True,
    },
    "Carry / Yield": {
        "description": (
            "Harvests the yield or carry differential between assets — interest rate carry in FX, "
            "roll yield in commodity futures, bond carry. Produces steady income with periodic "
            "sharp drawdowns when funding regimes reverse. "
            "Requires fundamental rate data beyond price feeds."
        ),
        "coming_soon": True,
    },
}


def _family_strategies(family: str) -> list:
    return [n for n, r in STRATEGY_REGISTRY.items() if r.get("family") == family]


# ---------------------------------------------------------------------------
# Sidebar — data configuration only
# ---------------------------------------------------------------------------

def render_sidebar() -> Dict:
    st.sidebar.title("Trading Research Platform")
    st.sidebar.markdown("---")

    ticker = st.sidebar.text_input("Ticker Symbol", value="AAPL").upper().strip()

    asset_class = st.sidebar.selectbox(
        "Asset Class (reference)",
        list(ASSET_CLASS_EXAMPLES.keys()),
    )
    st.sidebar.caption(f"Examples: {ASSET_CLASS_EXAMPLES[asset_class]}")

    interval = st.sidebar.selectbox("Timeframe", ["1d", "4h", "1h", "15m", "5m"], index=0)

    _interval_limits = {"5m": 60, "15m": 60, "1h": 730, "4h": 730}
    if interval in _interval_limits:
        _max_days = _interval_limits[interval]
        _earliest = date.today() - timedelta(days=_max_days)
        st.sidebar.caption(
            f"⚠️ {interval} data: Yahoo Finance limits to {_max_days} days — "
            f"start date must be {_earliest} or later."
        )

    col1, col2 = st.sidebar.columns(2)
    _default_start = date.today() - timedelta(days=3 * 365)
    if interval in _interval_limits:
        _default_start = date.today() - timedelta(days=_interval_limits[interval] - 5)
    start_date = col1.date_input("Start", value=_default_start)
    end_date   = col2.date_input("End",   value=date.today())

    return {
        "ticker":     ticker,
        "interval":   interval,
        "start_date": start_date,
        "end_date":   end_date,
    }


# ---------------------------------------------------------------------------
# Shared UI helpers
# ---------------------------------------------------------------------------

def _render_sltp_controls(key_prefix: str, default_enabled: bool = True):
    """
    Render SL/TP enable toggle + customisation options.
    Returns (use_sltp, sl_pct_fixed, tp_ratio, trailing_sl, trail_atr_mult, vol_method).
    tp_ratio is None when the user disables the take-profit.
    """
    use_sltp = st.checkbox(
        "Enable Stop-Loss / Take-Profit",
        value=default_enabled,
        key=f"{key_prefix}_use_sltp",
        help=(
            "When ON: each trade has a hard SL and TP exit. "
            "SL is volatility-sized (≈1× ATR) unless a fixed % is set below. "
            "TP = SL × ratio. "
            "When OFF: exits are managed entirely by the signal or max-bars rule."
        ),
    )

    sl_pct_fixed:  Optional[float] = None
    tp_ratio:      Optional[float] = 2.0
    trailing_sl    = False
    trail_atr_mult = 1.0
    vol_method     = "Rolling Std"

    if use_sltp:
        # ── SL method ────────────────────────────────────────────────────────
        sl_type = st.radio(
            "SL method",
            ["Volatility-sized (ATR)", "Trailing ATR", "Fixed %"],
            horizontal=True,
            key=f"{key_prefix}_sl_type",
            help=(
                "Volatility-sized: fixed stop at ATR distance from entry.\n"
                "Trailing ATR: stop ratchets up (long) / down (short) as price moves in your favour — locks in profit.\n"
                "Fixed %: fixed stop at a set % from entry."
            ),
        )

        if sl_type == "Trailing ATR":
            trailing_sl    = True
            trail_atr_mult = st.number_input(
                "Trail width (ATR ×)",
                min_value=0.5,
                max_value=10.0,
                value=2.0,
                step=0.5,
                format="%.1f",
                key=f"{key_prefix}_trail_mult",
                help="Trailing stop distance = ATR × this multiplier. Higher = wider trail, fewer premature exits.",
            )
        elif sl_type == "Fixed %":
            sl_pct_fixed = st.number_input(
                "SL distance (%)",
                min_value=0.1,
                max_value=20.0,
                value=2.0,
                step=0.1,
                format="%.2f",
                key=f"{key_prefix}_sl_fixed",
                help="Fixed stop-loss distance as % of entry price (one side).",
            ) / 100.0

        # ── TP (always visible so widget key is stable) ───────────────────
        # Default off for trailing (the stop itself locks in profit);
        # default on for fixed stops.
        tp_default = sl_type != "Trailing ATR"
        use_tp = st.checkbox(
            "Use Take Profit",
            value=tp_default,
            key=f"{key_prefix}_use_tp",
            help="Adds a fixed take-profit target. With a trailing stop this is optional — the stop already locks in gains.",
        )
        if use_tp:
            tp_ratio = st.number_input(
                "TP : SL ratio",
                min_value=0.5,
                max_value=10.0,
                value=2.0,
                step=0.5,
                format="%.1f",
                key=f"{key_prefix}_tp_ratio",
                help="Take-profit distance = SL distance × this ratio. 2.0 = 2:1 R:R.",
            )
        else:
            tp_ratio = None

        # ── Volatility method ─────────────────────────────────────────────
        vol_method = st.radio(
            "Volatility method",
            ["Rolling Std", "ATR", "EWMA"],
            horizontal=True,
            key=f"{key_prefix}_vol_method",
            help=(
                "Rolling Std: 20-bar standard deviation of returns.\n"
                "ATR: 20-bar Average True Range ÷ entry price — captures gaps and wicks.\n"
                "EWMA: RiskMetrics exponentially weighted variance — more weight on recent moves."
            ),
        )

    return use_sltp, sl_pct_fixed, tp_ratio, trailing_sl, trail_atr_mult, vol_method


# ---------------------------------------------------------------------------
# Trend / Momentum Strategy Builder
# ---------------------------------------------------------------------------

def _render_signal_params(reg: Dict, key_prefix: str) -> Dict:
    """Render sliders / selectboxes for a TREND_SIGNAL_REGISTRY entry's params."""
    params    = reg.get("params", {})
    p_list    = list(params.items())
    if not p_list:
        return {}
    cols      = st.columns(min(len(p_list), 3))
    result    = {}
    for k, (pname, pmeta) in enumerate(p_list):
        with cols[k % len(cols)]:
            label = pmeta.get("label", pname)
            if pmeta["type"] is int:
                result[pname] = st.slider(
                    label, pmeta["min"], pmeta["max"], pmeta["default"],
                    key=f"{key_prefix}_{pname}",
                )
            elif pmeta["type"] is float:
                lo, hi = float(pmeta["min"]), float(pmeta["max"])
                if pmeta.get("widget") == "number_input":
                    result[pname] = st.number_input(
                        label, min_value=lo, max_value=hi,
                        value=float(pmeta["default"]),
                        step=pmeta.get("step", 0.001),
                        format=pmeta.get("format", "%.3f"),
                        key=f"{key_prefix}_{pname}",
                    )
                else:
                    raw_step = (hi - lo) / 100
                    if raw_step >= 0.1:
                        step = round(raw_step, 1)
                    elif raw_step >= 0.01:
                        step = round(raw_step, 2)
                    else:
                        step = round(raw_step, 3)
                    result[pname] = st.slider(
                        label, lo, hi, float(pmeta["default"]), step=step,
                        key=f"{key_prefix}_{pname}",
                    )
            elif pmeta["type"] is str:
                options = pmeta.get("options", [pmeta["default"]])
                result[pname] = st.selectbox(
                    label, options, key=f"{key_prefix}_{pname}",
                )
    return result


def render_trend_momentum_builder(data_cfg: Dict):
    """
    Full Trend/Momentum Strategy Builder UI.
    Returns (strategy_cfg dict, run_clicked bool).
    """
    # ── Section 1: Signal Type ────────────────────────────────────────────
    st.subheader("Signal Type")
    signal_names = list(TREND_SIGNAL_REGISTRY.keys())
    signal_type  = st.selectbox(
        "Signal", signal_names, key="tmb_signal_type", label_visibility="collapsed",
    )
    reg = TREND_SIGNAL_REGISTRY[signal_type]
    st.caption(reg["description"])

    signal_params = _render_signal_params(reg, key_prefix="tmb_sp")

    # ── Section 2: Entry Logic ────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Entry Logic")

    confirmation_bars = st.slider(
        "Confirmation bars (1 = enter immediately)", 1, 10, 1, key="tmb_confirmation_bars",
    )
    if confirmation_bars > 1:
        st.caption(
            f"Trade enters only after {confirmation_bars} consecutive bars confirming the signal direction."
        )

    # ── Section 3: Exit Logic ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Exit Logic")

    exit_type = st.radio(
        "Exit rule",
        ["signal", "fixed_bars"],
        horizontal=True,
        key="tmb_exit_type",
        format_func=lambda x: {
            "signal":     "Signal reversal",
            "fixed_bars": "Fixed bars held",
        }[x],
    )

    exit_params   = {}
    max_bars_held = None

    if exit_type == "signal":
        st.caption("Position closes when the signal flips to the opposite direction.")
    elif exit_type == "fixed_bars":
        max_bars_held           = st.slider("Max bars held", 1, 200, 20, key="tmb_max_bars_held")
        exit_params["max_bars"] = max_bars_held

    use_sltp, sl_pct_fixed, tp_ratio, trailing_sl, trail_atr_mult, vol_method = _render_sltp_controls("tmb", default_enabled=False)

    # ── Section 4: Filters ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Filters")

    filter_config = {}
    c1, c2, c3 = st.columns(3)
    long_only  = c1.checkbox("Long only",  key="tmb_long_only")
    short_only = c2.checkbox("Short only", key="tmb_short_only")
    if long_only and short_only:
        st.warning("Both Long only and Short only checked — no trades will fire.")
    filter_config["long_only"]  = long_only
    filter_config["short_only"] = short_only

    adx_filter = c3.checkbox("ADX strength filter", key="tmb_adx_filter")
    if adx_filter:
        filter_config["adx_min"]    = st.slider("Minimum ADX", 10, 50, 25, key="tmb_adx_min")
        filter_config["adx_period"] = 14

    trend_filter_on     = st.checkbox("Higher-TF trend filter", key="tmb_trend_filter")
    trend_filter_period = 50
    if trend_filter_on:
        trend_filter_period = st.slider("Trend MA period", 10, 200, 50, key="tmb_trend_period")
    filter_config["trend_filter"] = trend_filter_on

    # ── Section 5: Execution ──────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Execution")

    c1, c2 = st.columns(2)
    commission_pct = c1.number_input(
        "Commission (% round trip)", min_value=0.0, max_value=2.0, value=0.0,
        step=0.001, format="%.3f", key="tmb_commission",
        help="e.g. 0.1 = 0.1% for equities, 0.002 = 0.002% for FX/futures",
    ) / 100.0
    slippage_pct = c2.number_input(
        "Slippage (% round trip)", min_value=0.0, max_value=1.0, value=0.0,
        step=0.001, format="%.3f", key="tmb_slippage",
        help="e.g. 0.05 = 0.05% for equities, 0.001 = 0.001% for FX",
    ) / 100.0

    vol_target_on = st.checkbox("Volatility targeting", value=False, key="tmb_vol_target_on")
    vol_target: Optional[float] = None
    if vol_target_on:
        vol_target = st.slider("Target annualised vol (%)", 5, 50, 15, key="tmb_vol_target") / 100.0

    # ── Section 6: Strategy Summary ───────────────────────────────────────
    st.markdown("---")
    st.subheader("Strategy Summary")
    risk_config = {
        "commission_pct": commission_pct,
        "slippage_pct":   slippage_pct,
        "vol_target":     vol_target,
    }
    summary = build_strategy_summary(
        signal_type, exit_type, filter_config, risk_config,
        signal_params=signal_params, exit_params=exit_params,
        confirmation_bars=confirmation_bars,
    )
    st.code(summary, language=None)

    # ── Run button ────────────────────────────────────────────────────────
    st.markdown("---")
    run = st.button(
        "Run Backtest", type="primary", use_container_width=True, key="tmb_run",
    )

    strategy_cfg = {
        "mode":               "trend_builder",
        "signal_type":        signal_type,
        "signal_params":      signal_params,
        "confirmation_bars":  confirmation_bars,
        "exit_type":          exit_type,
        "exit_params":        exit_params,
        "max_bars_held":      max_bars_held,
        "use_sltp":           use_sltp,
        "sl_pct_fixed":       sl_pct_fixed,
        "tp_ratio":           tp_ratio,
        "trailing_sl":        trailing_sl,
        "trail_atr_mult":     trail_atr_mult,
        "vol_method":         vol_method,
        "filter_config":      filter_config,
        "trend_filter_on":    trend_filter_on,
        "trend_filter_period": trend_filter_period,
        "commission_pct":     commission_pct,
        "slippage_pct":       slippage_pct,
        "vol_target":         vol_target,
        # Compatibility: main() uses selected_strategies to check "anything configured?"
        "selected_strategies": ["_trend_builder"],
        "strategy_params":    {},
        "combo_method":       "majority_vote",
        "weights":            None,
        "combo_threshold":    0.5,
    }
    return strategy_cfg, run


# ---------------------------------------------------------------------------
# Mean Reversion Strategy Builder
# ---------------------------------------------------------------------------

def render_mean_reversion_builder(data_cfg: Dict):
    """
    Full Mean Reversion Strategy Builder UI.
    Returns (strategy_cfg dict, run_clicked bool).
    """
    st.info(
        "Mean reversion strategies exploit temporary deviations from fair value. "
        "They perform best in range-bound markets and tend to struggle during "
        "strong directional trends."
    )

    # ── Section 1: Signal Type ────────────────────────────────────────────
    st.subheader("Signal Type")
    signal_names = list(MEAN_REVERSION_SIGNAL_REGISTRY.keys())
    signal_type  = st.selectbox(
        "Signal", signal_names, key="mrb_signal_type", label_visibility="collapsed",
    )
    reg = MEAN_REVERSION_SIGNAL_REGISTRY[signal_type]
    st.caption(reg["description"])

    signal_params = _render_signal_params(reg, key_prefix="mrb_sp")

    # ── Section 2: Entry Logic ────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Entry Logic")

    confirmation_bars = st.slider(
        "Confirmation bars (1 = enter immediately)", 1, 10, 1, key="mrb_conf_bars",
    )
    if confirmation_bars > 1:
        st.caption(
            f"Trade enters only after {confirmation_bars} consecutive bars confirming the signal direction."
        )

    wait_for_reversal = st.checkbox("Wait for indicator to start reversing", key="mrb_wait_reversal")
    if wait_for_reversal:
        st.caption(
            "Holds off entry until the indicator ticks in the right direction — "
            "reduces the risk of entering while the move is still running against you."
        )

    # ── Section 3: Exit Logic ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Exit Logic")

    exit_type = st.radio(
        "Exit rule",
        ["mean", "opposite", "fixed_bars"],
        horizontal=True,
        key="mrb_exit_type",
        format_func=lambda x: {
            "mean":       "Mean reversion",
            "opposite":   "Signal reversal",
            "fixed_bars": "Fixed bars held",
        }[x],
    )
    exit_hint = {
        "mean":       "Exit when signal returns to neutral — the trade closes once the reversion is complete.",
        "opposite":   "Hold until a signal in the opposite direction fires.",
        "fixed_bars": "Exit after a fixed number of bars regardless of signal.",
    }
    st.caption(exit_hint[exit_type])

    exit_params      = {}
    close_on_neutral = False
    max_bars_held    = None

    if exit_type == "mean":
        close_on_neutral = True
    elif exit_type == "fixed_bars":
        max_bars_held          = st.slider("Max bars held", 1, 100, 10, key="mrb_max_bars")
        exit_params["max_bars"] = max_bars_held

    # SL/TP off by default for MR — ATR stops fire before reversions complete
    st.caption("SL/TP: disabled by default for mean reversion (signal exit threshold is the risk control).")
    use_sltp, sl_pct_fixed, tp_ratio, trailing_sl, trail_atr_mult, vol_method = _render_sltp_controls("mrb", default_enabled=False)

    # ── Section 4: Filters ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Filters")
    st.caption("Mean reversion works best in low-trend (ranging) environments.")

    filter_config = {}

    c1, c2, c3 = st.columns(3)
    long_only     = c1.checkbox("Long only",              key="mrb_long_only")
    short_only    = c2.checkbox("Short only",             key="mrb_short_only")
    adx_range_on  = c3.checkbox("Ranging market filter",  key="mrb_adx_range")
    if long_only and short_only:
        st.warning("Both Long only and Short only checked — no trades will fire.")
    filter_config["long_only"]  = long_only
    filter_config["short_only"] = short_only

    if adx_range_on:
        filter_config["adx_max"]    = st.slider("Maximum ADX", 10, 50, 25, key="mrb_adx_max")
        filter_config["adx_period"] = 14

    vol_filter_on = st.checkbox("Low-volatility filter", key="mrb_vol_filter")
    if vol_filter_on:
        filter_config["vol_max"] = st.slider(
            "Max annualised vol (%)", 5, 100, 40, key="mrb_vol_max",
        ) / 100.0

    # ── Section 5: Execution ──────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Execution")

    c1, c2 = st.columns(2)
    commission_pct = c1.number_input(
        "Commission (% round trip)", min_value=0.0, max_value=2.0, value=0.0,
        step=0.001, format="%.3f", key="mrb_commission",
        help="e.g. 0.1 = 0.1% for equities, 0.002 = 0.002% for FX/futures",
    ) / 100.0
    slippage_pct = c2.number_input(
        "Slippage (% round trip)", min_value=0.0, max_value=1.0, value=0.0,
        step=0.001, format="%.3f", key="mrb_slippage",
        help="e.g. 0.05 = 0.05% for equities, 0.001 = 0.001% for FX",
    ) / 100.0

    vol_target_on = st.checkbox("Volatility targeting", value=False, key="mrb_vol_target_on")
    vol_target: Optional[float] = None
    if vol_target_on:
        vol_target = st.slider("Target annualised vol (%)", 5, 50, 10, key="mrb_vol_target") / 100.0

    # ── Section 6: Strategy Summary ───────────────────────────────────────
    st.markdown("---")
    st.subheader("Strategy Summary")
    risk_config = {
        "commission_pct": commission_pct,
        "slippage_pct":   slippage_pct,
        "vol_target":     vol_target,
    }
    summary = build_mr_strategy_summary(
        signal_type, exit_type, filter_config, risk_config,
        signal_params=signal_params, exit_params=exit_params,
        confirmation_bars=confirmation_bars,
        wait_for_reversal=wait_for_reversal,
    )
    st.code(summary, language=None)

    # ── Run button ────────────────────────────────────────────────────────
    st.markdown("---")
    run = st.button(
        "Run Backtest", type="primary", use_container_width=True, key="mrb_run",
    )

    strategy_cfg = {
        "mode":               "mr_builder",
        "signal_type":        signal_type,
        "signal_params":      signal_params,
        "confirmation_bars":  confirmation_bars,
        "wait_for_reversal":  wait_for_reversal,
        "exit_type":          exit_type,
        "exit_params":        exit_params,
        "close_on_neutral":   close_on_neutral,
        "max_bars_held":      max_bars_held,
        "use_sltp":          use_sltp,
        "sl_pct_fixed":      sl_pct_fixed,
        "tp_ratio":          tp_ratio,
        "trailing_sl":       trailing_sl,
        "trail_atr_mult":    trail_atr_mult,
        "vol_method":        vol_method,
        "filter_config":     filter_config,
        "commission_pct":    commission_pct,
        "slippage_pct":      slippage_pct,
        "vol_target":        vol_target,
        # Compatibility
        "selected_strategies": ["_mr_builder"],
        "strategy_params":   {},
        "combo_method":      "majority_vote",
        "weights":           None,
        "combo_threshold":   0.5,
        "trend_filter_on":   False,
        "trend_filter_period": 50,
    }
    return strategy_cfg, run


# ---------------------------------------------------------------------------
# Price Action Strategy Builder
# ---------------------------------------------------------------------------

def render_price_action_builder(data_cfg: Dict):
    """
    Full Price Action Strategy Builder UI.
    Returns (strategy_cfg dict, run_clicked bool).
    """
    st.info(
        "Price action strategies trade directly from candle structure — no lagging indicators. "
        "Patterns fire event signals on the bar they form; the backtest enters at the next open."
    )

    # ── Section 1: Pattern ────────────────────────────────────────────────
    st.subheader("Pattern")
    signal_names = list(PRICE_ACTION_SIGNAL_REGISTRY.keys())
    signal_type  = st.selectbox(
        "Pattern", signal_names, key="pab_signal_type", label_visibility="collapsed",
    )
    reg = PRICE_ACTION_SIGNAL_REGISTRY[signal_type]
    st.caption(reg["description"])

    if signal_type == "Opening Range Breakout":
        if data_cfg["interval"] == "1d":
            st.warning(
                "Opening Range Breakout requires intraday data (5m, 15m, 1h). "
                "No signals will fire on daily bars — switch the timeframe in the sidebar."
            )
        elif data_cfg["interval"] == "4h":
            st.info(
                "4h bars give only ~2 bars per session. "
                "Consider 1h or shorter for more meaningful opening ranges."
            )

    signal_params = _render_signal_params(reg, key_prefix="pab_sp")

    if signal_type == "Opening Range Breakout" and signal_params:
        rb       = signal_params.get("range_bars", 6)
        interval = data_cfg["interval"]
        _mins    = {"5m": 5, "15m": 15, "1h": 60, "4h": 240}
        if interval in _mins:
            st.caption(
                f"{rb} bars × {_mins[interval]} min = {rb * _mins[interval]} min opening range"
            )

    # ── Section 2: Entry Logic ────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Entry Logic")

    confirmation_bars = st.slider(
        "Confirmation bars (1 = enter immediately)", 1, 10, 1, key="pab_confirmation_bars",
    )
    if confirmation_bars > 1:
        st.caption(
            f"Trade enters only after {confirmation_bars} consecutive bars confirming the signal direction."
        )

    # ── Section 3: Exit Logic ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Exit Logic")

    exit_type = st.radio(
        "Exit rule",
        ["signal", "fixed_bars"],
        horizontal=True,
        key="pab_exit_type",
        format_func=lambda x: {
            "signal":     "Signal reversal",
            "fixed_bars": "Fixed bars held",
        }[x],
    )

    exit_params   = {}
    max_bars_held = None

    if exit_type == "signal":
        st.caption("Position closes when the signal flips to the opposite direction.")
    elif exit_type == "fixed_bars":
        max_bars_held           = st.slider("Max bars held", 1, 200, 20, key="pab_max_bars_held")
        exit_params["max_bars"] = max_bars_held
        if signal_type == "Opening Range Breakout":
            interval = data_cfg["interval"]
            _bars_per_session = {"5m": 78, "15m": 26, "1h": 7, "4h": 2}
            if interval in _bars_per_session:
                st.caption(
                    f"Tip: ~{_bars_per_session[interval]} bars per session on {interval} data. "
                    f"Set max bars held ≤ this to stay intraday."
                )

    use_sltp, sl_pct_fixed, tp_ratio, trailing_sl, trail_atr_mult, vol_method = _render_sltp_controls(
        "pab", default_enabled=True
    )

    # ── Section 4: Filters ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Filters")

    filter_config = {}
    c1, c2 = st.columns(2)
    long_only  = c1.checkbox("Long only",  key="pab_long_only")
    short_only = c2.checkbox("Short only", key="pab_short_only")
    if long_only and short_only:
        st.warning("Both Long only and Short only checked — no trades will fire.")
    filter_config["long_only"]  = long_only
    filter_config["short_only"] = short_only

    # ── Section 5: Execution ──────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Execution")

    c1, c2 = st.columns(2)
    commission_pct = c1.number_input(
        "Commission (% round trip)", min_value=0.0, max_value=2.0, value=0.0,
        step=0.001, format="%.3f", key="pab_commission",
        help="e.g. 0.1 = 0.1% for equities, 0.002 = 0.002% for FX/futures",
    ) / 100.0
    slippage_pct = c2.number_input(
        "Slippage (% round trip)", min_value=0.0, max_value=1.0, value=0.0,
        step=0.001, format="%.3f", key="pab_slippage",
        help="e.g. 0.05 = 0.05% for equities, 0.001 = 0.001% for FX",
    ) / 100.0

    vol_target_on = st.checkbox("Volatility targeting", value=False, key="pab_vol_target_on")
    vol_target: Optional[float] = None
    if vol_target_on:
        vol_target = st.slider("Target annualised vol (%)", 5, 50, 15, key="pab_vol_target") / 100.0

    # ── Section 6: Strategy Summary ───────────────────────────────────────
    st.markdown("---")
    st.subheader("Strategy Summary")
    risk_config = {
        "commission_pct": commission_pct,
        "slippage_pct":   slippage_pct,
        "vol_target":     vol_target,
    }
    summary = build_pa_strategy_summary(
        signal_type, exit_type, filter_config, risk_config,
        signal_params=signal_params, exit_params=exit_params,
        confirmation_bars=confirmation_bars,
    )
    st.code(summary, language=None)

    # ── Run button ────────────────────────────────────────────────────────
    st.markdown("---")
    run = st.button(
        "Run Backtest", type="primary", use_container_width=True, key="pab_run",
    )

    strategy_cfg = {
        "mode":                "pa_builder",
        "signal_type":         signal_type,
        "signal_params":       signal_params,
        "confirmation_bars":   confirmation_bars,
        "exit_type":           exit_type,
        "exit_params":         exit_params,
        "max_bars_held":       max_bars_held,
        "use_sltp":            use_sltp,
        "sl_pct_fixed":        sl_pct_fixed,
        "tp_ratio":            tp_ratio,
        "trailing_sl":         trailing_sl,
        "trail_atr_mult":      trail_atr_mult,
        "vol_method":          vol_method,
        "filter_config":       filter_config,
        "commission_pct":      commission_pct,
        "slippage_pct":        slippage_pct,
        "vol_target":          vol_target,
        "selected_strategies": ["_pa_builder"],
        "strategy_params":     {},
        "combo_method":        "majority_vote",
        "weights":             None,
        "combo_threshold":     0.5,
        "trend_filter_on":     False,
        "trend_filter_period": 50,
    }
    return strategy_cfg, run


# ---------------------------------------------------------------------------
# Tab 1 — Strategy Builder
# ---------------------------------------------------------------------------

def tab_strategy_builder(data_cfg: Dict):
    """
    Renders the Strategy Builder UI.
    Returns (strategy_cfg dict, run_clicked bool).
    """
    st.subheader("Strategy Family")

    family = st.radio(
        "family",
        list(_FAMILIES_META.keys()),
        horizontal=True,
        key="sb_family",
        label_visibility="collapsed",
    )

    meta = _FAMILIES_META[family]
    st.info(meta["description"])

    # ── Dedicated builders for configurable families ──────────────────────
    if family == "Trend / Momentum":
        return render_trend_momentum_builder(data_cfg)
    if family == "Mean Reversion":
        return render_mean_reversion_builder(data_cfg)
    if family == "Price Action":
        return render_price_action_builder(data_cfg)

    # ── All other families: generic multi-strategy picker ─────────────────
    selected_strategies: list = []
    strategy_params: Dict[str, Dict] = {}

    if meta["coming_soon"]:
        st.warning("No signal strategies available for this family yet.")
    else:
        avail = _family_strategies(family)
        if not avail:
            st.warning("No strategies registered for this family.")
        else:
            st.markdown("**Strategies**")
            selected_strategies = st.multiselect(
                "strategies",
                avail,
                default=[avail[0]],
                key=f"sb_strategies_{family}",
                label_visibility="collapsed",
            )

            for name in selected_strategies:
                reg = STRATEGY_REGISTRY[name]
                with st.expander(f"{name} — Parameters", expanded=len(selected_strategies) == 1):
                    p    = {}
                    cols = st.columns(min(len(reg["params"]), 3))
                    for k, (pname, pmeta) in enumerate(reg["params"].items()):
                        with cols[k % len(cols)]:
                            if pmeta["type"] is int:
                                p[pname] = st.slider(
                                    pname,
                                    min_value=pmeta["min"],
                                    max_value=pmeta["max"],
                                    value=pmeta["default"],
                                    key=f"sb_{name}_{pname}",
                                )
                            else:
                                p[pname] = st.slider(
                                    pname,
                                    min_value=float(pmeta["min"]),
                                    max_value=float(pmeta["max"]),
                                    value=float(pmeta["default"]),
                                    step=0.5,
                                    key=f"sb_{name}_{pname}",
                                )
                    strategy_params[name] = p

    # Signal combination — only relevant when >1 strategy is active
    combo_method    = "majority_vote"
    weights         = None
    combo_threshold = 0.5

    if len(selected_strategies) > 1:
        st.markdown("---")
        st.subheader("Signal Combination")
        combo_method = st.selectbox(
            "Method",
            ["majority_vote", "weighted", "threshold"],
            key="sb_combo_method",
            help=(
                "majority_vote: long if more strategies are long than short. "
                "weighted: each strategy contributes a scaled vote. "
                "threshold: require stronger consensus before opening a position."
            ),
        )
        if combo_method == "weighted":
            st.caption("Weights are normalised — only relative values matter.")
            wcols = st.columns(len(selected_strategies))
            weights = {}
            for k, name in enumerate(selected_strategies):
                weights[name] = wcols[k].number_input(
                    name, min_value=0.0, value=1.0, step=0.1, key=f"sb_w_{name}"
                )
        elif combo_method == "threshold":
            combo_threshold = st.slider(
                "Consensus threshold", 0.1, 1.0, 0.5, key="sb_threshold",
                help="Fraction of strategies that must agree before a signal is taken.",
            )

    st.markdown("---")
    st.subheader("Filters")

    c1, c2 = st.columns([1, 2])
    trend_filter_on = c1.checkbox(
        "Higher-TF trend filter",
        value=False,
        key="sb_trend_filter",
        help=(
            "Zero out signals that oppose the higher-timeframe trend. "
            "Trend = price above/below a moving average on the next timeframe up."
        ),
    )
    trend_filter_period = 50
    if trend_filter_on:
        trend_filter_period = c2.slider("Trend MA period", 10, 200, 50, key="sb_trend_period")

    st.markdown("---")
    st.subheader("Execution")

    c1, c2 = st.columns(2)
    commission_pct = c1.number_input(
        "Commission (% round trip)", min_value=0.0, max_value=2.0, value=0.1,
        step=0.001, format="%.3f", key="sb_commission",
        help="e.g. 0.1 = 0.1% for equities, 0.002 = 0.002% for FX/futures",
    ) / 100.0
    slippage_pct = c2.number_input(
        "Slippage (% round trip)", min_value=0.0, max_value=1.0, value=0.0,
        step=0.001, format="%.3f", key="sb_slippage",
        help="e.g. 0.05 = 0.05% for equities, 0.001 = 0.001% for FX",
    ) / 100.0

    use_sltp, sl_pct_fixed, tp_ratio, trailing_sl, trail_atr_mult, vol_method = _render_sltp_controls("sb", default_enabled=True)

    vol_target_on = st.checkbox(
        "Volatility targeting",
        value=False,
        key="sb_vol_target_on",
        help=(
            "Size each position so the portfolio annualised vol targets a fixed level, "
            "rather than risking a fixed 2% per trade."
        ),
    )
    vol_target: Optional[float] = None
    if vol_target_on:
        vol_target = st.slider(
            "Target annualised vol (%)", 5, 50, 15, key="sb_vol_target",
        ) / 100.0

    st.markdown("---")

    run = st.button(
        "Run Backtest",
        type="primary",
        use_container_width=True,
        key="sb_run",
        disabled=not selected_strategies,
    )

    return {
        "selected_strategies": selected_strategies,
        "strategy_params":     strategy_params,
        "combo_method":        combo_method,
        "weights":             weights,
        "combo_threshold":     combo_threshold,
        "trend_filter_on":     trend_filter_on,
        "trend_filter_period": trend_filter_period,
        "commission_pct":      commission_pct,
        "slippage_pct":        slippage_pct,
        "vol_target":          vol_target,
        "use_sltp":            use_sltp,
        "sl_pct_fixed":        sl_pct_fixed,
        "tp_ratio":            tp_ratio,
        "trailing_sl":         trailing_sl,
        "trail_atr_mult":      trail_atr_mult,
    }, run


# ---------------------------------------------------------------------------
# Tab 2 — Signal Diagnostics
# ---------------------------------------------------------------------------

_MAX_CHART_BARS = 2_500  # above this Plotly serialisation + browser rendering gets slow


def tab_signal_diagnostics(
    prices: pd.DataFrame,
    individual_signals: Dict,
    combined: pd.Series,
    trade_log: Optional[pd.DataFrame],
    indicator_overlays: Optional[list],
    interval: str,
):
    # Cap candles for rendering performance — backtest already ran on all bars
    total_bars = len(prices)
    if total_bars > _MAX_CHART_BARS:
        chart_prices   = prices.iloc[-_MAX_CHART_BARS:]
        chart_combined = combined.reindex(chart_prices.index)
        cutoff         = chart_prices.index[0]
        chart_tl = (
            trade_log[trade_log["Entry Date"] >= cutoff].copy()
            if trade_log is not None and not trade_log.empty and "Entry Date" in trade_log.columns
            else trade_log
        )
        chart_overlays = []
        for o in (indicator_overlays or []):
            trimmed = []
            for t in o["traces"]:
                if hasattr(t, "x") and t.x is not None:
                    # Normalize both sides to tz-naive for comparison.
                    # Plotly traces may store x as tz-naive or tz-aware depending on
                    # the pandas version and how the index was assigned; cutoff comes
                    # from prices.index which may be UTC-aware on intraday data.
                    x_s = pd.Series(t.x)
                    if pd.api.types.is_datetime64_any_dtype(x_s) and x_s.dt.tz is not None:
                        x_s = x_s.dt.tz_convert(None)   # UTC-aware → tz-naive UTC
                    cutoff_cmp = cutoff.replace(tzinfo=None)
                    mask = x_s >= cutoff_cmp
                    t.x  = pd.Series(t.x)[mask.values].values
                    t.y  = pd.Series(t.y)[mask.values].values
                trimmed.append(t)
            chart_overlays.append({**o, "traces": trimmed})
        st.caption(
            f"Chart shows the last {_MAX_CHART_BARS:,} of {total_bars:,} bars. "
            f"All {total_bars:,} bars were used for backtest metrics."
        )
    else:
        chart_prices   = prices
        chart_combined = combined
        chart_tl       = trade_log
        chart_overlays = indicator_overlays

    fig = plot_signals_on_price(
        chart_prices, chart_combined,
        title="Price + Trade Entries",
        trade_log=chart_tl,
        indicator_overlays=chart_overlays,
        interval=interval,
    )
    fig.update_layout(height=900)
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    if trade_log is not None and not trade_log.empty and "Return (%)" in trade_log.columns:
        wins       = trade_log[trade_log["Return (%)"] > 0]["Return (%)"]
        losses     = trade_log[trade_log["Return (%)"] <= 0]["Return (%)"]
        gross_win  = wins.sum()
        gross_loss = abs(losses.sum())
        pf         = round(gross_win / gross_loss, 2) if gross_loss > 0 else float("inf")
        pf_str     = f"{pf:.2f}" if pf != float("inf") else "∞"

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Trades",  len(trade_log))
        c2.metric("Win Rate",      f"{len(wins) / len(trade_log) * 100:.1f}%")
        c3.metric("Avg Win",       f"{wins.mean():.2f}%"   if len(wins)   else "—")
        c4.metric("Avg Loss",      f"{losses.mean():.2f}%" if len(losses) else "—")
        c5.metric("Profit Factor", pf_str)

    if len(individual_signals) > 1:
        st.markdown("---")
        st.subheader("Individual Strategy Signals")
        st.caption(
            "Raw signal output (1 = long, −1 = short, 0 = flat) for each strategy. "
            "Use this to identify where strategies agree or diverge."
        )
        fig_sigs = plot_signals_chart(
            pd.DataFrame(individual_signals), title="Strategy Signals"
        )
        st.plotly_chart(fig_sigs, use_container_width=True)


# ---------------------------------------------------------------------------
# Regime analysis helper
# ---------------------------------------------------------------------------

def compute_regime_stats(
    returns: pd.Series,
    prices: pd.DataFrame,
    trade_log: Optional[pd.DataFrame],
    interval: str,
    vol_window: int = 20,
) -> pd.DataFrame:
    periods_per_year = annualisation_factor(interval)
    rolling_vol      = prices["Close"].pct_change().rolling(vol_window).std()
    median_vol       = rolling_vol.median()

    try:
        adx = ta.trend.ADXIndicator(
            prices["High"], prices["Low"], prices["Close"], window=14
        ).adx()
    except Exception:
        adx = pd.Series(np.nan, index=prices.index)

    regimes = {
        "High Volatility":   rolling_vol > median_vol,
        "Low Volatility":    rolling_vol <= median_vol,
        "Trending (ADX>25)": adx > 25.0,
        "Ranging (ADX≤25)":  adx <= 25.0,
    }

    rows = []
    for name, mask in regimes.items():
        mask      = mask.reindex(returns.index).fillna(False)
        r         = returns[mask].dropna()
        pct_bars  = round(float(mask.sum()) / len(mask) * 100, 1) if len(mask) else 0.0
        strat_ret = round(float((1 + r).prod() - 1) * 100, 2)    if len(r) > 0  else 0.0
        std       = float(r.std())
        sharpe    = round(float(r.mean() / std * np.sqrt(periods_per_year)), 2) if std > 0 else 0.0

        trades_n = 0
        win_rate = "—"
        if trade_log is not None and not trade_log.empty and "Entry Date" in trade_log.columns:
            in_regime = set(mask[mask].index)
            subset    = trade_log[trade_log["Entry Date"].isin(in_regime)]
            trades_n  = len(subset)
            if trades_n > 0 and "Return (%)" in subset.columns:
                win_rate = f"{round((subset['Return (%)'] > 0).sum() / trades_n * 100, 1)}%"

        rows.append({
            "Regime":     name,
            "Bars (%)":   pct_bars,
            "Return (%)": strat_ret,
            "Sharpe":     sharpe,
            "Trades":     trades_n,
            "Win Rate":   win_rate,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tab 3 — Backtest Results
# ---------------------------------------------------------------------------

def tab_backtest_results(result: Dict, prices: pd.DataFrame, interval: str = "1d"):
    metrics   = result["metrics"]
    trade_log = result["trade_log"]

    n_trades = metrics.get("Number of Trades", 0)
    sharpe   = metrics.get("Sharpe Ratio", 0)

    if n_trades < 10:
        st.warning(f"Only {n_trades} trades — results may not be statistically meaningful.")
    if sharpe > 5:
        st.warning(f"Sharpe of {sharpe} is unusually high and may indicate overfitting or a data error.")
    if not trade_log.empty:
        dirs = trade_log["Direction"].value_counts()
        if len(dirs) == 1:
            only  = dirs.index[0]
            other = "Short" if only == "Long" else "Long"
            st.warning(f"All trades are {only} — no {other} signals were generated.")

    st.subheader("Performance Metrics")
    _row1 = [
        "Total Return (%)", "Annualised Return (%)", "Max Drawdown (%)",
        "Max DD Duration (bars)", "Sharpe Ratio", "Sortino Ratio", "Calmar Ratio",
    ]
    _row2 = [
        "Win Rate (%)", "Long Win Rate (%)", "Short Win Rate (%)",
        "Exposure (%)", "Number of Trades",
    ]
    row1 = {k: metrics[k] for k in _row1 if k in metrics}
    row2 = {k: metrics[k] for k in _row2 if k in metrics}

    for row in (row1, row2):
        cols = st.columns(len(row))
        for col, (k, v) in zip(cols, row.items()):
            col.metric(k, v)

    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        bh = (1 + calculate_returns(prices["Close"], log=False)).cumprod()
        st.plotly_chart(
            plot_equity_curve(result["equity_curve"], benchmark=bh, title="Equity Curve"),
            use_container_width=True,
        )
    with c2:
        st.plotly_chart(
            plot_drawdown(result["equity_curve"]),
            use_container_width=True,
        )

    st.markdown("---")
    st.subheader("Regime Analysis")
    st.caption(
        "High/Low Volatility: split at median 20-bar rolling std. "
        "Trending/Ranging: split at ADX = 25. "
        "Trades counted by entry bar."
    )
    try:
        regime_df = compute_regime_stats(result["returns"], prices, trade_log, interval)
        st.dataframe(regime_df.set_index("Regime"), use_container_width=True)
    except Exception as e:
        st.warning(f"Regime analysis unavailable: {e}")


# ---------------------------------------------------------------------------
# Tab 4 — Trade Analysis
# ---------------------------------------------------------------------------

def tab_trade_analysis(result: Dict):
    trade_log = result["trade_log"]

    if trade_log.empty:
        st.info("No completed trades in this period.")
        return

    st.subheader("Trade Log")
    st.dataframe(trade_log, use_container_width=True)

    if "Return (%)" not in trade_log.columns:
        return

    st.markdown("---")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Return Distribution")
        fig_ret = go.Figure()
        fig_ret.add_trace(go.Histogram(
            x=trade_log["Return (%)"],
            nbinsx=40,
            marker_color="#60a5fa",
            opacity=0.85,
        ))
        mean_ret = trade_log["Return (%)"].mean()
        fig_ret.add_vline(x=0,        line_dash="dash", line_color="#94a3b8", line_width=1.5)
        fig_ret.add_vline(
            x=mean_ret, line_dash="dot", line_color="#f59e0b", line_width=1.5,
            annotation_text=f"Mean {mean_ret:.2f}%",
            annotation_position="top right",
        )
        fig_ret.update_layout(
            template="plotly_dark",
            xaxis_title="Return (%)",
            yaxis_title="Count",
            showlegend=False,
            height=340,
        )
        st.plotly_chart(fig_ret, use_container_width=True)

    with c2:
        if "Bars Held" in trade_log.columns:
            st.subheader("Trade Duration")
            fig_dur = go.Figure()
            fig_dur.add_trace(go.Histogram(
                x=trade_log["Bars Held"],
                nbinsx=30,
                marker_color="#f59e0b",
                opacity=0.85,
            ))
            fig_dur.update_layout(
                template="plotly_dark",
                xaxis_title="Bars Held",
                yaxis_title="Count",
                showlegend=False,
                height=340,
            )
            st.plotly_chart(fig_dur, use_container_width=True)

    if "MAE (%)" in trade_log.columns and "MFE (%)" in trade_log.columns:
        mae_mfe = trade_log.dropna(subset=["MAE (%)", "MFE (%)"])
        if not mae_mfe.empty:
            st.markdown("---")
            st.subheader("MAE vs MFE")
            st.caption(
                "Each point is one trade. Green = win, red = loss. "
                "MAE = furthest the trade moved against you before closing. "
                "MFE = furthest it moved in your favour. "
                "Points above the diagonal had more upside potential than downside risk."
            )
            colors = ["#22c55e" if r > 0 else "#ef4444" for r in mae_mfe["Return (%)"]]
            max_val = max(mae_mfe["MAE (%)"].max(), mae_mfe["MFE (%)"].max()) * 1.1
            fig_mf = go.Figure()
            fig_mf.add_trace(go.Scatter(
                x=[0, max_val], y=[0, max_val],
                mode="lines",
                line=dict(color="#475569", width=1, dash="dash"),
                showlegend=False,
            ))
            fig_mf.add_trace(go.Scatter(
                x=mae_mfe["MAE (%)"],
                y=mae_mfe["MFE (%)"],
                mode="markers",
                marker=dict(
                    color=colors, size=7, opacity=0.75,
                    line=dict(width=0.5, color="#0f172a"),
                ),
                text=mae_mfe.apply(
                    lambda r: (
                        f"Return: {r['Return (%)']:.2f}% | "
                        f"{r.get('Direction', '')} | "
                        f"{r.get('Exit Reason', '')}"
                    ),
                    axis=1,
                ),
                hoverinfo="text+x+y",
                name="Trades",
            ))
            fig_mf.update_layout(
                template="plotly_dark",
                xaxis_title="MAE (%)",
                yaxis_title="MFE (%)",
                height=450,
            )
            st.plotly_chart(fig_mf, use_container_width=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    _inject_css()
    data_cfg = render_sidebar()

    # Invalidate cached backtest when the data config changes
    _data_sig = (
        data_cfg["ticker"],
        data_cfg["interval"],
        str(data_cfg["start_date"]),
        str(data_cfg["end_date"]),
    )
    if st.session_state.get("_data_sig") != _data_sig:
        for _k in [
            "backtest_result", "prices", "combined_signal",
            "individual_signals", "indicator_overlays", "run_label",
        ]:
            st.session_state.pop(_k, None)
        st.session_state["_data_sig"] = _data_sig

    tab1, tab2, tab3, tab4 = st.tabs([
        "Strategy Builder",
        "Signal Diagnostics",
        "Backtest Results",
        "Trade Analysis",
    ])

    with tab1:
        strategy_cfg, run = tab_strategy_builder(data_cfg)

        if run and strategy_cfg["selected_strategies"]:
            try:
                with st.spinner(f"Downloading {data_cfg['ticker']} data…"):
                    prices = fetch_data(
                        data_cfg["ticker"],
                        data_cfg["interval"],
                        data_cfg["start_date"],
                        data_cfg["end_date"],
                    )

                if prices is None:
                    st.error("Data download failed — check the ticker and date range.")
                elif len(prices) < 100:
                    st.error(f"Only {len(prices)} bars returned — need at least 100. Extend the date range.")
                else:
                    individual_signals: Dict[str, pd.Series] = {}
                    indicator_overlays: list = []

                    if strategy_cfg.get("mode") == "trend_builder":
                        # ── Trend/Momentum Builder path ───────────────────
                        with st.spinner("Computing signal…"):
                            try:
                                raw_signal = generate_trend_signal(
                                    prices,
                                    strategy_cfg["signal_type"],
                                    strategy_cfg["signal_params"],
                                )
                                signal = apply_entry_logic(
                                    raw_signal,
                                    mode="state",
                                    confirmation_bars=strategy_cfg["confirmation_bars"],
                                )
                                signal = apply_signal_filters(
                                    signal, prices,
                                    filter_config=strategy_cfg["filter_config"],
                                )
                                if strategy_cfg["trend_filter_on"]:
                                    signal = apply_trend_filter(
                                        signal, prices,
                                        interval=data_cfg["interval"],
                                        ma_period=strategy_cfg["trend_filter_period"],
                                    )
                                    st.info(
                                        f"Trend filter active — signals opposing the "
                                        f"{strategy_cfg['trend_filter_period']}-bar "
                                        f"higher-TF MA have been zeroed out."
                                    )
                                individual_signals[strategy_cfg["signal_type"]] = raw_signal
                                combined = signal
                                indicator_overlays = build_trend_indicators(
                                    prices,
                                    strategy_cfg["signal_type"],
                                    strategy_cfg["signal_params"],
                                )
                            except Exception as e:
                                st.error(f"Signal computation failed: {e}")

                    elif strategy_cfg.get("mode") == "mr_builder":
                        # ── Mean Reversion Builder path ───────────────────
                        with st.spinner("Computing signal…"):
                            try:
                                raw_signal  = generate_mr_signal(
                                    prices,
                                    strategy_cfg["signal_type"],
                                    strategy_cfg["signal_params"],
                                )
                                natural_mode = MEAN_REVERSION_SIGNAL_REGISTRY.get(
                                    strategy_cfg["signal_type"], {}
                                ).get("natural_mode", "event")

                                if natural_mode == "state":
                                    # State signals already encode entry+exit natively —
                                    # forward-filling would override the built-in exit logic.
                                    signal = raw_signal
                                else:
                                    # Event signals fire for 1 bar only; forward-fill so
                                    # the position holds while the condition persists.
                                    signal = apply_entry_logic(raw_signal, mode="state")

                                if strategy_cfg["confirmation_bars"] > 1:
                                    signal = apply_entry_logic(
                                        signal, mode="confirmation",
                                        confirmation_bars=strategy_cfg["confirmation_bars"],
                                    )

                                if strategy_cfg["wait_for_reversal"]:
                                    indicator = get_mr_indicator_series(
                                        prices,
                                        strategy_cfg["signal_type"],
                                        strategy_cfg["signal_params"],
                                    )
                                    signal = apply_mr_reversal_confirmation(signal, indicator)
                                signal = apply_signal_filters(
                                    signal, prices,
                                    filter_config=strategy_cfg["filter_config"],
                                )
                                individual_signals[strategy_cfg["signal_type"]] = raw_signal
                                combined = signal
                                indicator_overlays = build_mr_indicators(
                                    prices,
                                    strategy_cfg["signal_type"],
                                    strategy_cfg["signal_params"],
                                )
                            except Exception as e:
                                st.error(f"Signal computation failed: {e}")

                    elif strategy_cfg.get("mode") == "pa_builder":
                        # ── Price Action Builder path ─────────────────────
                        with st.spinner("Computing signal…"):
                            try:
                                raw_signal = generate_pa_signal(
                                    prices,
                                    strategy_cfg["signal_type"],
                                    strategy_cfg["signal_params"],
                                )
                                # All price action patterns are event signals — forward-fill to hold position
                                signal = apply_entry_logic(raw_signal, mode="state")
                                if strategy_cfg["confirmation_bars"] > 1:
                                    signal = apply_entry_logic(
                                        signal, mode="confirmation",
                                        confirmation_bars=strategy_cfg["confirmation_bars"],
                                    )
                                signal = apply_signal_filters(
                                    signal, prices,
                                    filter_config=strategy_cfg["filter_config"],
                                )
                                individual_signals[strategy_cfg["signal_type"]] = raw_signal
                                combined = signal
                                indicator_overlays = build_pa_indicators(
                                    prices,
                                    strategy_cfg["signal_type"],
                                    strategy_cfg["signal_params"],
                                )
                            except Exception as e:
                                st.error(f"Signal computation failed: {e}")

                    else:
                        # ── Generic multi-strategy path ────────────────────
                        with st.spinner("Computing signals…"):
                            for name in strategy_cfg["selected_strategies"]:
                                reg = STRATEGY_REGISTRY[name]
                                try:
                                    individual_signals[name] = reg["fn"](
                                        prices, **strategy_cfg["strategy_params"][name]
                                    )
                                except Exception as e:
                                    st.error(f"Strategy '{name}' failed: {e}")

                        for name in strategy_cfg["selected_strategies"]:
                            reg = STRATEGY_REGISTRY[name]
                            if "indicators" in reg and name in individual_signals:
                                try:
                                    indicator_overlays.extend(
                                        reg["indicators"](
                                            prices, **strategy_cfg["strategy_params"][name]
                                        )
                                    )
                                except Exception:
                                    pass

                        combined = combine_signals(
                            individual_signals,
                            method=strategy_cfg["combo_method"],
                            weights=strategy_cfg["weights"],
                            threshold=strategy_cfg["combo_threshold"],
                        ) if individual_signals else None

                        if combined is not None and strategy_cfg["trend_filter_on"]:
                            combined = apply_trend_filter(
                                combined, prices,
                                interval=data_cfg["interval"],
                                ma_period=strategy_cfg["trend_filter_period"],
                            )
                            st.info(
                                f"Trend filter active — signals opposing the "
                                f"{strategy_cfg['trend_filter_period']}-bar higher-TF MA "
                                f"have been zeroed out."
                            )

                    if not individual_signals:
                        st.error("No valid signals generated.")
                    else:
                        with st.spinner("Running backtest…"):
                            _fc = strategy_cfg.get("filter_config", {})
                            result = run_backtest(
                                combined.fillna(0), prices,
                                interval=data_cfg["interval"],
                                risk_per_trade=0.02,
                                commission_pct=strategy_cfg["commission_pct"],
                                slippage_pct=strategy_cfg["slippage_pct"],
                                vol_target=strategy_cfg["vol_target"],
                                close_on_neutral=strategy_cfg.get("close_on_neutral", False),
                                max_bars_held=strategy_cfg.get("max_bars_held"),
                                use_sltp=strategy_cfg.get("use_sltp", True),
                                sl_pct_fixed=strategy_cfg.get("sl_pct_fixed"),
                                tp_ratio=strategy_cfg.get("tp_ratio", 2.0),
                                exit_ma_period=strategy_cfg.get("exit_ma_period"),
                                trailing_sl=strategy_cfg.get("trailing_sl", False),
                                trail_atr_mult=strategy_cfg.get("trail_atr_mult", 1.0),
                                vol_method=strategy_cfg.get("vol_method", "Rolling Std"),
                                long_only=_fc.get("long_only", False),
                                short_only=_fc.get("short_only", False),
                            )

                        _mode = strategy_cfg.get("mode")
                        _label_strats = (
                            f"{strategy_cfg['signal_type']} (trend builder)"
                            if _mode == "trend_builder"
                            else f"{strategy_cfg['signal_type']} (MR builder)"
                            if _mode == "mr_builder"
                            else f"{strategy_cfg['signal_type']} (price action)"
                            if _mode == "pa_builder"
                            else ", ".join(strategy_cfg["selected_strategies"])
                        )
                        st.session_state.update({
                            "backtest_result":    result,
                            "prices":             prices,
                            "combined_signal":    combined,
                            "individual_signals": individual_signals,
                            "indicator_overlays": indicator_overlays,
                            "run_label": (
                                f"{data_cfg['ticker']} | {data_cfg['interval']} | "
                                f"{_label_strats} | {len(prices):,} bars"
                            ),
                        })

                        st.success(
                            f"Backtest complete — {data_cfg['ticker']} | "
                            f"{data_cfg['interval']} | {len(prices):,} bars"
                        )

            except Exception as e:
                st.error(f"Unexpected error: {e}")

    # Retrieve persisted state for results tabs
    result             = st.session_state.get("backtest_result")
    prices             = st.session_state.get("prices")
    combined           = st.session_state.get("combined_signal")
    individual_signals = st.session_state.get("individual_signals", {})
    indicator_overlays = st.session_state.get("indicator_overlays", [])
    run_label          = st.session_state.get("run_label")

    _no_results_msg = "Configure a strategy in **Strategy Builder** and click **Run Backtest**."

    def _run_caption():
        if run_label:
            st.caption(f"Showing results for: {run_label}")

    with tab2:
        if prices is not None and combined is not None:
            _run_caption()
            tab_signal_diagnostics(
                prices, individual_signals, combined,
                trade_log=result["trade_log"] if result else None,
                indicator_overlays=indicator_overlays,
                interval=data_cfg["interval"],
            )
        else:
            st.info(_no_results_msg)

    with tab3:
        if result is not None and prices is not None:
            _run_caption()
            tab_backtest_results(result, prices, data_cfg["interval"])
        else:
            st.info(_no_results_msg)

    with tab4:
        if result is not None:
            _run_caption()
            tab_trade_analysis(result)
        else:
            st.info(_no_results_msg)


if __name__ == "__main__":
    main()
