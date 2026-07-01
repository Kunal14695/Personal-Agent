import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes needed for the assistant: Modify Gmail, Calendar, Contacts Readonly, and Tasks Read/Write
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/contacts.readonly',
    'https://www.googleapis.com/auth/tasks'
]

def get_google_services(credentials_path='credentials.json', token_path='token.json'):
    """
    Handles OAuth authentication flow and returns authenticated service clients.
    If token.json exists and is valid, uses it. Otherwise, triggers a local browser OAuth flow.
    """
    creds = None
    
    # Load cached credentials if they exist
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    # If no valid credentials, run the OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired OAuth token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}. Re-authenticating...")
                creds = None
                
        if not creds:
            if not os.path.exists(credentials_path):
                # Look for credentials.json in the parent directory just in case
                parent_creds = os.path.join('..', credentials_path)
                if os.path.exists(parent_creds):
                    credentials_path = parent_creds
                else:
                    raise FileNotFoundError(
                        f"Error: '{credentials_path}' not found.\n"
                        "Please download the OAuth Client secrets JSON from Google Cloud Console,\n"
                        f"rename it to '{credentials_path}', and place it in the project root."
                    )
            
            print("Starting browser authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save cached credentials
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
            print(f"Successfully authenticated. Saved token to '{token_path}'.")

    # Build and return the services
    gmail_service = build('gmail', 'v1', credentials=creds)
    calendar_service = build('calendar', 'v3', credentials=creds)
    people_service = build('people', 'v1', credentials=creds)
    tasks_service = build('tasks', 'v1', credentials=creds)
    
    return {
        'gmail': gmail_service,
        'calendar': calendar_service,
        'people': people_service,
        'tasks': tasks_service
    }

if __name__ == '__main__':
    # Simple check when run directly
    try:
        print("Checking Google Authentication...")
        get_google_services()
        print("Auth check complete. Services initialized successfully!")
    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"Auth initialization failed: {e}")
