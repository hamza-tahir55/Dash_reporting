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
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.model: str = os.getenv("OPENAI_MODEL", "gpt-4")
        self.temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
        self.max_tokens: int = int(os.getenv("MAX_TOKENS", "4000"))
        
    def validate(self) -> bool:
        """Validate that required configuration is present."""
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. Please set it in your .env file or environment variables."
            )
        return True
    
    def get_api_key(self) -> str:
        """Get the OpenAI API key."""
        self.validate()
        return self.openai_api_key


# Global config instance
config = Config()
