"""
LLM-Powered Calendar Tool - Google Calendar API integration with DeepSeek AI
Uses LLM for time extraction and meeting request classification instead of regex
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from agno.tools import tool
from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from config import config
from dateutil import parser
import pytz

def get_deepseek_model():
    """Get DeepSeek model for LLM operations"""
    return DeepSeek(
        id=config.DEFAULT_MODEL,
        api_key=config.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

class CalendarService:
    """Handles Google Calendar API operations"""
    
    def __init__(self):
        self.service = None
        # Calendar API requires additional scope
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/calendar'
        ]
    
    def authenticate(self):
        """Authenticate with Google Calendar API"""
        creds = None
        
        # Load existing credentials
        if os.path.exists(config.GMAIL_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(
                config.GMAIL_TOKEN_FILE, 
                self.scopes
            )
        
        # If credentials are invalid or don't exist, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    if config.DEBUG:
                        print("Refreshed calendar credentials")
                except Exception as e:
                    if config.DEBUG:
                        print(f"Failed to refresh calendar credentials: {e}")
                    creds = None
            
            if not creds or not creds.valid:
                if not os.path.exists(config.GMAIL_CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {config.GMAIL_CREDENTIALS_FILE}"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GMAIL_CREDENTIALS_FILE, 
                    self.scopes
                )
                creds = flow.run_local_server(port=0)
                if config.DEBUG:
                    print("Obtained new calendar credentials")
            
            # Save credentials for future use
            with open(config.GMAIL_TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
                if config.DEBUG:
                    print(f"Saved calendar credentials to {config.GMAIL_TOKEN_FILE}")
        
        # Build and return Calendar service
        self.service = build('calendar', 'v3', credentials=creds)
        if config.DEBUG:
            print("Calendar service authenticated successfully")
        
        return self.service

    def get_service(self):
        """Get Calendar service object (authenticate if needed)"""
        if not self.service:
            return self.authenticate()
        return self.service

# Global calendar service instance
calendar_service = CalendarService()

def llm_extract_time_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Use LLM to extract time suggestions from email text
    
    Args:
        text: Email content to analyze
        
    Returns:
        List of extracted time suggestions with parsed datetime objects
    """
    current_datetime = datetime.now()
    current_date = current_datetime.strftime("%A, %B %d, %Y")
    current_time = current_datetime.strftime("%I:%M %p")
    
    extraction_prompt = f"""You are a time extraction expert. Analyze the email text and extract any specific meeting times mentioned.

**Current Context:**
- Today is: {current_date}
- Current time: {current_time}
- Year: {current_datetime.year}

**Email Text to Analyze:**
{text}

**Task:**
Extract ALL specific meeting times mentioned in the email. For each time found, provide:
1. The exact phrase from the email
2. The absolute date and time it refers to
3. Your confidence level (0.1 to 1.0)

**Output Format (JSON):**
Return a JSON array of objects with this exact structure:
[
    {{
        "original_phrase": "exact text from email",
        "absolute_datetime": "YYYY-MM-DD HH:MM:SS",
        "confidence": 0.9,
        "reasoning": "brief explanation of parsing"
    }}
]

**Rules:**
- Only extract specific times (e.g., "2pm tomorrow", "Monday at 10AM", "March 15th at 3pm")
- Skip vague references (e.g., "sometime next week", "when you're free")
- Convert relative times to absolute dates (tomorrow = {(current_datetime + timedelta(days=1)).strftime('%Y-%m-%d')})
- Use 24-hour format for absolute_datetime
- If no specific times found, return empty array []

**Examples:**
"Can we meet tomorrow at 2pm?" → [{{"original_phrase": "tomorrow at 2pm", "absolute_datetime": "{(current_datetime + timedelta(days=1)).strftime('%Y-%m-%d')} 14:00:00", "confidence": 0.9}}]

"How about next Tuesday at 10:30 AM?" → [{{"original_phrase": "next Tuesday at 10:30 AM", "absolute_datetime": "calculate-next-tuesday 10:30:00", "confidence": 0.9}}]

Extract times from the email now:"""

    try:
        # Use DeepSeek to extract times
        extraction_agent = Agent(
            model=get_deepseek_model(),
            instructions="You are a precise time extraction expert. Return only valid JSON arrays.",
            markdown=False
        )
        
        response = extraction_agent.run(extraction_prompt)
        
        if config.DEBUG:
            print(f"🤖 LLM Time Extraction Response: {response.content.strip()}")
        
        # Parse the JSON response
        try:
            # Clean the response to extract JSON
            response_text = response.content.strip()
            
            # Remove any markdown formatting
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            response_text = response_text.strip()
            
            # Parse JSON
            extracted_times = json.loads(response_text)
            
            # Convert to our format
            time_suggestions = []
            
            for time_data in extracted_times:
                try:
                    # Parse the absolute datetime
                    datetime_str = time_data['absolute_datetime']
                    
                    # Handle special cases like "calculate-next-tuesday"
                    if "calculate-next-tuesday" in datetime_str:
                        # Find next Tuesday
                        days_ahead = (1 - current_datetime.weekday()) % 7  # Tuesday = 1
                        if days_ahead == 0:
                            days_ahead = 7
                        next_tuesday = current_datetime + timedelta(days=days_ahead)
                        time_part = datetime_str.split(" ")[1]  # Get the time part
                        datetime_str = f"{next_tuesday.strftime('%Y-%m-%d')} {time_part}"
                    
                    parsed_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                    
                    time_suggestions.append({
                        'original_text': time_data['original_phrase'],
                        'parsed_datetime': parsed_datetime,
                        'confidence': time_data.get('confidence', 0.8),
                        'reasoning': time_data.get('reasoning', 'LLM extraction')
                    })
                    
                    if config.DEBUG:
                        print(f"✅ Extracted: '{time_data['original_phrase']}' → {parsed_datetime}")
                        
                except (ValueError, KeyError) as e:
                    if config.DEBUG:
                        print(f"❌ Failed to parse time data: {time_data} - {e}")
                    continue
            
            return time_suggestions
            
        except json.JSONDecodeError as e:
            if config.DEBUG:
                print(f"❌ Failed to parse LLM JSON response: {e}")
                print(f"Response was: {response.content}")
            return []
        
    except Exception as e:
        if config.DEBUG:
            print(f"❌ Error in LLM time extraction: {e}")
        return []

