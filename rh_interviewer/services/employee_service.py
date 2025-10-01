"""
Employee service module.
Handles business logic for employee operations.
"""

from datetime import datetime
from typing import Optional, List, Dict
from flask import current_app

from rh_interviewer.database.models import Employee
from rh_interviewer.database.db import get_db_session
from rh_interviewer.repositories.employee_repository import EmployeeRepository


class EmployeeService:
    """
    Service for handling employee business logic.
    Manages employee operations with proper session handling.
    """

    def __init__(self, repository: EmployeeRepository):
        """
        Initialize the EmployeeService.
        
        Args:
            repository: EmployeeRepository instance for data access
        """
        self.repository = repository

    def create_employee(
        self,
        firstname: str,
        lastname: str,
        poste_equiped: str,
        level_of_experience: str
    ) -> Optional[Dict]:
        """
        Create a new employee and return a dictionary representation.
        
        Args:
            firstname: Employee's first name
            lastname: Employee's last name
            poste_equiped: Position/role
            level_of_experience: Experience level (e.g., Junior, Senior)
            
        Returns:
            Dictionary representation of the created employee, or None if failed
        """
        session = get_db_session()
        
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

    def get_employee(self, employee_id: int) -> Optional[Employee]:
        """
        Get an employee record by ID.
        
        Args:
            employee_id: ID of the employee to retrieve
            
        Returns:
            Employee object if found, None otherwise
        """
        session = get_db_session()
        return self.repository.get_by_id(session, employee_id)

    def get_all_employees(self) -> List[Employee]:
        """
        Get all employee records.
        
        Returns:
            List of all Employee objects
        """
        session = get_db_session()
        return self.repository.get_all(session)

    def update_employee(self, employee_id: int, **kwargs) -> Optional[Employee]:
        """
        Update an employee record with business logic.
        Automatically updates the 'updated_at' timestamp.
        
        Args:
            employee_id: ID of the employee to update
            **kwargs: Fields to update
            
        Returns:
            Updated Employee object if successful, None otherwise
        """
        session = get_db_session()
        
        # Add timestamp for tracking updates
        kwargs['updated_at'] = datetime.utcnow()
        
        return self.repository.update(session, employee_id, **kwargs)

    def delete_employee(self, employee_id: int) -> bool:
        """
        Delete an employee record.
        
        Args:
            employee_id: ID of the employee to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        session = get_db_session()
        return self.repository.delete(session, employee_id)

    def get_employees_by_position(self, poste_equiped: str) -> List[Employee]:
        """
        Get all employees for a specific position.
        
        Args:
            poste_equiped: Position to filter by
            
        Returns:
            List of Employee objects matching the position
        """
        session = get_db_session()
        return self.repository.find_by_criteria(
            session,
            poste_equiped=poste_equiped
        )

    def get_employees_by_experience(self, level_of_experience: str) -> List[Employee]:
        """
        Get all employees with a specific experience level.
        
        Args:
            level_of_experience: Experience level to filter by
            
        Returns:
            List of Employee objects matching the experience level
        """
        session = get_db_session()
        return self.repository.find_by_criteria(
            session,
            level_of_experience=level_of_experience
        )

    def search_employees(self, search_term: str) -> List[Employee]:
        """
        Search employees by name (firstname or lastname).
        
        Args:
            search_term: Term to search for in employee names
            
        Returns:
            List of Employee objects matching the search term
        """
        session = get_db_session()
        all_employees = self.repository.get_all(session)
        
        # Filter employees by search term (case-insensitive)
        search_lower = search_term.lower()
        return [
            emp for emp in all_employees
            if search_lower in emp.firstname.lower() or search_lower in emp.lastname.lower()
        ]

    def get_employee_count(self) -> int:
        """
        Get the total count of employees.
        
        Returns:
            Total number of employees
        """
        session = get_db_session()
        return len(self.repository.get_all(session))

    def employee_exists(self, employee_id: int) -> bool:
        """
        Check if an employee exists.
        
        Args:
            employee_id: ID of the employee to check
            
        Returns:
            True if employee exists, False otherwise
        """
        return self.get_employee(employee_id) is not None


# ==============================================================================
# 🎯 Factory Function
# ==============================================================================

def create_employee_service() -> EmployeeService:
    """
    Factory function to create a new EmployeeService instance.
    Retrieves dependencies from the Flask application context.
    
    Returns:
        EmployeeService instance with injected dependencies
        
    Raises:
        RuntimeError: If called outside of Flask application context
    """
    services = current_app.extensions.get('services')
    
    if services is None:
        raise RuntimeError(
            "Services not found in app extensions. "
            "Make sure the app is properly initialized."
        )
    
    repository = services.get('employee_repository')
    
    if repository is None:
        raise RuntimeError(
            "EmployeeRepository not found in services. "
            "Make sure it's initialized in create_app()."
        )
    
    return EmployeeService(repository=repository)