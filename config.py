"""
Configuration settings for Gmail Email Classification System - DeepSeek Only
FIXED: Using Gmail-approved colors only
"""
import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for Gmail classification agents"""
    
    # DeepSeek API Configuration
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "deepseek-chat")
    
    # Gmail API Configuration
    GMAIL_CREDENTIALS_FILE: str = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    GMAIL_TOKEN_FILE: str = os.getenv("GMAIL_TOKEN_FILE", "token.json")
    GMAIL_SCOPES: List[str] = ['https://www.googleapis.com/auth/gmail.modify']
    
    # Classification Settings
    HISTORY_DAYS: int = int(os.getenv("HISTORY_DAYS", "10"))
    
    # Email Classification Labels with emojis
    DEFAULT_LABELS: List[str] = [
        "📋 To Do",
        "⏳ Awaiting Reply", 
        "📄 FYI",
        "✅ Done",
        "🗑️ Junk",
        "📚 History"
    ]
    
    # Gmail's OFFICIALLY APPROVED color palette only!
    # Source: https://developers.google.com/gmail/api/v1/reference/users/labels
    LABEL_COLORS: Dict[str, Dict[str, str]] = {
        "⏳ Awaiting Reply": {
            "backgroundColor": "#4a86e8",  # Gmail blue - official color
            "textColor": "#ffffff"
        },
        "✅ Done": {
            "backgroundColor": "#16a766",  # Gmail green - official color
            "textColor": "#ffffff"
        },
        "📄 FYI": {
            "backgroundColor": "#6d9eeb",  # Gmail light blue - official color
            "textColor": "#ffffff"
        },
        "📋 To Do": {
            "backgroundColor": "#ffad47",  # Gmail orange - official color
            "textColor": "#000000"
        },
        "📚 History": {
            "backgroundColor": "#cccccc",  # Gmail gray - official color
            "textColor": "#000000"
        },
        "🗑️ Junk": {
            "backgroundColor": "#cc3a21",  # Gmail red - official color
            "textColor": "#ffffff"
        }
    }
    
    # Custom labels from environment (if provided)
    CUSTOM_LABELS: List[str] = []
    if os.getenv("CUSTOM_LABELS"):
        CUSTOM_LABELS = [label.strip() for label in os.getenv("CUSTOM_LABELS", "").split(",")]
    
    # Use custom labels if provided, otherwise use default
    LABELS: List[str] = CUSTOM_LABELS if CUSTOM_LABELS else DEFAULT_LABELS
    
    # Debug and Logging
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    VERBOSE_LOGGING: bool = os.getenv("VERBOSE_LOGGING", "False").lower() == "true"
    
    # Validation
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings"""
        if not cls.DEEPSEEK_API_KEY:
            print("Warning: DEEPSEEK_API_KEY not set in environment variables")
            return False
        
        if not os.path.exists(cls.GMAIL_CREDENTIALS_FILE):
            print(f"Warning: Gmail credentials file not found: {cls.GMAIL_CREDENTIALS_FILE}")
            return False
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration (excluding sensitive info)"""
        print("Gmail Classification System Configuration:")
        print(f"  AI Provider: DeepSeek")
        print(f"  Model: {cls.DEFAULT_MODEL}")
        print(f"  History Days: {cls.HISTORY_DAYS}")
        print(f"  Labels: {cls.LABELS}")
        print(f"  Debug Mode: {cls.DEBUG}")
        print(f"  Credentials File: {cls.GMAIL_CREDENTIALS_FILE}")
        print(f"  Token File: {cls.GMAIL_TOKEN_FILE}")
        
        # Show API key (masked)
        if cls.DEEPSEEK_API_KEY:
            print(f"  DeepSeek API Key: sk-...{cls.DEEPSEEK_API_KEY[-8:]}")

# Create global config instance
config = Config()