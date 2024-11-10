from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Tuple, Dict

@dataclass
class Market:
    event_id: str
    market_name: str
    yes_price: Decimal  # Represented as probability (0-1)
    no_price: Decimal   # Represented as probability (0-1)
    max_position: Decimal
    service_name: str

class CrossMarketArbitrage:
    def __init__(self, fee_rate: Decimal = Decimal('0.00')):
        self.fee_rate = fee_rate

    def find_arbitrage(self, market1: Market, market2: Market, min_return: Decimal = Decimal('0.01')) -> Optional[Dict]:
        """
        Find arbitrage by taking opposing positions across two markets.
        Basic principle: if YES on one + NO on other < 1, there's guaranteed profit
        """
        # Calculate costs including fees for each possible combination
        # Strategy 1: Buy YES on market1, NO on market2
        strat1_cost = (market1.yes_price * (1 + self.fee_rate) + 
                    market2.no_price * (1 + self.fee_rate))
        
        # Strategy 2: Buy NO on market1, YES on market2
        strat2_cost = (market1.no_price * (1 + self.fee_rate) + 
                    market2.yes_price * (1 + self.fee_rate))
        
        # Find best strategy
        best_cost = min(strat1_cost, strat2_cost)
        is_strat1 = strat1_cost < strat2_cost
        
        # If total cost < 1 and meets minimum return requirement, we have an arbitrage opportunity
        if best_cost >= Decimal('1') or (Decimal('1') - best_cost) / best_cost < min_return:
            return None
            
        # Calculate profit per unit invested
        profit_per_unit = (Decimal('1') - best_cost) / best_cost
        
        if is_strat1:
            # Calculate maximum shares based on market liquidity and prices with fees
            max_yes_shares = market1.max_position / (market1.yes_price * (1 + self.fee_rate))
            max_no_shares = market2.max_position / (market2.no_price * (1 + self.fee_rate))
            max_shares = min(max_yes_shares, max_no_shares)
            
            positions = {
                market1.service_name: ("YES", market1.yes_price, market1.max_position),
                market2.service_name: ("NO", market2.no_price, market2.max_position)
            }
        else:
            # Calculate maximum shares for strategy 2
            max_no_shares = market1.max_position / (market1.no_price * (1 + self.fee_rate))
            max_yes_shares = market2.max_position / (market2.yes_price * (1 + self.fee_rate))
            max_shares = min(max_no_shares, max_yes_shares)
            
            positions = {
                market1.service_name: ("NO", market1.no_price, market1.max_position),
                market2.service_name: ("YES", market2.yes_price, market2.max_position)
            }
        
        # Round down to avoid precision issues
        max_shares = max_shares.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        
        # Calculate total investment needed
        total_cost = max_shares * best_cost
        
        # Calculate total profit
        total_profit = max_shares * (Decimal('1') - best_cost)
        
        return {
            'positions': positions,
            'shares': max_shares,
            'profit_per_unit': profit_per_unit,
            'total_profit': total_profit,
            'total_cost': total_cost,
            'best_cost': best_cost
        }

    def calculate_optimal_amounts(self,
                                arb_opportunity: Dict,
                                bankroll: Decimal,
                                min_return: Decimal = Decimal('0.01')) -> Dict[str, Decimal]:
        """
        Calculate optimal position sizes for prediction market arbitrage,
        taking into account available liquidity in each market.
        """
        positions = arb_opportunity['positions']
        total_cost = arb_opportunity['total_cost']
        best_cost = arb_opportunity['best_cost']
        
        # If total cost exceeds bankroll, scale down
        scale = min(Decimal('1'), bankroll / total_cost)
        shares = arb_opportunity['shares'] * scale
        
        # Calculate investment amount for each market
        amounts = {}
        running_total = Decimal('0')
        service_list = list(positions.keys())
        
        # Calculate amounts for all but the last market
        for service in service_list[:-1]:
            side, price, _ = positions[service]
            effective_price = price * (1 + self.fee_rate)
            amount = (shares * effective_price).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            amounts[service] = amount
            running_total += amount
        
        # Calculate last market amount to ensure we maintain exact ratio
        last_service = service_list[-1]
        last_side, last_price, _ = positions[last_service]
        last_effective_price = last_price * (1 + self.fee_rate)
        amounts[last_service] = (shares * last_effective_price).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        
        # Verify minimum return is met with actual amounts
        total_investment = sum(amounts.values())
        expected_profit = shares - total_investment
        if expected_profit / total_investment < min_return:
            return {}
        
        return amounts

    def validate_position_sizes(self,
                            amounts: Dict[str, Decimal],
                            arb_opportunity: Dict) -> Tuple[bool, str]:
        """
        Validate that position sizes will result in guaranteed profit and respect liquidity constraints.
        """
        if not amounts:
            return False, "No valid positions found"
            
        positions = arb_opportunity['positions']
        best_cost = arb_opportunity['best_cost']
        
        # Calculate total investment and effective shares
        total_investment = sum(amounts.values())
        shares = total_investment / best_cost
        
        # Check liquidity constraints
        for service, amount in amounts.items():
            _, _, max_position = positions[service]
            if amount > max_position:
                return False, f"Position size ${float(amount):.2f} exceeds available liquidity ${float(max_position):.2f} on {service}"
        
        # Calculate profit and ROI
        profit = shares - total_investment
        roi = (profit / total_investment) * 100
        
        if roi < Decimal('1'):
            return False, f"ROI of {float(roi):.2f}% is below minimum threshold of 1%"
        
        if profit <= 0:
            return False, f"No guaranteed profit. Expected profit: ${float(profit):.2f}"
            
        return True, f"Valid positions with ${float(profit):.2f} minimum profit ({float(roi):.2f}% ROI)"

    def execute_arbitrage(self,
                     market1: Market,
                     market2: Market,
                     opportunity: Dict,
                     amounts: Dict[str, Decimal]) -> None:
        """
        Execute the arbitrage trades (placeholder for actual execution)
        """
        positions = opportunity['positions']
        total_investment = sum(amounts.values())
        shares = total_investment / opportunity['best_cost']
        
        print(f"\nExecuting arbitrage for {market1.market_name}:")
        for service, (side, price, max_position) in positions.items():
            amount = amounts[service]
            liquidity_used = (amount / max_position * 100).quantize(Decimal('0.1'))
            print(f"  {service}: {side} position at {float(price):.3f} "
                f"with ${float(amount):.2f} ({float(liquidity_used)}% of available liquidity)")
        
        # Calculate profit and ROI
        profit = shares - total_investment
        roi = ((profit / total_investment) * 100).quantize(Decimal('0.01'))
        print(f"\nExpected profit: ${float(profit):.2f} ({float(roi):.2f}% return)")

