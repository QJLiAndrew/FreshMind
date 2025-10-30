from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


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
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()

# Create database engine
engine = create_engine(settings.database_url)
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