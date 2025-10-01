import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_session import Session

# Import configuration classes
from .config import DevelopmentConfig, ProductionConfig

# Import database utilities
from .database.db import DatabaseManager, close_db_session

# Import repositories
from .repositories.employee_repository import EmployeeRepository
from .repositories.interview_repository import InterviewRepository

# Import service factory functions
from .services.employee_service import create_employee_service
from .services.interview_service import create_interview_service
from .services.hr_assistant_service import create_hr_assistant_service
from .services.sessions_service import create_sessions_service

# Import blueprints
from .routes.sessions_routes import api_bp
from .routes.interview_routes import interview_bp
from .routes.employee_routes import employee_bp


def create_app(config_class=None):
    """
    Application factory function.
    Initializes and configures the Flask application using a config class.
    """
    app = Flask(__name__, instance_relative_config=True)

    # 1. Determine and load configuration
    if config_class is None:
        env = os.getenv('FLASK_ENV', 'development')
        config_class = ProductionConfig if env == 'production' else DevelopmentConfig
    
    app.config.from_object(config_class)
    
    print(f"🔧 Configuration loaded: {config_class.__name__}")


    # 2. Configure CORS and Session
    CORS(app, supports_credentials=True)
    Session(app)

    # 3. Initialize DatabaseManager and base service dictionary (CORRIGÉ)
    database_url = app.config.get('DATABASE_URL')
    db_manager = DatabaseManager(database_url=database_url)
    
    app.extensions['db_manager'] = db_manager
    
    # Initialiser le dictionnaire 'services' AVEC les dépôts de base.
    app.extensions['services'] = {
        'db_manager': db_manager,
        'employee_repository': EmployeeRepository(),
        'interview_repository': InterviewRepository()
    }
    
    print(f"✅ Database manager initialized with URL: {database_url}")

    # 4. Initialize database tables if needed
    try:
        db_manager.create_tables()
        print("✅ Database tables verified/created successfully")
    except Exception as e:
        print(f"⚠️ Warning: Could not create tables: {e}")

    # 5. Register teardown function for database cleanup
    app.teardown_appcontext(close_db_session)

    # 6. Initialize high-level services (CORRIGÉ)
    _initialize_services(app) 
    
    services_loaded = list(app.extensions['services'].keys())
    print(f"✅ All services initialized successfully: {services_loaded}")

    # 7. Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(interview_bp, url_prefix='/api')
    app.register_blueprint(employee_bp, url_prefix='/api')
    
    print("✅ All blueprints registered")

    # 8. Register error handlers
    _register_error_handlers(app)

    # 9. Health check route
    @app.route('/status')
    def status():
        return jsonify({
            "status": "running",
            "environment": config_class.__name__,
            "services_loaded": list(app.extensions['services'].keys())
        })

    return app


def _initialize_services(app):
    """
    Initialize all high-level services using their factory functions
    and update the existing app.extensions['services'] dictionary.
    """
    # On récupère le dictionnaire de services existant dans le contexte global de l'app.
    services = app.extensions['services'] 

    # Initialise les services dans le contexte de l'application
    with app.app_context():
        services['employee_service'] = create_employee_service()
        services['sessions_service'] = create_sessions_service()
        services['interview_service'] = create_interview_service()
        services['hr_assistant_service'] = create_hr_assistant_service()
    
    # Le dictionnaire est mis à jour en place, pas de retour nécessaire.


def _register_error_handlers(app):
    """
    Register error handlers for the application.
    """
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": "Not Found",
            "message": "The requested endpoint does not exist"
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "success": False,
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "success": False,
            "error": "Bad Request",
            "message": "The request could not be understood or was missing required parameters"
        }), 400