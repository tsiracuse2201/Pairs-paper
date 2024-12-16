def required_initial_capital(max_pairs, capital_per_pair, margin_requirement, loss_percentage, cushion):
    """
    Calculate the required initial capital given the scenario:
    
    Parameters:
    -----------
    max_pairs : int
        The maximum number of concurrent pair trades.
    capital_per_pair : float, optional
        The notional capital allocated per pair if no margin was used. Default is 10,000.
    margin_requirement : float, optional
        The fraction of the notional capital that must be covered by your own equity. Default is 0.6 (60%).
    loss_percentage : float, optional
        The fraction of the total initial position value you want to be able to lose without facing a margin call. Default is 0.5 (50%).
    cushion : float, optional
        The safety cushion to avoid margin calls. For example, 0.1 means you never want to exceed 90% of your margin capacity, leaving a 10% cushion.

    Returns:
    --------
    float
        The minimum initial capital required.
    """
    
    # Step 1: Calculate the total initial position at maximum concurrency
    total_position = max_pairs * capital_per_pair
    
    # Step 2: Without losses, you'd need margin_requirement * total_position of your own equity initially
    initial_equity_needed = total_position * margin_requirement
    
    # Step 3: Consider a large loss scenario: 
    # You want to be able to lose 'loss_percentage' * total_position without facing a margin call
    loss_amount = total_position * loss_percentage
    remaining_value = total_position - loss_amount  # The portfolio value after the loss
    
    # After this loss, to maintain the position at its reduced value,
    # you need margin_requirement * remaining_value of equity.
    post_loss_equity_needed = remaining_value * margin_requirement
    
    # Add the cushion. If you never want to exceed (1 - cushion) * 100% of your margin, 
    # effectively you have (1/(1 - cushion)) times the equity available. However, since 
    # we are considering that we want the post-loss equity to be at least post_loss_equity_needed * (1 + cushion), 
    # we can directly add the cushion as a multiplier to ensure safety.
    # Another interpretation: The cushion means if you can borrow up to 100% of your equity, 
    # you only want to use up to (1 - cushion)*100%. To ensure no margin call, let's 
    # increase the required equity by (1 + cushion) to have a comfortable buffer.
    # But given the previous explanation, let's follow the logic:
    # If cushion = 0.1, you want a 10% extra buffer above what's strictly needed.
    
    required_post_loss_equity_with_cushion = post_loss_equity_needed * (1 + cushion)
    
    # Step 4: Relate pre-loss and post-loss scenarios.
    # After losing 'loss_amount', your initial capital (C) is reduced by that same amount:
    # C - loss_amount >= required_post_loss_equity_with_cushion
    # Solve for C:
    required_initial = required_post_loss_equity_with_cushion + loss_amount
    
    return required_initial

# Example usage:
if __name__ == "__main__":
    max_pairs = 80
    capital_per_pair = 10000
    margin_requirement = 0.6  # 60%
    loss_percentage = .020    # 50% loss
    cushion = 0.1             # 10% cushion

    initial_capital = required_initial_capital(max_pairs, capital_per_pair, margin_requirement, loss_percentage, cushion)
    print(f"Required initial capital: ${initial_capital:,.2f}")
