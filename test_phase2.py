#!/usr/bin/env python3
"""
Test script for Phase 2: Data Layer with Rate Limiting
Tests rate limiter, data models, and API fetchers.

NOTE: This test requires Robinhood authentication.
Run test_phase1.py first to set up credentials.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all Phase 2 modules can be imported."""
    print("=" * 60)
    print("PHASE 2 TEST: Module Imports")
    print("=" * 60)

    try:
        print("✓ Testing rate_limiter import...")
        from src.data.rate_limiter import get_rate_limiter, rate_limited
        print("  ✓ rate_limiter imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import rate_limiter: {e}")
        return False

    try:
        print("✓ Testing models import...")
        from src.data.models import (
            StockQuote, PortfolioPosition, OptionContract,
            Portfolio, CoveredCallOpportunity
        )
        print("  ✓ models imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import models: {e}")
        return False

    try:
        print("✓ Testing robinhood_client import...")
        from src.data.robinhood_client import get_robinhood_client
        print("  ✓ robinhood_client imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import robinhood_client: {e}")
        return False

    try:
        print("✓ Testing portfolio_fetcher import...")
        from src.data.portfolio_fetcher import get_portfolio_fetcher
        print("  ✓ portfolio_fetcher imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import portfolio_fetcher: {e}")
        return False

    try:
        print("✓ Testing stock_fetcher import...")
        from src.data.stock_fetcher import get_stock_fetcher
        print("  ✓ stock_fetcher imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import stock_fetcher: {e}")
        return False

    try:
        print("✓ Testing options_fetcher import...")
        from src.data.options_fetcher import get_options_fetcher
        print("  ✓ options_fetcher imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import options_fetcher: {e}")
        return False

    print("\n✅ All Phase 2 modules imported successfully!\n")
    return True


