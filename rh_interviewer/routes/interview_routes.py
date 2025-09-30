from datetime import datetime
from typing import Dict, List, Any # Added Any for type hinting consistency

from flask import Blueprint, request, jsonify, current_app
from dataclasses import asdict

# Import utilities
from rh_interviewer.utils import create_success_response, create_error_response

# ==============================================================================
# 🎯 Interview and Statistics Endpoints (Blueprint)
# ==============================================================================

interview_bp = Blueprint('interviews', __name__)

# ==============================================================================
# 🎯 Helper Function to Get Services
# ==============================================================================

def get_services() -> Dict[str, Any]:
    """Helper function to retrieve all services from the app context."""
    return current_app.extensions['services']

# ==============================================================================
# 🎯 Interview Endpoints
# ==============================================================================

@interview_bp.route('/employees/<int:employee_id>/interviews', methods=['POST'])
def start_employee_interview(employee_id: int):
    """Start a new interview for an employee with integrated session."""
    try:
        services = get_services()
        employee_service = services['employee_service']
        sessions_service = services['sessions_service']
        interview_service = services['interview_service']
        
        # Check if employee exists. employee is now a DICT.
        employee = employee_service.get_employee(employee_id)
        if not employee:
            return create_error_response("Employee not found", status_code=404)
        
        # Create a new session with employee context
        session_id = sessions_service.create_session()
        
        # Store employee info in session metadata for context
        session_data = sessions_service.get_session(session_id)
        if session_data:
            session_data['employee_id'] = employee_id
            # 🎯 Access employee data using dictionary keys
            session_data['employee_name'] = f"{employee['firstname']} {employee['lastname']}"
            session_data['employee_position'] = employee['poste_equiped']
            session_data['employee_experience'] = employee['level_of_experience']
        
        # Create interview record linked to session. interview is now a DICT.
        interview = interview_service.create_interview(employee_id, session_id)
        if not interview:
            # Rollback: delete the session if interview creation fails
            sessions_service.delete_session(session_id)
            return create_error_response("Failed to create interview", status_code=500)
        
        # Get session info
        session_info = sessions_service.get_session_info(session_id)
        
        return jsonify(create_success_response(
            "Interview started successfully",
            {
                'interview': interview, # 🎯 No .to_dict() needed
                'session_id': session_id,
                'session_info': asdict(session_info),
                'employee': employee     # 🎯 No .to_dict() needed
            }
        ))
    
    except Exception as e:
        return create_error_response("Failed to start interview", str(e), 500)

@interview_bp.route('/employees/<int:employee_id>/interviews', methods=['GET'])
def get_employee_interviews(employee_id: int):
    """Get all interviews for an employee."""
    try:
        services = get_services()
        employee_service = services['employee_service']
        sessions_service = services['sessions_service']
        interview_service = services['interview_service']

        # employee is now a DICT
        employee = employee_service.get_employee(employee_id)
        if not employee:
            return create_error_response("Employee not found", status_code=404)
        
        # interviews is now a LIST[DICT]
        interviews_data = interview_service.get_employee_interviews(employee_id)
        
        # Enrich interview data with session status if session still exists
        for interview_dict in interviews_data:
            # 🎯 Access interview session_id using dictionary keys
            session_info = sessions_service.get_session_info(interview_dict['session_id'])
            if session_info:
                interview_dict['session_active'] = True
                interview_dict['current_stage'] = session_info.current_stage
            else:
                interview_dict['session_active'] = False
        
        return jsonify(create_success_response(
            "Employee interviews retrieved successfully",
            {
                'employee': employee, # 🎯 No .to_dict() needed
                'interviews': interviews_data,
                'total_interviews': len(interviews_data)
            }
        ))
    
    except Exception as e:
        return create_error_response("Failed to retrieve interviews", str(e), 500)

@interview_bp.route('/employees/<int:employee_id>/history', methods=['GET'])
def get_employee_history(employee_id: int):
    """Get complete interview history for an employee."""
    try:
        services = get_services()
        interview_service = services['interview_service']

        # history is already a DICT from the service
        history = interview_service.get_employee_interview_history(employee_id)
        if not history:
            return create_error_response("Employee not found", status_code=404) 
        
        return jsonify(create_success_response(
            "Employee history retrieved successfully",
            history
        ))
    
    except Exception as e:
        return create_error_response("Failed to retrieve employee history", str(e), 500)

# ==============================================================================
# 🎯 Interview Management Endpoints
# ==============================================================================

@interview_bp.route('/interviews/session/<string:session_id>', methods=['GET'])
def get_interview_by_session(session_id: str):
    """Get interview details by session ID with live session data."""
    try:
        services = get_services()
        interview_service = services['interview_service']
        sessions_service = services['sessions_service']
        employee_service = services['employee_service']

        # interview is now a DICT
        interview = interview_service.get_interview_by_session(session_id)
        if not interview:
            return create_error_response("Interview not found", status_code=404)
        
        # Get stage summaries (returns LIST[DICT])
        # 🎯 Access interview id using dictionary keys
        stage_summaries = interview_service.get_interview_stage_summaries(interview['id'])
        
        interview_data = interview # 🎯 interview is already a dictionary
        # 🎯 stage_summaries is already a list of dictionaries
        interview_data['stage_summaries'] = stage_summaries
        
        # Add live session info if session still exists
        session_info = sessions_service.get_session_info(session_id)
        if session_info:
            interview_data['session_info'] = asdict(session_info)
            interview_data['session_active'] = True
        else:
            interview_data['session_active'] = False
        
        # Get employee info. employee is now a DICT.
        # 🎯 Access employee_id using dictionary keys
        employee = employee_service.get_employee(interview['employee_id'])
        if employee:
            interview_data['employee'] = employee # 🎯 No .to_dict() needed
        
        return jsonify(create_success_response(
            "Interview retrieved successfully",
            interview_data
        ))
    
    except Exception as e:
        return create_error_response("Failed to retrieve interview", str(e), 500)

