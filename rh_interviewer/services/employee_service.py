# rh_interviewer/services/employee_service.py

from datetime import datetime
from typing import Optional, List, Any, Dict

# IMPORTANT: Add this import statement
from flask import current_app

from rh_interviewer.database.models import Employee
from rh_interviewer.database.config import db_manager
from rh_interviewer.repositories.employee_repository import EmployeeRepository

class EmployeeService:
    """Service for handling employee business logic."""

    def __init__(self, repository: EmployeeRepository, db_manager: Any):
        self.repository = repository
        self.db_manager = db_manager

    def create_employee(self, firstname: str, lastname: str, poste_equiped: str, level_of_experience: str) -> Optional[Dict]:
        """
        Create a new employee and return a dictionary representation.
        """
        session = self.db_manager.get_session()
        try:
            employee_data = {
                "firstname": firstname,
                "lastname": lastname,
                "poste_equiped": poste_equiped,
                "level_of_experience": level_of_experience
            }
            # Call the repository to create the object
            employee = self.repository.create(session, **employee_data)
            
            # If creation was successful, serialize to dictionary
            if employee:
                return employee.to_dict()
            return None
        finally:
            session.close()

    def get_employee(self, employee_id: int) -> Optional[Employee]:
        """Get an employee record using the repository."""
        session = self.db_manager.get_session()
        try:
            return self.repository.get_by_id(session, employee_id)
        finally:
            session.close()

    def get_all_employees(self) -> List[Employee]:
        """Get all employees using the repository."""
        session = self.db_manager.get_session()
        try:
            return self.repository.get_all(session)
        finally:
            session.close()

    def update_employee(self, employee_id: int, **kwargs) -> Optional[Employee]:
        """Update an employee record, handling business logic."""
        session = self.db_manager.get_session()
        try:
            kwargs['updated_at'] = datetime.utcnow()
            return self.repository.update(session, employee_id, **kwargs)
        finally:
            session.close()

    def delete_employee(self, employee_id: int) -> bool:
        """Delete an employee record."""
        session = self.db_manager.get_session()
        try:
            return self.repository.delete(session, employee_id)
        finally:
            session.close()

# ==============================================================================
# 🎯 Refactored Factory Function
# ==============================================================================

def create_employee_service():
    """
    Factory function to create a new EmployeeService instance.
    It retrieves its dependencies from the Flask application context.
    """
    services = current_app.extensions['services']
    repository = services['employee_repository']
    db_manager = services['db_manager']
    return EmployeeService(repository=repository, db_manager=db_manager)