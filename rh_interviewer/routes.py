# rh_interviewer/routes.py

from datetime import datetime
from typing import Dict
import json

from flask import Blueprint, request, jsonify
from langchain_core.messages import HumanMessage, BaseMessage
from dataclasses import asdict


# Import models and session manager from the local package
from .models import (
    session_manager
)

# Assuming these are provided by your base code
from rh_interviewer.rh_assistant_agent import app as langraph_app
from rh_interviewer.utils import safe_invoke_graph, get_stage_info, create_success_response, create_error_response

# ==============================================================================
# 🎯 API Endpoints (Blueprint)
# ==============================================================================
# Using a Blueprint to organize routes makes the app more modular.

api_bp = Blueprint('api', __name__)

# ==============================================================================
# 🛠️ Helper Functions
# ==============================================================================
# Helper functions needed for the routes logic

def serialize_message(message: BaseMessage, stage: str = "") -> Dict:
    """Convert a LangChain message to a serializable format."""
    content = getattr(message, 'content', str(message))
    role = getattr(message, 'role', 'assistant')
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

# ==============================================================================
# 🎯 Endpoints
# ==============================================================================

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify(create_success_response("HR Assistant API is running"))

@api_bp.route('/sessions', methods=['POST'])
def create_session():
    """Create a new HR Assistant session."""
    try:
        session_id = session_manager.create_session()
        session_info = session_manager.get_session_info(session_id)
        session_data = session_manager.get_session(session_id)
        
        initial_messages = session_data['state'].get('messages', [])
        formatted_messages = [serialize_message(msg, session_info.current_stage) for msg in initial_messages]
        stage_info = get_stage_info(session_info.current_stage, session_manager.global_config)
        
        return jsonify(create_success_response(
            "Session created successfully",
            {
                'session_id': session_id,
                'session_info': asdict(session_info),
                'messages': formatted_messages,
                'stage_info': stage_info
            }
        ))
    except Exception as e:
        return create_error_response("Failed to create session", str(e), 500)

@api_bp.route('/sessions/<string:session_id>', methods=['GET'])
def get_session_status(session_id: str):
    """Get current session status and information."""
    session_info = session_manager.get_session_info(session_id)
    if not session_info:
        return create_error_response("Session not found", status_code=404)
    
    session_data = session_manager.get_session(session_id)
    messages = session_data['state'].get('messages', [])
    recent_messages = [serialize_message(msg, session_info.current_stage) for msg in messages[-10:]]
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

@api_bp.route('/sessions/<string:session_id>/messages', methods=['POST'])
def send_message(session_id: str):
    """Send a message to the HR Assistant."""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return create_error_response("Message content is required", status_code=400)
    
    session_data = session_manager.get_session(session_id)
    if not session_data:
        return create_error_response("Session not found", status_code=404)
    
    current_state = session_data['state']
    current_state['messages'].append(HumanMessage(content=user_message))
    
    result, error = safe_invoke_graph(langraph_app, current_state, session_data['config'])
    
    if error:
        return create_error_response("Failed to process message", str(error), 500)
    
    session_manager.update_session(session_id, result)
    session_info = session_manager.get_session_info(session_id)
    
    last_message = result['messages'][-1]
    assistant_response = serialize_message(last_message, session_info.current_stage)
    
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

@api_bp.route('/sessions/<string:session_id>/messages', methods=['GET'])
def get_messages(session_id: str):
    """Get all messages for a session."""
    session_data = session_manager.get_session(session_id)
    if not session_data:
        return create_error_response("Session not found", status_code=404)
    
    session_info = session_manager.get_session_info(session_id)
    messages = session_data['state'].get('messages', [])
    formatted_messages = [serialize_message(msg, session_info.current_stage) for msg in messages]
    
    return jsonify(create_success_response(
        "Messages retrieved successfully",
        {
            'messages': formatted_messages,
            'total_count': len(formatted_messages),
            'session_info': asdict(session_info)
        }
    ))

@api_bp.route('/sessions/<string:session_id>/summary', methods=['GET'])
def get_summary(session_id: str):
    """Get the performance review summary."""
    session_data = session_manager.get_session(session_id)
    if not session_data:
        return create_error_response("Session not found", status_code=404)
    
    session_info = session_manager.get_session_info(session_id)
    if session_info.current_stage != "summary":
        return create_error_response("Summary not available yet. Complete all stages first.", status_code=400)
    
    messages = session_data['state'].get('messages', [])
    summary_content = ""
    for message in reversed(messages):
        if isinstance(message, BaseMessage) and message.content and 'summary' in message.content.lower():
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

@api_bp.route('/sessions/<string:session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """Delete a session."""
    if session_manager.delete_session(session_id):
        return jsonify(create_success_response("Session deleted successfully"))
    return create_error_response("Session not found", status_code=404)

@api_bp.route('/sessions/<string:session_id>/help', methods=['GET'])
def get_help(session_id: str):
    """Get context-sensitive help for current stage."""
    session_info = session_manager.get_session_info(session_id)
    if not session_info:
        return create_error_response("Session not found", status_code=404)
    
    help_content = {
        "advancements": {"title": "Professional Advancements", "description": "Share your professional growth...", "tips": ["Describe new skills..."]},
        "challenges": {"title": "Challenges & Obstacles", "description": "Discuss difficulties you've encountered...", "tips": ["Focus on learning experiences..."]},
        "achievements": {"title": "Key Achievements", "description": "Highlight your most significant successes...", "tips": ["Quantify your results..."]},
        "training_needs": {"title": "Training & Development Needs", "description": "Identify areas for professional growth...", "tips": ["Identify skill gaps..."]},
        "action_plan": {"title": "Action Plans & Future Goals", "description": "Set goals and create plans...", "tips": ["Set specific, measurable goals..."]},
        "summary": {"title": "Performance Review Summary", "description": "Review has been completed and summarized.", "tips": ["Review has been completed and summarized."]}
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