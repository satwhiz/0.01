#!/usr/bin/env python3
"""
Apply DateTime Fix to Calendar Tool
This script fixes the datetime format issue in the calendar tool
"""

import os
import re

def fix_calendar_tool():
    """Fix the datetime formatting in tools/calendar.py"""
    
    calendar_file = "tools/calendar.py"
    
    if not os.path.exists(calendar_file):
        print(f"❌ {calendar_file} not found")
        return False
    
    print("🔧 Applying datetime fix to tools/calendar.py...")
    
    # Read the current file
    with open(calendar_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Add timezone handling to _check_calendar_availability_impl
    availability_fix = '''def _check_calendar_availability_impl(
    start_time: str, 
    end_time: str = None, 
    duration_minutes: int = 60
) -> Dict[str, Any]:
    """
    Internal implementation of calendar availability check
    """
    try:
        service = calendar_service.get_service()
        
        # Parse start time
        start_dt = parser.parse(start_time)
        
        # Calculate end time if not provided
        if end_time:
            end_dt = parser.parse(end_time)
        else:
            end_dt = start_dt + timedelta(minutes=duration_minutes)
        
        # Ensure timezone awareness - Google Calendar API requires RFC3339 format with timezone
        if start_dt.tzinfo is None:
            # Assume local timezone if not specified
            local_tz = pytz.timezone('UTC')  # You can change this to your local timezone
            start_dt = local_tz.localize(start_dt)
        
        if end_dt.tzinfo is None:
            # Assume same timezone as start time
            if start_dt.tzinfo:
                end_dt = start_dt.tzinfo.localize(end_dt.replace(tzinfo=None))
            else:
                local_tz = pytz.timezone('UTC')
                end_dt = local_tz.localize(end_dt)
        
        # Convert to RFC3339 format for Calendar API (with timezone)
        start_rfc = start_dt.isoformat()
        end_rfc = end_dt.isoformat()
        
        if config.DEBUG:
            print(f"Checking availability from {start_rfc} to {end_rfc}")
        
        # Query calendar for events in this time range
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_rfc,
            timeMax=end_rfc,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Filter out declined events and all-day events
        conflicting_events = []
        for event in events:
            # Skip if user declined
            attendees = event.get('attendees', [])
            user_status = None
            for attendee in attendees:
                if attendee.get('self', False):
                    user_status = attendee.get('responseStatus')
                    break
            
            if user_status == 'declined':
                continue
            
            # Skip all-day events (they don't have 'dateTime')
            if 'date' in event.get('start', {}) and 'dateTime' not in event.get('start', {}):
                continue
            
            conflicting_events.append({
                'summary': event.get('summary', 'Untitled Event'),
                'start': event.get('start', {}).get('dateTime'),
                'end': event.get('end', {}).get('dateTime'),
                'status': event.get('status', 'confirmed')
            })
        
        is_available = len(conflicting_events) == 0
        
        result = {
            'available': is_available,
            'requested_start': start_rfc,
            'requested_end': end_rfc,
            'conflicting_events': conflicting_events,
            'total_conflicts': len(conflicting_events)
        }
        
        if config.DEBUG:
            print(f"Availability check result: {'Available' if is_available else 'Busy'}")
            if conflicting_events:
                print(f"Conflicts: {[e['summary'] for e in conflicting_events]}")
        
        return result
        
    except Exception as e:
        if config.DEBUG:
            print(f"Error checking calendar availability: {e}")
        return {
            'available': False,
            'error': str(e),
            'requested_start': start_time,
            'requested_end': end_time or 'calculated',
            'total_conflicts': 0,
            'conflicting_events': []
        }'''
    
    # Replace the existing function
    pattern = r'def _check_calendar_availability_impl\(.*?\n(?:.*?\n)*?        return {[^}]*?}'
    content = re.sub(pattern, availability_fix, content, flags=re.DOTALL)
    
    # Fix 2: Add timezone handling to _find_free_time_slots_impl
    # Add timezone awareness to datetime.now() calls
    content = content.replace(
        'current_time = max(start_search, datetime.now() + timedelta(hours=1))',
        'current_time = max(start_search, datetime.now().replace(tzinfo=start_search.tzinfo) + timedelta(hours=1))'
    )
    
    # Add timezone localization at the beginning of the function
    find_slots_fix = '''        # Define search range with proper timezone
        start_search = datetime.now()
        end_search = start_search + timedelta(days=days_ahead)
        
        # Add timezone awareness
        local_tz = pytz.timezone('UTC')  # Change to your timezone if needed
        if start_search.tzinfo is None:
            start_search = local_tz.localize(start_search)
        if end_search.tzinfo is None:
            end_search = local_tz.localize(end_search)'''
    
    content = content.replace(
        '''        # Define search range
        start_search = datetime.now()
        end_search = start_search + timedelta(days=days_ahead)''',
        find_slots_fix
    )
    
    # Write the fixed content back
    with open(calendar_file, 'w') as f:
        f.write(content)
    
    print("✅ Applied datetime fixes to tools/calendar.py")
    return True

def main():
    """Apply the datetime fixes"""
    print("🚀 Applying Calendar DateTime Fixes")
    print("This will fix the Google Calendar API datetime format issues")
    
    if fix_calendar_tool():
        print("\n✅ Fixes applied successfully!")
        print("\n📋 Next steps:")
        print("1. Run the test again: python test_calendar_integration.py")
        print("2. All calendar API calls should now work properly")
        print("3. If tests pass, you can use: python gmail_realtime_agent.py")
    else:
        print("\n❌ Failed to apply fixes")
        print("Please check that tools/calendar.py exists and try again")

if __name__ == "__main__":
    main()