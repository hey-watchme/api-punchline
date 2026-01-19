"""
LLM Provider abstraction layer for PUNCHLINE API

Unified interface for multiple LLM providers (OpenAI, Groq).
Provider switching can be done by changing the constants at the top of this file.
"""

from abc import ABC, abstractmethod
from typing import Optional
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ==========================================
# LLM Provider Configuration
# ==========================================
# Change this line to switch providers
CURRENT_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "groq"
CURRENT_MODEL = os.getenv("LLM_MODEL", "gpt-5-nano")
# Settings for Groq reasoning models (only used for models starting with "openai/")
CURRENT_REASONING_EFFORT = "medium"  # "low", "medium", "high"
CURRENT_MAX_COMPLETION_TOKENS = 8192
# ==========================================


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate response from prompt

        Args:
            prompt (str): Input prompt

        Returns:
            str: LLM response text
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name being used (including provider name)"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API Provider"""

    def __init__(self, model: str = "gpt-4o"):
        """
        Args:
            model (str): OpenAI model name
                e.g.: "gpt-4o", "gpt-4o-mini", "gpt-5-nano", "o1-preview"
        """
        from openai import OpenAI  # Lazy import

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=api_key)
        self._model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def generate(self, prompt: str) -> str:
        """Call OpenAI API to generate text (with retry)"""
        try:
            response = self.client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content

        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            raise

    @property
    def model_name(self) -> str:
        return f"openai/{self._model}"


class GroqProvider(LLMProvider):
    """Groq API Provider"""

    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        reasoning_effort: Optional[str] = None,
        max_completion_tokens: int = 8192
    ):
        """
        Args:
            model (str): Groq model name
                e.g.: "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-120b"
            reasoning_effort (str, optional): Parameter for reasoning models ("low", "medium", "high")
                Used for reasoning models like openai/gpt-oss-120b
            max_completion_tokens (int): Maximum output tokens (default: 8192)
        """
        from groq import Groq  # Lazy import

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")

        self.client = Groq(api_key=api_key)
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._max_completion_tokens = max_completion_tokens

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def generate(self, prompt: str) -> str:
        """Call Groq API to generate text (with retry)"""
        try:
            # Base parameters
            params = {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "max_completion_tokens": self._max_completion_tokens,
                "temperature": 1,
                "top_p": 1
            }

            # Add reasoning model parameters (for models starting with "openai/")
            if self._model.startswith("openai/") and self._reasoning_effort:
                params["reasoning_effort"] = self._reasoning_effort

            response = self.client.chat.completions.create(**params)
            return response.choices[0].message.content

        except Exception as e:
            print(f"Error calling Groq API: {e}")
            raise

    @property
    def model_name(self) -> str:
        return f"groq/{self._model}"


class LLMFactory:
    """Factory class for LLM providers"""

    @staticmethod
    def create(provider: str, model: Optional[str] = None) -> LLMProvider:
        """
        Create LLMProvider instance with specified provider and model

        Args:
            provider (str): Provider name ("openai", "groq")
            model (str, optional): Model name. Uses default if None

        Returns:
            LLMProvider: Instance of specified provider

        Raises:
            ValueError: If unknown provider name is specified
        """
        provider = provider.lower()

        if provider == "openai":
            default_model = "gpt-4o"
            return OpenAIProvider(model or default_model)

        elif provider == "groq":
            default_model = "llama-3.3-70b-versatile"
            return GroqProvider(model or default_model)

        else:
            raise ValueError(
                f"Unknown provider: {provider}\n"
                f"Supported providers: openai, groq"
            )

    @staticmethod
    def get_current() -> LLMProvider:
        """
        Get currently configured LLM provider

        Uses CURRENT_PROVIDER and CURRENT_MODEL constants at the top of this file

        Returns:
            LLMProvider: Current provider instance
        """
        print(f"Using LLM provider: {CURRENT_PROVIDER}/{CURRENT_MODEL}")

        if CURRENT_PROVIDER.lower() == "groq":
            # For Groq provider, pass reasoning model parameters too
            return GroqProvider(
                model=CURRENT_MODEL,
                reasoning_effort=CURRENT_REASONING_EFFORT if CURRENT_MODEL.startswith("openai/") else None,
                max_completion_tokens=CURRENT_MAX_COMPLETION_TOKENS
            )
        else:
            # For OpenAI and other providers
            return LLMFactory.create(CURRENT_PROVIDER, CURRENT_MODEL)


# Convenience function: Get current LLM
def get_current_llm() -> LLMProvider:
    """Get currently configured LLM provider (alias)"""
    return LLMFactory.get_current()