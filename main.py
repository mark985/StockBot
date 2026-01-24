#!/usr/bin/env python3
"""
StockBot - Robinhood Covered Call Advisor
Main entry point
"""

import argparse
import sys
from src.config import Config
from src.bot import StockBot


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="StockBot - AI-powered covered call advisor for Robinhood",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run full analysis
  python main.py --days 30          # Only look at options expiring within 30 days
  python main.py --quick AAPL       # Quick analysis for AAPL only
  python main.py --no-details       # Skip detailed options tables
        """
    )

    parser.add_argument(
        "--days",
        type=int,
        default=45,
        help="Maximum days until option expiration (default: 45)"
    )

    parser.add_argument(
        "--quick",
        type=str,
        metavar="SYMBOL",
        help="Quick analysis for a specific symbol"
    )

    parser.add_argument(
        "--no-details",
        action="store_true",
        help="Don't show detailed options tables"
    )

    parser.add_argument(
        "--env",
        type=str,
        default=".env",
        help="Path to .env file (default: .env)"
    )

    args = parser.parse_args()

    try:
        # Load configuration
        config = Config(env_file=args.env)

        # Initialize bot
        bot = StockBot(config)

        # Run analysis
        if args.quick:
            bot.quick_check(args.quick)
        else:
            bot.run(
                days_out=args.days,
                show_detailed=not args.no_details
            )

    except ValueError as e:
        print(f"\n✗ Configuration Error:\n{e}\n", file=sys.stderr)
        print("Please check your .env file. See .env.example for reference.")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}\n", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
