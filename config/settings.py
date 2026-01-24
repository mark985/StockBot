"""
Centralized configuration management for StockBot.
Uses pydantic for validation and python-dotenv for environment variables.
"""
from typing import Tuple
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os
from pathlib import Path


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration to prevent Robinhood API blocks."""

    calls_per_minute: int = Field(default=20, description="Maximum API calls per minute")
    calls_per_hour: int = Field(default=500, description="Maximum API calls per hour")
    min_delay_seconds: float = Field(default=2.0, description="Minimum delay between calls")
    backoff_factor: float = Field(default=2.0, description="Exponential backoff multiplier")
    max_retries: int = Field(default=3, description="Maximum retry attempts")

    class Config:
        env_prefix = ""


class StrategyConfig(BaseSettings):
    """Covered call strategy parameters."""

    min_option_volume: int = Field(default=100, description="Minimum option volume")
    min_open_interest: int = Field(default=50, description="Minimum open interest")
    min_premium: float = Field(default=0.50, description="Minimum premium per share")
    max_days_to_expiration: int = Field(default=45, description="Maximum days to expiration")
    min_days_to_expiration: int = Field(default=7, description="Minimum days to expiration")

    # Strike price range as percentage above current price
    min_strike_percent: float = Field(default=1.05, description="Minimum strike as % of current price")
    max_strike_percent: float = Field(default=1.15, description="Maximum strike as % of current price")

    # Delta range for options screening
    min_delta: float = Field(default=0.15, description="Minimum delta value")
    max_delta: float = Field(default=0.35, description="Maximum delta value")

    class Config:
        env_prefix = ""

    @validator('min_strike_percent', 'max_strike_percent')
    def validate_strike_percent(cls, v):
        if v <= 0:
            raise ValueError("Strike percentage must be positive")
        return v

    @validator('min_delta', 'max_delta')
    def validate_delta(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Delta must be between 0 and 1")
        return v


class SchedulerConfig(BaseSettings):
    """Scheduler configuration for automated scans."""

    schedule_enabled: bool = Field(default=False, description="Enable scheduled scans")
    schedule_time: str = Field(default="09:00", description="Daily scan time (HH:MM)")
    schedule_timezone: str = Field(default="America/New_York", description="Timezone for scheduling")

    class Config:
        env_prefix = ""


class NotificationConfig(BaseSettings):
    """Notification settings for email alerts."""

    notification_email: str = Field(default="", description="Email to receive notifications")
    smtp_server: str = Field(default="", description="SMTP server address")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_username: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")

    class Config:
        env_prefix = ""


class Settings(BaseSettings):
    """Main settings class for StockBot."""

    # Project paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    logs_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "logs")
    reports_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "reports")

    # Robinhood credentials (prefer keyring over env vars)
    robinhood_username: str = Field(default="", description="Robinhood username")
    robinhood_password: str = Field(default="", description="Robinhood password")

    # Gemini API
    gemini_api_key: str = Field(default="", description="Google Gemini API key")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Sub-configurations
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    @property
    def strike_range(self) -> Tuple[float, float]:
        """Get strike price range as tuple."""
        return (self.strategy.min_strike_percent, self.strategy.max_strike_percent)

    @property
    def delta_range(self) -> Tuple[float, float]:
        """Get delta range as tuple."""
        return (self.strategy.min_delta, self.strategy.max_delta)

    @property
    def expiration_range(self) -> Tuple[int, int]:
        """Get expiration days range as tuple."""
        return (self.strategy.min_days_to_expiration, self.strategy.max_days_to_expiration)


# Singleton instance
_settings = None


def get_settings() -> Settings:
    """Get or create settings singleton instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience function for quick access
def reload_settings() -> Settings:
    """Reload settings from environment/file."""
    global _settings
    _settings = Settings()
    return _settings
