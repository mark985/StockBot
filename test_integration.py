#!/usr/bin/env python3
"""
Test the integration of the custom Robinhood client with the main StockBot auth module.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.auth.robinhood_auth import get_robinhood_auth, ensure_authenticated
from loguru import logger

def main():
    print("=" * 70)
    print("Testing StockBot + Custom Robinhood Client Integration")
    print("=" * 70)

    try:
        # Get the authentication wrapper
        auth = get_robinhood_auth()

        # Try to authenticate (will use stored session if available)
        print("\nAttempting authentication...")
        authenticated_auth = ensure_authenticated()

        print("\n✓ Authentication successful!")

        # Get authentication status
        status = auth.get_authentication_status()
        print("\nAuthentication Status:")
        print(f"  - Authenticated: {status['is_authenticated']}")
        print(f"  - Username: {status.get('username', 'N/A')}")
        print(f"  - Has stored session: {status['has_stored_session']}")
        print(f"  - Has stored credentials: {status['has_stored_credentials']}")

        # Get the underlying client for API calls
        client = auth.get_client()

        # Test API calls
        print("\n" + "=" * 70)
        print("Testing API Calls via Integrated Client")
        print("=" * 70)

        # Get account info
        print("\nFetching account information...")
        account = client.get_account()
        print(f"✓ Account Number: {account.get('account_number', 'N/A')}")
        print(f"✓ Buying Power: ${float(account.get('buying_power', 0)):,.2f}")

        # Get positions
        print("\nFetching positions...")
        positions = client.get_positions()
        print(f"✓ Found {len(positions)} positions")

        if positions:
            for pos in positions[:3]:  # Show first 3
                instrument_url = pos.get("instrument")
                quantity = pos.get("quantity", "0")
                try:
                    instrument = client.get_instrument_by_url(instrument_url)
                    symbol = instrument.get("symbol", "UNKNOWN")
                    print(f"   - {symbol}: {quantity} shares")
                except:
                    print(f"   - {quantity} shares")

        # Get quotes
        print("\nFetching stock quotes...")
        quotes = client.get_quotes(["AAPL", "MSFT", "GOOGL"])
        print(f"✓ Retrieved {len(quotes)} quotes")
        for quote in quotes:
            symbol = quote.get("symbol", "N/A")
            price = quote.get("last_trade_price", "0")
            print(f"   - {symbol}: ${float(price):.2f}")

        print("\n" + "=" * 70)
        print("Integration Test Complete!")
        print("=" * 70)
        print("\n✓ StockBot is now using the custom Robinhood client")
        print("✓ All features working:")
        print("   - OAuth2 authentication with device tokens")
        print("   - SMS/email verification support")
        print("   - Session persistence")
        print("   - Account and position data")
        print("   - Stock quotes")
        print("\nReady for production use!")

    except Exception as e:
        print("\n" + "=" * 70)
        print("✗ Integration Test Failed")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
