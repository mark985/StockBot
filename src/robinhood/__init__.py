"""
Custom Robinhood API client built from scratch.
Provides clean, debuggable access to Robinhood's API.
"""

from src.robinhood.client import RobinhoodClient
from src.robinhood.exceptions import (
    RobinhoodError,
    AuthenticationError,
    VerificationRequired,
    APIError,
)

__all__ = [
    "RobinhoodClient",
    "RobinhoodError",
    "AuthenticationError",
    "VerificationRequired",
    "APIError",
]
