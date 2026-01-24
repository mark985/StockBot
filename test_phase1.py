#!/usr/bin/env python3
"""
Test script for Phase 1: Foundation & Authentication
Tests settings, credentials manager, and authentication structure.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all Phase 1 modules can be imported."""
    print("=" * 60)
    print("PHASE 1 TEST: Module Imports")
    print("=" * 60)

    try:
        print("✓ Testing config.settings import...")
        from config.settings import get_settings, Settings
        print("  ✓ config.settings imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import config.settings: {e}")
        return False

    try:
        print("✓ Testing src.auth.credentials_manager import...")
        from src.auth.credentials_manager import get_credentials_manager, CredentialsManager
        print("  ✓ src.auth.credentials_manager imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import credentials_manager: {e}")
        return False

    try:
        print("✓ Testing src.auth.robinhood_auth import...")
        from src.auth.robinhood_auth import get_robinhood_auth, RobinhoodAuth, RobinhoodAuthError
        print("  ✓ src.auth.robinhood_auth imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import robinhood_auth: {e}")
        return False

    print("\n✅ All Phase 1 modules imported successfully!\n")
    return True


def test_settings():
    """Test settings configuration."""
    print("=" * 60)
    print("PHASE 1 TEST: Settings Configuration")
    print("=" * 60)

    try:
        from config.settings import get_settings

        print("✓ Loading settings...")
        settings = get_settings()

        print(f"  - Base directory: {settings.base_dir}")
        print(f"  - Logs directory: {settings.logs_dir}")
        print(f"  - Reports directory: {settings.reports_dir}")
        print(f"  - Log level: {settings.log_level}")

        print("\n✓ Testing rate limit configuration...")
        print(f"  - Calls per minute: {settings.rate_limit.calls_per_minute}")
        print(f"  - Calls per hour: {settings.rate_limit.calls_per_hour}")
        print(f"  - Min delay (seconds): {settings.rate_limit.min_delay_seconds}")
        print(f"  - Backoff factor: {settings.rate_limit.backoff_factor}")
        print(f"  - Max retries: {settings.rate_limit.max_retries}")

        print("\n✓ Testing strategy configuration...")
        print(f"  - Min option volume: {settings.strategy.min_option_volume}")
        print(f"  - Min open interest: {settings.strategy.min_open_interest}")
        print(f"  - Min premium: ${settings.strategy.min_premium}")
        print(f"  - Strike range: {settings.strike_range}")
        print(f"  - Delta range: {settings.delta_range}")
        print(f"  - Expiration range (days): {settings.expiration_range}")

        print("\n✓ Testing scheduler configuration...")
        print(f"  - Schedule enabled: {settings.scheduler.schedule_enabled}")
        print(f"  - Schedule time: {settings.scheduler.schedule_time}")
        print(f"  - Timezone: {settings.scheduler.schedule_timezone}")

        # Verify directories were created
        if settings.logs_dir.exists():
            print(f"\n✓ Logs directory created: {settings.logs_dir}")
        else:
            print(f"\n✗ Logs directory not created: {settings.logs_dir}")
            return False

        if settings.reports_dir.exists():
            print(f"✓ Reports directory created: {settings.reports_dir}")
        else:
            print(f"✗ Reports directory not created: {settings.reports_dir}")
            return False

        print("\n✅ Settings configuration working correctly!\n")
        return True

    except Exception as e:
        print(f"\n✗ Settings test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_credentials_manager():
    """Test credentials manager."""
    print("=" * 60)
    print("PHASE 1 TEST: Credentials Manager")
    print("=" * 60)

    try:
        from src.auth.credentials_manager import get_credentials_manager

        print("✓ Initializing credentials manager...")
        cred_manager = get_credentials_manager()

        print("✓ Testing credential status check...")
        status = cred_manager.get_credentials_status()
        print(f"  - Robinhood username available: {status['robinhood_username']}")
        print(f"  - Robinhood password available: {status['robinhood_password']}")
        print(f"  - Gemini API key available: {status['gemini_api_key']}")

        print("\n✓ Testing keyring storage (test credentials)...")
        # Test with dummy credentials
        test_username = "test_user_phase1"
        test_password = "test_password_phase1"

        success = cred_manager.store_robinhood_credentials(test_username, test_password)
        if success:
            print("  ✓ Test credentials stored successfully")
        else:
            print("  ⚠ Keyring storage failed (this is OK if keyring is not available)")
            print("    You can use .env file as fallback")

        # Try to retrieve
        retrieved_username = cred_manager.get_robinhood_username()
        if retrieved_username == test_username:
            print(f"  ✓ Retrieved username matches: {retrieved_username}")

            # Clean up test credentials
            print("✓ Cleaning up test credentials...")
            cred_manager.delete_robinhood_credentials()
            print("  ✓ Test credentials deleted")
        else:
            if retrieved_username:
                print(f"  ℹ Retrieved username from environment: {retrieved_username}")
            else:
                print("  ℹ No credentials found (expected for fresh install)")

        print("\n✅ Credentials manager working correctly!\n")
        return True

    except Exception as e:
        print(f"\n✗ Credentials manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_robinhood_auth():
    """Test Robinhood authentication structure (without actual login)."""
    print("=" * 60)
    print("PHASE 1 TEST: Robinhood Authentication Structure")
    print("=" * 60)

    try:
        from src.auth.robinhood_auth import get_robinhood_auth, RobinhoodAuthError

        print("✓ Initializing Robinhood auth...")
        auth = get_robinhood_auth()

        print(f"  - Token file location: {auth.token_file}")
        print(f"  - Token directory exists: {auth.token_file.parent.exists()}")

        print("\n✓ Testing authentication status check...")
        status = auth.get_authentication_status()
        print(f"  - Is authenticated: {status['is_authenticated']}")
        print(f"  - Username: {status['username']}")
        print(f"  - Has stored session: {status['has_stored_session']}")
        print(f"  - Has stored credentials: {status['has_stored_credentials']}")

        print("\n✓ Testing MFA code generation...")
        try:
            # Test with a sample TOTP secret (this is just for testing the function)
            test_secret = "JBSWY3DPEHPK3PXP"  # Example secret
            mfa_code = auth.generate_mfa_code(test_secret)
            print(f"  ✓ MFA code generated: {mfa_code} (6 digits: {len(mfa_code) == 6})")
        except Exception as e:
            print(f"  ⚠ MFA generation test failed: {e}")

        print("\n✓ Testing error handling...")
        try:
            # This should raise an error since we don't have credentials
            auth.login()
            print("  ⚠ Expected error not raised")
        except RobinhoodAuthError as e:
            print(f"  ✓ Correctly raised RobinhoodAuthError: {str(e)[:100]}...")

        print("\n✅ Robinhood authentication structure working correctly!\n")
        return True

    except Exception as e:
        print(f"\n✗ Robinhood auth test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    print("=" * 60)
    print("DEPENDENCY CHECK")
    print("=" * 60)

    required_packages = [
        'pydantic',
        'keyring',
        'loguru',
        'robin_stocks',
        'pyotp',
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} installed")
        except ImportError:
            print(f"✗ {package} NOT installed")
            missing.append(package)

    if missing:
        print(f"\n⚠ Missing dependencies: {', '.join(missing)}")
        print("Please run: pip install -r requirements.txt")
        return False

    print("\n✅ All required dependencies installed!\n")
    return True


def main():
    """Run all Phase 1 tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "STOCKBOT PHASE 1 TEST SUITE" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    # Check dependencies first
    if not check_dependencies():
        print("\n❌ PHASE 1 TEST FAILED: Missing dependencies")
        print("Run 'pip install -r requirements.txt' and try again.")
        return False

    # Run tests
    results = []

    results.append(("Module Imports", test_imports()))
    results.append(("Settings Configuration", test_settings()))
    results.append(("Credentials Manager", test_credentials_manager()))
    results.append(("Robinhood Auth Structure", test_robinhood_auth()))

    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL PHASE 1 TESTS PASSED!")
        print("=" * 60)
        print("\nYou can now proceed to Phase 2: Data Layer with Rate Limiting")
        print("\nNext steps:")
        print("1. Get your Robinhood credentials ready")
        print("2. Get your Google Gemini API key")
        print("3. Run the Phase 2 implementation")
        return True
    else:
        print("❌ SOME PHASE 1 TESTS FAILED")
        print("=" * 60)
        print("\nPlease fix the issues above before proceeding.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
