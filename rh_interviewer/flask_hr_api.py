from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_session import Session
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from langchain_core.messages import HumanMessage, BaseMessage

# Import your existing components
from rh_interviewer.rh_assistant_agent import app as langraph_app
from rh_interviewer.utils import (
    build_default_config,
    initialize_state,
    safe_invoke_graph
)

from rh_interviewer.models import GlobalConfig

# ==============================================================================
# Flask App Configuration
# ==============================================================================
flask_app = Flask(__name__)
flask_app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
flask_app.config['SESSION_TYPE'] = 'filesystem'
flask_app.config['SESSION_PERMANENT'] = False
flask_app.config['SESSION_USE_SIGNER'] = True

# Enable CORS for frontend integration
CORS(flask_app, supports_credentials=True)
Session(flask_app)

# ==============================================================================
# Data Models for API Responses
# ==============================================================================
@dataclass
class APIResponse:
    """Standard API response structure."""
    success: bool
    message: str
    data: Dict[Any, Any] = None
    error: str = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class SessionInfo:
    """Session information structure."""
    session_id: str
    current_stage: str
    next_stage: str
    interaction_count: int
    completed_stages: list
    progress_percentage: float
    stage_completion_metrics: Dict[str, Any]

@dataclass
class MessageInfo:
    """Message information structure."""
    content: str
    role: str
    timestamp: str
    stage: str

# ==============================================================================
# Session Management
# ==============================================================================
class SessionManager:
    """Manages user sessions and their states."""
    
    def __init__(self):
        self.global_config = build_default_config()
        self.sessions: Dict[str, Dict] = {}
    
    def create_session(self) -> str:
        """Create a new session and return session ID."""
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
        """Get session data by ID."""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, state: Dict) -> bool:
        """Update session state."""
        if session_id in self.sessions:
            self.sessions[session_id]['state'] = state
            self.sessions[session_id]['last_activity'] = datetime.now()
            return True
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """Get formatted session information."""
        session_data = self.get_session(session_id)
        if not session_data:
            return None
        
        state = session_data['state']
        current_stage = state.get('current_stage', 'advancements')
        next_stage = state.get('next_stage', current_stage)
        
        # Calculate progress
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

# Initialize session manager
session_manager = SessionManager()

# ==============================================================================
# Helper Functions
# ==============================================================================
def serialize_message(message: BaseMessage, stage: str = "") -> Dict:
    """Convert a LangChain message to a serializable format."""
    if hasattr(message, 'content'):
        content = message.content
    else:
        content = str(message)
    
    # Determine role
    role = "assistant"
    if hasattr(message, 'role'):
        role = message.role
    elif hasattr(message, '__class__'):
        if 'Human' in message.__class__.__name__:
            role = "user"
        elif 'System' in message.__class__.__name__:
            role = "system"
    
    return {
        'content': content,
        'role': role,
        'timestamp': datetime.now().isoformat(),
        'stage': stage
    }

def get_stage_info(stage: str, config: GlobalConfig) -> Dict:
    """Get formatted stage information."""
    stage_config = config.stages.get(stage)
    if stage_config:
        # Handle StageConfig object (has attributes, not dictionary keys)
        pretty_name = getattr(stage_config, 'pretty_name', stage.title().replace('_', ' '))
        description = getattr(stage_config, 'description', '')
    else:
        # Fallback for missing stage config
        pretty_name = stage.title().replace('_', ' ')
        description = ''
    
    return {
        'stage': stage,
        'pretty_name': pretty_name,
        'description': description,
        'order': config.stage_order.index(stage) if stage in config.stage_order else -1,
        'total_stages': len(config.stage_order)
    }

def create_success_response(message: str, data: Dict = None) -> Dict:
    """Create a successful API response."""
    return APIResponse(success=True, message=message, data=data or {}).to_dict()

def create_error_response(message: str, error: str = None) -> Dict:
    """Create an error API response."""
    return APIResponse(success=False, message=message, error=error).to_dict()

# ==============================================================================
# API Endpoints
# ==============================================================================

@flask_app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify(create_success_response("HR Assistant API is running"))

