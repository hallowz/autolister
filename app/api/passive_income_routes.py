"""
FastAPI routes for Passive Income Dashboard
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json

from app.database import get_db, Manual, ScrapeJob
from app.passive_income.database import (
    Platform, PlatformListing, ActionQueue, Revenue, Setting,
    PassiveIncomeManager, create_passive_income_tables, init_default_platforms,
    NicheDiscovery, MarketResearch, AutoScrapingState
)
from app.passive_income.agent import AutonomousAgent
from app.passive_income.auto_scraping_agent import AutoScrapingAgent
from app.passive_income.platforms import PlatformRegistry

router = APIRouter(prefix="/api/passive-income", tags=["Passive Income"])


# ============ Platform Endpoints ============

@router.get("/platforms")
def get_platforms(db: Session = Depends(get_db)):
    """Get all platforms with status"""
    platforms = db.query(Platform).all()
    
    result = []
    for p in platforms:
        result.append({
            'id': p.id,
            'name': p.name,
            'display_name': p.display_name,
            'platform_type': p.platform_type,
            'is_active': p.is_active,
            'is_free': p.is_free,
            'supports_api_listing': p.supports_api_listing,
            'supports_digital_downloads': p.supports_digital_downloads,
            'credentials_status': p.credentials_status,
            'listing_count': p.listing_count,
            'total_revenue': p.total_revenue,
            'sync_status': p.sync_status,
            'last_sync': p.last_sync.isoformat() if p.last_sync else None,
            'sync_error': p.sync_error
        })
    
    return result


@router.post("/platforms/{platform_id}/configure")
def configure_platform(platform_id: int, credentials: dict, db: Session = Depends(get_db)):
    """Configure platform credentials"""
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    # Register platforms if not done
    from app.passive_income.platforms.registry import auto_register_platforms
    auto_register_platforms()
    
    # Store credentials (in production, encrypt these!)
    platform.credentials = json.dumps(credentials)
    platform.credentials_status = 'pending'
    db.commit()
    
    # Verify credentials
    from app.passive_income.platforms import PlatformRegistry
    platform_client = PlatformRegistry.get(platform.name, credentials=credentials)
    
    if platform_client:
        status_result = platform_client.check_status()
        if status_result.is_connected:
            platform.credentials_status = 'verified'
            platform.sync_error = None
        else:
            platform.credentials_status = 'error'
            platform.sync_error = status_result.error or 'Connection failed'
        db.commit()
    else:
        platform.credentials_status = 'error'
        platform.sync_error = f"Platform {platform.name} not registered"
        db.commit()
    
    return {
        'message': 'Credentials configured',
        'status': platform.credentials_status,
        'error': platform.sync_error
    }


@router.post("/platforms/{platform_id}/activate")
def activate_platform(platform_id: int, db: Session = Depends(get_db)):
    """Activate a platform"""
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    platform.is_active = True
    db.commit()
    
    return {'message': f'{platform.display_name} activated'}


@router.post("/platforms/{platform_id}/deactivate")
def deactivate_platform(platform_id: int, db: Session = Depends(get_db)):
    """Deactivate a platform"""
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    platform.is_active = False
    db.commit()
    
    return {'message': f'{platform.display_name} deactivated'}


@router.post("/platforms/{platform_id}/sync")
def sync_platform(platform_id: int, db: Session = Depends(get_db)):
    """Manually sync platform data"""
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    # Check if credentials are configured
    if platform.credentials_status != 'verified':
        raise HTTPException(status_code=400, detail="Platform credentials not verified")
    
    # Register platforms if not done
    from app.passive_income.platforms.registry import auto_register_platforms
    auto_register_platforms()
    
    agent = AutonomousAgent(db)
    
    try:
        agent._sync_platform_sales(platform)
        return {'message': 'Sync completed', 'last_sync': platform.last_sync.isoformat() if platform.last_sync else None}
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


# ============ Dashboard Stats ============

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    manager = PassiveIncomeManager(db)
    
    return {
        'platforms': manager.get_platform_stats(),
        'pending_actions': manager.get_action_count(),
        'revenue': manager.get_revenue_summary(days=30)
    }


@router.get("/revenue")
def get_revenue(days: int = 30, db: Session = Depends(get_db)):
    """Get revenue data"""
    manager = PassiveIncomeManager(db)
    return manager.get_revenue_summary(days=days)


# ============ Action Queue ============

@router.get("/actions")
def get_pending_actions(limit: int = 50, db: Session = Depends(get_db)):
    """Get pending actions requiring human intervention"""
    actions = db.query(ActionQueue).filter(
        ActionQueue.status == 'pending'
    ).order_by(
        ActionQueue.priority.asc(),
        ActionQueue.created_at.asc()
    ).limit(limit).all()
    
    return [{
        'id': a.id,
        'action_type': a.action_type,
        'priority': a.priority,
        'title': a.title,
        'description': a.description,
        'prompt': a.prompt,
        'input_type': a.input_type,
        'input_options': json.loads(a.input_options) if a.input_options else None,
        'created_at': a.created_at.isoformat(),
        'expires_at': a.expires_at.isoformat() if a.expires_at else None,
        'platform_id': a.platform_id,
        'listing_id': a.listing_id
    } for a in actions]


@router.post("/actions/{action_id}/resolve")
def resolve_action(action_id: int, response: dict, db: Session = Depends(get_db)):
    """Resolve an action with user response"""
    action = db.query(ActionQueue).filter(ActionQueue.id == action_id).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    action.user_response = response.get('response')
    action.responded_at = datetime.utcnow()
    action.status = 'completed'
    db.commit()
    
    # Process the response and resume work
    # Use AutoScrapingAgent for niche-related prompts, AutonomousAgent for others
    if action.action_type in ['new_niche_prompt', 'refine_config_prompt']:
        agent = AutoScrapingAgent(db)
    else:
        agent = AutonomousAgent(db)
    
    agent.process_action_response(action_id, response.get('response'))
    
    return {'message': 'Action resolved', 'action_id': action_id}


@router.post("/actions/{action_id}/cancel")
def cancel_action(action_id: int, db: Session = Depends(get_db)):
    """Cancel a pending action"""
    action = db.query(ActionQueue).filter(ActionQueue.id == action_id).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    action.status = 'cancelled'
    db.commit()
    
    return {'message': 'Action cancelled'}


# ============ Listings ============

@router.get("/listings")
def get_listings(
    status: str = None,
    platform_id: int = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get platform listings"""
    query = db.query(PlatformListing)
    
    if status:
        query = query.filter(PlatformListing.status == status)
    
    if platform_id:
        query = query.filter(PlatformListing.platform_id == platform_id)
    
    listings = query.order_by(PlatformListing.created_at.desc()).limit(limit).all()
    
    return [{
        'id': l.id,
        'manual_id': l.manual_id,
        'platform_id': l.platform_id,
        'title': l.title,
        'seo_title': l.seo_title,
        'price': l.price,
        'status': l.status,
        'platform_url': l.platform_url,
        'views': l.views,
        'sales': l.sales,
        'revenue': l.revenue,
        'created_at': l.created_at.isoformat(),
        'listed_at': l.listed_at.isoformat() if l.listed_at else None,
        'error_message': l.error_message
    } for l in listings]


