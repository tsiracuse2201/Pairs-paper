import yfinance as yf

# Read the input data from the text file
with open('tradable_pair_trading_results_more_5m_1mo_08272024VolAbove10000_McapAbove10000000htrtabv.8.txt', 'r') as file:
    pairs_lines = file.readlines()

# Function to get market cap of a stock and check if it is a regional bank
def get_stock_data(stock):
    ticker = yf.Ticker(stock)
    info = ticker.info
    #print(info)
    vol = info.get('averageVolume')
    
    marketCap = info.get('marketCap')
    # Check if it is a regional bank
    
    return vol, marketCap

# List to store pairs where both have market cap greater than 4 billion and are not regional banks
qualified_pairs = []

for line in pairs_lines:
    # Parse the stock symbols and profit from the line
    parts = line.strip().split(',')
    pair = parts[0].split(': ')[1]
    profit = parts[1].split(': ')[1]
    stock1, stock2 = pair.split(' and ')
    print(stock1,stock2)
    
    # Get market caps and bank types
    try:
        vol1, marketCap1 = get_stock_data(stock1)
        vol2, marketCap2 = get_stock_data(stock2)
    except:
        continue

    # Check if both market caps are greater than 4 billion and neither are regional banks
    #and (not is_regional1 and not is_regional2)
    try:
      if (vol1 > 500000 and vol2 > 500000):
          qualified_pairs.append(f"Pair: {stock1} and {stock2}, Profit: {profit}")
    except:
      continue

# Write qualified pairs to a new text file
with open('nowtrader.txt', 'w') as file:
    for pair in qualified_pairs:
        file.write(pair + "\n")

print("Filtered pairs written to 'filtered_tradeable_pairs.txt'")
