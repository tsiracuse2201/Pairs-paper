def parse_text_file(file_path):
    results = []
    with open(file_path, 'r') as file:
        lines = file.readlines()
        for line in lines:
            print(line)
            if line.strip():
                result = eval(line.strip())  # Convert the string representation of the dictionary to a dictionary
                results.append(result)
    return results

def filter_pairs(file_path, max_std, min_hit_rate, min_profit):
    results = parse_text_file(file_path)

    filtered_pairs = [
        pair for pair in results
        if pair['std_deviation'] < max_std and pair['hit_rate'] > min_hit_rate and pair['total_profit'] > min_profit and pair['trade_amounts']>=trade_count
    ]

    return filtered_pairs

def save_filtered_results(filtered_pairs, output_file):
    with open(output_file, 'w') as f:
        for pair in filtered_pairs:
            f.write(f'{pair}\n')

# Example usage
file_path = 'pair_trading_results_5min_2024_10_03to2024_11_03_more_pre.txt'
max_std = 6
min_hit_rate = .64
min_profit = 500
trade_count = 4
filtered_pairs = filter_pairs(file_path, max_std, min_hit_rate, min_profit)
filename = f'pair_trading_results_5m_2024_10_03to2024_11_03morestd{max_std}_minhitrate{min_hit_rate}min_profit{min_profit}min_tradecount{trade_count}.txt'
save_filtered_results(filtered_pairs, filename)
