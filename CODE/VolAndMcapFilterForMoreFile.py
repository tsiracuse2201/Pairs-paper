import ast  # For safely evaluating the input lines as dictionaries
import yfinance as yf

# Read the input data from the text file
with open('pair_trading_results_more_5m_1mo_08272024VolAbove10000_McapAbove10000000htrtabv.8.txt', 'r') as file:
    pairs_lines = file.readlines()

# Function to get market cap and volume of a stock
def get_stock_data(stock):
    ticker = yf.Ticker(stock)
    info = ticker.info
    vol = info.get('averageVolume')
    marketCap = info.get('marketCap')
    return vol, marketCap

# List to store pairs that meet the criteria
qualified_pairs = []

for line in pairs_lines:
    # Convert the string line to a dictionary
    try:
        pair_data = ast.literal_eval(line.strip())  # Safely parse the dictionary from string
    except (SyntaxError, ValueError):
        continue  # Skip if the line is not in proper format

    # Extract the stock tickers and other details from the dictionary
    stock1 = pair_data['ticker1']
    stock2 = pair_data['ticker2']
    total_profit = pair_data['total_profit']
    hit_rate = pair_data['hit_rate']
    ending_cash = pair_data['ending_cash']
    std_deviation = pair_data['std_deviation']
    avg_profit = pair_data['avg_profit']

    # Get market caps and volumes for both stocks
    try:
        vol1, marketCap1 = get_stock_data(stock1)
        
        vol2, marketCap2 = get_stock_data(stock2)
        print(stock1,stock2)
    except:
        print('error')
        continue

    # Check if both market caps are greater than 100 million and volumes greater than 100,000
    if (vol1 > 500000 and vol2 > 500000):
        qualified_pairs.append({
            'ticker1': stock1,
            'ticker2': stock2,
            'total_profit': total_profit,
            'hit_rate': hit_rate,
            'ending_cash': ending_cash,
            'std_deviation': std_deviation,
            'avg_profit': avg_profit
        })

# Write qualified pairs to a new text file in the desired format
with open('new_traer.txt', 'w') as file:
    for pair in qualified_pairs:
        file.write(str(pair) + "\n")

print("Filtered pairs written to 'tradeable_pairs_output.txt'")
