import ast

def process_file(input_file, output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            # Parse the line into a dictionary
            data = ast.literal_eval(line.strip())
            
            # Extract the relevant information
            ticker1 = data['ticker1']
            ticker2 = data['ticker2']
            total_profit = data['total_profit']
            
            # Format the string as required
            formatted_line = f"Pair: {ticker1} and {ticker2}, Profit: {total_profit}\n"
            print(formatted_line)
            # Write the formatted string to the output file
            outfile.write(formatted_line)

# Use the function with your input and output file names
process_file('pair_trading_results_more_5m_1mo_08272024VolAbove10000_McapAbove10000000htrtabv.8.txt', 'tradable_pair_trading_results_more_5m_1mo_08272024VolAbove10000_McapAbove10000000htrtabv.8.txt')
