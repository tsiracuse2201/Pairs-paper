import requests
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = "wUnDzCqDRV3C_0aPhhfJfzgARepZ3rsx"

def load_tickers_from_file(file_path):
    with open(file_path, 'r') as file:
        tickers = [line.strip() for line in file if line.strip()]
    return tickers

def download_polygon_data(ticker, start_date, end_date):
    """
    Download 5-minute price data for a single ticker from Polygon.
    """
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/5/minute/{start_date}/{end_date}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 70000,  # large enough for a month of 5-min data
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
    """
    Download data for all tickers from Polygon in parallel and return a combined DataFrame.
    """
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

# Paths and dates
file_path = 'all_tickers_all.txt'
data_file = 'all_stock_data_5min_2024_07_03to2024_08_03.csv'

start_date = '2024-07-03'
end_date = '2024-08-03'

# Load tickers from file
stock_list = load_tickers_from_file(file_path)

# Check if the data file already exists
try:
    all_data = load_data_from_csv(data_file)
    print(f"Data loaded from {data_file}")
except FileNotFoundError:
    # Download data for all tickers from Polygon in parallel
    all_data = download_all_stock_data_from_polygon(stock_list, start_date, end_date, max_workers=20)
    if all_data is not None and not all_data.empty:
        save_data_to_csv(all_data, data_file)
    else:
        print("No data downloaded.")
        all_data = None
