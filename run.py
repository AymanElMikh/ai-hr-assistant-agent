# run.py

import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_session import Session

# Import Blueprints
from rh_interviewer.routes.sessions_routes import api_bp
from rh_interviewer.routes.interview_routes import interview_bp
from rh_interviewer.routes.employee_routes import employee_bp

# --- IMPORTANT CHANGE HERE ---
# Import the factory functions instead of the service classes
from rh_interviewer.database.config import db_manager
from rh_interviewer.repositories.employee_repository import EmployeeRepository
from rh_interviewer.repositories.interview_repository import InterviewRepository
from rh_interviewer.services.employee_service import create_employee_service
from rh_interviewer.services.interview_service import create_interview_service
from rh_interviewer.services.hr_assistant_service import create_hr_assistant_service
from rh_interviewer.services.sessions_service import create_sessions_service

# Import other utilities
from rh_interviewer.utils import validate_environment

def create_app(services):
    """
    Application factory function.
    Initializes and configures the Flask application.
    Services are passed as an argument.
    """
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    
    # Enable CORS
    CORS(app, supports_credentials=True)
    Session(app)

    # Attach services to the app context or use a global manager
    # NOTE: This is where the service instances are made available to the rest of the application.
    app.extensions['services'] = services

    # Register Blueprints
    # Note: Blueprints are now responsible for getting services from the app context
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(interview_bp, url_prefix='/api')
    app.register_blueprint(employee_bp, url_prefix='/api')

    # Error Handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "message": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"success": False, "message": "Internal server error"}), 500
    
    return app

if __name__ == '__main__':
    # 1. Validation and Database Initialization
    try:
        # Validate environment
        validate_environment(db_manager)
        print("✅ Environment validation passed")
    except Exception as e:
        print(f"❌ Environment validation failed: {e}")
    
    try:
        # Initialize the SQL database tables
        print("🔧 Initializing SQL database tables...")
        db_manager.create_tables()
        print("✅ Database tables created successfully.")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}. Ensure SQLAlchemy models are defined.")

    # 2. Centralized Service Initialization using Factory Functions
    # Create a dictionary to hold all services and their dependencies.
    # This dictionary will be attached to the app context.
    all_services = {
        'db_manager': db_manager,
        'employee_repository': EmployeeRepository(),
        'interview_repository': InterviewRepository()
    }

    # Use the factory functions to instantiate services,
    # which will automatically pull dependencies from the `all_services` dictionary
    # when the Flask app context is available.
    # We must create the app instance first to have an app context.
    
    # Temporarily create the app to build services within an app context
    # This is a common pattern for complex Flask app factories
    temp_app = Flask(__name__)
    temp_app.extensions['services'] = all_services
    with temp_app.app_context():
        all_services['employee_service'] = create_employee_service()
        all_services['sessions_service'] = create_sessions_service()
        all_services['interview_service'] = create_interview_service()
        all_services['hr_assistant_service'] = create_hr_assistant_service()

    # 3. Start Application
    # Now that all services are instantiated, pass them to the main app factory
    app = create_app(all_services)
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starting HR Assistant Flask API on port {port}")
    print(f"🔧 Debug mode: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
