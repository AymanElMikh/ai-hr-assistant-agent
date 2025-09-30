# rh_interviewer/database/config.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create the declarative base
Base = declarative_base()


class DatabaseManager:
    """Database manager for handling connections and sessions."""
    
    def __init__(self, database_url: str = "sqlite:///hr_assistant.db"):
        """
        Initialize the database manager.
        
        Args:
            database_url: Database connection string
                - SQLite: "sqlite:///hr_assistant.db"
                - PostgreSQL: "postgresql://user:password@localhost/hr_assistant"
                - MySQL: "mysql+pymysql://user:password@localhost/hr_assistant"
        """
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables in the database."""
        # Import Base after models are defined to avoid circular imports
        from rh_interviewer.database.models import Base
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all tables in the database. Use with caution!"""
        from rh_interviewer.database.models import Base
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self):
        """Get a database session."""
        return self.SessionLocal()
    
    def close_session(self, session):
        """Close a database session."""
        session.close()
    
    def reset_database(self):
        """Reset the database by dropping and recreating all tables."""
        self.drop_tables()
        self.create_tables()


# Create a global database manager instance
db_manager = DatabaseManager()