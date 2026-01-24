# StockBot

A Python-based stock and options trading analysis bot powered by Google Gemini LLM. StockBot fetches real-time data from Robinhood, analyzes covered call opportunities, and provides intelligent buy/sell recommendations through both CLI and web interfaces.

## Features

- **Real-time Data Fetching**: Connects to Robinhood API to fetch portfolio, stock prices, and options chains
- **LLM-Powered Analysis**: Uses Google Gemini to analyze covered call opportunities and generate actionable recommendations
- **Covered Call Strategy**: Identifies optimal covered call positions with detailed metrics (ROI, annualized return, assignment probability)
- **Dual Interface**: Both command-line (CLI) and web dashboard (Streamlit) interfaces
- **Scheduled Automation**: Automated daily/weekly portfolio scans with email notifications
- **Secure Credentials**: Uses OS keyring for secure credential storage
- **Aggressive Rate Limiting**: Built-in protection against Robinhood API blocks
- **Recommendations Only**: Provides analysis and suggestions without executing trades automatically

## Disclaimer

**IMPORTANT**: This is educational software for analysis purposes only. It does NOT execute trades automatically. All recommendations are for informational purposes only and are not financial advice. Users are solely responsible for their own trading decisions. Use of Robinhood's unofficial API may result in account restrictions. Past performance does not guarantee future results.

## Tech Stack

- **Language**: Python 3.9+
- **LLM**: Google Gemini (google-generativeai SDK)
- **Data Source**: Robinhood (robin_stocks library - unofficial API)
- **CLI**: Click + Rich
- **Web**: Streamlit
- **Scheduler**: APScheduler
- **Security**: keyring + python-dotenv

## Installation

### Prerequisites

