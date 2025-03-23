# pairs_trading_bot.py

import time
import logging
from ib_insync import IB
from config import CONFIG
from data_manager import DataManager
from order_manager import OrderManager
from trade_logger import TradeLogger

# Import the new parallel processing function
from parallel_pairs import process_all_pairs_in_parallel

failed_pairs = {}  # Global dictionary for tracking pairs on cooldown

class PairsTradingBot:
    def __init__(self, config):
        self.config = config
        self.ib = IB()
        logging.info("Connecting to IB...")
        self.ib.connect('127.0.0.1', 7497, clientId=2)
        logging.info("Connected to IB.")
        self.data_manager = DataManager(config["API_KEY"], config["DATA_LOOKBACK_DAYS"], config["DATA_INTERVAL_MIN"])
        self.data_manager.load_pairs(config["PAIR_FILE"])
        self.order_manager = OrderManager(self.ib)
        self.trade_logger = TradeLogger(config["TRADES_FILE"])

    def check_for_entry_parallel(self):
        pairs_to_process = []
        now = time.time()
        for t1, t2 in self.data_manager.pairs:
            pair_key = "_".join(sorted([t1, t2]))
            if pair_key in failed_pairs and now < failed_pairs[pair_key]:
                print(f"Pair {pair_key} is on cooldown until {time.ctime(failed_pairs[pair_key])}. Skipping.")
                continue
            pairs_to_process.append((t1, t2))

        results = process_all_pairs_in_parallel(self.config, pairs_to_process)
        for trade in results:
            if trade:
                self.trade_logger.add_new_trade(trade["trade1"], trade["trade2"], trade["pair_key"])
                print(f"Entered trade for pair {trade['pair_key']} with z-score {trade['z_score']}")

    def monitor_and_exit_trades(self):
        trades = self.trade_logger.load_trades()
        if len(trades) < 2:
            return

        pair_indices = []
        for i in range(0, len(trades), 2):
            if i + 1 < len(trades):
                pair_indices.append((i, i + 1))

        data_df = self.data_manager.fetch_market_data()
        if data_df is None:
            print("No market data available (exit check).")
            return

        indices_to_remove = []
        for idx1, idx2 in pair_indices:
            trade1 = trades[idx1]
            trade2 = trades[idx2]
            sym1 = trade1["stock_symbol"]
            sym2 = trade2["stock_symbol"]
            z = self.data_manager.compute_z_score(data_df, sym1, sym2)
            if z is None:
                print(f"Could not compute z-score for pair ({sym1}, {sym2}).")
                continue

            logging.info(f"Monitoring pair ({sym1}, {sym2}): z-score = {z:.3f}")
            if self.config["Z_SCORE_EXIT_LOW"] <= z <= self.config["Z_SCORE_EXIT_HIGH"]:
                exit_trade1 = self.order_manager.exit_order_with_escalation(
                    sym1, trade1["action"], trade1["quantity"],
                    initial_timeout=5, escalation_timeout=3, max_escalations=2
                )
                exit_trade2 = self.order_manager.exit_order_with_escalation(
                    sym2, trade2["action"], trade2["quantity"],
                    initial_timeout=5, escalation_timeout=3, max_escalations=2
                )
                profit1 = self.compute_profit(trade1, exit_trade1)
                profit2 = self.compute_profit(trade2, exit_trade2)
                net_profit = profit1 + profit2
                profit_record = {
                    "pair_key": trade1["pair_key"],
                    "entry_time": trade1.get("entry_time"),
                    "exit_time": time.time(),
                    "leg1": {
                        "stock_symbol": sym1,
                        "action": trade1["action"],
                        "quantity": trade1["quantity"],
                        "entry_price": trade1.get("entry_price"),
                        "exit_price": exit_trade1.get("limit_price") if exit_trade1 and "limit_price" in exit_trade1 else None,
                        "profit": profit1
                    },
                    "leg2": {
                        "stock_symbol": sym2,
                        "action": trade2["action"],
                        "quantity": trade2["quantity"],
                        "entry_price": trade2.get("entry_price"),
                        "exit_price": exit_trade2.get("limit_price") if exit_trade2 and "limit_price" in exit_trade2 else None,
                        "profit": profit2
                    },
                    "net_profit": net_profit
                }
                print(f"Exited trade for pair ({sym1}, {sym2}) with net profit: {net_profit:.2f}")
                self.trade_logger.log_profit(profit_record)
                indices_to_remove.extend([idx1, idx2])

        if indices_to_remove:
            self.trade_logger.remove_trades_by_indices(indices_to_remove)

    def compute_profit(self, entry_trade, exit_trade):
        if exit_trade is None:
            return 0
        entry_price = entry_trade.get("entry_price")
        # Here we assume exit orders are limit orders with key 'limit_price'
        exit_price = exit_trade.get("limit_price")
        quantity = entry_trade.get("quantity", 0)
        if entry_price is None or exit_price is None:
            return 0
        if entry_trade["action"] == "BUY":
            return (exit_price - entry_price) * quantity
        else:
            return (entry_price - exit_price) * quantity

    def run(self):
        try:
            while True:
                print("=== Checking for new trade entries ===")
                self.check_for_entry_parallel()
                print("=== Monitoring open trades for exit conditions ===")
                self.monitor_and_exit_trades()
                print(f"Sleeping {self.config['FETCH_SLEEP_INTERVAL']} seconds before next scan...")
                time.sleep(self.config["FETCH_SLEEP_INTERVAL"])
        except KeyboardInterrupt:
            print("Interrupted by user. Disconnecting from IB and exiting.")
            self.ib.disconnect()

if __name__ == "__main__":
    bot = PairsTradingBot(CONFIG)
    bot.run()
