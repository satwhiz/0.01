"""
Enhanced Email Drafting Agent - DeepSeek Only with Calendar Integration (FIXED)
This agent creates email drafts for emails classified as "To Do" using DeepSeek AI
and integrates with Google Calendar for meeting scheduling.
"""

import sys
from typing import List, Dict, Any
from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from config import config
from gmail_auth import gmail_auth
from utils import extract_email_content, format_thread_context
from prompts.drafting_system_prompt import DRAFTING_SYSTEM_PROMPT
from tools.calendar import (
    check_calendar_availability,
    find_free_time_slots,
    extract_meeting_request_from_email,
    generate_calendar_invite_details,
    get_user_scheduling_link,
    _check_calendar_availability_impl,  # ADDED - Direct access to internal functions
    _find_free_time_slots_impl          # ADDED - Direct access to internal functions
)

def get_deepseek_model():
    """Get DeepSeek model with proper configuration"""
    return DeepSeek(
        id=config.DEFAULT_MODEL,
        api_key=config.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

class EnhancedEmailDraftingAgent:
    def __init__(self):
        self.service = None
        
    def initialize(self):
        """Initialize the agent with Gmail authentication"""
        if config.DEBUG:
            print("Initializing Enhanced Email Drafting Agent with Calendar Integration...")
        
        # Validate configuration
        if not config.validate():
            raise ValueError("Invalid configuration. Please check your settings.")
        
        # Authenticate with Gmail
        self.service = gmail_auth.authenticate()
        
        if config.DEBUG:
            print("Gmail authentication successful for enhanced drafting agent")
    
    def get_enhanced_drafting_prompt(self, latest_email_content: str, thread_context: str = "", calendar_context: str = "") -> str:
        """
        Generate the enhanced email drafting prompt with calendar integration
        
        Args:
            latest_email_content: Content of the latest email that needs a response
            thread_context: Context from the full email thread
            calendar_context: Calendar availability and meeting context
            
        Returns:
            Formatted prompt for email drafting with calendar awareness
        """
        prompt = DRAFTING_SYSTEM_PROMPT + "\n\n"
        
        # Add calendar-specific instructions
        prompt += """🗓️ **ENHANCED CALENDAR INTEGRATION INSTRUCTIONS:**

**CRITICAL DECISION FLOW - Follow Exactly:**

1. **STEP 1: Check if specific time was suggested AND if user is available**
   - If YES to both → Accept the time enthusiastically + mention calendar invite/Google Meet
   - If time suggested but user is BUSY → Politely decline + offer scheduling link
   
2. **STEP 2: If no specific time suggested OR user declined**
   - Offer to connect + provide scheduling link for them to choose
   
3. **STEP 3: Tone and Response Quality**
   - Match the sender's tone and formality level
   - Be enthusiastic about accepting available times
   - Be apologetic but helpful when declining due to conflicts
   - Always show interest in the meeting topic mentioned

**IMPROVED RESPONSE TEMPLATES:**

For AVAILABLE times:
"[Time] works perfectly for me! I'll send a calendar invite with a Google Meet link. Looking forward to discussing [topic]."

For BUSY times:
"I'm already booked at [time]. You can pick another time that works for you here: [scheduling link]. Happy to discuss [topic] whenever works for you!"

For GENERAL requests:
"I'd be happy to connect about [topic]. Please feel free to schedule a time that works for you: [scheduling link]"

**Calendar Context:**
""" + calendar_context + "\n\n"
        
        prompt += "**LATEST EMAIL TO RESPOND TO:**\n"
        prompt += latest_email_content + "\n\n"
        
        if thread_context:
            prompt += thread_context + "\n\n"
        
        prompt += """**CRITICAL INSTRUCTIONS:**
- Base your availability decision ONLY on the calendar analysis above
- If calendar shows "Available: True" → accept the time
- If calendar shows "Available: False" → decline and offer alternatives
- Always reference the specific topic mentioned in the email
- Use proper placeholders for calendar-related elements
- Be conversational and professional

Draft Response:"""
        
        return prompt

    def analyze_meeting_request(self, email_content: str) -> Dict[str, Any]:
        """
        Analyze email to understand meeting request and check calendar availability
        
        Args:
            email_content: Email content to analyze
            
        Returns:
            Dict with meeting analysis and calendar context
        """
        if config.DEBUG:
            print("🗓️ Analyzing email for meeting requests...")
        
        # Extract meeting request information
        meeting_analysis = extract_meeting_request_from_email(email_content)
        
        calendar_context = {
            'is_meeting_request': meeting_analysis['is_meeting_request'],
            'request_type': meeting_analysis['request_type'],
            'time_suggestions': meeting_analysis['time_suggestions'],
            'availability_checks': [],
            'free_slots': [],
            'scheduling_link': get_user_scheduling_link()
        }
        
        if config.DEBUG:
            print(f"Meeting request detected: {meeting_analysis['is_meeting_request']}")
            print(f"Request type: {meeting_analysis['request_type']}")
            print(f"Time suggestions found: {len(meeting_analysis['time_suggestions'])}")
            
            # Debug: Print extracted times
            for suggestion in meeting_analysis['time_suggestions']:
                print(f"  - '{suggestion['original_text']}' → {suggestion['parsed_datetime']}")
        
        # FIXED: Actually perform availability checks for suggested times
        if meeting_analysis['time_suggestions']:
            for suggestion in meeting_analysis['time_suggestions']:
                try:
                    if config.DEBUG:
                        print(f"🔍 Checking availability for: {suggestion['parsed_datetime']}")
                    
                    # FIXED: Use the internal implementation directly instead of tool
                    availability = _check_calendar_availability_impl(
                        start_time=suggestion['parsed_datetime'].isoformat(),
                        duration_minutes=60  # Default 1 hour meeting
                    )
                    
                    # FIXED: Add the check to the context (this was missing)
                    availability_check = {
                        'suggested_time': suggestion['parsed_datetime'].isoformat(),
                        'formatted_time': suggestion['parsed_datetime'].strftime('%A, %B %d at %I:%M %p'),
                        'available': availability['available'],
                        'conflicts': availability.get('conflicting_events', [])
                    }
                    
                    calendar_context['availability_checks'].append(availability_check)
                    
                    if config.DEBUG:
                        status = "✅ Available" if availability['available'] else "❌ Busy"
                        print(f"  Result: {status}")
                        if availability.get('conflicting_events'):
                            conflicts = [event['summary'] for event in availability['conflicting_events']]
                            print(f"  Conflicts: {conflicts}")
                        
                except Exception as e:
                    if config.DEBUG:
                        print(f"❌ Error checking availability for {suggestion['original_text']}: {e}")
                    
                    # Add failed check to context
                    calendar_context['availability_checks'].append({
                        'suggested_time': suggestion['parsed_datetime'].isoformat(),
                        'formatted_time': suggestion['parsed_datetime'].strftime('%A, %B %d at %I:%M %p'),
                        'available': False,
                        'conflicts': [],
                        'error': str(e)
                    })
        
        # Enhanced free slot finding - prioritize next available days
        if meeting_analysis['is_meeting_request']:
            # Check if any suggested times are available first
            has_available_suggested_time = any(
                check.get('available', False) 
                for check in calendar_context['availability_checks']
            )
            
            # Only find alternatives if user is busy or no specific time suggested
            if not has_available_suggested_time or not meeting_analysis['time_suggestions']:
                try:
                    if config.DEBUG:
                        print("🔍 Finding alternative time slots...")
                    
                    # FIXED: Use the internal implementation directly instead of tool
                    free_slots = _find_free_time_slots_impl(
                        days_ahead=7,  # Look 1 week ahead
                        max_suggestions=3,
                        duration_minutes=60,
                        business_hours_only=config.BUSINESS_HOURS_ONLY
                    )
                    calendar_context['free_slots'] = free_slots.get('free_slots', [])
                    
                    if config.DEBUG:
                        print(f"Found {len(calendar_context['free_slots'])} alternative slots")
                        for slot in calendar_context['free_slots']:
                            print(f"  - {slot['formatted_time']}")
                            
                except Exception as e:
                    if config.DEBUG:
                        print(f"❌ Error finding free slots: {e}")
        
        return calendar_context

    def format_calendar_context_for_prompt(self, calendar_context: Dict[str, Any]) -> str:
        """
        Format calendar context for inclusion in the drafting prompt
        
        Args:
            calendar_context: Calendar analysis results
            
        Returns:
            Formatted string for prompt
        """
        if not calendar_context['is_meeting_request']:
            return "This email does not appear to be a meeting request."
        
        context_text = "📅 CALENDAR ANALYSIS:\n"
        context_text += f"Meeting Request Type: {calendar_context['request_type']}\n"
        context_text += f"User's Scheduling Link: {calendar_context['scheduling_link']}\n\n"
        
        # Add availability checks for specific times
        if calendar_context['availability_checks']:
            context_text += "⏰ AVAILABILITY FOR SUGGESTED TIMES:\n"
            for check in calendar_context['availability_checks']:
                status = "✅ AVAILABLE" if check['available'] else "❌ BUSY"
                context_text += f"- {check['formatted_time']}: {status}\n"
                if not check['available'] and check['conflicts']:
                    context_text += f"  Conflicts: {[event['summary'] for event in check['conflicts']]}\n"
            context_text += "\n"
        
        # Add free slots for general requests
        if calendar_context['free_slots']:
            context_text += "🆓 AVAILABLE TIME SLOTS:\n"
            for slot in calendar_context['free_slots'][:3]:
                context_text += f"- {slot['formatted_time']}\n"
            context_text += "\n"
        
        return context_text

    def draft_email_reply(self, message_id: str) -> str:
        """
        Create a calendar-aware draft reply for the given email message
        
        Args:
            message_id: Gmail message ID that was classified as "To Do"
            
        Returns:
            Draft email content with calendar integration or error message
        """
        if not self.service:
            self.initialize()
        
        try:
            if config.DEBUG:
                print(f"📝 Creating calendar-aware draft for email: {message_id}")
            
            # Get the email
            email_data = self.service.users().messages().get(userId='me', id=message_id).execute()
            
            # Get thread context
            thread_id = email_data.get('threadId')
            thread_messages = [email_data]
            
            if thread_id:
                try:
                    thread = self.service.users().threads().get(userId='me', id=thread_id).execute()
                    thread_messages = thread.get('messages', [])
                    thread_messages.sort(key=lambda x: int(x['internalDate']))
                    if config.DEBUG:
                        print(f"Retrieved {len(thread_messages)} messages from thread: {thread_id}")
                except Exception as e:
                    if config.DEBUG:
                        print(f"Error retrieving thread {thread_id}: {e}")
            
            # Get the latest message (the one we need to respond to)
            latest_message = thread_messages[-1] if thread_messages else email_data
            
            # Extract content
            latest_email_content = extract_email_content(latest_message)
            thread_context = format_thread_context(thread_messages) if len(thread_messages) > 1 else ""
            
            # Analyze for meeting requests and check calendar
            calendar_context = self.analyze_meeting_request(latest_email_content)
            calendar_context_text = self.format_calendar_context_for_prompt(calendar_context)
            
            # Generate enhanced drafting prompt with calendar awareness
            drafting_prompt = self.get_enhanced_drafting_prompt(
                latest_email_content, 
                thread_context, 
                calendar_context_text
            )
            
            if config.DEBUG:
                print("🤖 Generating calendar-aware email draft with DeepSeek AI...")
            
            # Use DeepSeek to generate calendar-aware draft
            drafting_agent = Agent(
                model=get_deepseek_model(),
                tools=[
                    check_calendar_availability,
                    find_free_time_slots,
                    extract_meeting_request_from_email,
                    generate_calendar_invite_details
                ],
                instructions=DRAFTING_SYSTEM_PROMPT,
                markdown=False
            )
            
            response = drafting_agent.run(drafting_prompt)
            draft_content = response.content.strip()
            
            # Post-process draft to replace placeholders with actual values
            draft_content = self.process_calendar_placeholders(draft_content, calendar_context)
            
            # Extract subject from original email for context
            headers = latest_message.get('payload', {}).get('headers', [])
            original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            original_from = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            
            # Format the enhanced draft output
            draft_output = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     📧 CALENDAR-AWARE EMAIL DRAFT                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

📌 **Original Email Context:**
   • From: {original_from}
   • Subject: {original_subject}
   • Message ID: {message_id}
   • Thread Messages: {len(thread_messages)}

🗓️ **Calendar Analysis:**
   • Meeting Request: {'Yes' if calendar_context['is_meeting_request'] else 'No'}
   • Request Type: {calendar_context['request_type']}
   • Time Suggestions: {len(calendar_context['time_suggestions'])} found
   • Availability Checks: {len(calendar_context['availability_checks'])} performed

📝 **Generated Draft Reply:**
{'-' * 80}
{draft_content}
{'-' * 80}

💡 **Next Steps:**
   1. Review the draft above
   2. Fill in any remaining placeholders [like this] with actual information
   3. If calendar invite mentioned, create the actual calendar event
   4. Make any necessary edits
   5. Copy and send the email manually

🗓️ **Calendar Actions Needed:**
"""
            
            # Add calendar-specific next steps
            if calendar_context['is_meeting_request']:
                if any(check['available'] for check in calendar_context['availability_checks']):
                    draft_output += "   • Create calendar invite for accepted meeting time\n"
                    draft_output += "   • Generate Google Meet link\n"
                else:
                    draft_output += "   • No immediate calendar action needed (scheduling link provided)\n"
            else:
                draft_output += "   • No calendar actions required for this email\n"
            
            draft_output += f"""
🤖 **Generated by:** Fyxer AI (DeepSeek) with Calendar Integration
⏰ **Generated at:** {self._get_current_timestamp()}
🔗 **Your Scheduling Link:** {calendar_context['scheduling_link']}
"""
            
            return draft_output
            
        except Exception as e:
            error_msg = f"❌ Error creating calendar-aware email draft for {message_id}: {e}"
            if config.DEBUG:
                import traceback
                print(traceback.format_exc())
            return error_msg
    
    def process_calendar_placeholders(self, draft_content: str, calendar_context: Dict[str, Any]) -> str:
        """
        Replace calendar placeholders in draft with actual values
        
        Args:
            draft_content: Draft email content with placeholders
            calendar_context: Calendar analysis results
            
        Returns:
            Draft content with placeholders replaced
        """
        # Replace scheduling link placeholder
        if '[Your Scheduling Link]' in draft_content:
            draft_content = draft_content.replace('[Your Scheduling Link]', calendar_context['scheduling_link'])
        
        # Replace Google Meet link placeholder (if meeting time is confirmed)
        if '[Google Meet Link]' in draft_content:
            # For now, use a placeholder that user needs to fill
            draft_content = draft_content.replace('[Google Meet Link]', '[Google Meet link will be generated when calendar invite is created]')
        
        # Replace calendar invite placeholder
        if '[Calendar Invite Attached]' in draft_content:
            draft_content = draft_content.replace('[Calendar Invite Attached]', '[Calendar invite will be sent separately]')
        
        # Replace alternative time slots if requested
        if '[Alternative Time Slots]' in draft_content and calendar_context['free_slots']:
            alternatives = []
            for slot in calendar_context['free_slots'][:3]:
                alternatives.append(f"• {slot['formatted_time']}")
            
            alt_text = "Here are some alternative times that work for me:\n" + "\n".join(alternatives)
            draft_content = draft_content.replace('[Alternative Time Slots]', alt_text)
        
        return draft_content
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for draft metadata"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Global instance
_enhanced_drafting_agent_instance = None

def get_enhanced_drafting_agent_instance():
    """Get the global enhanced drafting agent instance"""
    global _enhanced_drafting_agent_instance
    if _enhanced_drafting_agent_instance is None:
        _enhanced_drafting_agent_instance = EnhancedEmailDraftingAgent()
        _enhanced_drafting_agent_instance.initialize()
    return _enhanced_drafting_agent_instance

def create_calendar_aware_draft_for_todo_email(message_id: str) -> str:
    """
    Public function to create a calendar-aware draft for a "To Do" email
    
    Args:
        message_id: Gmail message ID that was classified as "To Do"
        
    Returns:
        Calendar-aware draft email content formatted for terminal display
    """
    try:
        agent = get_enhanced_drafting_agent_instance()
        return agent.draft_email_reply(message_id)
    except Exception as e:
        return f"❌ Error in enhanced drafting agent: {e}"

def main():
    """Main function for testing the enhanced drafting agent"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Gmail Email Drafting Agent with Calendar Integration')
    parser.add_argument('message_id', help='Email message ID to create draft for')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Override debug setting if specified
    if args.debug:
        config.DEBUG = True
        config.VERBOSE_LOGGING = True
    
    print("🚀 Enhanced Gmail Email Drafting Agent with Calendar Integration")
    print("=" * 80)
    
    # Create calendar-aware draft for the specified email
    draft_result = create_calendar_aware_draft_for_todo_email(args.message_id)
    print(draft_result)

if __name__ == "__main__":
    main()