# Personal Assistant AI Agent 🤖

A local, web-based, and CLI-based Personal Assistant Agent powered by the **Google GenAI SDK (Gemini 3.5 Flash)** and **FastAPI**. The agent integrates with Gmail, Google Calendar, Google Tasks, Google Contacts, Tavily Web Search, and local workspace files. 

It features a **Human-in-the-Loop (HITL) validation layer** that prompts the user for approval before performing mutating actions (like sending emails or scheduling/deleting calendar events).

---

## Features 🌟

1. **Gmail Integration:**
   - List unread email summaries.
   - Search emails (e.g., `from:Alice` or `has:attachment`).
   - Read full email body details.
   - Create drafts & send drafts (requires approval).
   - Move emails to Trash.
2. **Google Calendar Integration:**
   - List upcoming schedule and events.
   - Schedule new meetings (e.g., *"tomorrow at 2 PM"*).
   - Update event times or summaries (requires approval).
   - Cancel/delete events (requires approval).
3. **Google Tasks Integration:**
   - List active to-do tasks.
   - Create new tasks.
   - Mark tasks as completed.
4. **Google Contacts Lookup:**
   - Search contacts by name or email (e.g. automatically finding an email address when drafting messages).
5. **Local File Management:**
   - Read and write text/markdown files inside the project workspace (useful for summaries, logs, or notes).
6. **Live Web Search:**
   - Leverages the Tavily Search API to answer current, real-time queries.
7. **Offline Demo Mode:**
   - Simulated mock data fallback is available for all Google services so you can test the entire agent immediately without credentials!

---

## Project Structure 📁

- `main.py`: Interactive CLI entry point.
- `server.py`: FastAPI web server with an asynchronous HITL state machine.
- `agent.py`: Core Gemini client initialization, timezone calculations, and agent loops.
- `tools.py`: Declarations for Gmail, Calendar, Contacts, Tasks, Search, and File functions.
- `auth.py`: Google OAuth client secrets loader and token manager.
- `static/`: HTML/JS/CSS source code for the premium glassmorphic UI.
- `.env`: Environment variables configuration.
- `.gitignore`: Security shield protecting your secret API keys and tokens.

---

## Setup Instructions 🛠️

### 1. Configure Keys (`.env`)
Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
GEMINI_MODEL=gemini-3.5-flash
```

### 2. Google OAuth Client Credentials (`credentials.json`)
To use Gmail, Calendar, Tasks, and Contacts live:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Gmail API**, **Google Calendar API**, **Tasks API**, and **People API**.
3. Configure the OAuth Consent Screen and add your email as a test user.
4. Create an **OAuth Client ID** credential (Application type: Desktop App).
5. Download the JSON, rename it to `credentials.json`, and place it in the project root.

### 3. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

---

## How to Run 🚀

### Option A: Interactive CLI Mode (Terminal)
```bash
python main.py
```

### Option B: Web Application (Local & Mobile)
1. Launch the FastAPI server:
   ```powershell
   ./run_web.ps1
   ```
2. Open your computer's browser to: `http://localhost:8000`
3. Access on your **Phone** (on the same Wi-Fi) by replacing `localhost` with your computer's local IP address (e.g., `http://192.168.0.28:8000`).

*Note: On your first prompt using Google features, a browser tab will open on your computer asking you to complete the one-time Google Account login. Subsequent requests will run silently.*

---

## Security Warning ⚠️
The `.gitignore` file is pre-configured to ignore `.env`, `credentials.json`, and `token.json` files. **Never remove these entries or push these secret files to a public Git repository.**
