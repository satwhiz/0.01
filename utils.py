"""
Utility functions for Gmail email classification - IMPROVED
"""
import base64
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from config import config

def extract_email_content(message: Dict[str, Any]) -> str:
    """
    Extract readable content from Gmail message
    
    Args:
        message: Gmail message object
        
    Returns:
        Formatted string with email content
    """
    payload = message.get('payload', {})
    
    # Get headers
    headers = payload.get('headers', [])
    subject = ""
    sender = ""
    recipient = ""
    date = ""
    
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        
        if name == 'subject':
            subject = value
        elif name == 'from':
            sender = value
        elif name == 'to':
            recipient = value
        elif name == 'date':
            date = value
    
    # Extract body
    body = extract_message_body(payload)
    
    return f"""Subject: {subject}
From: {sender}
To: {recipient}
Date: {date}
Body: {body}"""

def extract_message_body(payload: Dict[str, Any]) -> str:
    """
    Extract body text from Gmail message payload
    
    Args:
        payload: Gmail message payload
        
    Returns:
        Email body text
    """
    body = ""
    
    if 'parts' in payload:
        # Multi-part message
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    try:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
                    except Exception as e:
                        if config.DEBUG:
                            print(f"Error decoding message part: {e}")
                        continue
            elif part.get('mimeType') == 'multipart/alternative' and 'parts' in part:
                # Nested multipart
                body = extract_message_body(part)
                if body:
                    break
    else:
        # Single part message
        if payload.get('mimeType') == 'text/plain':
            data = payload.get('body', {}).get('data', '')
            if data:
                try:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                except Exception as e:
                    if config.DEBUG:
                        print(f"Error decoding message body: {e}")
    
    return body.strip()

def is_email_old(email_data: Dict[str, Any], days: int = None) -> bool:
    """
    Check if email is older than specified days
    
    Args:
        email_data: Gmail message object
        days: Number of days (defaults to config.HISTORY_DAYS)
        
    Returns:
        True if email is older than specified days
    """
    if days is None:
        days = config.HISTORY_DAYS
    
    try:
        # Gmail's internalDate is in milliseconds, convert to seconds
        email_timestamp = int(email_data['internalDate']) / 1000
        email_date = datetime.fromtimestamp(email_timestamp)
        cutoff_date = datetime.now() - timedelta(days=days)
        
        is_old = email_date < cutoff_date
        
        # Debug logging
        if config.DEBUG:
            print(f"Email date: {email_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Email is {'old' if is_old else 'recent'} (threshold: {days} days)")
        
        return is_old
        
    except (KeyError, ValueError, TypeError) as e:
        if config.DEBUG:
            print(f"Error checking email age: {e}")
        return False

def format_thread_context(thread_messages: List[Dict[str, Any]]) -> str:
    """
    Format thread messages for context
    
    Args:
        thread_messages: List of Gmail message objects in thread
        
    Returns:
        Formatted thread context string
    """
    if not thread_messages:
        return ""
    
    context = "THREAD CONTEXT:\n" + "="*50 + "\n"
    
    for i, msg in enumerate(thread_messages):
        content = extract_email_content(msg)
        context += f"\nMessage {i+1}:\n{'-'*20}\n{content}\n"
    
    context += "="*50
    return context

