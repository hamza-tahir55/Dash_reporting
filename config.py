"""
Configuration module for the presentation generator.
Handles environment variables and API settings.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for managing API keys and settings."""
    
    def __init__(self):
        # Provider selection
        self.provider: str = os.getenv("AI_PROVIDER", "openai").lower()  # "openai" or "deepseek"
        
        # OpenAI Configuration
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4")
        
        # DeepSeek Configuration
        self.deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        
        # Common settings
        self.temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
        self.max_tokens: int = int(os.getenv("MAX_TOKENS", "4000"))
        
    def validate(self) -> bool:
        """Validate that required configuration is present."""
        if self.provider == "openai":
            if not self.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY not found. Please set it in your .env file or environment variables."
                )
        elif self.provider == "deepseek":
            if not self.deepseek_api_key:
                raise ValueError(
                    "DEEPSEEK_API_KEY not found. Please set it in your .env file or environment variables."
                )
        else:
            raise ValueError(
                f"Invalid AI_PROVIDER: {self.provider}. Must be 'openai' or 'deepseek'"
            )
        return True
    
    def get_api_key(self) -> str:
        """Get the appropriate API key based on provider."""
        self.validate()
        if self.provider == "openai":
            return self.openai_api_key
        elif self.provider == "deepseek":
            return self.deepseek_api_key
    
    def get_model(self) -> str:
        """Get the appropriate model based on provider."""
        if self.provider == "openai":
            return self.openai_model
        elif self.provider == "deepseek":
            return self.deepseek_model
    
    def get_base_url(self) -> Optional[str]:
        """Get the base URL for the API (None for OpenAI, custom for DeepSeek)."""
        if self.provider == "deepseek":
            return self.deepseek_base_url
        return None


# Global config instance
config = Config()
