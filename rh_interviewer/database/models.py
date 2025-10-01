# rh_interviewer/database/models.py

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON
from werkzeug.security import generate_password_hash, check_password_hash # NOUVEAUTÉ

# Import Base from config
from rh_interviewer.database.db import Base


# ====================================================================
# NOUVEAU MODÈLE : User (Utilisateur)
# ====================================================================
class User(Base):
    """User model for storing authentication credentials."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    # Stocker le hachage du mot de passe
    password_hash = Column(String(128), nullable=False)
    is_active = Column(Integer, default=1) # 1=True, 0=False
    created_at = Column(DateTime, default=datetime.utcnow)

    # Méthodes pour gérer le mot de passe de manière sécurisée
    def set_password(self, password):
        """Hache et stocke le mot de passe."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Vérifie si le mot de passe soumis correspond au hachage stocké."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'is_active': bool(self.is_active)
        }
# ====================================================================


class Employee(Base):
    """Employee model for storing employee information."""
    __tablename__ = 'employees'
    
    # ... (Le reste du modèle Employee reste inchangé) ...
    id = Column(Integer, primary_key=True)
    firstname = Column(String(100), nullable=False)
    lastname = Column(String(100), nullable=False)
    poste_equiped = Column(String(200), nullable=False) 
    level_of_experience = Column(String(50), nullable=False) 
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to interviews
    interviews = relationship("Interview", back_populates="employee", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Employee(id={self.id}, name='{self.firstname} {self.lastname}', position='{self.poste_equiped}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'poste_equiped': self.poste_equiped,
            'level_of_experience': self.level_of_experience,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'interviews_count': len(self.interviews) if self.interviews else 0
        }


class Interview(Base):
    # ... (Modèle Interview inchangé) ...
    __tablename__ = 'interviews'
    
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    session_id = Column(String(100), unique=True, nullable=False)
    interview_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='in_progress')
    overall_score = Column(Float, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    employee = relationship("Employee", back_populates="interviews")
    stage_summaries = relationship("StageSummary", back_populates="interview", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Interview(id={self.id}, employee_id={self.employee_id}, status='{self.status}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'session_id': self.session_id,
            'interview_date': self.interview_date.isoformat() if self.interview_date else None,
            'status': self.status,
            'overall_score': self.overall_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'employee': self.employee.to_dict() if self.employee else None,
            'stage_summaries_count': len(self.stage_summaries) if self.stage_summaries else 0
        }


class StageSummary(Base):
    # ... (Modèle StageSummary inchangé) ...
    __tablename__ = 'stage_summaries'
    
    id = Column(Integer, primary_key=True)
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=False)
    stage_name = Column(String(100), nullable=False) 
    stage_order = Column(Integer, nullable=False) 
    
    # Summary content
    summary_text = Column(Text, nullable=True) 
    key_points = Column(JSON, nullable=True) 
    completion_score = Column(Float, nullable=True) 
    interaction_count = Column(Integer, default=0) 
    
    # Metadata
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    
    # Relationship
    interview = relationship("Interview", back_populates="stage_summaries")
    
    def __repr__(self):
        return f"<StageSummary(id={self.id}, stage='{self.stage_name}', score={self.completion_score})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'interview_id': self.interview_id,
            'stage_name': self.stage_name,
            'stage_order': self.stage_order,
            'summary_text': self.summary_text,
            'key_points': self.key_points,
            'completion_score': self.completion_score,
            'interaction_count': self.interaction_count,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_minutes': self.duration_minutes
        }