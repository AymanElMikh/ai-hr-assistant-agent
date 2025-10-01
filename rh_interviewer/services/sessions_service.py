# rh_interviewer/service/sessions_service.py

import uuid
import json
from datetime import datetime
from typing import Dict, Optional, Any
import os

from rh_interviewer.schemas import (
    GlobalConfig,
    SessionInfo,
    AgentState,
    build_default_config,
    initialize_state,
    serialize_agent_state,
    deserialize_json_to_state,
)

# --- Configuration for Persistence ---
PERSISTENCE_FILE = "persistent_sessions.json"

class SessionsService:
    """
    Service for managing user sessions and their states, now using persistent storage.
    
    NOTE: In this version, persistence is achieved via a local JSON file.
    For production, replace load/save_sessions with Redis client methods.
    """
    
    def __init__(self):
        """Initialize the sessions service and load existing sessions from persistence."""
        self.global_config = build_default_config()
        self.sessions: Dict[str, Dict] = {}
        self._load_sessions() # Load sessions on startup
    
    # ==========================================================================
    # 💾 PERSISTENCE HELPERS
    # ==========================================================================

    def _load_sessions(self) -> None:
        """Loads all sessions from the persistent store (simulated by a file)."""
        if not os.path.exists(PERSISTENCE_FILE):
            print(f"[{datetime.now().isoformat()}] Persistence file not found. Starting with empty sessions.")
            return

        try:
            with open(PERSISTENCE_FILE, 'r') as f:
                raw_data = json.load(f)
            
            loaded_count = 0
            for session_id, json_string in raw_data.items():
                session_data = deserialize_json_to_state(json_string)
                if session_data:
                    self.sessions[session_id] = session_data
                    loaded_count += 1
            
            print(f"[{datetime.now().isoformat()}] Successfully loaded {loaded_count} sessions from {PERSISTENCE_FILE}")

        except Exception as e:
            print(f"[{datetime.now().isoformat()}] CRITICAL: Failed to load sessions from file: {e}")
            self.sessions = {} # Reset sessions if load fails

    def _save_sessions(self) -> None:
        """Saves all active sessions to the persistent store."""
        data_to_save = {}
        
        for session_id, session_data in self.sessions.items():
            # Use the dedicated serialization function
            try:
                json_string = serialize_agent_state(
                    state=session_data['state'],
                    created_at=session_data['created_at'],
                    last_activity=session_data['last_activity'],
                    config=session_data['config']
                )
                data_to_save[session_id] = json_string
            except Exception as e:
                print(f"Warning: Could not serialize session {session_id}. Skipping save. Error: {e}")

        try:
            with open(PERSISTENCE_FILE, 'w') as f:
                json.dump(data_to_save, f, indent=4)
        except Exception as e:
            print(f"CRITICAL: Failed to save sessions to file: {e}")


    # ==========================================================================
    # 🧑‍💻 CORE SESSION LOGIC (Modified to call persistence helpers)
    # ==========================================================================
    
    def create_session(self) -> str:
        """
        Create a new session with initialized state and save it to persistence.
        """
        session_id = str(uuid.uuid4())
        initial_state = initialize_state(self.global_config)
        
        session_data = {
            'state': initial_state,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'config': {"configurable": {"thread_id": f"hr_session_{session_id}"}}
        }
        
        self.sessions[session_id] = session_data
        self._save_sessions() # Save to persistence immediately
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve session data by session ID (now guaranteed persistent if saved).
        """
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, state: AgentState) -> bool:
        """
        Update the state of an existing session and save to persistence.
        """
        if session_id in self.sessions:
            self.sessions[session_id]['state'] = state
            self.sessions[session_id]['last_activity'] = datetime.now()
            self._save_sessions() # Save new state
            return True
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from both memory and persistence.
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions() # Update persistence after deletion
            return True
        return False
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get detailed information about a session.
        (Logic remains the same, but now uses persistent data)
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return None
        
        state = session_data['state']
        current_stage = state.get('current_stage', 'advancements')
        next_stage = state.get('next_stage', current_stage)
        
        stage_order = self.global_config.stage_order
        try:
            current_idx = stage_order.index(current_stage)
            progress = ((current_idx + 1) / len(stage_order)) * 100
            completed_stages = stage_order[:current_idx]
        except ValueError:
            progress = 0
            completed_stages = []
        
        return SessionInfo(
            session_id=session_id,
            current_stage=current_stage,
            next_stage=next_stage,
            interaction_count=state.get('interaction_count', 0),
            completed_stages=completed_stages,
            progress_percentage=round(progress, 2),
            stage_completion_metrics=state.get('stage_completion_metrics', {})
        )
    
    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        return session_id in self.sessions
    
    def get_session_count(self) -> int:
        """Get the total number of active sessions."""
        return len(self.sessions)
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up sessions older than the specified age, and update the persistent store.
        """
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session_data in self.sessions.items():
            last_activity = session_data.get('last_activity', session_data.get('created_at'))
            age_hours = (current_time - last_activity).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            self._save_sessions() # Save persistence after cleanup
            
        return len(expired_sessions)
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics about a session.
        (Logic remains the same, but now uses persistent data)
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return None
        
        state = session_data['state']
        messages = state.get('messages', [])
        
        # Calculate message counts by role
        # Note: The logic for counting messages by role needs to be robust for the deserialized BaseMessage objects
        user_messages = sum(1 for msg in messages if msg.type == 'human')
        assistant_messages = sum(1 for msg in messages if msg.type == 'ai')
        
        # Calculate session duration
        created_at = session_data.get('created_at')
        last_activity = session_data.get('last_activity')
        duration_minutes = 0
        if created_at and last_activity:
            duration_minutes = (last_activity - created_at).total_seconds() / 60
        
        return {
            'session_id': session_id,
            'created_at': created_at.isoformat() if created_at else None,
            'last_activity': last_activity.isoformat() if last_activity else None,
            'duration_minutes': round(duration_minutes, 2),
            'total_messages': len(messages),
            'user_messages': user_messages,
            'assistant_messages': assistant_messages,
            'current_stage': state.get('current_stage'),
            'interaction_count': state.get('interaction_count', 0),
            'stages_completed': len(state.get('stage_completion_metrics', {}))
        }
    
    def get_global_config(self) -> GlobalConfig:
        """
        Get the global configuration.
        """
        return self.global_config


# ==============================================================================
# 🎯 Refactored Factory Function
# ==============================================================================

def create_sessions_service() -> SessionsService:
    """
    Factory function to create a new SessionsService instance.
    """
    return SessionsService()