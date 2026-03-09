import pandas as pd
import numpy as np
import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import config

client = oandapyV20.API(access_token=config.OANDA_API_KEY, environment="practice")


class DataManager:
    def __init__(self, profile_name):

        self.dataFrames = {}
        self.profile_name = profile_name

    def __getitem__(self, key: str) -> "InstrumentDataFrame":
        """
        Allows dictionary-style access to the managed DataFrames.
        """
        if key in self.dataFrames:
            return self.dataFrames[key]
        raise KeyError(f"No DataFrame found with the name '{key}'")

    def add_instrument_dataframe(self, instrument, start_date, candles, granularity, name=None) -> pd.DataFrame:
        key = f"{instrument}_{start_date}_{candles}_{granularity}"
        if name:
            key = name
        self.dataFrames[key] = InstrumentDataFrame(instrument, start_date, candles, granularity)
        return self.dataFrames[key].dataframe


class InstrumentDataFrame:
    def __init__(self, instrument, start_date, candles, granularity, name=None):
        self.instrument = instrument
        self.start_date = start_date
        self.candles_to_load = candles
        self.granularity = granularity
        
        # Auto-generate name if none provided
        if name is None:
            self.name = f"{instrument}_{granularity}_{start_date}"
        else:
            self.name = name
        
        self.dataframe = None
        self.built_df = False
        self.build_dataframe()
    
    def build_dataframe(self):
        MAX_COUNT = 4000
        num_candles=self.candles_to_load
        candles_remaining = num_candles
        granularity = self.granularity
        to_time = pd.to_datetime(self.start_date)

        all_records = []

        while candles_remaining > 0:
            batch_size = min(MAX_COUNT, candles_remaining)
            params = {"granularity": granularity, "price": "M", "count": batch_size, "from": to_time.strftime("%Y-%m-%dT%H:%M:%SZ")}
            r = instruments.InstrumentsCandles(instrument=self.instrument, params=params)
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
        self.dataframe = df
        self.built_df = 1
    
    def add_rsi(self, rsi_period: int) -> pd.DataFrame:
        df = self.dataframe
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(rsi_period).mean()
        avg_loss = loss.rolling(rsi_period).mean()

        rs = avg_gain / avg_loss
        df["RSI"] = 100 - (100 / (1 + rs))
        return df


    def add_bollinger_bands(self,
        bb_period: int,
        bb_std_mult: float,
        bb_width_avg_period: int = 100
    ) -> pd.DataFrame:
        df = self.dataframe
        df["BB_MID"] = df["close"].rolling(bb_period).mean()
        df["BB_STD"] = df["close"].rolling(bb_period).std()

        df["BB_UPPER"] = df["BB_MID"] + bb_std_mult * df["BB_STD"]
        df["BB_LOWER"] = df["BB_MID"] - bb_std_mult * df["BB_STD"]

        df["BB_WIDTH"] = df["BB_UPPER"] - df["BB_LOWER"]
        df["AVG_100_BB_WIDTH_20"] = df["BB_WIDTH"].rolling(bb_width_avg_period).mean()
        return df


    def add_true_range(self) -> pd.DataFrame:
        df = self.dataframe
        df["hl"] = df["high"] - df["low"]
        df["hc"] = (df["high"] - df["close"].shift()).abs()
        df["lc"] = (df["low"] - df["close"].shift()).abs()
        df["tr"] = df[["hl", "hc", "lc"]].max(axis=1)
        return df


    def add_atr_sma(self, periods: tuple[int, ...] = (14, 80)) -> pd.DataFrame:
        df = self.dataframe
        if "tr" not in df.columns:
            self.add_true_range()

        for period in periods:
            df[f"atr_SMA_{period}"] = df["tr"].rolling(period).mean()

        return df


    def add_relative_volume(self, vol_period: int = 50) -> pd.DataFrame:
        df = self.dataframe
        df["avg_vol"] = df["volume"].rolling(vol_period).mean()
        df["rvol"] = df["volume"] / df["avg_vol"]
        df["rvol"] = df["rvol"].replace([np.inf, -np.inf], 0).fillna(0)
        return df


    def add_indicators(self, rsi_period: int, bb_period: int, bb_std_mult: float) -> pd.DataFrame:
        self.add_rsi(rsi_period)
        self.add_bollinger_bands(bb_period, bb_std_mult, bb_width_avg_period=100)
        self.add_atr_sma(periods=(14, 80))
        self.add_relative_volume(vol_period=50)
        return self.dataframe