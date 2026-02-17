"""
API routes for scrape job queue management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db, ScrapeJob, SessionLocal
from app.api.schemas import (
    ScrapeJobCreate, ScrapeJobUpdate, ScrapeJobResponse,
    ScrapeJobListResponse, ScrapeJobStatsResponse,
    GenerateConfigRequest, GenerateConfigResponse
)
from app.config import get_settings
import json

settings = get_settings()

router = APIRouter(prefix="/api/scrape-jobs", tags=["Scrape Jobs"])


def get_queue_position(db: Session) -> int:
    """Get the next available queue position"""
    highest_position = db.query(ScrapeJob.queue_position).filter(
        ScrapeJob.queue_position.isnot(None),
        ScrapeJob.status == 'queued'
    ).order_by(ScrapeJob.queue_position.desc()).first()
    
    return (highest_position[0] + 1) if highest_position else 1


def reposition_queue(db: Session, from_position: int):
    """Reposition queue items after a given position"""
    jobs = db.query(ScrapeJob).filter(
        ScrapeJob.queue_position.isnot(None),
        ScrapeJob.queue_position > from_position,
        ScrapeJob.status == 'queued'
    ).order_by(ScrapeJob.queue_position).all()
    
    for job in jobs:
        job.queue_position -= 1
    
    db.commit()


@router.get("", response_model=ScrapeJobListResponse)
def get_scrape_jobs(db: Session = Depends(get_db)):
    """Get all scrape jobs with statistics"""
    jobs = db.query(ScrapeJob).order_by(ScrapeJob.created_at.desc()).all()
    
    # Calculate statistics
    stats = {
        'queued': db.query(ScrapeJob).filter(ScrapeJob.status == 'queued').count(),
        'scheduled': db.query(ScrapeJob).filter(ScrapeJob.status == 'scheduled').count(),
        'running': db.query(ScrapeJob).filter(ScrapeJob.status == 'running').count(),
        'completed': db.query(ScrapeJob).filter(ScrapeJob.status == 'completed').count(),
        'failed': db.query(ScrapeJob).filter(ScrapeJob.status == 'failed').count(),
    }
    
    return ScrapeJobListResponse(jobs=jobs, stats=stats)


@router.get("/stats", response_model=ScrapeJobStatsResponse)
def get_scrape_job_stats(db: Session = Depends(get_db)):
    """Get scrape job statistics"""
    return ScrapeJobStatsResponse(
        queued=db.query(ScrapeJob).filter(ScrapeJob.status == 'queued').count(),
        scheduled=db.query(ScrapeJob).filter(ScrapeJob.status == 'scheduled').count(),
        running=db.query(ScrapeJob).filter(ScrapeJob.status == 'running').count(),
        completed=db.query(ScrapeJob).filter(ScrapeJob.status == 'completed').count(),
        failed=db.query(ScrapeJob).filter(ScrapeJob.status == 'failed').count(),
    )


@router.post("", response_model=ScrapeJobResponse, status_code=status.HTTP_201_CREATED)
def create_scrape_job(job: ScrapeJobCreate, db: Session = Depends(get_db)):
    """Create a new scrape job"""
    # Determine status and queue position
    if job.scheduled_time:
        job_status = 'scheduled'
        queue_pos = None
    else:
        job_status = 'queued'
        queue_pos = get_queue_position(db)
    
    # Create the job
    db_job = ScrapeJob(
        name=job.name,
        source_type=job.source_type,
        query=job.query,
        max_results=job.max_results,
        status=job_status,
        scheduled_time=datetime.fromisoformat(job.scheduled_time) if job.scheduled_time else None,
        schedule_frequency=job.schedule_frequency,
        equipment_type=job.equipment_type,
        manufacturer=job.manufacturer,
        queue_position=queue_pos,
        autostart_enabled=job.autostart_enabled,
        # Advanced scraping settings
        sites=job.sites,
        search_terms=job.search_terms,
        exclude_terms=job.exclude_terms,
        min_pages=job.min_pages,
        max_pages=job.max_pages,
        min_file_size_mb=job.min_file_size_mb,
        max_file_size_mb=job.max_file_size_mb,
        follow_links=job.follow_links,
        max_depth=job.max_depth,
        extract_directories=job.extract_directories,
        file_extensions=job.file_extensions,
        skip_duplicates=job.skip_duplicates,
        notes=job.notes
    )
    
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    return db_job


@router.get("/current-scrape")
def get_current_scrape(db: Session = Depends(get_db)):
    """Get the currently running scrape job"""
    job = db.query(ScrapeJob).filter(ScrapeJob.status == 'running').first()
    
    if not job:
        return {"running": False, "job": None}
    
    return {
        "running": True,
        "job": {
            "id": job.id,
            "name": job.name,
            "source_type": job.source_type,
            "query": job.query,
            "max_results": job.max_results,
            "progress": job.progress,
            "status": job.status,
            "created_at": job.created_at,
            "updated_at": job.updated_at
        }
    }


@router.get("/{job_id}", response_model=ScrapeJobResponse)
def get_scrape_job(job_id: int, db: Session = Depends(get_db)):
    """Get a specific scrape job by ID"""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape job with ID {job_id} not found"
        )
    
    return job


@router.put("/{job_id}", response_model=ScrapeJobResponse)
def update_scrape_job(job_id: int, job_update: ScrapeJobUpdate, db: Session = Depends(get_db)):
    """Update a scrape job"""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape job with ID {job_id} not found"
        )
    
    # Don't allow updating running jobs
    if job.status == 'running':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a running job"
        )
    
    # Update fields
    update_data = job_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == 'scheduled_time' and value:
            setattr(job, field, datetime.fromisoformat(value))
        else:
            setattr(job, field, value)
    
    # Update status and queue position based on scheduled_time
    if 'scheduled_time' in update_data:
        if job.scheduled_time:
            job.status = 'scheduled'
            job.queue_position = None
        else:
            job.status = 'queued'
            job.queue_position = get_queue_position(db)
    
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    
    return job


@router.delete("/{job_id}")
def delete_scrape_job(job_id: int, db: Session = Depends(get_db)):
    """Delete a scrape job"""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape job with ID {job_id} not found"
        )
    
    # Don't allow deleting running jobs
    if job.status == 'running':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running job"
        )
    
    # Store queue position for repositioning
    queue_pos = job.queue_position
    
    db.delete(job)
    db.commit()
    
    # Reposition remaining items in queue
    if queue_pos:
        reposition_queue(db, queue_pos)
    
    return {"message": "Scrape job deleted successfully"}


@router.post("/{job_id}/run")
def run_scrape_job(job_id: int, db: Session = Depends(get_db)):
    """Run a queued scrape job immediately"""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape job with ID {job_id} not found"
        )
    
    if job.status not in ['queued', 'scheduled', 'failed']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot run job with status '{job.status}'"
        )
    
    # Check if there's already a running job
    running_job = db.query(ScrapeJob).filter(ScrapeJob.status == 'running').first()
    if running_job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Another scrape job is already running. Only one job can run at a time."
        )
    
    # Update job status
    job.status = 'running'
    job.queue_position = None
    job.progress = 0
    job.error_message = None
    job.updated_at = datetime.utcnow()
    db.commit()
    
    # Trigger the actual scraping job
    try:
        from app.tasks.jobs import run_search_job, run_multi_site_scraping_job
        
        # Capture job data before passing to thread
        job_query = job.query
        job_max_results = job.max_results
        job_source_type = job.source_type
        
        # Parse advanced settings
        sites = None
        if job.sites:
            try:
                sites = json.loads(job.sites)
            except json.JSONDecodeError:
                sites = [s.strip() for s in job.sites.split('\n') if s.strip()]
        
        search_terms = None
        if job.search_terms:
            search_terms = [t.strip() for t in job.search_terms.split(',') if t.strip()]
        
        exclude_terms = None
        if job.exclude_terms:
            exclude_terms = [t.strip() for t in job.exclude_terms.split(',') if t.strip()]
        
        file_extensions = None
        if job.file_extensions:
            file_extensions = [e.strip() for e in job.file_extensions.split(',') if e.strip()]
        
        # Run the scraping job in a background thread
        import threading
        def run_job_with_callback():
            def log_callback(message):
                # Update job progress/log
                try:
                    db = SessionLocal()
                    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                    if job:
                        # Extract progress from message if available
                        import re
                        progress_match = re.search(r'(\d+)%', message)
                        if progress_match:
                            job.progress = int(progress_match.group(1))
                        job.updated_at = datetime.utcnow()
                        db.commit()
                    db.close()
                except Exception as e:
                    print(f"Error updating job progress: {e}")
            
            try:
                # Choose the appropriate scraper based on source_type
                if job_source_type == 'multi_site':
                    # If no sites provided, use DuckDuckGo to find sites
                    if not sites:
                        from app.scrapers.duckduckgo import DuckDuckGoScraper
                        ddg_scraper = DuckDuckGoScraper(settings)
                        log_callback("Searching DuckDuckGo for sites...")
                        ddg_results = ddg_scraper.search(job_query, max_results=50)
                        
                        # Extract unique domains from DuckDuckGo results
                        unique_domains = set()
                        sites = []
                        for result in ddg_results:
                            from urllib.parse import urlparse
                            parsed = urlparse(result.url)
                            domain = parsed.netloc
                            if domain and domain not in unique_domains:
                                unique_domains.add(domain)
                                # Use the base URL of the site
                                base_url = f"{parsed.scheme}://{domain}"
                                sites.append(base_url)
                                log_callback(f"Found site: {base_url}")
                        
                        if not sites:
                            log_callback("No sites found from DuckDuckGo search")
                            raise Exception("No sites found from DuckDuckGo search")
                    
                    log_callback(f"Starting multi-site scraping for {len(sites)} sites")
                    run_multi_site_scraping_job(
                        sites=sites,
                        search_terms=search_terms,
                        exclude_terms=exclude_terms,
                        min_pages=job.min_pages,
                        max_pages=job.max_pages,
                        min_file_size_mb=job.min_file_size_mb,
                        max_file_size_mb=job.max_file_size_mb,
                        follow_links=job.follow_links,
                        max_depth=job.max_depth,
                        extract_directories=job.extract_directories,
                        file_extensions=file_extensions,
                        skip_duplicates=job.skip_duplicates,
                        max_results=job_max_results,
                        log_callback=log_callback
                    )
                else:
                    run_search_job(
                        query=job_query,
                        source_type=job_source_type,
                        max_results=job_max_results,
                        equipment_type=job.equipment_type,
                        manufacturer=job.manufacturer
                    )
                # Mark job as completed
                db = SessionLocal()
                job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                if job:
                    job.status = 'completed'
                    job.progress = 100
                    job.updated_at = datetime.utcnow()
                    db.commit()
                    
                    # Check if autostart is enabled and start next job
                    if job.autostart_enabled:
                        start_next_queued_job(db)
                    db.close()
            except Exception as e:
                # Mark job as failed
                db = SessionLocal()
                job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                if job:
                    job.status = 'failed'
                    job.error_message = str(e)
                    job.updated_at = datetime.utcnow()
                    db.commit()
                    db.close()
        
        thread = threading.Thread(target=run_job_with_callback, daemon=True)
        thread.start()
        
    except Exception as e:
        # Revert status if job failed to start
        job.status = 'failed'
        job.error_message = f"Failed to start scraping job: {str(e)}"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scraping job: {str(e)}"
        )
    
    return {"message": "Scrape job started successfully"}


def start_next_queued_job(db: Session):
    """Start the next queued job if autostart is enabled"""
    try:
        # Get the next queued job (position 1)
        next_job = db.query(ScrapeJob).filter(
            ScrapeJob.status == 'queued',
            ScrapeJob.queue_position == 1
        ).first()
        
        if next_job and next_job.autostart_enabled:
            # Update job status
            next_job.status = 'running'
            next_job.queue_position = None
            next_job.progress = 0
            next_job.error_message = None
            next_job.updated_at = datetime.utcnow()
            db.commit()
            
            # Reposition remaining queue
            reposition_queue(db, 0)
            
            # Trigger the actual scraping job
            from app.tasks.jobs import run_search_job, run_multi_site_scraping_job
            import threading
            
            # Parse advanced settings
            sites = None
            if next_job.sites:
                try:
                    sites = json.loads(next_job.sites)
                except json.JSONDecodeError:
                    sites = [s.strip() for s in next_job.sites.split('\n') if s.strip()]
            
            search_terms = None
            if next_job.search_terms:
                search_terms = [t.strip() for t in next_job.search_terms.split(',') if t.strip()]
            
            exclude_terms = None
            if next_job.exclude_terms:
                exclude_terms = [t.strip() for t in next_job.exclude_terms.split(',') if t.strip()]
            
            file_extensions = None
            if next_job.file_extensions:
                file_extensions = [e.strip() for e in next_job.file_extensions.split(',') if e.strip()]
            
            def run_job_with_callback():
                def log_callback(message):
                    try:
                        db = SessionLocal()
                        job = db.query(ScrapeJob).filter(ScrapeJob.id == next_job.id).first()
                        if job:
                            import re
                            progress_match = re.search(r'(\d+)%', message)
                            if progress_match:
                                job.progress = int(progress_match.group(1))
                            job.updated_at = datetime.utcnow()
                            db.commit()
                        db.close()
                    except Exception as e:
                        print(f"Error updating job progress: {e}")
                
                try:
                    # Choose the appropriate scraper based on source_type
                    if next_job.source_type == 'multi_site':
                        # If no sites provided, use DuckDuckGo to find sites
                        if not sites:
                            from app.scrapers.duckduckgo import DuckDuckGoScraper
                            ddg_scraper = DuckDuckGoScraper(settings)
                            log_callback("Searching DuckDuckGo for sites...")
                            ddg_results = ddg_scraper.search(next_job.query, max_results=50)
                            
                            # Extract unique domains from DuckDuckGo results
                            unique_domains = set()
                            sites = []
                            for result in ddg_results:
                                from urllib.parse import urlparse
                                parsed = urlparse(result.url)
                                domain = parsed.netloc
                                if domain and domain not in unique_domains:
                                    unique_domains.add(domain)
                                    # Use the base URL of the site
                                    base_url = f"{parsed.scheme}://{domain}"
                                    sites.append(base_url)
                                    log_callback(f"Found site: {base_url}")
                            
                            if not sites:
                                log_callback("No sites found from DuckDuckGo search")
                                raise Exception("No sites found from DuckDuckGo search")
                        
                        log_callback(f"Starting multi-site scraping for {len(sites)} sites")
                        run_multi_site_scraping_job(
                            sites=sites,
                            search_terms=search_terms,
                            exclude_terms=exclude_terms,
                            min_pages=next_job.min_pages,
                            max_pages=next_job.max_pages,
                            min_file_size_mb=next_job.min_file_size_mb,
                            max_file_size_mb=next_job.max_file_size_mb,
                            follow_links=next_job.follow_links,
                            max_depth=next_job.max_depth,
                            extract_directories=next_job.extract_directories,
                            file_extensions=file_extensions,
                            skip_duplicates=next_job.skip_duplicates,
                            max_results=next_job.max_results,
                            log_callback=log_callback
                        )
                    else:
                        run_search_job(
                            query=next_job.query,
                            source_type=next_job.source_type,
                            max_results=next_job.max_results,
                            equipment_type=next_job.equipment_type,
                            manufacturer=next_job.manufacturer
                        )
                    db = SessionLocal()
                    job = db.query(ScrapeJob).filter(ScrapeJob.id == next_job.id).first()
                    if job:
                        job.status = 'completed'
                        job.progress = 100
                        job.updated_at = datetime.utcnow()
                        db.commit()
                        
                        # Check if autostart is enabled and start next job
                        if job.autostart_enabled:
                            start_next_queued_job(db)
                        db.close()
                except Exception as e:
                    db = SessionLocal()
                    job = db.query(ScrapeJob).filter(ScrapeJob.id == next_job.id).first()
                    if job:
                        job.status = 'failed'
                        job.error_message = str(e)
                        job.updated_at = datetime.utcnow()
                        db.commit()
                        db.close()
            
            thread = threading.Thread(target=run_job_with_callback, daemon=True)
            thread.start()
    except Exception as e:
        print(f"Error starting next queued job: {e}")


@router.post("/toggle-autostart")
def toggle_autostart(db: Session = Depends(get_db)):
    """Toggle autostart for all queued jobs"""
    # Get current autostart state from first queued job
    first_job = db.query(ScrapeJob).filter(
        ScrapeJob.status == 'queued'
    ).order_by(ScrapeJob.queue_position).first()
    
    if not first_job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No queued jobs to toggle autostart"
        )
    
    # Toggle the state
    new_state = not first_job.autostart_enabled
    
    # Update all queued jobs
    db.query(ScrapeJob).filter(
        ScrapeJob.status == 'queued'
    ).update({'autostart_enabled': new_state})
    
    db.commit()
    
    return {"autostart_enabled": new_state, "message": f"Autostart {'enabled' if new_state else 'disabled'} for all queued jobs"}


@router.post("/{job_id}/stop")
def stop_scrape_job(job_id: int, db: Session = Depends(get_db)):
    """Stop a running scrape job"""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape job with ID {job_id} not found"
        )
    
    if job.status != 'running':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not running (current status: '{job.status}')"
        )
    
    # Update job status
    job.status = 'queued'
    job.queue_position = get_queue_position(db)
    job.updated_at = datetime.utcnow()
    db.commit()
    
    # TODO: Stop the actual scraping job
    
    return {"message": "Scrape job stopped successfully"}


@router.get("/{job_id}/logs")
def get_scrape_job_logs(job_id: int, db: Session = Depends(get_db)):
    """Get logs for a specific scrape job"""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape job with ID {job_id} not found"
        )
    
    # For now, return a simple log based on job status
    # In a real implementation, this would fetch from a logs table
    logs = []
    
    if job.status == 'running':
        logs.append({
            "time": datetime.utcnow().isoformat(),
            "level": "info",
            "message": f"Scraping job '{job.name}' is running..."
        })
        logs.append({
            "time": datetime.utcnow().isoformat(),
            "level": "info",
            "message": f"Query: {job.query}"
        })
        logs.append({
            "time": datetime.utcnow().isoformat(),
            "level": "info",
            "message": f"Max results: {job.max_results}"
        })
        if job.progress:
            logs.append({
                "time": datetime.utcnow().isoformat(),
                "level": "success",
                "message": f"Progress: {job.progress}%"
            })
    elif job.status == 'completed':
        logs.append({
            "time": job.updated_at.isoformat(),
            "level": "success",
            "message": f"Job completed successfully at {job.progress}%"
        })
    elif job.status == 'failed':
        logs.append({
            "time": job.updated_at.isoformat(),
            "level": "error",
            "message": f"Job failed: {job.error_message or 'Unknown error'}"
        })
    
    return {"logs": logs}


@router.post("/generate-config", response_model=GenerateConfigResponse)
def generate_scrape_config(request: GenerateConfigRequest):
    """Generate scrape configuration using AI (Groq)"""
    try:
        from groq import Groq
        
        # Check if API key is configured
        if not settings.groq_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Groq API key is not configured. Please set GROQ_API_KEY in your environment."
            )
        
        # Initialize Groq client
        client = Groq(api_key=settings.groq_api_key)
        
        # Create enhanced prompt for Groq with service manual focus
        system_prompt = """You are an expert at configuring web scraping jobs for finding PDF service manuals and technical documentation.

