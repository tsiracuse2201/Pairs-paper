import ast

input_file = "pair_trading_results_5m_2024_07_03to2024_08_03morestd6_minhitrate0.64min_profit500min_tradecount4.txt"   # Replace with your input file name
output_file = "pairsfor2023_2024.txt" # Replace with your desired output file name

with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
    for line in infile:
        line = line.strip()
        if not line:
            continue
        # Convert the string representation of a dict into an actual dict
        data = ast.literal_eval(line)

        # Extract ticker1 and ticker2 from the dict
        ticker1 = data['ticker1']
        ticker2 = data['ticker2']

        # Write the tuple with a hardcoded 1 as the third element
        outfile.write(f"('{ticker1}','{ticker2}',1)\n")
