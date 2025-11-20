from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from pathlib import Path


# Get the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Database
    database_url: str

    # Edamam APIs (optional for now)
    edamam_food_app_id: Optional[str] = None
    edamam_food_app_key: Optional[str] = None
    edamam_recipe_app_id: Optional[str] = None
    edamam_recipe_app_key: Optional[str] = None

    # USDA API (optional for now)
    usda_api_key: Optional[str] = None

    class Config:
        # Explicit path to .env file
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = 'utf-8'
        extra = "ignore"
        case_sensitive = False  # Allow DATABASE_URL or database_url


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()

# Create database engine with connection pooling
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# Dependency for database sessions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database tables
def init_db():
    """Create all tables in the database"""
    # Import all models to ensure they're registered with Base
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")