Your task is to generate a scrape job configuration based on the user's description. The configuration MUST include these fields:
- name: A short, descriptive name for the job
- source_type: One of: 'search', 'forum', 'manual_site', 'gdrive'
- query: The search query to use - MUST include 'filetype:pdf' operator for PDF files
- max_results: Number of results to fetch (typically 10-50)
- equipment_type: Optional - the type of equipment (e.g., Camera, Radio, etc.)
- manufacturer: Optional - the manufacturer name (e.g., Canon, Nikon, etc.)
- search_terms: Optional - Comma-separated relevant search terms for finding the target documents
- exclude_terms: Optional - Terms to exclude from search (e.g., "preview, operator, operation, user manual")
- min_pages: Optional - Minimum PDF page count (default: 5)
- traversal_pattern: Optional - Pattern for traversing links (e.g., "Follow links labeled 'download', 'manual', 'service'")

DEFAULT CONFIGURATION FOR SERVICE MANUALS:
When no specific equipment is mentioned, default to searching for service manuals with these criteria:
- Focus on: service manuals, repair manuals, workshop manuals, service station manuals
- Exclude: operator manuals, operation manuals, user manuals, preview PDFs
- Minimum pages: 5
- Traversal: Look for download links, manual sections, service documentation areas

EXAMPLE 1 (Service Manual Default):
For "Find service manuals", you would generate:
{
  "name": "Service Manuals Collection",
  "source_type": "search",
  "query": "service manual filetype:pdf -preview -operator -operation -user",
  "max_results": 20,
  "equipment_type": null,
  "manufacturer": null,
  "search_terms": "service manual, repair manual, workshop manual, service station manual",
  "exclude_terms": "preview, operator, operation, user manual",
  "min_pages": 5,
  "traversal_pattern": "Follow links containing: download, manual, service, repair, workshop"
}

