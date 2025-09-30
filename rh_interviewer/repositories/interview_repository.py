# rh_interviewer/repository/interview_repository.py

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload  # 🎯 Add this import

from rh_interviewer.database.models import Interview, StageSummary

class InterviewRepository:
    """Repository for handling direct database interactions for Interview and StageSummary models."""

    def __init__(self):
        # A repository doesn't need to manage its own session; it should receive it
        pass

    # Interview Operations
    def create_interview(self, session: Session, **kwargs) -> Optional[Interview]:
        """Creates a new interview record."""
        try:
            interview = Interview(**kwargs)
            session.add(interview)
            session.commit()
            session.refresh(interview)
            return interview
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error creating interview: {e}")
            return None

    def get_interview_by_session(self, session: Session, session_id: str) -> Optional[Interview]:
        """
        Gets an interview by its session ID, eagerly loading its stage summaries.
        """
        try:
            return session.query(Interview).options(selectinload(Interview.stage_summaries)).filter(Interview.session_id == session_id).first()
        except SQLAlchemyError as e:
            print(f"Error getting interview by session ID: {e}")
            return None

    def get_interviews_by_employee_id(self, session: Session, employee_id: int) -> List[Interview]:
        """
        Gets all interviews for a specific employee, eagerly loading their stage summaries.
        """
        try:
            return session.query(Interview).options(selectinload(Interview.stage_summaries)).filter(Interview.employee_id == employee_id).order_by(Interview.interview_date.desc()).all()
        except SQLAlchemyError as e:
            print(f"Error getting employee interviews: {e}")
            return []

    def update_interview(self, session: Session, interview_id: int, **kwargs) -> Optional[Interview]:
        """Updates an existing interview record."""
        try:
            # Note: The query here should also eagerly load to avoid issues later
            interview = session.query(Interview).options(selectinload(Interview.stage_summaries)).filter(Interview.id == interview_id).first()
            if interview:
                for key, value in kwargs.items():
                    if hasattr(interview, key):
                        setattr(interview, key, value)
                session.commit()
                session.refresh(interview)
                return interview
            return None
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error updating interview: {e}")
            return None
    
    # StageSummary Operations
    # These methods handle StageSummary objects directly, so they do not need eager loading
    def create_stage_summary(self, session: Session, **kwargs) -> Optional[StageSummary]:
        """Creates a new stage summary record."""
        try:
            stage_summary = StageSummary(**kwargs)
            session.add(stage_summary)
            session.commit()
            session.refresh(stage_summary)
            return stage_summary
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error creating stage summary: {e}")
            return None

    def get_stage_summaries_by_interview(self, session: Session, interview_id: int) -> List[StageSummary]:
        """Gets all stage summaries for a specific interview."""
        try:
            return session.query(StageSummary).filter(StageSummary.interview_id == interview_id).order_by(StageSummary.stage_order).all()
        except SQLAlchemyError as e:
            print(f"Error getting stage summaries: {e}")
            return []

    def get_stage_summary_by_interview_and_name(self, session: Session, interview_id: int, stage_name: str) -> Optional[StageSummary]:
        """Gets a specific stage summary by interview ID and stage name."""
        try:
            return session.query(StageSummary).filter(
                StageSummary.interview_id == interview_id,
                StageSummary.stage_name == stage_name
            ).first()
        except SQLAlchemyError as e:
            print(f"Error getting stage summary: {e}")
            return None

    def update_stage_summary(self, session: Session, stage_summary_id: int, **kwargs) -> Optional[StageSummary]:
        """Updates an existing stage summary record."""
        try:
            stage_summary = session.query(StageSummary).filter(StageSummary.id == stage_summary_id).first()
            if stage_summary:
                for key, value in kwargs.items():
                    if hasattr(stage_summary, key):
                        setattr(stage_summary, key, value)
                session.commit()
                session.refresh(stage_summary)
                return stage_summary
            return None
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error updating stage summary: {e}")
            return None