def llm_analyze_meeting_request(email_content: str) -> Dict[str, Any]:
    """
    Use LLM to analyze email for meeting requests and classify request type
    
    Args:
        email_content: Full email content to analyze
        
    Returns:
        Dict with meeting request analysis
    """
    
    analysis_prompt = f"""You are a meeting request analyzer. Analyze this email to determine if it's requesting a meeting and what type of request it is.

**Email Content:**
{email_content}

**Task:**
Analyze the email and provide a detailed classification.

**Output Format (JSON):**
Return a JSON object with this exact structure:
{{
    "is_meeting_request": true/false,
    "request_type": "specific_time_suggested" | "general_meeting_request" | "none",
    "confidence": 0.0-1.0,
    "meeting_keywords_found": ["list", "of", "keywords"],
    "meeting_topic": "brief description of what the meeting is about",
    "urgency_level": "low" | "medium" | "high",
    "reasoning": "explanation of your analysis"
}}

**Request Type Definitions:**
- "specific_time_suggested": Email contains specific date/time suggestions (e.g., "tomorrow at 2pm", "Monday at 10AM")
- "general_meeting_request": Asks for a meeting but no specific time (e.g., "let's schedule a call", "when are you available?")
- "none": Not a meeting request

**Meeting Keywords to Look For:**
meeting, call, chat, discuss, catch up, sync, conference, appointment, schedule, available, connect, talk, session, demo, presentation, video call, phone call, zoom, meet

**Examples:**
"Can we meet tomorrow at 2pm?" → {{"is_meeting_request": true, "request_type": "specific_time_suggested"}}
"Let's schedule a call sometime" → {{"is_meeting_request": true, "request_type": "general_meeting_request"}}
"Here are the documents you requested" → {{"is_meeting_request": false, "request_type": "none"}}

Analyze the email now:"""

    try:
        # Use DeepSeek to analyze the meeting request
        analysis_agent = Agent(
            model=get_deepseek_model(),
            instructions="You are a precise meeting request analyzer. Return only valid JSON.",
            markdown=False
        )
        
        response = analysis_agent.run(analysis_prompt)
        
        if config.DEBUG:
            print(f"🤖 LLM Meeting Analysis Response: {response.content.strip()}")
        
        # Parse the JSON response
        try:
            # Clean the response to extract JSON
            response_text = response.content.strip()
            
            # Remove any markdown formatting
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            response_text = response_text.strip()
            
            # Parse JSON
            analysis_result = json.loads(response_text)
            
            # Also extract time suggestions using the time extraction function
            time_suggestions = llm_extract_time_from_text(email_content)
            
            # Add time suggestions to the analysis
            analysis_result['time_suggestions'] = time_suggestions
            analysis_result['existing_scheduling_links'] = []  # Could add LLM detection for this too
            
            # Validate and set defaults
            analysis_result['is_meeting_request'] = analysis_result.get('is_meeting_request', False)
            analysis_result['request_type'] = analysis_result.get('request_type', 'none')
            analysis_result['confidence'] = analysis_result.get('confidence', 0.5)
            analysis_result['meeting_keywords_found'] = analysis_result.get('meeting_keywords_found', [])
            analysis_result['meeting_topic'] = analysis_result.get('meeting_topic', 'General discussion')
            analysis_result['urgency_level'] = analysis_result.get('urgency_level', 'medium')
            
            return analysis_result
            
        except json.JSONDecodeError as e:
            if config.DEBUG:
                print(f"❌ Failed to parse LLM analysis JSON: {e}")
                print(f"Response was: {response.content}")
            
            # Fallback to basic analysis
            return {
                'is_meeting_request': False,
                'request_type': 'none',
                'time_suggestions': [],
                'existing_scheduling_links': [],
                'meeting_keywords_found': [],
                'confidence': 0.1,
                'meeting_topic': 'Unknown',
                'urgency_level': 'medium',
                'reasoning': 'LLM analysis failed, using fallback'
            }
        
    except Exception as e:
        if config.DEBUG:
            print(f"❌ Error in LLM meeting analysis: {e}")
        
        # Fallback to basic analysis
        return {
            'is_meeting_request': False,
            'request_type': 'none',
            'time_suggestions': [],
            'existing_scheduling_links': [],
            'meeting_keywords_found': [],
            'confidence': 0.1,
            'meeting_topic': 'Unknown',
            'urgency_level': 'medium',
            'reasoning': f'LLM analysis error: {str(e)}'
        }

