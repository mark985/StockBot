"""
Configuration management for StockBot
"""

import os
from dotenv import load_dotenv
from typing import Optional


class Config:
    """Configuration loader and validator"""

    def __init__(self, env_file: str = ".env"):
        """
        Load configuration from environment

        Args:
            env_file: Path to .env file
        """
        load_dotenv(env_file)

        # Robinhood credentials
        self.robinhood_username = os.getenv("ROBINHOOD_USERNAME")
        self.robinhood_password = os.getenv("ROBINHOOD_PASSWORD")
        self.robinhood_mfa_code = os.getenv("ROBINHOOD_MFA_CODE")

        # Anthropic API
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.claude_model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

        # Bot configuration
        self.risk_tolerance = os.getenv("RISK_TOLERANCE", "moderate").lower()
        self.min_premium = float(os.getenv("MIN_PREMIUM", "50"))

        # Validate configuration
        self._validate()

    def _validate(self):
        """Validate required configuration"""
        errors = []

        if not self.robinhood_username:
            errors.append("ROBINHOOD_USERNAME is required")

        if not self.robinhood_password:
            errors.append("ROBINHOOD_PASSWORD is required")

        if not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required")

        if self.risk_tolerance not in ["conservative", "moderate", "aggressive"]:
            errors.append(
                f"RISK_TOLERANCE must be conservative, moderate, or aggressive "
                f"(got: {self.risk_tolerance})"
            )

        if self.min_premium < 0:
            errors.append(f"MIN_PREMIUM must be positive (got: {self.min_premium})")

        if errors:
            error_msg = "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)

    def __repr__(self):
        """String representation (hiding sensitive data)"""
        return f"""Config(
    robinhood_username={self.robinhood_username},
    robinhood_password=***,
    claude_model={self.claude_model},
    risk_tolerance={self.risk_tolerance},
    min_premium=${self.min_premium}
)"""
