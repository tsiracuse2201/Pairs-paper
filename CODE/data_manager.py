# data_manager.py

import os
import time
import datetime
import requests
import pandas as pd
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

class DataManager:
    def __init__(self, api_key, lookback_days, interval_min):
        self.api_key = api_key
        self.lookback_days = lookback_days
        self.interval_min = interval_min
        self.tickers = set()
        self.pairs = []

    def load_pairs(self, pair_file):
        if not os.path.exists(pair_file):
            logging.error(f"Pair file {pair_file} not found.")
            return
        with open(pair_file, 'r') as f:
            for line in f:
                parts = line.strip().split(', Profit: ')
                stocks = parts[0].replace('Pair: ', '').split(' and ')
                if len(stocks) == 2:
                    self.tickers.update(stocks)
                    self.pairs.append((stocks[0], stocks[1]))
                else:
                    logging.warning(f"Unrecognized line format: {line}")
        logging.info(f"Loaded pairs: {self.pairs}")
        logging.info(f"Unique tickers: {self.tickers}")

    @staticmethod
    def dt_to_ms(dt: datetime.datetime) -> int:
        return int(dt.timestamp() * 1000)

    def download_polygon_data(self, ticker, start_ms, end_ms):
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{self.interval_min}/minute/{start_ms}/{end_ms}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": 70000,
            "apiKey": self.api_key
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            logging.error(f"Failed to fetch data for {ticker}: HTTP {response.status_code}")
            return None
        data = response.json()
        if data.get("status") != "OK" or "results" not in data:
            logging.error(f"Invalid data for {ticker}")
            return None
        results = data["results"]
        df = pd.DataFrame(results)
        df["date"] = pd.to_datetime(df["t"], unit="ms")
        df.set_index("date", inplace=True)
        df = df[["c"]].rename(columns={"c": "Close"})
        return df

    def fetch_market_data(self):
        end_dt = datetime.datetime.utcnow()
        start_dt = end_dt - datetime.timedelta(days=self.lookback_days)
        end_ms = self.dt_to_ms(end_dt)
        start_ms = self.dt_to_ms(start_dt)
    
        downloaded_data = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futs = {executor.submit(self.download_polygon_data, ticker, start_ms, end_ms): ticker
                    for ticker in self.tickers}
            for fut in as_completed(futs):
                ticker = futs[fut]
                df = fut.result()
                downloaded_data[ticker] = df

        frames = []
        for ticker, df in downloaded_data.items():
            if df is not None and not df.empty:
                frames.append(df.rename(columns={"Close": ticker}))
        if not frames:
            logging.error("No valid market data downloaded.")
            return None
        combined = pd.concat(frames, axis=1)
        valid_mask = combined.count() >= 150  # Require at least 100 data points
        combined = combined.loc[:, valid_mask]
        if combined.empty:
            logging.error("Not enough data points for any ticker.")
            return None
        combined.ffill(inplace=True)
        return combined

    def get_current_price(self, ticker, data_df):
        if ticker in data_df.columns:
            return data_df[ticker].iloc[-1]
        return None

    def compute_z_score(self, df, t1, t2, window=40):
        if t1 not in df.columns or t2 not in df.columns:
            return None
        spread = df[t1] - df[t2]
        mean_spread = spread.rolling(window=window).mean()
        std_spread  = spread.rolling(window=window).std()
        z_series = (spread - mean_spread) / std_spread
        if z_series.empty or z_series.isna().all():
            return None
        return z_series.iloc[-1]
