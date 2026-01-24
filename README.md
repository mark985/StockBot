# 🤖 StockBot - AI-Powered Covered Call Advisor

An intelligent bot that fetches your Robinhood stock positions and options data, then uses Claude AI to provide personalized covered call selling recommendations.

## 🎯 Features

- **Automatic Data Fetching**: Connects to your Robinhood account to retrieve:
  - Stock positions (filters for 100+ shares)
  - Available call options with real-time pricing
  - Options Greeks (Delta, IV, etc.)
  - Volume and Open Interest data

- **AI-Powered Analysis**: Uses Anthropic's Claude to analyze:
  - Risk/reward profiles based on your risk tolerance
  - Probability of assignment
  - Premium income vs. upside sacrifice
  - Optimal strike prices and expiration dates
  - Liquidity considerations

- **Customizable Strategy**: Configure:
  - Risk tolerance (conservative/moderate/aggressive)
  - Minimum premium thresholds
  - Maximum days to expiration
  - And more...

- **Clear Recommendations**: Get actionable insights:
  - Ranked recommendations for each position
  - Expected premium income
  - Break-even analysis
  - Pros, cons, and risk warnings

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/mark985/StockBot.git
cd StockBot

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Robinhood Credentials
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_password
# ROBINHOOD_MFA_CODE=123456  # If you have 2FA enabled

# Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-xxx

# Bot Configuration
CLAUDE_MODEL=claude-3-5-sonnet-20241022
RISK_TOLERANCE=moderate  # conservative, moderate, or aggressive
MIN_PREMIUM=50  # Minimum premium in dollars
```

**Getting API Keys:**
- **Anthropic API**: Sign up at [console.anthropic.com](https://console.anthropic.com/)
- **Robinhood**: Use your existing account credentials

### 3. Run the Bot

```bash
# Full analysis of all positions
python main.py

# Only look at options expiring within 30 days
python main.py --days 30

# Quick analysis for a specific stock
python main.py --quick AAPL

# Skip detailed options tables
python main.py --no-details
```

## 📊 Example Output

```
================================================================================
                        StockBot - Covered Call Advisor
================================================================================

Step 1: Logging into Robinhood...
✓ Successfully logged into Robinhood

Step 2: Fetching account information...
  Account Equity: $125,450.00
  Market Value: $123,200.00
  Buying Power: $2,250.00

Step 3: Fetching stock positions (100+ shares)...

Symbol    Shares    Contracts    Avg Cost    Current      P/L %    Equity
--------  --------  -----------  ----------  ----------  -------  ----------
AAPL      300       3            $150.25     $175.50     16.81%   $52,650.00
TSLA      200       2            $220.00     $245.75     11.70%   $49,150.00

Step 4: Fetching call options (up to 45 days out)...
  Analyzing AAPL...
  Found 45 suitable options for AAPL
  Analyzing TSLA...
  Found 38 suitable options for TSLA

Step 5: Analyzing opportunities with Claude AI...
  Risk Tolerance: MODERATE
  Minimum Premium: $50

================================================================================
                            AI RECOMMENDATIONS
================================================================================

EXECUTIVE SUMMARY
Based on your moderate risk tolerance and current positions, I recommend focusing
on selling covered calls on AAPL with a 30-day expiration at the $180 strike,
which offers an excellent balance of premium income ($285/contract) and upside
preservation...

[Detailed AI analysis continues...]
```

## 🛠️ Project Structure

```
StockBot/
├── src/
│   ├── __init__.py
│   ├── robinhood_client.py    # Robinhood API integration
│   ├── llm_advisor.py          # Claude AI integration
│   ├── bot.py                  # Main bot orchestration
│   └── config.py               # Configuration management
├── main.py                     # CLI entry point
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

## 🔒 Security & Privacy

- **No Trade Execution**: The bot only reads data and provides recommendations. It does NOT execute any trades.
- **Local Credentials**: All credentials are stored locally in `.env` (never committed to git)
- **Session Management**: Proper login/logout handling with Robinhood
- **API Security**: Uses official Robinhood and Anthropic libraries

## ⚙️ Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ROBINHOOD_USERNAME` | Yes | - | Your Robinhood email |
| `ROBINHOOD_PASSWORD` | Yes | - | Your Robinhood password |
| `ROBINHOOD_MFA_CODE` | No | - | 2FA code (if enabled) |
| `ANTHROPIC_API_KEY` | Yes | - | Your Claude API key |
| `CLAUDE_MODEL` | No | `claude-3-5-sonnet-20241022` | Claude model to use |
| `RISK_TOLERANCE` | No | `moderate` | Risk level (conservative/moderate/aggressive) |
| `MIN_PREMIUM` | No | `50` | Minimum premium in dollars |

### Command Line Options

```bash
python main.py --help

options:
  -h, --help           show this help message and exit
  --days DAYS          Maximum days until option expiration (default: 45)
  --quick SYMBOL       Quick analysis for a specific symbol
  --no-details         Don't show detailed options tables
  --env ENV            Path to .env file (default: .env)
```

## 📈 How It Works

1. **Authentication**: Logs into your Robinhood account securely
2. **Data Collection**: Fetches all stock positions with 100+ shares
3. **Options Filtering**: For each position:
   - Gets available call options
   - Filters by expiration date (default: 45 days)
   - Filters by minimum premium
   - Calculates annualized returns and Greeks
4. **AI Analysis**: Sends data to Claude AI for analysis considering:
   - Your risk tolerance
   - Market conditions
   - Options Greeks and liquidity
   - Your cost basis
5. **Recommendations**: Provides ranked, actionable recommendations

## 🎓 Understanding Covered Calls

A **covered call** is an options strategy where you:
1. Own 100+ shares of a stock
2. Sell a call option on those shares
3. Collect premium income immediately
4. Potentially sell your shares at the strike price if assigned

**Benefits:**
- Generate income from existing holdings
- Reduce cost basis over time
- Works well in flat or slightly bullish markets

**Risks:**
- Cap your upside if stock price rises above strike
- Still exposed to downside risk
- May have to sell shares you wanted to keep

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## ⚠️ Disclaimer

**THIS SOFTWARE IS FOR EDUCATIONAL PURPOSES ONLY.**

- This bot does NOT provide financial advice
- Always do your own research before making investment decisions
- Options trading carries significant risk and may not be suitable for all investors
- Past performance does not guarantee future results
- The creators are not responsible for any financial losses

## 📝 License

MIT License - See LICENSE file for details

## 🐛 Troubleshooting

### "Failed to login to Robinhood"
- Check your username and password in `.env`
- If you have 2FA enabled, provide `ROBINHOOD_MFA_CODE`
- Ensure you're not exceeding Robinhood's API rate limits

### "Configuration errors: ANTHROPIC_API_KEY is required"
- Make sure you've created a `.env` file (not just `.env.example`)
- Verify your Anthropic API key is valid
- Check there are no quotes around the API key in `.env`

### "No positions found with 100+ shares"
- You need at least 100 shares of a stock to sell covered calls
- The bot automatically filters positions with less than 100 shares

### Import errors
- Make sure you've activated your virtual environment
- Run `pip install -r requirements.txt` again
- Verify you're using Python 3.8 or higher

## 📧 Support

For issues or questions:
- Open an issue on GitHub
- Check existing issues for solutions

---

**Happy Trading! 📈**

Remember: The best trade is an educated trade. Use this bot as a tool to inform your decisions, not make them for you.