# Replace the old functions with LLM-powered versions
def extract_time_from_text(text: str) -> List[Dict[str, Any]]:
    """
    LLM-powered time extraction (replaces regex version)
    """
    return llm_extract_time_from_text(text)

def extract_meeting_request_from_email(email_content: str) -> Dict[str, Any]:
    """
    LLM-powered meeting request analysis (replaces regex version)
    """
    return llm_analyze_meeting_request(email_content)

def _check_calendar_availability_impl(
    start_time: str, 
    end_time: str = None, 
    duration_minutes: int = 60
) -> Dict[str, Any]:
    """
    Internal implementation of calendar availability check - FIXED TIMEZONE HANDLING
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
        
        # FIXED: Proper timezone handling for IST
        import pytz
        ist_tz = pytz.timezone('Asia/Kolkata')
        
        # If no timezone info, assume IST (your local timezone)
        if start_dt.tzinfo is None:
            start_dt = ist_tz.localize(start_dt)
            if config.DEBUG:
                print(f"🌍 Localized start time to IST: {start_dt}")
        
        if end_dt.tzinfo is None:
            end_dt = ist_tz.localize(end_dt)
            if config.DEBUG:
                print(f"🌍 Localized end time to IST: {end_dt}")
        
        # Convert to RFC3339 format for Calendar API (keeps timezone info)
        start_rfc = start_dt.isoformat()
        end_rfc = end_dt.isoformat()
        
        if config.DEBUG:
            print(f"🔍 Checking availability from {start_rfc} to {end_rfc}")
            print(f"📅 This is {start_dt.strftime('%A, %B %d at %I:%M %p %Z')} to {end_dt.strftime('%I:%M %p %Z')}")
        
        # Query calendar for events in this time range
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_rfc,
            timeMax=end_rfc,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if config.DEBUG:
            print(f"📋 Found {len(events)} events in time range")
        
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
                if config.DEBUG:
                    print(f"⏭️  Skipping declined event: {event.get('summary')}")
                continue
            
            # Skip all-day events (they don't have 'dateTime')
            event_start = event.get('start', {})
            if 'date' in event_start and 'dateTime' not in event_start:
                if config.DEBUG:
                    print(f"⏭️  Skipping all-day event: {event.get('summary')}")
                continue
            
            # Check if this event actually overlaps
            if 'dateTime' in event_start:
                event_start_dt = parser.parse(event_start['dateTime'])
                event_end_dt = parser.parse(event.get('end', {}).get('dateTime'))
                
                # FIXED: Proper overlap detection with timezone awareness
                overlaps = (event_start_dt < end_dt and event_end_dt > start_dt)
                
                if config.DEBUG:
                    print(f"🔍 Event: {event.get('summary')}")
                    print(f"   Event time: {event_start_dt} to {event_end_dt}")
                    print(f"   Request time: {start_dt} to {end_dt}")
                    print(f"   Overlaps: {overlaps}")
                
                if overlaps:
                    conflicting_events.append({
                        'summary': event.get('summary', 'Untitled Event'),
                        'start': event_start['dateTime'],
                        'end': event.get('end', {}).get('dateTime'),
                        'status': event.get('status', 'confirmed')
                    })
                    
                    if config.DEBUG:
                        print(f"❌ CONFLICT: {event.get('summary')} overlaps with requested time")
        
        is_available = len(conflicting_events) == 0
        
        result = {
            'available': is_available,
            'requested_start': start_rfc,
            'requested_end': end_rfc,
            'conflicting_events': conflicting_events,
            'total_conflicts': len(conflicting_events)
        }
        
        if config.DEBUG:
            print(f"✅ Availability check result: {'Available' if is_available else 'Busy'}")
            if conflicting_events:
                print(f"❌ Conflicts found: {[e['summary'] for e in conflicting_events]}")
            else:
                print(f"✅ No conflicts - you're free!")
        
        return result
        
    except Exception as e:
        if config.DEBUG:
            print(f"❌ Error checking calendar availability: {e}")
            import traceback
            traceback.print_exc()
        return {
            'available': False,
            'error': str(e),
            'requested_start': start_time,
            'requested_end': end_time or 'calculated',
            'total_conflicts': 0,
            'conflicting_events': []
        }

@tool(
    name="check_calendar_availability",
    description="Check if user is available at a specific time by querying Google Calendar",
    show_result=False
)
def check_calendar_availability(
    start_time: str, 
    end_time: str = None, 
    duration_minutes: int = 60
) -> Dict[str, Any]:
    """
    Check calendar availability for a specific time slot
    
    Args:
        start_time: Start time in ISO format (e.g., "2024-01-15T14:00:00")
        end_time: End time in ISO format (optional, will use duration if not provided)
        duration_minutes: Meeting duration in minutes (default: 60)
        
    Returns:
        Dict with availability status and conflicting events if any
    """
    return _check_calendar_availability_impl(start_time, end_time, duration_minutes)

def _find_free_time_slots_impl(
    days_ahead: int = 7,
    duration_minutes: int = 60,
    business_hours_only: bool = True,
    max_suggestions: int = 5
) -> Dict[str, Any]:
    """
    Internal implementation of finding free time slots - FIXED TIMEZONE HANDLING
    """
    try:
        service = calendar_service.get_service()
        
        # FIXED: Proper timezone handling from the start
        import pytz
        ist_tz = pytz.timezone('Asia/Kolkata')
        
        # Define search range with proper timezone
        start_search = datetime.now()
        if start_search.tzinfo is None:
            start_search = ist_tz.localize(start_search)
        
        end_search = start_search + timedelta(days=days_ahead)
        
        if config.DEBUG:
            print(f"🔍 Searching for free slots from {start_search} to {end_search}")
        
        # Get all events in the search range
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_search.isoformat(),
            timeMax=end_search.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Parse busy times
        busy_times = []
        for event in events:
            # Skip declined events
            attendees = event.get('attendees', [])
            user_declined = False
            for attendee in attendees:
                if attendee.get('self', False) and attendee.get('responseStatus') == 'declined':
                    user_declined = True
                    break
            
            if user_declined:
                continue
            
            # Skip all-day events
            event_start = event.get('start', {})
            if 'dateTime' not in event_start:
                continue
            
            busy_start = parser.parse(event_start['dateTime'])
            busy_end = parser.parse(event.get('end', {}).get('dateTime'))
            
            busy_times.append((busy_start, busy_end))
        
        # Sort busy times
        busy_times.sort(key=lambda x: x[0])
        
        # Find free slots
        free_slots = []
        current_time = max(start_search, datetime.now())
        if current_time.tzinfo is None:
            current_time = ist_tz.localize(current_time)
        
        # Add 1 hour buffer
        current_time = current_time + timedelta(hours=1)
        
        for day_offset in range(days_ahead):
            day_start = (start_search + timedelta(days=day_offset)).replace(hour=9, minute=0, second=0, microsecond=0)
            day_end = day_start.replace(hour=17, minute=0)  # 5 PM
            
            if business_hours_only:
                # Skip weekends
                if day_start.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    continue
                
                search_start = max(current_time, day_start)
                search_end = day_end
            else:
                search_start = max(current_time, day_start.replace(hour=8))
                search_end = day_start.replace(hour=20)  # Until 8 PM
            
            # Check for free slots in this day
            slot_start = search_start
            
            while slot_start + timedelta(minutes=duration_minutes) <= search_end:
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                
                # Check if this slot conflicts with any busy time
                is_free = True
                for busy_start, busy_end in busy_times:
                    if (slot_start < busy_end and slot_end > busy_start):
                        is_free = False
                        # Jump to end of this busy period
                        slot_start = busy_end
                        break
                
                if is_free:
                    free_slots.append({
                        'start': slot_start.isoformat(),
                        'end': slot_end.isoformat(),
                        'duration_minutes': duration_minutes,
                        'day_of_week': slot_start.strftime('%A'),
                        'formatted_time': slot_start.strftime('%A, %B %d at %I:%M %p')
                    })
                    
                    if len(free_slots) >= max_suggestions:
                        break
                    
                    # Move to next possible slot (minimum 30 min gap)
                    slot_start = slot_end + timedelta(minutes=30)
                else:
                    # Continue from current position if no conflict was found
                    if slot_start == search_start or not any(slot_start < busy_end for busy_start, busy_end in busy_times):
                        slot_start += timedelta(minutes=30)
            
            if len(free_slots) >= max_suggestions:
                break
        
        return {
            'free_slots': free_slots[:max_suggestions],
            'search_days': days_ahead,
            'duration_requested': duration_minutes,
            'business_hours_only': business_hours_only
        }
        
    except Exception as e:
        if config.DEBUG:
            print(f"Error finding free time slots: {e}")
        return {
            'free_slots': [],
            'error': str(e)
        }

@tool(
    name="find_free_time_slots",
    description="Find available time slots in the user's calendar for scheduling",
    show_result=False
)
def find_free_time_slots(
    days_ahead: int = 7,
    duration_minutes: int = 60,
    business_hours_only: bool = True,
    max_suggestions: int = 5
) -> Dict[str, Any]:
    """
    Find available time slots in the coming days
    
    Args:
        days_ahead: Number of days to look ahead (default: 7)
        duration_minutes: Required meeting duration (default: 60)
        business_hours_only: Only suggest business hours 9am-5pm (default: True)
        max_suggestions: Maximum number of suggestions to return
        
    Returns:
        Dict with list of available time slots
    """
    return _find_free_time_slots_impl(days_ahead, duration_minutes, business_hours_only, max_suggestions)

@tool(
    name="generate_calendar_invite_details",
    description="Generate details for a calendar invite including Google Meet link",
    show_result=False
)
def generate_calendar_invite_details(
    meeting_time: str,
    duration_minutes: int = 60,
    meeting_title: str = None,
    attendee_email: str = None
) -> Dict[str, Any]:
    """
    Generate calendar invite details including Google Meet link
    
    Args:
        meeting_time: Meeting start time in ISO format
        duration_minutes: Meeting duration (default: 60)
        meeting_title: Title for the meeting (optional)
        attendee_email: Email of the person to invite (optional)
        
    Returns:
        Dict with calendar invite details
    """
    try:
        start_dt = parser.parse(meeting_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        
        # Generate a basic Google Meet link (placeholder)
        # In a real implementation, you'd create this through Google Calendar API
        meet_id = f"abc-defg-hij"  # This would be generated by Google
        meet_link = f"https://meet.google.com/{meet_id}"
        
        invite_details = {
            'title': meeting_title or "Meeting",
            'start_time': start_dt.isoformat(),
            'end_time': end_dt.isoformat(),
            'duration_minutes': duration_minutes,
            'google_meet_link': meet_link,
            'attendee_email': attendee_email,
            'formatted_time': start_dt.strftime('%A, %B %d, %Y at %I:%M %p'),
            'calendar_invite_text': f"""
