# service/sessions_service.py

import uuid
from datetime import datetime
from typing import Dict, Optional, Any

from rh_interviewer.models import (
    GlobalConfig,
    SessionInfo,
    AgentState,
    build_default_config,
    initialize_state
)


class SessionsService:
    """
    Service for managing user sessions and their states.
    NOTE: The current implementation uses in-memory storage, which is suitable
    for development but NOT for production. For a robust solution, consider
    using Redis, a database, or another persistent store.
    """
    
    def __init__(self):
        """Initialize the sessions service."""
        self.global_config = build_default_config()
        self.sessions: Dict[str, Dict] = {}
    
    def create_session(self) -> str:
        """
        Create a new session with initialized state.
        
        Returns:
            str: The unique session ID
        """
        session_id = str(uuid.uuid4())
        initial_state = initialize_state(self.global_config)
        
        self.sessions[session_id] = {
            'state': initial_state,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'config': {"configurable": {"thread_id": f"hr_session_{session_id}"}}
        }
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve session data by session ID.
        
        Args:
            session_id: The unique session identifier
            
        Returns:
            Optional[Dict]: Session data or None if not found
        """
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, state: AgentState) -> bool:
        """
        Update the state of an existing session.
        
        Args:
            session_id: The unique session identifier
            state: The new agent state
            
        Returns:
            bool: True if updated successfully, False if session not found
        """
        if session_id in self.sessions:
            self.sessions[session_id]['state'] = state
            self.sessions[session_id]['last_activity'] = datetime.now()
            return True
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The unique session identifier
            
        Returns:
            bool: True if deleted successfully, False if session not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get detailed information about a session.
        
        Args:
            session_id: The unique session identifier
            
        Returns:
            Optional[SessionInfo]: Session information or None if not found
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
        """
        Check if a session exists.
        
        Args:
            session_id: The unique session identifier
            
        Returns:
            bool: True if session exists, False otherwise
        """
        return session_id in self.sessions
    
    def get_session_count(self) -> int:
        """
        Get the total number of active sessions.
        
        Returns:
            int: Number of active sessions
        """
        return len(self.sessions)
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up sessions older than the specified age.
        
        Args:
            max_age_hours: Maximum age of sessions in hours
            
        Returns:
            int: Number of sessions cleaned up
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
        
        return len(expired_sessions)
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics about a session.
        
        Args:
            session_id: The unique session identifier
            
        Returns:
            Optional[Dict[str, Any]]: Session statistics or None if not found
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return None
        
        state = session_data['state']
        messages = state.get('messages', [])
        
        # Calculate message counts by role
        user_messages = sum(1 for msg in messages if hasattr(msg, 'role') and msg.role == 'user' or 'Human' in msg.__class__.__name__)
        assistant_messages = sum(1 for msg in messages if hasattr(msg, 'role') and msg.role == 'assistant' or 'AI' in msg.__class__.__name__)
        
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
        
        Returns:
            GlobalConfig: The global configuration object
        """
        return self.global_config


# Create a singleton instance for use in routes
sessions_service = SessionsService()