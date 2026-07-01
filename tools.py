import os
import base64
import requests
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from auth import get_google_services

# Lazy-loaded cache for services to prevent redundant authentications
_gmail_service = None
_calendar_service = None
_people_service = None
_tasks_service = None

# Global flag to enable mock responses for debugging/testing without credentials
DEMO_MODE = False

# Module-level variable to hold simulated tasks in Demo Mode
_MOCK_TASKS = [
    {"id": "task1", "title": "Buy groceries", "notes": "Milk, eggs, and bread", "status": "needsAction"},
    {"id": "task2", "title": "Finish assistant project", "notes": "Code all advanced tools", "status": "needsAction"}
]

def get_services():
    """
    Helper to get or initialize Google service clients.
    """
    global _gmail_service, _calendar_service, _people_service, _tasks_service
    if DEMO_MODE:
        return None, None, None, None
    if _gmail_service is None or _calendar_service is None or _people_service is None or _tasks_service is None:
        services = get_google_services()
        _gmail_service = services['gmail']
        _calendar_service = services['calendar']
        _people_service = services['people']
        _tasks_service = services['tasks']
    return _gmail_service, _calendar_service, _people_service, _tasks_service

# ==========================================
# 1. GMAIL TOOLS
# ==========================================

def list_unread_emails() -> list:
    """
    Retrieves a list of unread email summaries from the user's Gmail inbox.
    
    Returns:
        list: A list of dicts, each containing 'id', 'sender', 'subject', 'date', and 'snippet'.
    """
    if DEMO_MODE:
        return [
            {
                "id": "msg123", 
                "sender": "Alice Smith <alice@example.com>", 
                "subject": "Project Status Update", 
                "date": "Wed, 1 Jul 2026 09:00:00 -0700", 
                "snippet": "Hey, just wanted to check if you completed the task list for the new agent project. Let me know if you need help!"
            },
            {
                "id": "msg124", 
                "sender": "John Doe <john@company.com>", 
                "subject": "Meeting Tomorrow", 
                "date": "Wed, 1 Jul 2026 10:15:00 -0700", 
                "snippet": "Hi, let's connect tomorrow at 2 PM to talk about the coffee chat schedule."
            },
            {
                "id": "msg125", 
                "sender": "Travel Booking <noreply@airline.com>", 
                "subject": "Your flight itinerary", 
                "date": "Tue, 30 Jun 2026 18:30:00 -0700", 
                "snippet": "Your flight booking to Tokyo is confirmed. Seat 14A. Details inside."
            }
        ]
    
    gmail_service, _, _, _ = get_services()
    try:
        results = gmail_service.users().messages().list(userId='me', q='is:unread', maxResults=10).execute()
        messages = results.get('messages', [])
        
        summaries = []
        for msg in messages:
            m = gmail_service.users().messages().get(
                userId='me', 
                id=msg['id'], 
                format='metadata', 
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = m.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown Date')
            snippet = m.get('snippet', '')
            
            summaries.append({
                "id": msg['id'],
                "sender": sender,
                "subject": subject,
                "date": date,
                "snippet": snippet
            })
        return summaries
    except Exception as e:
        return [{"error": f"Failed to list unread emails: {str(e)}"}]

def search_emails(query: str) -> list:
    """
    Searches the user's Gmail messages using a query (e.g. 'from:Alice', 'invoice').
    
    Args:
        query: Gmail search filter query.
        
    Returns:
        list: Matching email summaries containing 'id', 'sender', 'subject', 'date', and 'snippet'.
    """
    if DEMO_MODE:
        mock_emails = [
            {"id": "msg123", "sender": "Alice Smith <alice@example.com>", "subject": "Project Status Update", "date": "Wed, 1 Jul 2026 09:00:00 -0700", "snippet": "Hey, just wanted to check if you completed the task list for the new agent project..."},
            {"id": "msg124", "sender": "John Doe <john@company.com>", "subject": "Meeting Tomorrow", "date": "Wed, 1 Jul 2026 10:15:00 -0700", "snippet": "Hi, let's connect tomorrow at 2 PM to talk about the coffee chat schedule..."},
            {"id": "msg125", "sender": "Travel Booking <noreply@airline.com>", "subject": "Your flight itinerary", "date": "Tue, 30 Jun 2026 18:30:00 -0700", "snippet": "Your flight booking to Tokyo is confirmed. Seat 14A..."},
            {"id": "msg126", "sender": "Invoice Billing <billing@saas.com>", "subject": "Invoice for July 2026", "date": "Wed, 1 Jul 2026 08:00:00 -0700", "snippet": "Your monthly SaaS invoice is ready. Total due: $49.00..."}
        ]
        return [e for e in mock_emails if query.lower() in e['sender'].lower() or query.lower() in e['subject'].lower() or query.lower() in e['snippet'].lower()]
        
    gmail_service, _, _, _ = get_services()
    try:
        results = gmail_service.users().messages().list(userId='me', q=query, maxResults=10).execute()
        messages = results.get('messages', [])
        
        summaries = []
        for msg in messages:
            m = gmail_service.users().messages().get(
                userId='me', 
                id=msg['id'], 
                format='metadata', 
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = m.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown Date')
            snippet = m.get('snippet', '')
            
            summaries.append({
                "id": msg['id'],
                "sender": sender,
                "subject": subject,
                "date": date,
                "snippet": snippet
            })
        return summaries
    except Exception as e:
        return [{"error": f"Failed to search emails: {str(e)}"}]

def read_email_details(message_id: str) -> dict:
    """
    Retrieves the full content and metadata of a specific Gmail email.
    
    Args:
        message_id: The Gmail message ID to retrieve.
        
    Returns:
        dict: A dictionary containing 'id', 'sender', 'subject', 'date', and 'body' (full text).
    """
    if DEMO_MODE:
        mock_bodies = {
            "msg123": "Hey, just wanted to check if you completed the task list for the new agent project. Let me know if you need help! Best, Alice",
            "msg124": "Hi, let's connect tomorrow at 2 PM to talk about the coffee chat schedule. Cheers, John",
            "msg125": "Your flight booking to Tokyo is confirmed. Seat 14A. Details inside. Departs at 10 PM on Friday.",
            "msg126": "Your monthly SaaS invoice is ready. Total due: $49.00. Payment will be processed automatically."
        }
        mock_emails = {
            "msg123": ("Alice Smith <alice@example.com>", "Project Status Update", "Wed, 1 Jul 2026 09:00:00 -0700"),
            "msg124": ("John Doe <john@company.com>", "Meeting Tomorrow", "Wed, 1 Jul 2026 10:15:00 -0700"),
            "msg125": ("Travel Booking <noreply@airline.com>", "Your flight itinerary", "Tue, 30 Jun 2026 18:30:00 -0700"),
            "msg126": ("Invoice Billing <billing@saas.com>", "Invoice for July 2026", "Wed, 1 Jul 2026 08:00:00 -0700")
        }
        hdr = mock_emails.get(message_id, ("System", "System Email", "Now"))
        return {
            "id": message_id,
            "sender": hdr[0],
            "subject": hdr[1],
            "date": hdr[2],
            "body": mock_bodies.get(message_id, "Simulated email body.")
        }
        
    gmail_service, _, _, _ = get_services()
    try:
        message = gmail_service.users().messages().get(userId='me', id=message_id, format='full').execute()
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown Date')
        
        body = ""
        # Parse payload parts for body
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        else:
            data = payload.get('body', {}).get('data', '')
            body = base64.urlsafe_b64decode(data).decode('utf-8')
            
        if not body:
            body = message.get('snippet', '')
            
        return {
            "id": message_id,
            "sender": sender,
            "subject": subject,
            "date": date,
            "body": body
        }
    except Exception as e:
        return {"error": f"Failed to retrieve email details: {str(e)}"}

def create_draft(to: str, subject: str, body: str) -> dict:
    """
    Creates an email draft in the user's Gmail account.
    
    Args:
        to: The recipient's email address (e.g. 'john@example.com').
        subject: The subject of the email.
        body: The plain text body of the email.
        
    Returns:
        dict: A status dictionary containing the created draft ID.
    """
    if DEMO_MODE:
        return {
            "draft_id": "draft_mock_abc123", 
            "status": "Draft created successfully (DEMO MODE)",
            "to": to,
            "subject": subject
        }
        
    gmail_service, _, _, _ = get_services()
    try:
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        draft_body = {
            'message': {
                'raw': raw
            }
        }
        draft = gmail_service.users().drafts().create(userId='me', body=draft_body).execute()
        return {
            "draft_id": draft['id'], 
            "status": "Draft created successfully",
            "to": to,
            "subject": subject
        }
    except Exception as e:
        return {"error": f"Failed to create draft: {str(e)}"}

def send_draft(draft_id: str) -> dict:
    """
    Sends an existing Gmail draft.
    
    Args:
        draft_id: The ID of the draft to send.
        
    Returns:
        dict: A status dictionary with the sent message ID.
    """
    if DEMO_MODE:
        return {
            "message_id": "msg_mock_xyz789", 
            "status": "Draft sent successfully (DEMO MODE)"
        }
        
    gmail_service, _, _, _ = get_services()
    try:
        sent_message = gmail_service.users().drafts().send(userId='me', body={'id': draft_id}).execute()
        return {
            "message_id": sent_message['id'], 
            "status": "Draft sent successfully"
        }
    except Exception as e:
        return {"error": f"Failed to send draft: {str(e)}"}

def trash_email(message_id: str) -> dict:
    """
    Moves an email to Gmail Trash.
    
    Args:
        message_id: The Gmail message ID to trash.
        
    Returns:
        dict: Status message confirming execution.
    """
    if DEMO_MODE:
        return {"message_id": message_id, "status": "Message moved to Trash successfully (DEMO MODE)"}
        
    gmail_service, _, _, _ = get_services()
    try:
        gmail_service.users().messages().trash(userId='me', id=message_id).execute()
        return {"message_id": message_id, "status": "Message moved to Trash successfully"}
    except Exception as e:
        return {"error": f"Failed to trash email: {str(e)}"}

# ==========================================
# 2. GOOGLE CALENDAR TOOLS
# ==========================================

def list_calendar_events(days: int = 7) -> list:
    """
    Retrieves the primary calendar events for the specified number of days in the future.
    
    Args:
        days: Number of days to retrieve events for (default: 7).
        
    Returns:
        list: A list of event dicts containing 'id', 'summary', 'start', 'end', and 'description'.
    """
    if DEMO_MODE:
        now = datetime.now()
        return [
            {
                "id": "evt001", 
                "summary": "Team Sync", 
                "start": now.replace(hour=10, minute=0, second=0, microsecond=0).isoformat(), 
                "end": now.replace(hour=11, minute=0, second=0, microsecond=0).isoformat(), 
                "description": "Weekly status meeting"
            },
            {
                "id": "evt002", 
                "summary": "Lunch with Bob", 
                "start": now.replace(hour=13, minute=0, second=0, microsecond=0).isoformat(), 
                "end": now.replace(hour=14, minute=0, second=0, microsecond=0).isoformat(), 
                "description": "Discussing UI designs"
            }
        ]
        
    _, calendar_service, _, _ = get_services()
    try:
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=days)).isoformat()
        
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        summaries = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            summaries.append({
                "id": event['id'],
                "summary": event.get('summary', 'No Title'),
                "start": start,
                "end": end,
                "description": event.get('description', '')
            })
        return summaries
    except Exception as e:
        return [{"error": f"Failed to list events: {str(e)}"}]

