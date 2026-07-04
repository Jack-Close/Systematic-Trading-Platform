"""
volatility.py — Volatility forecasting using a RandomForestRegressor.

Imports: nothing from this project (self-contained ML module).
Exports: build_vol_features, train_vol_model, forecast_volatility.

Walk-forward cross-validation is used instead of a random split because
financial data is sequential: training on future data to predict past data
would be data leakage and produce misleadingly good CV scores.
"""

import numpy as np
import pandas as pd
import joblib
import ta
import os
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

TRADING_DAYS_PER_YEAR = 252

_PERIODS_PER_YEAR = {
    "1d":  252.0,
    "1h":  252.0 * 6.5,
    "4h":  252.0 * 6.5 / 4,
    "15m": 252.0 * 6.5 * 4,
    "5m":  252.0 * 6.5 * 12,
}

def _periods_per_year(interval: str) -> float:
    return _PERIODS_PER_YEAR.get(interval, 252.0)

_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")


def _vol_model_path(interval: str, ticker: str = "") -> str:
    os.makedirs(_MODELS_DIR, exist_ok=True)
    safe = ticker.upper().replace("/", "-") if ticker else ""
    prefix = f"{safe}_" if safe else ""
    return os.path.join(_MODELS_DIR, f"{prefix}vol_model_{interval}.joblib")


def build_vol_features(df: pd.DataFrame, horizon: int = 5, interval: str = "1d") -> Tuple[pd.DataFrame, pd.Series]:
    """
    Engineer features and target variable for volatility prediction.

    Parameters
    ----------
    df      : OHLCV DataFrame from data.py.
    horizon : Forecast horizon in bars — target is realised vol over next
              `horizon` bars.

    Returns
    -------
    (X, y) where X is a feature DataFrame and y is the target Series.

    Target definition
    -----------------
    y = rolling std of log returns over the *next* horizon bars × sqrt(horizon)
    This is realised volatility — the thing we're trying to predict.
    # Why: annualised vol = daily vol × sqrt(252); here we just scale by
    # sqrt(horizon) so the units are consistent regardless of horizon.
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    log_ret = np.log(close / close.shift(1))
    ann     = _periods_per_year(interval)

    feats = pd.DataFrame(index=df.index)

    # Historical vol at multiple windows — the single strongest predictor of
    # future vol (vol clusters: high vol tends to follow high vol)
    for w in [5, 10, 20]:
        feats[f"hvol_{w}"] = log_ret.rolling(w).std() * np.sqrt(ann)

    feats["log_ret"] = log_ret
    feats["abs_ret"] = log_ret.abs()

    # RSI as regime indicator — extreme readings often precede vol spikes
    feats["rsi"] = ta.momentum.RSIIndicator(close, window=14).rsi()

    # MACD histogram — strong momentum can mean trending (lower vol) or
    # blow-off tops (higher vol)
    macd = ta.trend.MACD(close)
    feats["macd_hist"] = macd.macd_diff()

    # ADX — trend strength
    adx_ind = ta.trend.ADXIndicator(high, low, close, window=14)
    feats["adx"] = adx_ind.adx()

    # Seasonal features — volatility has known day-of-week and month patterns
    feats["day_of_week"] = df.index.dayofweek
    feats["month"] = df.index.month

    # Target: forward realised volatility
    # Rolling std uses shift so we don't include the current bar
    # min_periods=max(2, horizon//2) allows partial windows near the end
    target = (
        log_ret.shift(-1)
        .rolling(horizon, min_periods=max(2, horizon // 2))
        .std()
        * np.sqrt(horizon)
    )

    # Align and drop NaN rows
    combined = feats.join(target.rename("target")).dropna()
    X = combined.drop(columns=["target"])
    y = combined["target"]
    return X, y


def train_vol_model(
    df: pd.DataFrame,
    horizon: int = 5,
    n_folds: int = 5,
    force_retrain: bool = False,
    interval: str = "1d",
    ticker: str = "",
) -> Tuple[RandomForestRegressor, List[str], float, pd.Series]:
    """
    Train (or load from disk) a RandomForestRegressor to forecast volatility.

    Walk-forward cross-validation is used: the dataset is split into
    `n_folds` time-ordered chunks.  For each fold, all prior folds are used
    for training and the current fold for evaluation.

    Parameters
    ----------
    df            : OHLCV DataFrame.
    horizon       : Forecast horizon in bars.
    n_folds       : Number of walk-forward CV folds.
    force_retrain : If True, ignore cached model and retrain from scratch.

    Returns
    -------
    (model, feature_names, cv_mae, latest_forecast_series)
        model              — fitted RandomForestRegressor
        feature_names      — list of feature column names
        cv_mae             — mean absolute error across CV folds
        latest_forecast    — pd.Series of in-sample predictions (for charting)
    """
    model_path = _vol_model_path(interval, ticker)
    if not force_retrain and os.path.exists(model_path):
        model = joblib.load(model_path)
        X, y = build_vol_features(df, horizon, interval)
        preds = pd.Series(model.predict(X), index=X.index)
        return model, list(X.columns), float("nan"), preds

    X, y = build_vol_features(df, horizon, interval)
    n = len(X)
    fold_size = n // (n_folds + 1)

    maes = []
    for fold in range(1, n_folds + 1):
        train_end = fold * fold_size
        test_end = train_end + fold_size

        X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]
        X_test, y_test = X.iloc[train_end:test_end], y.iloc[train_end:test_end]

        if len(X_test) == 0:
            continue

        m = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        m.fit(X_train, y_train)
        preds_fold = m.predict(X_test)
        maes.append(mean_absolute_error(y_test, preds_fold))

    cv_mae = float(np.mean(maes)) if maes else float("nan")

    # Final model: train on all data
    model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(X, y)
    joblib.dump(model, model_path)

    full_preds = pd.Series(model.predict(X), index=X.index)
    return model, list(X.columns), cv_mae, full_preds


def predict_vol_series(
    model: RandomForestRegressor,
    df: pd.DataFrame,
    feature_names: List[str],
    horizon: int = 5,
    interval: str = "1d",
) -> pd.Series:
    """
    Generate a volatility prediction series for any price DataFrame.

    Used to produce out-of-sample (test-period) forecasts after a model
    has been trained on a different (training) period.
    """
    X, _ = build_vol_features(df, horizon, interval)
    if X.empty:
        return pd.Series(dtype=float)
    preds = model.predict(X[feature_names].fillna(0))
    return pd.Series(preds, index=X.index)


def forecast_volatility(
    model: RandomForestRegressor,
    df: pd.DataFrame,
    feature_names: List[str],
    horizon: int = 5,
    interval: str = "1d",
) -> float:
    """
    Produce a single-point volatility forecast using the latest available bar.

    Parameters
    ----------
    model         : Fitted RandomForestRegressor.
    df            : OHLCV DataFrame (needs enough history for features).
    feature_names : Feature column names the model was trained on.
    horizon       : Same horizon used during training.

    Returns
    -------
    float — predicted annualised volatility for the next `horizon` bars.
    """
    X, _ = build_vol_features(df, horizon, interval)
    if X.empty:
        return float("nan")

    latest = X[feature_names].iloc[[-1]]
    return float(model.predict(latest)[0])
