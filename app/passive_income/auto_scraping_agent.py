"""
Auto-Scraping Agent for Passive Income
Automatically discovers profitable niches, creates scrape jobs, evaluates results,
and lists suitable items for passive income generation.

Workflow:
1. Check for pending manuals → evaluate them for listing suitability
2. Check for running scrape jobs → monitor progress
3. If no pending manuals and no running jobs → discover new niches or create new jobs
4. Ensure duplicate scrapes are avoided
"""
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from urllib.parse import quote_plus

from app.database import SessionLocal, Manual, ScrapeJob
from app.passive_income.database import (
    Platform, PlatformListing, ActionQueue, Revenue, Setting, AgentLog,
    PassiveIncomeManager, NicheDiscovery, MarketResearch, AutoScrapingState
)
from app.config import get_settings

settings = get_settings()


# AI Prompts for the auto-scraping agent
NICHE_DISCOVERY_PROMPT = """You are an expert at finding profitable digital products that can be sold for passive income. Your task is to suggest types of PDFs and digital files that:

1. Are freely available on the internet (public domain, open source, freely shared)
2. Have genuine value to buyers
3. Have good search demand but manageable competition
4. Can be legally resold or distributed

IMPORTANT: Focus on LEGAL and ETHICAL sources only:
- Public domain documents
- Open source documentation
- Creative Commons licensed materials
- Freely distributed manufacturer manuals/guides
- Government publications
- Educational materials with permissive licenses

Return a JSON array of 3-5 niche suggestions with this format:
```json
[
  {
    "niche": "Vintage Camera Repair Manuals",
    "description": "Service manuals for film cameras from 1960s-1990s",
    "search_query": "vintage camera service manual repair guide PDF",
    "potential_price": "4.99-9.99",
    "demand_level": "medium",
    "competition_level": "low",
    "keywords": ["canon AE-1", "nikon FM2", "pentax K1000", "olympus OM-1"],
    "sites_to_search": ["manualslib.com", "butkus.org", "camera-manual.com"],
    "reason": "Film photography is resurging, many enthusiasts need repair info for vintage cameras"
  }
]
```

Consider these categories:
1. Equipment service manuals (ATVs, motorcycles, lawn equipment, generators)
2. Vintage electronics repair guides
3. Craft and DIY project patterns/plans
4. Educational resources and study guides
5. Technical documentation and specifications
6. Hobby-specific guides (woodworking, metalworking, radio)
7. Vehicle repair manuals
8. Appliance repair guides

Return ONLY the JSON array, no other text."""


EVALUATE_LISTING_PROMPT = """You are an expert at evaluating digital products for passive income potential. Analyze this file/listing and determine if it's worth listing.

Input data:
- Title: {title}
- Source URL: {source_url}
- Equipment Type: {equipment_type}
- Manufacturer: {manufacturer}
- Model: {model}
- File size: {file_size}
- Market research: {market_research}

Evaluate based on:
1. Is this a genuine service/repair manual (not a preview, user guide, or brochure)?
2. Is there market demand for this type of content?
3. Is the quality likely to be good enough to sell?
4. Are there legal concerns (copyright, trademark)?
5. What price point would work?

Return JSON:
```json
{{
  "suitable": true/false,
  "confidence": 0.0-1.0,
  "reason": "explanation",
  "suggested_price": 4.99,
  "seo_title": "optimized title for listing",
  "target_audience": "who would buy this",
  "keywords": ["keyword1", "keyword2"],
  "concerns": ["any issues to note"],
  "market_analysis": {{
    "demand": "low/medium/high",
    "competition": "low/medium/high", 
    "price_range": "3.99-7.99"
  }}
}}
```

Return ONLY the JSON object."""


