"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.database import init_db
from app.api.routes import router
from app.api.file_routes import router as file_router
from app.api.scrape_routes import router as scrape_router
from app.api.passive_income_routes import router as passive_income_router
from app.config import get_settings

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Automatic PDF Manual Scraper and Passive Income Generator"
)

# Include API routes
app.include_router(router)
app.include_router(file_router)
app.include_router(scrape_router)
app.include_router(passive_income_router)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    
    # Initialize passive income tables
    try:
        from app.passive_income.database import create_passive_income_tables, init_default_platforms
        create_passive_income_tables()
        init_default_platforms()
        print("Passive income system initialized!")
    except Exception as e:
        print(f"Warning: Could not initialize passive income system: {e}")
    
    # Clean up stale running jobs from previous app instance
    try:
        from app.api.scrape_routes import cleanup_stale_running_jobs
        from app.database import SessionLocal
        db = SessionLocal()
        cleanup_stale_running_jobs(db)
        db.close()
        print("Cleaned up stale running jobs from previous session")
    except Exception as e:
        print(f"Warning: Could not clean up stale jobs: {e}")
    
    print(f"{settings.app_name} v{settings.app_version} started!")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Serve static files for dashboard
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Serve dashboard HTML
@app.get("/dashboard")
async def dashboard():
    """Serve the dashboard HTML"""
    dashboard_path = Path(__file__).parent / "static" / "index.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"message": "Dashboard not found"}


# Serve scrape queue HTML
@app.get("/scrape-queue")
async def scrape_queue():
    """Serve the scrape queue HTML"""
    queue_path = Path(__file__).parent / "static" / "scrape-queue.html"
    if queue_path.exists():
        return FileResponse(queue_path)
    return {"message": "Scrape queue not found"}


# Serve passive income dashboard HTML
@app.get("/passive-income")
async def passive_income_dashboard():
    """Serve the passive income dashboard HTML"""
    dashboard_path = Path(__file__).parent / "static" / "passive-income.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"message": "Passive income dashboard not found"}


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon - return empty response"""
    return {"message": "No favicon"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        reload=settings.debug
    )
