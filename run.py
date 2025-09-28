# run.py

import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_session import Session

# Import the Blueprint from your package
from rh_interviewer.routes import api_bp
# Import the sessions service to access global config for validation
from rh_interviewer.services.sessions_service import sessions_service
from rh_interviewer.utils import validate_environment

def create_app():
    """
    Application factory function.
    Initializes and configures the Flask application.
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

    # Register Blueprint with a URL prefix
    app.register_blueprint(api_bp, url_prefix='/api')

    # Error Handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "message": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"success": False, "message": "Internal server error"}), 500
    
    return app

if __name__ == '__main__':
    try:
        # Validate environment using the sessions service's global config
        validate_environment(sessions_service.get_global_config())
        print("✅ Environment validation passed")
    except Exception as e:
        print(f"❌ Environment validation failed: {e}")
    
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starting HR Assistant Flask API on port {port}")
    print(f"🔧 Debug mode: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )