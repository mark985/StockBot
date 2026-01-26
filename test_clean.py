#!/usr/bin/env python3
"""
Clean test with minimal logging - only shows important info.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging BEFORE importing modules
from loguru import logger
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"  # Only show INFO, WARNING, ERROR - hide DEBUG
)

from src.auth.robinhood_auth import get_robinhood_auth, ensure_authenticated

def main():
    print("=" * 70)
    print("StockBot - Testing Custom Robinhood Client")
    print("=" * 70)

    try:
        # Authenticate (will use stored session if available)
        print("\nAuthenticating...")
        auth = ensure_authenticated()

        print("✓ Authentication successful!")

        # Get the client
        client = auth.get_client()

        # Get account info
        print("\nFetching account information...")
        account = client.get_account()
        print(f"✓ Account: {account.get('account_number', 'N/A')}")
        print(f"✓ Buying Power: ${float(account.get('buying_power', 0)):,.2f}")

        # Get positions
        print("\nFetching positions...")
        positions = client.get_positions()
        print(f"✓ Found {len(positions)} positions")

        if positions:
            print("\nYour positions:")
            for pos in positions[:5]:  # Show first 5
                instrument_url = pos.get("instrument")
                quantity = pos.get("quantity", "0")
                avg_price = pos.get("average_buy_price", "0")

                try:
                    instrument = client.get_instrument_by_url(instrument_url)
                    symbol = instrument.get("symbol", "UNKNOWN")
                    print(f"  • {symbol}: {quantity} shares @ ${float(avg_price):.2f}")
                except:
                    print(f"  • {quantity} shares")

        # Get quotes
        print("\nFetching stock quotes...")
        quotes = client.get_quotes(["AAPL", "MSFT", "GOOGL"])
        print(f"✓ Retrieved {len(quotes)} quotes")

        for quote in quotes:
            symbol = quote.get("symbol", "N/A")
            price = quote.get("last_trade_price", "0")
            print(f"  • {symbol}: ${float(price):.2f}")

        print("\n" + "=" * 70)
        print("✓ All tests passed!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
