# Systematic Trading Platform

A Python/Streamlit platform for building, backtesting, and stress-testing systematic trading strategies — spanning trend-following, mean-reversion, and price-action signals — with a backtest engine designed around realistic execution and strict look-ahead-bias prevention.

Full technical documentation (signal formulas, engine mechanics, and methodology) is included in this repo: `docs/Trading_Platform_Documentation_v2.pdf`.

## What it does

The platform lets you construct a strategy from a library of signals, configure entry/exit logic and risk management, and run it through a bar-by-bar backtest engine that produces performance metrics, an equity curve, and a full trade log, across four tabs: Strategy Builder, Signal Diagnostics, Backtest Results, and Trade Analysis.

Four ways to build a strategy:
- **Trend/Momentum Builder** — 12 signal generators (SMA/EMA crossover, MACD crossover/histogram, Donchian, Turtle breakout, ADX+DI, SuperTrend, Parabolic SAR, TSMOM, Price vs MA, MA Slope)
- **Mean Reversion Builder** — 6 signal generators (Z-Score, Bollinger Bands, RSI, Short-Term Reversal, MA Deviation, Range Reversion)
- **Price Action Builder** — 4 signal generators (Engulfing, Pin Bar, Inside Bar, Opening Range Breakout)
- **Classic Multi-Strategy Mode** — combine multiple strategies (SMA Crossover, MACD, Donchian, ADX, Ichimoku, Time-Series Momentum, RSI, Stochastic RSI, Bollinger Bands, Z-Score) via majority vote, weighted average, or threshold-based consensus

Three further families — Volatility, Cross-Sectional/Relative Value, and Carry/Yield — are scaffolded in the UI as a roadmap but not yet functional.

## Key features

- **Look-ahead-bias prevention** — every signal is shifted one full bar before being acted on, enforced at a single point in the engine
- **Volatility-based risk management** — ATR-based stop-loss/take-profit sizing, configurable reward-to-risk ratio, optional trailing stops
- **Position sizing** — fixed fractional risk-per-trade or volatility-targeting, matching approaches used by CTA/systematic macro funds
- **Realistic execution modeling** — commission and slippage applied symmetrically on entry and exit, SL/TP hit detection using intrabar highs/lows rather than close-only prices
- **Signal combination** — majority vote, weighted average, and threshold methods for combining multiple strategies into one composite signal
- **Parameter sweep** — grid search over two parameters with a heatmap visualization, with a minimum-trade-count filter to screen out statistically meaningless combinations
- **Full performance suite** — Sharpe, Sortino, Calmar, max drawdown, win rate (overall/long/short), exposure, MAE/MFE per trade
- **ML-assisted volatility forecasting** — a scikit-learn RandomForestRegressor (`volatility.py`) forecasts short-horizon realised volatility from technical features, trained with walk-forward cross-validation and cached under `models/`

## Tech stack

Python · Streamlit · pandas · NumPy · yfinance · scikit-learn · Plotly

## Project structure

```
app.py           # Streamlit UI entry point — wires everything together across four tabs
data.py          # OHLCV data ingestion (Yahoo Finance via yfinance), cleaning, session caching
strategies.py    # All 22 signal generators, signal combination, entry/exit logic, filters
backtest.py      # Bar-by-bar simulation engine — positions, SL/TP, returns, all metrics
utils.py         # Shared helpers, annualisation factors, Plotly charting functions
volatility.py    # RandomForestRegressor-based volatility forecasting and caching
docs/            # Technical documentation (PDF/HTML)
models/          # Cached trained model artifacts
```

## Getting started

```bash
git clone https://github.com/Jack-Close/Systematic-Trading-Platform.git
cd Systematic-Trading-Platform
pip install -r requirements.txt
streamlit run app.py
```

## Disclaimer

Built for research and educational purposes. Nothing here is investment advice, and past backtested performance does not guarantee future results.
