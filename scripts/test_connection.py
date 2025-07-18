#!/usr/bin/env python3
"""
Test Gmail API connection and setup validation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from gmail_auth import gmail_auth

def test_configuration():
    """Test configuration validity"""
    print("🔧 Testing Configuration...")
    
    # Test OpenAI API key
    if config.OPENAI_API_KEY:
        print("✅ OpenAI API key found")
    else:
        print("❌ OpenAI API key not found")
        return False
    
    # Test Gmail credentials file
    if os.path.exists(config.GMAIL_CREDENTIALS_FILE):
        print(f"✅ Gmail credentials file found: {config.GMAIL_CREDENTIALS_FILE}")
    else:
        print(f"❌ Gmail credentials file not found: {config.GMAIL_CREDENTIALS_FILE}")
        return False
    
    # Print configuration
    config.print_config()
    return True

def test_gmail_connection():
    """Test Gmail API connection"""
    print("\n📧 Testing Gmail API Connection...")
    
    try:
        # Test authentication
        service = gmail_auth.authenticate()
        print("✅ Gmail authentication successful")
        
        # Test basic API call
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile.get('emailAddress')
        total_messages = profile.get('messagesTotal', 0)
        
        print(f"✅ Connected to Gmail account: {email_address}")
        print(f"📊 Total messages in account: {total_messages}")
        
        # Test labels access
        labels_result = service.users().labels().list(userId='me').execute()
        labels = labels_result.get('labels', [])
        
        print(f"✅ Can access labels: {len(labels)} labels found")
        
        # Check if our classification labels exist
        label_names = [label['name'] for label in labels]
        existing_classification_labels = [name for name in config.LABELS if name in label_names]
        
        if existing_classification_labels:
            print(f"📋 Found existing classification labels: {', '.join(existing_classification_labels)}")
        else:
            print("📋 No classification labels found (will be created during setup)")
        
        return True
        
    except Exception as e:
        print(f"❌ Gmail connection failed: {e}")
        return False

def test_recent_emails():
    """Test recent emails access"""
    print("\n📬 Testing Recent Emails Access...")
    
    try:
        service = gmail_auth.get_service()
        
        # Get recent emails
        results = service.users().messages().list(
            userId='me', 
            q='in:inbox',
            maxResults=5
        ).execute()
        
        messages = results.get('messages', [])
        
        if messages:
            print(f"✅ Can access recent emails: {len(messages)} recent messages found")
            
            # Test retrieving a single message
            message_id = messages[0]['id']
            message = service.users().messages().get(userId='me', id=message_id).execute()
            
            # Get subject
            headers = message.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            
            print(f"✅ Can retrieve message details. Latest email subject: '{subject[:50]}...'")
            
        else:
            print("📭 No recent emails found in inbox")
        
        return True
        
    except Exception as e:
        print(f"❌ Recent emails access failed: {e}")
        return False

def test_label_creation():
    """Test label creation capability"""
    print("\n🏷️  Testing Label Creation...")
    
    try:
        service = gmail_auth.get_service()
        
        # Test creating a temporary label
        test_label_name = "Test_Classification_Label"
        
        label_body = {
            'name': test_label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        
        # Create test label
        label = service.users().labels().create(userId='me', body=label_body).execute()
        print(f"✅ Can create labels: Created test label '{test_label_name}'")
        
        # Delete test label
        service.users().labels().delete(userId='me', id=label['id']).execute()
        print(f"✅ Can delete labels: Removed test label")
        
        return True
        
    except Exception as e:
        print(f"❌ Label creation test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Gmail Email Classification System - Connection Test")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("Gmail Connection", test_gmail_connection),
        ("Recent Emails Access", test_recent_emails),
        ("Label Creation", test_label_creation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
        print()  # Add spacing between tests
    
    # Summary
    print("=" * 60)
    print("📊 Test Results Summary:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 All tests passed! Your system is ready for email classification.")
        print("\nNext steps:")
        print("1. Run 'python gmail_setup_agent.py' to create labels and classify existing emails")
        print("2. Run 'python gmail_realtime_agent.py' to classify new emails")
    else:
        print("⚠️  Some tests failed. Please fix the issues before proceeding.")
        print("\nTroubleshooting:")
        print("1. Check your .env file has the correct API keys")
        print("2. Ensure credentials.json is downloaded from Google Cloud Console")
        print("3. Make sure you have the necessary Gmail API permissions")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)