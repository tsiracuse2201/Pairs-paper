import pandas as pd
import numpy as np
import math
import openpyxl

# User-defined parameters
file_name = 'portfolio_mtm_values_5min_2024_11_03to2024_12_03.xlsx'
actual_initial_capital = 533440  # The actual initial capital you want to use
var_level = 0.99
alpha = 1 - var_level  # 0.01

# Load the Excel file
df = pd.read_excel(file_name, index_col=0, parse_dates=True)

# Check that we have the increments at 5-minute intervals
# For this code to work, you should have a column like 'Incremental_Portfolio_PnL'
# that represents the PnL increments at the 5-minute frequency.
if 'Incremental_Portfolio_PnL' not in df.columns:
    raise ValueError("'Incremental_Portfolio_PnL' column not found in the DataFrame.")

# Aggregate 5-minute increments to daily increments by summing over each day
daily_increments = df['Incremental_Portfolio_PnL'].resample('D').sum()

# Drop the first 40 days if you want, adjust as needed
print(daily_increments)

# If desired, you can also drop the last 28 days later after computing returns
# but let's first compute all metrics

# Compute cumulative PnL from daily increments
cumulative_pnl = daily_increments.cumsum()

# Compute daily portfolio value
portfolio_value = actual_initial_capital + cumulative_pnl

# Compute daily returns
daily_returns = portfolio_value.pct_change().dropna()


if daily_returns.empty:
    print("No daily returns available to calculate VaR/ES.")
else:
    # Sort returns to find VaR
    sorted_returns = daily_returns.sort_values()
    var_threshold_return = sorted_returns.quantile(alpha)  # 1% quantile (worst losses)
    # VaR is the absolute value of that return times 100 to get a percentage
    var_1d_percent = -var_threshold_return * 100.0

    # Extract the worst tail returns for ES calculation
    worst_tail = sorted_returns[sorted_returns <= var_threshold_return]
    es_1d = -worst_tail.mean() * 100.0

    # Annualization metrics
    mean_daily_return = daily_returns.mean()
    annualized_return = ((1 + mean_daily_return)**252) - 1
    daily_vol = daily_returns.std()
    monthly_vol = daily_vol * math.sqrt(21)
    annual_vol = daily_vol * math.sqrt(252)

    # Risk-free rate assumptions
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
