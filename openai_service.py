"""
AI service module for handling API interactions with multiple providers.
Supports OpenAI and DeepSeek with easy switching.
"""
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from config import config


class AIService:
    """Service class for interacting with AI APIs (OpenAI, DeepSeek, etc.)."""

    def __init__(self):
        """Initialize the AI client based on configured provider."""
        config.validate()
        self.provider = config.provider
        self.model = config.get_model()
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens

        if self.provider == "openai":
            self.client = OpenAI(api_key=config.get_api_key())
            print(f"🤖 Initialized OpenAI client with model: {self.model}")
        elif self.provider in ("deepseek", "groq"):
            self.client = OpenAI(
                api_key=config.get_api_key(),
                base_url=config.get_base_url()
            )
            icon = "🧠" if self.provider == "deepseek" else "⚡"
            print(f"{icon} Initialized {self.provider.title()} client with model: {self.model}")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """
        Generate a completion using the configured AI provider.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Override temperature (None uses config value; 0 is valid).
            max_tokens: Override max_tokens.
            json_mode: If True, enforce JSON output via response_format.

        Returns:
            Generated text response.
        """
        try:
            # Fix: use explicit None check so temperature=0 is honoured
            resolved_temp = temperature if temperature is not None else self.temperature

            params: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": resolved_temp,
            }

            if max_tokens or self.max_tokens:
                params["max_tokens"] = max_tokens if max_tokens is not None else self.max_tokens

            if json_mode:
                params["response_format"] = {"type": "json_object"}

            start_time = time.time()
            print(f"🔄 Generating completion with {self.provider} ({self.model})...")

            response = self.client.chat.completions.create(**params)

            elapsed = time.time() - start_time

            if hasattr(response, "usage") and response.usage:
                print(
                    f"📊 Token usage: {response.usage.prompt_tokens} in + "
                    f"{response.usage.completion_tokens} out = {response.usage.total_tokens} total"
                )
                print(
                    f"⚡ Response time: {elapsed:.2f}s "
                    f"({response.usage.total_tokens / elapsed:.0f} tokens/sec)"
                )
            else:
                print(f"⚡ Response time: {elapsed:.2f}s")

            return response.choices[0].message.content

        except Exception as e:
            print(f"❌ Error with {self.provider}: {str(e)}")
            raise Exception(f"Error generating completion with {self.provider}: {str(e)}")
