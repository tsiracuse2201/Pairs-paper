import requests
import pandas as pd
import numpy as np
from statistics import mean
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import openpyxl

API_KEY = "wUnDzCqDRV3C_0aPhhfJfzgARepZ3rsx"

def load_tickers_from_file(file_path):
    with open(file_path, 'r') as file:
        tickers = [line.strip() for line in file if line.strip()]
    return tickers

def load_pairs_from_file(file_path):
    result_list = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                data_tuple = eval(line.strip())
                if isinstance(data_tuple, tuple) and len(data_tuple) == 3:
                    result_list.append(data_tuple)
            except (SyntaxError, NameError):
                print(f"Skipping invalid line: {line.strip()}")
    return result_list

def download_polygon_data(ticker, start_date, end_date):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 70000,
        "apiKey": API_KEY
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None

    data = response.json()
    if data.get("status") != "OK" or "results" not in data:
        return None

    results = data["results"]
    df = pd.DataFrame(results)
    df["date"] = pd.to_datetime(df["t"], unit='ms')
    df.set_index("date", inplace=True)
    df = df[["c"]]
    df.columns = [ticker]
    return df

def download_all_stock_data_from_polygon(tickers, start_date, end_date, max_workers=10):
    dfs = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_polygon_data, t, start_date, end_date): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            df = future.result()
            if df is not None and not df.empty:
                dfs.append(df)
            else:
                print(f"No data for {ticker} within the given date range.")

    if not dfs:
        return None

    combined = pd.concat(dfs, axis=1)
    # Filter out tickers with fewer than 200 non-NaN values
    valid_mask = combined.count() >= 200
    combined = combined.loc[:, valid_mask]

    if combined.empty:
        return None

    combined.ffill(inplace=True)

    return combined

def save_data_to_csv(data, file_name):
    data.to_csv(file_name)
    print(f"Data saved to {file_name}")

def load_data_from_csv(file_name):
    return pd.read_csv(file_name, index_col=0, parse_dates=True)

def calculate_open_pnl(shares1, price1_entry, current_price1, position1,
                       shares2, price2_entry, current_price2, position2):
    def leg_pnl(shares, entry_price, current_price, position):
        if position == 'long':
            return (current_price - entry_price) * shares
        else:
            return (entry_price - current_price) * shares

    pnl_1 = leg_pnl(shares1, price1_entry, current_price1, position1)
    pnl_2 = leg_pnl(shares2, price2_entry, current_price2, position2)
    return pnl_1 + pnl_2

def convert_to_daily_increments(series):
    """
    Takes a cumulative series and returns daily increments:
    Each day's last timestamp will have the increment from 
    the previous day's end of day value, others set to 0.
    """
    # Resample to daily frequency using the last available value of that day
    daily_eod = series.resample('D').last().ffill().fillna(0)
    
    # Compute daily increments by differencing consecutive days
    daily_increments = daily_eod.diff().fillna(0)
    
    # Create a copy of the original series, set all to zero
    result = series.copy()
    result[:] = 0.0

    # Assign daily increment only to the last timestamp of each day
    for d in daily_increments.index:
        same_day_mask = (result.index.date == d.date())
        if same_day_mask.any():
            last_ts = result.index[same_day_mask][-1]
            result.at[last_ts] = daily_increments[d]
    
    return result


import datetime