📅 Meeting Invitation

📅 When: {start_dt.strftime('%A, %B %d, %Y at %I:%M %p')}
⏱️ Duration: {duration_minutes} minutes
🔗 Google Meet: {meet_link}

Please add this to your calendar and join using the Google Meet link above.
            """.strip()
        }
        
        return invite_details
        
    except Exception as e:
        if config.DEBUG:
            print(f"Error generating calendar invite details: {e}")
        return {
            'error': str(e),
            'meeting_time': meeting_time
        }

def get_user_scheduling_link() -> str:
    """
    Get user's scheduling link from environment or config
    This should be configured in the .env file
    """
    scheduling_link = os.getenv("USER_SCHEDULING_LINK", "")
    
    if not scheduling_link:
        # Fallback scheduling link placeholder
        scheduling_link = "[Your scheduling link - please configure USER_SCHEDULING_LINK in .env file]"
    
    return scheduling_link

# Expose the internal implementations for direct calling in tests
check_calendar_availability_direct = _check_calendar_availability_impl
find_free_time_slots_direct = _find_free_time_slots_impl






# """
# Gmail Calendar Tool - Google Calendar API integration for email drafting
# Provides calendar functionality for checking availability and managing meetings
# """

# import os
# from datetime import datetime, timedelta
# from typing import List, Dict, Any, Optional, Tuple
# from googleapiclient.discovery import build
# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from agno.tools import tool
# from config import config
# import re
# from dateutil import parser
# import pytz

