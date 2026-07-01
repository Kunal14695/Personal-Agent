import os
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Import tools
import tools

# Load env variables
load_dotenv()

# Global client variable to prevent garbage collection and connection closure
_client = None

def get_agent_chat():
    """
    Initializes and returns a Gemini Chat session configured with the assistant tools and system instructions.
    """
    global _client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY environment variable is not set. The Gemini client will attempt to use default credentials.")
        
    _client = genai.Client(api_key=api_key)
    
    # Dynamically inject current local time context so the model can resolve relative times
    local_now = datetime.now().astimezone()
    local_time_str = local_now.isoformat()
    
    system_instruction = f"""
You are a helpful, professional Personal Assistant Agent.
You have access to the user's Gmail (list, draft, send), Google Calendar (list, create), and Tavily Web Search.

Current Context:
- Current Local Time: {local_time_str}
- Use this time to resolve relative terms like "today", "tomorrow", "next Friday", "2 PM", etc.
- When calling `create_calendar_event`, ensure the `start_time` and `end_time` are formatted as valid ISO 8601 strings (e.g. 'YYYY-MM-DDTHH:MM:SS+HH:MM').

Guidelines:
- Explain what you are doing.
- Be precise when creating drafts or events. If details are missing, ask the user to clarify.
- Do not make up email IDs or event times.
- Mutating actions (specifically sending drafts and creating calendar events) will go through a human-in-the-loop approval prompt managed by the runner script. Call the tools directly; the environment handles the confirmation.
"""

    # Pass Python function definitions directly as tools.
    # We disable automatic function calling to manage HITL checks in our agent loop.
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[
            tools.list_unread_emails,
            tools.search_emails,
            tools.read_email_details,
            tools.create_draft,
            tools.send_draft,
            tools.trash_email,
            tools.list_calendar_events,
            tools.create_calendar_event,
            tools.update_calendar_event,
            tools.delete_calendar_event,
            tools.search_contacts,
            tools.list_tasks,
            tools.create_task,
            tools.complete_task,
            tools.web_search,
            tools.read_local_file,
            tools.write_local_file
        ],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.0
    )
    
    # Use model name from env (default to gemini-2.0-flash)
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    chat = _client.chats.create(model=model_name, config=config)
    return chat

def send_message_with_retry(chat, message, max_retries=5, initial_delay=3):
    """
    Sends a message to the chat session with automatic retry on 429 Rate Limit errors using exponential backoff.
    """
    from google.genai.errors import APIError, ClientError
    import time
    
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return chat.send_message(message)
        except (ClientError, APIError) as e:
            is_429 = False
            if hasattr(e, 'code') and e.code == 429:
                is_429 = True
            elif "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                is_429 = True
                
            if is_429:
                print(f"\n⚠️  [Rate limit (429) hit. Retrying in {delay}s (Attempt {attempt+1}/{max_retries})...]")
                time.sleep(delay)
                delay *= 2
            else:
                raise e
    return chat.send_message(message)

def process_agent_interaction(chat, user_message: str):
    """
    Sends a message to the agent chat session and handles the tool execution loop,
    including human-in-the-loop approvals for mutating actions.
    """
    response = send_message_with_retry(chat, user_message)
    
    while True:
        # If the model didn't request any function calls, we are done
        if not response.function_calls:
            if response.text:
                print(f"\nAgent: {response.text}")
            break
            
        tool_responses = []
        for call in response.function_calls:
            name = call.name
            args = call.args
            
            # Interactive Approval (Human-in-the-loop) for mutating actions
            approved = True
            if name in ["send_draft", "create_calendar_event", "update_calendar_event", "delete_calendar_event"]:
                print(f"\n⚠️  [Human-in-the-Loop Approval Required]")
                if name == "send_draft":
                    print(f"👉 Action: Send Email Draft")
                    print(f"👉 Draft ID: {args.get('draft_id')}")
                elif name == "create_calendar_event":
                    print(f"👉 Action: Schedule Calendar Event")
                    print(f"👉 Summary: {args.get('summary')}")
                    print(f"👉 Start: {args.get('start_time')}")
                    print(f"👉 End: {args.get('end_time')}")
                    print(f"👉 Description: {args.get('description', 'None')}")
                elif name == "update_calendar_event":
                    print(f"👉 Action: Update Calendar Event")
                    print(f"👉 Event ID: {args.get('event_id')}")
                    changes = {k: v for k, v in args.items() if k != 'event_id' and v is not None}
                    print(f"👉 Changes: {changes}")
                elif name == "delete_calendar_event":
                    print(f"👉 Action: Delete Calendar Event")
                    print(f"👉 Event ID: {args.get('event_id')}")
                    
                choice = input("\nApprove execution of this action? (y/n): ").strip().lower()
                if choice not in ['y', 'yes']:
                    approved = False
                    print("❌ Action rejected by user.")
                    result = {"status": "Rejected", "error": "User did not approve execution of this action."}
                else:
                    print("✅ Action approved. Executing...")
            
            # Execute tool if approved (or if it is non-mutating)
            if approved:
                try:
                    # Dynamically invoke the function matching the call name
                    func = getattr(tools, name)
                    result = func(**args)
                except Exception as e:
                    print(f"❌ Error executing tool '{name}': {e}")
                    result = {"status": "Error", "error": str(e)}
                    
            # Wrap the result as a FunctionResponse part
            tool_responses.append(
                types.Part.from_function_response(
                    name=name,
                    response={"result": result}
                )
            )
            
        # Send function execution results back to the chat history
        import time
        time.sleep(1)  # Rate limiting prevention delay
        response = send_message_with_retry(chat, tool_responses)
