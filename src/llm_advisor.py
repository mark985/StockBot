"""
LLM-powered covered call advisor using Anthropic's Claude
"""

import anthropic
from typing import List, Dict
import json


class CoveredCallAdvisor:
    """Uses Claude LLM to provide covered call strategy recommendations"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the advisor

        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def analyze_covered_call_opportunities(
        self,
        positions: List[Dict],
        options_data: Dict[str, List[Dict]],
        risk_tolerance: str = "moderate",
        min_premium: float = 50.0
    ) -> Dict:
        """
        Analyze covered call opportunities and get LLM recommendations

        Args:
            positions: List of stock positions
            options_data: Dictionary mapping symbols to their available call options
            risk_tolerance: Risk tolerance level (conservative, moderate, aggressive)
            min_premium: Minimum premium to consider (in dollars)

        Returns:
            Dictionary containing analysis and recommendations
        """
        # Prepare the data for the LLM
        analysis_prompt = self._build_analysis_prompt(
            positions,
            options_data,
            risk_tolerance,
            min_premium
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.3,  # Lower temperature for more consistent financial advice
                messages=[
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ]
            )

            # Extract the response
            analysis_text = response.content[0].text

            return {
                "success": True,
                "analysis": analysis_text,
                "model_used": self.model,
                "risk_tolerance": risk_tolerance
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _build_analysis_prompt(
        self,
        positions: List[Dict],
        options_data: Dict[str, List[Dict]],
        risk_tolerance: str,
        min_premium: float
    ) -> str:
        """
        Build the prompt for LLM analysis

        Args:
            positions: Stock positions
            options_data: Available options
            risk_tolerance: Risk tolerance level
            min_premium: Minimum premium threshold

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert options trading advisor specializing in covered call strategies.
Analyze the following stock positions and available call options, then provide specific recommendations
for selling covered calls.

RISK TOLERANCE: {risk_tolerance.upper()}
MINIMUM PREMIUM REQUIREMENT: ${min_premium}

CURRENT STOCK POSITIONS:
"""

        for pos in positions:
            prompt += f"""
- {pos['symbol']}:
  - Shares Owned: {pos['quantity']:.0f}
  - Contracts Available: {pos['contracts_available']}
  - Current Price: ${pos['current_price']:.2f}
  - Average Cost: ${pos['average_buy_price']:.2f}
  - Current P/L: {pos['percent_change']:.2f}%
  - Total Equity: ${pos['equity']:.2f}
"""

        prompt += "\n\nAVAILABLE CALL OPTIONS:\n"

        for symbol, options in options_data.items():
            if not options:
                prompt += f"\n{symbol}: No suitable options found\n"
                continue

            prompt += f"\n{symbol} - Top Options (sorted by annualized return):\n"

            # Show top 10 options per stock
            for i, opt in enumerate(options[:10], 1):
                prompt += f"""
  {i}. Strike: ${opt['strike_price']:.2f} | Exp: {opt['expiration_date']} ({opt['days_to_expiration']} days)
     Premium: ${opt['premium_per_contract']:.2f} | Annualized Return: {opt['annualized_return_pct']:.2f}%
     Moneyness: {opt['moneyness']:.2f}% {'OTM' if opt['moneyness'] > 0 else 'ITM'}
     Bid/Ask: ${opt['bid']:.2f}/${opt['ask']:.2f} | Volume: {opt['volume']} | OI: {opt['open_interest']}
     IV: {opt['implied_volatility']:.2f} | Delta: {opt['delta']:.2f}
"""

        prompt += f"""

ANALYSIS REQUIREMENTS:

1. For each stock position, recommend the BEST 1-3 covered call options to sell, considering:
   - Risk/reward profile based on {risk_tolerance} risk tolerance
   - Probability of assignment (based on delta and moneyness)
   - Premium income vs. potential upside sacrifice
   - Liquidity (volume and open interest)
   - Time decay optimization
   - Implied volatility levels

2. For EACH recommendation, provide:
   - Stock symbol and strike price
   - Expiration date
   - Expected premium income (per contract and total)
   - Probability of being assigned (estimate %)
   - Break-even analysis
   - Pros and cons
   - Risk assessment

3. Rank your recommendations from BEST to worst

4. Provide strategic insights:
   - Overall market conditions impact
   - Diversification considerations
   - Alternative strategies if applicable
   - Risk management tips

5. Format your response clearly with:
   - Executive Summary (2-3 sentences)
   - Detailed Recommendations (for each position)
   - Risk Warnings
   - Next Steps

IMPORTANT CONSIDERATIONS:
- Conservative: Prefer OTM options (lower assignment risk, lower premium)
- Moderate: Balance between premium and assignment risk
- Aggressive: Consider ATM or slightly ITM options (higher premium, higher assignment risk)
- Always consider the investor's cost basis
- Highlight any options with concerning low volume/OI
- Flag any positions where covered calls may not be optimal

Provide actionable, specific recommendations."""

        return prompt

    def quick_analysis(self, symbol: str, options: List[Dict], current_price: float) -> str:
        """
        Get a quick analysis for a single stock's options

        Args:
            symbol: Stock symbol
            options: Available options
            current_price: Current stock price

        Returns:
            Quick analysis text
        """
        if not options:
            return f"No suitable options found for {symbol}"

        prompt = f"""Quickly analyze these top 5 covered call options for {symbol} (current price: ${current_price:.2f}):

"""
        for i, opt in enumerate(options[:5], 1):
            prompt += f"""{i}. ${opt['strike_price']:.2f} strike, {opt['days_to_expiration']}d, ${opt['premium_per_contract']:.2f} premium
   Annualized: {opt['annualized_return_pct']:.2f}%, Delta: {opt['delta']:.2f}
"""

        prompt += "\nWhich option would you recommend and why? Keep it brief (3-4 sentences)."

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except Exception as e:
            return f"Error getting analysis: {e}"