# class CalendarService:
#     """Handles Google Calendar API operations"""
    
#     def __init__(self):
#         self.service = None
#         # Calendar API requires additional scope
#         self.scopes = [
#             'https://www.googleapis.com/auth/gmail.modify',
#             'https://www.googleapis.com/auth/calendar'
#         ]
    
#     def authenticate(self):
#         """Authenticate with Google Calendar API"""
#         creds = None
        
#         # Load existing credentials
#         if os.path.exists(config.GMAIL_TOKEN_FILE):
#             creds = Credentials.from_authorized_user_file(
#                 config.GMAIL_TOKEN_FILE, 
#                 self.scopes
#             )
        
#         # If credentials are invalid or don't exist, get new ones
#         if not creds or not creds.valid:
#             if creds and creds.expired and creds.refresh_token:
#                 try:
#                     creds.refresh(Request())
#                     if config.DEBUG:
#                         print("Refreshed calendar credentials")
#                 except Exception as e:
#                     if config.DEBUG:
#                         print(f"Failed to refresh calendar credentials: {e}")
#                     creds = None
            
#             if not creds or not creds.valid:
#                 if not os.path.exists(config.GMAIL_CREDENTIALS_FILE):
#                     raise FileNotFoundError(
#                         f"Gmail credentials file not found: {config.GMAIL_CREDENTIALS_FILE}"
#                     )
                
#                 flow = InstalledAppFlow.from_client_secrets_file(
#                     config.GMAIL_CREDENTIALS_FILE, 
#                     self.scopes
#                 )
#                 creds = flow.run_local_server(port=0)
#                 if config.DEBUG:
#                     print("Obtained new calendar credentials")
            
#             # Save credentials for future use
#             with open(config.GMAIL_TOKEN_FILE, 'w') as token:
#                 token.write(creds.to_json())
#                 if config.DEBUG:
#                     print(f"Saved calendar credentials to {config.GMAIL_TOKEN_FILE}")
        
#         # Build and return Calendar service
#         self.service = build('calendar', 'v3', credentials=creds)
#         if config.DEBUG:
#             print("Calendar service authenticated successfully")
        
#         return self.service

#     def get_service(self):
#         """Get Calendar service object (authenticate if needed)"""
#         if not self.service:
#             return self.authenticate()
#         return self.service

# # Global calendar service instance
# calendar_service = CalendarService()

# def extract_time_from_text(text: str) -> List[Dict[str, Any]]:
#     """
#     Extract time suggestions from email text using NLP patterns
    
#     Args:
#         text: Email content to analyze
        
#     Returns:
#         List of extracted time suggestions with parsed datetime objects
#     """
#     time_suggestions = []
    
#     # Common time patterns
#     patterns = [
#         # "Tuesday at 2pm", "Monday at 10:30 AM"
#         r'(\w+day)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))',
#         # "Tomorrow at 3pm", "Today at 11am"
#         r'(tomorrow|today)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))',
#         # "March 15th at 2pm", "Jan 20 at 10am"
#         r'(\w+\s+\d{1,2}(?:st|nd|rd|th)?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))',
#         # "2pm tomorrow", "10am next Tuesday"
#         r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))\s+(tomorrow|today|\w+day)',
#         # "How about 2pm on Tuesday?"
#         r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))\s+on\s+(\w+day)',
#         # ISO-like formats: "2024-01-15 14:00"
#         r'(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})',
#         # "Next week Tuesday 2pm"
#         r'(next\s+week\s+\w+day)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))'
#     ]
    