def backtest_pairs(pairs, all_data, initial_capital, max_pairs):
    results = []
    portfolio_df = pd.DataFrame(index=all_data.index)
    capital_per_pair = initial_capital / max_pairs

    # Market hours definition (U.S. equities, for example)
    market_open = datetime.time(14, 30)
    market_close = datetime.time(21, 0)


    # Strategy parameters
    window = 40
    exit_threshold = 0.5
    exit_threshold2 = -0.5
    enter1 = 1.5
    enter2 = -1.5

    for ticker1, ticker2, correlation in pairs:
        if ticker1 not in all_data.columns or ticker2 not in all_data.columns:
            continue

        data = all_data[[ticker1, ticker2]].copy()
        spread = data[ticker1] - data[ticker2]
        mean_spread = spread.rolling(window=window).mean()
        std_spread = spread.rolling(window=window).std()
        z_score = (spread - mean_spread) / std_spread

        trade_profits = []
        total_profit = 0
        in_trade1 = False
        in_trade2 = False
        open_trade = None
        
        # pair_cumulative will hold a cumulative PnL line for each timestamp
        pair_cumulative = pd.Series(0.0, index=data.index)

        for i in range(window, len(z_score)):
            current_date = data.index[i]
            current_time = current_date.time()

            # Check if current timestamp is within market hours
            within_market_hours = (market_open <= current_time < market_close)

            has_open_position = in_trade1 or in_trade2

            # Always update the cumulative series based on open positions (to track PnL changes)
            if has_open_position:
                current_pnl = calculate_open_pnl(
                    open_trade['shares1'], open_trade['price1'], data[ticker1].iloc[i], open_trade['position1'],
                    open_trade['shares2'], open_trade['price2'], data[ticker2].iloc[i], open_trade['position2']
                )
                new_value = total_profit + current_pnl
                pair_cumulative.iloc[i] = new_value
            else:
                # No open position => cumulative stays at realized total_profit
                pair_cumulative.iloc[i] = total_profit

            # Only attempt to enter or exit trades if we are within market hours
            if within_market_hours:
                # Entry conditions
                if not has_open_position:
                    if (z_score.iloc[i] > enter1 and z_score.iloc[i] > 0):
                        # Enter short ticker1, long ticker2
                        shares1 = (0.5 * capital_per_pair) / data[ticker1].iloc[i]
                        shares2 = (0.5 * capital_per_pair) / data[ticker2].iloc[i]
                        position1 = 'short'
                        position2 = 'long'
                        in_trade1 = True
                        open_trade = {
                            'shares1': shares1,
                            'price1': data[ticker1].iloc[i],
                            'shares2': shares2,
                            'price2': data[ticker2].iloc[i],
                            'position1': position1,
                            'position2': position2
                        }

                    elif (z_score.iloc[i] < enter2 and z_score.iloc[i] < 0):
                        # Enter long ticker1, short ticker2
                        shares1 = (0.5 * capital_per_pair) / data[ticker1].iloc[i]
                        shares2 = (0.5 * capital_per_pair) / data[ticker2].iloc[i]
                        position1 = 'long'
                        position2 = 'short'
                        in_trade2 = True
                        open_trade = {
                            'shares1': shares1,
                            'price1': data[ticker1].iloc[i],
                            'shares2': shares2,
                            'price2': data[ticker2].iloc[i],
                            'position1': position1,
                            'position2': position2
                        }

                # Exit conditions
                if in_trade1 and (z_score.iloc[i] < exit_threshold):
                    final_pnl = calculate_open_pnl(
                        open_trade['shares1'], open_trade['price1'], data[ticker1].iloc[i], open_trade['position1'],
                        open_trade['shares2'], open_trade['price2'], data[ticker2].iloc[i], open_trade['position2']
                    )
                    trade_profits.append(final_pnl)
                    total_profit += final_pnl
                    in_trade1 = False
                    open_trade = None
                    pair_cumulative.iloc[i] = total_profit

                elif in_trade2 and (z_score.iloc[i] > exit_threshold2):
                    final_pnl = calculate_open_pnl(
                        open_trade['shares1'], open_trade['price1'], data[ticker1].iloc[i], open_trade['position1'],
                        open_trade['shares2'], open_trade['price2'], data[ticker2].iloc[i], open_trade['position2']
                    )
                    trade_profits.append(final_pnl)
                    total_profit += final_pnl
                    in_trade2 = False
                    open_trade = None
                    pair_cumulative.iloc[i] = total_profit

        # Convert cumulative to increments at each timestamp
        final_series = pair_cumulative.diff().fillna(0)

        if len(trade_profits) == 0:
            results.append({
                'ticker1': ticker1,
                'ticker2': ticker2,
                'total_profit': 0,
                'hit_rate': 0,
                'ending_cash': capital_per_pair,
                'std_deviation': 0,
                'trade_amounts': 0,
                'avg_profit': 0
            })
        else:
            try:
                avg_trade = np.mean(trade_profits)
                sd_percent = (np.std(trade_profits) / avg_trade) * 100 if avg_trade != 0 else 0
            except ZeroDivisionError:
                sd_percent = 0
                avg_trade = 0

            results.append({
                'ticker1': ticker1,
                'ticker2': ticker2,
                'total_profit': total_profit,
                'hit_rate': len([x for x in trade_profits if x > 0]) / len(trade_profits),
                'ending_cash': capital_per_pair + total_profit,
                'std_deviation': np.std([(x / capital_per_pair)*100 for x in trade_profits]),
                'trade_amounts': len(trade_profits),
                'avg_profit': avg_trade
            })

        portfolio_df[f"{ticker1}_{ticker2}"] = final_series

    if not portfolio_df.empty:
        portfolio_df['Incremental_Portfolio_PnL'] = portfolio_df.sum(axis=1)
        portfolio_df['Cumulative_PnL'] = portfolio_df['Incremental_Portfolio_PnL'].cumsum()
        portfolio_df['Total_Portfolio_Value'] = initial_capital + portfolio_df['Cumulative_PnL']
        daily_portfolio = portfolio_df['Total_Portfolio_Value'].resample('D').last().dropna()
        daily_returns = daily_portfolio.pct_change().dropna()
    else:
        daily_returns = pd.Series([])

    return results, portfolio_df, daily_returns


