"""
API routes for scrape job queue management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db, ScrapeJob, ScrapeJobLog, SessionLocal
from app.api.schemas import (
    ScrapeJobCreate, ScrapeJobUpdate, ScrapeJobResponse,
    ScrapeJobListResponse, ScrapeJobStatsResponse,
    GenerateConfigRequest, GenerateConfigResponse
)
from app.config import get_settings
import json
import threading

settings = get_settings()

router = APIRouter(prefix="/api/scrape-jobs", tags=["Scrape Jobs"])

# Global thread tracking
running_threads = {}  # Maps job_id -> thread object
running_threads_lock = threading.Lock()


def get_queue_position(db: Session) -> int:
    """Get the next available queue position"""
    highest_position = db.query(ScrapeJob.queue_position).filter(
        ScrapeJob.queue_position.isnot(None),
        ScrapeJob.status == 'queued'
    ).order_by(ScrapeJob.queue_position.desc()).first()
    
    return (highest_position[0] + 1) if highest_position else 1


def reposition_queue(db: Session, from_position: int = 0):
    """Reposition all queued items to have consecutive positions starting from 1"""
    jobs = db.query(ScrapeJob).filter(
        ScrapeJob.status == 'queued',
        ScrapeJob.queue_position.isnot(None)
    ).order_by(ScrapeJob.queue_position.asc()).all()
    
    # Reassign positions consecutively
    for i, job in enumerate(jobs, start=1):
        job.queue_position = i
    
    db.commit()


def cleanup_stale_running_jobs(db: Session):
    """
    Clean up jobs that are marked as 'running' but have no active thread.
    This can happen if the application restarts or crashes.
    
    Also cleans up jobs that have been running too long (stuck jobs).
    """
    with running_threads_lock:
        running_job_ids = set(running_threads.keys())
    
    # Find jobs marked as running but without an active thread
    stale_jobs = db.query(ScrapeJob).filter(
        ScrapeJob.status == 'running'
    ).all()
    
    # Also check for jobs running too long (more than 2 hours)
    from datetime import timedelta
    stale_threshold = datetime.utcnow() - timedelta(hours=2)
    
    for job in stale_jobs:
        is_stale = False
        reason = ""
        
        # Check if job has no active thread
        if job.id not in running_job_ids:
            is_stale = True
            reason = "no active thread"
        # Check if job has been running too long
        elif job.started_at and job.started_at < stale_threshold:
            is_stale = True
            reason = f"running for {(datetime.utcnow() - job.started_at).total_seconds() / 3600:.1f} hours"
        # Check if thread is dead
        elif not is_job_actually_running(job.id):
            is_stale = True
            reason = "thread terminated"
        
        if is_stale:
            print(f"[cleanup] Found stale running job {job.id} ({reason}), marking as failed")
            job.status = 'failed'
            job.error_message = f'Job was interrupted ({reason})'
            job.updated_at = datetime.utcnow()
            
            # Remove from thread tracking if present
            with running_threads_lock:
                if job.id in running_threads:
                    del running_threads[job.id]
    
    if stale_jobs and any(job.id not in running_job_ids for job in stale_jobs):
        db.commit()


def is_job_actually_running(job_id: int) -> bool:
    """Check if a job has an actively running thread"""
    with running_threads_lock:
        if job_id not in running_threads:
            return False
        thread = running_threads[job_id]
        if not thread.is_alive():
            # Clean up dead thread
            del running_threads[job_id]
            return False
        return True


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
        exclude_sites=job.exclude_sites,
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
    
    # If autostart is enabled and no job is currently running, start immediately
    if job.autostart_enabled and job_status == 'queued':
        # Clean up stale jobs first
        cleanup_stale_running_jobs(db)
        
        running_job = db.query(ScrapeJob).filter(ScrapeJob.status == 'running').first()
        if not running_job or not is_job_actually_running(running_job.id):
            print(f"[create_scrape_job] Autostart enabled and no running job, starting job {db_job.id} immediately")
            # Start the job asynchronously
            def auto_start():
                db_local = SessionLocal()
                start_next_queued_job(db_local, previous_job_autostart=False)
                db_local.close()
            
            thread = threading.Thread(target=auto_start, daemon=True)
            thread.start()
    
    return db_job


@router.get("/current-scrape")
def get_current_scrape(db: Session = Depends(get_db)):
    """Get the currently running scrape job"""
    # Clean up any stale running jobs first
    cleanup_stale_running_jobs(db)
    
    job = db.query(ScrapeJob).filter(ScrapeJob.status == 'running').first()
    
    if not job:
        return {"running": False, "job": None}
    
    # Verify the job is actually running (has an active thread)
    if not is_job_actually_running(job.id):
        # Job is marked as running but thread is dead - clean it up
        job.status = 'failed'
        job.error_message = 'Job thread terminated unexpectedly'
        job.updated_at = datetime.utcnow()
        db.commit()
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
    # First, clean up any stale running jobs
    cleanup_stale_running_jobs(db)
    
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
    
    # Check if there's already a running job (both in DB and actually running)
    running_job = db.query(ScrapeJob).filter(ScrapeJob.status == 'running').first()
    if running_job and is_job_actually_running(running_job.id):
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
        job_min_pages = job.min_pages
        job_max_pages = job.max_pages
        job_min_file_size_mb = job.min_file_size_mb
        job_max_file_size_mb = job.max_file_size_mb
        job_follow_links = job.follow_links
        job_max_depth = job.max_depth
        job_extract_directories = job.extract_directories
        job_skip_duplicates = job.skip_duplicates
        job_equipment_type = job.equipment_type
        job_manufacturer = job.manufacturer
        job_autostart_enabled = job.autostart_enabled
        
        # Parse advanced settings
        sites = None
        if job.sites:
            try:
                sites = json.loads(job.sites)
            except json.JSONDecodeError:
                sites = [s.strip() for s in job.sites.split('\n') if s.strip()]
        
        exclude_sites = None
        if job.exclude_sites:
            try:
                exclude_sites = json.loads(job.exclude_sites)
            except json.JSONDecodeError:
                exclude_sites = [s.strip() for s in job.exclude_sites.split('\n') if s.strip()]
        
        search_terms = None
        if job.search_terms:
            search_terms = [t.strip() for t in job.search_terms.split(',') if t.strip()]
        
        # Add job.query to search_terms if provided (this is the main search query)
        if job.query:
            # Split query into terms and add to search_terms
            query_terms = [term.strip() for term in job.query.split() if term.strip()]
            if search_terms is None:
                search_terms = []
            search_terms.extend(query_terms)
        
        exclude_terms = None
        if job.exclude_terms:
            exclude_terms = [t.strip() for t in job.exclude_terms.split(',') if t.strip()]
        
        file_extensions = None
        if job.file_extensions:
            file_extensions = [e.strip() for e in job.file_extensions.split(',') if e.strip()]
        
        # Run the scraping job in a background thread
        import threading
        def run_job_with_callback():
            # Create a local copy of sites to avoid modifying the outer variable
            job_sites = sites.copy() if sites else None
            
            def log_callback(message):
                # Store log in database and update job progress
                try:
                    db = SessionLocal()
                    # Create log entry
                    log_entry = ScrapeJobLog(
                        job_id=job_id,
                        time=datetime.utcnow(),
                        level="info",
                        message=message
                    )
                    db.add(log_entry)
                    
                    # Update job progress if message contains percentage
                    import re
                    progress_match = re.search(r'(\d+)%', message)
                    if progress_match:
                        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                        if job:
                            job.progress = int(progress_match.group(1))
                            job.updated_at = datetime.utcnow()
                    db.commit()
                    db.close()
                except Exception as e:
                    print(f"Error logging message: {e}")
                    import traceback
                    traceback.print_exc()
            
            try:
                # Log job start
                log_callback(f"Job started: {job_source_type} - {job_query}")
                
                # Choose the appropriate scraper based on source_type
                if job_source_type == 'multi_site':
                    # If no sites provided, use DuckDuckGo to find sites
                    if not job_sites:
                        from app.scrapers.duckduckgo import DuckDuckGoScraper
                        log_callback("Searching DuckDuckGo for sites...")
                        log_callback(f"Query: {job_query}")
                        
                        try:
                            ddg_scraper = DuckDuckGoScraper({'user_agent': settings.user_agent, 'timeout': settings.request_timeout})
                            ddg_results = ddg_scraper.search(job_query, max_results=100)
                            log_callback(f"DuckDuckGo returned {len(ddg_results)} results")
                        except Exception as e:
                            log_callback(f"DuckDuckGo search failed: {e}")
                            import traceback
                            log_callback(f"Error details: {traceback.format_exc()}")
                            raise Exception(f"DuckDuckGo search failed: {e}")
                        
                        # Extract unique domains from DuckDuckGo results
                        unique_domains = set()
                        job_sites = []
                        for result in ddg_results:
                            from urllib.parse import urlparse
                            parsed = urlparse(result.url)
                            domain = parsed.netloc
                            # Skip excluded sites
                            if exclude_sites and any(exc in domain for exc in exclude_sites):
                                log_callback(f"Excluding site: {domain}")
                                continue
                            if domain and domain not in unique_domains:
                                unique_domains.add(domain)
                                # Use the base URL of the site
                                base_url = f"{parsed.scheme}://{domain}"
                                job_sites.append(base_url)
                                log_callback(f"Found site: {base_url}")
                        
                        if not job_sites:
                            log_callback("No sites found from DuckDuckGo search")
                            raise Exception("No sites found from DuckDuckGo search")
                    else:
                        # Filter provided sites against exclude list
                        if exclude_sites:
                            filtered_sites = []
                            for site in job_sites:
                                from urllib.parse import urlparse
                                parsed = urlparse(site)
                                domain = parsed.netloc
                                if not any(exc in domain for exc in exclude_sites):
                                    filtered_sites.append(site)
                                else:
                                    log_callback(f"Excluding site from list: {domain}")
                            job_sites = filtered_sites
                    
                    log_callback(f"Starting multi-site scraping for {len(job_sites)} sites")
                    new_manuals_count = run_multi_site_scraping_job(
                        sites=job_sites,
                        search_terms=search_terms,
                        exclude_terms=exclude_terms,
                        min_pages=job_min_pages,
                        max_pages=job_max_pages,
                        min_file_size_mb=job_min_file_size_mb,
                        max_file_size_mb=job_max_file_size_mb,
                        follow_links=job_follow_links,
                        max_depth=job_max_depth,
                        extract_directories=job_extract_directories,
                        file_extensions=file_extensions,
                        skip_duplicates=job_skip_duplicates,
                        max_results=job_max_results,
                        log_callback=log_callback,
                        job_id=job_id,
                        exclude_sites=exclude_sites
                    )
                else:
                    new_manuals_count = run_search_job(
                        query=job_query,
                        source_type=job_source_type,
                        max_results=job_max_results,
                        equipment_type=job_equipment_type,
                        manufacturer=job_manufacturer,
                        job_id=job_id
                    )
                
                # Log job completion
                if new_manuals_count > 0:
                    log_callback(f"Job completed successfully. Found {new_manuals_count} new manuals.")
                else:
                    log_callback("Job completed but no new manuals were found.")
                
                # Mark job as completed
                db = SessionLocal()
                job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                if job:
                    job.status = 'completed'
                    job.progress = 100
                    job.completed_at = datetime.utcnow()
                    job.updated_at = datetime.utcnow()
                    # Add note about results count
                    if new_manuals_count == 0:
                        job.error_message = "No new manuals found"
                    db.commit()
                    
                    # Remove from thread tracking
                    with running_threads_lock:
                        if job_id in running_threads:
                            del running_threads[job_id]
                    
                    # Check if autostart is enabled and start next job
                    if job_autostart_enabled:
                        print(f"[autostart] Job {job_id} completed with autostart, starting next job...")
                        start_next_queued_job(db, previous_job_autostart=True)
                    db.close()
            except Exception as e:
                # Mark job as failed
                import traceback
                error_msg = f"Error in job thread: {e}"
                print(error_msg)
                traceback.print_exc()
                log_callback(error_msg)
                log_callback(f"Error details: {traceback.format_exc()}")
                
                db = SessionLocal()
                try:
                    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                    if job:
                        job.status = 'failed'
                        job.error_message = str(e)
                        job.updated_at = datetime.utcnow()
                        db.commit()
                        
                        # Remove from thread tracking
                        with running_threads_lock:
                            if job_id in running_threads:
                                del running_threads[job_id]
                        
                        # Still try to continue autostart chain on failure
                        if job_autostart_enabled:
                            print(f"[autostart] Job {job_id} failed but autostart enabled, continuing chain...")
                            start_next_queued_job(db, previous_job_autostart=True)
                except Exception as db_error:
                    print(f"[job_thread] Error updating job status in database: {db_error}")
                    db.rollback()
                finally:
                    db.close()
        
        # Create and track the thread with better exception handling
        def run_job_wrapper():
            try:
                run_job_with_callback()
            except Exception as e:
                # Ensure job is marked as failed even if wrapper catches exception
                print(f"[job_wrapper] Unhandled exception in job thread: {e}")
                import traceback
                traceback.print_exc()
                
                db = SessionLocal()
                try:
                    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                    if job and job.status == 'running':
                        job.status = 'failed'
                        job.error_message = f"Thread crashed: {str(e)}"
                        job.updated_at = datetime.utcnow()
                        db.commit()
                except Exception as db_error:
                    print(f"[job_wrapper] Error updating job status: {db_error}")
                    db.rollback()
                finally:
                    db.close()
                    # Remove from thread tracking
                    with running_threads_lock:
                        if job_id in running_threads:
                            del running_threads[job_id]
        
        thread = threading.Thread(target=run_job_wrapper, daemon=True)
        with running_threads_lock:
            running_threads[job_id] = thread
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


def start_next_queued_job(db: Session, previous_job_autostart: bool = True):
    """Start the next queued job if autostart chain is enabled"""
    try:
        # First, clean up any stale running jobs
        cleanup_stale_running_jobs(db)
        
        # Reposition the queue to ensure position 1 exists
        reposition_queue(db, 0)
        
        # Get the next queued job (position 1 or first by position)
        next_job = db.query(ScrapeJob).filter(
            ScrapeJob.status == 'queued'
        ).order_by(ScrapeJob.queue_position.asc()).first()
        
        if not next_job:
            print("[start_next_queued_job] No queued jobs found")
            return False
        
        print(f"[start_next_queued_job] Found next job: {next_job.name} (id={next_job.id}, queue_position={next_job.queue_position})")
        
        # Update job status
        next_job.status = 'running'
        next_job.queue_position = None
        next_job.progress = 0
        next_job.error_message = None
        next_job.started_at = datetime.utcnow()
        next_job.updated_at = datetime.utcnow()
        db.commit()
        
        # Reposition remaining queue
        reposition_queue(db, 0)
        
        # Store job data for the thread
        job_id = next_job.id
        job_autostart = next_job.autostart_enabled
        job_source_type = next_job.source_type
        job_query = next_job.query
        job_max_results = next_job.max_results
        job_min_pages = next_job.min_pages
        job_max_pages = next_job.max_pages
        job_min_file_size_mb = next_job.min_file_size_mb
        job_max_file_size_mb = next_job.max_file_size_mb
        job_follow_links = next_job.follow_links
        job_max_depth = next_job.max_depth
        job_extract_directories = next_job.extract_directories
        job_skip_duplicates = next_job.skip_duplicates
        job_equipment_type = next_job.equipment_type
        job_manufacturer = next_job.manufacturer
        job_sites_str = next_job.sites
        job_search_terms = next_job.search_terms
        job_exclude_terms = next_job.exclude_terms
        job_file_extensions = next_job.file_extensions
        job_exclude_sites_str = next_job.exclude_sites
        
        # Trigger the actual scraping job
        import threading
        
        # Parse advanced settings
        sites = None
        if job_sites_str:
            try:
                sites = json.loads(job_sites_str)
            except json.JSONDecodeError:
                sites = [s.strip() for s in job_sites_str.split('\n') if s.strip()]
        
        search_terms = None
        if job_search_terms:
            search_terms = [t.strip() for t in job_search_terms.split(',') if t.strip()]
        
        # Add job_query to search_terms if provided (this is the main search query)
        if job_query:
            # Split query into terms and add to search_terms
            query_terms = [term.strip() for term in job_query.split() if term.strip()]
            if search_terms is None:
                search_terms = []
            search_terms.extend(query_terms)
        
        exclude_terms = None
        if job_exclude_terms:
            exclude_terms = [t.strip() for t in job_exclude_terms.split(',') if t.strip()]
        
        file_extensions = None
        if job_file_extensions:
            file_extensions = [e.strip() for e in job_file_extensions.split(',') if e.strip()]
        
        exclude_sites = None
        if job_exclude_sites_str:
            try:
                exclude_sites = json.loads(job_exclude_sites_str)
            except json.JSONDecodeError:
                exclude_sites = [s.strip() for s in job_exclude_sites_str.split('\n') if s.strip()]
        
        def run_job_with_callback():
            # Create a local copy of sites to avoid modifying the outer variable
            job_sites = sites.copy() if sites else None
            
            def log_callback(message):
                try:
                    db_local = SessionLocal()
                    job = db_local.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                    if job:
                        import re
                        progress_match = re.search(r'(\d+)%', message)
                        if progress_match:
                            job.progress = int(progress_match.group(1))
                        
                        # Add log entry
                        log_entry = ScrapeJobLog(
                            job_id=job_id,
                            time=datetime.utcnow(),
                            level="info",
                            message=message
                        )
                        db_local.add(log_entry)
                        job.updated_at = datetime.utcnow()
                        db_local.commit()
                    else:
                        # If job not found, still try to save the log
                        log_entry = ScrapeJobLog(
                            job_id=job_id,
                            time=datetime.utcnow(),
                            level="info",
                            message=message
                        )
                        db_local.add(log_entry)
                        db_local.commit()
                    db_local.close()
                except Exception as e:
                    print(f"Error updating job progress/log: {e}")
                    import traceback
                    traceback.print_exc()
            
            try:
                from app.tasks.jobs import run_search_job, run_multi_site_scraping_job
                
                # Log job start
                log_callback(f"Job started: {job_source_type} - {job_query}")
                
                # Choose the appropriate scraper based on source_type
                if job_source_type == 'multi_site':
                    # If no sites provided, use DuckDuckGo to find sites
                    if not job_sites:
                        from app.scrapers.duckduckgo import DuckDuckGoScraper
                        ddg_scraper = DuckDuckGoScraper({'user_agent': settings.user_agent, 'timeout': settings.request_timeout})
                        log_callback("Searching DuckDuckGo for sites...")
                        ddg_results = ddg_scraper.search(job_query, max_results=100)
                        
                        # Extract unique domains from DuckDuckGo results
                        unique_domains = set()
                        job_sites = []
                        for result in ddg_results:
                            from urllib.parse import urlparse
                            parsed = urlparse(result.url)
                            domain = parsed.netloc
                            # Skip excluded sites
                            if exclude_sites and any(exc in domain for exc in exclude_sites):
                                log_callback(f"Excluding site: {domain}")
                                continue
                            if domain and domain not in unique_domains:
                                unique_domains.add(domain)
                                # Use the base URL of the site
                                base_url = f"{parsed.scheme}://{domain}"
                                job_sites.append(base_url)
                                log_callback(f"Found site: {base_url}")
                        
                        if not job_sites:
                            log_callback("No sites found from DuckDuckGo search")
                            raise Exception("No sites found from DuckDuckGo search")
                    
                    log_callback(f"Starting multi-site scraping for {len(job_sites)} sites")
                    new_manuals_count = run_multi_site_scraping_job(
                        sites=job_sites,
                        search_terms=search_terms,
                        exclude_terms=exclude_terms,
                        min_pages=job_min_pages,
                        max_pages=job_max_pages,
                        min_file_size_mb=job_min_file_size_mb,
                        max_file_size_mb=job_max_file_size_mb,
                        follow_links=job_follow_links,
                        max_depth=job_max_depth,
                        extract_directories=job_extract_directories,
                        file_extensions=file_extensions,
                        skip_duplicates=job_skip_duplicates,
                        max_results=job_max_results,
                        log_callback=log_callback,
                        job_id=job_id,
                        exclude_sites=exclude_sites
                    )
                else:
                    new_manuals_count = run_search_job(
                        query=job_query,
                        source_type=job_source_type,
                        max_results=job_max_results,
                        equipment_type=job_equipment_type,
                        manufacturer=job_manufacturer,
                        job_id=job_id
                    )
                    
                # Log job completion
                if new_manuals_count > 0:
                    log_callback(f"Job completed successfully. Found {new_manuals_count} new manuals.")
                else:
                    log_callback("Job completed but no new manuals were found.")
                
                db_local = SessionLocal()
                job = db_local.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                if job:
                    job.status = 'completed'
                    job.progress = 100
                    job.completed_at = datetime.utcnow()
                    job.updated_at = datetime.utcnow()
                    # Add note about results count
                    if new_manuals_count == 0:
                        job.error_message = "No new manuals found"
                    db_local.commit()
                    
                    # Remove from thread tracking
                    with running_threads_lock:
                        if job_id in running_threads:
                            del running_threads[job_id]
                    
                    # Continue autostart chain if this job has autostart enabled
                    if job.autostart_enabled:
                        print(f"[autostart] Job {job_id} completed with autostart, starting next job...")
                        start_next_queued_job(db_local, previous_job_autostart=True)
                db_local.close()
            except Exception as e:
                import traceback
                error_msg = f"Error in autostart job: {e}"
                print(error_msg)
                traceback.print_exc()
                log_callback(error_msg)
                log_callback(f"Error details: {traceback.format_exc()}")
                db_local = SessionLocal()
                try:
                    job = db_local.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                    if job:
                        job.status = 'failed'
                        job.error_message = str(e)
                        job.updated_at = datetime.utcnow()
                        db_local.commit()
                        
                        # Remove from thread tracking
                        with running_threads_lock:
                            if job_id in running_threads:
                                del running_threads[job_id]
                        
                        # Still try to continue autostart chain
                        if job.autostart_enabled:
                            start_next_queued_job(db_local, previous_job_autostart=True)
                except Exception as db_error:
                    print(f"[autostart_job] Error updating job status in database: {db_error}")
                    db_local.rollback()
                finally:
                    db_local.close()
        
        # Create and track the thread with better exception handling
        def run_job_wrapper():
            try:
                run_job_with_callback()
            except Exception as e:
                # Ensure job is marked as failed even if wrapper catches exception
                print(f"[autostart_wrapper] Unhandled exception in job thread: {e}")
                import traceback
                traceback.print_exc()
                
                db_local = SessionLocal()
                try:
                    job = db_local.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                    if job and job.status == 'running':
                        job.status = 'failed'
                        job.error_message = f"Thread crashed: {str(e)}"
                        job.updated_at = datetime.utcnow()
                        db_local.commit()
                        
                        # Remove from thread tracking
                        with running_threads_lock:
                            if job_id in running_threads:
                                del running_threads[job_id]
                        
                        # Still try to continue autostart chain
                        if job_autostart:
                            start_next_queued_job(db_local, previous_job_autostart=True)
                except Exception as db_error:
                    print(f"[autostart_wrapper] Error updating job status: {db_error}")
                    db_local.rollback()
                finally:
                    db_local.close()
        
        thread = threading.Thread(target=run_job_wrapper, daemon=True)
        with running_threads_lock:
            running_threads[job_id] = thread
        thread.start()
        return True
        
    except Exception as e:
        import traceback
        print(f"Error starting next queued job: {e}")
        traceback.print_exc()
        return False


@router.post("/toggle-autostart")
def toggle_autostart(db: Session = Depends(get_db)):
    """Toggle autostart for all queued jobs"""
    # Get all queued jobs
    queued_jobs = db.query(ScrapeJob).filter(
        ScrapeJob.status == 'queued'
    ).all()
    
    if not queued_jobs:
        # No jobs to toggle - just return current state
        return {
            "autostart_enabled": False,
            "message": "No queued jobs to toggle autostart"
        }
    
    # Get current autostart state from first queued job
    first_job = queued_jobs[0]
    
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
    
    # Stop the actual scraping thread
    with running_threads_lock:
        if job_id in running_threads:
            thread = running_threads[job_id]
            # Note: We can't forcefully stop a thread in Python, but we can:
            # 1. Remove it from tracking so it won't be considered "running"
            # 2. The job will naturally complete or fail, and we'll clean up
            del running_threads[job_id]
            print(f"[stop_job] Removed job {job_id} from active tracking")
    
    # Update job status
    job.status = 'queued'
    job.queue_position = get_queue_position(db)
    job.error_message = 'Job was stopped by user'
    job.updated_at = datetime.utcnow()
    db.commit()
    
    # Add a log entry
    log_entry = ScrapeJobLog(
        job_id=job_id,
        time=datetime.utcnow(),
        level="warning",
        message="Job was stopped by user"
    )
    db.add(log_entry)
    db.commit()
    
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
    
    # Get logs from database
    logs = db.query(ScrapeJobLog).filter(
        ScrapeJobLog.job_id == job_id
    ).order_by(ScrapeJobLog.time.desc()).limit(100).all()
    
    # Convert to JSON-serializable format
    log_list = []
    for log in logs:
        log_list.append({
            "time": log.time.isoformat(),
            "level": log.level,
            "message": log.message
        })
    
    return {"logs": log_list}
    
    return {"logs": logs}


@router.post("/generate-config", response_model=GenerateConfigResponse)
def generate_scrape_config(request: GenerateConfigRequest):
    """Generate scrape configuration using AI (Groq)"""
    from app.processors.config_generator import generate_scrape_config
    
    result = generate_scrape_config(request.prompt)
    
    if not result.get('success', False):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get('error', 'Failed to generate configuration')
        )
    
    # Remove the success key before returning
    result.pop('success', None)
    result.pop('traceback', None)
    
    return GenerateConfigResponse(**result)


@router.post("/{job_id}/clone", response_model=ScrapeJobResponse, status_code=status.HTTP_201_CREATED)
def clone_scrape_job(job_id: int, db: Session = Depends(get_db)):
    """Clone an existing scrape job with all its configuration options"""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape job with ID {job_id} not found"
        )
    
    # Get the next queue position
    queue_pos = get_queue_position(db)
    
    # Create a new job with the same configuration
    new_job = ScrapeJob(
        name=f"{job.name} (Copy)",
        source_type=job.source_type,
        query=job.query,
        max_results=job.max_results,
        status='queued',
        scheduled_time=None,  # Cloned jobs start as queued, not scheduled
        schedule_frequency=job.schedule_frequency,
        equipment_type=job.equipment_type,
        manufacturer=job.manufacturer,
        queue_position=queue_pos,
        autostart_enabled=job.autostart_enabled,
        # Advanced scraping settings - copy all
        sites=job.sites,
        exclude_sites=job.exclude_sites,
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
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    return new_job


@router.get("/{job_id}/full-config")
def get_full_job_config(job_id: int, db: Session = Depends(get_db)):
    """Get the full configuration of a job for cloning/editing purposes"""
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape job with ID {job_id} not found"
        )
    
    return {
        "id": job.id,
        "name": job.name,
        "source_type": job.source_type,
        "query": job.query,
        "max_results": job.max_results,
        "scheduled_time": job.scheduled_time.isoformat() if job.scheduled_time else None,
        "schedule_frequency": job.schedule_frequency,
        "equipment_type": job.equipment_type,
        "manufacturer": job.manufacturer,
        "autostart_enabled": job.autostart_enabled,
        # Advanced scraping settings
        "sites": job.sites,
        "exclude_sites": job.exclude_sites,
        "search_terms": job.search_terms,
        "exclude_terms": job.exclude_terms,
        "min_pages": job.min_pages,
        "max_pages": job.max_pages,
        "min_file_size_mb": job.min_file_size_mb,
        "max_file_size_mb": job.max_file_size_mb,
        "follow_links": job.follow_links,
        "max_depth": job.max_depth,
        "extract_directories": job.extract_directories,
        "file_extensions": job.file_extensions,
        "skip_duplicates": job.skip_duplicates,
        "notes": job.notes,
        "status": job.status,
        "progress": job.progress,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None
    }
