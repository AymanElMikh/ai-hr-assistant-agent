# run.py

import os
from rh_interviewer import create_app
from rh_interviewer.config import DevelopmentConfig, ProductionConfig
from dotenv import load_dotenv

# 1. Charger les variables d'environnement
# Ceci est nécessaire pour que Flask puisse accéder à FLASK_ENV, OPENAI_API_KEY, etc.
# 🎯 DIAGNOSTIC: On récupère l'état de l'environnement AVANT et APRÈS.

load_dotenv()

# 2. Déterminer la configuration
# Lis la variable d'environnement FLASK_ENV. Par défaut, utilise Development.
FLASK_ENV = os.getenv('FLASK_ENV', 'development')

if FLASK_ENV == 'production':
    Config = ProductionConfig
    print("🌍 Lancement en mode PRODUCTION.")
else:
    Config = DevelopmentConfig
    print("💻 Lancement en mode DÉVELOPPEMENT.")

# 3. Créer l'application
# Utilise votre Application Factory pour construire l'application
app = create_app(config_class=Config)

# 4. Point d'entrée pour le serveur de développement
if __name__ == '__main__':
    # Récupérer le port configuré
    port = app.config.get('PORT', 5000)
    
    # Lancement du serveur de développement Flask
    print(f"🔗 Serveur lancé sur http://127.0.0.1:{port}")
    app.run(
        host='0.0.0.0', # Écoute toutes les interfaces
        port=port,
        debug=app.config.get('FLASK_DEBUG', False),
        use_reloader=app.config.get('FLASK_DEBUG', False) 
    )