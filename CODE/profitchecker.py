import json
from collections import defaultdict

def main():
    profit_file = "profits.json"  # Path to your JSON file
    try:
        with open(profit_file, "r") as f:
            profits = json.load(f)
    except Exception as e:
        print(f"Error loading {profit_file}: {e}")
        return

    # Use a dictionary to sum net profits by pair key.
    pair_profit = defaultdict(float)
    
    for record in profits:
        pair_key = record.get("pair_key", "UNKNOWN")
        net_profit = record.get("net_profit", 0)
        pair_profit[pair_key] += net_profit

    # Print the profit summary by pair.
    print("Profit Summary by Pair:")
    for pair, profit in sorted(pair_profit.items(), key=lambda x: x[0]):
        print(f"{pair}: {profit:.2f}")

    # Also calculate and print the overall total profit.
    total_net_profit = sum(pair_profit.values())
    print("\nTotal Net Profit: {:.2f}".format(total_net_profit))

if __name__ == "__main__":
    main()
