from datetime import datetime
from typing import Dict, Any

from flask import Blueprint, request, jsonify, current_app
from langchain_core.messages import HumanMessage, BaseMessage
from dataclasses import asdict

# Import utilities
from rh_interviewer.utils import get_stage_info, create_success_response, create_error_response

# ==============================================================================
# 🎯 API Endpoints (Blueprint)
# ==============================================================================

api_bp = Blueprint('api', __name__)

# ==============================================================================
# 🛠️ Helper Functions
# ==============================================================================

def get_services() -> Dict[str, Any]:
    """Helper function to retrieve all services from the app context."""
    return current_app.extensions['services']

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
# 🎯 Session Endpoints
# ==============================================================================

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify(create_success_response("HR Assistant API is running"))

@api_bp.route('/sessions', methods=['POST'])
def create_session():
    """
    Create a new HR Assistant session.
    Optionally link it to an employee/interview by providing employee_id.
    """
    try:
        services = get_services()
        sessions_service = services['sessions_service']
        employee_service = services['employee_service']
        interview_service = services['interview_service']
        
        data = request.get_json() or {}
        employee_id = data.get('employee_id')
        
        # Create the session
        session_id = sessions_service.create_session()
        session_info = sessions_service.get_session_info(session_id)
        session_data = sessions_service.get_session(session_id)
        
        interview = None
        employee = None
        
        # If employee_id provided, link session to employee and create interview
        if employee_id:
            # 1. Retrieve employee
            employee = employee_service.get_employee(employee_id)
            
            # DEFENSIVE FIX: Ensure object is a dictionary if it has .to_dict()
            if hasattr(employee, 'to_dict'):
                employee = employee.to_dict()
                
            if not employee:
                sessions_service.delete_session(session_id)
                return create_error_response("Employee not found", status_code=404)
            
            # Store employee context in session (using dictionary keys)
            session_data['employee_id'] = employee_id
            session_data['employee_name'] = f"{employee['firstname']} {employee['lastname']}"
            session_data['employee_position'] = employee['poste_equiped']
            session_data['employee_experience'] = employee['level_of_experience']
            
            # 2. Create interview record
            interview = interview_service.create_interview(employee_id, session_id)
            
            # DEFENSIVE FIX: Ensure object is a dictionary if it has .to_dict()
            if interview and hasattr(interview, 'to_dict'):
                interview = interview.to_dict()

            if not interview:
                sessions_service.delete_session(session_id)
                return create_error_response("Failed to create interview", status_code=500)
            
            # Update session state with interview_id for tools to use
            # Access 'id' using dictionary key
            session_data['state']['interview_id'] = interview['id']
        
        initial_messages = session_data['state'].get('messages', [])
        formatted_messages = [serialize_message(msg, session_info.current_stage) for msg in initial_messages]
        stage_info = get_stage_info(session_info.current_stage, sessions_service.get_global_config())
        
        response_data = {
            'session_id': session_id,
            'session_info': asdict(session_info),
            'messages': formatted_messages,
            'stage_info': stage_info
        }
        
        if employee:
            # employee is already a dictionary
            response_data['employee'] = employee
        if interview:
            # interview is already a dictionary
            response_data['interview'] = interview
        
        return jsonify(create_success_response(
            "Session created successfully",
            response_data
        ))
    except Exception as e:
        return create_error_response("Failed to create session", str(e), 500)

@api_bp.route('/sessions/<string:session_id>', methods=['GET'])
def get_session_status(session_id: str):
    """Get current session status with linked interview info if available."""
    services = get_services()
    sessions_service = services['sessions_service']
    interview_service = services['interview_service']
    employee_service = services['employee_service']
    
    session_info = sessions_service.get_session_info(session_id)
    if not session_info:
        return create_error_response("Session not found", status_code=404)
    
    session_data = sessions_service.get_session(session_id)
    messages = session_data['state'].get('messages', [])
    recent_messages = [serialize_message(msg, session_info.current_stage) for msg in messages[-10:]]
    stage_info = get_stage_info(session_info.current_stage, sessions_service.get_global_config())
    
    response_data = {
        'session_info': asdict(session_info),
        'recent_messages': recent_messages,
        'stage_info': stage_info,
        'total_messages': len(messages)
    }
    
    # Add interview info if session is linked to an interview
    interview = interview_service.get_interview_by_session(session_id)
    if interview:
        # DEFENSIVE FIX: Ensure object is a dictionary if it has .to_dict()
        if hasattr(interview, 'to_dict'):
            interview = interview.to_dict()
            
        # interview is now a DICT
        response_data['interview'] = interview
        
        # Access employee_id using dictionary key
        employee = employee_service.get_employee(interview['employee_id'])
        if employee:
            # DEFENSIVE FIX: Ensure object is a dictionary if it has .to_dict()
            if hasattr(employee, 'to_dict'):
                employee = employee.to_dict()
                
            # employee is now a DICT
            response_data['employee'] = employee
    
    return jsonify(create_success_response(
        "Session status retrieved",
        response_data
    ))