def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = "") -> dict:
    """
    Creates an event in the primary Google Calendar.
    
    Args:
        summary: Title/Summary of the event (e.g. 'Coffee Chat').
        start_time: ISO 8601 string of the start time (e.g. '2026-07-02T14:00:00+05:30').
        end_time: ISO 8601 string of the end time (e.g. '2026-07-02T15:00:00+05:30').
        description: Optional details or notes for the calendar event.
        
    Returns:
        dict: A status dictionary with the event's HTML link and ID.
    """
    if DEMO_MODE:
        return {
            "event_id": "evt_mock_999",
            "html_link": "https://calendar.google.com/calendar/r/event/mock",
            "status": "Event created successfully (DEMO MODE)",
            "summary": summary,
            "start": start_time,
            "end": end_time
        }
        
    _, calendar_service, _, _ = get_services()
    try:
        event_body = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time,
            },
            'end': {
                'dateTime': end_time,
            }
        }
        event = calendar_service.events().insert(calendarId='primary', body=event_body).execute()
        return {
            "event_id": event['id'],
            "html_link": event.get('htmlLink'),
            "status": "Event created successfully",
            "summary": summary,
            "start": start_time,
            "end": end_time
        }
    except Exception as e:
        return {"error": f"Failed to create event: {str(e)}"}

