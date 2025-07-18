"""
Utility functions for Gmail email classification
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
        email_timestamp = int(email_data['internalDate']) / 1000
        email_date = datetime.fromtimestamp(email_timestamp)
        cutoff_date = datetime.now() - timedelta(days=days)
        return email_date < cutoff_date
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
    return f"""You are an AI agent responsible for classifying Gmail emails into one of these mutually exclusive labels:

**To Do**: Requires user action (reply, review, decision, meeting invite)
- Include if: Email requests reply, input, task, or approval
- Include if: Email includes meeting invites or calendar coordination
- Rule: Applies only while user action is pending

**Awaiting Reply**: User has replied, waiting for others to respond
- Rule: Applies only after user has taken action
- Rule: Thread is active, responsibility is on another person

**FYI**: Purely informational, no action or reply required
- Rule: No action, decision, or engagement expected
- May contain useful context or updates

**Done**: No action needed, acknowledgment/completion message
- Use when: Email acknowledges, thanks, or closes conversation
- Use when: Communicates completion, agreement, or confirmation

**Spam**: Promotional, automated, or low-value content
- Categories: Ads, marketing, app notifications, newsletters

**History**: Resolved/inactive threads, completed items
- Use if: Thread is closed, acknowledged, or previously replied to but inactive
- Use if: To Do was replied to and no further action expected

**Classification Algorithm (in order):**
1. Check for To Do → If user action required, label as To Do
2. If not To Do, check for Awaiting Reply → If user waiting after replying
3. If not Awaiting Reply, check for FYI → If purely informational
4. If not FYI, check for Done → If acknowledgment/completion message
5. If not Done, check for SPAM → If promotional/automated
6. If none apply, label as History

**Email Content to Classify:**
{email_content}

{thread_content}

**Instructions:**
1. Analyze the email content and thread context
2. Apply the classification rules in the specified order
3. Return ONLY the label name ({', '.join(config.LABELS)})
4. Be decisive - choose the first rule that applies

Classification:"""

def validate_label(label: str) -> str:
    """
    Validate and normalize label name
    
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
            return valid_label
    
    # Partial match (case-insensitive for SPAM/Spam)
    for valid_label in config.LABELS:
        if (label.lower() == valid_label.lower() or 
            (label.lower() == "spam" and valid_label == "SPAM") or
            (label == "SPAM" and valid_label.lower() == "spam")):
            return valid_label
    
    if config.DEBUG:
        print(f"Invalid label '{label}', using 'History' as fallback")
    
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