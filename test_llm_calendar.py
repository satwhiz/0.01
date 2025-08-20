#!/usr/bin/env python3
"""
Debug Calendar Conflicts - Check what's really in your calendar
This script will help identify why "Daily Meet" is showing as a conflict
"""

import sys
import os
from datetime import datetime, timedelta
from dateutil import parser

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from tools.calendar import calendar_service

def debug_calendar_for_specific_time():
    """Debug what's in your calendar at the specific time"""
    
    print("🔍 **DEBUGGING CALENDAR CONFLICTS**")
    print("=" * 60)
    
    # The specific time that's causing issues
    target_time = "2025-08-18T12:00:00"
    
    print(f"🎯 Target time: {target_time} (12 PM tomorrow)")
    print(f"📅 Checking what's really in your calendar...")
    
    try:
        service = calendar_service.get_service()
        
        # Parse target time and add timezone
        start_dt = parser.parse(target_time)
        end_dt = start_dt + timedelta(minutes=30)  # 30 min window
        
        # Add timezone if not present
        import pytz
        if start_dt.tzinfo is None:
            local_tz = pytz.timezone('Asia/Kolkata')  # Your timezone (+05:30)
            start_dt = local_tz.localize(start_dt)
            end_dt = local_tz.localize(end_dt)
        
        start_rfc = start_dt.isoformat()
        end_rfc = end_dt.isoformat()
        
        print(f"🔍 Querying calendar from {start_rfc} to {end_rfc}")
        
        # Get ALL events around this time (wider window)
        wider_start = start_dt - timedelta(hours=2)
        wider_end = end_dt + timedelta(hours=2)
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=wider_start.isoformat(),
            timeMax=wider_end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        all_events = events_result.get('items', [])
        
        print(f"\n📋 **ALL EVENTS AROUND TARGET TIME** ({len(all_events)} found):")
        print("-" * 50)
        
        for i, event in enumerate(all_events, 1):
            event_start = event.get('start', {})
            event_end = event.get('end', {})
            
            # Get start and end times
            if 'dateTime' in event_start:
                start_time = parser.parse(event_start['dateTime'])
                end_time = parser.parse(event_end['dateTime'])
                is_all_day = False
            else:
                # All-day event
                start_time = parser.parse(event_start['date'])
                end_time = parser.parse(event_end['date'])
                is_all_day = True
            
            print(f"{i}. **{event.get('summary', 'Untitled Event')}**")
            print(f"   Start: {start_time}")
            print(f"   End: {end_time}")
            print(f"   All-day: {is_all_day}")
            print(f"   Status: {event.get('status', 'confirmed')}")
            
            # Check if user declined this event
            attendees = event.get('attendees', [])
            user_status = None
            for attendee in attendees:
                if attendee.get('self', False):
                    user_status = attendee.get('responseStatus')
                    break
            
            print(f"   Your response: {user_status or 'N/A'}")
            
            # Check if this overlaps with target time
            if not is_all_day:
                overlaps = (start_time < end_dt and end_time > start_dt)
                print(f"   Overlaps with 12 PM: {overlaps}")
                
                if overlaps:
                    print(f"   ⚠️  THIS EVENT IS CAUSING THE CONFLICT!")
                    
                    if user_status == 'declined':
                        print(f"   ✅ But you DECLINED it - should be ignored")
                    else:
                        print(f"   ❌ This is a real conflict")
            
            print()
        
        print("-" * 50)
        
        # Now check specifically for conflicts at 12 PM
        print(f"\n🎯 **CONFLICTS SPECIFICALLY AT 12 PM:**")
        
        conflicts_at_target = []
        
        for event in all_events:
            event_start = event.get('start', {})
            event_end = event.get('end', {})
            
            # Skip all-day events
            if 'date' in event_start:
                continue
            
            start_time = parser.parse(event_start['dateTime'])
            end_time = parser.parse(event_end['dateTime'])
            
            # Check if this overlaps with target time
            if start_time < end_dt and end_time > start_dt:
                # Check if user declined
                attendees = event.get('attendees', [])
                user_declined = False
                for attendee in attendees:
                    if attendee.get('self', False) and attendee.get('responseStatus') == 'declined':
                        user_declined = True
                        break
                
                if not user_declined:
                    conflicts_at_target.append({
                        'summary': event.get('summary', 'Untitled Event'),
                        'start': start_time,
                        'end': end_time,
                        'status': event.get('status', 'confirmed')
                    })
        
        if conflicts_at_target:
            print(f"❌ Found {len(conflicts_at_target)} real conflicts:")
            for conflict in conflicts_at_target:
                print(f"   • {conflict['summary']} ({conflict['start']} - {conflict['end']})")
        else:
            print(f"✅ NO REAL CONFLICTS FOUND - You should be available!")
        
        return len(conflicts_at_target) == 0
        
    except Exception as e:
        print(f"❌ Error debugging calendar: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_daily_meet_specifically():
    """Check if 'Daily Meet' is a recurring event causing false conflicts"""
    
    print(f"\n🔍 **DEBUGGING 'DAILY MEET' SPECIFICALLY**")
    print("-" * 50)
    
    try:
        service = calendar_service.get_service()
        
        # Search for events with 'Daily Meet' in the title
        # Get a wider range to find recurring patterns
        start_search = datetime.now() - timedelta(days=7)
        end_search = datetime.now() + timedelta(days=7)
        
        import pytz
        local_tz = pytz.timezone('Asia/Kolkata')
        if start_search.tzinfo is None:
            start_search = local_tz.localize(start_search)
            end_search = local_tz.localize(end_search)
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_search.isoformat(),
            timeMax=end_search.isoformat(),
            q='Daily Meet',  # Search for this specific event
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        daily_meet_events = events_result.get('items', [])
        
        print(f"📅 Found {len(daily_meet_events)} 'Daily Meet' events in the past/next week:")
        
        for i, event in enumerate(daily_meet_events, 1):
            event_start = event.get('start', {})
            event_end = event.get('end', {})
            
            if 'dateTime' in event_start:
                start_time = parser.parse(event_start['dateTime'])
                end_time = parser.parse(event_end['dateTime'])
                
                print(f"{i}. {event.get('summary', 'Untitled')}")
                print(f"   Time: {start_time.strftime('%A, %B %d at %I:%M %p')} - {end_time.strftime('%I:%M %p')}")
                print(f"   Recurring: {event.get('recurringEventId') is not None}")
                
                # Check if this is at 12 PM tomorrow
                target_date = datetime.now().date() + timedelta(days=1)
                if start_time.date() == target_date and start_time.hour == 12:
                    print(f"   ⚠️  THIS IS THE CONFLICTING EVENT!")
                    
                    # Check your response status
                    attendees = event.get('attendees', [])
                    for attendee in attendees:
                        if attendee.get('self', False):
                            status = attendee.get('responseStatus')
                            print(f"   Your response: {status}")
                            if status == 'declined':
                                print(f"   ✅ You declined - this should NOT be a conflict")
                            break
                
                print()
        
        # Check if there's a Daily Meet at exactly 12 PM tomorrow
        target_datetime = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)
        target_datetime = local_tz.localize(target_datetime)
        
        has_daily_meet_at_target = any(
            event.get('start', {}).get('dateTime') and
            parser.parse(event.get('start', {}).get('dateTime')).replace(tzinfo=None) == target_datetime.replace(tzinfo=None)
            for event in daily_meet_events
        )
        
        print(f"\n🎯 **ANALYSIS:**")
        if has_daily_meet_at_target:
            print(f"❌ There IS a 'Daily Meet' scheduled for 12 PM tomorrow")
            print(f"🔧 Check if you declined it or if it should be ignored")
        else:
            print(f"✅ No 'Daily Meet' found at 12 PM tomorrow")
            print(f"🐛 The conflict detection has a bug - false positive")
        
    except Exception as e:
        print(f"❌ Error searching for Daily Meet: {e}")