- Python 3.9 or higher
- Robinhood account
- Google Gemini API key ([Get it here](https://makersuite.google.com/app/apikey))

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd StockBot
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment (optional - keyring is preferred):
```bash
cp .env.example .env
# Edit .env with your credentials
```

## Quick Start

### 1. Login to Robinhood

```bash
python -m src.cli.main login
```

You'll be prompted for your Robinhood username, password, and 2FA code if enabled.

### 2. View Portfolio

```bash
python -m src.cli.main portfolio
```

### 3. Analyze Covered Call Opportunities

```bash
# Analyze specific stock
python -m src.cli.main analyze AAPL

# Scan entire portfolio
python -m src.cli.main scan
```

### 4. Launch Web Dashboard

```bash
python -m src.cli.main web
```

## Project Structure

```
StockBot/
├── config/                     # Configuration management
│   └── settings.py            # Pydantic settings with env support
├── src/
│   ├── auth/                  # Authentication & credentials
│   │   ├── credentials_manager.py
│   │   └── robinhood_auth.py
│   ├── data/                  # Data fetching layer
│   │   ├── robinhood_client.py
│   │   ├── rate_limiter.py
│   │   ├── stock_fetcher.py
│   │   ├── options_fetcher.py
│   │   └── portfolio_fetcher.py
│   ├── analysis/              # Analysis & LLM integration
│   │   ├── gemini_client.py
│   │   ├── covered_call_analyzer.py
│   │   ├── options_screener.py
│   │   └── prompt_templates.py
│   ├── strategies/            # Trading strategies
│   │   ├── base_strategy.py
│   │   ├── covered_call.py
│   │   └── strategy_registry.py
│   ├── scheduler/             # Automated scheduling
│   │   ├── scheduler.py
│   │   ├── tasks.py
│   │   └── notifications.py
│   ├── cli/                   # Command-line interface
│   │   ├── main.py
│   │   └── commands.py
│   └── web/                   # Web dashboard
│       ├── app.py
│       └── components/
├── tests/                     # Unit & integration tests
├── logs/                      # Application logs
└── reports/                   # Generated analysis reports
```

## Configuration

### Credential Storage

StockBot uses **keyring** for secure credential storage by default:

```python
from src.auth.credentials_manager import get_credentials_manager

cred_manager = get_credentials_manager()

# Store credentials
cred_manager.store_robinhood_credentials("username", "password")
cred_manager.store_gemini_api_key("your-api-key")

# Retrieve credentials
username = cred_manager.get_robinhood_username()
api_key = cred_manager.get_gemini_api_key()
```

### Strategy Parameters

Edit [config/settings.py](config/settings.py) or use environment variables:

```python
# Screening criteria
MIN_OPTION_VOLUME=100
MIN_OPEN_INTEREST=50
MIN_PREMIUM=0.50
MIN_DAYS_TO_EXPIRATION=7
MAX_DAYS_TO_EXPIRATION=45

# Rate limiting (CRITICAL for avoiding API blocks)
CALLS_PER_MINUTE=20
CALLS_PER_HOUR=500
MIN_DELAY_SECONDS=2
```

## CLI Commands

```bash
# Authentication
stockbot login              # Login to Robinhood
stockbot logout             # Logout

# Portfolio
stockbot portfolio          # View current holdings

# Analysis
stockbot analyze AAPL       # Analyze specific stock for covered calls
stockbot scan               # Scan entire portfolio

# Scheduler
stockbot schedule start     # Start automated scans
stockbot schedule stop      # Stop automated scans
stockbot schedule status    # View schedule status

# Configuration
stockbot config             # Manage settings

# Web Dashboard
stockbot web                # Launch Streamlit dashboard
```

## Covered Call Strategy

### How It Works

1. **Prerequisites Check**: Identifies holdings with 100+ shares
2. **Options Screening**: Filters options by:
   - Volume & Open Interest (liquidity)
   - Strike price (5-15% out-of-the-money)
   - Delta range (0.15-0.35 for ~15-35% assignment probability)
   - Expiration (7-45 days)
3. **Metrics Calculation**:
   - Premium income
   - ROI (Return on Investment)
   - Annualized return
   - Assignment probability
   - Breakeven price
4. **LLM Analysis**: Gemini analyzes opportunities and provides ranked recommendations
5. **Recommendations**: Presents top opportunities with reasoning and risk assessment

### Example Output

```
Top Covered Call Opportunities:
┏━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Symbol ┃ Strike ┃ Premium ┃ Ann ROI ┃ Expiration ┃ Rating  ┃
┡━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ AAPL   │ 180.00 │ $2.50   │ 12.5%   │ 2024-03-15 │ 8/10    │
│ MSFT   │ 385.00 │ $4.20   │ 11.2%   │ 2024-03-22 │ 7/10    │
└────────┴────────┴─────────┴─────────┴────────────┴─────────┘
```

## Development Status

### Completed (Phase 1)
- ✅ Project structure
- ✅ Configuration management (pydantic + env)
- ✅ Secure credentials storage (keyring)
- ✅ Robinhood authentication with 2FA support

### In Progress
- 🔨 Data layer (rate limiter, API clients)
- 🔨 Gemini LLM integration
- 🔨 Covered call strategy implementation

### Planned
- 📋 CLI interface
- 📋 Web dashboard
- 📋 Scheduler & automation
- 📋 Email notifications
- 📋 Comprehensive testing

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_auth/test_credentials_manager.py
```

## Rate Limiting

StockBot implements aggressive rate limiting to prevent Robinhood API blocks:

- Minimum 2-second delay between API calls
- Maximum 20 calls per minute
- Maximum 500 calls per hour
- Exponential backoff on errors
- Circuit breaker on repeated failures

**Important**: Robinhood uses an unofficial API. Excessive usage may result in account restrictions.

## Security

- Credentials stored in OS keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- Sensitive data never logged
- Session tokens encrypted at rest
- Environment variable support for CI/CD
- Input validation on all user inputs

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure code passes linting (black, flake8, mypy)
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
- Open an issue on GitHub
- Check the [documentation](docs/)
- Review the [implementation plan](/Users/huiyuma/.claude/plans/playful-swinging-graham.md)

## Roadmap

- [x] Phase 1: Foundation & Authentication
- [ ] Phase 2: Data Layer with Rate Limiting
- [ ] Phase 3: Basic CLI
- [ ] Phase 4: Gemini Integration
- [ ] Phase 5: Covered Call Strategy
- [ ] Phase 6: Enhanced CLI
- [ ] Phase 7: Web Dashboard
- [ ] Phase 7.5: Scheduler & Automation
- [ ] Phase 8: Production Readiness

Future enhancements:
- Additional strategies (cash-secured puts, iron condors, spreads)
- Backtesting framework
- Portfolio optimization
- Multi-broker support
- Mobile notifications