def update_calendar_event(event_id: str, summary: str = None, start_time: str = None, end_time: str = None, description: str = None) -> dict:
    """
    Updates details of an existing Google Calendar event.
    
    Args:
        event_id: The ID of the calendar event to update.
        summary: The new summary/title for the event (optional).
        start_time: New ISO 8601 start time (optional).
        end_time: New ISO 8601 end time (optional).
        description: New description notes (optional).
        
    Returns:
        dict: Updated event details.
    """
    if DEMO_MODE:
        return {
            "event_id": event_id,
            "status": "Event updated successfully (DEMO MODE)",
            "summary": summary or "Simulated Summary",
            "start": start_time or "Simulated Start",
            "end": end_time or "Simulated End"
        }
        
    _, calendar_service, _, _ = get_services()
    try:
        event = calendar_service.events().get(calendarId='primary', eventId=event_id).execute()
        if summary is not None:
            event['summary'] = summary
        if description is not None:
            event['description'] = description
        if start_time is not None:
            event['start'] = {'dateTime': start_time}
        if end_time is not None:
            event['end'] = {'dateTime': end_time}
            
        updated = calendar_service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        return {
            "event_id": updated['id'],
            "status": "Event updated successfully",
            "summary": updated.get('summary'),
            "start": updated.get('start', {}).get('dateTime'),
            "end": updated.get('end', {}).get('dateTime')
        }
    except Exception as e:
        return {"error": f"Failed to update calendar event: {str(e)}"}

