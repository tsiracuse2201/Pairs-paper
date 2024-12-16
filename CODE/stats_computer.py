import pandas as pd
import numpy as np
import math
import openpyxl
# User-defined parameters
file_name = 'portfolio_mtm_values_2023_10_08to2024_12_06.xlsx'
actual_initial_capital =  22490027

  # The actual initial capital you want to use
var_level = 0.99
alpha = 1 - var_level  # 0.01

# Load the CSV file
df = pd.read_excel(file_name, index_col=0, parse_dates=True)

# Ensure 'Total_Portfolio_PnL' column exists
if 'Daily_Portfolio_PnL' not in df.columns:
    raise ValueError("'Daily_Portfolio_PnL' column not found in the DataFrame.")
# After loading the data
df = pd.read_excel(file_name, index_col=0, parse_dates=True)

# Drop the first 40 rows which are zeroes
df = df.iloc[40:]

# Now proceed with the rest of your calculations as before
if 'Daily_Portfolio_PnL' not in df.columns:
    raise ValueError("'Total_Portfolio_PnL' column not found in the DataFrame.")

df['Cumulative_PnL'] = df['Daily_Portfolio_PnL'].cumsum()
df['Portfolio_Value'] = actual_initial_capital + df['Cumulative_PnL']
print(df['Portfolio_Value'])
df['Daily_Return'] = df['Portfolio_Value'].pct_change()
df.dropna(subset=['Daily_Return'], inplace=True)

daily_returns = df['Daily_Return']
sorted_returns = daily_returns.sort_values()
var_threshold_return = sorted_returns.quantile(alpha)
var_1d_percent = var_threshold_return * 100.0
worst_tail = sorted_returns[sorted_returns <= var_threshold_return]
es_1d = worst_tail.mean() * 100.0

mean_daily_return = daily_returns.mean()
annualized_return = ((1 + mean_daily_return)**252) - 1
daily_vol = daily_returns.std()
monthly_vol = daily_vol * math.sqrt(21)
annual_vol = daily_vol * math.sqrt(252)
annual_rf = 0.04
daily_rf = annual_rf / 252
sharpe_ratio = (mean_daily_return - daily_rf) / daily_vol * math.sqrt(252) if daily_vol != 0 else np.nan

print("=== Portfolio Performance Metrics ===")
print(f"1-day 99% VaR: {var_1d_percent:.2f}%")
print(f"1-day 99% ES: {es_1d:.2f}%")
print(f"Average Daily Return: {mean_daily_return * 100:.4f}%")
print(f"Annualized Return: {annualized_return * 100:.4f}%")
print(f"Daily Volatility: {daily_vol * 100:.4f}%")
print(f"Monthly Volatility (approx): {monthly_vol * 100:.4f}%")
print(f"Annual Volatility: {annual_vol * 100:.4f}%")
print(f"Sharpe Ratio (annualized, 4% RF): {sharpe_ratio:.4f}")
