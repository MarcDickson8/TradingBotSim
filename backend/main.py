import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import config
import uvicorn

app = FastAPI()


CHECK_INTERVAL_HIST = 0 #0.005
PAUSE_INTERVAL_HIST = 0 #0.03
INSTRUMENT = "XAU_AUD"
GRANULARITY_ENTRY = "M5"
GRANULARITY_TREND = "H1" #"H1" uses this one timeframe for general trend direction
CANDLES_TO_LOAD_HIST = 5000  # reduced for testing
SR_WINDOW_BOUNDS = 500
PLOT_ENABLED = False
TREND_DIRECTION_ENABLED = False
SHORT_ENABLED = False
LONG_ENABLED = True

END_DATE = "2026-02-06T23:59:59Z"

RSI_PERIOD = 14
BB_PERIOD = 20 #20
BB_STD = 2
RVOL_THRESHOLD = 1.5
SLTP_RATIO = 3

position = None
entry_price = 0
stop_loss = 0
take_profit = 0
total_profit = 0.0
trade_count = 0

# Stats
rsi_inbound_count = 0
BB_inbound_count = 0
RVOL_inbound_count = 0
SuccessfulShorts = 0
SuccessfulLongs = 0
ShortsAttempted = 0
LongsAttempted = 0
pending_setup = None
lossOne, lossTwo = False, False


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# OANDA CLIENT
# ==============================
client = oandapyV20.API(access_token=config.OANDA_API_KEY, environment="practice")

# ==============================
# CORE FUNCTIONS
# ==============================
def load_candles(granularity, end=END_DATE, num_candles=CANDLES_TO_LOAD_HIST):
    MAX_COUNT = 4000
    candles_remaining = num_candles
    to_time = pd.to_datetime(end)

    all_records = []

    while candles_remaining > 0:
        batch_size = min(MAX_COUNT, candles_remaining)
        params = {"granularity": granularity, "price": "M", "count": batch_size, "to": to_time.strftime("%Y-%m-%dT%H:%M:%SZ")}
        r = instruments.InstrumentsCandles(instrument=INSTRUMENT, params=params)
        client.request(r)
        candles = r.response.get("candles", [])
        if not candles:
            break
        records = []
        for candle in candles:
            if not candle["complete"]:
                continue
            records.append({
                "time": candle["time"],
                "open": float(candle["mid"]["o"]),
                "high": float(candle["mid"]["h"]),
                "low": float(candle["mid"]["l"]),
                "close": float(candle["mid"]["c"]),
                "volume": float(candle["volume"])
            })
        if not records:
            break
        df_chunk = pd.DataFrame(records)
        df_chunk["time"] = pd.to_datetime(df_chunk["time"])
        all_records.append(df_chunk)
        to_time = df_chunk["time"].min() - pd.Timedelta(seconds=1)
        candles_remaining -= len(df_chunk)

    if not all_records:
        return pd.DataFrame()
    df = pd.concat(all_records).drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
    if len(df) > num_candles:
        df = df.iloc[-num_candles:].reset_index(drop=True)
    return df

def add_indicators(df):
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(RSI_PERIOD).mean()
    avg_loss = loss.rolling(RSI_PERIOD).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["BB_MID"] = df["close"].rolling(BB_PERIOD).mean()
    df["BB_STD"] = df["close"].rolling(BB_PERIOD).std()
    df["BB_UPPER"] = df["BB_MID"] + BB_STD * df["BB_STD"]
    df["BB_LOWER"] = df["BB_MID"] - BB_STD * df["BB_STD"]
    df["BB_WIDTH"] = df["BB_UPPER"] - df["BB_LOWER"]
    df["AVG_100_BB_WIDTH_20"] = df["BB_WIDTH"].rolling(100).mean()

    df["hl"] = df["high"] - df["low"]
    df["hc"] = (df["high"] - df["close"].shift()).abs()
    df["lc"] = (df["low"] - df["close"].shift()).abs()
    df["tr"] = df[["hl", "hc", "lc"]].max(axis=1)
    df["atr_SMA_14"] = df["tr"].rolling(14).mean()
    df["atr_SMA_80"] = df["tr"].rolling(80).mean()

    df["avg_vol"] = df["volume"].rolling(50).mean()
    df["rvol"] = df["volume"] / df["avg_vol"]
    df["rvol"] = df["rvol"].replace([np.inf, -np.inf], 0).fillna(0)
    return df

