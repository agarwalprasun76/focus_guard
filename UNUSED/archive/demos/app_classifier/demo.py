"""
App Classifier Demo

This script demonstrates the functionality of the App Classifier system.
It shows how the classifier works with different calendar events and applications.
"""
# --- BEGIN WORKAROUNDS FOR STREAMLIT/TORCH ERRORS ---
import sys
import asyncio

# Workaround for 'no running event loop' error
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Workaround for torch custom class error with Streamlit file watcher
if "torch._classes" in sys.modules:
    del sys.modules["torch._classes"]

# If issues persist, try running Streamlit with:
#   streamlit run demos/app_classifier/demo.py --server.runOnSave false
# --- END WORKAROUNDS ---

import streamlit as st
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import random

# Add parent directory to path to import core modules
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.app_classifier import get_app_classifier, get_app_category
from core.app_classifier.context_rules import ContextRules

# Set page config
st.set_page_config(
    page_title="App Classifier Demo",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .app-view-container {
        max-width: 1200px;
    }
    .stButton>button {
        width: 100%;
    }
    .success {
        color: #2e7d32;
        font-weight: bold;
    }
    .warning {
        color: #ed6c02;
        font-weight: bold;
    }
    .error {
        color: #d32f2f;
        font-weight: bold;
    }
    .info-box {
        background-color: #f5f5f5;
        border-radius: 5px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .app-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Sample calendar events for demo
SAMPLE_EVENTS = [
    {
        "summary": "Math Homework - Calculus",
        "description": "Complete problem set 5",
        "start": {"dateTime": (datetime.now() - timedelta(hours=1)).isoformat()},
        "end": {"dateTime": (datetime.now() + timedelta(hours=1)).isoformat()},
        "id": "math1"
    },
    {
        "summary": "Team Standup",
        "description": "Daily sync with the development team",
        "start": {"dateTime": (datetime.now() + timedelta(hours=2)).isoformat()},
        "end": {"dateTime": (datetime.now() + timedelta(hours=2, minutes=30)).isoformat()},
        "id": "meeting1"
    },
    {
        "summary": "Lunch Break",
        "description": "Time for a break!",
        "start": {"dateTime": (datetime.now() - timedelta(minutes=30)).isoformat()},
        "end": {"dateTime": (datetime.now() + timedelta(minutes=30)).isoformat()},
        "id": "break1"
    },
    {
        "summary": "Research Paper Writing",
        "description": "Work on the machine learning research paper",
        "start": {"dateTime": (datetime.now() + timedelta(hours=4)).isoformat()},
        "end": {"dateTime": (datetime.now() + timedelta(hours=6)).isoformat()},
        "id": "research1"
    },
]

# Sample applications to test
SAMPLE_APPS = [
    ("chrome.exe", "Google - Calculator"),
    ("chrome.exe", "Overleaf - My Paper"),
    ("chrome.exe", "YouTube"),
    ("chrome.exe", "Stack Overflow"),
    ("code.exe", "app_classifier.py"),
    ("teams.exe", "Team Meeting"),
    ("spotify.exe", "Music"),
    ("excel.exe", "Budget.xlsx"),
]

class MockCalendarClient:
    """Mock calendar client for demo purposes."""
    
    def __init__(self):
        self.events = self
        self.calendarId = 'primary'
    
    def __call__(self, *args, **kwargs):
        # Make the instance callable like a method
        return self
    
    def list(self, calendarId=None, timeMin=None, timeMax=None, maxResults=10, singleEvents=True, orderBy='startTime'):
        """Mock the events().list() method from Google Calendar API."""
        now = datetime.now(timezone.utc)
        future_events = []
        
        for event in SAMPLE_EVENTS:
            start_str = event["start"].get("dateTime")
            end_str = event["end"].get("dateTime")
            
            if not start_str or not end_str:
                continue
                
            start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            
            # Make timezone aware if not already
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            
            # Only include events that haven't ended yet
            if end > now:
                future_events.append(event)
        
        # Sort by start time
        future_events.sort(key=lambda e: datetime.fromisoformat(e["start"]["dateTime"].replace('Z', '+00:00')))
        
        # Return in the format expected by the Google Calendar API
        return {
            'items': future_events[:maxResults]
        }
    
    def get_events(self) -> List[Dict]:
        """Get sample calendar events."""
        return SAMPLE_EVENTS
    
    def get_current_event(self) -> Optional[Dict]:
        """Get the current calendar event."""
        now = datetime.now(timezone.utc)
        for event in SAMPLE_EVENTS:
            start_str = event["start"].get("dateTime")
            end_str = event["end"].get("dateTime")
            
            if not start_str or not end_str:
                continue
                
            start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            
            # Make timezone aware if not already
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
                
            if start <= now <= end:
                return event
        return None
    
    def execute(self):
        """Mock the execute method that would normally make an API call."""
        return self

def get_status_emoji(status: str) -> str:
    """Get an emoji for the status."""
    return {
        "allowed": "✅",
        "warning": "⚠️",
        "blocked": "❌"
    }.get(status.lower(), "❓")

def display_app_card(app_name: str, window_title: str, result: Dict, show_expander: bool = True):
    """Display an application card with the classification result."""
    status = "warning" if "flag" in result["reason"].lower() else ("allowed" if result["allowed"] else "blocked")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown(f"### {get_status_emoji(status)}")
    with col2:
        st.markdown(f"**{app_name}**")
        st.caption(window_title)
        
    st.progress(80 if status == "allowed" else (40 if status == "warning" else 10))
    
    if show_expander:
        with st.expander("Details"):
            st.json(result, expanded=False)
    
    st.markdown("---")

def main():
    """Main demo function."""
    st.title("🔍 App Classifier Demo")
    st.markdown(
        "This demo shows how the app classifier works with different calendar events and applications. "
        "Select a calendar event to simulate and see which apps would be allowed or blocked."
    )
    
    # Mock the calendar client
    mock_calendar = MockCalendarClient()
    
    # Initialize the classifier with the mock calendar client
    classifier = get_app_classifier(calendar_client=mock_calendar)
    
    # Sidebar for event selection
    st.sidebar.title("🎯 Current Context")
    
    # Get current context
    current_event = mock_calendar.get_current_event()
    context_info = classifier.get_current_context()
    
    # Display current context
    if current_event:
        st.sidebar.markdown(f"### 📅 {current_event['summary']}")
        st.sidebar.caption(current_event.get('description', 'No description'))
        current_context = context_info.get('context', 'default').replace('_', ' ').title()
        st.sidebar.metric("Current Context", current_context)
    else:
        st.sidebar.info("No current calendar event")
        st.sidebar.metric("Current Context", "Default")
    
    # Display next context change
    next_change = context_info.get('next_change')
    if next_change and 'time' in next_change:
        try:
            next_change_time = datetime.fromisoformat(next_change['time'].replace('Z', '+00:00'))
            # Make sure next_change_time is timezone-aware
            if next_change_time.tzinfo is None:
                next_change_time = next_change_time.replace(tzinfo=timezone.utc)
            
            # Get current time with timezone
            now = datetime.now(timezone.utc)
            time_until = int((next_change_time - now).total_seconds() / 60)
            
            if time_until > 0:
                st.sidebar.metric("Next Change", f"In {time_until} mins")
            else:
                st.sidebar.metric("Next Change", "Now")
        except Exception as e:
            st.sidebar.warning(f"Could not determine next change time: {e}")
            st.sidebar.exception(e)
    
    st.sidebar.markdown("---")
    
    # Allow manual context override for demo purposes
    demo_context = st.sidebar.selectbox(
        "Override Context (for demo):",
        ["auto"] + [e['summary'] for e in SAMPLE_EVENTS],
        index=0
    )
    
    if demo_context != "auto":
        # Override the context for demo purposes
        for event in SAMPLE_EVENTS:
            if event['summary'] == demo_context:
                context_info['context'] = classifier.context_detector.get_primary_context(
                    f"{event['summary']} {event['description']}"
                ) or "default"
                context_info['event'] = event
                break
    
    # Display rules for current context
    st.sidebar.markdown("### 📜 Current Rules")
    rules = ContextRules().get_rules(context_info['context'])
    
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        st.metric("✅ Allowed", len(rules.get('allowed', [])))
    with col2:
        st.metric("⚠️ Flagged", len(rules.get('flag', [])))
    with col3:
        st.metric("❌ Blocked", len(rules.get('blocked', [])))
    
    # Main content
    st.header("Application Classification")
    st.markdown("Test how different applications are classified in the current context.")
    
    # Test sample applications
    for app_name, window_title in SAMPLE_APPS:
        # Get the classification result
        result = classifier.check_app(app_name, window_title)
        
        # Display the result
        st.markdown(f"### {app_name} - {window_title}")
        display_app_card(app_name, window_title, result, show_expander=True)
    
    # Add custom app test
    st.markdown("---")
    st.subheader("Test Custom Application")
    
    col1, col2 = st.columns(2)
    with col1:
        custom_app = st.text_input("Process Name (e.g., chrome.exe)", "chrome.exe")
    with col2:
        custom_window = st.text_input("Window Title (optional)", "")
    
    if st.button("Test Application"):
        if custom_app:
            result = classifier.check_app(custom_app, custom_window)
            display_app_card(custom_app, custom_window, result)
    
    # Show raw context info
    if st.checkbox("Show raw context info"):
        st.json(context_info)

if __name__ == "__main__":
    main()
