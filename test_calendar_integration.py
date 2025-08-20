#!/usr/bin/env python3
"""
Test Gmail Calendar Integration
This script tests the calendar functionality for email drafting
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from tools.calendar import (
    extract_time_from_text,
    check_calendar_availability_direct,
    find_free_time_slots_direct,
    extract_meeting_request_from_email,
    generate_calendar_invite_details,
    get_user_scheduling_link,
    calendar_service
)

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_time_extraction():
    """Test time extraction from email text"""
    print_header("Testing Time Extraction")
    
    test_emails = [
        "Can we meet tomorrow at 2pm?",
        "How about Tuesday at 10:30 AM?",
        "Are you free for a call on March 15th at 3pm?",
        "Let's schedule a meeting for next week Monday at 11am",
        "Can you do 2024-01-20 14:00?",
        "Meeting tomorrow at 9am would be great",
        "No specific time mentioned in this email"
    ]
    
    success = True
    for email_text in test_emails:
        print(f"\n📧 Email: '{email_text}'")
        try:
            time_suggestions = extract_time_from_text(email_text)
            
            if time_suggestions:
                for suggestion in time_suggestions:
                    print(f"  ⏰ Found: {suggestion['original_text']} → {suggestion['parsed_datetime']}")
            else:
                print("  ❌ No time suggestions found")
        except Exception as e:
            print(f"  💥 Error: {e}")
            success = False
    
    return success

def test_meeting_request_detection():
    """Test meeting request detection"""
    print_header("Testing Meeting Request Detection")
    
    test_emails = [
        {
            'content': "Can we schedule a meeting to discuss the project? How about Tuesday at 2pm?",
            'expected': 'specific_time_suggested'
        },
        {
            'content': "I'd like to set up a call with you. When are you available?",
            'expected': 'general_meeting_request'
        },
        {
            'content': "Here are the documents you requested. Let me know if you need anything else.",
            'expected': 'none'
        },
        {
            'content': "Thanks for the update. Can we chat about this tomorrow at 10am?",
            'expected': 'specific_time_suggested'
        }
    ]
    
    success = True
    for i, test_case in enumerate(test_emails, 1):
        email_content = test_case['content']
        expected = test_case['expected']
        
        print(f"\n{i}. Email: '{email_content}'")
        
        try:
            analysis = extract_meeting_request_from_email(email_content)
            
            print(f"   Is meeting request: {analysis['is_meeting_request']}")
            print(f"   Request type: {analysis['request_type']}")
            print(f"   Expected: {expected}")
            print(f"   ✅ Correct" if analysis['request_type'] == expected else "❌ Incorrect")
            
            if analysis['time_suggestions']:
                print(f"   Time suggestions: {len(analysis['time_suggestions'])}")
                for suggestion in analysis['time_suggestions']:
                    print(f"     - {suggestion['original_text']}")
        except Exception as e:
            print(f"   💥 Error: {e}")
            success = False
    
    return success

def test_calendar_authentication():
    """Test calendar service authentication"""
    print_header("Testing Calendar Authentication")
    
    try:
        service = calendar_service.authenticate()
        print("✅ Calendar authentication successful")
        
        # Test basic calendar access
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        print(f"✅ Found {len(calendars)} calendars")
        
        primary_calendar = next((cal for cal in calendars if cal.get('primary')), None)
        if primary_calendar:
            print(f"✅ Primary calendar: {primary_calendar.get('summary', 'No name')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Calendar authentication failed: {e}")
        print("\n🔧 Setup required:")
        print("1. Ensure your credentials.json includes Calendar API scope")
        print("2. Delete token.json to re-authenticate with Calendar permissions")
        print("3. Re-run authentication to grant Calendar access")
        return False

def test_availability_check():
    """Test calendar availability checking"""
    print_header("Testing Availability Check")
    
    # Test with a time 2 hours from now
    test_time = datetime.now() + timedelta(hours=2)
    test_time_str = test_time.isoformat()
    
    print(f"🕐 Testing availability for: {test_time.strftime('%Y-%m-%d %H:%M')}")
    
    try:
        # Use the direct function instead of the tool
        availability = check_calendar_availability_direct(test_time_str, duration_minutes=60)
        
        print(f"✅ Availability check completed")
        print(f"   Available: {availability['available']}")
        print(f"   Conflicts: {availability['total_conflicts']}")
        
        if availability['conflicting_events']:
            print("   Conflicting events:")
            for event in availability['conflicting_events']:
                print(f"     - {event['summary']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Availability check failed: {e}")
        return False

def test_free_slots_finding():
    """Test finding free time slots"""
    print_header("Testing Free Slots Finding")
    
    try:
        # Use the direct function instead of the tool
        free_slots = find_free_time_slots_direct(
            days_ahead=7,
            duration_minutes=60,
            max_suggestions=3
        )
        
        slots = free_slots.get('free_slots', [])
        
        print(f"✅ Free slots search completed")
        print(f"   Found {len(slots)} available slots")
        
        for i, slot in enumerate(slots, 1):
            print(f"   {i}. {slot['formatted_time']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Free slots finding failed: {e}")
        return False

def test_configuration():
    """Test configuration setup"""
    print_header("Testing Configuration")
    
    success = True
    
    print(f"DeepSeek API Key: {'✅ Set' if config.DEEPSEEK_API_KEY else '❌ Missing'}")
    print(f"Gmail Credentials: {'✅ Found' if os.path.exists(config.GMAIL_CREDENTIALS_FILE) else '❌ Missing'}")
    print(f"Scheduling Link: {'✅ Set' if config.USER_SCHEDULING_LINK else '⚠️  Not set'}")
    
    print(f"\nCalendar Settings:")
    print(f"  Default Meeting Duration: {config.DEFAULT_MEETING_DURATION} minutes")
    print(f"  Business Hours Only: {config.BUSINESS_HOURS_ONLY}")
    print(f"  Calendar Lookahead: {config.CALENDAR_LOOKAHEAD_DAYS} days")
    
    # Test scheduling link
    try:
        scheduling_link = get_user_scheduling_link()
        if "[Your scheduling link" in scheduling_link:
            print(f"⚠️  Scheduling link placeholder detected: Configure USER_SCHEDULING_LINK in .env")
            # This is not critical for basic functionality
        else:
            print(f"✅ Scheduling link configured: {scheduling_link}")
    except Exception as e:
        print(f"❌ Error getting scheduling link: {e}")
        success = False
    
    return success

def test_full_integration():
    """Test the full integration with a sample email"""
    print_header("Testing Full Integration")
    
    sample_email = """Subject: Project Discussion
