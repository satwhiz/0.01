#!/usr/bin/env python3
"""
Debug script to test the new classification system with your specific email
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from gmail_auth import gmail_auth
from utils import extract_email_content, is_email_old, get_classification_prompt, validate_label
from prompts.classification_system_prompt import CLASSIFICATION_SYSTEM_PROMPT
from agno.agent import Agent
from agno.models.deepseek import DeepSeek

def get_deepseek_model():
    """Get DeepSeek model with proper configuration"""
    return DeepSeek(
        id=config.DEFAULT_MODEL,
        api_key=config.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

def test_sample_email():
    """Test classification with your specific email"""
    
    # Force debug mode
    config.DEBUG = True
    config.VERBOSE_LOGGING = True
    
    print("🔍 Debug Script - Testing Classification with Your Email")
    print("=" * 80)
    
    # Your sample email
    sample_email = """Subject: Documentation Request
From: Satvik <satvikumar02@gmail.com>
To: me
Date: 17:22 (1 minute ago)
Body: Hey Satvik, 
Can you send me the documentation of the latest codes that you have completed? 
Regards"""
    
    print("📧 Sample Email to Classify:")
    print("-" * 40)
    print(sample_email)
    print("-" * 40)
    
    # Test the classification prompt generation
    print("\n🔧 Testing Classification Prompt Generation:")
    classification_prompt = get_classification_prompt(sample_email)
    print("Prompt length:", len(classification_prompt))
    print("System prompt included:", "Email Classification Agent System Prompt v2.0" in classification_prompt)
    print("Sample email included:", "Hey Satvik" in classification_prompt)
    
    # Show first 500 characters of the prompt
    print("\nFirst 500 chars of prompt:")
    print(classification_prompt[:500] + "...")
    
    # Test AI classification
    print("\n🤖 Testing DeepSeek AI Classification:")
    print("-" * 40)
    
    try:
        # Create classifier with the system prompt
        classifier_agent = Agent(
            model=get_deepseek_model(),
            instructions=CLASSIFICATION_SYSTEM_PROMPT,
            markdown=False
        )
        
        print("🔄 Running AI classification...")
        response = classifier_agent.run(classification_prompt)
        
        raw_response = response.content.strip()
        print(f"🎯 AI Raw Response: '{raw_response}'")
        
        # Test label validation
        validated_label = validate_label(raw_response)
        print(f"✅ Validated Label: '{validated_label}'")
        
        # Expected result analysis
        print("\n📊 Analysis:")
        if "send me the documentation" in sample_email.lower():
            print("✅ Email contains clear action request: 'send me the documentation'")
            if validated_label == "📋 To Do":
                print("✅ CORRECT: Email properly classified as 'To Do'")
            else:
                print(f"❌ INCORRECT: Expected 'To Do', got '{validated_label}'")
                print("🔧 This indicates an issue with the classification logic")
        
    except Exception as e:
        print(f"❌ Error in AI classification: {e}")
        import traceback
        traceback.print_exc()

def test_age_check():
    """Test if age check is interfering"""
    print("\n⏰ Testing Age Check Function:")
    print("-" * 40)
    
    # Create a mock recent email (current timestamp)
    current_timestamp = int(datetime.now().timestamp() * 1000)  # Gmail uses milliseconds
    
    mock_email = {
        'internalDate': str(current_timestamp)
    }
    
    is_old = is_email_old(mock_email, config.HISTORY_DAYS)
    print(f"Mock recent email is old? {is_old}")
    print(f"History threshold: {config.HISTORY_DAYS} days")
    
    if is_old:
        print("❌ PROBLEM: Recent email is being flagged as old!")
    else:
        print("✅ Age check is working correctly")

def test_system_prompt_directly():
    """Test the system prompt with a minimal example"""
    print("\n🧪 Testing System Prompt Directly:")
    print("-" * 40)
    
    # Direct prompt test
    direct_prompt = f"""{CLASSIFICATION_SYSTEM_PROMPT}

**Email Content to Classify:**
Subject: Documentation Request
From: colleague@company.com
To: me
Body: Can you send me the documentation of the latest codes that you have completed?

**IMPORTANT:** Analyze the email content above and classify according to the system prompt rules.

Classification:"""
    
    try:
        classifier_agent = Agent(
            model=get_deepseek_model(),
            instructions="You are an expert email classifier. Return only the classification label.",
            markdown=False
        )
        
        print("🔄 Testing with direct prompt...")
        response = classifier_agent.run(direct_prompt)
        
        raw_response = response.content.strip()
        print(f"🎯 Direct Test Result: '{raw_response}'")
        
        if raw_response.lower() in ['to do', 'todo']:
            print("✅ Direct test successful - should be 'To Do'")
        else:
            print(f"❌ Direct test failed - got '{raw_response}' instead of 'To Do'")
            print("🔧 Issue might be with the system prompt or AI model")
            
    except Exception as e:
        print(f"❌ Error in direct test: {e}")

def debug_latest_email():
    """Debug the actual latest email from Gmail"""
    print("\n📧 Testing Latest Email from Gmail:")
    print("-" * 40)
    
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
        print(f"📧 Latest email ID: {message_id}")
        
        # Get the full email
        email = service.users().messages().get(userId='me', id=message_id).execute()
        
        # Test age check
        print("\n⏰ Age Check Results:")
        email_timestamp = int(email['internalDate']) / 1000
        email_date = datetime.fromtimestamp(email_timestamp)
        cutoff_date = datetime.now() - timedelta(days=config.HISTORY_DAYS)
        
        print(f"Email timestamp: {email['internalDate']} (milliseconds)")
        print(f"Email date: {email_date}")
        print(f"Current time: {datetime.now()}")
        print(f"Cutoff date: {cutoff_date}")
        print(f"Days ago: {(datetime.now() - email_date).days}")
        
        is_old = is_email_old(email, config.HISTORY_DAYS)
        print(f"Is email old? {is_old}")
        
        if is_old:
            print("❌ FOUND THE PROBLEM: Email is being auto-classified as History due to age!")
            print("🔧 Check your HISTORY_DAYS setting in .env file")
        else:
            # Test classification
            email_content = extract_email_content(email)
            print(f"\n📄 Email Content Preview:")
            print(email_content[:300] + "...")
            
            if "send me the documentation" in email_content.lower():
                print("✅ Found your test email - it should be 'To Do'")
            
    except Exception as e:
        print(f"❌ Error testing latest email: {e}")

if __name__ == "__main__":
    print("🚀 Gmail Classification Debug Tool")
    print("This will help identify why your email was misclassified\n")
    
    # Run all tests
    test_sample_email()
    test_age_check() 
    test_system_prompt_directly()
    debug_latest_email()
    
    print("\n" + "=" * 80)
    print("🎯 SUMMARY:")
    print("If the email is being classified as 'History', check:")
    print("1. HISTORY_DAYS setting in your .env file")
    print("2. System prompt is being applied correctly")
    print("3. DeepSeek API is responding as expected")
    print("4. Label mapping is working correctly")