@router.post("/listings/{listing_id}/retry")
def retry_listing(listing_id: int, db: Session = Depends(get_db)):
    """Retry a failed listing"""
    listing = db.query(PlatformListing).filter(PlatformListing.id == listing_id).first()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing.status not in ['error', 'action_required']:
        raise HTTPException(status_code=400, detail="Can only retry failed listings")
    
    listing.status = 'pending'
    listing.retry_count += 1
    listing.last_retry = datetime.utcnow()
    db.commit()
    
    # Try to list again
    agent = AutonomousAgent(db)
    platform = db.query(Platform).get(listing.platform_id)
    manual = db.query(Manual).get(listing.manual_id)
    
    if manual and platform:
        agent._create_platform_listing(manual, platform)
    
    return {'message': 'Retry initiated', 'listing_id': listing_id}


# ============ Agent Control ============

@router.post("/agent/run")
def run_agent():
    """Manually trigger agent cycle"""
    agent = AutonomousAgent()
    
    try:
        agent.run_cycle()
        return {'message': 'Agent cycle completed'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Settings ============

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Get all passive income settings"""
    settings = db.query(Setting).all()
    
    return {s.key: s.value for s in settings}


@router.post("/settings")
def update_setting(key: str, value: str, db: Session = Depends(get_db)):
    """Update a setting"""
    setting = db.query(Setting).filter(Setting.key == key).first()
    
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    
    db.commit()
    
    return {'message': 'Setting updated', 'key': key}


# ============ Initialization ============

@router.post("/initialize")
def initialize_passive_income(db: Session = Depends(get_db)):
    """Initialize passive income tables and default data"""
    try:
        create_passive_income_tables()
        init_default_platforms()
        return {'message': 'Passive income system initialized'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Auto-Scraping Endpoints ============

@router.get("/auto-scraping/status")
def get_auto_scraping_status(db: Session = Depends(get_db)):
    """Get the current status of the auto-scraping agent"""
    
    # Get or create state
    state = db.query(AutoScrapingState).first()
    if not state:
        state = AutoScrapingState()
        db.add(state)
        db.commit()
        db.refresh(state)
    
    # Count pending manuals
    pending_count = db.query(Manual).filter(
        Manual.status == 'pending'
    ).count()
    
    # Count approved manuals waiting to be processed
    approved_count = db.query(Manual).filter(
        Manual.status == 'approved',
        Manual.pdf_path == None
    ).count()
    
    # Count running jobs
    running_jobs = db.query(ScrapeJob).filter(
        ScrapeJob.status == 'running'
    ).count()
    
    # Get available niches count
    available_niches = db.query(NicheDiscovery).filter(
        NicheDiscovery.status == 'discovered',
        NicheDiscovery.scrape_job_id == None
    ).count()
    
    # Get recent niche discoveries
    niches = db.query(NicheDiscovery).order_by(NicheDiscovery.created_at.desc()).limit(10).all()
    
    # Get recent market research
    research = db.query(MarketResearch).order_by(MarketResearch.created_at.desc()).limit(10).all()
    
    return {
        'enabled': state.is_enabled,
        'current_phase': state.current_phase,
        'current_job_id': state.current_job_id,
        'last_cycle': state.last_cycle_at.isoformat() if state.last_cycle_at else None,
        'next_cycle': state.next_cycle_at.isoformat() if state.next_cycle_at else None,
        'cycle_count': state.cycle_count,
        'total_niches_discovered': state.total_niches_discovered,
        'total_manuals_evaluated': state.total_manuals_evaluated,
        'total_manuals_listed': state.total_manuals_listed,
        'error_count': state.error_count,
        'last_error': state.last_error,
        # New fields for better visibility
        'pending_manuals': pending_count,
        'approved_manuals': approved_count,
        'running_jobs': running_jobs,
        'available_niches': available_niches,
        'niches': [{
            'id': n.id,
            'niche': n.niche,
            'description': n.description,
            'demand_level': n.demand_level,
            'competition_level': n.competition_level,
            'potential_price': n.potential_price,
            'status': n.status,
            'manuals_found': n.manuals_found,
            'manuals_listed': n.manuals_listed,
            'revenue_generated': n.revenue_generated,
            'created_at': n.created_at.isoformat()
        } for n in niches],
        'recent_research': [{
            'id': r.id,
            'manual_id': r.manual_id,
            'is_suitable': r.is_suitable,
            'confidence_score': r.confidence_score,
            'suggested_price': r.suggested_price,
            'seo_title': r.seo_title,
            'created_at': r.created_at.isoformat()
        } for r in research]
    }


@router.post("/auto-scraping/enable")
def enable_auto_scraping(db: Session = Depends(get_db)):
    """Enable the auto-scraping agent"""
    agent = AutoScrapingAgent(db)
    agent.enable()
    
    # Update state
    state = db.query(AutoScrapingState).first()
    if not state:
        state = AutoScrapingState(is_enabled=True)
        db.add(state)
    else:
        state.is_enabled = True
    db.commit()
    
    # Run a cycle immediately when enabled
    try:
        results = agent.run_cycle()
        return {
            'message': 'Auto-scraping enabled',
            'enabled': True,
            'cycle_results': results
        }
    except Exception as e:
        return {
            'message': 'Auto-scraping enabled but cycle failed',
            'enabled': True,
            'error': str(e)
        }


@router.post("/auto-scraping/disable")
def disable_auto_scraping(db: Session = Depends(get_db)):
    """Disable the auto-scraping agent"""
    agent = AutoScrapingAgent(db)
    agent.disable()
    
    # Update state
    state = db.query(AutoScrapingState).first()
    if state:
        state.is_enabled = False
        db.commit()
    
    return {'message': 'Auto-scraping disabled', 'enabled': False}


@router.post("/auto-scraping/run-cycle")
def run_auto_scraping_cycle(db: Session = Depends(get_db)):
    """Manually trigger an auto-scraping cycle"""
    import traceback
    
    agent = AutoScrapingAgent(db)
    
    try:
        # Run the cycle and get detailed results
        results = agent.run_cycle()
        
        return {
            'message': 'Cycle completed',
            'status': results.get('status'),
            'actions_taken': results.get('actions_taken', []),
            'manuals_evaluated': results.get('manuals_evaluated', 0),
            'manuals_processed': results.get('manuals_processed', 0),
            'jobs_created': results.get('jobs_created', 0),
            'niches_discovered': results.get('niches_discovered', 0),
            'running_jobs': results.get('running_jobs', 0),
            'error': results.get('error')
        }
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{tb}")


@router.post("/auto-scraping/discover-niches")
def discover_niches(db: Session = Depends(get_db)):
    """Trigger AI niche discovery"""
    agent = AutoScrapingAgent(db)
    
    try:
        # Agent already stores niches in database
        niches = agent.discover_niches()
        
        # Update state
        state = db.query(AutoScrapingState).first()
        if state:
            state.total_niches_discovered = (state.total_niches_discovered or 0) + len(niches)
        db.commit()
        
        return {
            'message': f'Discovered {len(niches)} niches',
            'niches': niches
        }
        
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.get("/auto-scraping/niches")
def get_discovered_niches(
    status: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get discovered niches"""
    query = db.query(NicheDiscovery)
    
    if status:
        query = query.filter(NicheDiscovery.status == status)
    
    niches = query.order_by(NicheDiscovery.created_at.desc()).limit(limit).all()
    
    return [{
        'id': n.id,
        'niche': n.niche,
        'description': n.description,
        'search_query': n.search_query,
        'potential_price': n.potential_price,
        'demand_level': n.demand_level,
        'competition_level': n.competition_level,
        'keywords': json.loads(n.keywords) if n.keywords else [],
        'sites_to_search': json.loads(n.sites_to_search) if n.sites_to_search else [],
        'reason': n.reason,
        'status': n.status,
        'scrape_job_id': n.scrape_job_id,
        'manuals_found': n.manuals_found,
        'manuals_listed': n.manuals_listed,
        'revenue_generated': n.revenue_generated,
        'created_at': n.created_at.isoformat(),
        'last_scraped_at': n.last_scraped_at.isoformat() if n.last_scraped_at else None
    } for n in niches]


@router.post("/auto-scraping/niches/{niche_id}/create-job")
def create_job_for_niche(niche_id: int, db: Session = Depends(get_db)):
    """Create a scrape job for a specific niche"""
    
    niche = db.query(NicheDiscovery).filter(NicheDiscovery.id == niche_id).first()
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    
    if niche.status not in ['discovered', 'job_created']:
        raise HTTPException(status_code=400, detail=f"Niche is in status '{niche.status}'")
    
    # Get next queue position
    highest_position = db.query(ScrapeJob.queue_position).filter(
        ScrapeJob.queue_position.isnot(None),
        ScrapeJob.status == 'queued'
    ).order_by(ScrapeJob.queue_position.desc()).first()
    
    queue_position = (highest_position[0] + 1) if highest_position else 1
    
    # Create scrape job
    keywords = json.loads(niche.keywords) if niche.keywords else []
    sites = json.loads(niche.sites_to_search) if niche.sites_to_search else []
    
    job = ScrapeJob(
        name=f"Auto: {niche.niche}",
        source_type='multi_site',
        query=niche.search_query or niche.niche,
        search_terms=','.join([niche.niche] + keywords[:5]) if keywords else niche.niche,
        exclude_terms='preview,operator,user manual,quick start,brochure,catalog',
        sites=json.dumps(sites) if sites else None,
        max_results=100,
        equipment_type=niche.niche.split()[0] if niche.niche else None,
        autostart_enabled=True,
        status='queued',
        queue_position=queue_position
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Update niche
    niche.scrape_job_id = job.id
    niche.status = 'job_created'
    db.commit()
    
    # Trigger the job to start - try Celery first, then fallback to sync
    try:
        from app.tasks.jobs import check_queue
        try:
            # Try async Celery first
            check_queue.delay()
        except Exception as celery_error:
            # Fallback to synchronous execution if Celery is not available
            print(f"[create_job_for_niche] Celery not available ({celery_error}), running synchronously")
            import threading
            # Run in a separate thread to avoid blocking
            def run_check_queue():
                from app.database import SessionLocal
                db = SessionLocal()
                try:
                    from app.tasks.jobs import check_queue as check_queue_func
                    # Run the actual function, not the Celery task
                    check_queue_func()
                except Exception as e:
                    print(f"[job_thread] Error: {e}")
                finally:
                    db.close()
            thread = threading.Thread(target=run_check_queue, daemon=True)
            thread.start()
    except Exception as e:
        print(f"[create_job_for_niche] Warning: Could not trigger check_queue: {e}")
    
    return {
        'message': f'Created scrape job for {niche.niche}',
        'job_id': job.id,
        'niche_id': niche_id
    }


@router.get("/market-research/{manual_id}")
def get_market_research(manual_id: int, db: Session = Depends(get_db)):
    """Get market research for a specific manual"""
    research = db.query(MarketResearch).filter(
        MarketResearch.manual_id == manual_id
    ).first()
    
    if not research:
        raise HTTPException(status_code=404, detail="Market research not found")
    
    return {
        'id': research.id,
        'manual_id': research.manual_id,
        'search_query': research.search_query,
        'similar_listings': json.loads(research.similar_listings) if research.similar_listings else [],
        'competitor_prices': json.loads(research.competitor_prices) if research.competitor_prices else [],
        'average_price': research.average_price,
        'price_range_low': research.price_range_low,
        'price_range_high': research.price_range_high,
        'demand_score': research.demand_score,
        'competition_score': research.competition_score,
        'profitability_score': research.profitability_score,
        'ai_evaluation': json.loads(research.ai_evaluation) if research.ai_evaluation else {},
        'is_suitable': research.is_suitable,
        'confidence_score': research.confidence_score,
        'suggested_price': research.suggested_price,
        'seo_title': research.seo_title,
        'target_audience': research.target_audience,
        'concerns': json.loads(research.concerns) if research.concerns else [],
        'created_at': research.created_at.isoformat()
    }


@router.post("/market-research/{manual_id}/evaluate")
def evaluate_manual(manual_id: int, db: Session = Depends(get_db)):
    """Trigger AI evaluation for a specific manual"""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")
    
    agent = AutoScrapingAgent(db)
    
    try:
        evaluation = agent._evaluate_manual(manual)
        
        # Create or update market research
        research = db.query(MarketResearch).filter(
            MarketResearch.manual_id == manual_id
        ).first()
        
        if not research:
            research = MarketResearch(manual_id=manual_id)
            db.add(research)
        
        research.ai_evaluation = json.dumps(evaluation)
        research.is_suitable = evaluation.get('suitable', True)
        research.confidence_score = evaluation.get('confidence', 0.5)
        research.suggested_price = evaluation.get('suggested_price', 4.99)
        research.seo_title = evaluation.get('seo_title', manual.title)
        research.target_audience = evaluation.get('target_audience', '')
        research.concerns = json.dumps(evaluation.get('concerns', []))
        research.market_analysis = json.dumps(evaluation.get('market_analysis', {}))
        
        db.commit()
        
        return {
            'message': 'Evaluation completed',
            'evaluation': evaluation
        }
        
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


# ============ Manual Management Endpoints ============

@router.get("/manuals")
def get_manuals(
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all manuals with market research data"""
    from app.passive_income.database import MarketResearch
    
    query = db.query(Manual)
    
    if status:
        query = query.filter(Manual.status == status)
    
    manuals = query.order_by(Manual.created_at.desc()).limit(limit).all()
    
    # Get statistics
    stats = {
        'pending': db.query(Manual).filter(Manual.status == 'pending').count(),
        'approved': db.query(Manual).filter(Manual.status == 'approved').count(),
        'rejected': db.query(Manual).filter(Manual.status == 'rejected').count(),
        'processing': db.query(Manual).filter(Manual.status == 'processing').count(),
        'processed': db.query(Manual).filter(Manual.status == 'processed').count(),
        'queued': db.query(Manual).filter(Manual.queue_position.isnot(None)).count()
    }
    
    # Get market research for each manual
    result = []
    for manual in manuals:
        research = db.query(MarketResearch).filter(
            MarketResearch.manual_id == manual.id
        ).first()
        
        manual_data = {
            'id': manual.id,
            'title': manual.title,
            'manufacturer': manual.manufacturer,
            'model': manual.model,
            'year': manual.year,
            'source_type': manual.source_type,
            'source_url': manual.source_url,
            'status': manual.status,
            'pdf_path': manual.pdf_path,
            'queue_position': manual.queue_position,
            'created_at': manual.created_at.isoformat() if manual.created_at else None,
            'market_research': {
                'is_suitable': research.is_suitable if research else None,
                'confidence_score': research.confidence_score if research else None,
                'suggested_price': research.suggested_price if research else None,
                'demand_score': research.demand_score if research else None,
                'competition_score': research.competition_score if research else None,
                'profitability_score': research.profitability_score if research else None,
                'ai_evaluation': research.ai_evaluation if research else None
            } if research else None
        }
        
        # Add top-level fields for easier access
        if research:
            manual_data['is_suitable'] = research.is_suitable
            manual_data['confidence_score'] = research.confidence_score
            manual_data['suggested_price'] = research.suggested_price
        
        result.append(manual_data)
    
    return {
        'manuals': result,
        'stats': stats
    }


@router.get("/manuals/{manual_id}")
def get_manual_detail(manual_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific manual"""
    from app.passive_income.database import MarketResearch
    
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")
    
    research = db.query(MarketResearch).filter(
        MarketResearch.manual_id == manual_id
    ).first()
    
    result = {
        'id': manual.id,
        'title': manual.title,
        'manufacturer': manual.manufacturer,
        'model': manual.model,
        'year': manual.year,
        'source_type': manual.source_type,
        'source_url': manual.source_url,
        'status': manual.status,
        'pdf_path': manual.pdf_path,
        'description': manual.description,
        'tags': manual.tags,
        'queue_position': manual.queue_position,
        'processing_state': manual.processing_state,
        'processing_started_at': manual.processing_started_at.isoformat() if manual.processing_started_at else None,
        'processing_completed_at': manual.processing_completed_at.isoformat() if manual.processing_completed_at else None,
        'created_at': manual.created_at.isoformat() if manual.created_at else None,
        'updated_at': manual.updated_at.isoformat() if manual.updated_at else None,
        'error_message': manual.error_message
    }
    
    if research:
        result['market_research'] = {
            'id': research.id,
            'is_suitable': research.is_suitable,
            'confidence_score': research.confidence_score,
            'suggested_price': research.suggested_price,
            'demand_score': research.demand_score,
            'competition_score': research.competition_score,
            'profitability_score': research.profitability_score,
            'seo_title': research.seo_title,
            'target_audience': research.target_audience,
            'concerns': research.concerns,
            'ai_evaluation': research.ai_evaluation,
            'created_at': research.created_at.isoformat() if research.created_at else None
        }
    
    return result


@router.post("/manuals/{manual_id}/approve")
def approve_manual(manual_id: int, db: Session = Depends(get_db)):
    """Manually approve a manual for listing"""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")
    
    manual.status = 'approved'
    manual.updated_at = datetime.utcnow()
    db.commit()
    
    return {'message': f'Manual {manual_id} approved successfully'}


@router.post("/manuals/{manual_id}/reject")
def reject_manual(manual_id: int, db: Session = Depends(get_db)):
    """Manually reject a manual"""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")
    
    manual.status = 'rejected'
    manual.updated_at = datetime.utcnow()
    db.commit()
    
    return {'message': f'Manual {manual_id} rejected successfully'}


@router.post("/manuals/{manual_id}/evaluate")
def evaluate_manual(manual_id: int, db: Session = Depends(get_db)):
    """Evaluate a single manual with AI"""
    from app.passive_income.auto_scraping_agent import AutoScrapingAgent
    
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")
    
    agent = AutoScrapingAgent(db)
    
    try:
        evaluation_result = agent._evaluate_manual_with_ai(manual)
        
        if evaluation_result:
            from app.passive_income.database import MarketResearch
            import json
            
            research = db.query(MarketResearch).filter(
                MarketResearch.manual_id == manual_id
            ).first()
            
            if not research:
                research = MarketResearch(manual_id=manual_id)
                db.add(research)
            
            research.ai_evaluation = json.dumps(evaluation_result)
            research.is_suitable = evaluation_result.get('suitable', False)
            research.confidence_score = evaluation_result.get('confidence', 0.0)
            research.suggested_price = evaluation_result.get('suggested_price', 4.99)
            
            # Update manual status based on evaluation
            if evaluation_result.get('suitable'):
                manual.status = 'approved'
            else:
                manual.status = 'rejected'
            
            db.commit()
            
            return {
                'message': f'Manual {manual_id} evaluated successfully',
                'suitable': evaluation_result.get('suitable'),
                'confidence': evaluation_result.get('confidence'),
                'reason': evaluation_result.get('reason')
            }
        else:
            raise HTTPException(status_code=500, detail="Evaluation failed")
            
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.post("/manuals/evaluate-pending")
def evaluate_pending_manuals(db: Session = Depends(get_db)):
    """Evaluate all pending manuals with AI"""
    from app.passive_income.auto_scraping_agent import AutoScrapingAgent
    
    agent = AutoScrapingAgent(db)
    
    try:
        evaluated_count = agent._evaluate_pending_manuals(limit=50)
        
        return {
            'message': f'Evaluated {evaluated_count} pending manuals',
            'evaluated_count': evaluated_count
        }
        
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.post("/manuals/{manual_id}/move-to-queue")
def move_manual_to_queue(manual_id: int, db: Session = Depends(get_db)):
    """Move an approved manual to the processing queue"""
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")
    
    if manual.status != 'approved':
        raise HTTPException(status_code=400, detail="Only approved manuals can be moved to queue")
    
    # Get the next available queue position
    from app.api.scrape_routes import get_queue_position
    queue_pos = get_queue_position(db)
    
    # Update manual status and queue position
    manual.status = 'queued'
    manual.queue_position = queue_pos
    manual.processing_state = 'queued'
    manual.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        'message': f'Manual {manual_id} moved to queue at position {queue_pos}',
        'queue_position': queue_pos
    }


@router.post("/manuals/move-approved-to-queue")
def move_all_approved_to_queue(db: Session = Depends(get_db)):
    """Move all approved manuals to the processing queue"""
    from app.api.scrape_routes import get_queue_position, reposition_queue
    
    # Get all approved manuals
    approved_manuals = db.query(Manual).filter(
        Manual.status == 'approved'
    ).all()
    
    if not approved_manuals:
        return {'message': 'No approved manuals to move', 'moved_count': 0}
    
    moved_count = 0
    start_position = get_queue_position(db)
    
    for i, manual in enumerate(approved_manuals):
        manual.status = 'queued'
        manual.queue_position = start_position + i
        manual.processing_state = 'queued'
        manual.updated_at = datetime.utcnow()
        moved_count += 1
    
    db.commit()
    
    return {
        'message': f'Moved {moved_count} approved manuals to queue',
        'moved_count': moved_count,
        'start_position': start_position
    }


# ============ Auto-Scraping Logs ============

@router.get("/auto-scraping/logs")
def get_auto_scraping_logs(
    limit: int = 100,
    agent_id: str = 'auto_scraping',
    db: Session = Depends(get_db)
):
    """Get recent auto-scraping agent logs"""
    from app.passive_income.database import AgentLog
    
    logs = db.query(AgentLog).filter(
        AgentLog.agent_id == agent_id
    ).order_by(AgentLog.created_at.desc()).limit(limit).all()
    
    return [{
        'id': l.id,
        'agent_id': l.agent_id,
        'action': l.action,
        'status': l.status,
        'message': l.message,
        'data': json.loads(l.data) if l.data else None,
        'created_at': l.created_at.isoformat()
    } for l in logs]