def delete_calendar_event(event_id: str) -> dict:
    """
    Deletes an event from the primary Google Calendar.
    
    Args:
        event_id: The ID of the event to delete.
        
    Returns:
        dict: Status message confirming execution.
    """
    if DEMO_MODE:
        return {"event_id": event_id, "status": "Event deleted successfully (DEMO MODE)"}
        
    _, calendar_service, _, _ = get_services()
    try:
        calendar_service.events().delete(calendarId='primary', eventId=event_id).execute()
        return {"event_id": event_id, "status": "Event deleted successfully"}
    except Exception as e:
        return {"error": f"Failed to delete event: {str(e)}"}

# ==========================================
# 3. GOOGLE CONTACTS & TASKS TOOLS
# ==========================================

def search_contacts(query: str) -> list:
    """
    Searches the user's Google Contacts connections for a matching name or email.
    
    Args:
        query: The name or email to search for.
        
    Returns:
        list: Matching contacts containing 'name' and 'email'.
    """
    if DEMO_MODE:
        mock_list = [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "Bob Johnson", "email": "bob@example.com"},
            {"name": "John Doe", "email": "john@company.com"},
            {"name": "Jane Miller", "email": "jane@company.com"}
        ]
        return [c for c in mock_list if query.lower() in c['name'].lower() or query.lower() in c['email'].lower()]
        
    _, _, people_service, _ = get_services()
    try:
        # Search contacts
        results = people_service.people().searchContacts(
            query=query,
            readMask='names,emailAddresses'
        ).execute()
        
        connections = results.get('results', [])
        contacts = []
        for conn in connections:
            person = conn.get('person', {})
            names = person.get('names', [])
            emails = person.get('emailAddresses', [])
            
            name = names[0].get('displayName') if names else 'Unknown Name'
            email = emails[0].get('value') if emails else 'No Email'
            contacts.append({"name": name, "email": email})
        return contacts
    except Exception as e:
        return [{"error": f"Failed to search contacts: {str(e)}"}]

def list_tasks() -> list:
    """
    Retrieves the list of active tasks from the user's default Google Tasks list.
    
    Returns:
        list: Active tasks containing 'id', 'title', 'notes', and 'status'.
    """
    if DEMO_MODE:
        return [t for t in _MOCK_TASKS if t['status'] != 'completed']
        
    _, _, _, tasks_service = get_services()
    try:
        results = tasks_service.tasks().list(tasklist='@default').execute()
        items = results.get('items', [])
        tasks = []
        for item in items:
            if item.get('status') != 'completed':
                tasks.append({
                    "id": item['id'],
                    "title": item['title'],
                    "notes": item.get('notes', ''),
                    "status": item['status']
                })
        return tasks
    except Exception as e:
        return [{"error": f"Failed to retrieve tasks: {str(e)}"}]

