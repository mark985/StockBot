"""
Robinhood API endpoint definitions.
All URLs in one place for easy maintenance.
"""

# Base URLs
BASE_API = "https://api.robinhood.com"
BASE_NUMMUS = "https://nummus.robinhood.com"
BASE_IDENTI = "https://identi.robinhood.com"


class Endpoints:
    """Robinhood API endpoints."""

    # Authentication
    LOGIN = f"{BASE_API}/oauth2/token/"
    CHALLENGE = f"{BASE_API}/challenge/{{challenge_id}}/respond/"

    # Pathfinder (Verification)
    PATHFINDER_USER_MACHINE = f"{BASE_API}/pathfinder/user_machine/"
    PATHFINDER_INQUIRIES = f"{BASE_API}/pathfinder/inquiries/{{machine_id}}/user_view/"
    PUSH_PROMPT_STATUS = f"{BASE_API}/push/{{challenge_id}}/get_prompts_status/"

    # Identity Workflow (identi.robinhood.com - for verification preferences)
    IDENTITY_WORKFLOW = f"{BASE_IDENTI}/idl/v1/workflow/{{workflow_id}}/"

    # Account & Profile
    ACCOUNTS = f"{BASE_API}/accounts/"
    USER_PROFILE = f"{BASE_API}/user/"
    BASIC_INFO = f"{BASE_API}/user/basic_info/"
    INVESTMENT_PROFILE = f"{BASE_API}/user/investment_profile/"
    PORTFOLIO = f"{BASE_API}/portfolios/"
    POSITIONS = f"{BASE_API}/positions/"

    # Market Data
    QUOTES = f"{BASE_API}/quotes/"
    INSTRUMENTS = f"{BASE_API}/instruments/"
    FUNDAMENTALS = f"{BASE_API}/fundamentals/"
    MARKET_DATA_QUOTES = f"{BASE_API}/marketdata/quotes/{{instrument_id}}/"

    # Options
    OPTIONS_CHAINS = f"{BASE_API}/options/chains/"
    OPTIONS_INSTRUMENTS = f"{BASE_API}/options/instruments/"
    OPTIONS_POSITIONS = f"{BASE_API}/options/positions/"
    OPTIONS_MARKET_DATA = f"{BASE_API}/marketdata/options/"
    OPTIONS_ORDERS = f"{BASE_API}/options/orders/"

    # Orders
    ORDERS = f"{BASE_API}/orders/"

    # Crypto
    CRYPTO_ACCOUNT = f"{BASE_NUMMUS}/accounts/"
    CRYPTO_HOLDINGS = f"{BASE_NUMMUS}/holdings/"
    CRYPTO_ORDERS = f"{BASE_NUMMUS}/orders/"


# OAuth2 Client ID (extracted from Robinhood mobile app)
OAUTH_CLIENT_ID = "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS"