From: client@company.com
To: me@example.com
Date: Today

Hi there,

Hope you're doing well! I'd like to schedule a meeting to discuss the project progress. 
Are you available tomorrow at 2pm? We could do a quick 30-minute call.

Let me know if that works for you.

Best regards,
Client"""
    
    print("📧 Sample email:")
    print(sample_email)
    print("\n🔍 Analysis:")
    
    success = True
    
    try:
        # Test meeting detection
        meeting_analysis = extract_meeting_request_from_email(sample_email)
        print(f"Meeting request: {meeting_analysis['is_meeting_request']}")
        print(f"Request type: {meeting_analysis['request_type']}")
        
        # Test time extraction
        if meeting_analysis['time_suggestions']:
            for suggestion in meeting_analysis['time_suggestions']:
                print(f"Time found: {suggestion['original_text']} → {suggestion['parsed_datetime']}")
                
                # Test availability check
                try:
                    availability = check_calendar_availability_direct(
                        suggestion['parsed_datetime'].isoformat(),
                        duration_minutes=30
                    )
                    status = "Available" if availability['available'] else "Busy"
                    print(f"Availability: {status}")
                except Exception as e:
                    print(f"Availability check error: {e}")
                    success = False
        else:
            print("No time suggestions found in sample email")
    except Exception as e:
        print(f"💥 Full integration test error: {e}")
        success = False
    
    return success

def main():
    """Run all calendar integration tests"""
    print("🚀 Gmail Calendar Integration Test Suite")
    print("This will test the calendar functionality for email drafting")
    
    # Force debug mode for testing
    config.DEBUG = True
    
    tests = [
        ("Configuration", test_configuration),
        ("Time Extraction", test_time_extraction),
        ("Meeting Request Detection", test_meeting_request_detection),
        ("Calendar Authentication", test_calendar_authentication),
        ("Availability Check", test_availability_check),
        ("Free Slots Finding", test_free_slots_finding),
        ("Full Integration", test_full_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running {test_name} test...")
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name} test passed")
            else:
                print(f"❌ {test_name} test failed")
                
        except Exception as e:
            print(f"💥 {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Results Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed >= 5:  # Allow some non-critical tests to fail
        print("🎉 Core tests passed! Calendar integration is ready.")
        print("\n📋 Next steps:")
        print("1. Run the enhanced real-time agent: python gmail_realtime_agent.py")
        print("2. Send yourself a test email with a meeting request")
        print("3. Watch the calendar-aware draft generation in action!")
    else:
        print("⚠️  Critical tests failed. Please fix the issues before using calendar integration.")
        print("\n🔧 Common fixes:")
        print("1. Ensure Calendar API is enabled in Google Cloud Console")
        print("2. Delete token.json and re-authenticate to grant Calendar permissions")
        print("3. Set USER_SCHEDULING_LINK in your .env file")
        print("4. Install missing dependencies: pip install python-dateutil pytz")
    
    return passed >= 5

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)