"""
Robinhood API client for fetching stock and options data
"""

import robin_stocks.robinhood as rh
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta


class RobinhoodClient:
    """Client for interacting with Robinhood API"""

    def __init__(self, username: str, password: str, mfa_code: Optional[str] = None):
        """
        Initialize Robinhood client

        Args:
            username: Robinhood account email
            password: Robinhood account password
            mfa_code: Optional MFA code if 2FA is enabled
        """
        self.username = username
        self.password = password
        self.mfa_code = mfa_code
        self.logged_in = False

    def login(self) -> bool:
        """
        Login to Robinhood

        Returns:
            True if login successful, False otherwise
        """
        try:
            if self.mfa_code:
                rh.login(self.username, self.password, mfa_code=self.mfa_code)
            else:
                rh.login(self.username, self.password)
            self.logged_in = True
            print("✓ Successfully logged into Robinhood")
            return True
        except Exception as e:
            print(f"✗ Failed to login to Robinhood: {e}")
            return False

    def logout(self):
        """Logout from Robinhood"""
        rh.logout()
        self.logged_in = False

    def get_stock_positions(self) -> List[Dict]:
        """
        Get all current stock positions

        Returns:
            List of dictionaries containing stock position data
        """
        if not self.logged_in:
            raise Exception("Not logged in to Robinhood")

        positions = []
        my_stocks = rh.build_holdings()

        for symbol, data in my_stocks.items():
            quantity = float(data['quantity'])
            # Only include positions with at least 100 shares (1 covered call contract)
            if quantity >= 100:
                positions.append({
                    'symbol': symbol,
                    'quantity': quantity,
                    'average_buy_price': float(data['average_buy_price']),
                    'current_price': float(data['price']),
                    'equity': float(data['equity']),
                    'percent_change': float(data['percent_change']),
                    'contracts_available': int(quantity // 100)
                })

        return positions

    def get_option_chains(self, symbol: str) -> Dict:
        """
        Get options chain data for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary containing options chain data
        """
        if not self.logged_in:
            raise Exception("Not logged in to Robinhood")

        try:
            # Get option chain expiration dates
            option_data = rh.options.find_options_by_expiration(
                symbol,
                expirationDate=None,
                optionType='call'
            )

            return option_data
        except Exception as e:
            print(f"Error fetching option chains for {symbol}: {e}")
            return {}

    def get_available_call_options(
        self,
        symbol: str,
        current_price: float,
        days_out: int = 45
    ) -> List[Dict]:
        """
        Get available call options for covered call strategy

        Args:
            symbol: Stock symbol
            current_price: Current stock price
            days_out: Maximum days until expiration (default 45)

        Returns:
            List of suitable call options
        """
        if not self.logged_in:
            raise Exception("Not logged in to Robinhood")

        options = []

        try:
            # Get expiration dates within the next X days
            target_date = datetime.now() + timedelta(days=days_out)

            # Get all expiration dates
            exp_dates = rh.options.get_chains(symbol)['expiration_dates']

            # Filter to dates within our range
            valid_dates = [
                date for date in exp_dates
                if datetime.strptime(date, '%Y-%m-%d') <= target_date
            ]

            for exp_date in valid_dates:
                # Get call options for this expiration
                calls = rh.options.find_options_by_expiration(
                    symbol,
                    expirationDate=exp_date,
                    optionType='call'
                )

                for option in calls:
                    strike_price = float(option['strike_price'])

                    # Only consider OTM or ATM options (strike >= current price)
                    if strike_price >= current_price * 0.95:  # 5% ITM to OTM range
                        market_data = rh.options.get_option_market_data_by_id(option['id'])

                        if market_data and len(market_data) > 0:
                            md = market_data[0]
                            bid = float(md.get('bid_price', 0) or 0)
                            ask = float(md.get('ask_price', 0) or 0)

                            if bid > 0:  # Only include options with actual bids
                                mid_price = (bid + ask) / 2
                                premium = mid_price * 100  # Per contract

                                days_to_exp = (
                                    datetime.strptime(exp_date, '%Y-%m-%d') -
                                    datetime.now()
                                ).days

                                annualized_return = (
                                    (premium / (current_price * 100)) * (365 / days_to_exp) * 100
                                    if days_to_exp > 0 else 0
                                )

                                options.append({
                                    'symbol': symbol,
                                    'strike_price': strike_price,
                                    'expiration_date': exp_date,
                                    'days_to_expiration': days_to_exp,
                                    'bid': bid,
                                    'ask': ask,
                                    'mid_price': mid_price,
                                    'premium_per_contract': premium,
                                    'volume': int(md.get('volume', 0) or 0),
                                    'open_interest': int(md.get('open_interest', 0) or 0),
                                    'implied_volatility': float(md.get('implied_volatility', 0) or 0),
                                    'delta': float(md.get('delta', 0) or 0),
                                    'annualized_return_pct': annualized_return,
                                    'moneyness': ((strike_price - current_price) / current_price) * 100
                                })

        except Exception as e:
            print(f"Error fetching call options for {symbol}: {e}")

        # Sort by annualized return
        options.sort(key=lambda x: x['annualized_return_pct'], reverse=True)

        return options

    def get_account_info(self) -> Dict:
        """
        Get account information

        Returns:
            Dictionary containing account data
        """
        if not self.logged_in:
            raise Exception("Not logged in to Robinhood")

        profile = rh.profiles.load_account_profile()
        portfolio = rh.profiles.load_portfolio_profile()

        return {
            'equity': float(portfolio.get('equity', 0)),
            'market_value': float(portfolio.get('market_value', 0)),
            'buying_power': float(profile.get('buying_power', 0)),
        }
