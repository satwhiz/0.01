"""
Gmail Real-time Email Classification Agent
This agent classifies new incoming emails in real-time.
"""

import sys
from typing import List, Dict, Any
from agno.agent import Agent
from agno.tools import tool
from agno.models.openai import OpenAIChat
from config import config
from gmail_auth import gmail_auth
from utils import (
    extract_email_content, 
    format_thread_context,
    get_classification_prompt,
    validate_label,
    log_classification,
    save_classification_log
)

class GmailRealtimeAgent:
    def __init__(self):
        self.service = None
        self.labels = config.LABELS
        self.label_ids = {}
        
    def initialize(self):
        """Initialize the agent with Gmail authentication"""
        if config.DEBUG:
            print("Initializing Gmail Real-time Agent...")
            config.print_config()
        
        # Validate configuration
        if not config.validate():
            raise ValueError("Invalid configuration. Please check your settings.")
        
        # Authenticate with Gmail
        self.service = gmail_auth.authenticate()
        self._load_label_ids()
        
        if config.DEBUG:
            print("Gmail authentication successful")
    
    def _load_label_ids(self):
        """Load existing label IDs"""
        if not self.service:
            return
        
        try:
            results = self.service.users().labels().list(userId='me').execute()
            all_labels = {label['name']: label['id'] for label in results.get('labels', [])}
            
            # Only keep labels that exist in our config
            self.label_ids = {name: id for name, id in all_labels.items() if name in self.labels}
            
            if config.DEBUG:
                print(f"Loaded {len(self.label_ids)} classification labels")
                
        except Exception as e:
            print(f"Error loading labels: {e}")
    
    @tool(
        name="get_email_by_id",
        description="Retrieve a specific email by ID",
        show_result=False
    )
    def get_email_by_id(self, message_id: str) -> Dict:
        """Retrieve a specific email by its ID"""
        if not self.service:
            return {}
        
        try:
            message = self.service.users().messages().get(userId='me', id=message_id).execute()
            if config.DEBUG:
                print(f"Retrieved email: {message_id}")
            return message
        except Exception as e:
            print(f"Error retrieving email {message_id}: {e}")
            return {}
    
    @tool(
        name="get_thread_messages",
        description="Get all messages in a thread",
        show_result=False
    )
    def get_thread_messages(self, thread_id: str) -> List[Dict]:
        """Get all messages in a thread for context"""
        if not self.service:
            return []
        
        try:
            thread = self.service.users().threads().get(userId='me', id=thread_id).execute()
            messages = thread.get('messages', [])
            
            # Sort messages by date
            messages.sort(key=lambda x: int(x['internalDate']))
            
            if config.DEBUG:
                print(f"Retrieved {len(messages)} messages from thread: {thread_id}")
                
            return messages
        except Exception as e:
            print(f"Error retrieving thread {thread_id}: {e}")
            return []
    
    @tool(
        name="classify_new_email",
        description="Classify a new email based on content and thread context",
        show_result=True
    )
    def classify_new_email(self, message_id: str) -> str:
        """
        Classify a new email based on the classification rules.
        
        Args:
            message_id: ID of the email to classify
            
        Returns:
            str: The label assigned and classification result
        """
        
        if config.DEBUG:
            print(f"Starting classification for email: {message_id}")
        
        # Get the email
        email_data = self.get_email_by_id(message_id)
        if not email_data:
            return "❌ Error: Could not retrieve email"
        
        # Get thread context
        thread_id = email_data.get('threadId')
        thread_messages = self.get_thread_messages(thread_id) if thread_id else [email_data]
        
        # Get the last message in the thread (most recent)
        last_message = thread_messages[-1] if thread_messages else email_data
        
        # Extract email content
        email_content = extract_email_content(last_message)
        thread_content = format_thread_context(thread_messages) if len(thread_messages) > 1 else ""
        
        # Generate classification prompt
        classification_prompt = get_classification_prompt(email_content, thread_content)
        
        try:
            # Use the agent to classify
            classifier_agent = Agent(
                model=OpenAIChat(id=config.DEFAULT_MODEL),
                system_prompt="You are an expert email classifier. Follow the rules precisely and return only the label name.",
                markdown=False
            )
            
            response = classifier_agent.run(classification_prompt)
            
            # Extract and validate label from response
            label = validate_label(response.content.strip())
            
            # Apply the label
            success = self.apply_label(message_id, label)
            
            # Log the result
            log_classification(message_id, label, success)
            
            # Save detailed log if debug enabled
            if config.DEBUG:
                save_classification_log(message_id, label, email_content, success)
            
            if success:
                return f"✅ Email `{message_id}` successfully classified as: **{label}**"
            else:
                return f"⚠️ Email `{message_id}` classified as: **{label}**, but failed to apply label (label may not exist)"
        
        except Exception as e:
            error_msg = f"❌ Error classifying email {message_id}: {e}"
            if config.DEBUG:
                import traceback
                print(traceback.format_exc())
            return error_msg
    
    @tool(
        name="apply_label_to_email",
        description="Apply a label to an email",
        show_result=False
    )
    def apply_label(self, message_id: str, label_name: str) -> bool:
        """Apply a label to an email"""
        if not self.service or label_name not in self.label_ids:
            if config.DEBUG:
                print(f"Cannot apply label {label_name}: service={bool(self.service)}, label_exists={label_name in self.label_ids}")
                if label_name not in self.label_ids:
                    print(f"Available labels: {list(self.label_ids.keys())}")
            return False
        
        try:
            label_id = self.label_ids[label_name]
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            if config.DEBUG:
                print(f"Applied label '{label_name}' to message {message_id}")
            return True
            
        except Exception as e:
            if config.DEBUG:
                print(f"Error applying label {label_name} to message {message_id}: {e}")
            return False
    
    @tool(
        name="classify_latest_email",
        description="Find and classify the most recent email",
        show_result=True
    )
    def classify_latest_email(self) -> str:
        """Find and classify the most recent email"""
        if not self.service:
            return "❌ Gmail service not authenticated"
        
        try:
            # Get the most recent email
            results = self.service.users().messages().list(
                userId='me', 
                q='in:inbox',
                maxResults=1
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                return "📭 No emails found in inbox"
            
            latest_message_id = messages[0]['id']
            
            if config.DEBUG:
                print(f"Found latest email: {latest_message_id}")
            
            return self.classify_new_email(latest_message_id)
            
        except Exception as e:
            error_msg = f"❌ Error finding latest email: {e}"
            if config.DEBUG:
                import traceback
                print(traceback.format_exc())
            return error_msg
    
    @tool(
        name="get_recent_emails",
        description="Get and classify multiple recent emails",
        show_result=True
    )
    def classify_recent_emails(self, count: int = 5) -> str:
        """Classify multiple recent emails"""
        if not self.service:
            return "❌ Gmail service not authenticated"
        
        try:
            # Get recent emails
            results = self.service.users().messages().list(
                userId='me', 
                q='in:inbox',
                maxResults=count
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                return "📭 No emails found in inbox"
            
            summary = f"🔄 Classifying {len(messages)} recent emails...\n\n"
            success_count = 0
            
            for i, message in enumerate(messages):
                message_id = message['id']
                try:
                    result = self.classify_new_email(message_id)
                    if "successfully classified" in result:
                        success_count += 1
                    summary += f"{i+1}. {result}\n"
                except Exception as e:
                    summary += f"{i+1}. ❌ Error processing {message_id}: {e}\n"
            
            summary += f"\n📊 **Summary:** {success_count}/{len(messages)} emails classified successfully"
            return summary
            
        except Exception as e:
            error_msg = f"❌ Error processing recent emails: {e}"
            if config.DEBUG:
                import traceback
                print(traceback.format_exc())
            return error_msg

def create_realtime_agent(message_id: str = None, count: int = None):
    """Create and run the real-time classification agent"""
    
    try:
        # Initialize the agent
        realtime_agent = GmailRealtimeAgent()
        realtime_agent.initialize()
        
        # Create the Agno agent with tools
        agent = Agent(
            model=OpenAIChat(id=config.DEFAULT_MODEL),
            tools=[
                realtime_agent.classify_new_email,
                realtime_agent.classify_latest_email,
                realtime_agent.classify_recent_emails
            ],
            show_tool_calls=config.DEBUG,
            markdown=True
        )
        
        if message_id:
            # Classify specific email
            print(f"🎯 Classifying specific email: {message_id}")
            agent.print_response(
                f"Please classify the email with ID: {message_id}",
                stream=True
            )
        elif count:
            # Classify multiple recent emails
            print(f"📬 Classifying {count} recent emails...")
            agent.print_response(
                f"Please classify the {count} most recent emails in the inbox.",
                stream=True
            )
        else:
            # Classify latest email
            print("📧 Finding and classifying the most recent email...")
            agent.print_response(
                "Please find and classify the most recent email in the inbox.",
                stream=True
            )
    
    except Exception as e:
        print(f"❌ Error starting real-time agent: {e}")
        if config.DEBUG:
            import traceback
            traceback.print_exc()

def main():
    """Main function for real-time email classification"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gmail Real-time Email Classification Agent')
    parser.add_argument('message_id', nargs='?', help='Specific email message ID to classify')
    parser.add_argument('--count', '-c', type=int, help='Number of recent emails to classify')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Override debug setting if specified
    if args.debug:
        config.DEBUG = True
        config.VERBOSE_LOGGING = True
    
    if args.message_id:
        create_realtime_agent(message_id=args.message_id)
    elif args.count:
        create_realtime_agent(count=args.count)
    else:
        create_realtime_agent()

if __name__ == "__main__":
    main()