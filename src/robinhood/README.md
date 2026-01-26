# Custom Robinhood Client

A clean, production-quality Python client for the Robinhood API built from scratch for StockBot.

## Why Custom Client?

Built to replace `robin_stocks` library due to:
- Frequent authentication bugs (Dec 2024 API changes)
- Poor error handling and debugging
- Unofficial API with no documentation
- Need for full control and transparency

## Features

- **OAuth2 Authentication**: Clean implementation with device token support
- **Session Persistence**: Save/load sessions to avoid repeated logins
- **Verification Handling**: Detects when SMS/email/app verification required
- **Complete API Coverage**: Account, positions, quotes, options chains
- **Detailed Logging**: Full request/response logging for debugging
- **Error Handling**: Custom exceptions with detailed error messages
- **Type Safety**: Type hints throughout for better IDE support

## Installation

No additional dependencies needed beyond StockBot requirements:
- `requests` - HTTP client
- `loguru` - Logging

## Quick Start

```python
from src.robinhood.client import RobinhoodClient
from src.robinhood.exceptions import VerificationRequired, AuthenticationError

# Create client
client = RobinhoodClient()

# Try to load saved session
if client.load_session():
    print("Logged in from saved session")
else:
    # Login with credentials
    try:
        client.login("your_email@example.com", "your_password")
        print("Login successful!")
    except VerificationRequired as e:
        print(f"Verification needed: {e.verification_type}")
        print(f"Check your {e.verification_type} for code")
    except AuthenticationError as e:
        print(f"Login failed: {e}")

# Get account info
account = client.get_account()
print(f"Buying Power: ${account['buying_power']}")

# Get stock positions
positions = client.get_positions()
for pos in positions:
    quantity = pos['quantity']
    print(f"Holding {quantity} shares")

# Get stock quote
quote = client.get_quote("AAPL")
print(f"AAPL: ${quote['last_trade_price']}")
```

## API Reference

### Authentication

#### `login(username, password, mfa_code=None)`
Authenticate with Robinhood using email and password.

**Returns:** Authentication response with tokens
**Raises:**
- `InvalidCredentialsError` - Wrong email/password
- `VerificationRequired` - SMS/email/app verification needed
- `AuthenticationError` - Other auth failures

```python
response = client.login("email@example.com", "password")
```

#### `load_session()`
Load saved session from `~/.tokens/robinhood_custom.pickle`.

**Returns:** `bool` - True if session loaded successfully

```python
if client.load_session():
    print("Logged in from saved session")
```

#### `logout()`
Clear session and delete saved tokens.

```python
client.logout()
```

### Account & Portfolio

#### `get_account()`
Get account information including buying power, cash, account number.

**Returns:** `dict` - Account details

```python
account = client.get_account()
print(f"Buying Power: ${account['buying_power']}")
print(f"Account Number: {account['account_number']}")
```

#### `get_positions(nonzero=True)`
Get current stock positions.

**Args:**
- `nonzero` (bool) - Only return positions with quantity > 0

**Returns:** `list` - List of position dictionaries

```python
positions = client.get_positions()
for pos in positions:
    instrument_url = pos['instrument']
    quantity = float(pos['quantity'])
    avg_price = float(pos['average_buy_price'])
```

#### `get_options_positions(nonzero=True)`
Get current options positions.

**Returns:** `list` - List of options position dictionaries

```python
options = client.get_options_positions()
for opt in options:
    quantity = opt['quantity']
    option_url = opt['option']
```

### Stock Data

#### `get_instrument_by_symbol(symbol)`
Get instrument details for a ticker symbol.

**Args:**
- `symbol` (str) - Stock ticker (e.g., 'AAPL')

**Returns:** `dict` - Instrument details including ID, symbol, name

```python
instrument = client.get_instrument_by_symbol("AAPL")
print(f"Name: {instrument['simple_name']}")
print(f"Tradeable: {instrument['tradeable']}")
```

#### `get_instrument_by_url(url)`
Get instrument details from instrument URL.

**Args:**
- `url` (str) - Full instrument URL

**Returns:** `dict` - Instrument details

```python
instrument = client.get_instrument_by_url(position['instrument'])
symbol = instrument['symbol']
```

#### `get_quote(symbol)`
Get current stock quote.

**Args:**
- `symbol` (str) - Stock ticker

**Returns:** `dict` - Quote with prices, volume, etc.

```python
quote = client.get_quote("AAPL")
print(f"Last Price: ${quote['last_trade_price']}")
print(f"Bid: ${quote['bid_price']}")
print(f"Ask: ${quote['ask_price']}")
```

#### `get_quotes(symbols)`
Get quotes for multiple symbols.

**Args:**
- `symbols` (list) - List of stock tickers

**Returns:** `list` - List of quote dictionaries

```python
quotes = client.get_quotes(["AAPL", "MSFT", "GOOGL"])
for quote in quotes:
    print(f"{quote['symbol']}: ${quote['last_trade_price']}")
```

### Options Data

#### `get_options_chains(symbol)`
Get options chains for a stock.