@api_bp.route('/sessions/<string:session_id>/messages', methods=['POST'])
def send_message(session_id: str):
    """Send a message to the HR Assistant and auto-save interview progress."""
    services = get_services()
    sessions_service = services['sessions_service']
    hr_assistant_service = services['hr_assistant_service']
    interview_service = services['interview_service']
    
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return create_error_response("Message content is required", status_code=400)
    
    session_data = sessions_service.get_session(session_id)
    if not session_data:
        return create_error_response("Session not found", status_code=404)
    
    current_state = session_data['state']
    current_state['messages'].append(HumanMessage(content=user_message))
    
    # Ensure interview_id is in the state if the session is linked to an interview
    interview = interview_service.get_interview_by_session(session_id)
    if interview:
        # DEFENSIVE FIX: Ensure object is a dictionary if it has .to_dict()
        if hasattr(interview, 'to_dict'):
            interview = interview.to_dict()
        
        # interview is now a DICT
        if 'interview_id' not in current_state:
            # Access 'id' using dictionary key
            current_state['interview_id'] = interview['id']
    
    # Use the HR Assistant service to process the message
    result, error = hr_assistant_service.process_message(current_state, session_data['config'])
    
    if error:
        return create_error_response("Failed to process message", str(error), 500)
    
    sessions_service.update_session(session_id, result)
    session_info = sessions_service.get_session_info(session_id)
    
    last_message = result['messages'][-1]
    assistant_response = serialize_message(last_message, session_info.current_stage)
    
    stage_transition = None
    previous_stage = session_info.current_stage
    
    # Check for stage transition
    if session_info.next_stage != session_info.current_stage:
        stage_transition = {
            'from': session_info.current_stage,
            'to': session_info.next_stage,
            'stage_info': get_stage_info(session_info.next_stage, sessions_service.get_global_config())
        }
        previous_stage = session_info.current_stage
    
    # Auto-save interview progress if session is linked to an interview
    if interview:
        # Update interview status (accessing 'id' using dictionary key)
        interview_service.update_interview(
            interview['id'],
            current_stage=session_info.current_stage,
            status='in_progress'
        )
        
        # If stage just completed (transition detected), save stage summary
        if stage_transition and previous_stage != 'summary':
            # Extract key information from the conversation for this stage
            stage_messages = [msg for msg in result['messages'] if hasattr(msg, 'content')]
            interaction_count = len([msg for msg in stage_messages if 'Human' in msg.__class__.__name__])
            
            # Create a basic stage summary (can be enhanced with AI summarization)
            key_points = [f"Stage completed with {interaction_count} interactions"]
            summary_text = f"Stage '{previous_stage}' completed successfully."
            
            # Accessing 'id' using dictionary key
            interview_service.complete_stage_summary(
                interview_id=interview['id'],
                stage_name=previous_stage,
                summary_text=summary_text,
                key_points=key_points,
                completion_score=0.0,  # Can be calculated based on interaction quality
                interaction_count=interaction_count
            )
    
    response_data = {
        'assistant_response': assistant_response,
        'session_info': asdict(session_info),
        'stage_info': get_stage_info(session_info.current_stage, sessions_service.get_global_config()),
        'stage_transition': stage_transition,
        'is_complete': session_info.current_stage == "summary"
    }
    
    # Add interview info if available (accessing 'id' and 'status' using dictionary keys)
    if interview:
        response_data['interview_id'] = interview['id']
        response_data['interview_status'] = interview['status']
    
    return jsonify(create_success_response(
        "Message processed successfully",
        response_data
    ))

@api_bp.route('/sessions/<string:session_id>/messages', methods=['GET'])
def get_messages(session_id: str):
    """Get all messages for a session."""
    services = get_services()
    sessions_service = services['sessions_service']
    interview_service = services['interview_service']
    
    session_data = sessions_service.get_session(session_id)
    if not session_data:
        return create_error_response("Session not found", status_code=404)
    
    session_info = sessions_service.get_session_info(session_id)
    messages = session_data['state'].get('messages', [])
    formatted_messages = [serialize_message(msg, session_info.current_stage) for msg in messages]
    
    response_data = {
        'messages': formatted_messages,
        'total_count': len(formatted_messages),
        'session_info': asdict(session_info)
    }
    
    # Add interview info if session is linked (interview is now a DICT)
    interview = interview_service.get_interview_by_session(session_id)
    if interview:
        # DEFENSIVE FIX: Ensure object is a dictionary if it has .to_dict()
        if hasattr(interview, 'to_dict'):
            interview = interview.to_dict()
        
        # interview is now a DICT
        response_data['interview'] = interview
    
    return jsonify(create_success_response(
        "Messages retrieved successfully",
        response_data
    ))

