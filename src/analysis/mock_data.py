"""
Mock data generator for testing Gemini analysis without Robinhood authentication.
Provides realistic portfolio and options data for development and testing.
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import random


def generate_mock_portfolio() -> Dict[str, Any]:
    """
    Generate mock portfolio data for testing.

    Returns:
        dict: Portfolio data with holdings
    """
    portfolio = {
        "AAPL": {
            "shares": 200,
            "current_price": 185.50,
            "average_buy_price": 175.00,
            "total_value": 37100.00,
        },
        "MSFT": {
            "shares": 150,
            "current_price": 380.25,
            "average_buy_price": 360.00,
            "total_value": 57037.50,
        },
        "GOOGL": {
            "shares": 100,
            "current_price": 142.75,
            "average_buy_price": 135.00,
            "total_value": 14275.00,
        },
        "NVDA": {
            "shares": 300,
            "current_price": 495.80,
            "average_buy_price": 450.00,
            "total_value": 148740.00,
        },
        "TSLA": {
            "shares": 50,  # Only 50 shares - not eligible for covered calls
            "current_price": 245.30,
            "average_buy_price": 250.00,
            "total_value": 12265.00,
        },
    }

    return portfolio


def generate_mock_options(symbol: str, current_price: float, num_options: int = 10) -> List[Dict[str, Any]]:
    """
    Generate mock options chain for a symbol.

    Args:
        symbol: Stock ticker symbol
        current_price: Current stock price
        num_options: Number of option contracts to generate

    Returns:
        list: List of option contracts with metrics
    """
    options = []
    base_date = datetime.now()

    # Generate options with varying strikes and expirations
    for i in range(num_options):
        # Strike prices 2-15% OTM
        otm_pct = random.uniform(2, 15)
        strike = current_price * (1 + otm_pct / 100)
        strike = round(strike / 0.5) * 0.5  # Round to nearest $0.50

        # Expiration 7-45 days out
        days_to_exp = random.randint(7, 45)
        expiration_date = base_date + timedelta(days=days_to_exp)

        # Calculate premium (higher premium for near-the-money, longer-dated options)
        base_premium = current_price * 0.015  # ~1.5% of stock price
        premium = base_premium * (1 - (otm_pct / 100)) * (days_to_exp / 30)
        premium = round(premium, 2)

        # Total premium for 1 contract (100 shares)
        total_premium = premium * 100

        # ROI and annualized return
        roi = (premium / current_price) * 100
        annualized_return = (roi / days_to_exp) * 365

        # Delta (probability of finishing ITM)
        delta = max(0.05, min(0.60, 0.50 - (otm_pct / 50)))

        # IV (implied volatility) - random but realistic
        iv = random.uniform(0.25, 0.55)

        # Volume and OI
        volume = random.randint(100, 5000)
        open_interest = random.randint(200, 10000)

        option = {
            "symbol": symbol,
            "strike": strike,
            "expiration_date": expiration_date.strftime("%Y-%m-%d"),
            "days_to_expiration": days_to_exp,
            "premium": premium,
            "total_premium": total_premium,
            "roi": round(roi, 2),
            "annualized_return": round(annualized_return, 2),
            "delta": round(delta, 3),
            "iv": round(iv, 3),
            "volume": volume,
            "open_interest": open_interest,
            "otm_percentage": round(otm_pct, 2),
            "bid": round(premium - 0.05, 2),
            "ask": round(premium + 0.05, 2),
        }

        options.append(option)

    # Sort by annualized return (descending)
    options.sort(key=lambda x: x["annualized_return"], reverse=True)

    return options


def generate_full_mock_data() -> Dict[str, Any]:
    """
    Generate complete mock data for covered call analysis.

    Returns:
        dict: Complete dataset with portfolio, options, and market context
    """
    portfolio = generate_mock_portfolio()

    # Generate options for each eligible holding (100+ shares)
    all_options = []
    for symbol, holding in portfolio.items():
        if holding["shares"] >= 100:
            options = generate_mock_options(symbol, holding["current_price"], num_options=8)
            all_options.extend(options)

    # Sort all options by annualized return
    all_options.sort(key=lambda x: x["annualized_return"], reverse=True)

    # Market context
    market_context = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "vix": round(random.uniform(12, 25), 2),
        "trend": random.choice(["Bullish", "Neutral", "Bearish"]),
        "sp500_change": round(random.uniform(-1.5, 2.0), 2),
    }

    return {
        "portfolio": portfolio,
        "options": all_options,
        "market_context": market_context,
    }


def print_mock_data_summary(data: Dict[str, Any]) -> None:
    """
    Print a summary of mock data for verification.

    Args:
        data: Mock data dictionary
    """
    print("\n" + "=" * 60)
    print("MOCK DATA SUMMARY")
    print("=" * 60)

    print("\nPortfolio Holdings:")
    print("-" * 60)
    for symbol, holding in data["portfolio"].items():
        eligible = "✓" if holding["shares"] >= 100 else "✗"
        print(f"{eligible} {symbol:6s} | {holding['shares']:4d} shares @ ${holding['current_price']:.2f} = ${holding['total_value']:,.2f}")

    print(f"\nTotal Portfolio Value: ${sum(h['total_value'] for h in data['portfolio'].values()):,.2f}")

    print("\nTop 5 Options by Annualized Return:")
    print("-" * 60)
    for i, opt in enumerate(data["options"][:5], 1):
        print(f"{i}. {opt['symbol']:6s} ${opt['strike']:.2f} Call ({opt['days_to_expiration']} days)")
        print(f"   Premium: ${opt['premium']:.2f} | ROI: {opt['roi']:.2f}% | Ann. Return: {opt['annualized_return']:.2f}%")

    print("\nMarket Context:")
    print("-" * 60)
    for key, value in data["market_context"].items():
        print(f"  {key}: {value}")

    print("=" * 60 + "\n")
