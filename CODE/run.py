# run.py

from pairs_trading_bot import PairsTradingBot
from config import CONFIG

if __name__ == "__main__":
    bot = PairsTradingBot(CONFIG)
    bot.run()
