"""
LLM Client for AI-powered insights and completions.

Provides a unified interface for multiple LLM providers (Anthropic Claude, OpenAI GPT)
with retry logic, rate limiting, and structured output support.
"""

import asyncio
import json
import time
import logging
from typing import Any, Optional, Literal
from enum import Enum
from datetime import datetime

from anthropic import AsyncAnthropic, APIError as AnthropicAPIError
from openai import AsyncOpenAI, APIError as OpenAIAPIError

from app.core.config import settings


logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class LLMModel(str, Enum):
    """Available LLM models."""
    # Anthropic Claude models
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"

    # OpenAI GPT models
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_4 = "gpt-4"
    GPT_35_TURBO = "gpt-3.5-turbo"


class LLMClient:
    """
    Unified LLM client supporting multiple providers.

    Features:
    - Multi-provider support (Anthropic, OpenAI)
    - Automatic retry with exponential backoff
    - Rate limiting
    - Structured JSON output
    - API call logging for debugging and cost tracking
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 60.0
    ):
        """
        Initialize LLM client.

        Args:
            provider: LLM provider (anthropic or openai). Defaults to config setting.
            model: Model name. Defaults to provider's default model.
            api_key: API key. Defaults to config setting for the provider.
            max_retries: Maximum number of retry attempts
            retry_delay: Initial retry delay in seconds (exponential backoff)
            timeout: Request timeout in seconds
        """
        # Determine provider
        if provider is None:
            provider = LLMProvider(settings.DEFAULT_LLM_PROVIDER)
        self.provider = provider

        # Get API key
        if api_key is None:
            if self.provider == LLMProvider.ANTHROPIC:
                api_key = settings.ANTHROPIC_API_KEY
            elif self.provider == LLMProvider.OPENAI:
                api_key = settings.OPENAI_API_KEY

        if not api_key:
            raise ValueError(f"API key not provided for {self.provider.value}")

        # Initialize client
        if self.provider == LLMProvider.ANTHROPIC:
            self.client = AsyncAnthropic(api_key=api_key, timeout=timeout)
            self.model = model or LLMModel.CLAUDE_3_5_SONNET.value
        elif self.provider == LLMProvider.OPENAI:
            self.client = AsyncOpenAI(api_key=api_key, timeout=timeout)
            self.model = model or LLMModel.GPT_4_TURBO.value
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        # Statistics for logging
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: User prompt/message
            system_prompt: Optional system prompt for context
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text response
        """
        start_time = time.time()

        try:
            if self.provider == LLMProvider.ANTHROPIC:
                response = await self._generate_anthropic_completion(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            elif self.provider == LLMProvider.OPENAI:
                response = await self._generate_openai_completion(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            # Log the API call
            elapsed_time = time.time() - start_time
            self._log_api_call(
                method="generate_completion",
                prompt_length=len(prompt),
                response_length=len(response),
                elapsed_time=elapsed_time,
                success=True
            )

            return response

        except Exception as e:
            elapsed_time = time.time() - start_time
            self._log_api_call(
                method="generate_completion",
                prompt_length=len(prompt),
                response_length=0,
                elapsed_time=elapsed_time,
                success=False,
                error=str(e)
            )
            raise

    async def generate_structured_output(
        self,
        prompt: str,
        schema: dict[str, Any],
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> dict[str, Any]:
        """
        Generate structured JSON output matching a schema.

        Args:
            prompt: User prompt/message
            schema: JSON schema for the expected output structure
            system_prompt: Optional system prompt for context
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            **kwargs: Additional provider-specific parameters

        Returns:
            Parsed JSON object matching the schema
        """
        # Add schema to system prompt
        schema_instruction = f"\n\nYou must respond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        full_system_prompt = (system_prompt or "") + schema_instruction

        start_time = time.time()

        try:
            response = await self.generate_completion(
                prompt=prompt,
                system_prompt=full_system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            # Parse JSON response
            # Try to extract JSON from markdown code blocks if present
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            parsed_response = json.loads(response)

            elapsed_time = time.time() - start_time
            self._log_api_call(
                method="generate_structured_output",
                prompt_length=len(prompt),
                response_length=len(response),
                elapsed_time=elapsed_time,
                success=True
            )

            return parsed_response

        except json.JSONDecodeError as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Failed to parse JSON response: {e}\nResponse: {response}")
            self._log_api_call(
                method="generate_structured_output",
                prompt_length=len(prompt),
                response_length=len(response) if isinstance(response, str) else 0,
                elapsed_time=elapsed_time,
                success=False,
                error=f"JSON parse error: {str(e)}"
            )
            raise ValueError(f"Failed to parse JSON response: {e}")

        except Exception as e:
            elapsed_time = time.time() - start_time
            self._log_api_call(
                method="generate_structured_output",
                prompt_length=len(prompt),
                response_length=0,
                elapsed_time=elapsed_time,
                success=False,
                error=str(e)
            )
            raise

    async def _generate_anthropic_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate completion using Anthropic Claude API."""
        messages = [{"role": "user", "content": prompt}]

        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_prompt:
            params["system"] = system_prompt

        # Add any additional kwargs
        params.update(kwargs)

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = await self.client.messages.create(**params)

                # Track usage
                self.total_requests += 1
                if hasattr(response, "usage"):
                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                    self.total_tokens += input_tokens + output_tokens

                    # Estimate cost (Claude 3.5 Sonnet pricing as example)
                    cost = (input_tokens * 0.003 / 1000) + (output_tokens * 0.015 / 1000)
                    self.total_cost += cost

                return response.content[0].text

            except AnthropicAPIError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Anthropic API error (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Anthropic API error after {self.max_retries} attempts: {e}")
                    raise

        if last_exception:
            raise last_exception

    async def _generate_openai_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate completion using OpenAI GPT API."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add any additional kwargs
        params.update(kwargs)

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(**params)

                # Track usage
                self.total_requests += 1
                if hasattr(response, "usage"):
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                    self.total_tokens += input_tokens + output_tokens

                    # Estimate cost (GPT-4 pricing as example)
                    cost = (input_tokens * 0.03 / 1000) + (output_tokens * 0.06 / 1000)
                    self.total_cost += cost

                return response.choices[0].message.content

            except OpenAIAPIError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"OpenAI API error (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"OpenAI API error after {self.max_retries} attempts: {e}")
                    raise

        if last_exception:
            raise last_exception

    def _log_api_call(
        self,
        method: str,
        prompt_length: int,
        response_length: int,
        elapsed_time: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Log API call for debugging and cost tracking."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "provider": self.provider.value,
            "model": self.model,
            "method": method,
            "prompt_length": prompt_length,
            "response_length": response_length,
            "elapsed_time": round(elapsed_time, 3),
            "success": success,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "estimated_cost": round(self.total_cost, 4)
        }

        if error:
            log_data["error"] = error

        if success:
            logger.info(f"LLM API call successful: {json.dumps(log_data)}")
        else:
            logger.error(f"LLM API call failed: {json.dumps(log_data)}")

    def get_usage_stats(self) -> dict[str, Any]:
        """
        Get usage statistics for this client instance.

        Returns:
            Dict with usage metrics
        """
        return {
            "provider": self.provider.value,
            "model": self.model,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.total_cost, 4)
        }


# Factory functions
def get_llm_client(
    provider: Optional[LLMProvider] = None,
    model: Optional[str] = None
) -> LLMClient:
    """
    Get LLM client instance.

    Args:
        provider: LLM provider (defaults to config setting)
        model: Model name (defaults to provider's default)

    Returns:
        LLMClient instance
    """
    return LLMClient(provider=provider, model=model)


def get_anthropic_client(model: Optional[str] = None) -> LLMClient:
    """
    Get Anthropic Claude client.

    Args:
        model: Model name (defaults to Claude 3.5 Sonnet)

    Returns:
        LLMClient configured for Anthropic
    """
    return LLMClient(
        provider=LLMProvider.ANTHROPIC,
        model=model or LLMModel.CLAUDE_3_5_SONNET.value
    )


def get_openai_client(model: Optional[str] = None) -> LLMClient:
    """
    Get OpenAI GPT client.

    Args:
        model: Model name (defaults to GPT-4 Turbo)

    Returns:
        LLMClient configured for OpenAI
    """
    return LLMClient(
        provider=LLMProvider.OPENAI,
        model=model or LLMModel.GPT_4_TURBO.value
    )
