# trade_logger.py

import json
import os
import time

class TradeLogger:
    def __init__(self, trades_file, profit_file="profits.json"):
        self.trades_file = trades_file
        self.profit_file = profit_file

    def load_trades(self):
        try:
            with open(self.trades_file, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def save_trades(self, trades):
        with open(self.trades_file, 'w') as f:
            json.dump(trades, f, indent=4)

    def add_new_trade(self, trade1, trade2, pair_key):
        # Record entry details with a timestamp and the entry price (limit_price)
        trades = self.load_trades()
        trade1["pair_key"] = pair_key
        trade2["pair_key"] = pair_key
        trade1["entry_time"] = time.time()
        trade2["entry_time"] = time.time()
        # Ensure the entry price is recorded if not already
        if "limit_price" in trade1:
            trade1["entry_price"] = trade1["limit_price"]
        if "limit_price" in trade2:
            trade2["entry_price"] = trade2["limit_price"]
        trades.append(trade1)
        trades.append(trade2)
        self.save_trades(trades)

    def log_profit(self, profit_record):
        """
        Append a profit record for a completed pair trade.
        profit_record is a dictionary that contains:
          - pair_key
          - leg1: { stock_symbol, action, quantity, entry_price, exit_price, profit }
          - leg2: { stock_symbol, action, quantity, entry_price, exit_price, profit }
          - net_profit
          - entry_time and exit_time
        """
        try:
            if os.path.exists(self.profit_file):
                with open(self.profit_file, "r") as f:
                    profits = json.load(f)
            else:
                profits = []
        except Exception:
            profits = []

        profits.append(profit_record)

        with open(self.profit_file, "w") as f:
            json.dump(profits, f, indent=4)


    def remove_trades_by_indices(self, indices):
        trades = self.load_trades()
        for i in sorted(indices, reverse=True):
            if 0 <= i < len(trades):
                trades.pop(i)
        self.save_trades(trades)
