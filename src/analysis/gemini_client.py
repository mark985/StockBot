"""
Google Gemini LLM client for stock and options analysis.
Provides AI-powered recommendations using structured prompts.
"""
import json
from typing import Dict, Any, List, Optional
from loguru import logger
import google.generativeai as genai

from config.settings import get_settings


class GeminiClientError(Exception):
    """Custom exception for Gemini client errors."""
    pass


class GeminiClient:
    """
    Client for interacting with Google Gemini LLM.

    Features:
    - Structured JSON responses
    - Configurable model selection
    - Error handling and retries
    - Temperature and safety settings
    """

    def __init__(self, model_name: str = "gemini-pro"):
        """
        Initialize Gemini client.

        Args:
            model_name: Gemini model to use (default: gemini-pro)
        """
        self.settings = get_settings()
        self.model_name = model_name

        # Configure Gemini with API key
        if not self.settings.gemini_api_key:
            raise GeminiClientError(
                "Gemini API key not found. Set GEMINI_API_KEY environment variable."
            )

        genai.configure(api_key=self.settings.gemini_api_key)

        # Initialize model
        self.model = genai.GenerativeModel(model_name)

        logger.info(f"GeminiClient initialized with model: {model_name}")

    def generate_analysis(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
    ) -> str:
        """
        Generate text analysis from Gemini.

        Args:
            prompt: The prompt to send to Gemini
            temperature: Controls randomness (0.0-1.0)
            max_output_tokens: Maximum response length

        Returns:
            str: Generated text response

        Raises:
            GeminiClientError: If generation fails
        """
        try:
            logger.debug(f"Sending prompt to Gemini (length: {len(prompt)} chars)")

            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )

            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
            )

            # Extract text from response
            if not response or not response.text:
                raise GeminiClientError("Empty response from Gemini")

            logger.debug(f"Received response from Gemini (length: {len(response.text)} chars)")

            return response.text

        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise GeminiClientError(f"Failed to generate analysis: {str(e)}") from e

    def generate_json_analysis(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON analysis from Gemini.

        Args:
            prompt: The prompt to send to Gemini (should request JSON output)
            temperature: Controls randomness (0.0-1.0)
            max_output_tokens: Maximum response length

        Returns:
            dict: Parsed JSON response

        Raises:
            GeminiClientError: If generation or parsing fails
        """
        try:
            # Get text response
            response_text = self.generate_analysis(prompt, temperature, max_output_tokens)

            # Try to extract JSON from response
            # Gemini sometimes wraps JSON in markdown code blocks
            response_text = response_text.strip()

            # Remove markdown code block markers if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            elif response_text.startswith("```"):
                response_text = response_text[3:]  # Remove ```

            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove trailing ```

            response_text = response_text.strip()

            # Parse JSON
            try:
                result = json.loads(response_text)
                logger.debug("Successfully parsed JSON response from Gemini")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Gemini response: {e}")
                logger.error(f"Response text: {response_text[:500]}...")
                raise GeminiClientError(
                    f"Gemini response is not valid JSON: {str(e)}"
                ) from e

        except GeminiClientError:
            raise
        except Exception as e:
            logger.error(f"JSON analysis failed: {e}")
            raise GeminiClientError(f"Failed to generate JSON analysis: {str(e)}") from e

    def analyze_covered_calls(
        self,
        portfolio_data: Dict[str, Any],
        options_data: List[Dict[str, Any]],
        market_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze covered call opportunities using Gemini.

        Args:
            portfolio_data: Portfolio holdings information
            options_data: Screened options data with metrics
            market_context: Optional market conditions context

        Returns:
            dict: Analysis with recommendations

        Raises:
            GeminiClientError: If analysis fails
        """
        try:
            # Import prompt templates
            from src.analysis.prompt_templates import build_covered_call_prompt

            # Build the prompt
            prompt = build_covered_call_prompt(
                portfolio_data=portfolio_data,
                options_data=options_data,
                market_context=market_context,
            )

            logger.info("Analyzing covered call opportunities with Gemini...")

            # Generate analysis
            analysis = self.generate_json_analysis(prompt, temperature=0.7)

            logger.info(f"Analysis complete. Found {len(analysis.get('recommendations', []))} recommendations")

            return analysis

        except Exception as e:
            logger.error(f"Covered call analysis failed: {e}")
            raise GeminiClientError(f"Failed to analyze covered calls: {str(e)}") from e


# Singleton instance
_gemini_client = None


def get_gemini_client(model_name: str = "gemini-pro") -> GeminiClient:
    """Get or create GeminiClient singleton instance."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient(model_name)
    return _gemini_client
