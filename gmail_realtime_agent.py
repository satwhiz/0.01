"""
Gmail Real-time Email Classification Agent - DeepSeek Only (FINAL FIX)
This agent classifies new incoming emails in real-time using DeepSeek AI.
ENHANCED: Now includes email drafting for "To Do" emails.
UPDATED: Uses separate system prompt files for better code structure.
"""

import sys
from typing import List, Dict, Any
from agno.agent import Agent
from agno.tools import tool
from agno.models.deepseek import DeepSeek
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
from prompts.classification_system_prompt import CLASSIFICATION_SYSTEM_PROMPT
from email_drafting_agent import create_draft_for_todo_email

def get_deepseek_model():
    """Get DeepSeek model with proper configuration"""
    return DeepSeek(
        id=config.DEFAULT_MODEL,
        api_key=config.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

class GmailRealtimeAgent:
    def __init__(self):
        self.service = None
        self.labels = config.LABELS
        self.label_ids = {}
        
    def initialize(self):
        """Initialize the agent with Gmail authentication"""
        if config.DEBUG:
            print("Initializing Gmail Real-time Agent with DeepSeek...")
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
                print(f"Available labels: {list(self.label_ids.keys())}")
                
        except Exception as e:
            print(f"Error loading labels: {e}")

# Global instance for tool functions
_realtime_agent_instance = None

def get_realtime_agent_instance():
    """Get the global agent instance"""
    global _realtime_agent_instance
    if _realtime_agent_instance is None:
        _realtime_agent_instance = GmailRealtimeAgent()
        _realtime_agent_instance.initialize()
    return _realtime_agent_instance

def _classify_single_email(message_id: str) -> str:
    """Internal function to classify a single email (not a tool)"""
    agent = get_realtime_agent_instance()
    
    if config.DEBUG:
        print(f"Starting DeepSeek AI classification for email: {message_id}")
    
    # Get the email
    if not agent.service:
        return "❌ Error: Gmail service not authenticated"
    
    try:
        email_data = agent.service.users().messages().get(userId='me', id=message_id).execute()
        if config.DEBUG:
            print(f"Retrieved email: {message_id}")
    except Exception as e:
        return f"❌ Error retrieving email {message_id}: {e}"
    
    # Get thread context
    thread_id = email_data.get('threadId')
    thread_messages = [email_data]
    
    if thread_id:
        try:
            thread = agent.service.users().threads().get(userId='me', id=thread_id).execute()
            thread_messages = thread.get('messages', [])
            thread_messages.sort(key=lambda x: int(x['internalDate']))
            if config.DEBUG:
                print(f"Retrieved {len(thread_messages)} messages from thread: {thread_id}")
        except Exception as e:
            if config.DEBUG:
                print(f"Error retrieving thread {thread_id}: {e}")
    
    # Get the last message in the thread (most recent)
    last_message = thread_messages[-1] if thread_messages else email_data
    
    # Extract email content
    email_content = extract_email_content(last_message)
    thread_content = format_thread_context(thread_messages) if len(thread_messages) > 1 else ""
    
    # Generate classification prompt
    classification_prompt = get_classification_prompt(email_content, thread_content)
    
    try:
        # Use DeepSeek to classify
        classifier_agent = Agent(
            model=get_deepseek_model(),
            instructions="You are an expert email classifier. Follow the rules precisely and return only the label name.",
            markdown=False
        )
        
        response = classifier_agent.run(classification_prompt)
        
        # Extract and validate label from response
        label = validate_label(response.content.strip())
        
        # Apply the label
        success = False
        if label in agent.label_ids:
            try:
                label_id = agent.label_ids[label]
                agent.service.users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={'addLabelIds': [label_id]}
                ).execute()
                success = True
                if config.DEBUG:
                    print(f"Applied label '{label}' to message {message_id}")
            except Exception as e:
                if config.DEBUG:
                    print(f"Error applying label {label} to message {message_id}: {e}")
        else:
            if config.DEBUG:
                print(f"Label '{label}' not found in available labels")
                print(f"Available labels: {list(agent.label_ids.keys())}")
        
        # Log the result
        log_classification(message_id, label, success)
        
        # Save detailed log if debug enabled
        if config.DEBUG:
            save_classification_log(message_id, label, email_content, success)
        
        # ✨ NEW FEATURE: Auto-draft email if classified as "To Do"
        result_message = ""
        if success:
            result_message = f"✅ Email `{message_id}` successfully classified as: **{label}** using DeepSeek AI"
            
            # Check if this email needs a draft (classified as "To Do")
            if label == "📋 To Do":
                print("\n" + "="*80)
                print("🎯 EMAIL CLASSIFIED AS 'TO DO' - GENERATING DRAFT...")
                print("="*80)
                
                try:
                    draft_content = create_draft_for_todo_email(message_id)
                    print(draft_content)
                    result_message += f"\n\n🎯 **Auto-Draft Generated**: Email draft has been created for this 'To Do' email (see above)."
                except Exception as e:
                    error_msg = f"⚠️ Draft generation failed: {e}"
                    print(f"\n{error_msg}")
                    result_message += f"\n\n{error_msg}"
        else:
            result_message = f"⚠️ Email `{message_id}` classified as: **{label}**, but failed to apply label (label may not exist)"
        
        return result_message
    
    except Exception as e:
        error_msg = f"❌ Error classifying email {message_id} with DeepSeek: {e}"
        if config.DEBUG:
            import traceback
            print(traceback.format_exc())
        return error_msg

