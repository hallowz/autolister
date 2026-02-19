"""
Database models for Passive Income Dashboard
Extends the main database with models for multi-platform listing, 
action queue, revenue tracking, and platform management.
"""
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from app.database import Base, engine, SessionLocal


class Platform(Base):
    """
    Platform model for tracking listing platforms (Etsy, Gumroad, Payhip, eBay, etc.)
    """
    __tablename__ = "platforms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # 'etsy', 'gumroad', 'payhip', 'ebay'
    display_name = Column(String, nullable=False)  # 'Etsy', 'Gumroad', 'Payhip', 'eBay'
    platform_type = Column(String, nullable=False)  # 'digital_download', 'dropshipping', 'marketplace'
    api_base_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_free = Column(Boolean, default=True)  # No upfront costs
    supports_api_listing = Column(Boolean, default=False)
    supports_digital_downloads = Column(Boolean, default=True)
    requires_verification = Column(Boolean, default=False)
    credentials = Column(Text, nullable=True)  # JSON encrypted credentials
    credentials_status = Column(String, default='not_configured')  # 'not_configured', 'pending', 'verified', 'error'
    listing_count = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    last_sync = Column(DateTime, nullable=True)
    sync_status = Column(String, default='never_synced')  # 'never_synced', 'syncing', 'synced', 'error'
    sync_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    listings = relationship("PlatformListing", back_populates="platform")
    actions = relationship("ActionQueue", back_populates="platform")


