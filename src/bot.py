"""
Main StockBot orchestration logic
"""

from typing import Dict, List, Optional
from tabulate import tabulate

from .robinhood_client import RobinhoodClient
from .llm_advisor import CoveredCallAdvisor
from .config import Config


class StockBot:
    """Main bot orchestrator for covered call recommendations"""

    def __init__(self, config: Config):
        """
        Initialize StockBot

        Args:
            config: Configuration object
        """
        self.config = config
        self.rh_client = RobinhoodClient(
            username=config.robinhood_username,
            password=config.robinhood_password,
            mfa_code=config.robinhood_mfa_code
        )
        self.advisor = CoveredCallAdvisor(
            api_key=config.anthropic_api_key,
            model=config.claude_model
        )

    def run(self, days_out: int = 45, show_detailed: bool = True):
        """
        Run the bot analysis

        Args:
            days_out: Maximum days until option expiration
            show_detailed: Whether to show detailed analysis
        """
        print("\n" + "="*80)
        print(" StockBot - Covered Call Advisor".center(80))
        print("="*80 + "\n")

        # Step 1: Login to Robinhood
        print("Step 1: Logging into Robinhood...")
        if not self.rh_client.login():
            print("\n✗ Failed to login. Please check your credentials.")
            return

        try:
            # Step 2: Get account info
            print("\nStep 2: Fetching account information...")
            account_info = self.rh_client.get_account_info()
            self._display_account_info(account_info)

            # Step 3: Get stock positions
            print("\nStep 3: Fetching stock positions (100+ shares)...")
            positions = self.rh_client.get_stock_positions()

            if not positions:
                print("\n✗ No positions found with 100+ shares.")
                print("  You need at least 100 shares of a stock to sell covered calls.")
                return

            self._display_positions(positions)

            # Step 4: Get options data
            print(f"\nStep 4: Fetching call options (up to {days_out} days out)...")
            options_data = {}

            for pos in positions:
                symbol = pos['symbol']
                print(f"  Analyzing {symbol}...")

                options = self.rh_client.get_available_call_options(
                    symbol=symbol,
                    current_price=pos['current_price'],
                    days_out=days_out
                )

                # Filter by minimum premium
                options = [
                    opt for opt in options
                    if opt['premium_per_contract'] >= self.config.min_premium
                ]

                options_data[symbol] = options
                print(f"  Found {len(options)} suitable options for {symbol}")

            # Step 5: Get LLM analysis
            print("\nStep 5: Analyzing opportunities with Claude AI...")
            print(f"  Risk Tolerance: {self.config.risk_tolerance.upper()}")
            print(f"  Minimum Premium: ${self.config.min_premium}")

            analysis = self.advisor.analyze_covered_call_opportunities(
                positions=positions,
                options_data=options_data,
                risk_tolerance=self.config.risk_tolerance,
                min_premium=self.config.min_premium
            )

            # Step 6: Display recommendations
            print("\n" + "="*80)
            print(" AI RECOMMENDATIONS".center(80))
            print("="*80 + "\n")

            if analysis['success']:
                print(analysis['analysis'])
                print(f"\n(Analysis powered by {analysis['model_used']})")
            else:
                print(f"✗ Error getting analysis: {analysis['error']}")

            # Optional: Show detailed options table
            if show_detailed:
                self._display_detailed_options(options_data)

        finally:
            # Always logout
            print("\nLogging out of Robinhood...")
            self.rh_client.logout()
            print("✓ Done!\n")

    def _display_account_info(self, info: Dict):
        """Display account information"""
        print(f"\n  Account Equity: ${info['equity']:,.2f}")
        print(f"  Market Value: ${info['market_value']:,.2f}")
        print(f"  Buying Power: ${info['buying_power']:,.2f}")

    def _display_positions(self, positions: List[Dict]):
        """Display stock positions in a table"""
        table_data = []
        for pos in positions:
            table_data.append([
                pos['symbol'],
                f"{pos['quantity']:.0f}",
                f"{pos['contracts_available']}",
                f"${pos['average_buy_price']:.2f}",
                f"${pos['current_price']:.2f}",
                f"{pos['percent_change']:.2f}%",
                f"${pos['equity']:,.2f}"
            ])

        headers = ["Symbol", "Shares", "Contracts", "Avg Cost", "Current", "P/L %", "Equity"]
        print("\n" + tabulate(table_data, headers=headers, tablefmt="simple"))

    def _display_detailed_options(self, options_data: Dict[str, List[Dict]]):
        """Display detailed options data in tables"""
        print("\n" + "="*80)
        print(" DETAILED OPTIONS DATA".center(80))
        print("="*80 + "\n")

        for symbol, options in options_data.items():
            if not options:
                print(f"\n{symbol}: No suitable options found\n")
                continue

            print(f"\n{symbol} - Top Options:\n")

            table_data = []
            for opt in options[:10]:  # Show top 10
                table_data.append([
                    f"${opt['strike_price']:.2f}",
                    opt['expiration_date'],
                    opt['days_to_expiration'],
                    f"${opt['premium_per_contract']:.2f}",
                    f"{opt['annualized_return_pct']:.1f}%",
                    f"{opt['moneyness']:.1f}%",
                    f"{opt['delta']:.2f}",
                    opt['volume'],
                    opt['open_interest']
                ])

            headers = [
                "Strike", "Expiration", "DTE", "Premium",
                "Ann. Return", "Moneyness", "Delta", "Volume", "OI"
            ]

            print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def quick_check(self, symbol: str):
        """
        Quick check for a specific symbol

        Args:
            symbol: Stock symbol to analyze
        """
        print(f"\nQuick analysis for {symbol}...")

        if not self.rh_client.login():
            print("Failed to login")
            return

        try:
            positions = self.rh_client.get_stock_positions()
            position = next((p for p in positions if p['symbol'] == symbol.upper()), None)

            if not position:
                print(f"No position found for {symbol} with 100+ shares")
                return

            options = self.rh_client.get_available_call_options(
                symbol=symbol,
                current_price=position['current_price'],
                days_out=45
            )

            options = [
                opt for opt in options
                if opt['premium_per_contract'] >= self.config.min_premium
            ]

            analysis = self.advisor.quick_analysis(
                symbol=symbol,
                options=options,
                current_price=position['current_price']
            )

            print(f"\n{analysis}\n")

        finally:
            self.rh_client.logout()
