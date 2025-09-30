# rh_interviewer/repositories/employee_repository.py

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload # 🎯 Add this import

from rh_interviewer.database.models import Employee

class EmployeeRepository:
    """Repository for handling direct employee database interactions."""

    def create(self, session: Session, **kwargs) -> Optional[Employee]:
        """Creates a new employee record in the database."""
        try:
            employee = Employee(**kwargs)
            session.add(employee)
            session.commit()
            session.refresh(employee)
            return employee
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error creating employee: {e}")
            return None

    def get_by_id(self, session: Session, employee_id: int) -> Optional[Employee]:
        """
        Retrieves an employee by their ID, eagerly loading their interviews.
        This prevents lazy-loading errors when the session is closed.
        """
        try:
            return session.query(Employee).options(selectinload(Employee.interviews)).filter(Employee.id == employee_id).first()
        except SQLAlchemyError as e:
            print(f"Error getting employee by ID: {e}")
            return None

    def get_all(self, session: Session) -> List[Employee]:
        """Retrieves all employees from the database."""
        try:
            return session.query(Employee).all()
        except SQLAlchemyError as e:
            print(f"Error getting all employees: {e}")
            return []

    def update(self, session: Session, employee_id: int, **kwargs) -> Optional[Employee]:
        """Updates an existing employee record."""
        try:
            employee = self.get_by_id(session, employee_id)
            if employee:
                for key, value in kwargs.items():
                    if hasattr(employee, key):
                        setattr(employee, key, value)
                session.commit()
                session.refresh(employee)
                return employee
            return None
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error updating employee: {e}")
            return None

    def delete(self, session: Session, employee_id: int) -> bool:
        """Deletes an employee record from the database."""
        try:
            employee = self.get_by_id(session, employee_id)
            if employee:
                session.delete(employee)
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error deleting employee: {e}")
            return False