class PlatformListing(Base):
    """
    Tracks listings across multiple platforms for a single manual/product
    """
    __tablename__ = "platform_listings"
    
    id = Column(Integer, primary_key=True, index=True)
    manual_id = Column(Integer, ForeignKey("manuals.id"), nullable=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    
    # Platform-specific IDs
    platform_listing_id = Column(String, nullable=True)  # External platform's listing ID
    platform_url = Column(String, nullable=True)  # URL to the listing on the platform
    
    # Listing content (can be platform-specific)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)  # For discounts
    currency = Column(String, default='USD')
    
    # SEO and metadata
    seo_title = Column(String, nullable=True)
    seo_keywords = Column(Text, nullable=True)  # Comma-separated
    tags = Column(Text, nullable=True)  # JSON array
    
    # Status tracking
    status = Column(String, default='pending')  # 'pending', 'listed', 'active', 'sold', 'expired', 'error'
    listing_type = Column(String, default='digital')  # 'digital', 'physical', 'dropship'
    
    # Analytics
    views = Column(Integer, default=0)
    favorites = Column(Integer, default=0)
    sales = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    last_retry = Column(DateTime, nullable=True)
    
    # Scheduling
    scheduled_list_at = Column(DateTime, nullable=True)
    listed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    platform = relationship("Platform", back_populates="listings")
    manual = relationship("Manual", backref="platform_listings")
    revenue_records = relationship("Revenue", back_populates="listing")


class ActionQueue(Base):
    """
    Queue for actions requiring human intervention
    When the autonomous agent encounters something it can't do automatically,
    it adds an action here for the user to handle via the dashboard.
    """
    __tablename__ = "action_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=True)
    listing_id = Column(Integer, ForeignKey("platform_listings.id"), nullable=True)
    manual_id = Column(Integer, ForeignKey("manuals.id"), nullable=True)
    
    # Action details
    action_type = Column(String, nullable=False)  # 'account_setup', 'verification', 'captcha', 'manual_listing', 'price_adjustment', etc.
    priority = Column(Integer, default=5)  # 1-10, 1 being highest
    status = Column(String, default='pending')  # 'pending', 'in_progress', 'completed', 'cancelled', 'expired'
    
    # Description and prompt
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    prompt = Column(Text, nullable=True)  # What to ask the user
    input_type = Column(String, default='text')  # 'text', 'url', 'file', 'selection', 'confirmation'
    input_options = Column(Text, nullable=True)  # JSON for selection options
    
    # User response
    user_response = Column(Text, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    
    # Context data (for the agent to resume work)
    context = Column(Text, nullable=True)  # JSON with context for resuming
    
    # Retry and expiry
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    platform = relationship("Platform", back_populates="actions")


class Revenue(Base):
    """
    Revenue tracking for all platforms
    """
    __tablename__ = "revenue"
    
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("platform_listings.id"), nullable=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    
    # Transaction details
    transaction_id = Column(String, nullable=True)  # Platform's transaction ID
    transaction_type = Column(String, default='sale')  # 'sale', 'refund', 'fee', 'payout'
    amount = Column(Float, nullable=False)
    currency = Column(String, default='USD')
    fee = Column(Float, default=0.0)
    net_amount = Column(Float, nullable=False)
    
    # Metadata
    buyer_info = Column(Text, nullable=True)  # JSON (anonymized)
    product_info = Column(Text, nullable=True)  # JSON
    
    transaction_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    listing = relationship("PlatformListing", back_populates="revenue_records")
    platform = relationship("Platform", backref="revenue_records")


class Setting(Base):
    """
    General settings for the passive income system
    """
    __tablename__ = "passive_income_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, nullable=False, unique=True)
    value = Column(Text, nullable=True)
    value_type = Column(String, default='string')  # 'string', 'int', 'float', 'bool', 'json'
    category = Column(String, default='general')  # 'general', 'platform', 'agent', 'seo'
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentLog(Base):
    """
    Logs from the autonomous agent for debugging and monitoring
    """
    __tablename__ = "agent_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, nullable=False)  # Identifier for the agent instance
    action = Column(String, nullable=False)
    status = Column(String, default='started')  # 'started', 'completed', 'failed', 'waiting'
    message = Column(Text, nullable=True)
    data = Column(Text, nullable=True)  # JSON with additional data
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=True)
    listing_id = Column(Integer, ForeignKey("platform_listings.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class NicheDiscovery(Base):
    """
    Stores AI-discovered niches for passive income opportunities
    """
    __tablename__ = "niche_discoveries"
    
    id = Column(Integer, primary_key=True, index=True)
    niche = Column(String, nullable=False)  # Niche name
    description = Column(Text, nullable=True)  # Detailed description
    search_query = Column(Text, nullable=True)  # Suggested search query
    potential_price = Column(String, nullable=True)  # e.g., "4.99-9.99"
    demand_level = Column(String, default='medium')  # 'low', 'medium', 'high'
    competition_level = Column(String, default='medium')  # 'low', 'medium', 'high'
    keywords = Column(Text, nullable=True)  # JSON array of keywords
    sites_to_search = Column(Text, nullable=True)  # JSON array of sites
    reason = Column(Text, nullable=True)  # Why this niche is good
    status = Column(String, default='discovered')  # 'discovered', 'job_created', 'scraping', 'evaluated', 'exhausted'
    scrape_job_id = Column(Integer, ForeignKey("scrape_jobs.id"), nullable=True)
    manuals_found = Column(Integer, default=0)
    manuals_listed = Column(Integer, default=0)
    revenue_generated = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_scraped_at = Column(DateTime, nullable=True)


class MarketResearch(Base):
    """
    Stores market research data for individual manuals/products
    """
    __tablename__ = "market_research"
    
    id = Column(Integer, primary_key=True, index=True)
    manual_id = Column(Integer, ForeignKey("manuals.id"), nullable=True)
    niche_id = Column(Integer, ForeignKey("niche_discoveries.id"), nullable=True)
    
    # Search data
    search_query = Column(Text, nullable=True)
    similar_listings = Column(Text, nullable=True)  # JSON array of similar listings found
    competitor_prices = Column(Text, nullable=True)  # JSON array of prices
    average_price = Column(Float, nullable=True)
    price_range_low = Column(Float, nullable=True)
    price_range_high = Column(Float, nullable=True)
    
    # Market analysis
    demand_score = Column(Float, default=0.0)  # 0-1 score
    competition_score = Column(Float, default=0.0)  # 0-1 score
    profitability_score = Column(Float, default=0.0)  # 0-1 score
    
    # AI evaluation
    ai_evaluation = Column(Text, nullable=True)  # JSON with full AI evaluation
    is_suitable = Column(Boolean, default=True)
    confidence_score = Column(Float, default=0.0)
    suggested_price = Column(Float, default=4.99)
    seo_title = Column(String, nullable=True)
    target_audience = Column(Text, nullable=True)
    concerns = Column(Text, nullable=True)  # JSON array of concerns
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    manual = relationship("Manual", backref="market_research")


class AutoScrapingState(Base):
    """
    Tracks the state of the auto-scraping agent
    """
    __tablename__ = "auto_scraping_state"
    
    id = Column(Integer, primary_key=True, index=True)
    is_enabled = Column(Boolean, default=False)
    current_phase = Column(String, default='idle')  # 'idle', 'discovering', 'scraping', 'evaluating', 'listing'
    current_job_id = Column(Integer, nullable=True)
    last_cycle_at = Column(DateTime, nullable=True)
    next_cycle_at = Column(DateTime, nullable=True)
    cycle_count = Column(Integer, default=0)
    total_niches_discovered = Column(Integer, default=0)
    total_manuals_evaluated = Column(Integer, default=0)
    total_manuals_listed = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PassiveIncomeManager:
    """
    Manager class for passive income operations
    """
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
    
    def get_platform_stats(self) -> Dict:
        """Get statistics for all platforms"""
        platforms = self.db.query(Platform).all()
        
        stats = {
            'total_platforms': len(platforms),
            'active_platforms': len([p for p in platforms if p.is_active]),
            'total_listings': sum(p.listing_count for p in platforms),
            'total_revenue': sum(p.total_revenue for p in platforms),
            'platforms': []
        }
        
        for platform in platforms:
            platform_stat = {
                'id': platform.id,
                'name': platform.name,
                'display_name': platform.display_name,
                'is_active': platform.is_active,
                'is_free': platform.is_free,
                'supports_api_listing': platform.supports_api_listing,
                'credentials_status': platform.credentials_status,
                'listing_count': platform.listing_count,
                'total_revenue': platform.total_revenue,
                'sync_status': platform.sync_status,
                'last_sync': platform.last_sync.isoformat() if platform.last_sync else None
            }
            stats['platforms'].append(platform_stat)
        
        return stats
    
    def get_pending_actions(self, limit: int = 50) -> List[ActionQueue]:
        """Get all pending actions requiring human intervention"""
        return self.db.query(ActionQueue).filter(
            ActionQueue.status == 'pending'
        ).order_by(
            ActionQueue.priority.asc(),
            ActionQueue.created_at.asc()
        ).limit(limit).all()
    
    def get_action_count(self) -> int:
        """Get count of pending actions"""
        return self.db.query(ActionQueue).filter(
            ActionQueue.status == 'pending'
        ).count()
    
    def get_revenue_summary(self, days: int = 30) -> Dict:
        """Get revenue summary for the last N days"""
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        records = self.db.query(Revenue).filter(
            Revenue.transaction_date >= start_date
        ).all()
        
        total_sales = len([r for r in records if r.transaction_type == 'sale'])
        total_revenue = sum(r.net_amount for r in records if r.transaction_type == 'sale')
        total_fees = sum(r.fee for r in records if r.transaction_type == 'sale')
        
        by_platform = {}
        for r in records:
            if r.transaction_type == 'sale':
                if r.platform_id not in by_platform:
                    by_platform[r.platform_id] = {'sales': 0, 'revenue': 0.0, 'fees': 0.0}
                by_platform[r.platform_id]['sales'] += 1
                by_platform[r.platform_id]['revenue'] += r.net_amount
                by_platform[r.platform_id]['fees'] += r.fee
        
        return {
            'period_days': days,
            'total_sales': total_sales,
            'total_revenue': total_revenue,
            'total_fees': total_fees,
            'by_platform': by_platform
        }
    
    def create_action(
        self,
        action_type: str,
        title: str,
        description: str,
        prompt: str = None,
        input_type: str = 'text',
        input_options: List = None,
        platform_id: int = None,
        listing_id: int = None,
        manual_id: int = None,
        context: Dict = None,
        priority: int = 5,
        expires_hours: int = 72
    ) -> ActionQueue:
        """Create a new action in the queue"""
        from datetime import timedelta
        
        action = ActionQueue(
            action_type=action_type,
            title=title,
            description=description,
            prompt=prompt,
            input_type=input_type,
            input_options=str(input_options) if input_options else None,
            platform_id=platform_id,
            listing_id=listing_id,
            manual_id=manual_id,
            context=str(context) if context else None,
            priority=priority,
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours)
        )
        
        self.db.add(action)
        self.db.commit()
        self.db.refresh(action)
        
        return action
    
    def resolve_action(self, action_id: int, response: str) -> ActionQueue:
        """Resolve an action with user response"""
        action = self.db.query(ActionQueue).filter(ActionQueue.id == action_id).first()
        
        if not action:
            raise ValueError(f"Action {action_id} not found")
        
        action.user_response = response
        action.responded_at = datetime.utcnow()
        action.status = 'completed'
        
        self.db.commit()
        self.db.refresh(action)
        
        return action
    
    def get_listings_by_status(self, status: str = None, platform_id: int = None) -> List[PlatformListing]:
        """Get listings filtered by status and/or platform"""
        query = self.db.query(PlatformListing)
        
        if status:
            query = query.filter(PlatformListing.status == status)
        
        if platform_id:
            query = query.filter(PlatformListing.platform_id == platform_id)
        
        return query.order_by(PlatformListing.created_at.desc()).all()
    
    def get_state(self) -> AutoScrapingState:
        """Get the current auto-scraping state"""
        state = self.db.query(AutoScrapingState).first()
        if not state:
            state = AutoScrapingState()
            self.db.add(state)
            self.db.commit()
            self.db.refresh(state)
        return state
    
    def update_state(self, state: AutoScrapingState) -> AutoScrapingState:
        """Update the auto-scraping state"""
        state.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(state)
        return state


def create_passive_income_tables():
    """Create all passive income tables"""
    Base.metadata.create_all(bind=engine, tables=[
        Platform.__table__,
        PlatformListing.__table__,
        ActionQueue.__table__,
        Revenue.__table__,
        Setting.__table__,
        AgentLog.__table__,
        NicheDiscovery.__table__,
        MarketResearch.__table__,
        AutoScrapingState.__table__
    ])


def init_default_platforms():
    """Initialize default platforms in the database"""
    db = SessionLocal()
    try:
        # Check if platforms already exist
        if db.query(Platform).first():
            return
        
        default_platforms = [
            {
                'name': 'etsy',
                'display_name': 'Etsy',
                'platform_type': 'digital_download',
                'api_base_url': 'https://openapi.etsy.com/v3',
                'is_free': True,
                'supports_api_listing': True,
                'supports_digital_downloads': True,
                'requires_verification': True
            },
            {
                'name': 'gumroad',
                'display_name': 'Gumroad',
                'platform_type': 'digital_download',
                'api_base_url': 'https://api.gumroad.com/v2',
                'is_free': True,
                'supports_api_listing': True,
                'supports_digital_downloads': True,
                'requires_verification': False
            },
            {
                'name': 'payhip',
                'display_name': 'Payhip',
                'platform_type': 'digital_download',
                'api_base_url': 'https://payhip.com/api/v1',
                'is_free': True,
                'supports_api_listing': False,  # No public API
                'supports_digital_downloads': True,
                'requires_verification': False
            },
            {
                'name': 'ebay',
                'display_name': 'eBay',
                'platform_type': 'marketplace',
                'api_base_url': 'https://api.ebay.com',
                'is_free': False,  # Has listing fees
                'supports_api_listing': True,
                'supports_digital_downloads': False,  # Policy restrictions
                'requires_verification': True
            },
            {
                'name': 'woocommerce',
                'display_name': 'WooCommerce',
                'platform_type': 'digital_download',
                'api_base_url': None,  # Self-hosted
                'is_free': True,
                'supports_api_listing': True,
                'supports_digital_downloads': True,
                'requires_verification': False
            },
            {
                'name': 'shopify',
                'display_name': 'Shopify',
                'platform_type': 'digital_download',
                'api_base_url': 'https://{shop}.myshopify.com/admin/api/2024-01',
                'is_free': False,  # Monthly fee
                'supports_api_listing': True,
                'supports_digital_downloads': True,
                'requires_verification': False
            },
            {
                'name': 'amazon',
                'display_name': 'Amazon KDP',
                'platform_type': 'digital_download',
                'api_base_url': None,  # No API for listing
                'is_free': True,
                'supports_api_listing': False,
                'supports_digital_downloads': True,
                'requires_verification': True
            }
        ]
        
        for platform_data in default_platforms:
            platform = Platform(**platform_data)
            db.add(platform)
        
        db.commit()
        print(f"Initialized {len(default_platforms)} default platforms")
        
    except Exception as e:
        db.rollback()
        print(f"Error initializing platforms: {e}")
    finally:
        db.close()
