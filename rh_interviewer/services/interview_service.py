# rh_interviewer/service/interview_service.py

from datetime import datetime
from typing import Optional, List, Dict, Any

from flask import current_app

from rh_interviewer.database.models import Interview, StageSummary
from rh_interviewer.database.config import db_manager
from rh_interviewer.repositories.interview_repository import InterviewRepository


class InterviewService:
    """Service for handling interview and stage summary business logic."""

    def __init__(self, repository: InterviewRepository, employee_service: Any, db_manager: Any):
        self.repository = repository
        # Use the injected employee_service instance
        self.employee_service = employee_service
        self.db_manager = db_manager

    # Interview operations
    def create_interview(self, employee_id: int, session_id: str) -> Optional[Dict]:
        """Create a new interview record with default 'in_progress' status."""
        session = self.db_manager.get_session()
        try:
            interview = self.repository.create_interview(
                session,
                employee_id=employee_id,
                session_id=session_id,
                status='in_progress'
            )
            # 🎯 Serialize to dictionary before returning
            if interview:
                return interview.to_dict()
            return None
        finally:
            session.close()

    def get_interview_by_session(self, session_id: str) -> Optional[Dict]:
        """Get an interview by session ID."""
        session = self.db_manager.get_session()
        try:
            interview = self.repository.get_interview_by_session(session, session_id)
            # 🎯 Serialize to dictionary before returning
            if interview:
                return interview.to_dict()
            return None
        finally:
            session.close()

    def update_interview(self, interview_id: int, **kwargs) -> Optional[Dict]:
        """Update an existing interview record with new data."""
        session = self.db_manager.get_session()
        try:
            interview = self.repository.update_interview(session, interview_id, **kwargs)
            # 🎯 Serialize to dictionary before returning
            if interview:
                return interview.to_dict()
            return None
        finally:
            session.close()

    def get_employee_interviews(self, employee_id: int) -> List[Dict]:
        """Get all interviews for an employee."""
        session = self.db_manager.get_session()
        try:
            interviews = self.repository.get_interviews_by_employee_id(session, employee_id)
            # 🎯 Serialize all ORM objects to a list of dictionaries
            return [interview.to_dict() for interview in interviews]
        finally:
            session.close()
    
    def complete_interview(self, session_id: str, overall_score: Optional[float] = None) -> Optional[Dict]:
        """Mark an interview as completed and set its score."""
        session = self.db_manager.get_session()
        try:
            interview = self.repository.get_interview_by_session(session, session_id)
            if interview:
                updated_interview = self.repository.update_interview(
                    session,
                    interview.id,
                    status='completed',
                    completed_at=datetime.utcnow(),
                    overall_score=overall_score
                )
                # 🎯 Serialize to dictionary before returning
                if updated_interview:
                    return updated_interview.to_dict()
            return None
        finally:
            session.close()

    # Stage Summary operations
    def create_stage_summary(self, interview_id: int, stage_name: str, stage_order: int, 
                             **kwargs) -> Optional[Dict]:
        """Create a stage summary record with a new ID."""
        session = self.db_manager.get_session()
        try:
            stage_summary = self.repository.create_stage_summary(
                session,
                interview_id=interview_id,
                stage_name=stage_name,
                stage_order=stage_order,
                **kwargs
            )
            # 🎯 Serialize to dictionary before returning
            if stage_summary:
                return stage_summary.to_dict()
            return None
        finally:
            session.close()
    
    def update_stage_summary_by_interview_and_name(self, interview_id: int, stage_name: str, **kwargs) -> Optional[Dict]:
        """Update a stage summary using a combination of interview ID and stage name."""
        session = self.db_manager.get_session()
        try:
            stage_summary = self.repository.get_stage_summary_by_interview_and_name(session, interview_id, stage_name)
            if stage_summary:
                updated_summary = self.repository.update_stage_summary(session, stage_summary.id, **kwargs)
                # 🎯 Serialize to dictionary before returning
                if updated_summary:
                    return updated_summary.to_dict()
            return None
        finally:
            session.close()

    def get_interview_stage_summaries(self, interview_id: int) -> List[Dict]:
        """Get all stage summaries for an interview."""
        session = self.db_manager.get_session()
        try:
            summaries = self.repository.get_stage_summaries_by_interview(session, interview_id)
            # 🎯 Serialize to a list of dictionaries before returning
            return [summary.to_dict() for summary in summaries]
        finally:
            session.close()
            
    def complete_stage_summary(self, interview_id: int, stage_name: str, **kwargs) -> Optional[Dict]:
        """Complete a stage summary, updating it or creating it if it doesn't exist."""
        session = self.db_manager.get_session()
        try:
            stage_summary = self.repository.get_stage_summary_by_interview_and_name(session, interview_id, stage_name)
            
            kwargs['completed_at'] = datetime.utcnow()
            
            if stage_summary:
                updated_summary = self.repository.update_stage_summary(session, stage_summary.id, **kwargs)
                if updated_summary:
                    return updated_summary.to_dict()
            else:
                stage_summaries = self.repository.get_stage_summaries_by_interview(session, interview_id)
                stage_order = len(stage_summaries) + 1
                kwargs['interview_id'] = interview_id
                kwargs['stage_name'] = stage_name
                kwargs['stage_order'] = stage_order
                created_summary = self.repository.create_stage_summary(session, **kwargs)
                if created_summary:
                    return created_summary.to_dict()
            return None
        finally:
            session.close()
            
    # Utility methods
    def get_employee_interview_history(self, employee_id: int) -> Dict[str, Any]:
        """Get the complete interview history for a given employee."""
        # 🎯 The employee service now returns a dictionary, so no need for .to_dict()
        employee_data = self.employee_service.get_employee(employee_id)
        if not employee_data:
            return {}
        
        # 🎯 The repository now returns dictionaries, so no need for list comprehensions
        interviews = self.get_employee_interviews(employee_id)
        
        # 🎯 Iterating through the dictionary data
        for interview in interviews:
            stage_summaries = self.get_interview_stage_summaries(interview.get('id'))
            interview['stage_summaries'] = stage_summaries
            
        return {
            'employee': employee_data,
            'interviews': interviews,
            'total_interviews': len(interviews),
            'completed_interviews': len([i for i in interviews if i.get('status') == 'completed'])
        }


# ==============================================================================
# 🎯 Refactored Factory Function for Flask App Context
# ==============================================================================

def create_interview_service() -> InterviewService:
    """
    Factory function to create a new InterviewService instance.
    It retrieves its dependencies from the Flask application context.
    """
    services = current_app.extensions['services']
    repository = services['interview_repository']
    employee_service = services['employee_service']
    db_manager = services['db_manager']
    
    return InterviewService(repository=repository, employee_service=employee_service, db_manager=db_manager)