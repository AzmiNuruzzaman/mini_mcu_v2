# auth/session_manager.py
import json
import os
import streamlit as st
from datetime import datetime, timedelta
import hashlib

SESSION_FILE = "session_data.json"
SESSION_TIMEOUT_HOURS = 24  # Sessions expire after 24 hours

def get_session_id():
    """Generate a unique session ID based on Streamlit's session"""
    if 'session_id' not in st.session_state:
        # Create a unique session ID using Streamlit's session info
        try:
            # Try to get Streamlit's session ID
            import streamlit.runtime.scriptrunner as scriptrunner
            ctx = scriptrunner.get_script_run_ctx()
            session_id = str(ctx.session_id) if ctx else str(id(st.session_state))
        except:
            # Fallback: use memory address of session_state
            session_id = str(id(st.session_state))
        
        st.session_state.session_id = hashlib.md5(session_id.encode()).hexdigest()
    return st.session_state.session_id

def save_session(username, user_role, employee_uid=None):
    """Save session data to file"""
    session_id = get_session_id()
    
    # Load existing sessions
    sessions = {}
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                sessions = json.load(f)
        except:
            sessions = {}
    
    # Save current session
    sessions[session_id] = {
        'username': username,
        'user_role': user_role,
        'employee_uid': employee_uid,
        'timestamp': datetime.now().isoformat(),
        'expires': (datetime.now() + timedelta(hours=SESSION_TIMEOUT_HOURS)).isoformat()
    }
    
    # Clean expired sessions
    current_time = datetime.now()
    sessions = {k: v for k, v in sessions.items() 
                if datetime.fromisoformat(v['expires']) > current_time}
    
    # Save to file
    with open(SESSION_FILE, 'w') as f:
        json.dump(sessions, f)

def load_session():
    """Load session data from file if valid"""
    if not os.path.exists(SESSION_FILE):
        return None
        
    session_id = get_session_id()
    
    try:
        with open(SESSION_FILE, 'r') as f:
            sessions = json.load(f)
            
        if session_id in sessions:
            session_data = sessions[session_id]
            
            # Check if session is still valid
            if datetime.fromisoformat(session_data['expires']) > datetime.now():
                return session_data
            else:
                # Session expired, remove it
                del sessions[session_id]
                with open(SESSION_FILE, 'w') as f:
                    json.dump(sessions, f)
                    
    except:
        pass
        
    return None

def clear_session():
    """Clear current session"""
    if not os.path.exists(SESSION_FILE):
        return
        
    session_id = get_session_id()
    
    try:
        with open(SESSION_FILE, 'r') as f:
            sessions = json.load(f)
            
        if session_id in sessions:
            del sessions[session_id]
            
            with open(SESSION_FILE, 'w') as f:
                json.dump(sessions, f)
    except:
        pass