EXAMPLE 2 (Specific Equipment):
For "I want to find vintage Canon camera service manuals from the 1970s", you would generate:
{
  "name": "Vintage Canon Service Manuals 1970s",
  "source_type": "search",
  "query": "Canon service manual filetype:pdf 1970s -preview -operator -operation -user",
  "max_results": 25,
  "equipment_type": "Camera",
  "manufacturer": "Canon",
  "search_terms": "service manual, repair manual, workshop manual, service station manual",
  "exclude_terms": "preview, operator, operation, user manual",
  "min_pages": 5,
  "traversal_pattern": "Follow links containing: download, manual, service, repair, workshop, Canon"
}

EXAMPLE 3 (Nikon DSLR):
For "Find Nikon DSLR service manuals", you would generate:
{
  "name": "Nikon DSLR Service Manuals",
  "source_type": "search",
  "query": "Nikon DSLR service manual filetype:pdf -preview -operator -operation -user",
  "max_results": 20,
  "equipment_type": "Camera",
  "manufacturer": "Nikon",
  "search_terms": "service manual, repair manual, workshop manual, service station manual",
  "exclude_terms": "preview, operator, operation, user manual",
  "min_pages": 5,
  "traversal_pattern": "Follow links containing: download, manual, service, repair, workshop, Nikon"
}