@api_bp.route('/sessions/<string:session_id>/summary', methods=['GET'])
def get_summary(session_id: str):
    """Get the performance review summary and save to interview if linked."""
    services = get_services()
    sessions_service = services['sessions_service']
    interview_service = services['interview_service']
    
    session_data = sessions_service.get_session(session_id)
    if not session_data:
        return create_error_response("Session not found", status_code=404)
    
    session_info = sessions_service.get_session_info(session_id)
    if session_info.current_stage != "summary":
        return create_error_response("Summary not available yet. Complete all stages first.", status_code=400)
    
    messages = session_data['state'].get('messages', [])
    summary_content = ""
    for message in reversed(messages):
        if isinstance(message, BaseMessage) and message.content and 'summary' in message.content.lower():
            summary_content = message.content
            break
    
    response_data = {
        'summary': summary_content,
        'session_info': asdict(session_info),
        'completed_at': datetime.now().isoformat()
    }
    
    # Save summary to interview if linked
    interview = interview_service.get_interview_by_session(session_id)
    if interview and summary_content:
        # DEFENSIVE FIX: Ensure object is a dictionary if it has .to_dict()
        if hasattr(interview, 'to_dict'):
            interview = interview.to_dict()
        
        # interview is now a DICT
        
        # Complete the interview with summary
        interview_service.complete_interview(session_id, overall_score=None)
        
        # Save summary stage (accessing 'id' using dictionary key)
        interview_service.complete_stage_summary(
            interview_id=interview['id'],
            stage_name='summary',
            summary_text=summary_content,
            key_points=['Final summary generated'],
            completion_score=1.0,
            interaction_count=len(messages)
        )
        
        # interview is already a dictionary
        response_data['interview'] = interview
    
    return jsonify(create_success_response(
        "Summary retrieved successfully",
        response_data
    ))

@api_bp.route('/sessions/<string:session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """Delete a session. Optionally preserve interview data."""
    services = get_services()
    sessions_service = services['sessions_service']
    interview_service = services['interview_service']
    
    data = request.get_json() or {}
    preserve_interview = data.get('preserve_interview', True)
    
    # Check if session is linked to an interview
    interview = interview_service.get_interview_by_session(session_id)
    
    if interview:
        # DEFENSIVE FIX: Ensure object is a dictionary if it has .to_dict()
        if hasattr(interview, 'to_dict'):
            interview = interview.to_dict()
            
    # interview is now a DICT
    
    if interview and not preserve_interview:
        # Note: This would delete the interview too - might want to restrict this
        return create_error_response(
            "Cannot delete session with linked interview. Complete the interview first.", 
            status_code=400
        )
    
    if sessions_service.delete_session(session_id):
        return jsonify(create_success_response(
            "Session deleted successfully",
            {'interview_preserved': preserve_interview and interview is not None}
        ))
    return create_error_response("Session not found", status_code=404)

@api_bp.route('/sessions/<string:session_id>/help', methods=['GET'])
def get_help(session_id: str):
    """Get context-sensitive help for current stage."""
    services = get_services()
    sessions_service = services['sessions_service']
    
    session_info = sessions_service.get_session_info(session_id)
    if not session_info:
        return create_error_response("Session not found", status_code=404)
    
    help_content = {
        "advancements": {
            "title": "Professional Advancements", 
            "description": "Share your professional growth...", 
            "tips": ["Describe new skills learned", "Mention certifications obtained", "Discuss expanded responsibilities"]
        },
        "challenges": {
            "title": "Challenges & Obstacles", 
            "description": "Discuss difficulties you've encountered...", 
            "tips": ["Focus on learning experiences", "Explain how you overcame obstacles", "Share lessons learned"]
        },
        "achievements": {
            "title": "Key Achievements", 
            "description": "Highlight your most significant successes...", 
            "tips": ["Quantify your results with metrics", "Describe impact on team/company", "Include specific examples"]
        },
        "training_needs": {
            "title": "Training & Development Needs", 
            "description": "Identify areas for professional growth...", 
            "tips": ["Identify skill gaps", "Suggest specific training programs", "Align with career goals"]
        },
        "action_plan": {
            "title": "Action Plans & Future Goals", 
            "description": "Set goals and create plans...", 
            "tips": ["Set specific, measurable goals", "Create realistic timelines", "Identify required resources"]
        },
        "summary": {
            "title": "Performance Review Summary", 
            "description": "Review has been completed and summarized.", 
            "tips": ["Review the complete summary", "Save or export for your records"]
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
            'stage_info': get_stage_info(session_info.current_stage, sessions_service.get_global_config()),
            'session_info': asdict(session_info)
        }
    ))

# EOF
