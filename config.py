"""
Configuration settings for Gmail Email Classification System - SIMPLE FIXED VERSION
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
    
    # SIMPLIFIED: Use simple labels without emojis for now (to avoid confusion)
    DEFAULT_LABELS: List[str] = [
        "To Do",
        "Awaiting Reply", 
        "FYI",
        "Done",
        "Spam",  # FIXED: Consistent with AI output
        "History"
    ]
    
    # Label colors for Gmail (we'll add these later when emoji issue is resolved)
    LABEL_COLORS: Dict[str, Dict[str, str]] = {
        "To Do": {
            "backgroundColor": "#fb4c2f",  # Red
            "textColor": "#ffffff"
        },
        "Awaiting Reply": {
            "backgroundColor": "#ffad47",  # Orange  
            "textColor": "#ffffff"
        },
        "FYI": {
            "backgroundColor": "#42d692",  # Green
            "textColor": "#ffffff"
        },
        "Done": {
            "backgroundColor": "#16a766",  # Dark Green
            "textColor": "#ffffff"
        },
        "Spam": {
            "backgroundColor": "#8e24aa",  # Purple
            "textColor": "#ffffff"
        },
        "History": {
            "backgroundColor": "#a4a4a4",  # Gray
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