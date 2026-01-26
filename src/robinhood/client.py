"""
Robinhood HTTP client with authentication and session management.
Built from scratch for full control and debuggability.
"""
import requests
import secrets
import time
import pickle
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

from src.robinhood.endpoints import Endpoints, OAUTH_CLIENT_ID
from src.robinhood.exceptions import (
    RobinhoodError,
    AuthenticationError,
    VerificationRequired,
    APIError,
    InvalidCredentialsError,
)


class RobinhoodClient:
    """
    Custom Robinhood API client.

    Features:
    - Clean OAuth2 authentication
    - Session persistence
    - Verification workflow handling
    - Detailed error messages
    - Full request/response logging
    """

    def __init__(self, session_file: Optional[Path] = None):
        """
        Initialize Robinhood client.

        Args:
            session_file: Path to save/load session data
        """
        self.session = requests.Session()
        # Headers must match robin_stocks to avoid "Update Robinhood" errors
        self.session.headers.update({
            "Accept": "*/*",
            "Accept-Encoding": "gzip,deflate,br",
            "Accept-Language": "en-US,en;q=1",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "X-Robinhood-API-Version": "1.431.4",
            "Connection": "keep-alive",
            "User-Agent": "*"
        })

        # Session management
        self.session_file = session_file or Path.home() / ".tokens" / "robinhood_custom.pickle"
        self.session_file.parent.mkdir(parents=True, exist_ok=True)

        # Authentication state
        self.is_authenticated = False
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.device_token: Optional[str] = None
        self.account_number: Optional[str] = None

        logger.debug("RobinhoodClient initialized")

    def _generate_device_token(self) -> str:
        """Generate a cryptographically secure device token."""
        rands = [secrets.randbelow(256) for _ in range(16)]
        hexa = [format(i, '02x') for i in range(256)]
        token = ""
        for i, r in enumerate(rands):
            token += hexa[r]
            if i in [3, 5, 7, 9]:
                token += "-"
        return token

    def _request(
        self,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        authenticated: bool = False,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            data: Form data
            json_data: JSON data
            params: Query parameters
            authenticated: Whether request requires authentication

        Returns:
            dict: Response JSON

        Raises:
            APIError: On HTTP or API errors
        """
        try:
            logger.debug(f"{method} {url}")
            if data:
                logger.debug(f"Data: {self._sanitize_log(data)}")
            if json_data:
                logger.debug(f"JSON: {self._sanitize_log(json_data)}")

            # Update headers for authenticated requests
            if authenticated and self.access_token:
                self.session.headers["Authorization"] = f"Bearer {self.access_token}"

            # Set content type for JSON requests
            if json_data:
                self.session.headers["Content-Type"] = "application/json"

            # Make request
            response = self.session.request(
                method=method,
                url=url,
                data=data,
                json=json_data,
                params=params,
                timeout=30,
            )

            # Reset content type
            if json_data:
                self.session.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=utf-8"

            logger.debug(f"Response status: {response.status_code}")

            # Parse JSON response
            try:
                response_data = response.json()
                logger.debug(f"Response data: {self._sanitize_log(response_data)}")
            except ValueError:
                response_data = {"text": response.text}
                logger.debug(f"Non-JSON response: {response.text[:200]}")

            # Check for errors (but allow verification_workflow responses through)
            if response.status_code >= 400:
                # Verification workflows can return 403 - don't treat as error
                if "verification_workflow" not in response_data:
                    error_msg = response_data.get("detail", response_data.get("error", f"HTTP {response.status_code}"))
                    logger.error(f"API error: {error_msg}")
                    raise APIError(
                        message=error_msg,
                        status_code=response.status_code,
                        response=response_data,
                    )

            return response_data

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise APIError(f"Network error: {str(e)}")

    def _sanitize_log(self, data: Dict) -> Dict:
        """Sanitize sensitive data for logging."""
        if not isinstance(data, dict):
            return data

        sanitized = data.copy()
        sensitive_keys = ["password", "mfa_code", "access_token", "refresh_token"]

        for key in sensitive_keys:
            if key in sanitized:
                sanitized[key] = "***REDACTED***"

        return sanitized

    def login(
        self,
        username: str,
        password: str,
        mfa_code: Optional[str] = None,
        prefer_sms: bool = False,
    ) -> Dict[str, Any]:
        """
        Login to Robinhood.

        Args:
            username: Robinhood email
            password: Robinhood password
            mfa_code: Optional MFA code
            prefer_sms: If True, request SMS/email verification instead of app push

        Returns:
            dict: Authentication response

        Raises:
            AuthenticationError: On login failure
            VerificationRequired: When additional verification needed
        """
        logger.info(f"Logging in as {username}")

        # Generate device token if not exists
        if not self.device_token:
            self.device_token = self._generate_device_token()
            logger.debug(f"Generated device token: {self.device_token[:8]}...")

        # Build login payload (fields must match latest Robinhood API requirements)
        payload = {
            "client_id": OAUTH_CLIENT_ID,
            "expires_in": 86400,
            "grant_type": "password",
            "password": password,
            "scope": "internal",
            "username": username,
            "device_token": self.device_token,
            "try_passkeys": False,
            "token_request_path": "/login",
            "create_read_only_secondary_token": True,
        }

        if mfa_code:
            payload["mfa_code"] = mfa_code

        # Make login request
        try:
            response = self._request("POST", Endpoints.LOGIN, data=payload)

            # Check for verification workflow
            if "verification_workflow" in response:
                workflow_data = response["verification_workflow"]
                workflow_id = workflow_data["id"]
                workflow_status = workflow_data.get("workflow_status")

                logger.warning(f"Verification required: {workflow_status}")
                logger.debug(f"Full workflow data: {workflow_data}")

                # Automatically handle verification workflow
                try:
                    response = self._handle_verification_workflow(workflow_id, username, password, mfa_code, prefer_sms)
                except Exception as e:
                    # If automatic handling fails, raise VerificationRequired for manual handling
                    logger.error(f"Automatic verification failed: {e}")
                    raise VerificationRequired(
                        message="Robinhood requires additional verification",
                        workflow_id=workflow_id,
                        verification_type=workflow_status,
                        workflow_data=workflow_data,
                    )

            # Check for successful authentication
            if "access_token" in response:
                self.access_token = response["access_token"]
                self.refresh_token = response.get("refresh_token")
                self.is_authenticated = True

                logger.info("Login successful!")

                # Save session
                self._save_session()

                return response
            else:
                # Unexpected response
                logger.error(f"Unexpected login response: {response}")
                raise AuthenticationError(
                    "Login failed: Unexpected response format",
                    response_data=response,
                )

        except APIError as e:
            # Check for specific error types
            if e.status_code == 400:
                error_detail = e.response.get("detail", str(e))
                if "credentials" in error_detail.lower():
                    raise InvalidCredentialsError("Invalid username or password")

            raise AuthenticationError(f"Login failed: {str(e)}", response_data=e.response)

    def _save_session(self) -> None:
        """Save session data to file."""
        if not self.access_token:
            return

        session_data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "device_token": self.device_token,
        }

        try:
            with open(self.session_file, "wb") as f:
                pickle.dump(session_data, f)
            logger.debug(f"Session saved to {self.session_file}")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    def load_session(self) -> bool:
        """
        Load session from file.

        Returns:
            bool: True if session loaded successfully
        """
        if not self.session_file.exists():
            logger.debug("No saved session found")
            return False

        try:
            with open(self.session_file, "rb") as f:
                session_data = pickle.load(f)

            self.access_token = session_data.get("access_token")
            self.refresh_token = session_data.get("refresh_token")
            self.device_token = session_data.get("device_token")

            if self.access_token:
                self.is_authenticated = True
                logger.info("Session loaded successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to load session: {e}")

        return False

    def get(self, url: str, params: Optional[Dict] = None, authenticated: bool = True) -> Dict[str, Any]:
        """Make authenticated GET request."""
        return self._request("GET", url, params=params, authenticated=authenticated)

    def post(self, url: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None, authenticated: bool = True) -> Dict[str, Any]:
        """Make authenticated POST request."""
        return self._request("POST", url, data=data, json_data=json_data, authenticated=authenticated)

    def logout(self) -> None:
        """Logout and clear session."""
        self.is_authenticated = False
        self.access_token = None
        self.refresh_token = None

        if self.session_file.exists():
            self.session_file.unlink()

        logger.info("Logged out successfully")

    # ===== Verification Workflow Methods =====

    def _request_sms_verification(self, workflow_id: str) -> bool:
        """
        Request SMS or email verification instead of app push using identity workflow API.

        This uses the identi.robinhood.com endpoint discovered through browser network analysis.
        When the user clicks "Send text instead" on the web interface, Robinhood sends a PATCH
        request to the identity workflow endpoint with deviceApprovalChallengeAction.fallback.

        Args:
            workflow_id: Verification workflow ID from initial login response

        Returns:
            bool: True if successfully requested SMS/email, False otherwise
        """
        try:
            logger.info("Requesting SMS/email verification via identity workflow API")

            # Build identity workflow URL
            identity_url = Endpoints.IDENTITY_WORKFLOW.format(workflow_id=workflow_id)

            # Build payload matching browser's "Send text instead" action
            payload = {
                "clientVersion": "1.0.0",
                "screenName": "DEVICE_APPROVAL_CHALLENGE",
                "id": workflow_id,
                "deviceApprovalChallengeAction": {
                    "fallback": {}
                }
            }

            logger.debug(f"Sending PATCH to {identity_url}")
            logger.debug(f"Payload: {payload}")

            # Send PATCH request (unauthenticated - before login completes)
            response = self._request("PATCH", identity_url, json_data=payload, authenticated=False)

            logger.info("✓ Successfully requested SMS/email verification via fallback")
            logger.debug(f"Identity workflow response: {response}")

            # Extract SMS challenge ID from the identity workflow response
            # This allows us to submit the SMS code directly without waiting for Pathfinder
            sms_challenge_id = None
            try:
                screen = response.get('route', {}).get('replace', {}).get('screen', {})
                if screen.get('name') == 'SMS_CHALLENGE':
                    sms_params = screen.get('smsChallengeScreenParams', {})
                    sheriff_challenge = sms_params.get('sheriffChallenge', {})
                    sms_challenge_id = sheriff_challenge.get('id')
                    if sms_challenge_id:
                        logger.info(f"Extracted SMS challenge ID: {sms_challenge_id}")
            except Exception as e:
                logger.debug(f"Could not extract SMS challenge ID from response: {e}")

            return (True, sms_challenge_id)

        except Exception as e:
            logger.error(f"Failed to request SMS verification via identity workflow: {e}")
            return (False, None)

    def _handle_verification_workflow(self, workflow_id: str, username: str, password: str, mfa_code: Optional[str] = None, prefer_sms: bool = False) -> Dict[str, Any]:
        """
        Handle Robinhood's verification workflow automatically.

        This follows the same process as robin_stocks:
        1. Register device with Pathfinder
        2. Poll for challenge details
        3. Handle challenge (prompt/sms/email)
        4. Confirm workflow approval
        5. Retry login

        Args:
            workflow_id: Verification workflow ID from initial login
            username: Robinhood username
            password: Robinhood password
            mfa_code: Optional MFA code
            prefer_sms: If True, request SMS/email verification instead of app push

        Returns:
            dict: Successful login response with access_token

        Raises:
            AuthenticationError: If verification fails or times out
        """
        logger.info("Starting verification workflow handling")

        try:
            # Step 1: Register device with Pathfinder
            logger.info("Registering device with Pathfinder...")
            machine_payload = {
                'device_id': self.device_token,
                'flow': 'suv',
                'input': {'workflow_id': workflow_id}
            }
            machine_response = self._request("POST", Endpoints.PATHFINDER_USER_MACHINE, json_data=machine_payload)

            if 'id' not in machine_response:
                raise AuthenticationError("No machine ID returned from Pathfinder")

            machine_id = machine_response['id']
            logger.info(f"Machine registered with ID: {machine_id}")

            # Step 2: Poll for challenge details
            inquiries_url = Endpoints.PATHFINDER_INQUIRIES.format(machine_id=machine_id)
            start_time = time.time()
            timeout = 120  # 2-minute timeout
            sms_already_requested = False  # Track if we've already requested SMS

            logger.info("Polling for challenge details...")
            while time.time() - start_time < timeout:
                time.sleep(5)  # Wait before polling

                try:
                    inquiries_response = self.get(inquiries_url, authenticated=False)
                except Exception as e:
                    logger.warning(f"Polling error (will retry): {e}")
                    continue

                # Check if challenge is available
                if 'context' in inquiries_response and 'sheriff_challenge' in inquiries_response['context']:
                    challenge = inquiries_response['context']['sheriff_challenge']
                    challenge_type = challenge.get('type')
                    challenge_status = challenge.get('status')
                    challenge_id = challenge.get('id')

                    logger.info(f"Challenge detected: type={challenge_type}, status={challenge_status}")

                    # Step 3: Handle challenge based on type
                    if challenge_type == 'prompt':
                        # App push notification
                        if prefer_sms and not sms_already_requested:
                            # User prefers SMS/email, try to request alternative verification (only once)
                            logger.info("App push detected but user prefers SMS/email verification")
                            print("\n⚠️  Robinhood selected app push notification, but you prefer SMS/email.")
                            print("Attempting to request SMS or email verification instead...")

                            # Request SMS verification using identity workflow API
                            sms_requested, sms_challenge_id = self._request_sms_verification(workflow_id)

                            if not sms_requested:
                                print("\n⚠️  Could not switch to SMS/email. You can either:")
                                print("1. Check your Robinhood mobile app to approve this login")
                                print("2. Cancel and try logging in via the official Robinhood app first")

                                user_choice = input("\nWait for app push? (y/n): ").strip().lower()
                                if user_choice != 'y':
                                    raise AuthenticationError("User cancelled app push verification")
                            elif sms_challenge_id:
                                # We have the SMS challenge ID from identity workflow - use it directly!
                                sms_already_requested = True
                                logger.info(f"Got SMS challenge ID directly from identity workflow: {sms_challenge_id}")
                                print("\n✓ SMS verification code has been sent to your phone!")

                                # Prompt user for SMS code
                                user_code = input("Enter the SMS verification code: ")

                                # Submit SMS code directly using the challenge ID from identity workflow
                                challenge_url = Endpoints.CHALLENGE.format(challenge_id=sms_challenge_id)
                                challenge_payload = {"response": user_code}
                                challenge_response = self._request("POST", challenge_url, json_data=challenge_payload, authenticated=False)

                                if challenge_response.get('status') == 'validated':
                                    logger.info("SMS code accepted!")
                                    break  # Exit polling loop and proceed to workflow confirmation
                                else:
                                    logger.error(f"SMS code rejected: {challenge_response}")
                                    raise AuthenticationError(f"SMS verification code was rejected: {challenge_response}")
                            else:
                                # SMS requested but no challenge ID - fall back to polling
                                sms_already_requested = True
                                logger.info("Successfully requested SMS/email verification - waiting for Pathfinder to update...")
                                print("\n✓ SMS requested! Waiting for verification code to arrive...")
                                print("   (The code may take a few seconds to arrive)")
                                continue  # Continue polling for SMS challenge to appear

                        # If we're still seeing prompt after requesting SMS, just continue polling
                        if sms_already_requested:
                            logger.debug("Still seeing prompt challenge after SMS request - continuing to poll...")
                            continue

                        # Wait for app push approval
                        logger.info("Verification via Robinhood app required")
                        print("\n⚠️  Check your Robinhood mobile app to approve this login")

                        # Poll push endpoint for approval
                        prompt_url = Endpoints.PUSH_PROMPT_STATUS.format(challenge_id=challenge_id)
                        while time.time() - start_time < timeout:
                            time.sleep(5)
                            try:
                                prompt_status = self.get(prompt_url, authenticated=False)
                                if prompt_status.get('challenge_status') == 'validated':
                                    logger.info("App approval received!")
                                    break
                            except Exception as e:
                                logger.debug(f"Push polling error: {e}")
                                continue
                        break

                    elif challenge_type in ['sms', 'email'] and challenge_status == 'issued':
                        # Code-based verification
                        logger.info(f"Verification code sent via {challenge_type}")
                        print(f"\n⚠️  Check your {challenge_type} for the verification code")

                        # Prompt user for code
                        user_code = input(f"Enter the {challenge_type} verification code: ")

                        # Submit verification code
                        challenge_url = Endpoints.CHALLENGE.format(challenge_id=challenge_id)
                        challenge_payload = {"response": user_code}
                        challenge_response = self._request("POST", challenge_url, json_data=challenge_payload)

                        if challenge_response.get('status') == 'validated':
                            logger.info("Verification code accepted!")
                            break
                        else:
                            raise AuthenticationError(f"Verification code rejected: {challenge_response}")

                    elif challenge_status == 'validated':
                        logger.info("Challenge already validated")
                        break

            # Step 4: Confirm workflow approval
            logger.info("Confirming workflow approval...")
            retry_attempts = 5

            while time.time() - start_time < timeout and retry_attempts > 0:
                try:
                    inquiries_payload = {"sequence": 0, "user_input": {"status": "continue"}}
                    inquiries_response = self._request("POST", inquiries_url, json_data=inquiries_payload)

                    # Check if workflow is approved
                    if 'type_context' in inquiries_response:
                        result = inquiries_response['type_context'].get('result')
                        if result == 'workflow_status_approved':
                            logger.info("Workflow approved!")
                            break

                    workflow_status = inquiries_response.get('verification_workflow', {}).get('workflow_status')
                    if workflow_status == 'workflow_status_approved':
                        logger.info("Workflow approved!")
                        break
                    elif workflow_status == 'workflow_status_internal_pending':
                        logger.debug("Still pending approval...")
                        time.sleep(5)
                    else:
                        retry_attempts -= 1
                        if retry_attempts == 0:
                            logger.warning("Max retries reached, assuming approved")
                            break
                        time.sleep(5)

                except Exception as e:
                    logger.warning(f"Workflow confirmation error (will retry): {e}")
                    retry_attempts -= 1
                    if retry_attempts == 0:
                        logger.warning("Max retries reached, assuming approved")
                        break
                    time.sleep(5)

            # Step 5: Retry login with same credentials
            logger.info("Retrying login after verification...")
            payload = {
                "client_id": OAUTH_CLIENT_ID,
                "expires_in": 86400,
                "grant_type": "password",
                "password": password,
                "scope": "internal",
                "username": username,
                "device_token": self.device_token,
                "try_passkeys": False,
                "token_request_path": "/login",
                "create_read_only_secondary_token": True,
            }

            if mfa_code:
                payload["mfa_code"] = mfa_code

            response = self._request("POST", Endpoints.LOGIN, data=payload)

            if "access_token" in response:
                logger.info("Login successful after verification!")
                return response
            else:
                raise AuthenticationError(f"Login failed after verification: {response}")

        except Exception as e:
            logger.error(f"Verification workflow failed: {e}")
            raise AuthenticationError(f"Verification failed: {str(e)}")

    # ===== Account & Portfolio Methods =====

    def get_account(self) -> Dict[str, Any]:
        """
        Get account information.

        Returns:
            dict: Account details including account number, buying power, etc.
        """
        if not self.is_authenticated:
            raise AuthenticationError("Must be logged in to get account info")

        logger.debug("Fetching account information")
        response = self.get(Endpoints.ACCOUNTS)

        if "results" in response and len(response["results"]) > 0:
            account = response["results"][0]
            self.account_number = account.get("account_number")
            logger.debug(f"Account number: {self.account_number}")
            return account

        raise APIError("No account found")

    def get_positions(self, nonzero: bool = True) -> list:
        """
        Get current stock positions.

        Args:
            nonzero: If True, only return positions with quantity > 0

        Returns:
            list: List of position dictionaries
        """
        if not self.is_authenticated:
            raise AuthenticationError("Must be logged in to get positions")

        logger.info("Fetching stock positions")
        all_positions = []

        url = Endpoints.POSITIONS
        while url:
            response = self.get(url)
            positions = response.get("results", [])

            if nonzero:
                positions = [p for p in positions if float(p.get("quantity", 0)) > 0]

            all_positions.extend(positions)

            # Handle pagination
            url = response.get("next")

        logger.info(f"Found {len(all_positions)} positions")
        return all_positions

    def get_options_positions(self, nonzero: bool = True) -> list:
        """
        Get current options positions.

        Args:
            nonzero: If True, only return positions with quantity > 0

        Returns:
            list: List of options position dictionaries
        """
        if not self.is_authenticated:
            raise AuthenticationError("Must be logged in to get options positions")

        logger.info("Fetching options positions")
        all_positions = []

        url = Endpoints.OPTIONS_POSITIONS
        while url:
            response = self.get(url)
            positions = response.get("results", [])

            if nonzero:
                positions = [p for p in positions if float(p.get("quantity", 0)) > 0]

            all_positions.extend(positions)

            # Handle pagination
            url = response.get("next")

        logger.info(f"Found {len(all_positions)} options positions")
        return all_positions

    # ===== Stock Data Methods =====

    def get_instrument_by_url(self, instrument_url: str) -> Dict[str, Any]:
        """
        Get instrument details from URL.

        Args:
            instrument_url: Full URL to instrument

        Returns:
            dict: Instrument details including symbol
        """
        logger.debug(f"Fetching instrument: {instrument_url}")
        return self.get(instrument_url)

    def get_instrument_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Get instrument details by ticker symbol.

        Args:
            symbol: Stock ticker (e.g., 'AAPL')

        Returns:
            dict: Instrument details
        """
        logger.debug(f"Fetching instrument for {symbol}")
        url = Endpoints.INSTRUMENTS
        response = self.get(url, params={"symbol": symbol})

        results = response.get("results", [])
        if not results:
            raise APIError(f"Instrument not found for symbol: {symbol}")

        return results[0]

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get current stock quote.

        Args:
            symbol: Stock ticker (e.g., 'AAPL')

        Returns:
            dict: Quote data with prices, volume, etc.
        """
        logger.debug(f"Fetching quote for {symbol}")
        url = Endpoints.QUOTES
        response = self.get(url, params={"symbols": symbol})

        results = response.get("results", [])
        if not results:
            raise APIError(f"Quote not found for symbol: {symbol}")

        return results[0]

    def get_quotes(self, symbols: list) -> list:
        """
        Get quotes for multiple symbols.

        Args:
            symbols: List of stock tickers

        Returns:
            list: List of quote dictionaries
        """
        logger.debug(f"Fetching quotes for {len(symbols)} symbols")
        symbols_str = ",".join(symbols)
        url = Endpoints.QUOTES
        response = self.get(url, params={"symbols": symbols_str})

        return response.get("results", [])

    # ===== Options Data Methods =====

    def get_options_chains(self, symbol: str) -> Dict[str, Any]:
        """
        Get options chains for a symbol.

        Args:
            symbol: Stock ticker (e.g., 'AAPL')

        Returns:
            dict: Options chain metadata
        """
        logger.debug(f"Fetching options chains for {symbol}")
        url = Endpoints.OPTIONS_CHAINS
        response = self.get(url, params={"equity_instrument_ids": symbol})

        results = response.get("results", [])
        if not results:
            raise APIError(f"Options chain not found for symbol: {symbol}")

        return results[0]

    def get_options_instruments(
        self,
        chain_id: str,
        expiration_dates: Optional[list] = None,
        option_type: str = "call",
        state: str = "active",
    ) -> list:
        """
        Get options instruments for a chain.

        Args:
            chain_id: Options chain ID
            expiration_dates: List of expiration dates (YYYY-MM-DD)
            option_type: 'call' or 'put'
            state: 'active' or 'inactive'

        Returns:
            list: List of options instrument dictionaries
        """
        logger.info(f"Fetching {option_type} options for chain {chain_id}")

        params = {
            "chain_id": chain_id,
            "state": state,
            "type": option_type,
        }

        if expiration_dates:
            params["expiration_dates"] = ",".join(expiration_dates)

        all_instruments = []
        url = Endpoints.OPTIONS_INSTRUMENTS

        while url:
            response = self.get(url, params=params if url == Endpoints.OPTIONS_INSTRUMENTS else None)
            instruments = response.get("results", [])
            all_instruments.extend(instruments)

            # Handle pagination
            url = response.get("next")

        logger.info(f"Found {len(all_instruments)} options instruments")
        return all_instruments

    def get_options_market_data(self, option_ids: list) -> list:
        """
        Get market data for options instruments.

        Args:
            option_ids: List of options instrument IDs

        Returns:
            list: List of market data dictionaries with prices, Greeks, etc.
        """
        logger.debug(f"Fetching market data for {len(option_ids)} options")

        # API accepts comma-separated IDs
        ids_str = ",".join(option_ids)
        url = f"{Endpoints.OPTIONS_MARKET_DATA}?instruments={ids_str}"

        all_data = []
        while url:
            response = self.get(url)
            data = response.get("results", [])
            all_data.extend(data)

            # Handle pagination
            url = response.get("next")

        logger.debug(f"Retrieved market data for {len(all_data)} options")
        return all_data