def get_classification_prompt(email_content: str, thread_content: str = "") -> str:
    """
    Generate the THREAD-AWARE classification prompt for the AI model
    
    Args:
        email_content: Content of the email to classify
        thread_content: Context from the email thread
        
    Returns:
        Formatted prompt for classification
    """
    return f"""**Gmail Email Classifier – THREAD-AWARE Label Assignment Instructions**

You are an AI agent responsible for classifying Gmail emails into one of the following **mutually exclusive** labels:
• To Do
• Awaiting Reply  
• FYI
• Done
• Junk
• History

**CRITICAL: Analyze the ENTIRE conversation thread to understand the flow and completion status.**

**1. To Do**
**Definition:** Label as **To Do** if **OTHERS are asking the USER to take action**.

**Key Indicators:**
• Someone is requesting something FROM the user
• Email asks the user to provide, complete, approve, or decide something
• External parties need the user to respond or do work

**Examples:**
• "Kindly provide Memorandum and Article of Association"
• "Please submit your report by Friday"  
• "Can you approve this by EOD?"
• "Kindly update the Addendum with the Date and share the scanned copy"

**2. Awaiting Reply**
**Definition:** Label as **Awaiting Reply** if the **USER is asking others to take action** or waiting for responses.

**Key Indicators:**
• The user has asked questions or made requests
• The user is waiting for others to provide information or feedback
• The user has delegated tasks and is expecting updates
• The user asked "Could you help me figure out..." or similar

**Examples:**
• "Could you help me figure out the date for the same?"
• "Please let me know your availability"
• "I've sent the documents, please review and confirm"
• "What's the status on the project?"

**3. FYI**
**Definition:** Pure information sharing with **no action required from anyone**.

**Examples:**
• "Monthly performance dashboard is now available"
• "Here's the policy update for your reference"
• "Team event photos from last week"

**4. Done**
**Definition:** Conversation is **complete** with no further action needed.

**THREAD COMPLETION INDICATORS:**
• User provides final deliverable without asking questions
• User says "Please find attached" as final response to a request
• User completes a requested task and doesn't ask for anything more
• Conversation naturally concludes after request fulfillment

**Examples:**
• "Please find the attached document. Thanks, Gaurav" (after being asked for a document)
• "Here's the final report you requested"
• "Completed as requested. Let me know if you need anything else"
• "All set from my end"

**5. Junk**
**Definition:** Promotional, automated, or low-value emails.

**6. History**
**Definition:** Old, resolved, or archived conversations.

**THREAD-AWARE Classification Algorithm:**

1. **ANALYZE THE FULL CONVERSATION THREAD:**
   - What was the original request?
   - What has been provided/completed?
   - Is this the final step in the conversation?

2. **IDENTIFY THE CURRENT EMAIL'S PURPOSE:**
   - Is the user FULFILLING a previous request? → Likely **Done**
   - Is the user ASKING for something new? → **Awaiting Reply**
   - Is someone REQUESTING something from the user? → **To Do**

3. **CHECK FOR COMPLETION PATTERNS:**
   - "Please find attached" + no new questions = **Done**
   - "Thanks" + final deliverable = **Done**
   - Simple acknowledgment after task completion = **Done**

4. **CONVERSATION FLOW ANALYSIS:**
   - If others asked for X, and user provides X without asking anything = **Done**
   - If others asked for X, and user provides X BUT asks for Y = **Awaiting Reply**
   - If others ask for X in this email = **To Do**

**Email Content to Classify:**
{email_content}

{thread_content}

**CRITICAL THREAD ANALYSIS EXAMPLE:**
Thread: 
1. Others: "Please provide documents A, B, C"
2. User: "Here are A, B. Could you help with date for C?"
3. Others: "Date should be March 26. Please provide updated C"
4. User: "Please find the attached document. Thanks"

Email #4 classification: **Done** (user fulfilled final request, no new questions, conversation complete)

**Instructions:**
1. **Read the ENTIRE thread context** to understand the conversation flow
2. **Identify if this email COMPLETES a previous request**
3. **Check if the user is asking for anything NEW**
4. **Determine if conversation is FINISHED or CONTINUING**
5. **Return ONLY the label name**: To Do, Awaiting Reply, FYI, Done, Junk, History

Classification:"""

def validate_label(label: str) -> str:
    """Validate and normalize label name with emoji mapping"""
    label = label.strip()
    
    # Map AI responses to emoji labels
    ai_to_emoji_mapping = {
        "To Do": "📋 To Do",
        "Awaiting Reply": "⏳ Awaiting Reply",
        "FYI": "📄 FYI",
        "Done": "✅ Done", 
        "Junk": "🗑️ Junk",
        "Spam": "🗑️ Junk",  # Map both Spam and SPAM to Junk
        "SPAM": "🗑️ Junk",
        "History": "📚 History"
    }
    
    # Direct mapping from AI response
    if label in ai_to_emoji_mapping:
        result = ai_to_emoji_mapping[label]
        if config.DEBUG:
            print(f"Mapped AI label '{label}' to emoji label '{result}'")
        return result
    
    # Direct match with emoji labels
    if label in config.LABELS:
        return label
    
    return "📚 History"  # Default fallback

def log_classification(message_id: str, label: str, success: bool):
    """
    Log classification results
    
    Args:
        message_id: Gmail message ID
        label: Applied label
        success: Whether labeling was successful
    """
    if config.VERBOSE_LOGGING:
        status = "SUCCESS" if success else "FAILED"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {status}: Message {message_id} → {label}")

def save_classification_log(message_id: str, label: str, email_content: str, success: bool):
    """
    Save detailed classification log to file
    
    Args:
        message_id: Gmail message ID
        label: Applied label
        email_content: Email content that was classified
        success: Whether labeling was successful
    """
    if not config.DEBUG:
        return
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "message_id": message_id,
        "label": label,
        "success": success,
        "email_preview": email_content[:200] + "..." if len(email_content) > 200 else email_content
    }
    
    try:
        with open("classification_log.json", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Error saving classification log: {e}")

# Test function
def test_label_mapping():
    """Test function to verify label mapping works correctly"""
    print("🧪 Testing label mapping...")
    
    test_cases = [
        "To Do",
        "Junk", 
        "SPAM",
        "spam",
        "History",
        "Invalid Label"
    ]
    
    for test_label in test_cases:
        result = validate_label(test_label)
        print(f"'{test_label}' -> '{result}'")

if __name__ == "__main__":
    # Run test if this file is executed directly
    import sys
    sys.path.append('.')
    from config import config
    config.DEBUG = True
    test_label_mapping()