#     for pattern in patterns:
#         matches = re.finditer(pattern, text, re.IGNORECASE)
#         for match in matches:
#             try:
#                 # Try to parse the matched time expression
#                 time_str = f"{match.group(1)} {match.group(2)}"
#                 parsed_time = parser.parse(time_str, fuzzy=True)
                
#                 # If the parsed time is in the past, assume it's for next occurrence
#                 if parsed_time < datetime.now():
#                     if 'tomorrow' in time_str.lower():
#                         parsed_time = parsed_time + timedelta(days=1)
#                     elif 'next week' in time_str.lower():
#                         parsed_time = parsed_time + timedelta(weeks=1)
#                     elif any(day in time_str.lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
#                         # Find next occurrence of this weekday
#                         days_ahead = (parsed_time.weekday() - datetime.now().weekday()) % 7
#                         if days_ahead == 0:  # Today
#                             days_ahead = 7  # Next week
#                         parsed_time = datetime.now().replace(
#                             hour=parsed_time.hour, 
#                             minute=parsed_time.minute, 
#                             second=0, 
#                             microsecond=0
#                         ) + timedelta(days=days_ahead)
                
#                 time_suggestions.append({
#                     'original_text': match.group(0),
#                     'parsed_datetime': parsed_time,
#                     'confidence': 0.8  # Basic confidence scoring
#                 })
                
#             except (ValueError, OverflowError) as e:
#                 if config.DEBUG:
#                     print(f"Failed to parse time: {match.group(0)} - {e}")
#                 continue
    
#     return time_suggestions

# def _check_calendar_availability_impl(
#     start_time: str, 
#     end_time: str = None, 
#     duration_minutes: int = 60
# ) -> Dict[str, Any]:
#     """
#     Internal implementation of calendar availability check
#     """
#     try:
#         service = calendar_service.get_service()
        
#         # Parse start time
#         start_dt = parser.parse(start_time)
        
#         # Calculate end time if not provided
#         if end_time:
#             end_dt = parser.parse(end_time)
#         else:
#             end_dt = start_dt + timedelta(minutes=duration_minutes)
        
#         # Ensure timezone awareness - Google Calendar API requires RFC3339 format with timezone
#         if start_dt.tzinfo is None:
#             # Assume local timezone if not specified
#             local_tz = pytz.timezone('UTC')  # You can change this to your local timezone
#             start_dt = local_tz.localize(start_dt)
        
#         if end_dt.tzinfo is None:
#             # Assume same timezone as start time
#             if start_dt.tzinfo:
#                 end_dt = start_dt.tzinfo.localize(end_dt.replace(tzinfo=None))
#             else:
#                 local_tz = pytz.timezone('UTC')
#                 end_dt = local_tz.localize(end_dt)
        
#         # Convert to RFC3339 format for Calendar API (with timezone)
#         start_rfc = start_dt.isoformat()
#         end_rfc = end_dt.isoformat()
        
#         if config.DEBUG:
#             print(f"Checking availability from {start_rfc} to {end_rfc}")
        
#         # Query calendar for events in this time range
#         events_result = service.events().list(
#             calendarId='primary',
#             timeMin=start_rfc,
#             timeMax=end_rfc,
#             singleEvents=True,
#             orderBy='startTime'
#         ).execute()
        
#         events = events_result.get('items', [])
        
#         # Filter out declined events and all-day events
#         conflicting_events = []
#         for event in events:
#             # Skip if user declined
#             attendees = event.get('attendees', [])
#             user_status = None
#             for attendee in attendees:
#                 if attendee.get('self', False):
#                     user_status = attendee.get('responseStatus')
#                     break
            
#             if user_status == 'declined':
#                 continue
            
#             # Skip all-day events (they don't have 'dateTime')
#             if 'date' in event.get('start', {}) and 'dateTime' not in event.get('start', {}):
#                 continue
            
#             conflicting_events.append({
#                 'summary': event.get('summary', 'Untitled Event'),
#                 'start': event.get('start', {}).get('dateTime'),
#                 'end': event.get('end', {}).get('dateTime'),
#                 'status': event.get('status', 'confirmed')
#             })
        
#         is_available = len(conflicting_events) == 0
        
#         result = {
#             'available': is_available,
#             'requested_start': start_rfc,
#             'requested_end': end_rfc,
#             'conflicting_events': conflicting_events,
#             'total_conflicts': len(conflicting_events)
#         }
        
#         if config.DEBUG:
#             print(f"Availability check result: {'Available' if is_available else 'Busy'}")
#             if conflicting_events:
#                 print(f"Conflicts: {[e['summary'] for e in conflicting_events]}")
        
#         return result
        
#     except Exception as e:
#         if config.DEBUG:
#             print(f"Error checking calendar availability: {e}")
#         return {
#             'available': False,
#             'error': str(e),
#             'requested_start': start_time,
#             'requested_end': end_time or 'calculated',
#             'total_conflicts': 0,
#             'conflicting_events': []
#         }

# @tool(
#     name="check_calendar_availability",
#     description="Check if user is available at a specific time by querying Google Calendar",
#     show_result=False
# )
# def check_calendar_availability(
#     start_time: str, 
#     end_time: str = None, 
#     duration_minutes: int = 60
# ) -> Dict[str, Any]:
#     """
#     Check calendar availability for a specific time slot
    
#     Args:
#         start_time: Start time in ISO format (e.g., "2024-01-15T14:00:00")
#         end_time: End time in ISO format (optional, will use duration if not provided)
#         duration_minutes: Meeting duration in minutes (default: 60)
        
