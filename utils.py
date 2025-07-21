"""
Utility functions for Gmail email classification - SIMPLE FIXED VERSION
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
    Generate the classification prompt for the AI model
    
    Args:
        email_content: Content of the email to classify
        thread_content: Context from the email thread
        
    Returns:
        Formatted prompt for classification
    """
    return f"""**Gmail Email Classifier – Label Assignment Instructions**

You are an AI agent responsible for classifying Gmail emails into one of the following **mutually exclusive** labels:
• To Do
• Awaiting Reply  
• FYI
• Done
• Spam
• History

Use the following **rules, definitions, and label hierarchy** to classify each email based on its content and context.

**1. To Do**
**Definition:** Label an email as **To Do** if it requires the **user to take action**, such as replying, reviewing, scheduling, or making a decision.

**Include if:**
• The email requests a reply, input, task, or approval
• The email includes meeting invites or requires calendar coordination
• Someone is asking for something to be completed, reviewed, or decided

**Rules:**
• Applies **only while user action is pending**
• If the user has already replied, re-evaluate:
  - If others are expected to respond → move to **Awaiting Reply**
  - If the thread is complete → move to **History**

**Examples:**
• "Can you approve this by EOD?"
• "Are you available for a call tomorrow?"  
• "Please confirm your attendance"
• "Can you complete the work by tomorrow?"

**2. Awaiting Reply**
**Definition:** Label an email as **Awaiting Reply** if the **user has replied**, and is now **waiting on someone else** to take action or respond.

**Rules:**
• Applies only **after the user has taken action**
• Thread is still **active**, but responsibility is now on another person

**Examples:**
• "I've shared the document, waiting for your feedback"
• "Let me know what you decide"
• "Following up on the earlier thread"

**3. FYI**
**Definition:** Label an email as **FYI** if it is **purely informational**. These messages are for **awareness only** and require **no action or reply**.

**Rules:**
• No action, decision, or engagement expected
• May contain useful context or updates

**Examples:**
• "Monthly performance dashboard is now available"
• "Here's the new policy update for your reference"
• "Team event photos from last week"

**4. Done**
**Definition:** Label an email as **Done** if it is clear that **no action is needed** and **no response is expected**.

**Use Done when:**
• The email was sent to **acknowledge**, **thank**, or **close a conversation**
• It communicates **completion, agreement, or confirmation**

**Examples:**
• "Thanks, I've noted that"
• "All good from my side"
• "Looks fine. No changes needed"

**5. Spam**
**Definition:** Label an email as **Spam** if it is **promotional, automated, or low-value**, and does **not require attention**.

**Typical categories:**
• Ads and marketing emails
• App or service notifications  
• Social updates or newsletters
• Promotional content and sales pitches

**Examples:**
• "Flash Sale: 50% off this weekend only!"
• "You've unlocked a new badge"
• "Your weekly usage report is ready"
• "Turn Your Image Into a Professional Video"
• "Wednesday Web Drop + Our new competitor research service"

**6. History**
**Definition:** Label an email as **History** if it is part of a **resolved, inactive, or archived thread**.

**Rules:**
• Use if the thread is **closed**, **acknowledged**, or **previously replied to** but now inactive
• Also used when a **To Do** was replied to, and **no further action** is expected

**Examples:**
• "Thanks for your input. All sorted now"
• "Noted, closing this issue"
• "Appreciate the update — no further questions"

**Classification Algorithm (Decision Sequence)**
Classify each email using the following order:

1. **Check for To Do** → If user action or reply is required, label as **To Do**
2. **If not To Do, check for Awaiting Reply** → If user is waiting for others after having replied → **Awaiting Reply**
3. **If not Awaiting Reply, check for FYI** → If email is purely informational → **FYI**
4. **If not FYI, check for Done** → If no action is needed, but it's a conclusion/acknowledgment message → **Done**
5. **If not Done, check for Spam** → If email is promotional or auto-generated → **Spam**
6. **If none of the above apply**, label as **History**

**Email Content to Classify:**
{email_content}

{thread_content}

**Instructions:**
1. Analyze the email content and thread context carefully
2. Apply the classification rules in the exact order specified above
3. Return ONLY the label name: {', '.join(config.LABELS)}
4. Be decisive - choose the FIRST rule that applies
5. For emails asking for tasks, responses, or decisions, always choose "To Do"

Classification:"""

def validate_label(label: str) -> str:
    """
    SIMPLIFIED: Validate and normalize label name - no emoji mapping for now
    
    Args:
        label: Label name to validate
        
    Returns:
        Valid label name or default fallback
    """
    label = label.strip()
    
    # Direct match
    if label in config.LABELS:
        return label
    
    # Case-insensitive match
    for valid_label in config.LABELS:
        if label.lower() == valid_label.lower():
            if config.DEBUG:
                print(f"Case-insensitive match: '{label}' -> '{valid_label}'")
            return valid_label
    
    # Handle legacy SPAM -> Spam
    if label.upper() == "SPAM":
        return "Spam"
    
    if config.DEBUG:
        print(f"Invalid label '{label}', using 'History' as fallback")
        print(f"Available labels: {config.LABELS}")
    
    return "History"  # Default fallback

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
        "Spam", 
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