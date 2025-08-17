"""
Email Drafting Agent - DeepSeek Only
This agent creates email drafts for emails classified as "To Do" using DeepSeek AI.
"""

import sys
from typing import List, Dict, Any
from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from config import config
from gmail_auth import gmail_auth
from utils import extract_email_content, format_thread_context
from prompts.drafting_system_prompt import DRAFTING_SYSTEM_PROMPT

def get_deepseek_model():
    """Get DeepSeek model with proper configuration"""
    return DeepSeek(
        id=config.DEFAULT_MODEL,
        api_key=config.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

class EmailDraftingAgent:
    def __init__(self):
        self.service = None
        
    def initialize(self):
        """Initialize the agent with Gmail authentication"""
        if config.DEBUG:
            print("Initializing Email Drafting Agent with DeepSeek...")
        
        # Validate configuration
        if not config.validate():
            raise ValueError("Invalid configuration. Please check your settings.")
        
        # Authenticate with Gmail
        self.service = gmail_auth.authenticate()
        
        if config.DEBUG:
            print("Gmail authentication successful for drafting agent")
    
    def get_drafting_prompt(self, latest_email_content: str, thread_context: str = "") -> str:
        """
        Generate the email drafting prompt for the AI model
        
        Args:
            latest_email_content: Content of the latest email that needs a response
            thread_context: Context from the full email thread
            
        Returns:
            Formatted prompt for email drafting
        """
        prompt = DRAFTING_SYSTEM_PROMPT + "\n\n"
        
        prompt += "**LATEST EMAIL TO RESPOND TO:**\n"
        prompt += latest_email_content + "\n\n"
        
        if thread_context:
            prompt += thread_context + "\n\n"
        
        prompt += "**IMPORTANT:** Focus your draft primarily on responding to the LATEST email above. Use thread context only for background understanding.\n\n"
        prompt += "Draft Response:"
        
        return prompt

    def draft_email_reply(self, message_id: str) -> str:
        """
        Create a draft reply for the given email message
        
        Args:
            message_id: Gmail message ID that was classified as "To Do"
            
        Returns:
            Draft email content or error message
        """
        if not self.service:
            self.initialize()
        
        try:
            if config.DEBUG:
                print(f"📝 Creating draft for email: {message_id}")
            
            # Get the email
            email_data = self.service.users().messages().get(userId='me', id=message_id).execute()
            
            # Get thread context
            thread_id = email_data.get('threadId')
            thread_messages = [email_data]
            
            if thread_id:
                try:
                    thread = self.service.users().threads().get(userId='me', id=thread_id).execute()
                    thread_messages = thread.get('messages', [])
                    thread_messages.sort(key=lambda x: int(x['internalDate']))
                    if config.DEBUG:
                        print(f"Retrieved {len(thread_messages)} messages from thread: {thread_id}")
                except Exception as e:
                    if config.DEBUG:
                        print(f"Error retrieving thread {thread_id}: {e}")
            
            # Get the latest message (the one we need to respond to)
            latest_message = thread_messages[-1] if thread_messages else email_data
            
            # Extract content
            latest_email_content = extract_email_content(latest_message)
            thread_context = format_thread_context(thread_messages) if len(thread_messages) > 1 else ""
            
            # Generate drafting prompt
            drafting_prompt = self.get_drafting_prompt(latest_email_content, thread_context)
            
            if config.DEBUG:
                print("🤖 Generating email draft with DeepSeek AI...")
            
            # Use DeepSeek to generate draft
            drafting_agent = Agent(
                model=get_deepseek_model(),
                instructions=DRAFTING_SYSTEM_PROMPT,
                markdown=False
            )
            
            response = drafting_agent.run(drafting_prompt)
            draft_content = response.content.strip()
            
            # Extract subject from original email for context
            headers = latest_message.get('payload', {}).get('headers', [])
            original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            original_from = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            
            # Format the draft output
            draft_output = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           📧 EMAIL DRAFT GENERATED                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

📌 **Original Email Context:**
   • From: {original_from}
   • Subject: {original_subject}
   • Message ID: {message_id}
   • Thread Messages: {len(thread_messages)}

📝 **Generated Draft Reply:**
{'-' * 80}
{draft_content}
{'-' * 80}

💡 **Next Steps:**
   1. Review the draft above
   2. Fill in any placeholders [like this] with actual information
   3. Make any necessary edits
   4. Copy and send the email manually (or integrate with Gmail API for auto-drafting)

🤖 **Generated by:** Fyxer AI (DeepSeek)
⏰ **Generated at:** {self._get_current_timestamp()}
"""
            
            return draft_output
            
        except Exception as e:
            error_msg = f"❌ Error creating email draft for {message_id}: {e}"
            if config.DEBUG:
                import traceback
                print(traceback.format_exc())
            return error_msg
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for draft metadata"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Global instance
_drafting_agent_instance = None

def get_drafting_agent_instance():
    """Get the global drafting agent instance"""
    global _drafting_agent_instance
    if _drafting_agent_instance is None:
        _drafting_agent_instance = EmailDraftingAgent()
        _drafting_agent_instance.initialize()
    return _drafting_agent_instance

def create_draft_for_todo_email(message_id: str) -> str:
    """
    Public function to create a draft for a "To Do" email
    
    Args:
        message_id: Gmail message ID that was classified as "To Do"
        
    Returns:
        Draft email content formatted for terminal display
    """
    try:
        agent = get_drafting_agent_instance()
        return agent.draft_email_reply(message_id)
    except Exception as e:
        return f"❌ Error in drafting agent: {e}"

def main():
    """Main function for testing the drafting agent"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gmail Email Drafting Agent with DeepSeek AI')
    parser.add_argument('message_id', help='Email message ID to create draft for')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Override debug setting if specified
    if args.debug:
        config.DEBUG = True
        config.VERBOSE_LOGGING = True
    
    print("🚀 Gmail Email Drafting Agent with DeepSeek AI")
    print("=" * 80)
    
    # Create draft for the specified email
    draft_result = create_draft_for_todo_email(args.message_id)
    print(draft_result)

if __name__ == "__main__":
    main()