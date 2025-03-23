import time
import logging
from ib_insync import IB
from data_manager import DataManager
from order_manager import OrderManager
import requests
from trade_logger import TradeLogger
from config import CONFIG
def process_pairs_chunk(pairs_chunk, config, client_id):
    from data_manager import DataManager
    import time
    from order_manager import round_to_tick
    """
    Process a chunk (list) of pairs using a single IB connection.
    Returns a list of successful trade details.
    """
    results = []
    ib = IB()
    try:
        ib.connect('127.0.0.1', config["IB_PORT"], clientId=client_id)
    except Exception as e:
        print(f"IB connection failed for chunk with clientId {client_id}: {e}")
        return results

    order_manager = OrderManager(ib)
    data_manager = DataManager(config["API_KEY"], config["DATA_LOOKBACK_DAYS"], config["DATA_INTERVAL_MIN"])

    # Ensure that tickers are loaded.
    data_manager.tickers = {ticker for pair in pairs_chunk for ticker in pair}
    
    data_df = data_manager.fetch_market_data()
    if data_df is None:
        print(f"No valid market data downloaded for clientId {client_id}. Skipping chunk.")
        ib.disconnect()
        return results

    # Process each pair in the chunk using the same market data
    for t1, t2 in pairs_chunk:
        pair_key = "_".join(sorted([t1, t2]))
        print(f"Processing pair {pair_key} in chunk (clientId {client_id})")
        z = data_manager.compute_z_score(data_df, t1, t2)
        if z is None:
            logging.warning(f"Could not compute z-score for pair {pair_key}")
            continue

        trade1 = None
        trade2 = None
        if z > config["ENTER_THRESHOLD_SHORT"] and z > 0:
            print(f"Entry signal for pair {pair_key}: SELL {t1} / BUY {t2}")
            trade1 = order_manager.place_order_with_escalation(t1, "SELL", config["CAPITAL_PER_TRADE"])
            if trade1 is None:
                logging.warning(f"First leg (SELL {t1}) did not fill for pair {pair_key}.")
                continue  # Skip to next pair
            trade2 = order_manager.place_order_with_escalation(t2, "BUY", config["CAPITAL_PER_TRADE"])
            if trade2 is None:
                print(f"Second leg (BUY {t2}) did not fill after first leg for pair {pair_key}. Exiting leg {t1}.")
                order_manager.exit_order_with_escalation(
                    t1, trade1["action"], trade1["quantity"],
                    initial_timeout=5, escalation_timeout=3, max_escalations=2
                )
                continue
        elif z < config["ENTER_THRESHOLD_LONG"] and z < 0:
            logging.info(f"Entry signal for pair {pair_key}: BUY {t1} / SELL {t2}")
            trade1 = order_manager.place_order_with_escalation(t1, "BUY", config["CAPITAL_PER_TRADE"])
            if trade1 is None:
                print(f"First leg (BUY {t1}) did not fill for pair {pair_key}.")
                continue
            trade2 = order_manager.place_order_with_escalation(t2, "SELL", config["CAPITAL_PER_TRADE"])
            if trade2 is None:
                print(f"Second leg (SELL {t2}) did not fill after first leg for pair {pair_key}. Exiting leg {t1}.")
                order_manager.exit_order_with_escalation(
                    t1, trade1["action"], trade1["quantity"],
                    initial_timeout=5, escalation_timeout=3, max_escalations=2
                )
                continue
        else:
            print(f"No entry conditions met for pair {pair_key} (z-score: {z})")
            continue

        results.append({"pair_key": pair_key, "trade1": trade1, "trade2": trade2, "z_score": z})
    ib.disconnect()
    return results
def round_to_tick(price, tick_size=0.01):
        """Rounds the given price to the nearest valid tick."""
        return round(price / tick_size) * tick_size
def chunk_pairs(pairs, chunk_size):
    """Yield successive chunks (sublists) of size chunk_size from pairs."""
    for i in range(0, len(pairs), chunk_size):
        yield pairs[i:i + chunk_size]

def process_all_pairs_in_parallel(config, pairs):
    """
    Divides the list of pairs into chunks and processes each chunk in its own process.
    Each process gets a unique client id based on a base value plus its chunk index.
    Uses max_workers=4 and adds a 2-second delay between process launches.
    """
    results = []
    chunk_size = config.get("CHUNK_SIZE", 400)
    chunks = list(chunk_pairs(pairs, chunk_size))
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import time

    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = []
        for idx, chunk in enumerate(chunks):
            future = executor.submit(process_pairs_chunk, chunk, config, config["PROCESS_CLIENT_ID_BASE"] + idx)
            futures.append(future)
            time.sleep(1)  # 2-second delay between process launches
        for future in as_completed(futures):
            try:
                chunk_results = future.result()
                if chunk_results:
                    results.extend(chunk_results)
            except Exception as e:
                print(f"Error processing a chunk: {e}")
    return results
