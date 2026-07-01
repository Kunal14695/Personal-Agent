import os
import sys
from dotenv import load_dotenv
from agent import get_agent_chat, process_agent_interaction

def main():
    # Load environment variables from .env
    load_dotenv()
    
    demo_mode = False
    # Check for credentials.json
    if not os.path.exists("credentials.json"):
        # Also check parent directory
        if os.path.exists("../credentials.json"):
            # Move/copy it or just change path in auth.py (already handled)
            pass
        else:
            print("="*70)
            print("INFO: 'credentials.json' not found in the current directory.")
            print("Gmail and Google Calendar operations require OAuth client credentials.")
            print("="*70)
            choice = input("Would you like to run in Mock DEMO mode instead? (y/n): ").strip().lower()
            if choice in ['y', 'yes']:
                demo_mode = True
                import tools
                tools.DEMO_MODE = True
                print("🚀 Running in Mock DEMO mode (Gmail & Calendar will use simulated responses).")
            else:
                print("Google credentials are required to run in live mode. Exiting.")
                sys.exit(1)
        
    # Check/Prompt for Gemini API Key
    if not os.environ.get("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY is not set in the environment or .env file.")
        api_key = input("Please enter your Gemini API Key: ").strip()
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
            # Write to .env for persistence
            with open(".env", "a") as f:
                f.write(f"\nGEMINI_API_KEY={api_key}")
        else:
            print("Gemini API Key is required. Exiting.")
            sys.exit(1)
            
    # Check/Prompt for Tavily API Key
    if not os.environ.get("TAVILY_API_KEY"):
        print("WARNING: TAVILY_API_KEY is not set in the environment or .env file.")
        tav_key = input("Please enter your Tavily API Key (press Enter to skip web search tool): ").strip()
        if tav_key:
            os.environ["TAVILY_API_KEY"] = tav_key
            # Write to .env for persistence
            with open(".env", "a") as f:
                f.write(f"\nTAVILY_API_KEY={tav_key}")

    print("\nInitializing Personal Assistant Agent...")
    try:
        chat = get_agent_chat()
        print("Agent ready! Connected to Gmail, Calendar, Contacts, and Tasks.")
    except Exception as e:
        print(f"Failed to initialize assistant: {e}")
        sys.exit(1)
        
    print("\n" + "="*70)
    print("Welcome to your Personal Assistant CLI Agent!")
    print("You can prompt the agent to:")
    print(" - Gmail: List, search, read details, reply, send, or trash emails")
    print(" - Calendar: List, schedule, update, or delete events")
    print(" - Tasks: List, create, or mark tasks as completed")
    print(" - Contacts: Search your contact list for names/emails")
    print(" - Local Files: Read and write text/markdown files in the workspace")
    print(" - Web Search: Find current web information via Tavily")
    print("\nType 'exit' or 'quit' to terminate the session.")
    print("="*70)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
            process_agent_interaction(chat, user_input)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred during interaction: {e}")

if __name__ == '__main__':
    main()