@flask_app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create a new HR Assistant session."""
    try:
        session_id = session_manager.create_session()
        session_info = session_manager.get_session_info(session_id)
        session_data = session_manager.get_session(session_id)
        
        # Get initial message
        initial_messages = session_data['state'].get('messages', [])
        formatted_messages = [
            serialize_message(msg, session_info.current_stage) 
            for msg in initial_messages
        ]
        
        stage_info = get_stage_info(session_info.current_stage, session_manager.global_config)
        
        return jsonify(create_success_response(
            "Session created successfully",
            {
                'session_id': session_id,
                'session_info': asdict(session_info),
                'messages': formatted_messages,
                'stage_info': stage_info,
                'initial_message': initial_messages[-1].content if initial_messages else ""
            }
        ))
    
    except Exception as e:
        return jsonify(create_error_response(
            "Failed to create session", 
            str(e)
        )), 500

@flask_app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session_status(session_id: str):
    """Get current session status and information."""
    try:
        session_info = session_manager.get_session_info(session_id)
        if not session_info:
            return jsonify(create_error_response("Session not found")), 404
        
        session_data = session_manager.get_session(session_id)
        messages = session_data['state'].get('messages', [])
        
        # Get recent messages (last 10)
        recent_messages = [
            serialize_message(msg, session_info.current_stage) 
            for msg in messages[-10:]
        ]
        
        stage_info = get_stage_info(session_info.current_stage, session_manager.global_config)
        
        return jsonify(create_success_response(
            "Session status retrieved",
            {
                'session_info': asdict(session_info),
                'recent_messages': recent_messages,
                'stage_info': stage_info,
                'total_messages': len(messages)
            }
        ))
    
    except Exception as e:
        return jsonify(create_error_response(
            "Failed to get session status", 
            str(e)
        )), 500

@flask_app.route('/api/sessions/<session_id>/messages', methods=['POST'])
def send_message(session_id: str):
    """Send a message to the HR Assistant."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify(create_error_response("Message content is required")), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify(create_error_response("Message cannot be empty")), 400
        
        # Get session
        session_data = session_manager.get_session(session_id)
        if not session_data:
            return jsonify(create_error_response("Session not found")), 404
        
        # Add user message to state
        current_state = session_data['state']
        current_state['messages'].append(HumanMessage(content=user_message))
        
        # Process through LangGraph
        result, error = safe_invoke_graph(
            langraph_app, 
            current_state, 
            session_data['config']
        )
        
        if error:
            return jsonify(create_error_response(
                "Failed to process message", 
                str(error)
            )), 500
        
        # Update session with result
        session_manager.update_session(session_id, result)
        
        # Get updated session info
        session_info = session_manager.get_session_info(session_id)
        
        # Get assistant's response
        last_message = result['messages'][-1]
        assistant_response = serialize_message(last_message, session_info.current_stage)
        
        # Check for stage transition
        stage_transition = None
        if session_info.next_stage != session_info.current_stage:
            stage_transition = {
                'from': session_info.current_stage,
                'to': session_info.next_stage,
                'stage_info': get_stage_info(session_info.next_stage, session_manager.global_config)
            }
        
        return jsonify(create_success_response(
            "Message processed successfully",
            {
                'assistant_response': assistant_response,
                'session_info': asdict(session_info),
                'stage_info': get_stage_info(session_info.current_stage, session_manager.global_config),
                'stage_transition': stage_transition,
                'is_complete': session_info.current_stage == "summary"
            }
        ))
    
    except Exception as e:
        return jsonify(create_error_response(
            "Failed to process message", 
            str(e)
        )), 500

@flask_app.route('/api/sessions/<session_id>/messages', methods=['GET'])
def get_messages(session_id: str):
    """Get all messages for a session."""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            return jsonify(create_error_response("Session not found")), 404
        
        session_info = session_manager.get_session_info(session_id)
        messages = session_data['state'].get('messages', [])
        
        # Format all messages
        formatted_messages = [
            serialize_message(msg, session_info.current_stage) 
            for msg in messages
        ]
        
        return jsonify(create_success_response(
            "Messages retrieved successfully",
            {
                'messages': formatted_messages,
                'total_count': len(formatted_messages),
                'session_info': asdict(session_info)
            }
        ))
    
    except Exception as e:
        return jsonify(create_error_response(
            "Failed to retrieve messages", 
            str(e)
        )), 500

@flask_app.route('/api/sessions/<session_id>/summary', methods=['GET'])
def get_summary(session_id: str):
    """Get the performance review summary."""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            return jsonify(create_error_response("Session not found")), 404
        
        session_info = session_manager.get_session_info(session_id)
        
        if session_info.current_stage != "summary":
            return jsonify(create_error_response(
                "Summary not available yet. Complete all stages first."
            )), 400
        
        # Find the summary content
        messages = session_data['state'].get('messages', [])
        summary_content = ""
        
        for message in reversed(messages):
            if hasattr(message, 'content') and message.content:
                content_lower = message.content.lower()
                if any(keyword in content_lower for keyword in ['summary', 'review', 'overview']):
                    summary_content = message.content
                    break
        
        return jsonify(create_success_response(
            "Summary retrieved successfully",
            {
                'summary': summary_content,
                'session_info': asdict(session_info),
                'completed_at': datetime.now().isoformat()
            }
        ))
    
    except Exception as e:
        return jsonify(create_error_response(
            "Failed to retrieve summary", 
            str(e)
        )), 500