@interview_bp.route('/interviews/session/<string:session_id>/complete', methods=['POST'])
def complete_interview(session_id: str):
    """Mark an interview as completed and optionally close the session."""
    try:
        services = get_services()
        interview_service = services['interview_service']
        sessions_service = services['sessions_service']

        data = request.get_json() or {}
        overall_score = data.get('overall_score')
        close_session = data.get('close_session', True)
        
        # Complete the interview. interview is now a DICT.
        interview = interview_service.complete_interview(session_id, overall_score)
        if not interview:
            return create_error_response("Interview not found", status_code=404)
        
        # Optionally close the session
        if close_session:
            sessions_service.delete_session(session_id)
        
        return jsonify(create_success_response(
            "Interview completed successfully",
            {
                'interview': interview, # 🎯 No .to_dict() needed
                'session_closed': close_session
            }
        ))
    
    except Exception as e:
        return create_error_response("Failed to complete interview", str(e), 500)

@interview_bp.route('/interviews/session/<string:session_id>/stages', methods=['POST'])
def create_stage_summary(session_id: str):
    """Create or update a stage summary from session stage completion."""
    try:
        services = get_services()
        interview_service = services['interview_service']

        data = request.get_json()
        
        # Get interview by session. interview is now a DICT.
        interview = interview_service.get_interview_by_session(session_id)
        if not interview:
            return create_error_response("Interview not found", status_code=404)
        
        # Validate required fields
        required_fields = ['stage_name', 'summary_text']
        for field in required_fields:
            if not data.get(field):
                return create_error_response(f"Missing required field: {field}", status_code=400)
        
        # stage_summary is now a DICT
        stage_summary = interview_service.complete_stage_summary(
            interview_id=interview['id'], # 🎯 Access ID using dictionary key
            stage_name=data['stage_name'],
            summary_text=data['summary_text'],
            key_points=data.get('key_points', []),
            completion_score=data.get('completion_score', 0.0),
            interaction_count=data.get('interaction_count', 0),
            duration_minutes=data.get('duration_minutes')
        )
        
        if stage_summary:
            return jsonify(create_success_response(
                "Stage summary created successfully",
                stage_summary # 🎯 No .to_dict() needed
            ))
        else:
            return create_error_response("Failed to create stage summary", status_code=500)
    
    except Exception as e:
        return create_error_response("Failed to create stage summary", str(e), 500)

@interview_bp.route('/interviews/session/<string:session_id>/auto-save', methods=['POST'])
def auto_save_interview_progress(session_id: str):
    """Auto-save interview progress from active session (called periodically)."""
    try:
        services = get_services()
        interview_service = services['interview_service']
        sessions_service = services['sessions_service']

        # Get interview and session. interview is now a DICT.
        interview = interview_service.get_interview_by_session(session_id)
        if not interview:
            return create_error_response("Interview not found", status_code=404)
        
        session_info = sessions_service.get_session_info(session_id)
        if not session_info:
            return create_error_response("Session not found", status_code=404)
        
        session_data = sessions_service.get_session(session_id)
        if not session_data:
            return create_error_response("Session data not found", status_code=404)
        
        # Update interview with current session stage
        # 🎯 Access ID using dictionary key
        interview_service.update_interview(
            interview['id'],
            status='in_progress',
            current_stage=session_info.current_stage
        )
        
        # Extract stage-specific data from session messages if available
        messages = session_data['state'].get('messages', [])
        
        return jsonify(create_success_response(
            "Progress auto-saved successfully",
            {
                'interview_id': interview['id'], # 🎯 Access ID using dictionary key
                'session_id': session_id,
                'current_stage': session_info.current_stage,
                'message_count': len(messages)
            }
        ))
    
    except Exception as e:
        return create_error_response("Failed to auto-save progress", str(e), 500)

# ==============================================================================
# 🎯 Statistics Endpoints
# ==============================================================================

@interview_bp.route('/statistics/overview', methods=['GET'])
def get_statistics_overview():
    """Get overview statistics."""
    try:
        services = get_services()
        employee_service = services['employee_service']
        sessions_service = services['sessions_service']
        interview_service = services['interview_service']

        # Get all employees and their interviews. employees is now LIST[DICT].
        employees = employee_service.get_all_employees()
        all_interviews = []
        
        for employee in employees:
            # 🎯 Access ID using dictionary key. interviews is now LIST[DICT].
            interviews = interview_service.get_employee_interviews(employee['id'])
            all_interviews.extend(interviews)
        
        # 🎯 Use .get() for dictionary access during filtering
        completed_interviews = [i for i in all_interviews if i.get('status') == 'completed']
        in_progress_interviews = [i for i in all_interviews if i.get('status') == 'in_progress']
        
        # Calculate average score for completed interviews
        # 🎯 Use .get() for dictionary access
        scores = [i.get('overall_score') for i in completed_interviews if i.get('overall_score') is not None]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # Get active sessions count
        # 🎯 Use .get() for dictionary access
        active_sessions = len([i for i in in_progress_interviews 
                                 if sessions_service.get_session_info(i.get('session_id'))])
        
        stats = {
            'total_employees': len(employees),
            'total_interviews': len(all_interviews),
            'completed_interviews': len(completed_interviews),
            'in_progress_interviews': len(in_progress_interviews),
            'active_sessions': active_sessions,
            'average_score': round(avg_score, 2)
        }
        
        return jsonify(create_success_response(
            "Statistics retrieved successfully",
            stats
        ))
    
    except Exception as e:
        return create_error_response("Failed to retrieve statistics", str(e), 500)
