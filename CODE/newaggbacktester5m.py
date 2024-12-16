import pandas as pd
import numpy as np
from statistics import mean

# Load all stock data once from a CSV file
all_data = pd.read_csv('all_stock_data_5min_2024_10_03to2024_11_03.csv', index_col=0, parse_dates=True)

def fetch_recent_data(tickers):
    """
    Instead of using yfinance, we fetch data from the already loaded 'all_data' DataFrame.
    This function returns only the columns (tickers) requested.
    """
    # Ensure the requested tickers are in all_data
    available_tickers = [t for t in tickers if t in all_data.columns]
    if not available_tickers:
        return pd.DataFrame()  # Return empty DataFrame if none of the tickers exist
    
    # Slice the data for only the requested tickers
    data = all_data[available_tickers].copy()
    # Forward fill any missing data
    data.ffill(inplace=True)
    return data

def calculate_profit(shares, entry_price, exit_price, position):
    if position == 'long':
        return (exit_price - entry_price) * shares
    elif position == 'short':
        return (entry_price - exit_price) * abs(shares)

def backtest_pairs(pairs):
    results = []
    for pair in pairs:
        
        print(pair)
        ticker1, ticker2, correlation = pair
        
        data = fetch_recent_data([ticker1, ticker2])

        # If we don't have data for both tickers, skip this pair
        if ticker1 not in data.columns or ticker2 not in data.columns:
            continue

        window = 40
        cash_balance = 10000

        exit_threshold = 0.5
        exit_threshold2 = -0.5
        enter1 = 1.5
        enter2 = -1.5
        trades = {}
        trade_count = 0
        in_trade1 = False
        in_trade2 = False
        total_profit = 0
        trade_profits = []

        # Accessing the close prices directly as columns
        spread = data[ticker1] - data[ticker2]

        mean_spread = spread.rolling(window=window).mean()
        std_spread = spread.rolling(window=window).std()
        z_score = (spread - mean_spread) / std_spread

        # Iterate over the time series after the rolling window
        for i in range(window, len(z_score)):
            # Conditions to enter trades
            if ((z_score.iloc[i] > enter1 and z_score.iloc[i] > 0) or 
                (z_score.iloc[i] < enter2 and z_score.iloc[i] < 0)):
                if not in_trade1 and not in_trade2:
                    trade_count += 1
                    entry_balance = cash_balance

                    # Determine positions (short-long or long-short)
                    if z_score.iloc[i] > enter1:
                        # Short ticker1, Long ticker2
                        shares1 = (0.5 * cash_balance) / data[ticker1].iloc[i]
                        shares2 = (0.5 * cash_balance) / data[ticker2].iloc[i]
                        position1 = 'short'
                        position2 = 'long'
                        in_trade1 = True
                    else:
                        # Long ticker1, Short ticker2
                        shares1 = (0.5 * cash_balance) / data[ticker1].iloc[i]
                        shares2 = (0.5 * cash_balance) / data[ticker2].iloc[i]
                        position1 = 'long'
                        position2 = 'short'
                        in_trade2 = True

                    trades[trade_count] = {
                        'entry_index': i,
                        'shares1': shares1,
                        'price1': data[ticker1].iloc[i],
                        'shares2': shares2,
                        'price2': data[ticker2].iloc[i],
                        'position1': position1,
                        'position2': position2
                    }

            # Conditions to exit trades
            if (z_score.iloc[i] < exit_threshold and in_trade1):
                in_trade1 = False
                trade = trades[trade_count]

                profit1 = calculate_profit(
                    trade['shares1'],
                    data[ticker1].iloc[trade['entry_index']],
                    data[ticker1].iloc[i],
                    trade['position1']
                )
                profit2 = calculate_profit(
                    trade['shares2'],
                    data[ticker2].iloc[trade['entry_index']],
                    data[ticker2].iloc[i],
                    trade['position2']
                )

                trade_profit = profit1 + profit2
                trade_profits.append(trade_profit)
                total_profit += trade_profit
                cash_balance = entry_balance + trade_profit
                trades[trade_count].update({'exit_index': i, 'profit': trade_profit})

            elif (z_score.iloc[i] > exit_threshold2 and in_trade2):
                in_trade2 = False
                trade = trades[trade_count]

                profit1 = calculate_profit(
                    trade['shares1'],
                    data[ticker1].iloc[trade['entry_index']],
                    data[ticker1].iloc[i],
                    trade['position1']
                )
                profit2 = calculate_profit(
                    trade['shares2'],
                    data[ticker2].iloc[trade['entry_index']],
                    data[ticker2].iloc[i],
                    trade['position2']
                )

                trade_profit = profit1 + profit2
                trade_profits.append(trade_profit)
                total_profit += trade_profit
                cash_balance = entry_balance + trade_profit
                trades[trade_count].update({'exit_index': i, 'profit': trade_profit})

        # Compute statistics
        pos = [x for x in trade_profits if x > 0]
        neg = [x for x in trade_profits if x <= 0]
        if len(trade_profits) == 0:
            continue
        try:
            sd_percent = (np.std(trade_profits) / mean(trade_profits)) * 100
        except ZeroDivisionError:
            continue
        plist = [(x / 10000) * 100 for x in trade_profits]

        results.append({
            'ticker1': ticker1,
            'ticker2': ticker2,
            'total_profit': total_profit,
            'hit_rate': len(pos) / (len(neg) + len(pos)) if (len(neg) + len(pos)) > 0 else 0,
            'ending_cash': cash_balance,
            'std_deviation': np.std(plist),
            'trade_amounts':len(trade_profits),
            'avg_profit': mean(trade_profits) if trade_profits else 0
        })

    return results

def load_data_from_file(file_path):
    result_list = []
    with open(file_path, 'r') as file:
        for line in file:
            # Strip whitespace and newline characters, then evaluate the line as a Python tuple
            try:
                data_tuple = eval(line.strip())
                if isinstance(data_tuple, tuple) and len(data_tuple) == 3:
                    result_list.append(data_tuple)
            except (SyntaxError, NameError):
                print(f"Skipping invalid line: {line.strip()}")
    return result_list

file_path = 'corrpolymulti_2024_10_03_to_2024_11_03.txt'
pairs = load_data_from_file(file_path)
results = backtest_pairs(pairs)

# Sort results by total_profit
sorted_results = sorted(results, key=lambda x: x['total_profit'], reverse=True)
with open('pair_trading_results_5min_2024_10_03to2024_11_03_pre.txt', 'w') as f:
    for result in sorted_results:
        f.write(f"Pair: {result['ticker1']} and {result['ticker2']}, Profit: {result['total_profit']}\n")

# Print top 3 most profitable pairs
print("Top 3 Most Profitable Pairs:")
for result in sorted_results[:3]:
    print(result)

with open('pair_trading_results_5min_2024_10_03to2024_11_03_more_pre.txt', 'w') as f:
    for result in sorted_results:
        f.write(f'{result}\n')
