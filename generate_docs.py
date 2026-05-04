"""
generate_docs.py — Generates a detailed PDF documentation of the Trading Research Platform.
Run: python generate_docs.py
Output: Trading_Platform_Documentation.pdf
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import (
    HexColor, black, white, Color
)
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import ListFlowable, ListItem

# ── Colour palette ─────────────────────────────────────────────────────────────
DARK_BG    = HexColor("#0f172a")
PANEL_BG   = HexColor("#1e293b")
ACCENT     = HexColor("#00b4d8")
ACCENT2    = HexColor("#60a5fa")
GREEN      = HexColor("#22c55e")
RED        = HexColor("#ef4444")
AMBER      = HexColor("#f59e0b")
PURPLE     = HexColor("#a78bfa")
MUTED      = HexColor("#94a3b8")
LIGHT_TEXT = HexColor("#e2e8f0")
MID_TEXT   = HexColor("#cbd5e1")

# ── Document setup ─────────────────────────────────────────────────────────────
OUTPUT = "Trading_Platform_Documentation.pdf"

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    leftMargin=2.2*cm,
    rightMargin=2.2*cm,
    topMargin=2.5*cm,
    bottomMargin=2.5*cm,
    title="Trading Research Platform — Technical Documentation",
    author="Trading Research Platform",
)

W = A4[0] - 4.4*cm  # usable page width

# ── Styles ─────────────────────────────────────────────────────────────────────
base = getSampleStyleSheet()

def make_style(name, parent="Normal", **kw):
    return ParagraphStyle(name, parent=base[parent], **kw)

S = {
    "cover_title": make_style("cover_title",
        fontSize=32, leading=40, textColor=LIGHT_TEXT,
        spaceAfter=10, alignment=TA_CENTER, fontName="Helvetica-Bold"),

    "cover_sub": make_style("cover_sub",
        fontSize=14, leading=20, textColor=MUTED,
        spaceAfter=6, alignment=TA_CENTER),

    "h1": make_style("h1",
        fontSize=20, leading=26, textColor=ACCENT,
        spaceBefore=22, spaceAfter=8, fontName="Helvetica-Bold"),

    "h2": make_style("h2",
        fontSize=14, leading=20, textColor=ACCENT2,
        spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold"),

    "h3": make_style("h3",
        fontSize=11, leading=16, textColor=AMBER,
        spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold"),

    "body": make_style("body",
        fontSize=9.5, leading=15, textColor=MID_TEXT,
        spaceAfter=6, alignment=TA_JUSTIFY),

    "body_left": make_style("body_left",
        fontSize=9.5, leading=15, textColor=MID_TEXT,
        spaceAfter=6, alignment=TA_LEFT),

    "formula": make_style("formula",
        fontSize=9, leading=14, textColor=GREEN,
        spaceAfter=6, fontName="Courier", leftIndent=20),

    "code": make_style("code",
        fontSize=8.5, leading=13, textColor=HexColor("#86efac"),
        spaceAfter=4, fontName="Courier", leftIndent=20),

    "note": make_style("note",
        fontSize=8.5, leading=13, textColor=MUTED,
        spaceAfter=4, fontName="Helvetica-Oblique", leftIndent=12),

    "caption": make_style("caption",
        fontSize=9, leading=13, textColor=MUTED,
        spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica-Oblique"),

    "table_header": make_style("table_header",
        fontSize=9, leading=13, textColor=white,
        fontName="Helvetica-Bold", alignment=TA_CENTER),

    "table_cell": make_style("table_cell",
        fontSize=8.5, leading=13, textColor=MID_TEXT, alignment=TA_LEFT),
}

# ── Table style helper ─────────────────────────────────────────────────────────
def dark_table(data, col_widths=None):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), PANEL_BG),
        ("TEXTCOLOR",  (0,0), (-1,0), ACCENT2),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,0), 9),
        ("ALIGN",      (0,0), (-1,0), "CENTER"),
        ("BACKGROUND", (0,1), (-1,-1), HexColor("#111827")),
        ("TEXTCOLOR",  (0,1), (-1,-1), MID_TEXT),
        ("FONTSIZE",   (0,1), (-1,-1), 8.5),
        ("FONTNAME",   (0,1), (-1,-1), "Helvetica"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [HexColor("#111827"), HexColor("#1a2332")]),
        ("GRID",       (0,0), (-1,-1), 0.4, HexColor("#334155")),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING",(0,0), (-1,-1), 7),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
    ]))
    return t


def hr():
    return HRFlowable(width="100%", thickness=0.5, color=HexColor("#334155"), spaceAfter=8)


def p(text, style="body"):
    return Paragraph(text, S[style])


def bullet(items, style="body_left"):
    return ListFlowable(
        [ListItem(Paragraph(i, S[style]), leftIndent=20, bulletColor=ACCENT2) for i in items],
        bulletType="bullet", bulletFontSize=8, spaceAfter=4,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CONTENT
# ══════════════════════════════════════════════════════════════════════════════
story = []

# ── Cover page ─────────────────────────────────────────────────────────────────
story += [
    Spacer(1, 3*cm),
    p("Trading Research Platform", "cover_title"),
    p("Complete Technical Documentation", "cover_sub"),
    Spacer(1, 0.5*cm),
    p("Signal Generation  ·  Backtesting Engine  ·  Performance Metrics  ·  Risk Management", "cover_sub"),
    Spacer(1, 2*cm),
    hr(),
    Spacer(1, 0.5*cm),
    p("This document explains every component of the platform in precise detail: "
      "how each trading strategy generates signals, how look-ahead bias is prevented, "
      "how the backtest engine simulates trades bar by bar, how position sizes are "
      "calculated using volatility, how risk is managed with stop-losses and take-profits, "
      "and what every performance metric measures.", "body"),
    Spacer(1, 1*cm),
    PageBreak(),
]

# ── Table of Contents ─────────────────────────────────────────────────────────
story += [
    p("Table of Contents", "h1"),
    hr(),
]
toc = [
    ("1", "Architecture Overview", "3"),
    ("2", "Data Ingestion", "4"),
    ("3", "Signal Convention & Look-Ahead Bias", "5"),
    ("4", "Trading Strategies", "6"),
    ("  4.1", "SMA Crossover", "6"),
    ("  4.2", "RSI (Relative Strength Index)", "7"),
    ("  4.3", "Stochastic RSI", "9"),
    ("  4.4", "MACD", "10"),
    ("  4.5", "Bollinger Bands", "12"),
    ("  4.6", "Donchian Channels", "13"),
    ("  4.7", "ADX (Average Directional Index)", "14"),
    ("  4.8", "Ichimoku Cloud", "16"),
    ("5", "Signal Combination", "18"),
    ("6", "Higher-Timeframe Trend Filter", "20"),
    ("7", "Backtest Engine", "21"),
    ("  7.1", "Bar-by-Bar Simulation Loop", "21"),
    ("  7.2", "Volatility-Based Stop-Loss Sizing", "23"),
    ("  7.3", "Position Sizing", "25"),
    ("  7.4", "Take-Profit Calculation", "26"),
    ("  7.5", "Commission & Slippage", "26"),
    ("  7.6", "Signal Re-Entry (Pending Entry)", "27"),
    ("8", "Performance Metrics", "28"),
    ("9", "Trade Log Columns", "33"),
    ("10", "Parameter Sweep", "34"),
]
toc_data = [
    [p("§", "table_header"), p("Section", "table_header"), p("Page", "table_header")]
] + [
    [p(n, "table_cell"), p(t, "table_cell"), p(pg, "table_cell")]
    for n, t, pg in toc
]
story.append(dark_table(toc_data, col_widths=[1.5*cm, 13*cm, 1.5*cm]))
story.append(PageBreak())


# ══════════════════════════════════════════════════════════════════════════════
# 1  ARCHITECTURE OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
story += [
    p("1. Architecture Overview", "h1"), hr(),
    p("The platform is structured as five independent Python modules that "
      "communicate through well-defined interfaces. Each module has a single "
      "responsibility and imports nothing from the others except where explicitly "
      "stated. This makes each piece easy to test, extend, or replace in isolation."),
]

arch_data = [
    [p("Module", "table_header"), p("File", "table_header"), p("Responsibility", "table_header")],
    [p("Data", "table_cell"), p("data.py", "table_cell"),
     p("Downloads OHLCV price data from Yahoo Finance via yfinance and caches it in the Streamlit session.", "table_cell")],
    [p("Strategies", "table_cell"), p("strategies.py", "table_cell"),
     p("Implements all 8 trading strategies plus signal combination and the higher-timeframe trend filter.", "table_cell")],
    [p("Backtest", "table_cell"), p("backtest.py", "table_cell"),
     p("Bar-by-bar simulation engine: converts signals to positions, applies SL/TP, computes returns and all metrics.", "table_cell")],
    [p("Utils", "table_cell"), p("utils.py", "table_cell"),
     p("Shared helpers: return calculation, annualisation factor, all Plotly charting functions.", "table_cell")],
    [p("App", "table_cell"), p("app.py", "table_cell"),
     p("Streamlit UI entry point. Wires all modules together into a three-tab web application.", "table_cell")],
]
story.append(dark_table(arch_data, col_widths=[2.5*cm, 2.8*cm, 10.7*cm]))
story += [
    Spacer(1, 0.4*cm),
    p("Data flow (left to right):"),
    bullet([
        "<b>data.py</b> fetches OHLCV price bars from Yahoo Finance.",
        "<b>strategies.py</b> reads the price DataFrame and produces a signal Series (1, -1, or 0 per bar).",
        "<b>backtest.py</b> reads both the signal Series and the price DataFrame, simulates trades bar by bar, and returns metrics, an equity curve, and a trade log.",
        "<b>utils.py</b> converts those outputs into Plotly charts.",
        "<b>app.py</b> orchestrates the above in order, stores results in Streamlit session state between re-renders, and displays everything across three tabs.",
    ]),
    PageBreak(),
]


# ══════════════════════════════════════════════════════════════════════════════
# 2  DATA INGESTION
# ══════════════════════════════════════════════════════════════════════════════
story += [
    p("2. Data Ingestion", "h1"), hr(),
    p("All market data is sourced from Yahoo Finance through the <b>yfinance</b> library. "
      "The function <b>fetch_data(ticker, interval, start, end)</b> in data.py handles "
      "downloading, cleaning, and caching."),

    p("Supported Timeframes", "h2"),
    p("The platform supports five bar intervals:"),
]

tf_data = [
    [p("Interval", "table_header"), p("Bar Duration", "table_header"),
     p("Yahoo Finance Limit", "table_header"), p("Approx. Bars per Year", "table_header")],
    [p("1d",  "table_cell"), p("1 calendar day",  "table_cell"), p("No limit",   "table_cell"), p("252",   "table_cell")],
    [p("4h",  "table_cell"), p("4 hours",         "table_cell"), p("730 days",   "table_cell"), p("~411",  "table_cell")],
    [p("1h",  "table_cell"), p("1 hour",          "table_cell"), p("730 days",   "table_cell"), p("~1,638","table_cell")],
    [p("15m", "table_cell"), p("15 minutes",      "table_cell"), p("60 days",    "table_cell"), p("~1,638","table_cell")],
    [p("5m",  "table_cell"), p("5 minutes",       "table_cell"), p("60 days",    "table_cell"), p("~4,914","table_cell")],
]
story.append(dark_table(tf_data, col_widths=[2*cm, 3.5*cm, 4*cm, 4.5*cm]))
story += [
    Spacer(1, 0.3*cm),
    p("The Yahoo Finance API enforces hard limits on how far back intraday data goes: "
      "5-minute and 15-minute data is available for the last 60 days only; "
      "1-hour and 4-hour data is available for the last 730 days only. "
      "The platform enforces these limits before attempting a download and shows "
      "an error to the user if the requested date range exceeds the limit."),

    p("auto_adjust=True", "h3"),
    p("All downloads use <b>auto_adjust=True</b>. This instructs Yahoo Finance to return "
      "prices already adjusted for historical stock splits and dividend distributions. "
      "Without adjustment, a 2:1 stock split would appear in the price history as a "
      "50% crash overnight — the backtest engine would then generate a massive sell "
      "signal and record a large loss that never actually happened. Adjusted prices "
      "ensure the entire price history is internally consistent and suitable for "
      "accurate backtesting."),

    p("Session Caching", "h3"),
    p("Downloaded data is stored in <b>st.session_state</b> using a cache key of the form "
      "<i>ticker_interval_start_end</i>. If the user clicks 'Run Backtest' again with "
      "identical settings, the cached DataFrame is returned immediately without a "
      "second network request. The cache is invalidated whenever the ticker, interval, "
      "or date range changes."),

    p("Data Cleaning", "h3"),
    bullet([
        "If yfinance returns a MultiIndex column structure (which can occur on some versions), it is flattened to standard column names.",
        "Only the five standard OHLCV columns are retained: Open, High, Low, Close, Volume.",
        "Any row where Close is NaN is dropped — this can occur at the end of the data range when the most recent bar has not yet closed.",
        "A minimum of 100 bars is required before a backtest can run. Below this threshold the platform rejects the data with an error message.",
    ]),
    PageBreak(),
]


# ══════════════════════════════════════════════════════════════════════════════
# 3  SIGNAL CONVENTION & LOOK-AHEAD BIAS
# ══════════════════════════════════════════════════════════════════════════════
story += [
    p("3. Signal Convention & Look-Ahead Bias Prevention", "h1"), hr(),

    p("Signal Values", "h2"),
    p("Every strategy returns a <b>pd.Series</b> of integer values with the same index as "
      "the price DataFrame. The three possible values are:"),
]
sig_data = [
    [p("Value", "table_header"), p("Meaning", "table_header")],
    [p("1",  "table_cell"), p("Long signal — go long (buy) at the next bar's open.", "table_cell")],
    [p("-1", "table_cell"), p("Short signal — go short (sell) at the next bar's open.", "table_cell")],
    [p("0",  "table_cell"), p("No signal — do nothing, stay flat.", "table_cell")],
]
story.append(dark_table(sig_data, col_widths=[2*cm, 14*cm]))
story += [
    Spacer(1, 0.3*cm),
    p("Event-Based Signals", "h2"),
    p("Signals are <b>event-based</b>, not state-based. A signal value of 1 means "
      "<i>a crossover just happened on this bar</i>, not <i>the fast line is currently "
      "above the slow line</i>. A signal fires on exactly one bar — the bar where "
      "the condition transitions from false to true — and is 0 on every other bar, "
      "even if the condition continues to hold. This is implemented using pandas "
      "shift comparisons:"),
    p("signal[(fast > slow) & (fast.shift(1) <= slow.shift(1))] = 1", "formula"),
    p("The left condition checks the current bar; the right condition checks the previous "
      "bar. A signal fires only when the current bar satisfies the condition AND the "
      "previous bar did not — i.e. only on the exact bar of the transition."),

    p("The One-Bar Delay Rule (Look-Ahead Prevention)", "h2"),
    p("Look-ahead bias is the most common mistake in backtesting. It occurs when the "
      "backtest uses information from the current bar to decide whether to enter a "
      "trade on the same bar. In reality, you cannot observe the close price of bar N "
      "and simultaneously enter a trade on bar N — the close price is the last price "
      "of the bar, by which time the bar is over."),
    p("The platform prevents look-ahead bias by applying a <b>one-bar shift</b> to all "
      "signals inside the backtest engine:"),
    p("shifted_signals = signals.shift(1).reindex(prices.index).fillna(0)", "formula"),
    p("This means: a signal generated at the close of bar N is only acted upon at "
      "bar N+1. The position is entered at <b>the close of bar N</b> (used as the "
      "entry price proxy), and the trade result is calculated from bar N+1 onwards. "
      "This correctly models the real-world workflow: observe the close, decide to "
      "trade, execute at or near the next open."),
    p("This is a non-negotiable design decision. Any backtest without this shift "
      "is technically invalid and will report unrealistically good results."),
    PageBreak(),
]


# ══════════════════════════════════════════════════════════════════════════════
# 4  TRADING STRATEGIES
# ══════════════════════════════════════════════════════════════════════════════
story += [p("4. Trading Strategies", "h1"), hr()]

# ── 4.1 SMA CROSSOVER ─────────────────────────────────────────────────────────
story += [
    p("4.1  SMA Crossover", "h2"),
    p("<b>Type:</b> Trend-following  |  <b>Parameters:</b> fast_period (default 10), slow_period (default 50)",
      "note"),
    p("The Simple Moving Average crossover is one of the oldest and most widely used "
      "systematic trading signals. It is based on the idea that when a short-term "
      "average of price crosses above a long-term average, momentum has shifted upward "
      "and a trend may be beginning."),

    p("How it is calculated", "h3"),
    bullet([
        "<b>Fast SMA:</b> the arithmetic mean of the closing price over the last fast_period bars. "
          "By default this is 10 bars.",
        "<b>Slow SMA:</b> the arithmetic mean of the closing price over the last slow_period bars. "
          "By default this is 50 bars.",
    ]),
    p("Formula:"),
    p("SMA(N) at bar t  =  (Close[t] + Close[t-1] + ... + Close[t-N+1])  /  N", "formula"),

    p("Signal logic", "h3"),
    p("The signal fires only on the bar where the crossover actually happens — "
      "not on every bar where the fast is above the slow:"),
    p("Long  (+1): fast crosses ABOVE slow  →  fast[t] > slow[t]  AND  fast[t-1] <= slow[t-1]", "formula"),
    p("Short (-1): fast crosses BELOW slow  →  fast[t] < slow[t]  AND  fast[t-1] >= slow[t-1]", "formula"),

    p("Why it works (theory)", "h3"),
    p("A short-term average reacts quickly to recent price changes. A long-term average "
      "moves slowly and reflects the broader trend. When the short-term average crosses "
      "above the long-term average, it means recent prices have risen sharply relative "
      "to the longer history — a bullish momentum signal. The reverse crossover indicates "
      "that recent prices have declined sharply, a bearish signal."),

    p("Practical considerations", "h3"),
    bullet([
        "<b>Trending markets:</b> SMA crossover performs best in clear, sustained trends. It is a momentum/trend-following strategy by design.",
        "<b>Ranging markets:</b> In sideways, choppy markets the two SMAs cross back and forth frequently, generating many small losses known as 'whipsaws'. The ADX strategy (Section 4.7) was designed specifically to address this.",
        "<b>Lag:</b> Moving averages are lagging indicators. The signal always fires some time after the trend has already started. Shorter periods reduce lag but increase whipsaws; longer periods reduce whipsaws but enter later into moves.",
        "<b>Parameter constraints:</b> fast_period must be strictly less than slow_period. The platform raises an error if this constraint is violated.",
    ]),
    PageBreak(),
]

# ── 4.2 RSI ──────────────────────────────────────────────────────────────────
story += [
    p("4.2  RSI — Relative Strength Index", "h2"),
    p("<b>Type:</b> Mean-reversion  |  <b>Parameters:</b> period (default 14), oversold (default 30), overbought (default 70)",
      "note"),

    p("The RSI is a momentum oscillator developed by J. Welles Wilder in 1978. "
      "It measures the speed and magnitude of recent price changes to evaluate "
      "whether an asset is overbought (too expensive, likely to fall) or oversold "
      "(too cheap, likely to rise). RSI always oscillates between 0 and 100."),

    p("How RSI is calculated", "h3"),
    p("Step 1: For each bar, compute the price change from the previous bar:"),
    p("Delta[t] = Close[t] - Close[t-1]", "formula"),
    p("Step 2: Separate gains and losses:"),
    p("Gain[t] = max(Delta[t], 0)    Loss[t] = max(-Delta[t], 0)", "formula"),
    p("Step 3: Compute smoothed average gain and average loss over the lookback period "
      "(the ta library uses Wilder's exponential smoothing, which gives more weight to "
      "recent values than a simple average):"),
    p("Avg Gain = Exponential Moving Average of Gain  over  period  bars", "formula"),
    p("Avg Loss = Exponential Moving Average of Loss  over  period  bars", "formula"),
    p("Step 4: Compute the Relative Strength (RS) and then the RSI:"),
    p("RS  = Avg Gain / Avg Loss", "formula"),
    p("RSI = 100 - (100 / (1 + RS))", "formula"),
    p("When all recent bars closed higher, Avg Loss approaches zero, RS approaches "
      "infinity, and RSI approaches 100. When all recent bars closed lower, Avg Gain "
      "approaches zero, RS approaches zero, and RSI approaches 0."),

    p("Signal logic", "h3"),
    p("The platform uses a <b>reversal confirmation</b> approach rather than a simple "
      "threshold level. This means the signal fires when RSI exits the extreme zone, "
      "not when it enters it:"),
    p("Long  (+1): RSI crosses back UP through the oversold level", "formula"),
    p("            prev_RSI < oversold  AND  RSI >= oversold", "formula"),
    p("Short (-1): RSI crosses back DOWN through the overbought level", "formula"),
    p("            prev_RSI > overbought  AND  RSI <= overbought", "formula"),
    p("This confirmation step is important. Entering when RSI first drops below 30 can "
      "mean buying into a market that is still falling hard. Waiting for the exit from "
      "the oversold zone (the bounce back above 30) provides evidence that the selling "
      "pressure has abated and the price is actually starting to recover."),

    p("Why it works (theory)", "h3"),
    p("RSI is a mean-reversion strategy. The underlying assumption is that markets "
      "tend to overshoot — they fall too far (fear/panic) or rise too far (greed/euphoria) "
      "and then revert toward fair value. When RSI reaches extreme levels it indicates "
      "that recent price movement has been unusually one-sided. The strategy bets that "
      "this imbalance will correct."),

    p("Practical considerations", "h3"),
    bullet([
        "<b>Trending markets:</b> RSI performs poorly in strong trends. In a bull trend, RSI can remain overbought (above 70) for extended periods, generating premature short signals. The higher-TF trend filter (Section 6) can mitigate this.",
        "<b>Oversold does not mean 'buy immediately':</b> An RSI of 10 means the market has fallen sharply; it doesn't mean it can't fall further. The reversal confirmation signal (waiting for the exit from the zone) adds a layer of confirmation.",
        "<b>Period sensitivity:</b> A shorter period (e.g. 7) makes RSI more reactive and oscillate more frequently; a longer period (e.g. 21) makes it smoother and generates fewer, slower signals.",
    ]),
    PageBreak(),
]

# ── 4.3 STOCHASTIC RSI ───────────────────────────────────────────────────────
story += [
    p("4.3  Stochastic RSI", "h2"),
    p("<b>Type:</b> Mean-reversion  |  <b>Parameters:</b> period (14), smooth_k (3), smooth_d (3), oversold (20), overbought (80)",
      "note"),

    p("Stochastic RSI applies the Stochastic Oscillator formula to the RSI values "
      "rather than directly to price. It was developed by Tushar Chande and Stanley "
      "Kroll in 1994. The result is a more sensitive indicator that oscillates "
      "between 0 and 100 and reaches extreme levels more frequently than plain RSI."),

    p("How it is calculated", "h3"),
    p("Step 1: Compute the RSI series over period bars (same as Section 4.2)."),
    p("Step 2: Apply the Stochastic formula to the RSI series over the same period:"),
    p("StochRSI = (RSI[t] - min(RSI, period)) / (max(RSI, period) - min(RSI, period))", "formula"),
    p("This rescales the RSI so that its highest value over the period equals 1 and "
      "its lowest value equals 0."),
    p("Step 3: Smooth the raw StochRSI with a rolling mean to get the %K line:"),
    p("%K = rolling_mean(StochRSI, smooth_k)", "formula"),
    p("Step 4: Smooth %K again to get the %D (signal) line:"),
    p("%D = rolling_mean(%K, smooth_d)", "formula"),
    p("The platform scales %K to 0–100 to match the standard charting convention. "
      "The thresholds (default 20 for oversold, 80 for overbought) also follow this "
      "100-point scale."),

    p("Signal logic", "h3"),
    p("Identical to RSI: signals fire when %K exits the extreme zones (reversal confirmation):"),
    p("Long  (+1): %K crosses up through oversold   →  prev_%K < 20  AND  %K >= 20", "formula"),
    p("Short (-1): %K crosses down through overbought →  prev_%K > 80  AND  %K <= 80", "formula"),

    p("How it differs from plain RSI", "h3"),
    p("Because StochRSI is RSI-of-RSI, it is much more sensitive and volatile than "
      "plain RSI. It reaches extreme levels frequently, generating more signals. "
      "The double smoothing (smooth_k and smooth_d) controls how reactive or smooth "
      "the indicator is. Increasing smooth_k or smooth_d reduces signal frequency "
      "and removes short-term noise."),
    PageBreak(),
]

# ── 4.4 MACD ─────────────────────────────────────────────────────────────────
story += [
    p("4.4  MACD — Moving Average Convergence Divergence", "h2"),
    p("<b>Type:</b> Trend-following / momentum  |  <b>Parameters:</b> fast (12), slow (26), signal_period (9)",
      "note"),

    p("MACD was developed by Gerald Appel in the late 1970s. It works by measuring "
      "the relationship between two exponential moving averages of price, and then "
      "smoothing that relationship further. It is one of the most widely used "
      "indicators in systematic trading."),

    p("How it is calculated", "h3"),
    p("Step 1: Compute two Exponential Moving Averages (EMA) of the closing price. "
      "Unlike a simple moving average which weights all bars equally, an EMA gives "
      "progressively more weight to recent prices:"),
    p("EMA multiplier  k  =  2 / (N + 1)", "formula"),
    p("EMA[t]  =  Close[t] * k  +  EMA[t-1] * (1 - k)", "formula"),
    p("Step 2: Compute the MACD line as the difference between the fast and slow EMAs:"),
    p("MACD Line  =  EMA(fast)  -  EMA(slow)", "formula"),
    p("When the fast EMA is above the slow EMA, MACD is positive (bullish momentum). "
      "When it is below, MACD is negative (bearish momentum)."),
    p("Step 3: Compute the Signal line — an EMA of the MACD line itself:"),
    p("Signal Line  =  EMA(MACD Line, signal_period)", "formula"),
    p("The Signal line is a smoothed version of the MACD line. It reacts more slowly "
      "to changes in the MACD."),
    p("Step 4: Compute the Histogram — the difference between MACD and Signal:"),
    p("Histogram  =  MACD Line  -  Signal Line", "formula"),
    p("The histogram is shown as bars on the chart. Positive (green) bars indicate "
      "the MACD is above its signal line; negative (red) bars indicate it is below. "
      "Growing bars mean momentum is accelerating; shrinking bars mean it is fading."),

    p("Signal logic", "h3"),
    p("The platform uses the MACD/Signal line crossover:"),
    p("Long  (+1): MACD crosses ABOVE Signal", "formula"),
    p("            prev_MACD < prev_Signal  AND  MACD >= Signal", "formula"),
    p("Short (-1): MACD crosses BELOW Signal", "formula"),
    p("            prev_MACD > prev_Signal  AND  MACD <= Signal", "formula"),

    p("Why it works (theory)", "h3"),
    p("MACD is fundamentally a momentum indicator. It captures the relationship "
      "between short-term and long-term price momentum. When the MACD line crosses "
      "above the signal line, it means short-term momentum is accelerating relative "
      "to its own recent history — a bullish signal. The signal line acts as a "
      "smoother, confirming that the MACD movement is sustained rather than a "
      "one-bar spike."),

    p("Practical considerations", "h3"),
    bullet([
        "<b>Lag:</b> MACD is a lagging indicator — it is derived entirely from past price data. It identifies existing trends rather than predicting future ones.",
        "<b>Default parameters:</b> 12, 26, 9 are the standard parameters used across almost all financial software. They were chosen by Appel to work well on daily stock data.",
        "<b>Histogram divergence:</b> Experienced traders also watch for divergences — when price makes a new high but the histogram makes a lower high, it can signal weakening momentum before a reversal. This divergence logic is not currently automated in the platform.",
    ]),
    PageBreak(),
]

# ── 4.5 BOLLINGER BANDS ──────────────────────────────────────────────────────
story += [
    p("4.5  Bollinger Bands", "h2"),
    p("<b>Type:</b> Mean-reversion  |  <b>Parameters:</b> period (default 20), std_dev (default 2.0)",
      "note"),

    p("Bollinger Bands were developed by John Bollinger in the 1980s. They place an "
      "upper and lower envelope around price at a configurable number of standard "
      "deviations from a moving average. The bands automatically widen during volatile "
      "periods and contract during quiet periods."),

    p("How it is calculated", "h3"),
    p("Step 1: Compute the Middle Band — a simple moving average of closing price:"),
    p("Middle Band  =  SMA(Close, period)", "formula"),
    p("Step 2: Compute the rolling standard deviation of closing price over the same period:"),
    p("σ  =  sqrt( (1/N) * Σ(Close[i] - SMA)² )  over the last N bars", "formula"),
    p("Step 3: Place the Upper and Lower Bands at a multiple of σ from the Middle Band:"),
    p("Upper Band  =  Middle Band  +  std_dev * σ", "formula"),
    p("Lower Band  =  Middle Band  -  std_dev * σ", "formula"),
    p("With std_dev=2.0 (default), statistically approximately 95% of all closing "
      "prices should fall inside the bands — assuming normally distributed returns."),

    p("Signal logic", "h3"),
    p("The platform uses a mean-reversion approach: buy when price touches the lower "
      "band (oversold), sell when price touches the upper band (overbought). Signals "
      "fire only on the bar price first crosses the band:"),
    p("Long  (+1): Close crosses DOWN through Lower Band", "formula"),
    p("            Close[t] <= Lower[t]  AND  Close[t-1] > Lower[t-1]", "formula"),
    p("Short (-1): Close crosses UP through Upper Band", "formula"),
    p("            Close[t] >= Upper[t]  AND  Close[t-1] < Upper[t-1]", "formula"),

    p("Why it works (theory)", "h3"),
    p("The underlying assumption is that price tends to revert to its mean after "
      "unusual deviations. A price touching the lower band means it has moved more "
      "than two standard deviations below its recent average — statistically uncommon "
      "if returns were truly random. The strategy bets that this is a temporary "
      "overextension that will correct."),

    p("Practical considerations", "h3"),
    bullet([
        "<b>Volatile moves:</b> In a genuine crash or breakout, price can 'walk the band' — touching the outer band for many consecutive bars while a strong trend continues. The mean-reversion assumption breaks down in these conditions.",
        "<b>Band width as a volatility gauge:</b> Narrow bands mean recent volatility has been low; wide bands mean high volatility. Some traders use this to size positions or adjust other indicators.",
        "<b>std_dev parameter:</b> Wider bands (e.g. 2.5–3.0) are touched less often, generating fewer but potentially higher-quality signals. Narrower bands (1.5–2.0) are touched more frequently.",
    ]),
    PageBreak(),
]

# ── 4.6 DONCHIAN CHANNELS ────────────────────────────────────────────────────
story += [
    p("4.6  Donchian Channels", "h2"),
    p("<b>Type:</b> Breakout / momentum  |  <b>Parameters:</b> period (default 20)",
      "note"),

    p("Donchian Channels were invented by Richard Donchian, a pioneer of trend "
      "following in the 1950s. The famous Turtle Traders system used a variant of "
      "this strategy in the 1980s. The logic is simple: if price breaks out to a "
      "new N-bar high, a new trend may be starting upward; if it breaks to a new "
      "N-bar low, a new trend may be starting downward."),

    p("How it is calculated", "h3"),
    p("Upper Channel  =  Highest High over the last period bars", "formula"),
    p("Lower Channel  =  Lowest Low over the last period bars", "formula"),
    p("Middle Channel  =  (Upper + Lower) / 2", "formula"),

    p("Signal logic", "h3"),
    p("A breakout occurs on the first bar that closes above/below the channel boundary. "
      "Crucially, the channel is shifted by one bar to avoid look-ahead bias — the "
      "comparison is against the channel calculated using only prior bars:"),
    p("Long  (+1): Close > Upper Channel of the PREVIOUS bar  (first bar to break out)", "formula"),
    p("Short (-1): Close < Lower Channel of the PREVIOUS bar  (first bar to break out)", "formula"),
    p("Signals fire only on the first bar of the breakout. Subsequent bars where price "
      "remains outside the channel do not generate new signals."),

    p("Why it works (theory)", "h3"),
    p("The Donchian system is purely trend-following. The hypothesis is that if price "
      "breaks through the highest level it has seen in the past N bars, the market "
      "has shown genuine momentum in that direction and a new trend is likely underway. "
      "The strategy catches large moves in exchange for accepting many small losses "
      "from false breakouts."),

    p("Practical considerations", "h3"),
    bullet([
        "<b>Breakout failure:</b> Many breakouts fail — price pokes above the channel, triggers a long signal, then reverses back inside. The fixed-ratio stop-loss in the backtest engine limits the damage from these false breakouts.",
        "<b>Period length:</b> A 20-bar period captures roughly one month of daily moves. Longer periods (50–100) filter out shorter-term noise and produce fewer, larger trades. Shorter periods (10–15) are more reactive but generate more false breakouts.",
        "<b>Best in trending markets:</b> Like all momentum strategies, Donchian performs best when trends are sustained. It performs poorly in choppy, range-bound markets.",
    ]),
    PageBreak(),
]

# ── 4.7 ADX ──────────────────────────────────────────────────────────────────
story += [
    p("4.7  ADX — Average Directional Index", "h2"),
    p("<b>Type:</b> Trend filter + DI crossover  |  <b>Parameters:</b> period (default 14), threshold (default 25.0)",
      "note"),

    p("The ADX system was also developed by J. Welles Wilder in 1978. It is unique "
      "among the strategies in the platform because it explicitly measures whether "
      "the market is trending at all before taking a position. An ADX below the "
      "threshold means the market is ranging — the strategy goes flat. An ADX above "
      "the threshold means a trend is in progress — the strategy then uses the "
      "Directional Indicator (+DI/-DI) crossover to determine direction."),

    p("How it is calculated", "h3"),
    p("Step 1: For each bar, compute the True Range (TR) — the largest of three measures:"),
    p("TR[t]  =  max( High[t]-Low[t],  |High[t]-Close[t-1]|,  |Low[t]-Close[t-1]| )", "formula"),
    p("True Range accounts for overnight gaps — if the market gaps up significantly, "
      "the High-Low range of the new bar understates the actual price movement."),
    p("Step 2: Compute the Directional Movements:"),
    p("+DM[t]  =  High[t] - High[t-1]  if positive and > (Low[t-1] - Low[t]),  else 0", "formula"),
    p("-DM[t]  =  Low[t-1] - Low[t]    if positive and > (High[t] - High[t-1]),  else 0", "formula"),
    p("Step 3: Smooth TR, +DM, and -DM using Wilder's exponential smoothing over period bars."),
    p("Step 4: Compute the Directional Indicators:"),
    p("+DI  =  100 * (Smoothed +DM  /  Smoothed TR)", "formula"),
    p("-DI  =  100 * (Smoothed -DM  /  Smoothed TR)", "formula"),
    p("+DI measures upward pressure; -DI measures downward pressure. When +DI > -DI, "
      "the market is being pushed upward; when -DI > +DI, downward."),
    p("Step 5: Compute ADX — the smoothed absolute difference between +DI and -DI, "
      "normalised by their sum:"),
    p("DX[t]   =  100 * |+DI - -DI|  /  (+DI + -DI)", "formula"),
    p("ADX[t]  =  Wilder_EMA(DX, period)", "formula"),
    p("ADX ranges from 0 to 100. A rising ADX means the trend (in either direction) "
      "is strengthening. Values below ~20–25 indicate a ranging market; values above "
      "25 indicate a trending market; values above 40–50 indicate a very strong trend."),

    p("Signal logic", "h3"),
    p("The strategy ONLY generates signals when ADX > threshold (market is trending):"),
    p("Long  (+1): ADX > threshold  AND  +DI crosses ABOVE -DI", "formula"),
    p("Short (-1): ADX > threshold  AND  -DI crosses ABOVE +DI", "formula"),
    p("When ADX < threshold the strategy outputs 0 (flat) regardless of what the "
      "DI lines are doing."),

    p("Why it works (theory)", "h3"),
    p("ADX addresses the fundamental weakness of pure trend-following strategies: "
      "they generate many whipsaws in sideways markets. By only trading when ADX "
      "confirms that a trend is in progress, the strategy avoids many of the false "
      "crossover signals that occur in choppy conditions. The cost is that the "
      "strategy misses the beginning of trends (ADX is a lagging indicator — it only "
      "rises after a trend has started)."),
    PageBreak(),
]

# ── 4.8 ICHIMOKU ─────────────────────────────────────────────────────────────
story += [
    p("4.8  Ichimoku Cloud", "h2"),
    p("<b>Type:</b> Trend-following with cloud filter  |  <b>Parameters:</b> tenkan (9), kijun (26), senkou_b (52)",
      "note"),

    p("Ichimoku Kinko Hyo (which translates roughly to 'equilibrium chart at a glance') "
      "was developed by journalist Goichi Hosoda, who published it in 1969 after decades "
      "of research. It is a complete trading system on its own, combining trend direction, "
      "momentum, support/resistance, and a confirmation signal into a single chart. "
      "The platform implements the most widely used subset: Tenkan/Kijun crossover "
      "confirmed by Cloud position."),

    p("The five components", "h3"),
]
ichi_data = [
    [p("Component", "table_header"), p("Formula", "table_header"), p("Role", "table_header")],
    [p("Tenkan-sen\n(Conversion Line)", "table_cell"),
     p("(Highest High + Lowest Low) / 2\nover tenkan bars", "table_cell"),
     p("Short-term equilibrium. Faster-reacting line.", "table_cell")],
    [p("Kijun-sen\n(Base Line)", "table_cell"),
     p("(Highest High + Lowest Low) / 2\nover kijun bars", "table_cell"),
     p("Medium-term equilibrium. Slower-reacting line.", "table_cell")],
    [p("Senkou Span A\n(Leading Span A)", "table_cell"),
     p("(Tenkan + Kijun) / 2,\nplotted kijun bars forward", "table_cell"),
     p("Upper edge of bullish cloud.", "table_cell")],
    [p("Senkou Span B\n(Leading Span B)", "table_cell"),
     p("(Highest High + Lowest Low) / 2\nover senkou_b bars,\nplotted kijun bars forward", "table_cell"),
     p("Lower edge of bullish cloud.", "table_cell")],
    [p("The Cloud\n(Kumo)", "table_cell"),
     p("Shaded region between\nSpan A and Span B", "table_cell"),
     p("Dynamic support/resistance zone.\nColour shows bullish (green) or\nbearish (red) condition.", "table_cell")],
]
story.append(dark_table(ichi_data, col_widths=[3.5*cm, 5*cm, 7.5*cm]))
story += [
    Spacer(1, 0.3*cm),
    p("Cloud shifting in the platform", "h3"),
    p("The ta library computes Span A and Span B at bar T, but by convention they "
      "are displayed at bar T+kijun (26 bars into the future). The platform shifts "
      "them forward by kijun bars so that <b>cloud_top[T]</b> represents the cloud "
      "actually visible at bar T — not a future value. This is essential to avoid "
      "look-ahead bias:"),
    p("cloud_top    = max(Span_A.shift(kijun),  Span_B.shift(kijun))", "formula"),
    p("cloud_bottom = min(Span_A.shift(kijun),  Span_B.shift(kijun))", "formula"),

    p("Signal logic", "h3"),
    p("The signal requires two conditions to be satisfied simultaneously:"),
    p("Long  (+1): Tenkan crosses ABOVE Kijun  AND  Close > cloud_top", "formula"),
    p("Short (-1): Tenkan crosses BELOW Kijun  AND  Close < cloud_bottom", "formula"),
    p("The Cloud acts as a confirmation filter: long signals are only taken when price "
      "is already above the cloud (bullish trend), and short signals only when price "
      "is below the cloud (bearish trend). This prevents trading against the prevailing "
      "trend."),

    p("Why it works (theory)", "h3"),
    p("The Tenkan/Kijun cross is similar in concept to an SMA crossover, but using "
      "midpoint averages rather than arithmetic means — this makes the lines more "
      "responsive to high and low extremes than to the average close. The Cloud adds "
      "a second, independent confirmation layer: even if the fast line crosses the "
      "slow line, the signal is suppressed if price is trading inside or against the "
      "cloud. This dual-confirmation approach reduces false signals compared to a "
      "simple crossover."),
    PageBreak(),
]


# ══════════════════════════════════════════════════════════════════════════════
# 5  SIGNAL COMBINATION
# ══════════════════════════════════════════════════════════════════════════════
story += [
    p("5. Signal Combination", "h1"), hr(),

    p("When multiple strategies are selected, their individual signals must be combined "
      "into a single composite signal before the backtest runs. Three combination "
      "methods are available, each representing a different consensus philosophy."),

    p("Why combine signals?", "h2"),
    p("Each strategy has strengths in different market conditions. Trend-following "
      "strategies like SMA and Donchian perform well in sustained trends but suffer "
      "in ranges. Mean-reversion strategies like RSI and Bollinger Bands perform well "
      "in ranges but suffer in trends. Combining signals from strategies with different "
      "philosophies can smooth out the performance profile — when one strategy "
      "struggles, another may compensate."),

    p("Method 1: Majority Vote", "h2"),
    p("The simplest and most robust combination method. Each strategy votes +1 (long), "
      "-1 (short), or 0 (abstain). The sign of the total vote determines the signal:"),
    p("Combined Signal  =  sign( sum of all individual signals )", "formula"),
    bullet([
        "If more strategies are long (+1) than short (-1), the combined signal is +1 (Long).",
        "If more are short, the combined signal is -1 (Short).",
        "If exactly balanced (e.g. one long, one short), the sum is 0 — flat.",
        "Abstentions (0) from strategies that have no signal count as 0 votes.",
    ]),
    p("Example: 3 strategies selected — SMA=+1, RSI=0, MACD=+1. "
      "Sum = +2. Sign(+2) = +1 → Long.", "note"),

    p("Method 2: Weighted Average", "h2"),
    p("Like majority vote but assigns different importance to each strategy. "
      "Weights are entered in the sidebar and normalised internally so they sum to 1:"),
    p("Normalised weight(i)  =  weight(i) / sum(all weights)", "formula"),
    p("Combined Signal  =  sign( sum( normalised_weight(i) * signal(i) ) )", "formula"),
    p("Example: SMA weight=2, RSI weight=1, both long (+1). "
      "Normalised: SMA=0.667, RSI=0.333. "
      "Weighted sum = 0.667*1 + 0.333*1 = 1.0. Sign(1.0) = +1 → Long.", "note"),
    p("A strategy with weight 0 is completely ignored. A strategy with a very high "
      "weight dominates the combined signal."),

    p("Method 3: Threshold", "h2"),
    p("A stricter method that requires stronger consensus before taking a position. "
      "The average signal (ranging from -1 to +1) must exceed a threshold:"),
    p("Average Signal  =  mean of all individual signals", "formula"),
    p("Long  if  Average > +threshold", "formula"),
    p("Short if  Average < -threshold", "formula"),
    p("Flat  otherwise", "formula"),
    p("With threshold=0.5 and three strategies, at least two must agree (and the "
      "dissenter votes 0, not against) for a signal to be generated. This is stricter "
      "than majority vote. With threshold=0.33, a single strategy signal (1/3 ≈ 0.33) "
      "is sufficient."),
    p("The threshold parameter (0.1 to 1.0) is adjustable in the sidebar. "
      "Higher values require more consensus; lower values require less.", "note"),

    PageBreak(),
]


# ══════════════════════════════════════════════════════════════════════════════
# 6  HIGHER-TIMEFRAME TREND FILTER
# ══════════════════════════════════════════════════════════════════════════════
story += [
    p("6. Higher-Timeframe Trend Filter", "h1"), hr(),

    p("The trend filter is an optional overlay that suppresses signals on the current "
      "timeframe when they conflict with the trend on the next timeframe up. For "
      "example, if trading on the 1-hour chart, the filter checks whether the daily "
      "trend is bullish or bearish, and blocks short signals when the daily trend "
      "is up (and vice versa)."),

    p("Higher-timeframe mapping", "h2"),
]
htf_data = [
    [p("Trading Interval", "table_header"), p("Higher TF Used for Filter", "table_header")],
    [p("5 minutes",  "table_cell"), p("1 hour",      "table_cell")],
    [p("15 minutes", "table_cell"), p("4 hours",     "table_cell")],
    [p("1 hour",     "table_cell"), p("1 day (daily)", "table_cell")],
    [p("4 hours",    "table_cell"), p("1 day (daily)", "table_cell")],
    [p("1 day",      "table_cell"), p("1 week (weekly, closing Friday)", "table_cell")],
]
story.append(dark_table(htf_data, col_widths=[8*cm, 8*cm]))
story += [
    Spacer(1, 0.3*cm),

    p("Implementation", "h2"),
    p("Rather than making a second API call for higher-TF data, the filter derives "
      "it by resampling the existing price data that was already downloaded:"),
    p("htf_close = prices['Close'].resample(rule).last().dropna()", "formula"),
    p("This takes the existing bar-by-bar close series and resamples it to the "
      "higher timeframe by selecting the last close within each higher-TF period. "
      "For example, resampling hourly bars with rule='D' produces one bar per day "
      "using the last hourly close of each trading day — equivalent to the daily close."),
    p("A simple moving average of configurable period (default 50 bars) is then "
      "computed on the higher-TF close:"),
    p("Higher-TF trend  =  +1  if  HTF Close >= HTF SMA(50)", "formula"),
    p("                    -1  if  HTF Close <  HTF SMA(50)", "formula"),
    p("The resulting trend signal (1 or -1, one value per higher-TF bar) is then "
      "forward-filled onto every bar of the original lower-TF signal series:"),
    p("trend_aligned = trend.reindex(signal.index).ffill()", "formula"),
    p("This ensures every lower-TF bar has a higher-TF trend value — the current "
      "higher-TF bar's trend holds until the next higher-TF bar closes."),

    p("Filtering rule", "h2"),
    p("Long signals (+1) are zeroed out when the higher-TF trend is bearish (-1)."),
    p("Short signals (-1) are zeroed out when the higher-TF trend is bullish (+1)."),
    p("Flat signals (0) are unchanged regardless of trend direction."),

    p("Practical effect", "h2"),
    p("The trend filter converts the underlying strategy into a trend-following "
      "regime-aware strategy. It will typically reduce the total number of trades "
      "significantly (by removing all counter-trend signals) and will alter the "
      "win rate and return profile considerably. It is not always beneficial — "
      "mean-reversion strategies like RSI and Bollinger Bands may actually perform "
      "worse with the filter applied, since their edge often comes specifically from "
      "trading against short-term overextensions within larger trends."),
    PageBreak(),
]


# ══════════════════════════════════════════════════════════════════════════════
# 7  BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════════════════════
story += [p("7. Backtest Engine", "h1"), hr()]

# ── 7.1 Bar-by-bar loop ───────────────────────────────────────────────────────
story += [
    p("7.1  Bar-by-Bar Simulation Loop", "h2"),

    p("The core of the backtest engine is a single loop that iterates through every "
      "price bar from bar 1 to the end of the data (bar 0 is skipped because the "
      "returns calculation requires a prior close). At each bar the engine does "
      "exactly what a real trader would have to do — in order, with no knowledge "
      "of future bars."),

    p("Order of operations at each bar", "h3"),
    p("The following steps happen in this precise order at every bar i:"),

    bullet([
        "<b>Step 1 — Read current bar data:</b> Extract bar_high, bar_low, bar_close, and bar_return for bar i. Read the shifted signal for bar i (which was generated at bar i-1's close).",
        "<b>Step 2 — Check exits (if in a trade):</b> Before doing anything else, check whether the current bar's High or Low triggered the Stop-Loss or Take-Profit. Also check whether a reversal signal arrived on this bar.",
        "<b>Step 3 — Update MAE/MFE tracking:</b> Update the trade's running minimum low and maximum high with this bar's values.",
        "<b>Step 4 — Resolve effective signal:</b> Determine whether to act on the current bar's signal, a queued pending_entry from a prior signal flip, or nothing.",
        "<b>Step 5 — Open new trade (if not in a trade):</b> If a valid signal exists and no trade is open, calculate the SL/TP levels, position size, and open the trade.",
        "<b>Step 6 — Check SL/TP on entry bar:</b> Immediately check whether the new trade's SL or TP was hit on the same bar it was opened. This handles gap-downs/gap-ups on entry.",
    ]),

    p("What each variable tracks", "h3"),
]

vars_data = [
    [p("Variable", "table_header"), p("Type", "table_header"), p("Purpose", "table_header")],
    [p("in_trade", "table_cell"),          p("bool",    "table_cell"), p("True while a position is open.", "table_cell")],
    [p("direction", "table_cell"),         p("int",     "table_cell"), p("+1 for Long, -1 for Short.", "table_cell")],
    [p("sl_price", "table_cell"),          p("float",   "table_cell"), p("Absolute stop-loss price level.", "table_cell")],
    [p("tp_price", "table_cell"),          p("float",   "table_cell"), p("Absolute take-profit price level.", "table_cell")],
    [p("sl_pct_val", "table_cell"),        p("float",   "table_cell"), p("SL distance as a fraction of entry price (e.g. 0.02 = 2%).", "table_cell")],
    [p("tp_pct_val", "table_cell"),        p("float",   "table_cell"), p("TP distance as a fraction of entry price (always 2×sl_pct_val).", "table_cell")],
    [p("pos_fraction", "table_cell"),      p("float",   "table_cell"), p("Position size as a fraction of total capital (0 to 1.0).", "table_cell")],
    [p("pending_entry", "table_cell"),     p("int",     "table_cell"), p("Direction of a queued re-entry signal after a signal flip exit.", "table_cell")],
    [p("trade_min_low", "table_cell"),     p("float",   "table_cell"), p("Lowest Low seen since trade opened (used for MAE/MFE).", "table_cell")],
    [p("trade_max_high", "table_cell"),    p("float",   "table_cell"), p("Highest High seen since trade opened (used for MAE/MFE).", "table_cell")],
    [p("current_entry_idx", "table_cell"), p("Index",   "table_cell"), p("The bar index (timestamp) when the current trade was opened.", "table_cell")],
    [p("trade_sltp", "table_cell"),        p("dict",    "table_cell"), p("Maps each trade's entry bar → detailed price levels and exit info.", "table_cell")],
]
story.append(dark_table(vars_data, col_widths=[3.5*cm, 2*cm, 10.5*cm]))
story += [Spacer(1, 0.3*cm), PageBreak()]

# ── 7.2 Volatility-based SL sizing ───────────────────────────────────────────
story += [
    p("7.2  Volatility-Based Stop-Loss Sizing", "h2"),
    p("<b>Important note:</b> This is pure statistical mathematics — there is no machine learning "
      "or predictive model in this component. Stop-loss sizes are derived directly from "
      "the recent historical volatility of the asset using a rolling standard deviation.",
      "note"),

    p("Motivation", "h3"),
    p("A fixed stop-loss (e.g. always 2% below entry) is naive because market volatility "
      "varies enormously. On a quiet day for a large-cap stock, a 2% move is a major "
      "event. For a cryptocurrency on a volatile day, a 2% move might happen in minutes "
      "as normal noise. A fixed SL that is too tight relative to normal volatility will "
      "be triggered constantly by noise, resulting in a long sequence of small losses "
      "even when the overall trade direction is correct. A volatility-adaptive SL places "
      "the stop just beyond the range of typical noise for that specific asset at that "
      "specific moment."),

    p("Calculation", "h3"),
    p("At the moment a new trade is opened on bar i, the engine looks back at the "
      "most recent 20 closing prices (or fewer if less data is available) and computes "
      "their rolling standard deviation:"),
    p("window     =  min(20, i)", "formula"),
    p("pct_changes = Close[i-window : i].pct_change()", "formula"),
    p("per_bar_vol = standard_deviation(pct_changes)", "formula"),
    p("This gives a per-bar volatility expressed as a decimal fraction. For example, "
      "a per_bar_vol of 0.012 means the stock typically moves about 1.2% per bar."),

    p("Interval-specific bounds", "h3"),
    p("A stop-loss that is too tight will be hit constantly by noise; one that is too "
      "wide means risking an impractical amount of capital. The per_bar_vol is clamped "
      "to sensible bounds that have been set specifically for each timeframe:"),
]
bounds_data = [
    [p("Interval", "table_header"), p("Minimum SL", "table_header"), p("Maximum SL", "table_header"),
     p("Rationale", "table_header")],
    [p("1d",  "table_cell"), p("0.5%",  "table_cell"), p("10%",  "table_cell"),
     p("Daily moves rarely exceed 10% for major assets.", "table_cell")],
    [p("4h",  "table_cell"), p("0.3%",  "table_cell"), p("6%",   "table_cell"),
     p("4-hour candles cover half a trading session.", "table_cell")],
    [p("1h",  "table_cell"), p("0.2%",  "table_cell"), p("4%",   "table_cell"),
     p("Hourly moves are smaller than daily.", "table_cell")],
    [p("15m", "table_cell"), p("0.1%",  "table_cell"), p("1%",   "table_cell"),
     p("Very short bars — extremely tight SL bounds.", "table_cell")],
    [p("5m",  "table_cell"), p("0.05%", "table_cell"), p("0.5%", "table_cell"),
     p("5-minute bars — minimal meaningful movement.", "table_cell")],
]
story.append(dark_table(bounds_data, col_widths=[2*cm, 3*cm, 3*cm, 8*cm]))
story += [
    Spacer(1, 0.3*cm),
    p("np.clip(per_bar_vol, min_sl, max_sl)", "formula"),
    p("The final sl_pct_val is this clamped value. The SL price level is then:"),
    p("sl_price  =  entry_price × (1  -  sl_pct_val × direction)", "formula"),
    p("For a Long (+1): sl_price = entry × (1 - sl_pct_val)  →  below entry"),
    p("For a Short (-1): sl_price = entry × (1 + sl_pct_val) →  above entry", "formula"),
    PageBreak(),
]

# ── 7.3 Position Sizing ───────────────────────────────────────────────────────
story += [
    p("7.3  Position Sizing", "h2"),
    p("Position sizing answers the question: <i>what fraction of total capital should "
      "be deployed in this trade?</i> The platform offers two modes."),

    p("Mode 1: Fixed Risk Per Trade (default)", "h3"),
    p("The position size is calculated so that if the stop-loss is hit, the loss "
      "equals exactly risk_per_trade (default 2%) of total capital. This is sometimes "
      "called the '2% rule' and is one of the most widely used professional risk "
      "management frameworks."),
    p("pos_fraction  =  min( risk_per_trade / sl_pct_val,  1.0 )", "formula"),
    p("Example: risk_per_trade=0.02 (2%), sl_pct_val=0.01 (1%).", "note"),
    p("pos_fraction = 0.02 / 0.01 = 2.0 → clamped to 1.0 (100% of capital, no leverage).", "note"),
    p("Example: risk_per_trade=0.02 (2%), sl_pct_val=0.04 (4%).", "note"),
    p("pos_fraction = 0.02 / 0.04 = 0.50 (50% of capital deployed).", "note"),
    p("When sl_pct_val is wide (high volatility), the position is sized down so the "
      "monetary risk remains constant. When sl_pct_val is tight (low volatility), "
      "the position is sized up, but never beyond 100%."),

    p("Mode 2: Volatility Targeting (optional)", "h3"),
    p("When enabled, position sizes are calculated to target a specified level of "
      "annualised portfolio volatility (e.g. 15% per year) regardless of individual "
      "trade risk. This is a portfolio-level risk management approach used by many "
      "systematic hedge funds."),
    p("ann_vol      =  per_bar_vol × sqrt(periods_per_year)", "formula"),
    p("pos_fraction =  min( vol_target / ann_vol,  1.0 )", "formula"),
    p("per_bar_vol is the same rolling 20-bar standard deviation used for SL sizing. "
      "periods_per_year converts it to an annualised figure (252 for daily, 1638 for "
      "hourly, etc). If the current annualised vol is 30% and the target is 15%, "
      "pos_fraction = 15/30 = 0.5 — deploy 50% of capital."),
    p("During high-volatility periods, the strategy automatically reduces size; "
      "during low-volatility periods, it increases size. This tends to produce more "
      "consistent risk-adjusted returns over time, but individual trade wins/losses "
      "can be larger than with fixed risk.", "note"),
    PageBreak(),
]

# ── 7.4 TP Calculation ───────────────────────────────────────────────────────
story += [
    p("7.4  Take-Profit Calculation", "h2"),
    p("The take-profit distance is always exactly twice the stop-loss distance. "
      "This means the reward-to-risk ratio (R:R) of every trade is 2:1 by design."),
    p("tp_pct_val  =  2.0 × sl_pct_val", "formula"),
    p("tp_price    =  entry_price × (1  +  tp_pct_val × direction)", "formula"),
    p("For a Long (+1): tp_price = entry × (1 + tp_pct_val)  →  above entry"),
    p("For a Short (-1): tp_price = entry × (1 - tp_pct_val) →  below entry", "formula"),
    p("Why 2:1?", "h3"),
    p("A 2:1 reward-to-risk ratio means the strategy only needs to win 34% of trades "
      "to break even (before costs). For example: 10 trades, 3 winners (+2%) and "
      "7 losers (-1%). Net = 3×2% - 7×1% = 6% - 7% = -1% (near breakeven at 30% "
      "win rate). Most strategies with genuine edge achieve win rates above 35%, "
      "making a 2:1 R:R profitable over time."),
    p("A fixed R:R also makes the strategy simple and transparent. More sophisticated "
      "systems use variable targets based on volatility projections or support/resistance "
      "levels, but these introduce additional complexity and more parameters to overfit."),

    p("7.5  Commission & Slippage", "h2"),
    p("Both commission and slippage reduce the return of every trade by being "
      "subtracted at exit:"),
    p("rt_cost  =  (2 × commission_pct  +  2 × slippage_pct) × pos_fraction", "formula"),
    p("strategy_return[exit bar]  -=  rt_cost", "formula"),
    p("The factor of 2 accounts for both entry and exit legs of the trade. "
      "commission_pct covers broker fees (e.g. 0.05% per leg = 0.1% round trip). "
      "slippage_pct covers the cost of market impact — the fact that large orders "
      "move the price against the trader slightly at both entry and exit. "
      "Both are expressed as fractions of the position value, and both are scaled "
      "by pos_fraction so a smaller position incurs proportionally smaller costs."),
    PageBreak(),
]

# ── 7.6 Pending Entry ─────────────────────────────────────────────────────────
story += [
    p("7.6  Signal Re-Entry — The Pending Entry Mechanism", "h2"),
    p("Because signals are event-based (fire on exactly one bar), a subtle re-entry "
      "problem must be handled carefully. The scenario is:"),
    bullet([
        "Bar N: Long signal fires. Trade opens long.",
        "Bar M: Short signal fires. Long trade closes on bar M. At the same moment, a short trade should open.",
        "But: the short signal was on bar M. The bar M close is used as the exit price for the long trade. If we also enter short on bar M, we are entering and exiting on the same bar — possible in theory but requires careful logic.",
    ]),
    p("The platform uses a <b>pending_entry</b> variable to queue the opposite direction "
      "for the next available bar:"),
    bullet([
        "When a trade exits because the signal flipped, the new direction is saved as pending_entry.",
        "The just_exited flag is set to True for the current bar, preventing any new trade from opening immediately.",
        "On the very next bar (bar M+1), pending_entry is read and a new trade opens in the queued direction.",
        "Any new real signal arriving on a later bar overrides and clears pending_entry.",
    ]),
    p("This correctly models the real-world constraint: you can't simultaneously exit "
      "one position and enter the reverse position at exactly the same price — there "
      "is at minimum a one-tick spread between the two fills."),
    PageBreak(),
]


# ══════════════════════════════════════════════════════════════════════════════
# 8  PERFORMANCE METRICS
# ══════════════════════════════════════════════════════════════════════════════
story += [
    p("8. Performance Metrics", "h1"), hr(),
    p("The following metrics are computed after the backtest loop completes and "
      "displayed in the Backtest Results tab. Every metric is derived from the "
      "strategy_returns series (per-bar returns) and the trade_log DataFrame."),
    Spacer(1, 0.2*cm),
]

metrics_sections = [
    (
        "Total Return (%)",
        "The cumulative compounded return of the strategy over the entire backtest period.",
        "Equity Curve[-1]  -  1.0",
        "Where Equity Curve starts at 1.0 and compounds: EC[t] = EC[t-1] × (1 + r[t]). "
        "A Total Return of 45.2% means £10,000 grew to £14,520 over the period.",
    ),
    (
        "Annualised Return (%)",
        "The geometric annual growth rate — what average yearly return would compound to the total return over the period.",
        "Annualised Return  =  (1 + Total Return)^(1 / years)  -  1",
        "years = number of bars / periods_per_year. This normalises returns across "
        "different-length backtests so they can be compared. A 3-year backtest with "
        "50% total return annualises to approximately 14.5% per year.",
    ),
    (
        "Max Drawdown (%)",
        "The largest peak-to-trough decline in the equity curve at any point during the backtest. "
        "It measures the worst loss experienced by an investor who bought at the worst possible moment.",
        "Rolling Peak[t]  =  max(Equity Curve[0..t])\n"
        "Drawdown[t]      =  (Equity Curve[t]  -  Rolling Peak[t]) / Rolling Peak[t]\n"
        "Max Drawdown     =  min(Drawdown[t])  over all t",
        "Max Drawdown is always negative (or zero). A Max Drawdown of -20% means the "
        "strategy at some point lost 20% of its peak value. This is the most important "
        "measure of downside risk — it represents the actual experience of an investor "
        "who held through the strategy's worst period.",
    ),
    (
        "Sharpe Ratio",
        "The risk-adjusted return per unit of total volatility. It answers: how much return "
        "did the strategy earn per unit of risk taken? Higher is better; a ratio above 1.0 "
        "is generally considered good.",
        "Sharpe  =  mean(returns) / std(returns)  ×  sqrt(periods_per_year)",
        "Returns here are per-bar strategy returns. The sqrt(periods_per_year) factor "
        "annualises the ratio so it is comparable across timeframes. The denominator "
        "is total volatility — both upside and downside moves. A Sharpe of 1.5 means "
        "the strategy earned 1.5 units of return for every unit of volatility. "
        "A Sharpe below 0 means the strategy lost money on average. "
        "Unusually high Sharpe ratios (above 3–4 on daily data) can indicate look-ahead "
        "bias or data errors.",
    ),
    (
        "Sortino Ratio",
        "Like Sharpe, but penalises only downside volatility (negative returns) rather than "
        "total volatility. This is more appropriate for asymmetric return distributions — "
        "it doesn't penalise large upside moves the way Sharpe does.",
        "Downside Deviation  =  std(returns where returns < 0)\n"
        "Sortino             =  mean(returns) / Downside Deviation  ×  sqrt(periods_per_year)",
        "A strategy with large winning trades and small losing trades will have a "
        "Sortino ratio significantly higher than its Sharpe ratio. The two together "
        "give a more complete picture of the risk/return profile.",
    ),
    (
        "Calmar Ratio",
        "The annualised return divided by the maximum drawdown. It answers: how much "
        "annual return did the strategy earn per unit of maximum pain suffered?",
        "Calmar  =  Annualised Return  /  |Max Drawdown|",
        "A Calmar of 1.0 means the strategy earns one year of annual return for "
        "every point of max drawdown. A Calmar of 0.5 means it would take 2 years "
        "of gains to recover from the worst historical drawdown. Hedge funds typically "
        "target Calmar ratios above 0.5; ratios above 2.0 are exceptional.",
    ),
    (
        "Win Rate (%)",
        "The percentage of completed trades that were profitable.",
        "Win Rate  =  (Number of trades with Return > 0)  /  (Total Trades)  ×  100",
        "Note: this is trade-level win rate, not bar-level. A trade is profitable if "
        "its total compounded return across all bars it was open is greater than zero. "
        "With a 2:1 reward/risk ratio, a strategy needs a win rate above approximately "
        "34% to be profitable before costs. Most systematic strategies win between "
        "35% and 55% of trades.",
    ),
    (
        "Long Win Rate / Short Win Rate (%)",
        "Win rates broken down separately for long and short trades. "
        "These reveal directional biases in the strategy's performance.",
        "Long Win Rate   =  Winning Long Trades  /  Total Long Trades  ×  100\n"
        "Short Win Rate  =  Winning Short Trades / Total Short Trades  ×  100",
        "For example, a strategy might have a 50% long win rate but only a 30% short "
        "win rate — suggesting the asset trends upward and short signals are less reliable. "
        "These metrics are only shown when at least some trades exist in that direction.",
    ),
    (
        "Exposure (%)",
        "The percentage of total bars during which the strategy held an open position. "
        "A strategy with low exposure spends most of its time in cash.",
        "Exposure  =  bars where strategy_return ≠ 0  /  total bars  ×  100",
        "Low exposure (e.g. 20%) means the strategy is selective and only in the "
        "market 20% of the time. High exposure (e.g. 80%) means it is almost always "
        "in a position. Low exposure reduces risk but may also reduce returns. "
        "Comparing the Sharpe ratio to exposure tells you whether the strategy earns "
        "its returns efficiently or just by being long a rising market most of the time.",
    ),
    (
        "Number of Trades",
        "The total count of completed trades over the backtest period.",
        "Count of rows in the trade log.",
        "Statistical reliability requires a minimum number of trades to draw meaningful "
        "conclusions. With fewer than 20–30 trades, all metrics have very wide confidence "
        "intervals — the results could be due to luck rather than genuine strategy edge. "
        "The platform warns when fewer than 10 trades were generated.",
    ),
]

for name, description, formula, commentary in metrics_sections:
    story += [
        p(name, "h3"),
        p(description),
        p(formula, "formula"),
        p(commentary, "body"),
        Spacer(1, 0.2*cm),
    ]

story.append(PageBreak())


# ══════════════════════════════════════════════════════════════════════════════
# 9  TRADE LOG
# ══════════════════════════════════════════════════════════════════════════════
story += [
    p("9. Trade Log Columns", "h1"), hr(),
    p("Every completed trade produces one row in the trade log. The columns are:"),
    Spacer(1, 0.2*cm),
]

tl_data = [
    [p("Column", "table_header"), p("Type", "table_header"), p("Description", "table_header")],
    [p("Entry Date",   "table_cell"), p("Timestamp", "table_cell"),
     p("The bar index (date/time) at which the trade was opened.", "table_cell")],
    [p("Exit Date",    "table_cell"), p("Timestamp", "table_cell"),
     p("The bar at which the trade was closed.", "table_cell")],
    [p("Entry Price",  "table_cell"), p("float",     "table_cell"),
     p("The closing price of the bar just before entry — used as the fill price proxy.", "table_cell")],
    [p("SL Price",     "table_cell"), p("float",     "table_cell"),
     p("The stop-loss price level calculated at entry (entry × (1 ± sl_pct_val)).", "table_cell")],
    [p("TP Price",     "table_cell"), p("float",     "table_cell"),
     p("The take-profit price level calculated at entry (entry × (1 ± tp_pct_val)).", "table_cell")],
    [p("Exit Price",   "table_cell"), p("float",     "table_cell"),
     p("The actual exit fill price: sl_price if SL hit, tp_price if TP hit, or the close price if exited by signal or end of data.", "table_cell")],
    [p("Exit Reason",  "table_cell"), p("string",    "table_cell"),
     p("'SL' — stop-loss triggered. 'TP' — take-profit triggered. 'Signal' — a reversal signal caused the exit. 'End' — trade was open at the end of the data.", "table_cell")],
    [p("Direction",    "table_cell"), p("string",    "table_cell"),
     p("'Long' or 'Short'.", "table_cell")],
    [p("Return (%)",   "table_cell"), p("float",     "table_cell"),
     p("The compounded total return of the trade including all commission and slippage costs. Expressed as a percentage.", "table_cell")],
    [p("Bars Held",    "table_cell"), p("int",       "table_cell"),
     p("The number of bars the trade was open — from entry bar to exit bar.", "table_cell")],
    [p("MAE (%)",      "table_cell"), p("float",     "table_cell"),
     p("Maximum Adverse Excursion — the worst intra-trade drawdown from entry price, as a percentage. For a Long: (Entry - Trade Min Low) / Entry × 100. Measures how far against you the trade went at its worst point.", "table_cell")],
    [p("MFE (%)",      "table_cell"), p("float",     "table_cell"),
     p("Maximum Favourable Excursion — the best intra-trade gain from entry price, as a percentage. For a Long: (Trade Max High - Entry) / Entry × 100. Measures how far in your favour the trade went at its best point.", "table_cell")],
]
story.append(dark_table(tl_data, col_widths=[2.5*cm, 2.2*cm, 11.3*cm]))
story += [
    Spacer(1, 0.4*cm),
    p("Using MAE and MFE together", "h3"),
    bullet([
        "If most trades show large MFE but small final Return, the TP may be placed too close — the trade often went well past the TP before reversing.",
        "If MAE is frequently much larger than the final loss (SL exits), the SL may be placed too tight and triggering on normal noise.",
        "If MAE ≈ final loss for SL-exited trades, the SL is well-placed relative to the trade's actual adverse movement.",
        "A trade with MFE of 5% but Return of -1% suggests poor exit timing or an SL that was hit after a reversal from a profitable position.",
    ]),
    PageBreak(),
]


# ══════════════════════════════════════════════════════════════════════════════
# 10  PARAMETER SWEEP
# ══════════════════════════════════════════════════════════════════════════════
story += [
    p("10. Parameter Sweep", "h1"), hr(),
    p("The Parameter Sweep tab runs a full backtest for every combination of two "
      "selected parameters across a configurable grid of values. The results are "
      "displayed as a table and as a Sharpe Ratio heatmap, making it easy to "
      "identify which parameter combinations perform best."),

    p("How it works", "h2"),
    p("The sweep uses a Cartesian product of all parameter values. If you choose "
      "4 steps for each of 2 parameters, the sweep runs 4×4 = 16 backtests. "
      "With 3 parameters at 4 steps each, it runs 4³ = 64 backtests."),
    p("For each combination, the strategy function is called with those parameter "
      "values to generate signals, run_backtest is called on those signals, and the "
      "resulting metrics are stored. All non-swept parameters use their default values "
      "from the strategy registry."),

    p("The linspace grid", "h3"),
    p("Parameter values are generated using numpy's linspace — evenly spaced values "
      "between the parameter's minimum and maximum bounds. For integer parameters "
      "(like period lengths), the values are rounded to integers. For float parameters, "
      "they are rounded to 2 decimal places."),
    p("n_steps=4 for integer param range [2, 50]:  → [2, 18, 34, 50]", "formula"),
    p("n_steps=4 for float param range [0.5, 4.0]:  → [0.5, 1.5, 2.5, 4.0]", "formula"),

    p("Minimum trades filter", "h3"),
    p("The min_trades slider (default 10) hides parameter combinations that generated "
      "fewer than the specified number of trades. This prevents the heatmap from "
      "highlighting parameter combinations that look excellent on paper but only "
      "executed 1 or 2 trades — which would be entirely due to luck."),

    p("The heatmap", "h2"),
    p("After all backtests complete, the results are pivoted so that one parameter "
      "forms the X axis and the other forms the Y axis, with each cell coloured by "
      "the Sharpe Ratio. The colour scale runs from red (low/negative Sharpe) through "
      "yellow to green (high Sharpe)."),
    p("Looking for smooth gradients in the heatmap rather than isolated peaks is "
      "important: a single bright green cell surrounded by red cells indicates "
      "overfitting — those exact parameter values happen to work on this historical "
      "data but are unlikely to generalise. A broad region of green cells indicates "
      "robust parameters that work well across a range of values."),

    p("Limitations and warnings", "h2"),
    bullet([
        "<b>In-sample optimisation:</b> Any parameters selected using the sweep have been optimised on the same data used to evaluate them. This is called in-sample fitting. The metrics shown in the heatmap are optimistically biased — real out-of-sample performance will typically be worse.",
        "<b>Combinatorial explosion:</b> Adding a third parameter to the sweep makes it N³ backtests. 8 steps × 8 steps × 8 steps = 512 backtests. The platform warns about this in the UI.",
        "<b>The sweep finds the past's best parameters:</b> Even a genuine robust region in the heatmap may not remain the best region in the future. Markets change regimes — a slow-period of 50 that worked for 3 years of trending market may fail in a subsequent ranging market.",
        "<b>Use as hypothesis generation, not final selection:</b> Use the sweep to understand how sensitive the strategy is to parameter choices, not to pick the single best combination and trust it blindly.",
    ]),
    Spacer(1, 0.5*cm),
    hr(),
    Spacer(1, 0.3*cm),
    p("End of Documentation", "caption"),
    p("Trading Research Platform  —  All strategies are for research and educational purposes only. "
      "Past performance does not guarantee future results.", "caption"),
]


# ══════════════════════════════════════════════════════════════════════════════
# BUILD
# ══════════════════════════════════════════════════════════════════════════════
doc.build(story)
print(f"PDF written to: {OUTPUT}")
