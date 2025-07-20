#!/usr/bin/env python3
"""
Debug script to test classification of a single recent email - FIXED VERSION
"""

import sys
import os
from datetime import datetime, timedelta
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from gmail_auth import gmail_auth
from utils import extract_email_content, is_email_old, get_classification_prompt, validate_label

def debug_single_email():
    """Debug classification of the most recent email"""
    
    # Force debug mode
    config.DEBUG = True
    config.VERBOSE_LOGGING = True
    
    print("🔍 Debug Script - Testing Single Email Classification")
    print("=" * 60)
    
    try:
        # Authenticate
        service = gmail_auth.authenticate()
        print("✅ Gmail authentication successful")
        
        # Get the most recent email
        results = service.users().messages().list(
            userId='me', 
            q='in:inbox',
            maxResults=1
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            print("❌ No emails found in inbox")
            return
        
        message_id = messages[0]['id']
        print(f"📧 Testing email ID: {message_id}")
        
        # Get the full email
        email = service.users().messages().get(userId='me', id=message_id).execute()
        
        # Extract content
        email_content = extract_email_content(email)
        print("\n📄 Email Content:")
        print("-" * 40)
        print(email_content[:500] + "..." if len(email_content) > 500 else email_content)
        print("-" * 40)
        
        # Test age calculation
        print(f"\n⏰ Age Test (threshold: {config.HISTORY_DAYS} days):")
        print("-" * 40)
        
        # Debug the timestamp conversion
        email_timestamp = int(email['internalDate']) / 1000
        email_date = datetime.fromtimestamp(email_timestamp)
        cutoff_date = datetime.now() - timedelta(days=config.HISTORY_DAYS)
        
        print(f"Email timestamp: {email['internalDate']} (milliseconds)")
        print(f"Email date: {email_date}")
        print(f"Current time: {datetime.now()}")
        print(f"Cutoff date: {cutoff_date}")
        print(f"Days ago: {(datetime.now() - email_date).days}")
        
        is_old = is_email_old(email, config.HISTORY_DAYS)
        print(f"Is old? {is_old}")
        
        if is_old:
            print("❌ Email is being auto-classified as History due to age")
            return
        
        # Test AI classification
        print("\n🤖 AI Classification Test:")
        print("-" * 40)
        
        classification_prompt = get_classification_prompt(email_content)
        print("Prompt preview:")
        print(classification_prompt[:300] + "...")
        
        # Run AI classification with CORRECT syntax
        classifier_agent = Agent(
            model=OpenAIChat(id=config.DEFAULT_MODEL),
            instructions="You are an expert email classifier. Follow the rules precisely and return only the label name.",
            markdown=False
        )
        
        print("\n🔄 Running AI classification...")
        response = classifier_agent.run(classification_prompt)
        
        raw_label = response.content.strip()
        validated_label = validate_label(raw_label)
        
        print(f"AI Response: '{raw_label}'")
        print(f"Validated Label: '{validated_label}'")
        
        # Check if the email should be "To Do"
        if "complete" in email_content.lower() and "tomorrow" in email_content.lower():
            print("\n✅ This email contains 'complete' and 'tomorrow' - should be 'To Do'")
            if validated_label != "To Do":
                print(f"❌ But AI classified it as: {validated_label}")
                print("\n💡 This suggests the classification prompt needs adjustment")
            else:
                print("✅ AI correctly classified it as 'To Do'")
        
    except Exception as e:
        print(f"❌ Error in debug script: {e}")
        import traceback
        traceback.print_exc()

def test_prompt_with_sample():
    """Test the classification prompt with your sample email"""
    
    print("\n🧪 Testing Prompt with Sample Email")
    print("=" * 60)
    
    sample_email = """Subject: can you complete the work by tomorrow ?
From: Satvik <satvikumar02@gmail.com>
To: me
Date: 18 Jul 2025, 18:45
Body: can you complete the work by tomorrow ?
thanks"""
    
    print("Sample email:")
    print(sample_email)
    
    prompt = get_classification_prompt(sample_email)
    print("\nGenerated prompt:")
    print(prompt)
    
    # Test AI classification with CORRECT syntax
    try:
        classifier_agent = Agent(
            model=OpenAIChat(id=config.DEFAULT_MODEL),
            instructions="You are an expert email classifier. Follow the rules precisely and return only the label name.",
            markdown=False
        )
        
        response = classifier_agent.run(prompt)
        raw_label = response.content.strip()
        validated_label = validate_label(raw_label)
        
        print(f"\nAI Response: '{raw_label}'")
        print(f"Validated Label: '{validated_label}'")
        
        if validated_label == "To Do":
            print("✅ Correct! This should be 'To Do'")
        else:
            print(f"❌ Incorrect! Expected 'To Do', got '{validated_label}'")
            print("\n🔧 The classification prompt may need improvement")
            
    except Exception as e:
        print(f"❌ Error testing prompt: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_single_email()
    test_prompt_with_sample()