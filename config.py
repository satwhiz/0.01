"""
Configuration settings for Gmail Email Classification System
"""
import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for Gmail classification agents"""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-4")
    
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
        "🗑️ Junk",  # Using "Junk" with emoji instead of "Spam"
        "📚 History"
    ]
    
    # Gmail's accepted color palette (based on your suggestions)
    LABEL_COLORS: Dict[str, Dict[str, str]] = {
        "⏳ Awaiting Reply": {
            "backgroundColor": "#76a5af",  # Cool teal
            "textColor": "#000000"
        },
        "✅ Done": {
            "backgroundColor": "#93c47d",  # Greenish tone
            "textColor": "#000000"
        },
        "📄 FYI": {
            "backgroundColor": "#6fa8dc",  # Blue, matches info purpose
            "textColor": "#000000"
        },
        "📋 To Do": {
            "backgroundColor": "#f6b26b",  # Orange-ish, like a task color
            "textColor": "#000000"
        },
        "📚 History": {
            "backgroundColor": "#cccccc",  # Neutral, subdued
            "textColor": "#000000"
        },
        "🗑️ Junk": {
            "backgroundColor": "#e06666",  # Red-tinted, alerts attention
            "textColor": "#000000"
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
        if not cls.OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY not set in environment variables")
            return False
        
        if not os.path.exists(cls.GMAIL_CREDENTIALS_FILE):
            print(f"Warning: Gmail credentials file not found: {cls.GMAIL_CREDENTIALS_FILE}")
            return False
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration (excluding sensitive info)"""
        print("Gmail Classification System Configuration:")
        print(f"  Model: {cls.DEFAULT_MODEL}")
        print(f"  History Days: {cls.HISTORY_DAYS}")
        print(f"  Labels: {cls.LABELS}")
        print(f"  Debug Mode: {cls.DEBUG}")
        print(f"  Credentials File: {cls.GMAIL_CREDENTIALS_FILE}")
        print(f"  Token File: {cls.GMAIL_TOKEN_FILE}")

# Create global config instance
config = Config()