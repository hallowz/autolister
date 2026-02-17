"""
API routes for scrape job queue management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db, ScrapeJob
from app.api.schemas import (
    ScrapeJobCreate, ScrapeJobUpdate, ScrapeJobResponse,
    ScrapeJobListResponse, ScrapeJobStatsResponse,
    GenerateConfigRequest, GenerateConfigResponse
)
from app.config import get_settings
import json

settings = get_settings()

router = APIRouter(prefix="/scrape-jobs", tags=["Scrape Jobs"])


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
        queue_position=queue_pos
    )
    
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    return db_job


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
    
    # Update job status
    job.status = 'running'
    job.queue_position = None
    job.progress = 0
    job.error_message = None
    job.updated_at = datetime.utcnow()
    db.commit()
    
    # TODO: Trigger the actual scraping job
    # This would call the scraping logic from app.tasks.jobs
    
    return {"message": "Scrape job started successfully"}


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


@router.post("/generate-config", response_model=GenerateConfigResponse)
def generate_scrape_config(request: GenerateConfigRequest):
    """Generate scrape configuration using AI (Groq)"""
    try:
        from groq import Groq
        
        # Initialize Groq client
        client = Groq(api_key=settings.groq_api_key)
        
        # Create prompt for Groq
        system_prompt = """You are an expert at configuring web scraping jobs. 
Given a user's description, generate a scrape job configuration with the following fields:
- name: A short, descriptive name for the job
- source_type: One of: 'search', 'forum', 'manual_site', 'gdrive'
- query: The search query to use (include relevant search operators like filetype:pdf)
- max_results: Number of results to fetch (typically 10-50)
- equipment_type: Optional - the type of equipment (e.g., Camera, Radio, etc.)
- manufacturer: Optional - the manufacturer name (e.g., Canon, Nikon, etc.)

Return ONLY valid JSON, no other text."""
        
        user_prompt = f"Generate a scrape job configuration for: {request.prompt}"
        
        # Call Groq API
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        config_json = completion.choices[0].message.content
        config = json.loads(config_json)
        
        # Validate and set defaults
        config.setdefault('name', 'Generated Scrape Job')
        config.setdefault('source_type', 'search')
        config.setdefault('query', request.prompt[:200])
        config.setdefault('max_results', 10)
        config.setdefault('equipment_type', None)
        config.setdefault('manufacturer', None)
        
        return GenerateConfigResponse(**config)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate configuration: {str(e)}"
        )