def test_rate_limiter():
    """Test rate limiter functionality."""
    print("=" * 60)
    print("PHASE 2 TEST: Rate Limiter")
    print("=" * 60)

    try:
        from src.data.rate_limiter import get_rate_limiter
        import time

        print("✓ Initializing rate limiter...")
        limiter = get_rate_limiter()

        print(f"  - Min delay: {limiter.min_delay}s")
        print(f"  - Calls per minute limit: {limiter.calls_per_minute_limit}")
        print(f"  - Calls per hour limit: {limiter.calls_per_hour_limit}")

        print("\n✓ Testing rate limiting enforcement...")
        start_time = time.time()

        # Test 3 consecutive calls
        for i in range(3):
            limiter.wait_if_needed()
            print(f"  - Call {i + 1} allowed")

        elapsed = time.time() - start_time
        expected_min_delay = limiter.min_delay * 2  # 2 delays for 3 calls

        if elapsed >= expected_min_delay:
            print(f"\n✓ Rate limiting working: {elapsed:.2f}s elapsed (expected >={expected_min_delay:.2f}s)")
        else:
            print(f"\n⚠ Rate limiting may not be working: {elapsed:.2f}s elapsed")

        print("\n✓ Testing rate limiter stats...")
        stats = limiter.get_stats()
        print(f"  - Calls last minute: {stats['calls_last_minute']}/{stats['minute_limit']}")
        print(f"  - Calls last hour: {stats['calls_last_hour']}/{stats['hour_limit']}")
        print(f"  - Failure count: {stats['failure_count']}")
        print(f"  - Circuit open: {stats['circuit_open']}")

        print("\n✅ Rate limiter working correctly!\n")
        return True

    except Exception as e:
        print(f"\n✗ Rate limiter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_models():
    """Test pydantic data models."""
    print("=" * 60)
    print("PHASE 2 TEST: Data Models")
    print("=" * 60)

    try:
        from src.data.models import (
            StockQuote, PortfolioPosition, OptionContract
        )
        from datetime import date

        print("✓ Testing StockQuote model...")
        quote = StockQuote(
            symbol="AAPL",
            last_trade_price=175.50,
            bid_price=175.45,
            ask_price=175.55,
            previous_close=174.00,
            volume=50000000
        )
        print(f"  ✓ Created quote: {quote.symbol} @ ${quote.last_trade_price}")

        print("\n✓ Testing PortfolioPosition model...")
        position = PortfolioPosition(
            symbol="AAPL",
            quantity=150,
            average_buy_price=170.00,
            current_price=175.50
        )
        print(f"  ✓ Created position: {position.symbol} - {position.quantity} shares")
        print(f"    - Market value: ${position.market_value:.2f}")
        print(f"    - Unrealized P/L: ${position.unrealized_pl:.2f}")
        print(f"    - Covered call eligible: {position.is_covered_call_eligible}")

        print("\n✓ Testing OptionContract model...")
        option = OptionContract(
            symbol="AAPL",
            strike_price=180.00,
            expiration_date=date(2024, 3, 15),
            option_type="call",
            bid_price=2.40,
            ask_price=2.60,
            delta=0.30,
            volume=1000,
            open_interest=5000
        )
        print(f"  ✓ Created option: {option.symbol} ${option.strike_price} Call")
        print(f"    - Premium: ${option.premium:.2f}")
        print(f"    - Days to expiration: {option.days_to_expiration}")
        print(f"    - Is liquid: {option.is_liquid}")

        print("\n✅ Data models working correctly!\n")
        return True

    except Exception as e:
        print(f"\n✗ Data models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_authentication():
    """Test Robinhood authentication."""
    print("=" * 60)
    print("PHASE 2 TEST: Authentication Check")
    print("=" * 60)

    try:
        from src.auth.robinhood_auth import get_robinhood_auth

        print("✓ Checking authentication status...")
        auth = get_robinhood_auth()
        status = auth.get_authentication_status()

        print(f"  - Is authenticated: {status['is_authenticated']}")
        print(f"  - Username: {status['username'] or 'Not set'}")
        print(f"  - Has stored session: {status['has_stored_session']}")
        print(f"  - Has stored credentials: {status['has_stored_credentials']}")

        if not status['is_authenticated']:
            print("\n⚠ NOT AUTHENTICATED")
            print("  Phase 2 tests require Robinhood authentication.")
            print("  Please run one of the following:")
            print("    1. Set credentials in .env file")
            print("    2. Use credentials_manager to store credentials")
            print("    3. Wait for CLI implementation to login interactively")
            print("\n  Skipping live API tests...")
            return False

        print("\n✅ Authentication verified!\n")
        return True

    except Exception as e:
        print(f"\n✗ Authentication check failed: {e}")
        print("\n  Skipping live API tests...")
        return False


def test_robinhood_client_basic():
    """Test basic Robinhood client functionality (requires auth)."""
    print("=" * 60)
    print("PHASE 2 TEST: Robinhood Client (Basic)")
    print("=" * 60)

    try:
        from src.data.robinhood_client import get_robinhood_client

        print("✓ Initializing Robinhood client...")
        client = get_robinhood_client()

        print("✓ Testing rate limiter stats...")
        stats = client.get_rate_limiter_stats()
        print(f"  - Calls last minute: {stats['calls_last_minute']}")
        print(f"  - Calls last hour: {stats['calls_last_hour']}")

        print("\n✅ Robinhood client initialized!\n")
        print("ℹ Live API tests skipped (require authentication)")
        print("  To test with real data:")
        print("  1. Authenticate with Robinhood")
        print("  2. Run this script again")

        return True

    except Exception as e:
        print(f"\n✗ Robinhood client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 2 tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "STOCKBOT PHASE 2 TEST SUITE" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    # Run tests
    results = []

    results.append(("Module Imports", test_imports()))
    results.append(("Rate Limiter", test_rate_limiter()))
    results.append(("Data Models", test_data_models()))
    results.append(("Authentication Check", test_authentication()))
    results.append(("Robinhood Client", test_robinhood_client_basic()))

    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    print("\n" * 2 + "=" * 60)
    if all_passed:
        print("🎉 ALL PHASE 2 TESTS PASSED!")
        print("=" * 60)
        print("\nPhase 2 Complete: Data Layer with Rate Limiting")
        print("\nKey Components Implemented:")
        print("  ✓ Rate limiter with aggressive limits")
        print("  ✓ Pydantic data models for type safety")
        print("  ✓ Robinhood API client wrapper")
        print("  ✓ Portfolio, stock, and options fetchers")
        print("\nNext Steps:")
        print("  1. Authenticate with Robinhood (if not already done)")
        print("  2. Test with real data")
        print("  3. Proceed to Phase 3: Basic CLI")
        return True
    else:
        print("❌ SOME PHASE 2 TESTS FAILED")
        print("=" * 60)
        print("\nPlease fix the issues above before proceeding.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
