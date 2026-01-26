"""
Prompt templates for Gemini LLM analysis.
Structured prompts for covered call and other option strategies.
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


def build_covered_call_prompt(
    portfolio_data: Dict[str, Any],
    options_data: List[Dict[str, Any]],
    market_context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build a structured prompt for covered call analysis.

    Args:
        portfolio_data: Portfolio holdings with shares owned
        options_data: Screened options with metrics (premium, ROI, etc.)
        market_context: Optional market conditions (VIX, trends, etc.)

    Returns:
        str: Formatted prompt for Gemini
    """
    # Build market context section
    market_info = ""
    if market_context:
        market_info = f"""
## Market Context
- Current Date: {market_context.get('date', datetime.now().strftime('%Y-%m-%d'))}
- VIX Level: {market_context.get('vix', 'N/A')}
- Market Trend: {market_context.get('trend', 'Unknown')}
"""

    # Build portfolio section
    portfolio_info = "## Portfolio Holdings\n\n"
    for symbol, data in portfolio_data.items():
        shares = data.get('shares', 0)
        current_price = data.get('current_price', 0)
        total_value = shares * current_price
        avg_buy_price = data.get('average_buy_price', current_price)
        pnl_pct = ((current_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 else 0

        portfolio_info += f"""
### {symbol}
- Shares Owned: {shares}
- Current Price: ${current_price:.2f}
- Average Cost: ${avg_buy_price:.2f}
- P/L: {pnl_pct:+.2f}%
- Position Value: ${total_value:,.2f}
- Eligible for Covered Calls: {'Yes' if shares >= 100 else 'No'} ({shares // 100} contracts)
"""

    # Build options data section
    options_info = "## Screened Options Data\n\n"
    if not options_data:
        options_info += "No options data available.\n"
    else:
        for i, option in enumerate(options_data[:20], 1):  # Limit to top 20
            options_info += f"""
### Option {i}: {option.get('symbol', 'N/A')} - ${option.get('strike', 0):.2f} Call
- Expiration: {option.get('expiration_date', 'N/A')}
- Days to Expiry: {option.get('days_to_expiration', 'N/A')}
- Strike Price: ${option.get('strike', 0):.2f}
- Current Premium: ${option.get('premium', 0):.2f} per share
- Total Premium Income: ${option.get('total_premium', 0):.2f}
- Return on Investment (ROI): {option.get('roi', 0):.2f}%
- Annualized Return: {option.get('annualized_return', 0):.2f}%
- Delta: {option.get('delta', 'N/A')}
- Implied Volatility: {option.get('iv', 'N/A')}
- Volume: {option.get('volume', 'N/A')}
- Open Interest: {option.get('open_interest', 'N/A')}
- Distance from Current Price: {option.get('otm_percentage', 0):.2f}%
"""

    # Build the complete prompt
    prompt = f"""You are an expert options trading analyst specializing in covered call strategies. Analyze the following portfolio and options data to provide actionable covered call recommendations.

{market_info}

{portfolio_info}

{options_info}

## Your Task

Analyze the above data and provide covered call recommendations in **valid JSON format only**. Your response must be pure JSON with no additional text or markdown.

Consider:
1. **Income Generation**: Which options provide the best premium income?
2. **Risk vs Reward**: Balance between premium income and assignment risk
3. **Timeframe**: Optimal expiration dates for consistent income
4. **Volatility**: Current IV levels and their impact on premiums
5. **Market Conditions**: How current market trends affect the strategy
6. **Assignment Risk**: Likelihood of shares being called away

## Required JSON Output Format

Return ONLY valid JSON in this exact structure:

{{
  "analysis_summary": "Brief overview of market conditions and portfolio suitability for covered calls",
  "recommendations": [
    {{
      "rank": 1,
      "symbol": "AAPL",
      "action": "SELL_CALL",
      "strike": 150.00,
      "expiration": "2024-02-16",
      "contracts": 2,
      "premium_per_share": 2.50,
      "total_premium": 500.00,
      "roi": 3.33,
      "annualized_return": 48.00,
      "confidence": "high",
      "reasoning": "Detailed explanation of why this is recommended",
      "risk_assessment": "Analysis of assignment risk and downsides",
      "alternative_strikes": ["145.00", "155.00"]
    }}
  ],
  "market_outlook": "Brief market outlook and how it affects covered call strategy",
  "risk_warnings": [
    "Important risk to be aware of",
    "Another consideration"
  ],
  "next_steps": [
    "Actionable step 1",
    "Actionable step 2"
  ]
}}

**CRITICAL**: Respond with ONLY the JSON object. No explanatory text, no markdown formatting, just pure JSON.
"""

    return prompt


def build_simple_analysis_prompt(
    symbol: str,
    current_price: float,
    option_data: Dict[str, Any],
) -> str:
    """
    Build a simple prompt for single option analysis.

    Args:
        symbol: Stock symbol
        current_price: Current stock price
        option_data: Single option contract data

    Returns:
        str: Formatted prompt
    """
    prompt = f"""Analyze this covered call opportunity:

Stock: {symbol}
Current Price: ${current_price:.2f}

Call Option:
- Strike: ${option_data.get('strike', 0):.2f}
- Expiration: {option_data.get('expiration_date', 'N/A')}
- Premium: ${option_data.get('premium', 0):.2f}
- ROI: {option_data.get('roi', 0):.2f}%

Provide a brief analysis (2-3 sentences) on whether this is a good covered call opportunity and why.
"""
    return prompt
