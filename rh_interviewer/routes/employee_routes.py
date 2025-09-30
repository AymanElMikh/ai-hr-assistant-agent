# rh_interviewer/routes/employee_routes.py

from typing import Dict, List

from flask import Blueprint, request, jsonify, current_app

# Import utilities
from rh_interviewer.utils import create_success_response, create_error_response

# ==============================================================================
# 🎯 Employee CRUD Endpoints (Blueprint)
# ==============================================================================

# Ce blueprint gère uniquement les opérations CRUD sur la ressource 'employee'.
employee_bp = Blueprint('employees', __name__)

# ==============================================================================
# 🎯 Helper Function to Get Service
# ==============================================================================

def get_employee_service():
    """Helper function to retrieve the employee service from the app context."""
    return current_app.extensions['services']['employee_service']

# ==============================================================================
# 🎯 Employee Endpoints
# ==============================================================================

@employee_bp.route('/employees', methods=['POST'])
def create_employee():
    """Create a new employee."""
    try:
        employee_service = get_employee_service()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['firstname', 'lastname', 'poste_equiped', 'level_of_experience']
        for field in required_fields:
            if not data.get(field):
                return create_error_response(f"Missing required field: {field}", status_code=400)
        
        # The service now returns a dictionary directly
        employee_data = employee_service.create_employee(
            firstname=data['firstname'],
            lastname=data['lastname'],
            poste_equiped=data['poste_equiped'],
            level_of_experience=data['level_of_experience']
        )
        
        if employee_data:
            return jsonify(create_success_response(
                "Employee created successfully",
                employee_data # 🎯 Pass the dictionary directly
            ))
        else:
            return create_error_response("Failed to create employee", status_code=500)
    
    except Exception as e:
        return create_error_response("Failed to create employee", str(e), 500)
    
    
@employee_bp.route('/employees', methods=['GET'])
def get_all_employees():
    """Get all employees."""
    try:
        employee_service = get_employee_service()
        employees = employee_service.get_all_employees()
        employees_data = [emp.to_dict() for emp in employees]
        
        return jsonify(create_success_response(
            "Employees retrieved successfully",
            {
                'employees': employees_data,
                'total_count': len(employees_data)
            }
        ))
    
    except Exception as e:
        return create_error_response("Failed to retrieve employees", str(e), 500)

@employee_bp.route('/employees/<int:employee_id>', methods=['GET'])
def get_employee(employee_id: int):
    """Get a specific employee."""
    try:
        employee_service = get_employee_service()
        employee = employee_service.get_employee(employee_id)
        if not employee:
            return create_error_response("Employee not found", status_code=404)
        
        # ✅ Apply the fix here: serialize the object to a dictionary before returning it.
        employee_data = employee.to_dict() 
        
        return jsonify(create_success_response(
            "Employee retrieved successfully",
            employee_data
        ))
    
    except Exception as e:
        return create_error_response("Failed to retrieve employee", str(e), 500)

@employee_bp.route('/employees/<int:employee_id>', methods=['PUT'])
def update_employee(employee_id: int):
    """Update an employee."""
    try:
        employee_service = get_employee_service()
        data = request.get_json()
        
        # Remove None values and invalid fields
        allowed_fields = ['firstname', 'lastname', 'poste_equiped', 'level_of_experience']
        update_data = {k: v for k, v in data.items() if k in allowed_fields and v is not None}
        
        if not update_data:
            return create_error_response("No valid fields to update", status_code=400)
        
        employee = employee_service.update_employee(employee_id, **update_data)
        if not employee:
            return create_error_response("Employee not found", status_code=404)
        
        return jsonify(create_success_response(
            "Employee updated successfully",
            employee.to_dict()
        ))
    
    except Exception as e:
        return create_error_response("Failed to update employee", str(e), 500)

@employee_bp.route('/employees/<int:employee_id>', methods=['DELETE'])
def delete_employee(employee_id: int):
    """Delete an employee."""
    try:
        employee_service = get_employee_service()
        success = employee_service.delete_employee(employee_id)
        if success:
            return jsonify(create_success_response("Employee deleted successfully"))
        else:
            return create_error_response("Employee not found", status_code=404)
    
    except Exception as e:
        return create_error_response("Failed to delete employee", str(e), 500)

# EOF