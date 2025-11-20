from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database import engine, Base


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FreshMind API",
    version="1.0.0",
    description="API for FreshMind - Food Inventory & Meal Planning App"
)

# CORS middleware for Android app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from backend.app.routers import inventory, recipes
from backend.app.routers import grocery, users

app.include_router(inventory.router)
app.include_router(recipes.router)
# app.include_router(grocery.router, prefix="/api/grocery", tags=["grocery"])
app.include_router(grocery.router)
app.include_router(users.router)


@app.get("/")
def root():
    return {
        "message": "FreshMind API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)