###################
# Main Execution
###################

file_path = 'all_tickers_all.txt'  # Input tickers list
pairs_file_path = 'pairsfor11_12.txt' # Input pairs
data_file = 'all_stock_data_5min_2024_11_03to2024_12_03.csv'


start_date = '2021-10-08'
end_date = '2022-12-06'

stock_list = load_tickers_from_file(file_path)

try:
    all_data = load_data_from_csv(data_file)
    print(f"Data loaded from {data_file}")
except FileNotFoundError:
    all_data = download_all_stock_data_from_polygon(stock_list, start_date, end_date, max_workers=20)
    if all_data is not None and not all_data.empty:
        save_data_to_csv(all_data, data_file)
    else:
        print("No data downloaded.")
        all_data = None

if all_data is not None:
    # User-defined variables
    max_pairs=80
    initial_capital = max_pairs * 10000.0

    pairs = load_pairs_from_file(pairs_file_path)
    results, portfolio_df, daily_returns = backtest_pairs(pairs, all_data, initial_capital, max_pairs)

    sorted_results = sorted(results, key=lambda x: x['total_profit'], reverse=True)
    with open('pair_trading_results_2019_10_08to2023_12_06.txt', 'w') as f:
        for result in sorted_results:
            f.write(f"Pair: {result['ticker1']} and {result['ticker2']}, Profit: {result['total_profit']}\n")

    print("Top 3 Most Profitable Pairs:")
    for result in sorted_results[:3]:
        print(result)

    portfolio_df.to_excel('portfolio_mtm_values_5min_2024_11_03to2024_12_03.xlsx')
    print("Saved portfolio MTM spreadsheet to 'portfolio_mtm_values_2023_10_08to2024_12_06.xlxs'")

    daily_returns.to_csv('daily_returns5min_2024_08_03to2024_09_03.csv', header=['Daily_Return'])
    print("Saved daily returns to 'daily_returns.csv'")

if not daily_returns.empty:
    # Calculate 1-day 99% VaR and ES as percentages
    # var_level = 0.99 => alpha = 0.01 (1% worst losses)
    var_level = 0.99
    alpha = 1 - var_level  # alpha = 0.01
    
    # Remove the first 40 days and the last 28 days
    
    
    # Quantile at 1% gives us the return level at the worst 1%
    var_threshold_return = daily_returns.quantile(alpha)  # This is a negative return
    
    # Convert to percentage:
    # If var_threshold_return = -0.02 => VaR is a 2% loss
    # VaR is the absolute value of that return times 100 to get a percentage
    var_1d_percent = -var_threshold_return * 100  # e.g. 2.0 means 2%
    
    # Extract worst 1% of returns
    worst_tail_returns = daily_returns[daily_returns <= var_threshold_return]
    # ES is the mean of these worst tail returns, also converted to percentage
    es_1d_percent = -worst_tail_returns.mean() * 100
    
    # Approximate 10-day VaR and ES, assuming sqrt(10) scaling
    var_10d_percent = var_1d_percent * np.sqrt(10)
    es_10d_percent = es_1d_percent * np.sqrt(10)
    
    print(f"1-day 99% VaR: {var_1d_percent:.2f}%")
    print(f"1-day 99% ES: {es_1d_percent:.2f}%")
    print(f"10-day 99% VaR (approx.): {var_10d_percent:.2f}%")
    print(f"10-day 99% ES (approx.): {es_10d_percent:.2f}%")
else:
    print("No daily returns available to calculate VaR/ES.")