IMPORTANT RULES:
1. ALWAYS include 'filetype:pdf' in the query to target PDF files specifically
2. ALWAYS exclude: preview, operator, operation, user manuals (use - operator in query)
3. Set min_pages to 5 or higher to avoid short preview documents
4. Focus on service manuals, repair manuals, workshop manuals, service station manuals
5. Keep the name concise but descriptive
6. Set max_results between 10-50 for optimal performance
7. Extract equipment_type and manufacturer from the description if available
8. Provide search_terms that include relevant synonyms
9. Provide exclude_terms to filter out unwanted content
10. Provide traversal_pattern for finding PDFs on web pages

Return ONLY valid JSON, no other text."""
        
        user_prompt = f"Generate a scrape job configuration for: {request.prompt}"
        
        # Call Groq API
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        config_json = completion.choices[0].message.content
        config = json.loads(config_json)
        
        # Validate and set defaults
        config.setdefault('name', 'Service Manuals Collection')
        config.setdefault('source_type', 'search')
        config.setdefault('query', 'service manual filetype:pdf -preview -operator -operation -user')
        config.setdefault('max_results', 20)
        config.setdefault('equipment_type', None)
        config.setdefault('manufacturer', None)
        config.setdefault('search_terms', 'service manual, repair manual, workshop manual, service station manual')
        config.setdefault('exclude_terms', 'preview, operator, operation, user manual')
        config.setdefault('min_pages', 5)
        config.setdefault('traversal_pattern', 'Follow links containing: download, manual, service, repair, workshop')
        
        return GenerateConfigResponse(**config)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Failed to generate configuration: {str(e)}\n{traceback.format_exc()}"
        print(f"Error in generate_scrape_config: {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate configuration: {str(e)}"
        )
