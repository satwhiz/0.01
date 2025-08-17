"""
Utility functions for Gmail email classification - UPDATED WITH NEW SYSTEM PROMPT
"""
import base64
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from config import config
from prompts.classification_system_prompt import CLASSIFICATION_SYSTEM_PROMPT

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
        
        # Debug logging - ALWAYS show for recent emails that might be misclassified
        if config.DEBUG or (datetime.now() - email_date).total_seconds() < 3600:  # Show for emails less than 1 hour old
            print(f"📅 Email timestamp: {email_data['internalDate']} ms")
            print(f"📅 Email date: {email_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📅 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📅 Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📅 Age in hours: {(datetime.now() - email_date).total_seconds() / 3600:.1f}")
            print(f"📅 History threshold: {days} days")
            print(f"📅 Email is {'OLD (will be auto-classified as History)' if is_old else 'RECENT (will use AI classification)'}")
            
            if is_old and (datetime.now() - email_date).days < 1:
                print(f"⚠️  WARNING: Email is less than 1 day old but being flagged as History!")
                print(f"⚠️  Check your HISTORY_DAYS setting: {days}")
        
        return is_old
        
    except (KeyError, ValueError, TypeError) as e:
        if config.DEBUG:
            print(f"❌ Error checking email age: {e}")
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
    Generate the classification prompt using the new system prompt
    
    Args:
        email_content: Content of the email to classify
        thread_content: Context from the email thread
        
    Returns:
        Formatted prompt for classification
    """
    
    # Debug: Check if system prompt is loaded
    if config.DEBUG:
        print(f"🔍 System prompt length: {len(CLASSIFICATION_SYSTEM_PROMPT)}")
        print(f"🔍 System prompt starts with: {CLASSIFICATION_SYSTEM_PROMPT[:100]}...")
    
    prompt = CLASSIFICATION_SYSTEM_PROMPT + "\n\n"
    
    prompt += "**Email Content to Classify:**\n"
    prompt += email_content + "\n\n"
    
    if thread_content:
        prompt += thread_content + "\n\n"
    
    prompt += "**IMPORTANT:** Analyze the entire thread context above and classify according to the system prompt rules.\n\n"
    prompt += "**CRITICAL:** This email contains a direct request 'Can you send me the documentation' - this should be classified as 'To Do' since it requires action from the user.\n\n"
    prompt += "Classification:"
    
    if config.DEBUG:
        print(f"🔍 Final prompt length: {len(prompt)}")
    
    return prompt

def validate_label(label: str) -> str:
    """Validate and normalize label name with emoji mapping"""
    # Clean the response - extract just the label part
    label = label.strip()
    
    # If the response contains extra text, extract just the classification
    if "Classification:" in label:
        label = label.split("Classification:")[-1].strip()
    
    # Handle responses that contain reasoning or extra text
    first_line = label.split('\n')[0].strip()
    if first_line:
        label = first_line
    
    # Remove common prefixes that might appear
    prefixes_to_remove = ["Classification:", "Label:", "Category:", "Result:"]
    for prefix in prefixes_to_remove:
        if label.startswith(prefix):
            label = label[len(prefix):].strip()
    
    # Debug: Print what we received
    if config.DEBUG:
        print(f"🔍 Raw input: '{label}'")
        print(f"🔍 Cleaned label: '{label}'")
    
    # Map AI responses to emoji labels - COMPREHENSIVE MAPPING
    ai_to_emoji_mapping = {
        # Standard responses
        "To Do": "📋 To Do",
        "Awaiting Reply": "⏳ Awaiting Reply", 
        "FYI": "📄 FYI",
        "Done": "✅ Done", 
        "Junk": "🗑️ Junk",
        "Spam": "🗑️ Junk",
        "History": "📚 History",
        
        # Case variations
        "TO DO": "📋 To Do",
        "Todo": "📋 To Do",
        "TODO": "📋 To Do",
        "to do": "📋 To Do",
        "To do": "📋 To Do",
        
        "Awaiting reply": "⏳ Awaiting Reply",
        "awaiting reply": "⏳ Awaiting Reply",
        "AWAITING REPLY": "⏳ Awaiting Reply",
        "Awaiting Reply": "⏳ Awaiting Reply",
        
        "fyi": "📄 FYI",
        "Fyi": "📄 FYI",
        
        "done": "✅ Done",
        "DONE": "✅ Done",
        "Done": "✅ Done",
        
        "spam": "🗑️ Junk",
        "SPAM": "🗑️ Junk",
        "Spam": "🗑️ Junk",
        "junk": "🗑️ Junk",
        "JUNK": "🗑️ Junk",
        "Junk": "🗑️ Junk",
        
        "history": "📚 History",
        "HISTORY": "📚 History",
        "History": "📚 History"
    }
    
    # Direct mapping from AI response
    if label in ai_to_emoji_mapping:
        result = ai_to_emoji_mapping[label]
        if config.DEBUG:
            print(f"✅ Mapped AI label '{label}' to emoji label '{result}'")
        return result
    
    # Direct match with emoji labels (from config)
    if label in config.LABELS:
        if config.DEBUG:
            print(f"✅ Direct match found: '{label}'")
        return label
    
    # Fuzzy matching for partial matches
    label_lower = label.lower()
    if "to do" in label_lower or "todo" in label_lower:
        if config.DEBUG:
            print(f"✅ Fuzzy match: '{label}' -> To Do")
        return "📋 To Do"
    elif "awaiting" in label_lower and "reply" in label_lower:
        if config.DEBUG:
            print(f"✅ Fuzzy match: '{label}' -> Awaiting Reply")
        return "⏳ Awaiting Reply"
    elif "fyi" in label_lower:
        if config.DEBUG:
            print(f"✅ Fuzzy match: '{label}' -> FYI")
        return "📄 FYI"
    elif "done" in label_lower:
        if config.DEBUG:
            print(f"✅ Fuzzy match: '{label}' -> Done")
        return "✅ Done"
    elif "spam" in label_lower or "junk" in label_lower:
        if config.DEBUG:
            print(f"✅ Fuzzy match: '{label}' -> Junk")
        return "🗑️ Junk"
    elif "history" in label_lower:
        if config.DEBUG:
            print(f"✅ Fuzzy match: '{label}' -> History")
        return "📚 History"
    
    # Debug: Print available options if no match
    if config.DEBUG:
        print(f"❌ No mapping found for '{label}'")
        print(f"Available mappings: {list(ai_to_emoji_mapping.keys())}")
        print(f"Available emoji labels: {config.LABELS}")
        print(f"Defaulting to History")
    
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
        "Spam",
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