# ==============================
# API ENDPOINT
# ==============================
@app.get("/backtest")
def run_backtest(
    num_candles: int = Query(2000)
):
    # Load Data
    global total_profit
    total_profit = 0.0
    df_trend = add_indicators(load_candles(GRANULARITY_TREND))
    df_entry = add_indicators(load_candles(GRANULARITY_ENTRY))
    df_trend["EMA200"] = df_trend["close"].ewm(span=200, adjust=False).mean()
    # df_entry["time_num"] = mdates.date2num(df_entry["time"])
    
    # State Variables (Reset on every request)

    trades = []
    chart_data = []
    entry_time = df_entry.iloc[0]["time"] # Initialize entry_time
    new_trailing_sl = 0
    print(f"Printing output: ")

    for i in range(len(df_entry)):
        global position, entry_price, stop_loss, take_profit, pending_setup
        global trade_count, SuccessfulLongs, SuccessfulShorts
        global LongsAttempted, ShortsAttempted, lossOne, lossTwo
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
        if atr < 0.8 * atr_sma:
            #print(f"LOW VOLATILITY")
            long_atrChopCheck = True

        # ❌ avoid low volatility chop
        if atr < 0.8 * atr_sma:
            #print(f"LOW VOLATILITY")
            short_atrChopCheck = True

        if position is None and pending_setup is None:
        # LONG SETUP (price stretched down)
            if LONG_ENABLED and rsi < long_rsi_thershold and price <= (bb_lower * 1) and rvol >= RVOL_THRESHOLD and long_atrChopCheck == False: # Removed Conditions:trend_direction == "long" and 
                pending_setup = "long"

            # SHORT SETUP (price stretched up)
            elif SHORT_ENABLED and rsi > short_rsi_thershold and price >= (bb_upper * 1) and short_atrChopCheck == False and trend_direction == "short": # Removed Conditions:  || and rvol >= RVOL_THRESHOLD  
                pending_setup = "short"

        # REVERSAL CONFIRMATION
        if pending_setup == "long":
            # Reversal confirmation:
            # 1. RSI turns up
            # 2. Price closes back inside BB
            if rsi > long_rsi_thershold and price > bb_lower: #and price > prev_price:
                position = "long"
                entry_price = price
                stop_loss = entry_price - avg_bb_width
                take_profit = entry_price + (entry_price - stop_loss) * SLTP_RATIO
                variable_interval = PAUSE_INTERVAL_HIST
                pending_setup = None

        elif pending_setup == "short":
            # Reversal confirmation:
            if  rsi < short_rsi_thershold and price < bb_upper: # and price < prev_price: # removed conditions:  rsi < prev_rsi 
                position = "short"
                entry_price = price
                stop_loss = entry_price + avg_bb_width
                take_profit = entry_price - (stop_loss - entry_price) * SLTP_RATIO
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
                if price <= stop_loss or price >= take_profit:
                    pnl = price - entry_price
                    SuccessfulLongs += 1 if pnl > 0 else 0
                    LongsAttempted += 1
                    total_profit += pnl
                    trade_count += 1
                    entry_price = stop_loss = take_profit = 0
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
                if price >= stop_loss or price <= take_profit:
                    pnl = entry_price - price
                    SuccessfulShorts += 1 if pnl > 0 else 0
                    ShortsAttempted += 1
                    total_profit += pnl
                    trade_count += 1
                    entry_price = stop_loss = take_profit = 0
                    position = None
                    variable_interval = CHECK_INTERVAL_HIST

        # Format for Frontend
        
        chart_data.append({
            "time": int(row['time'].timestamp()),
            "open": row['open'], "high": row['high'], "low": row['low'], "close": row['close'],
            "bb_upper": row['BB_UPPER'], "bb_lower": row['BB_LOWER'], "trailing_sl": stop_loss, 
            "entry_price": entry_price, "total_profit": round(total_profit, 2), "trade_count": len(trades)//2})
        #print("\r", end="")
        
        
        print(f"total_profit: {round(total_profit, 2)}")
        #print(f"Candle {i}")

    return {
        "chartData": chart_data,
        "trades": trades
    }


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