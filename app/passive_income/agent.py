"""
Autonomous Agent for Passive Income Operations
Handles automatic listing, pricing, and multi-platform synchronization
"""
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.database import SessionLocal, Manual
from app.passive_income.database import (
    Platform, PlatformListing, ActionQueue, Revenue, Setting, AgentLog,
    PassiveIncomeManager
)
from app.passive_income.platforms import PlatformRegistry


class AutonomousAgent:
    """
    Autonomous agent that runs background tasks for passive income generation
    
    Responsibilities:
    - Auto-list processed manuals on multiple platforms
    - Generate SEO-optimized titles and descriptions using AI
    - Synchronize listings across platforms
    - Handle pricing optimization
    - Create action queue items for human intervention
    """
    
    def __init__(self, db: Session = None, agent_id: str = "main"):
        self.db = db or SessionLocal()
        self.manager = PassiveIncomeManager(self.db)
        self.agent_id = agent_id
        self.running = False
        self._log_buffer = []
    
    def log(self, action: str, status: str, message: str, data: Dict = None,
            platform_id: int = None, listing_id: int = None):
        """Log agent activity"""
        log_entry = AgentLog(
            agent_id=self.agent_id,
            action=action,
            status=status,
            message=message,
            data=json.dumps(data) if data else None,
            platform_id=platform_id,
            listing_id=listing_id
        )
        self.db.add(log_entry)
        self.db.commit()
        print(f"[Agent {self.agent_id}] {action}: {status} - {message}")
    
    def run_cycle(self):
        """Run one cycle of autonomous operations"""
        self.log('cycle', 'started', 'Starting autonomous cycle')
        
        try:
            # 1. Process pending listings
            self._process_pending_listings()
            
            # 2. Sync platform data
            self._sync_platforms()
            
            # 3. Check for action timeouts
            self._check_action_timeouts()
            
            # 4. Auto-adjust pricing (if enabled)
            self._auto_adjust_pricing()
            
            self.log('cycle', 'completed', 'Autonomous cycle completed')
            
        except Exception as e:
            self.log('cycle', 'failed', f'Error: {str(e)}')
    
    def _process_pending_listings(self):
        """Process manuals that are ready to be listed"""
        # Get processed manuals without platform listings
        manuals = self.db.query(Manual).filter(
            Manual.status == 'processed',
            ~Manual.id.in_(
                self.db.query(PlatformListing.manual_id).filter(
                    PlatformListing.status.in_(['pending', 'listed', 'active'])
                )
            )
        ).limit(10).all()
        
        self.log('process_listings', 'started', f'Found {len(manuals)} manuals to list')
        
        for manual in manuals:
            self._list_manual_on_platforms(manual)
    
    def _list_manual_on_platforms(self, manual: Manual):
        """List a manual on all active platforms"""
        # Get active platforms with API support
        platforms = self.db.query(Platform).filter(
            Platform.is_active == True,
            Platform.supports_api_listing == True
        ).all()
        
        for platform in platforms:
            try:
                self._create_platform_listing(manual, platform)
            except Exception as e:
                self.log('list', 'failed', f'Error listing on {platform.name}: {str(e)}',
                        platform_id=platform.id)
    
    def _create_platform_listing(self, manual: Manual, platform: Platform):
        """Create a listing on a specific platform"""
        # Get platform client
        credentials = json.loads(platform.credentials) if platform.credentials else {}
        platform_client = PlatformRegistry.get(platform.name, credentials=credentials)
        
        if not platform_client:
            self.log('list', 'failed', f'Platform {platform.name} not registered',
                    platform_id=platform.id)
            return
        
        # Check platform status
        status = platform_client.check_status()
        if not status.is_connected:
            self._create_action_for_auth(platform, status)
            return
        
        # Generate SEO title
        seo_title = self._generate_seo_title(manual, platform.name)
        
        # Get listing content
        description = manual.description or self._generate_description(manual)
        price = self._calculate_price(manual)
        tags = self._extract_tags(manual)
        
        # Create listing record first
        listing = PlatformListing(
            manual_id=manual.id,
            platform_id=platform.id,
            title=seo_title,
            description=description,
            price=price,
            seo_title=seo_title,
            tags=json.dumps(tags),
            status='pending'
        )
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        
        # Attempt to create on platform
        result = platform_client.create_listing(
            title=seo_title,
            description=description,
            price=price,
            file_path=manual.pdf_path,
            images=self._get_manual_images(manual),
            tags=tags
        )
        
        if result.success:
            listing.status = 'listed'
            listing.platform_listing_id = result.listing_id
            listing.platform_url = result.listing_url
            listing.listed_at = datetime.utcnow()
            self.db.commit()
            
            self.log('list', 'completed', f'Listed on {platform.name}',
                    platform_id=platform.id, listing_id=listing.id)
            
        elif result.requires_action:
            listing.status = 'action_required'
            self.db.commit()
            
            # Create action queue item
            self.manager.create_action(
                action_type=result.action_type,
                title=f"Action required for {platform.display_name}",
                description=result.error,
                prompt="Please complete this action to continue listing",
                platform_id=platform.id,
                listing_id=listing.id,
                manual_id=manual.id,
                context={'listing_id': listing.id, 'error': result.error}
            )
        else:
            listing.status = 'error'
            listing.error_message = result.error
            self.db.commit()
            
            self.log('list', 'failed', f'Failed to list: {result.error}',
                    platform_id=platform.id, listing_id=listing.id)
    
    def _create_action_for_auth(self, platform: Platform, status):
        """Create an action for authentication"""
        # Check if action already exists
        existing = self.db.query(ActionQueue).filter(
            ActionQueue.platform_id == platform.id,
            ActionQueue.action_type == 'authentication',
            ActionQueue.status == 'pending'
        ).first()
        
        if existing:
            return
        
        self.manager.create_action(
            action_type='authentication',
            title=f"{platform.display_name} Authentication Required",
            description=f"Your {platform.display_name} connection needs to be re-authenticated.",
            prompt="Click the link to authenticate",
            input_type='url',
            platform_id=platform.id,
            context={'auth_url': status.auth_url},
            priority=1
        )
    
    def _sync_platforms(self):
        """Sync data from all connected platforms"""
        platforms = self.db.query(Platform).filter(
            Platform.is_active == True,
            Platform.credentials_status == 'verified'
        ).all()
        
        for platform in platforms:
            try:
                self._sync_platform_sales(platform)
            except Exception as e:
                self.log('sync', 'failed', f'Sync failed for {platform.name}: {str(e)}',
                        platform_id=platform.id)
    
    def _sync_platform_sales(self, platform: Platform):
        """Sync sales data from a platform"""
        credentials = json.loads(platform.credentials) if platform.credentials else {}
        platform_client = PlatformRegistry.get(platform.name, credentials=credentials)
        
        if not platform_client:
            return
        
        sales = platform_client.get_sales(days=30)
        
        for sale in sales:
            # Check if we already have this transaction
            existing = self.db.query(Revenue).filter(
                Revenue.transaction_id == sale.get('transaction_id')
            ).first()
            
            if existing:
                continue
            
            # Find the listing
            listing = self.db.query(PlatformListing).filter(
                PlatformListing.platform_id == platform.id,
                PlatformListing.platform_listing_id == sale.get('listing_id')
            ).first()
            
            # Create revenue record
            revenue = Revenue(
                listing_id=listing.id if listing else None,
                platform_id=platform.id,
                transaction_id=sale.get('transaction_id'),
                amount=sale.get('amount', 0),
                fee=sale.get('fee', 0),
                net_amount=sale.get('amount', 0) - sale.get('fee', 0),
                currency='USD',
                transaction_date=datetime.fromisoformat(sale['date'].replace('Z', '')) if sale.get('date') else datetime.utcnow()
            )
            self.db.add(revenue)
            
            # Update listing stats
            if listing:
                listing.sales += 1
                listing.revenue += sale.get('amount', 0)
            
            # Update platform total
            platform.total_revenue += sale.get('amount', 0)
        
        platform.last_sync = datetime.utcnow()
        platform.sync_status = 'synced'
        self.db.commit()
        
        self.log('sync', 'completed', f'Synced {len(sales)} sales from {platform.name}',
                platform_id=platform.id)
    
    def _check_action_timeouts(self):
        """Check for actions that have expired"""
        expired = self.db.query(ActionQueue).filter(
            ActionQueue.status == 'pending',
            ActionQueue.expires_at < datetime.utcnow()
        ).all()
        
        for action in expired:
            action.status = 'expired'
            self.log('action', 'expired', f'Action {action.id} expired: {action.title}')
        
        self.db.commit()
    
    def _auto_adjust_pricing(self):
        """Auto-adjust pricing based on performance (if enabled)"""
        # Check if auto-pricing is enabled
        setting = self.db.query(Setting).filter(
            Setting.key == 'auto_pricing_enabled'
        ).first()
        
        if not setting or setting.value != 'true':
            return
        
        # Get listings with low views but no sales
        listings = self.db.query(PlatformListing).filter(
            PlatformListing.status == 'active',
            PlatformListing.sales == 0,
            PlatformListing.views > 50
        ).all()
        
        for listing in listings:
            # Reduce price by 10%
            new_price = listing.price * 0.9
            if new_price >= 0.99:  # Minimum price
                listing.price = new_price
                listing.original_price = listing.original_price or listing.price
                
                # Update on platform
                platform = self.db.query(Platform).get(listing.platform_id)
                self._update_platform_price(platform, listing, new_price)
        
        self.db.commit()
    
    def _update_platform_price(self, platform: Platform, listing: PlatformListing, price: float):
        """Update listing price on platform"""
        credentials = json.loads(platform.credentials) if platform.credentials else {}
        platform_client = PlatformRegistry.get(platform.name, credentials=credentials)
        
        if platform_client and listing.platform_listing_id:
            platform_client.update_listing(
                listing.platform_listing_id,
                price=price
            )
    
    def _generate_seo_title(self, manual: Manual, platform_name: str) -> str:
        """Generate SEO-optimized title using AI or templates"""
        base_title = manual.title or f"{manual.manufacturer} {manual.model} Service Manual"
        
        # Build SEO title
        parts = []
        
        if manual.year:
            parts.append(manual.year)
        
        if manual.manufacturer:
            parts.append(manual.manufacturer)
        
        if manual.model:
            parts.append(manual.model)
        
        parts.append('Service Manual')
        
        seo_title = ' '.join(parts)
        
        # Platform-specific suffixes
        if platform_name == 'etsy':
            seo_title += ' | Digital Download PDF'
        elif platform_name == 'gumroad':
            seo_title += ' [PDF Digital Download]'
        
        return seo_title[:140]  # Max title length
    
    def _generate_description(self, manual: Manual) -> str:
        """Generate listing description"""
        desc_parts = []
        
        title = f"{manual.year + ' ' if manual.year else ''}{manual.manufacturer or ''} {manual.model or ''} Service Manual".strip()
        desc_parts.append(f"# {title}")
        desc_parts.append("")
        desc_parts.append("## Digital PDF Download")
        desc_parts.append("")
        desc_parts.append("This is a complete service manual for your equipment.")
        desc_parts.append("")
        desc_parts.append("### What's Included:")
        desc_parts.append("- Complete service procedures")
        desc_parts.append("- Wiring diagrams")
        desc_parts.append("- Troubleshooting guides")
        desc_parts.append("- Maintenance schedules")
        desc_parts.append("")
        desc_parts.append("### Features:")
        desc_parts.append("- Instant digital download")
        desc_parts.append("- PDF format - works on all devices")
        desc_parts.append("- Fully searchable")
        desc_parts.append("- Printable")
        desc_parts.append("")
        desc_parts.append("**This is a digital product. No physical item will be shipped.**")
        
        return '\n'.join(desc_parts)
    
    def _calculate_price(self, manual: Manual) -> float:
        """Calculate optimal listing price"""
        base_price = 4.99
        
        # Adjust based on page count if available
        # More pages = higher value
        # This could be enhanced with AI pricing optimization
        
        return base_price
    
    def _extract_tags(self, manual: Manual) -> List[str]:
        """Extract tags from manual metadata"""
        tags = []
        
        if manual.manufacturer:
            tags.append(manual.manufacturer.lower())
        
        if manual.model:
            tags.append(manual.model.lower())
            # Extract model number
            import re
            numbers = re.findall(r'\d+', manual.model)
            for num in numbers[:2]:
                tags.append(num)
        
        if manual.year:
            tags.append(manual.year)
        
        if manual.equipment_type:
            tags.append(manual.equipment_type.lower())
        
        # Add standard tags
        standard_tags = ['service manual', 'repair guide', 'pdf', 'digital download', 'diy', 'workshop manual']
        tags.extend(standard_tags)
        
        return list(set(tags))[:13]  # Unique, max 13
    
    def _get_manual_images(self, manual: Manual) -> List[str]:
        """Get image paths for a manual"""
        if manual.pdf_path:
            # Images should be generated during PDF processing
            import os
            from pathlib import Path
            
            pdf_dir = Path(manual.pdf_path).parent
            image_dir = pdf_dir / 'images'
            
            if image_dir.exists():
                return [str(f) for f in sorted(image_dir.glob('*.jpg'))[:5]]
        
        return []
    
    def process_action_response(self, action_id: int, response: str):
        """Process a response to an action and resume work"""
        action = self.manager.resolve_action(action_id, response)
        
        if not action:
            return
        
        self.log('action', 'completed', f'Action {action_id} resolved')
        
        # Resume the task that was waiting
        if action.context:
            context = json.loads(action.context) if isinstance(action.context, str) else action.context
            
            if action.action_type == 'authentication':
                # Retry listing after auth
                if action.listing_id:
                    listing = self.db.query(PlatformListing).get(action.listing_id)
                    if listing and listing.manual:
                        platform = self.db.query(Platform).get(listing.platform_id)
                        self._create_platform_listing(listing.manual, platform)
            
            elif action.action_type == 'manual_listing':
                # User completed manual listing
                if action.listing_id:
                    listing = self.db.query(PlatformListing).get(action.listing_id)
                    if listing:
                        listing.status = 'listed'
                        listing.listed_at = datetime.utcnow()
                        listing.platform_url = response  # User provides listing URL
                        self.db.commit()


def run_agent_cycle():
    """Run a single agent cycle (for scheduled tasks)"""
    agent = AutonomousAgent()
    agent.run_cycle()