class AutoScrapingAgent:
    """
    Autonomous agent for automated passive income generation through:
    1. AI-powered niche discovery
    2. Automatic scrape job creation
    3. AI evaluation of discovered content
    4. Market research integration
    5. Automated listing pipeline
    
    The agent runs in cycles, always working on the most important task:
    - If there are pending manuals → evaluate them
    - If there are running jobs → monitor them
    - If idle → discover niches and create jobs
    """
    
    def __init__(self, db: Session = None, agent_id: str = "auto_scraping"):
        self.db = db or SessionLocal()
        self.manager = PassiveIncomeManager(self.db)
        self.agent_id = agent_id
        self.running = False
        
    def log(self, action: str, status: str, message: str, data: Dict = None):
        """Log agent activity"""
        log_entry = AgentLog(
            agent_id=self.agent_id,
            action=action,
            status=status,
            message=message,
            data=json.dumps(data) if data else None
        )
        self.db.add(log_entry)
        self.db.commit()
        print(f"[AutoScrapingAgent] {action}: {status} - {message}")
        return {'action': action, 'status': status, 'message': message, 'data': data}
    
    def get_setting(self, key: str, default: str = None) -> str:
        """Get a setting value"""
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        return setting.value if setting else default
    
    def set_setting(self, key: str, value: str, category: str = 'auto_scraping'):
        """Set a setting value"""
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = Setting(key=key, value=value, category=category)
            self.db.add(setting)
        self.db.commit()
    
    def is_enabled(self) -> bool:
        """Check if auto-scraping is enabled"""
        state = self.db.query(AutoScrapingState).first()
        return state.is_enabled if state else False
    
    def enable(self):
        """Enable auto-scraping"""
        self.set_setting('auto_scraping_enabled', 'true')
        state = self._get_or_create_state()
        state.is_enabled = True
        self.db.commit()
        self.log('auto_scraping', 'enabled', 'Auto-scraping agent enabled')
    
    def disable(self):
        """Disable auto-scraping"""
        self.set_setting('auto_scraping_enabled', 'false')
        state = self.db.query(AutoScrapingState).first()
        if state:
            state.is_enabled = False
            self.db.commit()
        self.log('auto_scraping', 'disabled', 'Auto-scraping agent disabled')
    
    def _get_or_create_state(self) -> AutoScrapingState:
        """Get or create the agent state"""
        state = self.db.query(AutoScrapingState).first()
        if not state:
            state = AutoScrapingState()
            self.db.add(state)
            self.db.commit()
            self.db.refresh(state)
        return state
    
    def run_cycle(self) -> Dict:
        """
        Run one intelligent cycle of the auto-scraping agent.
        
        Priority order:
        1. Evaluate pending manuals
        2. Check on running scrape jobs
        3. Process approved manuals (download/process)
        4. Create new scrape jobs if idle
        
        Returns a summary of what was done.
        """
        results = {
            'started_at': datetime.utcnow().isoformat(),
            'actions_taken': [],
            'manuals_evaluated': 0,
            'jobs_created': 0,
            'niches_discovered': 0,
            'manuals_processed': 0,
            'status': 'running'
        }
        
        state = self._get_or_create_state()
        
        if not state.is_enabled:
            results['status'] = 'disabled'
            results['message'] = 'Auto-scraping is disabled'
            return results
        
        self.log('cycle', 'started', 'Starting intelligent auto-scraping cycle')
        state.current_phase = 'evaluating'
        self.db.commit()
        
        try:
            # STEP 1: Evaluate pending manuals
            eval_result = self._evaluate_pending_manuals()
            results['manuals_evaluated'] = eval_result['count']
            if eval_result['count'] > 0:
                results['actions_taken'].append(f"Evaluated {eval_result['count']} pending manuals")
                results['actions_taken'].extend(eval_result['details'])
            
            # STEP 2: Process approved manuals (download and process)
            process_result = self._process_approved_manuals()
            results['manuals_processed'] = process_result['count']
            if process_result['count'] > 0:
                results['actions_taken'].append(f"Started processing {process_result['count']} approved manuals")
            
            # STEP 3: Check running scrape jobs
            jobs_status = self._check_running_jobs()
            results['running_jobs'] = jobs_status['running_count']
            if jobs_status['running_count'] > 0:
                results['actions_taken'].append(f"Monitoring {jobs_status['running_count']} running scrape jobs")
            
            # STEP 4: If no pending work, discover niches and create jobs
            if (eval_result['count'] == 0 and 
                process_result['count'] == 0 and 
                jobs_status['running_count'] == 0):
                
                # Check if we need new niches
                available_niches = self._get_available_niches()
                
                if not available_niches:
                    # Discover new niches
                    state.current_phase = 'discovering'
                    self.db.commit()
                    
                    niches = self._discover_niches()
                    results['niches_discovered'] = len(niches)
                    if len(niches) > 0:
                        results['actions_taken'].append(f"AI discovered {len(niches)} new profitable niches")
                    available_niches = self._get_available_niches()
                
                # Create scrape job from an available niche
                if available_niches:
                    state.current_phase = 'creating_job'
                    self.db.commit()
                    
                    job_result = self._create_job_from_niche(available_niches[0])
                    if job_result.get('created'):
                        results['jobs_created'] = 1
                        results['actions_taken'].append(f"Created scrape job: {job_result['job_name']}")
                    elif job_result.get('reason'):
                        results['actions_taken'].append(job_result['reason'])
            
            # Update state
            state.last_cycle_at = datetime.utcnow()
            state.cycle_count = (state.cycle_count or 0) + 1
            state.total_manuals_evaluated = (state.total_manuals_evaluated or 0) + results['manuals_evaluated']
            state.total_manuals_listed = (state.total_manuals_listed or 0) + results['manuals_processed']
            state.total_niches_discovered = (state.total_niches_discovered or 0) + results['niches_discovered']
            state.current_phase = 'idle'
            state.error_count = 0
            self.db.commit()
            
            results['status'] = 'completed'
            results['completed_at'] = datetime.utcnow().isoformat()
            
            self.log('cycle', 'completed', 
                    f"Cycle complete: {len(results['actions_taken'])} actions taken",
                    {'results': results})
            
            return results
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            tb = traceback.format_exc()
            
            state.current_phase = 'error'
            state.error_count = (state.error_count or 0) + 1
            state.last_error = error_msg
            self.db.commit()
            
            results['status'] = 'error'
            results['error'] = error_msg
            results['traceback'] = tb
            
            self.log('cycle', 'failed', f'Error: {error_msg}', {'traceback': tb})
            return results
    
    def _evaluate_pending_manuals(self) -> Dict:
        """Evaluate all pending manuals for listing suitability"""
        result = {'count': 0, 'details': []}
        
        # Get pending manuals that haven't been evaluated
        pending_manuals = self.db.query(Manual).filter(
            Manual.status == 'pending'
        ).limit(20).all()
        
        if not pending_manuals:
            return result
        
        self.log('evaluation', 'started', f'Found {len(pending_manuals)} pending manuals to evaluate')
        
        for manual in pending_manuals:
            try:
                evaluation = self._evaluate_manual(manual)
                
                # Check if we already have a platform listing for this
                existing_listing = self.db.query(PlatformListing).filter(
                    PlatformListing.manual_id == manual.id
                ).first()
                
                if not existing_listing:
                    # Create evaluation record
                    listing = PlatformListing(
                        manual_id=manual.id,
                        platform_id=self._get_default_platform_id(),
                        title=manual.title or 'Untitled',
                        price=evaluation.get('suggested_price', 4.99),
                        seo_title=evaluation.get('seo_title', manual.title),
                        status='evaluated' if evaluation.get('suitable') else 'rejected',
                        error_message=json.dumps(evaluation) if not evaluation.get('suitable') else None
                    )
                    self.db.add(listing)
                
                # If suitable with good confidence, approve for processing
                if evaluation.get('suitable') and evaluation.get('confidence', 0) > 0.6:
                    manual.status = 'approved'
                    result['details'].append(f"✓ Approved: {manual.title[:50]}... (confidence: {evaluation.get('confidence', 0):.2f})")
                else:
                    manual.status = 'rejected'
                    result['details'].append(f"✗ Rejected: {manual.title[:50]}... (reason: {evaluation.get('reason', 'unknown')[:50]})")
                
                result['count'] += 1
                self.db.commit()
                
            except Exception as e:
                result['details'].append(f"! Error evaluating manual {manual.id}: {str(e)[:50]}")
                self.log('evaluation', 'failed', f"Error evaluating manual {manual.id}: {str(e)}")
        
        self.log('evaluation', 'completed', f"Evaluated {result['count']} manuals")
        return result
    
    def _process_approved_manuals(self) -> Dict:
        """Start processing approved manuals (download and process PDFs)"""
        result = {'count': 0, 'details': []}
        
        # Get approved manuals that need downloading
        approved_manuals = self.db.query(Manual).filter(
            Manual.status == 'approved',
            Manual.pdf_path == None
        ).limit(10).all()
        
        if not approved_manuals:
            return result
        
        self.log('processing', 'started', f'Found {len(approved_manuals)} manuals to process')
        
        # Trigger async processing
        try:
            from app.tasks.jobs import process_approved_manuals
            process_approved_manuals.delay()
            result['count'] = len(approved_manuals)
            result['details'] = [f"Started processing {len(approved_manuals)} manuals"]
        except Exception as e:
            self.log('processing', 'warning', f"Could not trigger processing: {str(e)}")
            result['details'] = [f"Processing will be handled by scheduled task"]
        
        return result
    
    def _check_running_jobs(self) -> Dict:
        """Check status of running scrape jobs"""
        result = {'running_count': 0, 'completed_count': 0, 'failed_count': 0}
        
        running_jobs = self.db.query(ScrapeJob).filter(
            ScrapeJob.status == 'running'
        ).all()
        
        result['running_count'] = len(running_jobs)
        
        # Check for jobs that have been running too long (stale)
        for job in running_jobs:
            if job.started_at:
                runtime = datetime.utcnow() - job.started_at
                if runtime > timedelta(hours=2):  # Job running over 2 hours
                    self.log('job_monitor', 'warning', 
                            f"Job {job.id} has been running for {runtime}")
        
        return result
    
    def _get_available_niches(self) -> List[NicheDiscovery]:
        """Get niches that haven't been scraped yet"""
        return self.db.query(NicheDiscovery).filter(
            NicheDiscovery.status == 'discovered',
            NicheDiscovery.scrape_job_id == None
        ).order_by(
            # Prioritize high demand, low competition
            NicheDiscovery.demand_level.desc()
        ).limit(5).all()
    
    def _create_job_from_niche(self, niche: NicheDiscovery) -> Dict:
        """Create a scrape job from a niche"""
        result = {'created': False, 'reason': None, 'job_name': None}
        
        # Check if we already have a similar job (avoid duplicates)
        existing_job = self.db.query(ScrapeJob).filter(
            ScrapeJob.name.ilike(f"%{niche.niche[:30]}%")
        ).first()
        
        if existing_job:
            result['reason'] = f"Similar job already exists: {existing_job.name}"
            return result
        
        # Check if this niche has been scraped recently
        recent_niche_scrape = self.db.query(NicheDiscovery).filter(
            NicheDiscovery.niche == niche.niche,
            NicheDiscovery.last_scraped_at > datetime.utcnow() - timedelta(days=7)
        ).first()
        
        if recent_niche_scrape:
            result['reason'] = f"Niche '{niche.niche}' was scraped recently"
            return result
        
        try:
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
                status='queued'
            )
            
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            
            # Update niche
            niche.scrape_job_id = job.id
            niche.status = 'job_created'
            niche.last_scraped_at = datetime.utcnow()
            self.db.commit()
            
            result['created'] = True
            result['job_id'] = job.id
            result['job_name'] = job.name
            
            self.log('job_created', 'completed', 
                    f"Created scrape job for niche: {niche.niche}",
                    {'job_id': job.id, 'niche': niche.niche})
            
        except Exception as e:
            result['reason'] = f"Error creating job: {str(e)}"
            self.log('job_created', 'failed', f"Error creating job: {str(e)}")
        
        return result
    
    def discover_niches(self) -> List[Dict]:
        """Public method to discover niches"""
        return self._discover_niches()
    
    def _discover_niches(self) -> List[Dict]:
        """Use AI to discover profitable niches for passive income"""
        # Check cache
        last_discovery = self.get_setting('last_niche_discovery')
        discovery_interval = int(self.get_setting('niche_discovery_interval_hours', '1'))
        
        if last_discovery:
            try:
                last_time = datetime.fromisoformat(last_discovery)
                if datetime.utcnow() - last_time < timedelta(hours=discovery_interval):
                    cached = self.get_setting('cached_niches')
                    if cached:
                        return json.loads(cached)
            except:
                pass
        
        self.log('niche_discovery', 'started', 'Discovering new profitable niches')
        
        try:
            from groq import Groq
            
            if not settings.groq_api_key:
                self.log('niche_discovery', 'failed', 'GROQ_API_KEY not configured')
                return []
            
            client = Groq(api_key=settings.groq_api_key)
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": NICHE_DISCOVERY_PROMPT},
                    {"role": "user", "content": "Suggest profitable niches for digital PDF products that can be found freely online and sold for passive income. Focus on service manuals, repair guides, and technical documentation."}
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            response_text = completion.choices[0].message.content
            niches = json.loads(response_text)
            
            # Handle if it's wrapped in a key
            if isinstance(niches, dict) and 'niches' in niches:
                niches = niches['niches']
            elif isinstance(niches, dict) and not isinstance(niches, list):
                # Single niche object
                niches = [niches]
            
            # Store in database and cache
            for niche_data in niches:
                if not isinstance(niche_data, dict):
                    continue
                    
                existing = self.db.query(NicheDiscovery).filter(
                    NicheDiscovery.niche == niche_data.get('niche')
                ).first()
                
                if not existing:
                    niche = NicheDiscovery(
                        niche=niche_data.get('niche'),
                        description=niche_data.get('description'),
                        search_query=niche_data.get('search_query'),
                        potential_price=niche_data.get('potential_price'),
                        demand_level=niche_data.get('demand_level', 'medium'),
                        competition_level=niche_data.get('competition_level', 'medium'),
                        keywords=json.dumps(niche_data.get('keywords', [])),
                        sites_to_search=json.dumps(niche_data.get('sites_to_search', [])),
                        reason=niche_data.get('reason')
                    )
                    self.db.add(niche)
            
            self.db.commit()
            
            # Cache results
            self.set_setting('cached_niches', json.dumps(niches))
            self.set_setting('last_niche_discovery', datetime.utcnow().isoformat())
            
            self.log('niche_discovery', 'completed', f'Discovered {len(niches)} niches')
            
            return niches
            
        except Exception as e:
            self.log('niche_discovery', 'failed', f'Error: {str(e)}')
            return []
    
    def _evaluate_manual(self, manual: Manual) -> Dict:
        """Evaluate a single manual for listing suitability"""
        try:
            from groq import Groq
            
            if not settings.groq_api_key:
                return {
                    'suitable': True,
                    'confidence': 0.5,
                    'reason': 'AI evaluation not available, defaulting to suitable',
                    'suggested_price': 4.99
                }
            
            # Quick check for obvious non-service manuals
            title_lower = (manual.title or '').lower()
            url_lower = (manual.source_url or '').lower()
            
            # Skip obvious non-matches
            skip_terms = ['preview', 'sample', 'brochure', 'catalog', 'price list', 
                         'advertisement', 'promotional', 'warranty card']
            for term in skip_terms:
                if term in title_lower or term in url_lower:
                    return {
                        'suitable': False,
                        'confidence': 0.8,
                        'reason': f'Appears to be a {term}, not a service manual',
                        'suggested_price': 0
                    }
            
            client = Groq(api_key=settings.groq_api_key)
            
            prompt = EVALUATE_LISTING_PROMPT.format(
                title=manual.title or 'Unknown',
                source_url=manual.source_url or 'Unknown',
                equipment_type=manual.equipment_type or 'Unknown',
                manufacturer=manual.manufacturer or 'Unknown',
                model=manual.model or 'Unknown',
                file_size='Unknown',
                market_research='Not available'
            )
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert at evaluating digital products for passive income potential."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            evaluation = json.loads(completion.choices[0].message.content)
            
            # Ensure required fields
            evaluation.setdefault('suitable', True)
            evaluation.setdefault('confidence', 0.5)
            evaluation.setdefault('suggested_price', 4.99)
            evaluation.setdefault('reason', 'No specific reason provided')
            
            # Store market research
            research = self.db.query(MarketResearch).filter(
                MarketResearch.manual_id == manual.id
            ).first()
            
            if not research:
                research = MarketResearch(manual_id=manual.id)
                self.db.add(research)
            
            research.ai_evaluation = json.dumps(evaluation)
            research.is_suitable = evaluation.get('suitable', True)
            research.confidence_score = evaluation.get('confidence', 0.5)
            research.suggested_price = evaluation.get('suggested_price', 4.99)
            research.seo_title = evaluation.get('seo_title', manual.title)
            research.target_audience = evaluation.get('target_audience', '')
            research.concerns = json.dumps(evaluation.get('concerns', []))
            self.db.commit()
            
            return evaluation
            
        except Exception as e:
            return {
                'suitable': True,  # Default to suitable if evaluation fails
                'confidence': 0.5,
                'reason': f'Evaluation error: {str(e)}',
                'suggested_price': 4.99
            }
    
    def _get_default_platform_id(self) -> int:
        """Get the default platform ID for listings"""
        platform = self.db.query(Platform).filter(
            Platform.is_active == True,
            Platform.supports_api_listing == True
        ).first()
        
        if platform:
            return platform.id
        
        platform = self.db.query(Platform).first()
        return platform.id if platform else 1
    
    def get_status(self) -> Dict:
        """Get the current status of the auto-scraping agent"""
        state = self._get_or_create_state()
        
        # Count pending manuals
        pending_count = self.db.query(Manual).filter(
            Manual.status == 'pending'
        ).count()
        
        # Count approved manuals waiting to be processed
        approved_count = self.db.query(Manual).filter(
            Manual.status == 'approved',
            Manual.pdf_path == None
        ).count()
        
        # Count running jobs
        running_jobs = self.db.query(ScrapeJob).filter(
            ScrapeJob.status == 'running'
        ).count()
        
        # Get available niches
        available_niches = len(self._get_available_niches())
        
        return {
            'enabled': state.is_enabled,
            'current_phase': state.current_phase,
            'last_cycle': state.last_cycle_at.isoformat() if state.last_cycle_at else None,
            'cycle_count': state.cycle_count,
            'pending_manuals': pending_count,
            'approved_manuals': approved_count,
            'running_jobs': running_jobs,
            'available_niches': available_niches,
            'total_niches_discovered': state.total_niches_discovered,
            'total_manuals_evaluated': state.total_manuals_evaluated,
            'total_manuals_listed': state.total_manuals_listed,
            'error_count': state.error_count,
            'last_error': state.last_error
        }


def run_auto_scraping_cycle():
    """Run a single auto-scraping cycle (for scheduled tasks)"""
    agent = AutoScrapingAgent()
    return agent.run_cycle()
