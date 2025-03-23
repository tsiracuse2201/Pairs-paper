# order_manager.py
import os
import math
import logging
from ib_insync import IB, Stock, Order
import requests
import datetime
import time
def round_to_tick(price, tick_size=0.01):
        """Rounds the given price to the nearest valid tick."""
        return round(price / tick_size) * tick_size
class OrderManager:
    def __init__(self, ib):
        self.ib = ib
        self.api_key = os.getenv("POLYGON_API_KEY", "wUnDzCqDRV3C_0aPhhfJfzgARepZ3rsx")
        self.default_tick_size = 0.01
    def get_contract(self, stock_symbol):
        logging.debug(f"Creating contract for {stock_symbol}")
        return Stock(stock_symbol, "SMART", "USD")
    def round_to_tick(price, tick_size=0.01):
        """Rounds the given price to the nearest valid tick."""
        return round(price / tick_size) * tick_size

    def get_mid_price(self, stock_symbol):
        # Construct the Polygon URL for NBBO quotes:
        url = f"https://api.polygon.io/v3/quotes/{stock_symbol}"
        # Use today’s date (YYYY-MM-DD) as the timestamp to get the most recent quotes.
        today = datetime.date.today().isoformat()
        params = {
            "timestamp": today,
            "limit": 1,              # Only need the most recent quote
            "sort": "timestamp",     # Sort by timestamp...
            "order": "desc",         # ...in descending order so the first is the latest
            "apiKey": self.api_key
        }
        try:
            response = requests.get(url, params=params)
        except Exception as e:
            logging.error(f"Error fetching NBBO data for {stock_symbol}: {e}")
            return None

        if response.status_code != 200:
            logging.error(f"Failed to fetch NBBO data for {stock_symbol}: HTTP {response.status_code}")
            return None

        data = response.json()
        if data.get("status") != "OK" or "results" not in data or not data["results"]:
            logging.error(f"Invalid NBBO data received for {stock_symbol}: {data}")
            return None

        # Use the first (most recent) result
        quote = data["results"][0]
        bid = quote.get("bid_price")
        ask = quote.get("ask_price")
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            logging.warning(f"Invalid NBBO prices for {stock_symbol}: bid={bid}, ask={ask}")
            return None

        mid = (bid + ask) / 2
        # Use a fixed tick size of 0.01 as requested.
        mid = round_to_tick(mid, 0.01)
        print(f"Computed NBBO mid price for {stock_symbol} is {mid}")
        return mid

    def get_quantity(self, stock_symbol, amount_usd, price):
        if price is None or price <= 0:
            logging.error(f"Invalid price for {stock_symbol}: {price}")
            return 0
        quantity = math.ceil(amount_usd / price)
        logging.debug(f"Computed quantity for {stock_symbol} with ${amount_usd} at price {price} is {quantity}")
        return quantity

    def create_limit_order(self, action, quantity, limit_price):
        order = Order()
        order.action = action  # "BUY" or "SELL"
        order.orderType = "LMT"
        order.totalQuantity = quantity
        order.lmtPrice = limit_price
        logging.debug(f"Created limit order: {action} {quantity} @ {limit_price}")
        return order

    def create_market_order(self, action, quantity):
        order = Order()
        order.action = action
        order.orderType = "MKT"
        order.totalQuantity = quantity
        logging.debug(f"Created market order: {action} {quantity}")
        return order

    def wait_for_fill(self, trade, timeout=10):
        """Wait for an order to fill or timeout.
        Returns True if filled, False if not."""
        start_time = time.time()
        order_id = trade.orderStatus.orderId
        logging.debug(f"Waiting for order {order_id} to fill...")
        while True:
            self.ib.sleep(1)
            status = trade.orderStatus.status
            elapsed = time.time() - start_time
            logging.debug(f"Order {order_id} status after {elapsed:.1f} sec: {status}")
            if status in ["Filled", "Cancelled", "Inactive", "Rejected"]:
                logging.debug(f"Order {order_id} reached terminal status: {status}")
                return status == "Filled"
            if elapsed > timeout:
                logging.info(f"Timeout reached for order {order_id} after {elapsed:.1f} sec")
                return False

    def cancel_order_if_pending(self, order, stock_symbol):
        """Cancel the order if it's still pending; handle errors gracefully."""
        try:
            open_trades = self.ib.reqAllOpenOrders()
            open_order_ids = {trade.order.orderId for trade in open_trades if trade.order is not None}
            order_id = getattr(order, "orderId", None)
            logging.debug(f"Open order IDs: {open_order_ids}")
            if order_id is not None and order_id in open_order_ids:
                logging.info(f"Order {order_id} for {stock_symbol} is still pending; attempting cancellation.")
                self.ib.cancelOrder(order)
            else:
                logging.info(f"Order {order_id if order_id is not None else 'unknown'} for {stock_symbol} is not pending; skipping cancellation.")
        except Exception as e:
            logging.error(f"Error when cancelling order for {stock_symbol}: {e}")
    '''
    def get_tick_size(self, stock_symbol):
        contract = self.get_contract(stock_symbol)
        try:
            details = self.ib.reqContractDetails(contract)
            if details and len(details) > 0:
                tick_size = details[0].minTick
                if tick_size is None or tick_size <= 0:
                    tick_size = 0.01  # fallback default
                logging.debug(f"Tick size for {stock_symbol} is {tick_size}")
                return tick_size
        except Exception as e:
            logging.error(f"Error fetching tick size for {stock_symbol}: {e}")
        return 0.01  # default tick size if request fails
    '''
    def place_order_with_escalation(self, stock_symbol, action, amount_usd,
                                initial_timeout=3, escalation_timeout=2, max_escalations=3):
        base_price = self.get_mid_price(stock_symbol)
        if base_price is None:
            logging.error(f"Invalid mid price for {stock_symbol}. Skipping order.")
            return None
        price = base_price
        tick_size = 0.01   # Get dynamic tick size
        quantity = self.get_quantity(stock_symbol, amount_usd, price)
        if quantity <= 0:
            logging.error(f"Computed quantity is zero for {stock_symbol}.")
            return None

        contract = self.get_contract(stock_symbol)
        for escalation in range(max_escalations + 1):
            order = self.create_limit_order(action, quantity, price)
            logging.info(f"Attempt {escalation+1}: Placing {action} limit order for {stock_symbol} "
                         f"({quantity} shares) at ${price:.2f}")
            trade = self.ib.placeOrder(contract, order)
            current_timeout = initial_timeout if escalation == 0 else escalation_timeout
            if self.wait_for_fill(trade, timeout=current_timeout):
                logging.info(f"Order for {stock_symbol} filled at ${price:.2f} on attempt {escalation+1}")
                formatted_price = f"{price:.2f}"

                return {
                    "stock_symbol": stock_symbol,
                    "action": action,
                    "quantity": quantity,
                    "amount_usd": amount_usd,
                    "limit_price": formatted_price
                }
            else:
                logging.info(f"Order for {stock_symbol} did not fill within {current_timeout} sec at ${price:.2f}. Cancelling and escalating.")
                self.cancel_order_if_pending(order, stock_symbol)
                # For BUY orders, increase price; for SELL orders, decrease price.
                price = round_to_tick(price + tick_size if action == "BUY" else price - tick_size, tick_size)
        print(f"All escalated limit orders for {stock_symbol} did not fill. Placing market order.")
        market_order = self.create_market_order(action, quantity)
        trade_market = self.ib.placeOrder(contract, market_order)
        if not self.wait_for_fill(trade_market, timeout=20):
            logging.info(f"Market order for {stock_symbol} did not fill within 20 seconds. Cancelling order and moving on.")
            self.cancel_order_if_pending(market_order, stock_symbol)
            return None
        logging.info(f"Market order for {stock_symbol} filled.")
        return {
            "stock_symbol": stock_symbol,
            "action": action,
            "quantity": quantity,
            "amount_usd": amount_usd,
            "order_type": "Market"
        }

    def exit_order_with_escalation(self, symbol, current_action, quantity,
                                   initial_timeout=5, escalation_timeout=3, max_escalations=2, tick_size=0.01):
        """
        Exit an open trade using a tiered limit order strategy.
        For a trade opened with BUY, the exit order is a SELL.
        For a trade opened with SELL, the exit order is a BUY.
        Uses a shorter initial timeout (default 5 sec) and then escalates in price in 3-sec intervals.
        If still unfilled after max escalations, sends a market order.
        """
        
        tick_size = 0.01
        
        
        exit_action = "SELL" if current_action == "BUY" else "BUY"
        base_price = self.get_mid_price(symbol)
        if base_price is None:
            logging.error(f"Invalid mid price for exit of {symbol}. Skipping exit.")
            return None
        price = base_price
        # Get the contract for the symbol
        contract = self.get_contract(symbol)
        # Try the limit exit order with initial timeout and then escalation steps.
        for escalation in range(max_escalations + 1):
            order = self.create_limit_order(exit_action, quantity, price)
            logging.info(f"Exit attempt {escalation+1}: Placing {exit_action} limit order for {symbol} ({quantity} shares) at ${price:.2f}")
            trade = self.ib.placeOrder(contract, order)
            current_timeout = initial_timeout if escalation == 0 else escalation_timeout
            if self.wait_for_fill(trade, timeout=current_timeout):
                logging.info(f"Exit order for {symbol} filled at ${price:.2f} on attempt {escalation+1}")
                return {
                    "stock_symbol": symbol,
                    "action": exit_action,
                    "quantity": quantity,
                    "order_type": "Limit",
                    "limit_price": price
                }
            else:
                logging.info(f"Exit order for {symbol} did not fill within {current_timeout} sec at ${price:.2f}. Cancelling and escalating.")
                self.cancel_order_if_pending(order, symbol)
                # Adjust price to be more aggressive:
                if exit_action == "BUY":
                    price += tick_size  # raise price to buy back faster
                else:
                    price -= tick_size  # lower price to sell faster
                price = round_to_tick(price, tick_size)
        # If all limit attempts fail, place a market order.
        logging.info(f"All escalated exit limit orders for {symbol} did not fill. Placing market order.")
        market_order = self.create_market_order(exit_action, quantity)
        trade_market = self.ib.placeOrder(contract, market_order)
        while not trade_market.isDone():
            self.ib.sleep(1)
        logging.info(f"Market exit order for {symbol} filled.")
        return {
            "stock_symbol": symbol,
            "action": exit_action,
            "quantity": quantity,
            "order_type": "Market"
        }


