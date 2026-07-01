import os
import uuid
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from agent import get_agent_chat, send_message_with_retry
from google.genai import types
import tools

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

app = FastAPI(title="Personal Assistant Agent API")

# Ensure static directory exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")

# In-memory sessions database
# maps session_id -> { "chat": ChatSession, "pending_calls": List[FunctionCall], "tool_responses": List[Part] }
_SESSIONS: Dict[str, Dict[str, Any]] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ApprovalDecision(BaseModel):
    name: str
    approved: bool

class ApprovalRequest(BaseModel):
    session_id: str
    decisions: List[ApprovalDecision]

def handle_agent_response(session_id: str, session: dict, response) -> dict:
    """
    Recursive handler for model responses.
    - If Gemini requests function calls:
        - If any calls are mutating (send draft, schedule calendar, etc.), it saves them,
          pauses execution, and returns a 'requires_approval' status.
        - If all calls are non-mutating (list events, search, read emails), it runs them,
          feeds results back to Gemini, and continues the loop.
    - If Gemini returns text only, it returns 'success' with the text content.
    """
    chat = session["chat"]
    
    if response.function_calls:
        mutating_calls = []
        non_mutating_calls = []
        
        for call in response.function_calls:
            if call.name in ["send_draft", "create_calendar_event", "update_calendar_event", "delete_calendar_event"]:
                mutating_calls.append(call)
            else:
                non_mutating_calls.append(call)
                
        # If there are any mutating calls, pause the execution and ask the user
        if mutating_calls:
            logger.info(f"Pausing agent execution for user approval on session: {session_id}")
            session["pending_calls"] = response.function_calls
            
            return {
                "session_id": session_id,
                "status": "requires_approval",
                "pending_calls": [
                    {
                        "name": call.name,
                        "args": call.args
                    } for call in response.function_calls
                ]
            }
            
        # If only non-mutating calls (e.g. read email, list tasks, search web) are requested, execute them immediately
        tool_responses = []
        for call in response.function_calls:
            name = call.name
            args = call.args
            logger.info(f"Executing non-mutating tool '{name}' automatically.")
            try:
                func = getattr(tools, name)
                result = func(**args)
            except Exception as e:
                logger.error(f"Error executing tool '{name}': {e}")
                result = {"status": "Error", "error": str(e)}
                
            tool_responses.append(
                types.Part.from_function_response(
                    name=name,
                    response={"result": result}
                )
            )
            
        # Submit results back to Gemini and recurse
        import time
        time.sleep(1)  # rate limit prevention
        next_response = send_message_with_retry(chat, tool_responses)
        return handle_agent_response(session_id, session, next_response)
        
    else:
        # Base case: model returned a final text answer
        return {
            "session_id": session_id,
            "status": "success",
            "response": response.text or "I have processed your request."
        }

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    session_id = req.session_id
    
    # Initialize a new session if none is provided or valid
    if not session_id or session_id not in _SESSIONS:
        session_id = str(uuid.uuid4())
        logger.info(f"Creating new agent session: {session_id}")
        try:
            chat = get_agent_chat()
            _SESSIONS[session_id] = {
                "chat": chat,
                "pending_calls": None
            }
        except Exception as e:
            logger.error(f"Failed to initialize chat session: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize agent: {str(e)}")
            
    session = _SESSIONS[session_id]
    chat = session["chat"]
    
    try:
        logger.info(f"Processing message on session {session_id}: '{req.message}'")
        response = send_message_with_retry(chat, req.message)
        return handle_agent_response(session_id, session, response)
    except Exception as e:
        logger.error(f"Error during chat processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/approve")
def approve_endpoint(req: ApprovalRequest):
    session_id = req.session_id
    if session_id not in _SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = _SESSIONS[session_id]
    pending_calls = session.get("pending_calls")
    if not pending_calls:
        raise HTTPException(status_code=400, detail="No pending actions found for this session")
        
    # Map decisions by function name
    decision_map = {d.name: d.approved for d in req.decisions}
    
    tool_responses = []
    chat = session["chat"]
    
    for call in pending_calls:
        name = call.name
        args = call.args
        
        # Check if the user approved this specific tool call
        approved = True
        if name in ["send_draft", "create_calendar_event", "update_calendar_event", "delete_calendar_event"]:
            approved = decision_map.get(name, False)
            
        if approved:
            logger.info(f"Executing approved action: {name}")
            try:
                func = getattr(tools, name)
                result = func(**args)
            except Exception as e:
                logger.error(f"Error executing approved action '{name}': {e}")
                result = {"status": "Error", "error": str(e)}
        else:
            logger.info(f"Skipping rejected action: {name}")
            result = {"status": "Rejected", "error": "User did not approve execution of this action."}
            
        tool_responses.append(
            types.Part.from_function_response(
                name=name,
                response={"result": result}
            )
        )
        
    # Clear the pending calls state
    session["pending_calls"] = None
    
    # Resume agent execution loop
    try:
        import time
        time.sleep(1)  # rate limit prevention
        next_response = send_message_with_retry(chat, tool_responses)
        return handle_agent_response(session_id, session, next_response)
    except Exception as e:
        logger.error(f"Error during resumed chat processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
def status_endpoint():
    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    return {
        "status": "online",
        "model": model_name,
        "demo_mode": tools.DEMO_MODE,
        "has_credentials": os.path.exists("credentials.json")
    }
