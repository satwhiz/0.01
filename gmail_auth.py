"""
Gmail Authentication Module
Handles OAuth2 authentication for Gmail API access
"""
import os
from typing import Optional
from googleapiclient.discovery import build, Resource
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from config import config

class GmailAuthenticator:
    """Handles Gmail API authentication"""
    
    def __init__(self):
        self.credentials: Optional[Credentials] = None
        self.service: Optional[Resource] = None
    
    def authenticate(self) -> Resource:
        """
        Authenticate with Gmail API and return service object
        
        Returns:
            Gmail service object for API calls
        """
        # Load existing credentials
        if os.path.exists(config.GMAIL_TOKEN_FILE):
            self.credentials = Credentials.from_authorized_user_file(
                config.GMAIL_TOKEN_FILE, 
                config.GMAIL_SCOPES
            )
        
        # If credentials are invalid or don't exist, get new ones
        if not self.credentials or not self.credentials.valid:
            if (self.credentials and 
                self.credentials.expired and 
                self.credentials.refresh_token):
                try:
                    self.credentials.refresh(Request())
                    if config.DEBUG:
                        print("Refreshed existing credentials")
                except Exception as e:
                    if config.DEBUG:
                        print(f"Failed to refresh credentials: {e}")
                    self.credentials = None
            
            # Get new credentials if refresh failed or no credentials exist
            if not self.credentials or not self.credentials.valid:
                if not os.path.exists(config.GMAIL_CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {config.GMAIL_CREDENTIALS_FILE}\n"
                        "Please download it from Google Cloud Console"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GMAIL_CREDENTIALS_FILE, 
                    config.GMAIL_SCOPES
                )
                self.credentials = flow.run_local_server(port=0)
                if config.DEBUG:
                    print("Obtained new credentials")
            
            # Save credentials for future use
            with open(config.GMAIL_TOKEN_FILE, 'w') as token:
                token.write(self.credentials.to_json())
                if config.DEBUG:
                    print(f"Saved credentials to {config.GMAIL_TOKEN_FILE}")
        
        # Build and return Gmail service
        self.service = build('gmail', 'v1', credentials=self.credentials)
        if config.DEBUG:
            print("Gmail service authenticated successfully")
        
        return self.service
    
    def get_service(self) -> Resource:
        """
        Get Gmail service object (authenticate if needed)
        
        Returns:
            Gmail service object
        """
        if not self.service:
            return self.authenticate()
        return self.service
    
    def test_connection(self) -> bool:
        """
        Test Gmail API connection
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            service = self.get_service()
            # Try a simple API call
            profile = service.users().getProfile(userId='me').execute()
            if config.DEBUG:
                print(f"Connected to Gmail for: {profile.get('emailAddress')}")
            return True
        except Exception as e:
            if config.DEBUG:
                print(f"Gmail connection test failed: {e}")
            return False
    
    def revoke_credentials(self):
        """Revoke stored credentials (for logout)"""
        if os.path.exists(config.GMAIL_TOKEN_FILE):
            os.remove(config.GMAIL_TOKEN_FILE)
            if config.DEBUG:
                print("Credentials revoked and token file deleted")
        
        self.credentials = None
        self.service = None

# Global authenticator instance
gmail_auth = GmailAuthenticator()