#     Returns:
#         Dict with availability status and conflicting events if any
#     """
#     return _check_calendar_availability_impl(start_time, end_time, duration_minutes)

# def _find_free_time_slots_impl(
#     days_ahead: int = 7,
#     duration_minutes: int = 60,
#     business_hours_only: bool = True,
#     max_suggestions: int = 5
# ) -> Dict[str, Any]:
#     """
#     Internal implementation of finding free time slots
#     """
#     try:
#         service = calendar_service.get_service()
        
#         # Define search range with proper timezone
#         start_search = datetime.now()
#         end_search = start_search + timedelta(days=days_ahead)
        
#         # Add timezone awareness
#         local_tz = pytz.timezone('UTC')  # Change to your timezone if needed
#         if start_search.tzinfo is None:
#             start_search = local_tz.localize(start_search)
#         if end_search.tzinfo is None:
#             end_search = local_tz.localize(end_search)
        
#         # Get all events in the search range
#         events_result = service.events().list(
#             calendarId='primary',
#             timeMin=start_search.isoformat(),
#             timeMax=end_search.isoformat(),
#             singleEvents=True,
#             orderBy='startTime'
#         ).execute()
        
#         events = events_result.get('items', [])
        
#         # Parse busy times
#         busy_times = []
#         for event in events:
#             # Skip declined events
#             attendees = event.get('attendees', [])
#             user_declined = False
#             for attendee in attendees:
#                 if attendee.get('self', False) and attendee.get('responseStatus') == 'declined':
#                     user_declined = True
#                     break
            
#             if user_declined:
#                 continue
            
#             # Skip all-day events
#             start_time = event.get('start', {})
#             if 'dateTime' not in start_time:
#                 continue
            
#             busy_start = parser.parse(start_time['dateTime'])
#             busy_end = parser.parse(event.get('end', {}).get('dateTime'))
            
#             busy_times.append((busy_start, busy_end))
        
#         # Sort busy times
#         busy_times.sort(key=lambda x: x[0])
        
#         # Find free slots
#         free_slots = []
#         current_time = max(start_search, datetime.now().replace(tzinfo=start_search.tzinfo) + timedelta(hours=1))
        
#         for day_offset in range(days_ahead):
#             day_start = (start_search + timedelta(days=day_offset)).replace(hour=9, minute=0, second=0, microsecond=0)
#             day_end = day_start.replace(hour=17, minute=0)  # 5 PM
            
#             if business_hours_only:
#                 # Skip weekends
#                 if day_start.weekday() >= 5:  # Saturday = 5, Sunday = 6
#                     continue
                
#                 search_start = max(current_time, day_start)
#                 search_end = day_end
#             else:
#                 search_start = max(current_time, day_start.replace(hour=8))
#                 search_end = day_start.replace(hour=20)  # Until 8 PM
            
#             # Check for free slots in this day
#             slot_start = search_start
            
#             while slot_start + timedelta(minutes=duration_minutes) <= search_end:
#                 slot_end = slot_start + timedelta(minutes=duration_minutes)
                
#                 # Check if this slot conflicts with any busy time
#                 is_free = True
#                 for busy_start, busy_end in busy_times:
#                     if (slot_start < busy_end and slot_end > busy_start):
#                         is_free = False
#                         # Jump to end of this busy period
#                         slot_start = busy_end
#                         break
                
#                 if is_free:
#                     free_slots.append({
#                         'start': slot_start.isoformat(),
#                         'end': slot_end.isoformat(),
#                         'duration_minutes': duration_minutes,
#                         'day_of_week': slot_start.strftime('%A'),
#                         'formatted_time': slot_start.strftime('%A, %B %d at %I:%M %p')
#                     })
                    
#                     if len(free_slots) >= max_suggestions:
#                         break
                    
#                     # Move to next possible slot (minimum 30 min gap)
#                     slot_start = slot_end + timedelta(minutes=30)
#                 else:
#                     # Continue from current position if no conflict was found
#                     if slot_start == search_start or not any(slot_start < busy_end for busy_start, busy_end in busy_times):
#                         slot_start += timedelta(minutes=30)
            
#             if len(free_slots) >= max_suggestions:
#                 break
        
#         return {
#             'free_slots': free_slots[:max_suggestions],
#             'search_days': days_ahead,
#             'duration_requested': duration_minutes,
#             'business_hours_only': business_hours_only
#         }
        
#     except Exception as e:
#         if config.DEBUG:
#             print(f"Error finding free time slots: {e}")
#         return {
#             'free_slots': [],
#             'error': str(e)
#         }

# @tool(
#     name="find_free_time_slots",
#     description="Find available time slots in the user's calendar for scheduling",
#     show_result=False
# )
# def find_free_time_slots(
#     days_ahead: int = 7,
#     duration_minutes: int = 60,
#     business_hours_only: bool = True,
#     max_suggestions: int = 5
# ) -> Dict[str, Any]:
#     """
#     Find available time slots in the coming days
    
#     Args:
#         days_ahead: Number of days to look ahead (default: 7)
#         duration_minutes: Required meeting duration (default: 60)
#         business_hours_only: Only suggest business hours 9am-5pm (default: True)
#         max_suggestions: Maximum number of suggestions to return
        
#     Returns:
#         Dict with list of available time slots
#     """
#     return _find_free_time_slots_impl(days_ahead, duration_minutes, business_hours_only, max_suggestions)