def test_availability_function_directly():
    """Test the availability function that's being used in the drafting agent"""
    
    print(f"\n🧪 **TESTING AVAILABILITY FUNCTION DIRECTLY**")
    print("-" * 50)
    
    try:
        # Import the exact function being used
        from tools.calendar import _check_calendar_availability_impl
        
        # Test the exact same parameters
        target_time = "2025-08-18T12:00:00"
        
        print(f"🎯 Testing availability for: {target_time}")
        print(f"🔧 Using _check_calendar_availability_impl function directly...")
        
        result = _check_calendar_availability_impl(
            start_time=target_time,
            duration_minutes=60
        )
        
        print(f"\n📊 **DIRECT FUNCTION RESULT:**")
        print(f"   Available: {result['available']}")
        print(f"   Total conflicts: {result['total_conflicts']}")
        print(f"   Requested start: {result['requested_start']}")
        print(f"   Requested end: {result['requested_end']}")
        
        if result['conflicting_events']:
            print(f"   Conflicting events:")
            for event in result['conflicting_events']:
                print(f"     • {event['summary']} ({event['start']} - {event['end']})")
        else:
            print(f"   No conflicting events found")
        
        if 'error' in result:
            print(f"   Error: {result['error']}")
        
        # Compare with what we expect
        print(f"\n🎯 **ANALYSIS:**")
        if result['available']:
            print(f"✅ Function correctly shows you're AVAILABLE")
            print(f"🎉 This should lead to an ACCEPTING draft")
        else:
            print(f"❌ Function shows you're BUSY")
            if result['conflicting_events']:
                print(f"🔍 Need to investigate these conflicts:")
                for event in result['conflicting_events']:
                    print(f"     • '{event['summary']}' - is this a real conflict?")
            else:
                print(f"🐛 No conflicts listed but shows busy - function bug")
        
        return result
        
    except Exception as e:
        print(f"❌ Error testing availability function: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_timezone_handling():
    """Check if timezone differences are causing issues"""
    
    print(f"\n🌍 **TESTING TIMEZONE HANDLING**")
    print("-" * 50)
    
    try:
        import pytz
        from datetime import datetime
        
        # Test different timezone representations
        target_time_variants = [
            "2025-08-18T12:00:00",
            "2025-08-18T12:00:00+05:30",
            "2025-08-18T06:30:00+00:00",  # UTC equivalent of 12:00 IST
        ]
        
        print("🕐 Testing different timezone representations:")
        
        for i, time_str in enumerate(target_time_variants, 1):
            print(f"\n{i}. Testing: {time_str}")
            
            try:
                from tools.calendar import _check_calendar_availability_impl
                
                result = _check_calendar_availability_impl(
                    start_time=time_str,
                    duration_minutes=30
                )
                
                print(f"   Result: {'Available' if result['available'] else 'Busy'}")
                print(f"   Conflicts: {len(result.get('conflicting_events', []))}")
                if result.get('conflicting_events'):
                    for event in result['conflicting_events']:
                        print(f"     - {event['summary']}")
                
            except Exception as e:
                print(f"   Error: {e}")
        
        # Show current timezone info
        print(f"\n🌍 **TIMEZONE INFO:**")
        now = datetime.now()
        ist = pytz.timezone('Asia/Kolkata')
        utc = pytz.timezone('UTC')
        
        now_ist = ist.localize(now) if now.tzinfo is None else now.astimezone(ist)
        now_utc = now_ist.astimezone(utc)
        
        print(f"Current time IST: {now_ist}")
        print(f"Current time UTC: {now_utc}")
        print(f"Tomorrow 12 PM IST: {now_ist.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)}")
        
    except Exception as e:
        print(f"❌ Error in timezone testing: {e}")

def test_declined_event_filtering():
    """Test if declined events are being properly filtered"""
    
    print(f"\n🚫 **TESTING DECLINED EVENT FILTERING**")
    print("-" * 50)
    
    try:
        service = calendar_service.get_service()
        
        # Get events around tomorrow 12 PM
        tomorrow_12pm = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        import pytz
        local_tz = pytz.timezone('Asia/Kolkata')
        if tomorrow_12pm.tzinfo is None:
            tomorrow_12pm = local_tz.localize(tomorrow_12pm)
        
        start_window = tomorrow_12pm - timedelta(minutes=30)
        end_window = tomorrow_12pm + timedelta(minutes=30)
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_window.isoformat(),
            timeMax=end_window.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events_in_window = events_result.get('items', [])
        
        print(f"📅 Events around 12 PM tomorrow ({len(events_in_window)} found):")
        
        declined_events = []
        accepted_events = []
        
        for event in events_in_window:
            event_start = event.get('start', {})
            
            # Skip all-day events
            if 'date' in event_start:
                continue
            
            attendees = event.get('attendees', [])
            user_status = None
            
            for attendee in attendees:
                if attendee.get('self', False):
                    user_status = attendee.get('responseStatus')
                    break
            
            event_info = {
                'summary': event.get('summary', 'Untitled'),
                'start': event_start.get('dateTime'),
                'status': user_status or 'No response'
            }
            
            if user_status == 'declined':
                declined_events.append(event_info)
            else:
                accepted_events.append(event_info)
            
            print(f"   • {event_info['summary']}")
            print(f"     Time: {event_info['start']}")
            print(f"     Your response: {event_info['status']}")
            print(f"     Should be filtered: {'YES' if user_status == 'declined' else 'NO'}")
            print()
        
        print(f"📊 **FILTERING ANALYSIS:**")
        print(f"   Events you DECLINED: {len(declined_events)} (should be ignored)")
        print(f"   Events you ACCEPTED/No response: {len(accepted_events)} (real conflicts)")
        
        if declined_events:
            print(f"\n🚫 **DECLINED EVENTS (should NOT cause conflicts):**")
            for event in declined_events:
                print(f"   • {event['summary']} at {event['start']}")
        
        if accepted_events:
            print(f"\n✅ **REAL CONFLICTS:**")
            for event in accepted_events:
                print(f"   • {event['summary']} at {event['start']}")
        else:
            print(f"\n✅ **NO REAL CONFLICTS** - You should be available!")
        
        return len(accepted_events) == 0
        
    except Exception as e:
        print(f"❌ Error testing declined event filtering: {e}")
        return False

def main():
    """Run calendar debugging"""
    
    print("🚀 **CALENDAR CONFLICT DEBUGGING**")
    print("This will help identify why you're showing as 'busy' when you should be free")
    
    config.DEBUG = True
    
    # Debug the specific time
    is_actually_free = debug_calendar_for_specific_time()
    
    # Debug Daily Meet specifically
    debug_daily_meet_specifically()
    
    # Test declined event filtering
    no_real_conflicts = test_declined_event_filtering()
    
    # Test the function directly
    function_result = test_availability_function_directly()
    
    # Test timezone handling
    compare_timezone_handling()
    
    print("\n" + "=" * 60)
    print("🎯 **SUMMARY & RECOMMENDATIONS:**")
    
    if is_actually_free and no_real_conflicts:
        print("✅ You ARE actually free at 12 PM tomorrow")
        print("🐛 The conflict detection has a bug - need to fix the logic")
        print("\n🔧 Likely fixes needed:")
        print("1. Fix declined event filtering")
        print("2. Fix timezone handling")
        print("3. Check recurring event handling")
    else:
        print("❌ You actually DO have conflicts at 12 PM tomorrow")
        print("📅 The calendar detection is correct")
        print("\n🔧 Actions needed:")
        print("1. Check if you want to decline the conflicting event")
        print("2. Verify the event times are correct")
        print("3. Consider rescheduling if needed")
    
    print(f"\n📋 **NEXT STEPS:**")
    print("1. Review the 'Daily Meet' event details above")
    print("2. If it's a false conflict, check if you declined it")
    print("3. If timezone issues, update the calendar tool")
    print("4. Re-test with: python gmail_realtime_agent.py")
    
    if function_result and not function_result['available']:
        print(f"\n🚨 **URGENT:** The availability function is incorrectly showing busy")
        print("This needs to be fixed in the calendar tool logic")
        
        # Provide specific fix recommendations
        if function_result.get('conflicting_events'):
            print(f"\n🔧 **SPECIFIC ISSUE FOUND:**")
            for event in function_result['conflicting_events']:
                print(f"   Event: '{event['summary']}'")
                print(f"   Time: {event['start']} - {event['end']}")
                print(f"   Recommendation: Check if this is declined or should be filtered")

if __name__ == "__main__":
    main()