@tool(
    name="classify_email_by_id",
    description="Classify a specific email using DeepSeek AI and create draft if it's 'To Do'",
    show_result=True
)
def classify_email_by_id(message_id: str) -> str:
    """Classify a specific email by its ID using DeepSeek AI"""
    return _classify_single_email(message_id)

@tool(
    name="classify_latest_email_tool",
    description="Find and classify the most recent email using DeepSeek AI and create draft if it's 'To Do'",
    show_result=True
)
def classify_latest_email_tool() -> str:
    """Find and classify the most recent email"""
    agent = get_realtime_agent_instance()
    
    if not agent.service:
        return "❌ Gmail service not authenticated"
    
    try:
        # Get the most recent email
        results = agent.service.users().messages().list(
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
        
        # Use the internal function to classify
        return _classify_single_email(latest_message_id)
        
    except Exception as e:
        error_msg = f"❌ Error finding latest email: {e}"
        if config.DEBUG:
            import traceback
            print(traceback.format_exc())
        return error_msg

@tool(
    name="classify_multiple_recent_emails",
    description="Get and classify multiple recent emails using DeepSeek AI and create drafts for 'To Do' emails",
    show_result=True
)
def classify_multiple_recent_emails(count: int = 5) -> str:
    """Classify multiple recent emails"""
    agent = get_realtime_agent_instance()
    
    if not agent.service:
        return "❌ Gmail service not authenticated"
    
    try:
        # Get recent emails
        results = agent.service.users().messages().list(
            userId='me', 
            q='in:inbox',
            maxResults=count
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return "📭 No emails found in inbox"
        
        summary = f"🔄 Classifying {len(messages)} recent emails using DeepSeek AI...\n\n"
        success_count = 0
        todo_draft_count = 0
        
        for i, message in enumerate(messages):
            message_id = message['id']
            try:
                # Use the internal function to classify
                result = _classify_single_email(message_id)
                if "successfully classified" in result:
                    success_count += 1
                if "Auto-Draft Generated" in result:
                    todo_draft_count += 1
                summary += f"{i+1}. {result}\n"
            except Exception as e:
                summary += f"{i+1}. ❌ Error processing {message_id}: {e}\n"
        
        summary += f"\n📊 **Summary:** {success_count}/{len(messages)} emails classified successfully by DeepSeek AI"
        if todo_draft_count > 0:
            summary += f"\n📝 **Drafts Generated:** {todo_draft_count} email drafts created for 'To Do' emails"
        
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
        # Initialize the agent instance
        agent_instance = get_realtime_agent_instance()
        
        # Create the Agno agent with tools
        agent = Agent(
            model=get_deepseek_model(),
            tools=[
                classify_email_by_id,
                classify_latest_email_tool, 
                classify_multiple_recent_emails
            ],
            show_tool_calls=config.DEBUG,
            markdown=True
        )
        
        if message_id:
            # Classify specific email
            print(f"🎯 Classifying specific email: {message_id} using DeepSeek AI")
            print("📝 Auto-draft will be generated if email is classified as 'To Do'\n")
            agent.print_response(
                f"Please classify the email with ID: {message_id}",
                stream=True
            )
        elif count:
            # Classify multiple recent emails
            print(f"📬 Classifying {count} recent emails using DeepSeek AI...")
            print("📝 Auto-drafts will be generated for any emails classified as 'To Do'\n")
            agent.print_response(
                f"Please classify the {count} most recent emails in the inbox using DeepSeek AI.",
                stream=True
            )
        else:
            # Classify latest email
            print("📧 Finding and classifying the most recent email using DeepSeek AI...")
            print("📝 Auto-draft will be generated if email is classified as 'To Do'\n")
            agent.print_response(
                "Please find and classify the most recent email in the inbox using DeepSeek AI.",
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
    
    parser = argparse.ArgumentParser(description='Gmail Real-time Email Classification Agent with DeepSeek AI + Auto-Drafting')
    parser.add_argument('message_id', nargs='?', help='Specific email message ID to classify')
    parser.add_argument('--count', '-c', type=int, help='Number of recent emails to classify')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Override debug setting if specified
    if args.debug:
        config.DEBUG = True
        config.VERBOSE_LOGGING = True
    
    print("🚀 Gmail Real-time Classification + Auto-Drafting Agent")
    print("📝 Automatic email drafts will be generated for 'To Do' emails")
    print("=" * 80)
    
    if args.message_id:
        create_realtime_agent(message_id=args.message_id)
    elif args.count:
        create_realtime_agent(count=args.count)
    else:
        create_realtime_agent()

if __name__ == "__main__":
    main()