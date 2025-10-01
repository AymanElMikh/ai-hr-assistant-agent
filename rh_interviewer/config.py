# rh_interviewer/config.py

import os
# L'intégration de la clé OpenAI n'est pas recommandée ici pour la sécurité,
# mais si vous la mettez, utilisez os.environ.get.
# Pour les besoins de Flask, nous allons juste configurer les variables Flask.

class BaseConfig:
    """Configuration de base commune à tous les environnements."""
    
    # Récupère la clé secrète de l'environnement (recommandé pour la production)
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key_here')
    
    # Configuration de la session Flask
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    # Configuration de l'API OpenAI (lue de l'environnement)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') 


class DevelopmentConfig(BaseConfig):
    """Configuration pour l'environnement de développement."""
    FLASK_DEBUG = True
    PORT = os.environ.get('PORT', 5000)
    # L'URL de la base de données de développement (ici SQLite par défaut)
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///hr_assistant.db')


class ProductionConfig(BaseConfig):
    """Configuration pour l'environnement de production."""
    FLASK_DEBUG = False
    PORT = os.environ.get('PORT', 80)
    # L'URL de la base de données de production (doit être définie dans l'environnement)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # Assurez-vous que la clé secrète est bien définie en production
    if not BaseConfig.SECRET_KEY:
        raise ValueError("FATAL ERROR: FLASK_SECRET_KEY must be set in production.")