# def extract_meeting_request_from_email(email_content: str) -> Dict[str, Any]:
#     """
#     Analyze email content to detect meeting requests and extract suggested times
    
#     Args:
#         email_content: Full email content to analyze
        
#     Returns:
#         Dict with meeting request analysis and extracted times
#     """
#     # Keywords that indicate meeting requests
#     meeting_keywords = [
#         'meeting', 'call', 'chat', 'discuss', 'catch up', 'sync',
#         'conference', 'appointment', 'schedule', 'available',
#         'connect', 'talk', 'session', 'demo', 'presentation'
#     ]
    
#     # Check if email contains meeting-related keywords
#     content_lower = email_content.lower()
#     is_meeting_request = any(keyword in content_lower for keyword in meeting_keywords)
    
#     # Extract time suggestions from text
#     time_suggestions = extract_time_from_text(email_content)
    
#     # Look for scheduling links in the email
#     scheduling_patterns = [
#         r'calendly\.com/[\w\-/]+',
#         r'cal\.com/[\w\-/]+',
#         r'schedule\.?(?:once|meeting)\.?com/[\w\-/]+',
#         r'acuity(?:scheduling)?\.com/[\w\-/]+',
#         r'book(?:me|ing)\.[\w\-/.]+',
#     ]
    
#     existing_scheduling_links = []
#     for pattern in scheduling_patterns:
#         matches = re.finditer(pattern, email_content, re.IGNORECASE)
#         for match in matches:
#             existing_scheduling_links.append(match.group(0))
    
#     # Determine meeting request type
#     request_type = "none"
#     if time_suggestions:
#         request_type = "specific_time_suggested"
#     elif is_meeting_request:
#         request_type = "general_meeting_request"
    
#     return {
#         'is_meeting_request': is_meeting_request,
#         'request_type': request_type,
#         'time_suggestions': time_suggestions,
#         'existing_scheduling_links': existing_scheduling_links,
#         'meeting_keywords_found': [kw for kw in meeting_keywords if kw in content_lower],
#         'confidence': 0.9 if time_suggestions else (0.7 if is_meeting_request else 0.1)
#     }

# @tool(
#     name="extract_meeting_request_from_email",
#     description="Analyze email content to detect meeting requests and extract suggested times",
#     show_result=False
# )
# def extract_meeting_request_from_email_tool(email_content: str) -> Dict[str, Any]:
#     """
#     Tool wrapper for extracting meeting requests from email content
#     """
#     return extract_meeting_request_from_email(email_content)

# @tool(
#     name="generate_calendar_invite_details",
#     description="Generate details for a calendar invite including Google Meet link",
#     show_result=False
# )
# def generate_calendar_invite_details(
#     meeting_time: str,
#     duration_minutes: int = 60,
#     meeting_title: str = None,
#     attendee_email: str = None
# ) -> Dict[str, Any]:
#     """
#     Generate calendar invite details including Google Meet link
    
#     Args:
#         meeting_time: Meeting start time in ISO format
#         duration_minutes: Meeting duration (default: 60)
#         meeting_title: Title for the meeting (optional)
#         attendee_email: Email of the person to invite (optional)
        
#     Returns:
#         Dict with calendar invite details
#     """
#     try:
#         start_dt = parser.parse(meeting_time)
#         end_dt = start_dt + timedelta(minutes=duration_minutes)
        
#         # Generate a basic Google Meet link (placeholder)
#         # In a real implementation, you'd create this through Google Calendar API
#         meet_id = f"abc-defg-hij"  # This would be generated by Google
#         meet_link = f"https://meet.google.com/{meet_id}"
        
#         invite_details = {
#             'title': meeting_title or "Meeting",
#             'start_time': start_dt.isoformat(),
#             'end_time': end_dt.isoformat(),
#             'duration_minutes': duration_minutes,
#             'google_meet_link': meet_link,
#             'attendee_email': attendee_email,
#             'formatted_time': start_dt.strftime('%A, %B %d, %Y at %I:%M %p'),
#             'calendar_invite_text': f"""
# 📅 Meeting Invitation

# 📅 When: {start_dt.strftime('%A, %B %d, %Y at %I:%M %p')}
# ⏱️ Duration: {duration_minutes} minutes
# 🔗 Google Meet: {meet_link}

# Please add this to your calendar and join using the Google Meet link above.
#             """.strip()
#         }
        
#         return invite_details
        
#     except Exception as e:
#         if config.DEBUG:
#             print(f"Error generating calendar invite details: {e}")
#         return {
#             'error': str(e),
#             'meeting_time': meeting_time
#         }

# def get_user_scheduling_link() -> str:
#     """
#     Get user's scheduling link from environment or config
#     This should be configured in the .env file
#     """
#     # You can add this to your .env file:
#     # USER_SCHEDULING_LINK=https://calendly.com/yourusername
#     scheduling_link = os.getenv("USER_SCHEDULING_LINK", "")
    
#     if not scheduling_link:
#         # Fallback scheduling link placeholder
#         scheduling_link = "[Your scheduling link - please configure USER_SCHEDULING_LINK in .env file]"
    
#     return scheduling_link

# # Expose the internal implementations for direct calling in tests
# check_calendar_availability_direct = _check_calendar_availability_impl
# find_free_time_slots_direct = _find_free_time_slots_impl

