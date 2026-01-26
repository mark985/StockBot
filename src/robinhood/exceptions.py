"""
Custom exceptions for Robinhood API client.
"""


class RobinhoodError(Exception):
    """Base exception for all Robinhood errors."""
    pass


class AuthenticationError(RobinhoodError):
    """Raised when authentication fails."""

    def __init__(self, message: str, response_data: dict = None):
        super().__init__(message)
        self.response_data = response_data or {}


class VerificationRequired(AuthenticationError):
    """Raised when Robinhood requires additional verification."""

    def __init__(self, message: str, workflow_id: str = None, verification_type: str = None, workflow_data: dict = None):
        super().__init__(message)
        self.workflow_id = workflow_id
        self.verification_type = verification_type
        self.workflow_data = workflow_data or {}


class APIError(RobinhoodError):
    """Raised when API request fails."""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when username/password are incorrect."""
    pass