**Args:**
- `symbol` (str) - Stock ticker

**Returns:** `dict` - Options chain metadata including chain ID

```python
chain = client.get_options_chains("AAPL")
chain_id = chain['id']
print(f"Chain ID: {chain_id}")
```

#### `get_options_instruments(chain_id, expiration_dates=None, option_type='call', state='active')`
Get options instruments for a chain.

**Args:**
- `chain_id` (str) - Options chain ID
- `expiration_dates` (list) - List of dates (YYYY-MM-DD format)
- `option_type` (str) - 'call' or 'put'
- `state` (str) - 'active' or 'inactive'

**Returns:** `list` - List of options instruments

```python
# Get all active calls
calls = client.get_options_instruments(
    chain_id="12345",
    option_type="call"
)

# Get calls for specific expirations
calls = client.get_options_instruments(
    chain_id="12345",
    expiration_dates=["2026-02-21", "2026-03-21"],
    option_type="call"
)
```

#### `get_options_market_data(option_ids)`
Get market data for options.

**Args:**
- `option_ids` (list) - List of options instrument IDs

**Returns:** `list` - Market data with prices, Greeks, IV

```python
# Get market data for options
market_data = client.get_options_market_data([
    "12345-abc",
    "12345-def"
])

for data in market_data:
    print(f"Strike: ${data['strike_price']}")
    print(f"Premium: ${data['adjusted_mark_price']}")
    print(f"Delta: {data['delta']}")
    print(f"IV: {data['implied_volatility']}")
```

### Low-Level Methods

#### `get(url, params=None, authenticated=True)`
Make authenticated GET request.

```python
response = client.get(
    "https://api.robinhood.com/positions/",
    authenticated=True
)
```

#### `post(url, data=None, json_data=None, authenticated=True)`
Make authenticated POST request.

```python
response = client.post(
    "https://api.robinhood.com/some/endpoint/",
    json_data={"key": "value"}
)
```

## Error Handling

The client uses a custom exception hierarchy:

```
RobinhoodError (base)
├── AuthenticationError
│   ├── InvalidCredentialsError
│   └── VerificationRequired
└── APIError
```

**Example:**

```python
from src.robinhood.exceptions import (
    InvalidCredentialsError,
    VerificationRequired,
    APIError
)

try:
    client.login(username, password)
except InvalidCredentialsError:
    print("Wrong email or password")
except VerificationRequired as e:
    print(f"Verification needed: {e.verification_type}")
    print(f"Workflow ID: {e.workflow_id}")
except AuthenticationError as e:
    print(f"Auth failed: {e}")
    if e.response_data:
        print(f"Details: {e.response_data}")
```

## Logging

The client uses `loguru` for detailed logging. To see debug logs:

```python
from loguru import logger
import sys

logger.remove()
logger.add(sys.stderr, level="DEBUG")
```

This will show all HTTP requests, responses, and authentication flow.

## Session Management

Sessions are saved to `~/.tokens/robinhood_custom.pickle` and include:
- Access token (expires in 24 hours)
- Refresh token
- Device token

The session file is created automatically on successful login.

## Testing

Run the test script:

```bash
python3 test_clean.py
```

This will test:
- Authentication with session restore
- Account information
- Stock positions
- Stock quotes

For integration testing:

```bash
python3 test_integration.py
```

This demonstrates integration with the StockBot auth module.

## Security Notes

**WARNING:** This uses Robinhood's unofficial API which:
- Violates Robinhood's Terms of Service
- May result in account restrictions or bans
- Has no official documentation or support
- Can change without notice

**Best Practices:**
- Store credentials securely (use keyring, not .env files)
- Never commit tokens or session files to git
- Use rate limiting to avoid API blocks
- Monitor for API changes and errors

## Implementation Details

### OAuth2 Flow

1. Generate cryptographically secure device token (UUID format)
2. POST to `/oauth2/token/` with credentials + device_token
3. Robinhood returns:
   - Success: `access_token` + `refresh_token`
   - Verification needed: `verification_workflow` object
4. Save tokens to pickle file for reuse

### Device Token Format

```
a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

Generated using `secrets.randbelow(256)` for cryptographic security.

### Client ID

Hardcoded client ID extracted from Robinhood mobile app:
```
c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS
```

This is the same ID used by `robin_stocks` and other unofficial clients.

## Future Enhancements

Potential additions:
- [ ] Refresh token rotation
- [ ] Verification workflow completion (SMS/email code submission)
- [ ] Options order placement
- [ ] Stock order placement
- [ ] Crypto support
- [ ] Rate limiting built-in
- [ ] Async support with `httpx`

## License

Part of StockBot project. For educational purposes only.

## Disclaimer

**THIS SOFTWARE IS FOR EDUCATIONAL PURPOSES ONLY.**

Using unofficial APIs violates Robinhood's Terms of Service and may result in account restrictions or permanent bans. The authors are not responsible for any account issues, financial losses, or other damages resulting from use of this software.

Always verify data accuracy and make your own trading decisions. This is NOT financial advice.
