"""
Gmail Email Classification Setup Agent
This agent creates labels and classifies all existing emails in Gmail.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from agno.agent import Agent
from agno.tools import tool
from agno.models.openai import OpenAIChat
from config import config
from gmail_auth import gmail_auth
from utils import (
    extract_email_content, 
    is_email_old, 
    format_thread_context,
    get_classification_prompt,
    validate_label,
    log_classification,
    save_classification_log
)

# Global instance for tool functions
_setup_agent_instance = None

class GmailSetupAgent:
    def __init__(self):
        self.service = None
        self.labels = config.LABELS
        self.label_ids = {}
        self.history_days = config.HISTORY_DAYS
        
    def initialize(self):
        """Initialize the agent with Gmail authentication"""
        if config.DEBUG:
            print("Initializing Gmail Setup Agent...")
            config.print_config()
        
        # Validate configuration
        if not config.validate():
            raise ValueError("Invalid configuration. Please check your settings.")
        
        # Authenticate with Gmail
        self.service = gmail_auth.authenticate()
        if config.DEBUG:
            print("Gmail authentication successful")

def get_setup_agent_instance():
    """Get the global agent instance"""
    global _setup_agent_instance
    if _setup_agent_instance is None:
        _setup_agent_instance = GmailSetupAgent()
        _setup_agent_instance.initialize()
    return _setup_agent_instance

@tool(
    name="create_gmail_labels",
    description="Create Gmail labels for email classification",
    show_result=True
)
def create_labels() -> str:
    """Create the required Gmail labels if they don't exist"""
    agent = get_setup_agent_instance()
    
    if not agent.service:
        return "Gmail service not authenticated"
    
    try:
        # Get existing labels (including Gmail's built-in labels)
        results = agent.service.users().labels().list(userId='me').execute()
        existing_labels = {label['name']: label['id'] for label in results.get('labels', [])}
        
        created_labels = []
        for label_name in agent.labels:
            if label_name not in existing_labels:
                # Skip creating SPAM label as Gmail has a built-in SPAM label
                if label_name.upper() == "SPAM":
                    # Find Gmail's built-in SPAM label
                    spam_label = next((label for label in results.get('labels', []) 
                                     if label['name'] == 'SPAM'), None)
                    if spam_label:
                        existing_labels["SPAM"] = spam_label['id']
                        if config.DEBUG:
                            print("Using Gmail's built-in SPAM label")
                    continue
                
                label_body = {
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
                
                try:
                    label = agent.service.users().labels().create(userId='me', body=label_body).execute()
                    created_labels.append(label_name)
                    existing_labels[label_name] = label['id']
                    if config.DEBUG:
                        print(f"Created label: {label_name}")
                except Exception as e:
                    print(f"Error creating label {label_name}: {e}")
        
        agent.label_ids = existing_labels
        
        if created_labels:
            return f"✅ Created new labels: {', '.join(created_labels)}\n📋 Total available labels: {', '.join([label for label in existing_labels.keys() if label in agent.labels])}"
        else:
            return f"📋 All required labels already exist: {', '.join([label for label in existing_labels.keys() if label in agent.labels])}"
    
    except Exception as e:
        return f"❌ Error managing labels: {e}"

@tool(
    name="classify_all_emails",
    description="Classify all emails in Gmail and apply appropriate labels",
    show_result=True
)
def classify_all_emails(max_emails: int = 500) -> str:
    """Main function to classify all emails"""
    agent = get_setup_agent_instance()
    
    if not agent.service:
        return "❌ Gmail service not authenticated"
    
    print(f"🔄 Starting classification of up to {max_emails} emails...")
    
    try:
        # Get all messages in inbox
        results = agent.service.users().messages().list(
            userId='me', 
            q='in:inbox',
            maxResults=max_emails
        ).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return "📭 No emails found in inbox"
        
        emails = []
        total_messages = len(messages)
        
        for i, message in enumerate(messages):
            if config.DEBUG and i % 50 == 0:
                print(f"Retrieving email {i+1}/{total_messages}")
            
            try:
                msg = agent.service.users().messages().get(userId='me', id=message['id']).execute()
                emails.append(msg)
            except Exception as e:
                if config.DEBUG:
                    print(f"Error retrieving message {message['id']}: {e}")
                continue
        
        if config.DEBUG:
            print(f"Retrieved {len(emails)} emails successfully")
        
        classified_count = 0
        error_count = 0
        classification_summary = {label: 0 for label in agent.labels}
        
        # Group emails by thread
        threads = {}
        for email in emails:
            thread_id = email['threadId']
            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append(email)
        
        total_threads = len(threads)
        print(f"📊 Processing {len(emails)} emails across {total_threads} threads...")
        
        # Process each thread
        for i, (thread_id, thread_messages) in enumerate(threads.items()):
            if config.DEBUG and i % 10 == 0:
                print(f"Processing thread {i+1}/{total_threads}")
            
            # Sort messages by date
            thread_messages.sort(key=lambda x: int(x['internalDate']))
            
            # Classify each message in the thread
            for email in thread_messages:
                try:
                    # Check if email is older than history_days - skip AI classification
                    if is_email_old(email, agent.history_days):
                        label = "History"
                        if config.DEBUG:
                            print(f"Email {email['id']} is older than {agent.history_days} days - auto-classified as History")
                    else:
                        # Get the last message in the thread (most recent)
                        last_message = thread_messages[-1] if thread_messages else email
                        
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
                            
                            if config.DEBUG:
                                print(f"Classified email as: {label}")
                        
                        except Exception as e:
                            if config.DEBUG:
                                print(f"Error in classification: {e}")
                            label = "History"  # Default fallback
                    
                    # Apply the label
                    if label in agent.label_ids:
                        label_id = agent.label_ids[label]
                        agent.service.users().messages().modify(
                            userId='me',
                            id=email['id'],
                            body={'addLabelIds': [label_id]}
                        ).execute()
                        success = True
                    else:
                        success = False
                        if config.DEBUG:
                            print(f"Label {label} not found in available labels")
                    
                    if success:
                        classified_count += 1
                        classification_summary[label] += 1
                        log_classification(email['id'], label, True)
                        
                        # Save detailed log if debug enabled
                        if config.DEBUG:
                            email_content = extract_email_content(email)
                            save_classification_log(email['id'], label, email_content, True)
                    else:
                        error_count += 1
                        log_classification(email['id'], label, False)
                
                except Exception as e:
                    error_count += 1
                    if config.DEBUG:
                        print(f"Error processing email {email['id']}: {e}")
        
        # Generate summary report
        summary = f"""
🎉 Email Classification Complete!

📈 **Results Summary:**
- Total emails processed: {len(emails)}
- Successfully classified: {classified_count}
- Errors encountered: {error_count}
- Success rate: {(classified_count/len(emails)*100):.1f}%

📊 **Classification Breakdown:**
"""
        
        for label, count in classification_summary.items():
            percentage = (count/len(emails)*100) if len(emails) > 0 else 0
            summary += f"• {label}: {count} emails ({percentage:.1f}%)\n"
        
        summary += f"\n⚙️ **Settings Used:**\n• History threshold: {agent.history_days} days\n• Model: {config.DEFAULT_MODEL}"
        
        if config.DEBUG:
            summary += f"\n\n📝 Detailed logs saved to: classification_log.json"
        
        return summary
    
    except Exception as e:
        return f"❌ Error in classification process: {e}"

def main():
    """Main function to run the setup agent"""
    try:
        # Create the Agno agent with tools
        agent = Agent(
            model=OpenAIChat(id=config.DEFAULT_MODEL),
            tools=[
                create_labels,
                classify_all_emails
            ],
            show_tool_calls=config.DEBUG,
            markdown=True
        )
        
        # Run the setup process
        print("🚀 Starting Gmail Email Classification Setup...")
        print("This will create labels and classify all emails in your inbox.\n")
        
        agent.print_response(
            "Please create the Gmail labels first, then classify all existing emails according to the classification rules.",
            stream=True
        )
    
    except Exception as e:
        print(f"❌ Error starting setup agent: {e}")
        if config.DEBUG:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()