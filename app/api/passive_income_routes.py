"""
FastAPI routes for Passive Income Dashboard
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json

from app.database import get_db
from app.passive_income.database import (
    Platform, PlatformListing, ActionQueue, Revenue, Setting,
    PassiveIncomeManager, create_passive_income_tables, init_default_platforms
)
from app.passive_income.agent import AutonomousAgent
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


# Add Manual import
from app.database import Manual
