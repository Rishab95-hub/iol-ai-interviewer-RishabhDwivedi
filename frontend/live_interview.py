"""
Real-Time Interview Interface
WebSocket-based live interview with streaming AI responses
"""
import streamlit as st
import asyncio
import websockets
import json
from datetime import datetime
import requests

# Configuration
API_BASE_URL = "http://localhost:8001/api"
WS_BASE_URL = "ws://localhost:8001"

st.set_page_config(
    page_title="Live Interview - AI Interviewer",
    page_icon="🎤",
    layout="wide"
)

def api_get(endpoint: str):
    """Make GET request to API"""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


async def connect_interview(interview_id: int):
    """Connect to interview WebSocket"""
    uri = f"{WS_BASE_URL}/ws/interview/{interview_id}"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Store websocket in session state
            return websocket
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None


def main():
    st.title("🎤 Live AI Interview")
    
    # Get interview ID from query params or input
    query_params = st.query_params
    interview_id = query_params.get("interview_id", None)
    
    if not interview_id:
        st.info("Enter your interview ID to begin")
        interview_id_input = st.number_input("Interview ID", min_value=1, step=1)
        
        if st.button("Start Interview"):
            st.query_params["interview_id"] = str(interview_id_input)
            st.rerun()
        return
    
    interview_id = int(interview_id)
    
    # Fetch interview details
    interview = api_get(f"/interviews/{interview_id}")
    
    if not interview:
        st.error("Interview not found")
        return
    
    # Display interview info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Position", interview.get('job_title', 'N/A'))
    with col2:
        st.metric("Status", interview['status'])
    with col3:
        st.metric("Progress", f"{interview.get('current_question_index', 0)}/10")
    
    st.markdown("---")
    
    # Interview interface
    if interview['status'] == 'pending':
        st.info("👋 Welcome to your AI interview! Click 'Begin Interview' when ready.")
        
        if st.button("🎬 Begin Interview", type="primary"):
            st.session_state['interview_started'] = True
            st.rerun()
    
    elif interview['status'] == 'in_progress':
        # Show chat interface
        st.markdown("### 💬 Interview Chat")
        
        # Initialize session state
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'ws_connected' not in st.session_state:
            st.session_state.ws_connected = False
        
        # Display conversation
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Input area
        user_input = st.chat_input("Type your answer here...")
        
        if user_input:
            # Add user message
            st.session_state.messages.append({
                "role": "user",
                "content": user_input
            })
            
            # Send via WebSocket (placeholder - needs async)
            st.info("⏳ AI is processing your response...")
            st.rerun()
        
        # WebSocket connection indicator
        st.sidebar.markdown("### Connection Status")
        if st.session_state.ws_connected:
            st.sidebar.success("🟢 Connected")
        else:
            st.sidebar.warning("🟡 Connecting...")
    
    elif interview['status'] == 'completed':
        st.success("✅ Interview Completed!")
        st.balloons()
        
        st.markdown("### 📊 Interview Summary")
        st.write(f"**Duration:** {interview.get('duration_seconds', 0) // 60} minutes")
        st.write(f"**Questions Answered:** {interview.get('current_question_index', 0)}")
        
        st.info("Your interview report will be generated shortly and sent to the hiring team.")
        
        if st.button("View Transcript"):
            st.write("Transcript feature coming soon")


if __name__ == "__main__":
    main()
