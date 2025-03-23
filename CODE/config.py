import os

CONFIG = {
    "API_KEY": os.getenv("POLYGON_API_KEY", "wUnDzCqDRV3C_0aPhhfJfzgARepZ3rsx"),
    "PAIR_FILE": "profit_milker.txt",       # File listing your pairs
    "TRADES_FILE": "trades3.json",            # File for logging trades
    "CAPITAL_PER_TRADE": 500,
    "ENTER_THRESHOLD_SHORT": 1.8,
    "ENTER_THRESHOLD_LONG": -1.8,
    "Z_SCORE_EXIT_LOW": -0.35,
    "Z_SCORE_EXIT_HIGH": 0.35,
    "DATA_LOOKBACK_DAYS": 5,
    "DATA_INTERVAL_MIN": 5,     # 5-minute bars
    "FETCH_SLEEP_INTERVAL": 100,
    "COOLDOWN_PERIOD": 1000,    # Cooldown seconds for failed pairs
    "IB_PORT": 7497,            # IB connection port
    "PROCESS_CLIENT_ID_BASE": 3,  # Base client ID for parallel processes.
    "CHUNK_SIZE": 100           # Number of pairs per process (adjust as needed)
}