def create_task(title: str, notes: str = "") -> dict:
    """
    Creates a new task in the user's default Google Tasks list.
    
    Args:
        title: The title/summary of the task.
        notes: Optional details or description for the task.
        
    Returns:
        dict: A status dictionary containing the created task ID.
    """
    if DEMO_MODE:
        new_task = {
            "id": f"task_mock_{len(_MOCK_TASKS)+1}",
            "title": title,
            "notes": notes,
            "status": "needsAction"
        }
        _MOCK_TASKS.append(new_task)
        return {"task_id": new_task['id'], "status": "Task created successfully (DEMO MODE)", "title": title}
        
    _, _, _, tasks_service = get_services()
    try:
        body = {'title': title}
        if notes:
            body['notes'] = notes
        task = tasks_service.tasks().insert(tasklist='@default', body=body).execute()
        return {
            "task_id": task['id'], 
            "status": "Task created successfully", 
            "title": title
        }
    except Exception as e:
        return {"error": f"Failed to create task: {str(e)}"}

def complete_task(task_id: str) -> dict:
    """
    Marks a Google task as completed.
    
    Args:
        task_id: The ID of the task to mark as complete.
        
    Returns:
        dict: A status dictionary.
    """
    if DEMO_MODE:
        for t in _MOCK_TASKS:
            if t['id'] == task_id:
                t['status'] = 'completed'
                return {"task_id": task_id, "status": "Task marked as completed (DEMO MODE)"}
        return {"error": f"Task '{task_id}' not found."}
        
    _, _, _, tasks_service = get_services()
    try:
        tasks_service.tasks().patch(tasklist='@default', task=task_id, body={'status': 'completed'}).execute()
        return {"task_id": task_id, "status": "Task marked as completed"}
    except Exception as e:
        return {"error": f"Failed to complete task: {str(e)}"}

# ==========================================
# 4. WEB SEARCH & LOCAL FILE TOOLS
# ==========================================

def web_search(query: str) -> str:
    """
    Performs a web search using the Tavily Search API.
    
    Args:
        query: The search query to submit.
        
    Returns:
        str: A text summary of results containing snippets and links.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key or api_key == "your_tavily_api_key_here":
        if DEMO_MODE:
            return f"Answer Summary: This is a simulated search result for query '{query}' in Demo Mode.\n\nSearch Details:\n[1] Title: Mock Result 1\nURL: https://mocksearch.com/1\nSnippet: Current weather in Tokyo is sunny and 26°C with 45% humidity.\n[2] Title: Mock Result 2\nURL: https://mocksearch.com/2\nSnippet: Complete guide to visiting Tokyo in July."
        return "Error: TAVILY_API_KEY environment variable is not set."
        
    url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json"}
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": True
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        results = []
        if data.get("answer"):
            results.append(f"Answer Summary: {data['answer']}\n")
            
        results.append("Search Details:")
        for idx, result in enumerate(data.get("results", [])[:5]):
            results.append(f"[{idx+1}] Title: {result.get('title')}\nURL: {result.get('url')}\nSnippet: {result.get('content')}\n")
            
        return "\n".join(results)
    except Exception as e:
        return f"Error executing web search: {str(e)}"

def read_local_file(filepath: str) -> str:
    """
    Reads the content of a local text or markdown file inside the project workspace.
    
    Args:
        filepath: The path to the file relative to the project directory (e.g. 'report.txt').
        
    Returns:
        str: The content of the file or an error message.
    """
    base_dir = os.path.abspath(os.getcwd())
    target_path = os.path.abspath(os.path.join(base_dir, filepath))
    
    # Path traversal security check
    if not target_path.startswith(base_dir):
        return "Error: Access denied. You can only read files within the project workspace."
        
    try:
        if not os.path.exists(target_path):
            return f"Error: File '{filepath}' does not exist."
        with open(target_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_local_file(filepath: str, content: str) -> dict:
    """
    Creates or overwrites a local text or markdown file in the project workspace with contents.
    
    Args:
        filepath: The path to the file relative to the project directory (e.g. 'notes.md').
        content: The text content to write to the file.
        
    Returns:
        dict: A status dictionary.
    """
    base_dir = os.path.abspath(os.getcwd())
    target_path = os.path.abspath(os.path.join(base_dir, filepath))
    
    # Path traversal security check
    if not target_path.startswith(base_dir):
        return {"error": "Access denied. You can only write files within the project workspace."}
        
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {
            "filepath": filepath,
            "status": "File written successfully",
            "bytes_written": len(content)
        }
    except Exception as e:
        return {"error": f"Error writing file: {str(e)}"}
