import uvicorn

if __name__ == "__main__":
    # Since this file is in 'backend/', uvicorn sees the 'app' folder correctly
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)