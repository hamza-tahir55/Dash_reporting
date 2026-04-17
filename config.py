"""
Configuration module for the presentation generator.
Handles environment variables and API settings.
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class for managing API keys and settings."""

    def __init__(self):
        # Provider: "openai" | "deepseek" | "groq"
        self.provider: str = os.getenv("AI_PROVIDER", "openai").lower()

        # OpenAI
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4")

        # DeepSeek
        self.deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

        # Groq (OpenAI-compatible, fast inference)
        self.groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
        self.groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

        # Common settings
        self.temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
        self.max_tokens: int = int(os.getenv("MAX_TOKENS", "4000"))

    def validate(self) -> bool:
        if self.provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY not found in environment.")
        elif self.provider == "deepseek":
            if not self.deepseek_api_key:
                raise ValueError("DEEPSEEK_API_KEY not found in environment.")
        elif self.provider == "groq":
            if not self.groq_api_key:
                raise ValueError("GROQ_API_KEY not found in environment.")
        else:
            raise ValueError(
                f"Invalid AI_PROVIDER: '{self.provider}'. Must be 'openai', 'deepseek', or 'groq'."
            )
        return True

    def get_api_key(self) -> str:
        self.validate()
        if self.provider == "openai":
            return self.openai_api_key
        if self.provider == "deepseek":
            return self.deepseek_api_key
        if self.provider == "groq":
            return self.groq_api_key

    def get_model(self) -> str:
        if self.provider == "openai":
            return self.openai_model
        if self.provider == "deepseek":
            return self.deepseek_model
        if self.provider == "groq":
            return self.groq_model

    def get_base_url(self) -> Optional[str]:
        if self.provider == "deepseek":
            return self.deepseek_base_url
        if self.provider == "groq":
            return self.groq_base_url
        return None  # OpenAI uses default SDK base URL


# Global config instance
config = Config()
