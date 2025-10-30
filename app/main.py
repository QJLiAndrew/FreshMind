from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base

# Import routers (we'll create these next)
# from app.routers import inventory, recipes, grocery

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

# Include routers (uncomment as you create them)
# app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
# app.include_router(recipes.router, prefix="/api/recipes", tags=["recipes"])
# app.include_router(grocery.router, prefix="/api/grocery", tags=["grocery"])


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