def example():
    # Example markets for "Will BTC exceed $100k in 2024?"
    market1 = Market(
        event_id="btc-100k-2024",
        market_name="BTC > $100k in 2024",
        yes_price=Decimal('0.09'),
        no_price=Decimal('0.94'),
        max_position=Decimal('0.9'),
        service_name="Kalshi"
    )
    
    market2 = Market(
        event_id="btc-100k-2024",
        market_name="BTC > $100k in 2024",
        yes_price=Decimal('0.15'),
        no_price=Decimal('0.86'),
        max_position=Decimal('80.99'),
        service_name="Polymarket"
    )
    
    arbitrageur = CrossMarketArbitrage(fee_rate=Decimal('0.00'))
    
    opportunity = arbitrageur.find_arbitrage(market1, market2)
    
    if opportunity:
        amounts = arbitrageur.calculate_optimal_amounts(
            arb_opportunity=opportunity,
            bankroll=Decimal('5000'),
            min_return=Decimal('0.01')  # 1% minimum return
        )
        
        is_valid, message = arbitrageur.validate_position_sizes(amounts, opportunity)
        
        if is_valid:
            arbitrageur.execute_arbitrage(market1, market2, opportunity, amounts)
            
            total_investment = sum(amounts.values())
            shares = total_investment / opportunity['best_cost']
            profit = shares - total_investment
            roi = ((profit / total_investment) * 100).quantize(Decimal('0.01'))
            
            print("\nArbitrage Details:")
            print(f"Total Investment: ${float(total_investment):.2f}")
            print(f"Expected Profit: ${float(profit):.2f}")
            print(f"ROI: {float(roi):.2f}%")
            print(f"Capital Efficiency: {float(total_investment/Decimal('5000')*100):.1f}% of bankroll used")
        else:
            print(f"\nValidation Failed: {message}")
    else:
        print("\nNo viable arbitrage opportunity found")
        print("Market prices (including fees):")
        print(f"Kalshi - YES: {float(market1.yes_price * (1 + arbitrageur.fee_rate)):.3f}, "
              f"NO: {float(market1.no_price * (1 + arbitrageur.fee_rate)):.3f}")
        print(f"Polymarket - YES: {float(market2.yes_price * (1 + arbitrageur.fee_rate)):.3f}, "
              f"NO: {float(market2.no_price * (1 + arbitrageur.fee_rate)):.3f}")

if __name__ == "__main__":
    example()