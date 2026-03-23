import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import config
import uvicorn
from data_manager import DataManager, InstrumentDataFrame
from leaderboard import add_entry, get_entries, delete_all, delete_one

app = FastAPI()


CHECK_INTERVAL_HIST = 0 #0.005
PAUSE_INTERVAL_HIST = 0 #0.03
INSTRUMENT = "XAU_USD"
GRANULARITY_ENTRY = "M5"
GRANULARITY_TREND = "H1" #"H1" uses this one timeframe for general trend direction
CANDLES_TO_LOAD_HIST = 20000  # reduced for testing
SR_WINDOW_BOUNDS = 500
PLOT_ENABLED = False
TREND_DIRECTION_ENABLED = True
SHORT_ENABLED = False
LONG_ENABLED = True

START_DATE = "2025-02-06T23:59:59Z"

RSI_PERIOD = 14
BB_PERIOD = 20 #20
BB_STD = 2
RVOL_THRESHOLD = 1.5
SLTP_RATIO = 3


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================
# API ENDPOINT
# ==============================
@app.get("/backtest")
def run_backtest(
    num_candles: int = Query(20000),
    bb_period: int = Query(20),
    longs_enabled: bool = Query(True),
    shorts_enabled: bool = Query(False),
    trend_enabled: bool = Query(False),
    granularity: str = Query("M5"),
    rsi_period: int = Query(14),
    bb_std: float = Query(2),
    rvol_threshold: float = Query(1.5),
    atr_chop_enabled: bool = Query(False),
    start_date: str = Query(None),
    reinvest_enabled: bool = Query(False),
    initial_capital: float = Query(10000),
    leverage: float = Query(1),
    trading_start_time: str = Query("05:00"),
    trading_end_time: str = Query("17:00"),
    sl_multiplier: float = Query(1.0)
):
    from datetime import datetime, timedelta, timezone
    if start_date is None:
        start_date = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        start_date = f"{start_date}T00:00:00Z"

    print(f"[REQUEST] Frontend request received — num_candles={num_candles}, granularity={granularity}")

    GRANULARITY_MINUTES = {"M1": 1, "M5": 5, "M10": 10, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D": 1440}
    entry_mins = GRANULARITY_MINUTES.get(granularity, 5)
    trend_mins = GRANULARITY_MINUTES.get(GRANULARITY_TREND, 60)
    ratio = trend_mins // entry_mins
    num_candles_trend = max(200, num_candles // ratio) if ratio > 0 else 200

    dataManager = DataManager("GoldBotProfile")

    dataManager.add_instrument_dataframe(INSTRUMENT, start_date, num_candles, granularity, "XAUD_M5_ENTRY")
    dataManager.add_instrument_dataframe(INSTRUMENT, start_date, num_candles_trend, GRANULARITY_TREND, "XAUD_H1_TREND")
    # Load Data
    total_profit = 0.0
    dataManager["XAUD_M5_ENTRY"].add_indicators(rsi_period, bb_period, bb_std)
    df_trend = dataManager["XAUD_H1_TREND"].dataframe
    df_entry = dataManager["XAUD_M5_ENTRY"].dataframe
    df_trend["EMA200"] = df_trend["close"].ewm(span=200, adjust=False).mean()
    print(f"[PROCESSING] Data loaded — {len(df_entry)} entry candles, {len(df_trend)} trend candles. Starting backtest...")
    # df_entry["time_num"] = mdates.date2num(df_entry["time"])
    
    # Parse trading hours
    from datetime import time as dt_time
    sh, sm = map(int, trading_start_time.split(':'))
    eh, em = map(int, trading_end_time.split(':'))
    trade_start = dt_time(sh, sm)
    trade_end = dt_time(eh, em)

    # State Variables (Reset on every request)
    position = None
    entry_price = 0
    stop_loss = 0
    pending_setup = None
    SuccessfulLongs = 0
    SuccessfulShorts = 0
    LongsAttempted = 0
    ShortsAttempted = 0

    total_fees = 0.0
    total_profit = 0.0
    trade_units = 1.0
    trade_spread = 0.0

    trades = []
    chart_data = []
    entry_time = df_entry.iloc[0]["time"] # Initialize entry_time
    new_trailing_sl = 0
    trade_count = 0
    print(f"Printing output: ")

    for i in range(len(df_entry)):
        row = df_entry.iloc[i]


        if i == 0:
            continue
        atr = row["atr_SMA_14"]
        atr_sma = row["atr_SMA_80"]
        # today = dt_time(0, 0, 0)
        # candles_today = df_entry[df_entry["time"].dt.time >= today]
        # sr_window = min(len(candles_today), sr_window_bounds)

        df_window = df_entry.iloc[i - SR_WINDOW_BOUNDS:i].reset_index(drop=True)
        df_window = df_window.tail(SR_WINDOW_BOUNDS)

        prev_price = df_entry.iloc[i - 1]["close"]
        price = row["close"]
        
        
        # Skip warm-up
        # if i < BB_PERIOD:
        #     continue

        # Align trend EMA
        trend_price = df_trend.iloc[-1]["close"]
        trend_ema = df_trend.iloc[-1]["EMA200"]
        trend_direction = "long" if trend_price > trend_ema else "short"

        # ==============================
        # ENTRY LOGIC
        # ==============================
        prev_rsi = df_entry.iloc[i - 1]["RSI"]
        rsi = row["RSI"]
        rvol = row["rvol"]
        bb_upper = row["BB_UPPER"]
        bb_lower = row["BB_LOWER"]

        short_atrChopCheck = False
        long_atrChopCheck = False


        short_rsi_thershold = 73
        long_rsi_thershold = 40 #30
        
        avg_bb_width = row["AVG_100_BB_WIDTH_20"]
        if np.isnan(avg_bb_width):
            continue


        # ❌ avoid low volatility chop
        if atr_chop_enabled and atr < 0.8 * atr_sma:
            long_atrChopCheck = True

        # ❌ avoid low volatility chop
        if atr_chop_enabled and atr < 0.8 * atr_sma:
            short_atrChopCheck = True

        # Trading hours check
        candle_time = row['time'].time()
        in_trading_hours = trade_start <= candle_time < trade_end

        # Cancel pending setup outside trading hours
        if not in_trading_hours and pending_setup is not None:
            pending_setup = None

        # Force close position at end of trading day
        if position is not None and candle_time >= trade_end:
            if position == "long":
                pnl = (price - entry_price) * trade_units
                SuccessfulLongs += 1 if pnl > 0 else 0
                LongsAttempted += 1
            else:
                pnl = (entry_price - price) * trade_units
                SuccessfulShorts += 1 if pnl > 0 else 0
                ShortsAttempted += 1
            total_profit += pnl
            total_fees += trade_spread * trade_units
            trade_count += 1
            entry_price = stop_loss = 0
            position = None

        if position is None and pending_setup is None and in_trading_hours:
        # LONG SETUP (price stretched down)
            # for long conditions I swapped rvol >= thershold to rvol <= thershold (9/03/26). Profit boosted significantly for 2025 data.
            if longs_enabled and rsi < long_rsi_thershold and price <= (bb_lower * 1) and rvol <= rvol_threshold and long_atrChopCheck == False and (not trend_enabled or trend_direction == "long"):
                pending_setup = "long"

            # SHORT SETUP (price stretched up)
            elif shorts_enabled and rsi > short_rsi_thershold and price >= (bb_upper * 1) and rvol >= rvol_threshold and short_atrChopCheck == False and (not trend_enabled or trend_direction == "short"):
                pending_setup = "short"

        # REVERSAL CONFIRMATION
        if pending_setup == "long":
            # Reversal confirmation:
            # 1. RSI turns up
            # 2. Price closes back inside BB
            if rsi > long_rsi_thershold and price > bb_lower: #and price > prev_price:
                position = "long"
                entry_price = price
                stop_loss = entry_price - avg_bb_width * sl_multiplier
                capital = initial_capital + max(0, total_profit) if reinvest_enabled else initial_capital
                trade_units = (capital * leverage) / entry_price
                trade_spread = row['ask_close'] - row['bid_close']
                variable_interval = PAUSE_INTERVAL_HIST
                pending_setup = None

        elif pending_setup == "short":
            # Reversal confirmation:
            if  rsi < short_rsi_thershold and price < bb_upper: # and price < prev_price: # removed conditions:  rsi < prev_rsi
                position = "short"
                entry_price = price
                stop_loss = entry_price + avg_bb_width * sl_multiplier
                capital = initial_capital + max(0, total_profit) if reinvest_enabled else initial_capital
                trade_units = (capital * leverage) / entry_price
                trade_spread = row['ask_close'] - row['bid_close']
                variable_interval = PAUSE_INTERVAL_HIST
                pending_setup = None

        # EXIT LOGIC
        bb_range = bb_upper - bb_lower

        if bb_range > 0:
            # 0 = lower band, 1 = upper band
            bb_pos = np.clip((price - bb_lower) / bb_range, 0, 1)

        if position is not None:

            # =========================
            # LONG POSITION
            # =========================
            if position == "long" and bb_range > 0:

                # Exponential tightening toward upper band
                EXP_POWER = 2.5
                MIN_TRAIL = 0.05    # tight near upper band (5% of BB width)
                MAX_TRAIL = 0.35    # loose near lower band (35% of BB width)

                exp_factor = bb_pos ** EXP_POWER

                trail_dist = (
                    MAX_TRAIL * bb_range
                    - exp_factor * (MAX_TRAIL - MIN_TRAIL) * bb_range
                )

                new_trailing_sl = price - trail_dist

                # Never loosen stop
                stop_loss = max(stop_loss, new_trailing_sl)

                # -------- EXIT --------
                if price <= stop_loss:
                    pnl = (price - entry_price) * trade_units
                    SuccessfulLongs += 1 if pnl > 0 else 0
                    LongsAttempted += 1
                    total_profit += pnl
                    total_fees += trade_spread * trade_units
                    trade_count += 1
                    entry_price = stop_loss = 0
                    position = None
                    variable_interval = CHECK_INTERVAL_HIST


            # =========================
            # SHORT POSITION
            # =========================
            elif position == "short" and bb_range > 0:

                # Invert BB position for shorts
                bb_pos_short = 1 - bb_pos

                EXP_POWER = 2.5
                MIN_TRAIL = 0.05
                MAX_TRAIL = 0.35

                exp_factor = bb_pos_short ** EXP_POWER

                trail_dist = (
                    MAX_TRAIL * bb_range
                    - exp_factor * (MAX_TRAIL - MIN_TRAIL) * bb_range
                )

                new_trailing_sl = price + trail_dist

                # Never loosen stop
                stop_loss = min(stop_loss, new_trailing_sl)

                # -------- EXIT --------
                if price >= stop_loss:
                    pnl = (entry_price - price) * trade_units
                    SuccessfulShorts += 1 if pnl > 0 else 0
                    ShortsAttempted += 1
                    total_profit += pnl
                    total_fees += trade_spread * trade_units
                    trade_count += 1
                    entry_price = stop_loss = 0
                    position = None
                    variable_interval = CHECK_INTERVAL_HIST

        # Format for Frontend
        
        chart_data.append({
            "time": int(row['time'].timestamp()),
            "open": row['open'], "high": row['high'], "low": row['low'], "close": row['close'],
            "bb_upper": row['BB_UPPER'], "bb_lower": row['BB_LOWER'], "trailing_sl": stop_loss,
            "entry_price": entry_price, "total_profit": round(total_profit, 2),
            "total_fees": round(total_fees, 2), "trade_count": trade_count})
        #print("\r", end="")
        
        
        print(f"total_profit: {round(total_profit, 2)}")
        #print(f"Candle {i}")

    add_entry(
        params={
            "granularity": granularity, "bb_period": bb_period, "bb_std": bb_std,
            "rsi_period": rsi_period, "rvol_threshold": rvol_threshold,
            "longs_enabled": longs_enabled, "shorts_enabled": shorts_enabled,
            "trend_enabled": trend_enabled, "atr_chop_enabled": atr_chop_enabled,
            "reinvest_enabled": reinvest_enabled, "initial_capital": initial_capital,
            "leverage": leverage, "trading_start_time": trading_start_time,
            "trading_end_time": trading_end_time, "sl_multiplier": sl_multiplier,
            "start_date": start_date, "num_candles": num_candles,
        },
        result={
            "actual_candles": len(df_entry),
            "total_profit": round(total_profit, 2),
            "total_fees": round(total_fees, 2),
            "trade_count": trade_count,
        }
    )

    return {
        "chartData": chart_data,
        "trades": trades,
        "actualCandles": len(df_entry)
    }


@app.get("/leaderboard")
def get_leaderboard():
    return get_entries()


@app.delete("/leaderboard")
def clear_leaderboard():
    delete_all()
    return {"status": "cleared"}


@app.delete("/leaderboard/{entry_id}")
def delete_leaderboard_entry(entry_id: str):
    found = delete_one(entry_id)
    if not found:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"status": "deleted"}


# @app.get("/backtest")
# def run_backtest(
#     num_candles: int = Query(2000),
#     bb_period: int = Query(20),
#     longs_enabled: bool = Query(True),
#     shorts_enabled: bool = Query(True),
#     trend_enabled: bool = Query(True)
# ):
#     chart_data = []
#     start_time = 1736985600

#     for i in range(50):
#         chart_data.append({
#             "time": start_time + (i * 300),
#             "close": 2005.0 + (i * 300),
#         })

#     return {"chartData": chart_data}


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)