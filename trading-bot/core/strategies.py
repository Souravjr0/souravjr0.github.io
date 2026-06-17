from dataclasses import dataclass
import numpy as np
import pandas as pd
from advanced_skills import analyze_advanced

@dataclass(frozen=True)
class SignalSummary:
    direction: str
    score: str
    stop: float | None
    take: float | None
    per_strategy: dict[str, str]
    chandelier_stop: float | None = None


def add_strategy_signals(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    close = df["close"]
    ema_fast = df["ema_fast"]
    ema_slow = df["ema_slow"]
    
    # 1. EMA Crossover + RSI Strategy
    cross_up = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
    cross_down = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))
    ema_rsi_signal = np.where(
        cross_up & (df["rsi14"] > 50),
        1,
        np.where(cross_down & (df["rsi14"] < 50), -1, 0),
    )
    df["signal_ema_rsi"] = ema_rsi_signal

    # 2. Donchian Channel Breakout Strategy
    donchian_high = df["donchian_high"].shift(1)
    donchian_low = df["donchian_low"].shift(1)
    breakout_signal = np.where(
        close > donchian_high,
        1,
        np.where(close < donchian_low, -1, 0),
    )
    df["signal_breakout"] = breakout_signal

    # 3. Mean Reversion Strategy (RSI + BB)
    bb_mid = df.get("bb_mid", close.rolling(20).mean())
    bb_lower = df.get("bb_lower", bb_mid - 2 * close.rolling(20).std())
    bb_upper = df.get("bb_upper", bb_mid + 2 * close.rolling(20).std())
    
    mean_rev_signal = np.where(
        (df["rsi14"] < 30) | (close <= bb_lower),
        1,
        np.where((df["rsi14"] > 70) | (close >= bb_upper), -1, 0),
    )
    df["signal_mean_rev"] = mean_rev_signal

    return df


def _signal_label(value: float) -> str:
    if value > 0:
        return "LONG"
    if value < 0:
        return "SHORT"
    return "NEUTRAL"


def _atr_levels(
    close: float,
    atr: float | None,
    direction: str,
    atr_mult_sl: float,
    atr_mult_tp: float,
) -> tuple[float | None, float | None]:
    if atr is None or np.isnan(atr) or direction == "NEUTRAL":
        return None, None
    if direction == "LONG":
        return close - atr * atr_mult_sl, close + atr * atr_mult_tp
    if direction == "SHORT":
        return close + atr * atr_mult_sl, close - atr * atr_mult_tp
    return None, None

def evaluate_latest_signals(
    df: pd.DataFrame,
    atr_mult_sl: float,
    atr_mult_tp: float,
    ml_signal: str | None = None,
    ml_confidence: float = 0.0,
    tv_rating: str | None = None,
    strategy_weights: dict[str, float] | None = None,
    consensus_threshold: float | None = None,
) -> SignalSummary:
    """Evaluate 7 to 8-indicator consensus (Super-Consensus) strategy including optional ML and TradingView signals."""
    df = add_strategy_signals(df)
    last = df.iloc[-1]
    
    # 1. Base technical strategy outputs
    per_strategy = {
        "EMA_RSI": _signal_label(last.get("signal_ema_rsi", 0)),
        "BREAKOUT": _signal_label(last.get("signal_breakout", 0)),
        "MEAN_REV": _signal_label(last.get("signal_mean_rev", 0)),
    }
    
    # 2. Add Premium skills indicators
    adv = analyze_advanced(df)
    
    # Supertrend
    st = adv.get("supertrend", 0)
    per_strategy["SUPERTREND"] = "LONG" if st == 1 else "SHORT" if st == -1 else "NEUTRAL"
    
    # Ichimoku
    ichi_bull = adv.get("ichi_bull")
    per_strategy["ICHIMOKU"] = "LONG" if ichi_bull is True else "SHORT" if ichi_bull is False else "NEUTRAL"
    
    # Squeeze Momentum
    sq_on = adv.get("squeeze_on", False)
    sq_mom = adv.get("squeeze_mom", 0.0)
    sq_dir = adv.get("squeeze_dir", "NEUTRAL")
    
    if not sq_on and sq_mom != 0.0:  # Squeeze released, trade active momentum
        if sq_mom > 0 and sq_dir == "UP":
            per_strategy["SQUEEZE"] = "LONG"
        elif sq_mom < 0 and sq_dir == "DOWN":
            per_strategy["SQUEEZE"] = "SHORT"
        else:
            per_strategy["SQUEEZE"] = "NEUTRAL"
    else:
        per_strategy["SQUEEZE"] = "NEUTRAL"
        
    # 3. Add ML Signal as 7th indicator
    if ml_signal is not None:
        if ml_signal == "BUY":
            per_strategy["ML_SIGNAL"] = "LONG"
        elif ml_signal == "SELL":
            per_strategy["ML_SIGNAL"] = "SHORT"
        else:
            per_strategy["ML_SIGNAL"] = "NEUTRAL"

    # 3b. Add TradingView Scanner Rating as 8th indicator
    if tv_rating is not None:
        if tv_rating in {"STRONG BUY", "BUY"}:
            per_strategy["TV_RATING"] = "LONG"
        elif tv_rating in {"STRONG SELL", "SELL"}:
            per_strategy["TV_RATING"] = "SHORT"
        else:
            per_strategy["TV_RATING"] = "NEUTRAL"

    # Count votes across indicators (ML has weight 1.5 if confidence > 0.80)
    has_ml = "ML_SIGNAL" in per_strategy
    has_tv = "TV_RATING" in per_strategy
    
    total_indicators = 6
    if has_ml:
        total_indicators += 1
    if has_tv:
        total_indicators += 1
    
    def get_votes(direction_val: str) -> float:
        votes = 0.0
        for k, v in per_strategy.items():
            if v == direction_val:
                weight = 1.0
                if strategy_weights and k in strategy_weights:
                    weight = strategy_weights[k]
                
                if k == "ML_SIGNAL" and ml_confidence > 0.80:
                    votes += weight * 1.5
                else:
                    votes += weight
        return votes

    long_votes = get_votes("LONG")
    short_votes = get_votes("SHORT")
    
    if consensus_threshold is not None:
        threshold = consensus_threshold
    else:
        threshold = 4.0 if total_indicators <= 7 else 5.0
    
    def format_score(votes: float) -> str:
        v_str = str(int(votes)) if votes.is_integer() else f"{votes:.1f}"
        return f"{v_str}/{total_indicators}"

    if long_votes >= threshold:
        direction = "LONG"
        score = format_score(long_votes)
    elif short_votes >= threshold:
        direction = "SHORT"
        score = format_score(short_votes)
    else:
        direction = "NEUTRAL"
        score = format_score(max(long_votes, short_votes))
        
    atr = last.get("atr14")
    close = float(last["close"])
    
    # Traditional ATR-based stops
    stop, take = _atr_levels(close, atr, direction, atr_mult_sl, atr_mult_tp)
    
    # Premium Trailing Stops: Chandelier Exit stop levels
    chandelier_stop = None
    if direction == "LONG":
        chandelier_stop = adv.get("chandelier_long")
    elif direction == "SHORT":
        chandelier_stop = adv.get("chandelier_short")
        
    return SignalSummary(
        direction=direction,
        score=score,
        stop=stop,
        take=take,
        per_strategy=per_strategy,
        chandelier_stop=chandelier_stop
    )

