# rh_interviewer/database/config.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
# Importations Flask nécessaires pour le contexte de requête
from flask import g, current_app 

# Créer la base déclarative (Base pour tous les modèles)
Base = declarative_base()


class DatabaseManager:
    """Gestionnaire de base de données (SQLAlchemy Engine/SessionMaker).
       Ce gestionnaire ne s'occupe PAS de la fermeture des sessions dans le contexte Flask.
    """
    
    def __init__(self, database_url: str):
        """Initialise l'Engine et le SessionLocal. La base_url est obligatoire."""
        self.database_url = database_url
        # echo=False en production, True en dev pour voir les requêtes SQL
        self.engine = create_engine(database_url, echo=False) 
        
        # Configure le fabricant de sessions (SessionMaker)
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
    
    # --- Méthodes de Gestion des Tables ---
    # NOTE: Ces méthodes n'ont pas besoin de 'Base' importé ici.
    # L'importation doit se faire dans la fonction au moment de l'appel (comme vous l'aviez fait)
    def create_tables(self):
        """Crée toutes les tables dans la base de données."""
        from rh_interviewer.database.models import Base  # Importation au besoin
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Supprime toutes les tables dans la base de données. À utiliser avec prudence !"""
        from rh_interviewer.database.models import Base
        Base.metadata.drop_all(bind=self.engine)

# --- Fonction Utilitaires pour l'Intégration Flask ---

# NOTE : db_manager n'est PAS initialisé globalement ici. Il est créé
# et stocké dans l'objet 'app' dans l'Application Factory.

def get_db_session():
    """
    Retourne la session de base de données unique pour la requête en cours.
    Si elle n'existe pas, la crée et la stocke dans l'objet 'g'.
    """
    # 1. Vérifie si la session est dans l'objet 'g' de la requête
    if 'db_session' not in g:
        
        # 2. Récupère l'instance du DatabaseManager stockée dans l'application
        db_manager = current_app.extensions['db_manager']
        
        # 3. Crée une nouvelle session et la stocke dans g
        g.db_session = db_manager.SessionLocal()

    return g.db_session

def close_db_session(e=None):
    """
    Ferme la session de base de données stockée dans l'objet 'g'.
    Cette fonction doit être enregistrée comme fonction de nettoyage Flask.
    """
    # Récupère et supprime la session de 'g'
    session = g.pop('db_session', None)

    if session is not None:
        # 4. Ferme la session SQLAlchemy
        session.close()