@flask_app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """Delete a session."""
    try:
        if session_manager.delete_session(session_id):
            return jsonify(create_success_response("Session deleted successfully"))
        else:
            return jsonify(create_error_response("Session not found")), 404
    
    except Exception as e:
        return jsonify(create_error_response(
            "Failed to delete session", 
            str(e)
        )), 500

@flask_app.route('/api/sessions/<session_id>/help', methods=['GET'])
def get_help(session_id: str):
    """Get context-sensitive help for current stage."""
    try:
        session_info = session_manager.get_session_info(session_id)
        if not session_info:
            return jsonify(create_error_response("Session not found")), 404
        
        # Help content for each stage
        help_content = {
            "advancements": {
                "title": "Professional Advancements & Milestones",
                "description": "Share your professional growth and development",
                "tips": [
                    "Describe new skills you've developed",
                    "Mention certifications or training completed",
                    "Highlight process improvements you've made",
                    "Share technology or tools you've mastered",
                    "Include leadership or mentoring experiences"
                ]
            },
            "challenges": {
                "title": "Challenges & Obstacles",
                "description": "Discuss difficulties you've encountered and how you handled them",
                "tips": [
                    "Be honest about difficulties faced",
                    "Focus on learning experiences",
                    "Mention resource constraints or barriers",
                    "Include team or communication challenges",
                    "Describe how you approached problem-solving"
                ]
            },
            "achievements": {
                "title": "Key Achievements & Accomplishments",
                "description": "Highlight your most significant successes",
                "tips": [
                    "Quantify your results with numbers/metrics",
                    "Include project successes and deliverables",
                    "Mention recognition or awards received",
                    "Highlight contributions to team/company goals",
                    "Share positive feedback from clients/colleagues"
                ]
            },
            "training_needs": {
                "title": "Training & Development Needs",
                "description": "Identify areas for professional growth",
                "tips": [
                    "Identify skill gaps you want to address",
                    "Mention industry trends you want to learn about",
                    "Include technical skills or certifications needed",
                    "Consider leadership or soft skills development",
                    "Think about career advancement requirements"
                ]
            },
            "action_plan": {
                "title": "Action Plans & Future Goals",
                "description": "Set goals and create plans for continued growth",
                "tips": [
                    "Set specific, measurable goals",
                    "Include realistic timelines",
                    "Identify resources or support needed",
                    "Plan regular check-in points",
                    "Consider both short-term and long-term objectives"
                ]
            },
            "summary": {
                "title": "Performance Review Summary",
                "description": "Complete performance review summary",
                "tips": ["Review has been completed and summarized"]
            }
        }
        
        current_help = help_content.get(session_info.current_stage, {
            "title": "General Help",
            "description": "Provide detailed responses with specific examples",
            "tips": ["Be specific and detailed in your responses"]
        })
        
        return jsonify(create_success_response(
            "Help information retrieved",
            {
                'help': current_help,
                'stage_info': get_stage_info(session_info.current_stage, session_manager.global_config),
                'session_info': asdict(session_info)
            }
        ))
    
    except Exception as e:
        return jsonify(create_error_response(
            "Failed to retrieve help", 
            str(e)
        )), 500

# ==============================================================================
# Error Handlers
# ==============================================================================
@flask_app.errorhandler(404)
def not_found(error):
    return jsonify(create_error_response("Endpoint not found")), 404

@flask_app.errorhandler(500)
def internal_error(error):
    return jsonify(create_error_response("Internal server error")), 500

@flask_app.errorhandler(Exception)
def handle_exception(e):
    """Handle unexpected exceptions."""
    return jsonify(create_error_response(
        "An unexpected error occurred", 
        str(e)
    )), 500

# ==============================================================================
# Main Application Runner
# ==============================================================================
if __name__ == '__main__':
    # Validate environment
    try:
        from rh_interviewer.utils import validate_environment
        validate_environment(session_manager.global_config)
        print("✅ Environment validation passed")
    except Exception as e:
        print(f"❌ Environment validation failed: {e}")
    
    # Run the Flask app
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starting HR Assistant Flask API on port {port}")
    print(f"🔧 Debug mode: {debug}")
    
    flask_app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )