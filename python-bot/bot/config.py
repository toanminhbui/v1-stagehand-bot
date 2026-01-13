"""
Configuration management for the Marketing Link Verifier bot.
Loads and validates environment variables on startup.
"""

import os
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator
from typing import Optional


# Load .env file if present
load_dotenv()


class Config(BaseModel):
    """Application configuration loaded from environment variables."""
    
    # Slack configuration
    slack_bot_token: str
    slack_signing_secret: str
    slack_app_token: str  # Required for Socket Mode
    
    # Browserbase / Stagehand configuration
    browserbase_api_key: str
    browserbase_project_id: str
    
    # Optional: OpenAI API key for Stagehand
    openai_api_key: Optional[str] = None
    
    @field_validator("slack_bot_token")
    @classmethod
    def validate_slack_bot_token(cls, v: str) -> str:
        if not v.startswith("xoxb-"):
            raise ValueError("SLACK_BOT_TOKEN must start with 'xoxb-'")
        return v
    
    @field_validator("slack_app_token")
    @classmethod
    def validate_slack_app_token(cls, v: str) -> str:
        if not v.startswith("xapp-"):
            raise ValueError("SLACK_APP_TOKEN must start with 'xapp-'")
        return v


def load_config() -> Config:
    """
    Load configuration from environment variables.
    Raises ValueError if required variables are missing or invalid.
    """
    try:
        return Config(
            slack_bot_token=os.environ.get("SLACK_BOT_TOKEN", ""),
            slack_signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""),
            slack_app_token=os.environ.get("SLACK_APP_TOKEN", ""),
            browserbase_api_key=os.environ.get("BROWSERBASE_API_KEY", ""),
            browserbase_project_id=os.environ.get("BROWSERBASE_PROJECT_ID", ""),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
        )
    except Exception as e:
        raise ValueError(f"Configuration error: {e}")


# Global config instance (lazy-loaded)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config

