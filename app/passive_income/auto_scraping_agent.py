"""
Auto-Scraping Agent for Passive Income
Automatically discovers profitable niches, creates scrape jobs, evaluates results,
and lists suitable items for passive income generation.
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

# Prompt for AI to discover profitable niches
NICHE_DISCOVERY_PROMPT = """You are an AI assistant that discovers profitable niches for digital PDF products that can be found freely online and sold for passive income.

For each niche suggestion, you MUST include:
1. A clear niche name (e.g., "Vintage Camera Manuals", "Motorcycle Repair Guides")
2. A search query to use (e.g., "vintage camera manual filetype:pdf", "motorcycle repair guide pdf")
3. Keywords to filter results (e.g., ["service manual", "repair guide", "workshop manual"])
4. Demand level (low/medium/high)
5. Competition level (low/medium/high)
6. Potential price range (e.g., "4.99-9.99")

Return ONLY a JSON object with this exact structure:
{
  "niches": [
    {
      "niche": "Vintage Camera Manuals",
      "search_query": "vintage camera manual filetype:pdf",
      "keywords": ["service manual", "repair guide", "workshop manual"],
      "demand_level": "high",
      "competition_level": "low",
      "potential_price": "4.99-9.99",
      "reason": "Vintage cameras have high demand and low competition for service manuals"
    }
  ]
}

DO NOT include any other fields or wrap the response in additional objects."""


class AutoScrapingAgent:
    """
    Autonomous agent for automated passive income generation through:
    1. AI-powered niche discovery
    2. Automatic scrape job creation
    3. AI evaluation of discovered content
    4. Automatic listing creation
    """

    def __init__(self, db: Session, agent_id: str = "auto_scraping_agent"):
        self.db = db
        self.manager = PassiveIncomeManager(db)
        self.agent_id = agent_id

    def log(self, action: str, status: str, message: str, data: Dict = None):
        """Log agent action"""
        log_entry = AgentLog(
            agent_id=self.agent_id,
            action=action,
            status=status,
            message=message,
            data=json.dumps(data) if data else None
        )
        self.db.add(log_entry)
        self.db.commit()
        print(f"[{action.upper()}] {status}: {message}")

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        return setting.value if setting else default

    def set_setting(self, key: str, value: Any):
        """Set a setting value"""
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = json.dumps(value) if isinstance(value, (dict, list)) else value
            setting.updated_at = datetime.utcnow()
        else:
            setting = Setting(key=key, value=json.dumps(value) if isinstance(value, (dict, list)) else value, updated_at=datetime.utcnow())
        self.db.add(setting)
        self.db.commit()

    def enable(self):
        """Enable auto-scraping agent"""
        self.log('enable', 'completed', 'Auto-scraping agent enabled')
    
    def disable(self):
        """Disable auto-scraping agent"""
        self.log('disable', 'completed', 'Auto-scraping agent disabled')
    
    def run_cycle(self) -> Dict:
        """
        Run one complete cycle of the auto-scraping agent
        
        Returns:
            Dict with cycle results including:
            - actions_taken: List of actions performed
            - niches_discovered: Number of niches discovered
            - jobs_created: Number of jobs created
            - running_jobs: Number of jobs currently running
            - manuals_processed: Number of manuals evaluated
            - prompted: Whether a user prompt was created (agent idle)
            - prompt_type: Type of prompt created ('new_niche' or 'refine_config')
            - prompt_id: ID of the created prompt
        """
        result = {
            'actions_taken': [],
            'niches_discovered': 0,
            'jobs_created': 0,
            'running_jobs': 0,
            'manuals_processed': 0,
            'status': 'idle',
            'error': None,
            'prompted': False,
            'prompt_type': None,
            'prompt_id': None
        }

        try:
            # STEP 1: Get current state
            state = self.manager.get_state()

            # STEP 2: Check for running jobs
            running_jobs = self.db.query(ScrapeJob).filter(ScrapeJob.status == 'running').count()
            result['running_jobs'] = running_jobs

            if running_jobs > 0:
                self.log('job_check', 'completed', 'Job already running, waiting for completion')
                result['status'] = 'running'
                return result

            # STEP 3: Check for pending manuals
            pending_manuals = self.db.query(Manual).filter(
                Manual.status == 'pending'
            ).count()

            # STEP 4: If no pending work, discover new niches
            if pending_manuals == 0 and running_jobs == 0:
                self.log('niche_discovery', 'started', 'No pending work, discovering new niches')
                result['status'] = 'discovering'
                state.current_phase = 'discovering'

                # Discover niches
                niches = self._discover_niches()
                result['niches_discovered'] = len(niches)
                result['actions_taken'].append(f"AI discovered {len(niches)} new profitable niches")

                # STEP 5: Create jobs from available niches
                available_niches = self._get_available_niches()
                if available_niches:
                    self.log('job_creation', 'started', f'Creating jobs from {len(available_niches)} available niches')
                    result['status'] = 'creating_jobs'
                    state.current_phase = 'creating_job'

                    # Create jobs for niches (limit to 3 to avoid overwhelming the system)
                    jobs_created = 0
                    for niche in available_niches[:3]:
                        job_result = self._create_job_from_niche(niche)
                        if job_result.get('created'):
                            jobs_created += 1
                            result['actions_taken'].append(job_result.get('reason'))

                    result['jobs_created'] = jobs_created

                # STEP 6: If jobs were created, monitor them
                if jobs_created > 0:
                    self.log('job_monitoring', 'started', f'Monitoring {jobs_created} created jobs')
                    result['status'] = 'monitoring'
                    state.current_phase = 'monitoring'

                    # Wait a bit for jobs to start
                    time.sleep(2)

                    # Check if jobs are running
                    running_count = self.db.query(ScrapeJob).filter(ScrapeJob.status == 'running').count()
                    result['running_jobs'] = running_count

                    if running_count == 0:
                        self.log('job_monitoring', 'completed', 'No jobs started, something went wrong')
                        result['status'] = 'error'
                        result['error'] = 'Jobs were created but failed to start'
                    else:
                        self.log('job_monitoring', 'completed', f'{running_count} jobs are now running')
                        result['status'] = 'running'
                        result['actions_taken'].append(f'{running_count} jobs started successfully')

                # STEP 7: If no jobs running, evaluate pending manuals
                if running_jobs == 0:
                    pending_count = self.db.query(Manual).filter(
                        Manual.status == 'pending'
                    ).count()

                    if pending_count > 0:
                        self.log('evaluation', 'started', f'Evaluating {pending_count} pending manuals')
                        result['status'] = 'evaluating'
                        state.current_phase = 'evaluating'

                        # Evaluate manuals
                        manuals_processed = self._evaluate_pending_manuals(pending_count)
                        result['manuals_processed'] = manuals_processed

                        # STEP 8: If suitable manuals found, create listings
                        if manuals_processed > 0:
                            self.log('listing', 'started', f'Creating listings for {manuals_processed} suitable manuals')
                            result['status'] = 'creating_listings'
                            state.current_phase = 'creating_listings'

                            # Create listings (limit to 5 to avoid overwhelming the system)
                            listings_created = self._create_listings_for_manuals(manuals_processed)
                            result['actions_taken'].append(f'Created {listings_created} Etsy listings')

                            result['listings_created'] = listings_created
                        else:
                            self.log('evaluation', 'completed', f'No suitable manuals found for listing')

                # STEP 8: Handle idle state - prompt for new niches or refined configurations
                if running_jobs == 0 and pending_manuals == 0 and result['jobs_created'] == 0:
                    # Get available niches again for the idle check
                    available_niches = self._get_available_niches()
                    
                    # Handle idle state
                    prompt_result = self._handle_idle_state(running_jobs, pending_manuals, available_niches)
                    
                    if prompt_result.get('prompted'):
                        result['prompted'] = True
                        result['prompt_type'] = prompt_result.get('prompt_type')
                        result['prompt_id'] = prompt_result.get('prompt_id')
                        result['status'] = 'waiting_for_input'
                        result['actions_taken'].append(f"Created {prompt_result.get('prompt_type')} prompt for user input")
                        self.log('idle_state', 'completed', f'Agent idle, created {prompt_result.get("prompt_type")} prompt (ID: {prompt_result.get("prompt_id")})')

            # STEP 9: Update state
            state.total_niches_discovered = (state.total_niches_discovered or 0) + result['niches_discovered']
            state.total_manuals_evaluated = (state.total_manuals_evaluated or 0) + result['manuals_processed']
            state.current_phase = 'idle'
            self.manager.update_state(state)
            self.db.commit()

            result['status'] = 'completed'
            return result

        except Exception as e:
            self.log('cycle', 'failed', f'Error: {str(e)}')
            result['status'] = 'error'
            result['error'] = str(e)
            return result

    def _get_available_niches(self) -> List[NicheDiscovery]:
        """Get niches that haven't been scraped yet"""
        return self.db.query(NicheDiscovery).filter(
            NicheDiscovery.status == 'discovered',
            NicheDiscovery.scrape_job_id == None
        ).all()

    def _should_prompt_for_input(self, running_jobs: int, pending_manuals: int, available_niches: List[NicheDiscovery]) -> bool:
        """
        Check if the agent should prompt for user input.
        
        Returns True when:
        - No running jobs
        - No pending manuals
        - No available niches to scrape
        - No pending prompts already in action queue
        """
        # Check if there's already a pending prompt
        pending_prompt = self.db.query(ActionQueue).filter(
            ActionQueue.status == 'pending',
            ActionQueue.action_type.in_(['new_niche_prompt', 'refine_config_prompt'])
        ).first()
        
        if pending_prompt:
            return False
        
        # Check if we should prompt (idle state with no work to do)
        return (
            running_jobs == 0 and
            pending_manuals == 0 and
            len(available_niches) == 0
        )

    def _create_niche_prompt(self) -> Optional[ActionQueue]:
        """
        Create an action queue prompt for new niches.
        Returns the created ActionQueue or None if a prompt already exists.
        """
        # Check for existing prompt
        existing_prompt = self.db.query(ActionQueue).filter(
            ActionQueue.status == 'pending',
            ActionQueue.action_type == 'new_niche_prompt'
        ).first()
        
        if existing_prompt:
            return None
        
        # Get recent niches for context
        from sqlalchemy import desc
        recent_niches = self.db.query(NicheDiscovery).order_by(
            desc(NicheDiscovery.created_at)
        ).limit(5).all()
        
        context_data = {
            'recent_niches': [{'niche': n.niche, 'status': n.status} for n in recent_niches]
        }
        
        prompt = ActionQueue(
            action_type='new_niche_prompt',
            priority=5,
            status='pending',
            title='Agent Needs New Niches',
            description='The auto-scraping agent has exhausted all available niches. Please provide new niche suggestions or allow the agent to discover more.',
            prompt='Please provide one or more new niches for the agent to scrape. You can:\n\n1. Enter specific niche names (e.g., "Vintage Camera Manuals", "Motorcycle Repair Guides")\n2. Let the agent discover new niches automatically using AI\n3. Provide both specific niches and allow AI discovery\n\nWhat would you like to do?',
            input_type='text',
            input_options=json.dumps([
                {'value': 'auto_discover', 'label': 'Let AI discover new niches'},
                {'value': 'manual_input', 'label': 'I will provide specific niches'}
            ]),
            context=json.dumps(context_data)
        )
        
        self.db.add(prompt)
        self.db.commit()
        self.db.refresh(prompt)
        
        self.log('prompt_created', 'completed', f'Created new niche prompt (ID: {prompt.id})')
        
        return prompt

    def _create_refine_config_prompt(self, known_niches: List[NicheDiscovery]) -> Optional[ActionQueue]:
        """
        Create an action queue prompt for refining scrape configurations for known niches.
        Returns the created ActionQueue or None if a prompt already exists.
        """
        # Check for existing prompt
        existing_prompt = self.db.query(ActionQueue).filter(
            ActionQueue.status == 'pending',
            ActionQueue.action_type == 'refine_config_prompt'
        ).first()
        
        if existing_prompt:
            return None
        
        if not known_niches:
            return None
        
        # Group niches by status and get some examples
        exhausted_niches = [n for n in known_niches if n.status == 'exhausted'][:3]
        scraped_niches = [n for n in known_niches if n.status in ['job_created', 'scraping', 'evaluated']][:3]
        
        context_data = {
            'exhausted_niches': [{'niche': n.niche, 'manuals_found': n.manuals_found} for n in exhausted_niches],
            'scraped_niches': [{'niche': n.niche, 'manuals_found': n.manuals_found} for n in scraped_niches],
            'total_niches': len(known_niches)
        }
        
        prompt_text = 'The agent has several known niches that may benefit from refined scrape configurations to find more files.\n\n'
        
        if exhausted_niches:
            prompt_text += f'Exhausted niches (no new results):\n'
            for n in exhausted_niches:
                prompt_text += f'  - {n.niche} (found {n.manuals_found} manuals)\n'
            prompt_text += '\n'
        
        if scraped_niches:
            prompt_text += f'Recently scraped niches:\n'
            for n in scraped_niches:
                prompt_text += f'  - {n.niche} (found {n.manuals_found} manuals)\n'
            prompt_text += '\n'
        
        prompt_text += 'Would you like to:\n\n1. Refine search queries for specific niches\n2. Add new sites to search for specific niches\n3. Adjust keywords or filters\n4. Skip for now and provide new niches instead'
        
        prompt = ActionQueue(
            action_type='refine_config_prompt',
            priority=4,
            status='pending',
            title='Refine Scrape Configurations for Known Niches',
            description='Some known niches may benefit from refined configurations to discover more files.',
            prompt=prompt_text,
            input_type='text',
            input_options=json.dumps([
                {'value': 'refine_queries', 'label': 'Refine search queries'},
                {'value': 'add_sites', 'label': 'Add new sites to search'},
                {'value': 'adjust_keywords', 'label': 'Adjust keywords/filters'},
                {'value': 'skip', 'label': 'Skip - provide new niches instead'}
            ]),
            context=json.dumps(context_data)
        )
        
        self.db.add(prompt)
        self.db.commit()
        self.db.refresh(prompt)
        
        self.log('prompt_created', 'completed', f'Created refine config prompt (ID: {prompt.id})')
        
        return prompt

    def _handle_idle_state(self, running_jobs: int, pending_manuals: int, available_niches: List[NicheDiscovery]) -> Dict:
        """
        Handle the idle state by prompting for new niches or refined configurations.
        
        Returns a dict with:
        - prompted: bool - whether a prompt was created
        - prompt_type: str - type of prompt created ('new_niche' or 'refine_config')
        - prompt_id: int - ID of the created prompt
        """
        result = {
            'prompted': False,
            'prompt_type': None,
            'prompt_id': None
        }
        
        if not self._should_prompt_for_input(running_jobs, pending_manuals, available_niches):
            return result
        
        # Get all known niches for context
        all_niches = self.db.query(NicheDiscovery).all()
        
        # Decide which type of prompt to create
        # If we have exhausted niches, prompt for refinement first
        exhausted_count = sum(1 for n in all_niches if n.status == 'exhausted')
        
        if exhausted_count > 0 and len(all_niches) > 3:
            # Prompt for refining configurations
            prompt = self._create_refine_config_prompt(all_niches)
            if prompt:
                result['prompted'] = True
                result['prompt_type'] = 'refine_config'
                result['prompt_id'] = prompt.id
        else:
            # Prompt for new niches
            prompt = self._create_niche_prompt()
            if prompt:
                result['prompted'] = True
                result['prompt_type'] = 'new_niche'
                result['prompt_id'] = prompt.id
        
        return result

    def process_action_response(self, action_id: int, response: str):
        """
        Process a response to an action and resume work.
        
        Handles responses for:
        - new_niche_prompt: User provides new niches or triggers AI discovery
        - refine_config_prompt: User provides refined configurations for known niches
        """
        action = self.db.query(ActionQueue).filter(ActionQueue.id == action_id).first()
        
        if not action:
            self.log('action_response', 'failed', f'Action {action_id} not found')
            return
        
        self.log('action_response', 'started', f'Processing response for action {action_id} (type: {action.action_type})')
        
        try:
            if action.action_type == 'new_niche_prompt':
                self._process_niche_prompt_response(action, response)
            elif action.action_type == 'refine_config_prompt':
                self._process_refine_config_response(action, response)
            else:
                self.log('action_response', 'warning', f'Unknown action type: {action.action_type}')
                
            self.log('action_response', 'completed', f'Action {action_id} processed successfully')
            
        except Exception as e:
            self.log('action_response', 'failed', f'Error processing action {action_id}: {str(e)}')

    def _process_niche_prompt_response(self, action: ActionQueue, response: str):
        """
        Process response to new niche prompt.
        
        Response can be:
        - 'auto_discover': Trigger AI niche discovery
        - 'manual_input': User provides specific niche names (comma-separated)
        """
        response_lower = response.lower().strip()
        
        if response_lower == 'auto_discover':
            # Trigger AI niche discovery
            self.log('niche_response', 'started', 'Triggering AI niche discovery')
            niches = self._discover_niches()
            self.log('niche_response', 'completed', f'AI discovered {len(niches)} new niches')
            
        elif response_lower == 'manual_input' or ',' in response:
            # Parse manual niche input
            niche_names = [n.strip() for n in response.split(',') if n.strip()]
            
            if niche_names and response_lower != 'manual_input':
                # Create niches from user input
                for niche_name in niche_names:
                    existing = self.db.query(NicheDiscovery).filter(
                        NicheDiscovery.niche == niche_name
                    ).first()
                    
                    if not existing:
                        niche = NicheDiscovery(
                            niche=niche_name,
                            description=f"Service manuals and repair guides for {niche_name}",
                            search_query=f"{niche_name} manual filetype:pdf",
                            potential_price='4.99-9.99',
                            demand_level='medium',
                            competition_level='medium',
                            keywords=json.dumps([]),
                            sites_to_search=json.dumps([]),
                            reason='User-provided niche'
                        )
                        self.db.add(niche)
                
                self.db.commit()
                self.log('niche_response', 'completed', f'Created {len(niche_names)} niches from user input')
            else:
                # User selected manual_input but didn't provide niches
                self.log('niche_response', 'warning', 'User selected manual input but no niches provided')
        else:
            # Single niche name provided
            existing = self.db.query(NicheDiscovery).filter(
                NicheDiscovery.niche == response
            ).first()
            
            if not existing:
                niche = NicheDiscovery(
                    niche=response,
                    description=f"Service manuals and repair guides for {response}",
                    search_query=f"{response} manual filetype:pdf",
                    potential_price='4.99-9.99',
                    demand_level='medium',
                    competition_level='medium',
                    keywords=json.dumps([]),
                    sites_to_search=json.dumps([]),
                    reason='User-provided niche'
                )
                self.db.add(niche)
                self.db.commit()
                self.log('niche_response', 'completed', f'Created niche: {response}')

    def _process_refine_config_response(self, action: ActionQueue, response: str):
        """
        Process response to refine config prompt.
        
        Response can be:
        - 'refine_queries': User provides refined search queries
        - 'add_sites': User provides new sites to search
        - 'adjust_keywords': User provides adjusted keywords
        - 'skip': User wants to skip and provide new niches instead
        """
        response_lower = response.lower().strip()
        
        if response_lower == 'skip':
            # Trigger new niche prompt
            self.log('refine_response', 'info', 'User skipped refinement, creating new niche prompt')
            self._create_niche_prompt()
            
        elif response_lower == 'refine_queries':
            # User would provide refined queries (for now, just log)
            self.log('refine_response', 'info', f'User wants to refine queries: {response}')
            # TODO: Implement query refinement logic
            
        elif response_lower == 'add_sites':
            # User would provide new sites (for now, just log)
            self.log('refine_response', 'info', f'User wants to add sites: {response}')
            # TODO: Implement site addition logic
            
        elif response_lower == 'adjust_keywords':
            # User would provide adjusted keywords (for now, just log)
            self.log('refine_response', 'info', f'User wants to adjust keywords: {response}')
            # TODO: Implement keyword adjustment logic
        else:
            # Try to parse as JSON for more complex responses
            try:
                data = json.loads(response)
                self.log('refine_response', 'info', f'Received complex refine response: {data}')
                # TODO: Implement complex response handling
            except json.JSONDecodeError:
                self.log('refine_response', 'warning', f'Unrecognized refine response: {response}')

    def _create_job_from_niche(self, niche: NicheDiscovery) -> Dict:
        """Create a scrape job from a niche"""
        from app.database import ScrapeJob
        import json

        # Check if we already have a similar job
        existing_job = self.db.query(ScrapeJob).filter(
            ScrapeJob.name.ilike(f"%{niche.niche[:30]}%")
        ).first()

        if existing_job:
            return {
                'created': False,
                'reason': f"Similar job already exists: {existing_job.name}"
            }

        # Check if this niche has been scraped recently
        from datetime import datetime, timedelta
        recent_niche_scrape = self.db.query(NicheDiscovery).filter(
            NicheDiscovery.niche == niche.niche,
            NicheDiscovery.last_scraped_at > datetime.utcnow() - timedelta(days=7)
        ).first()

        if recent_niche_scrape:
            return {
                'created': False,
                'reason': f"Niche '{niche.niche}' was scraped recently"
            }

        try:
            # Get next queue position
            from app.api.scrape_routes import get_queue_position
            queue_position = get_queue_position(self.db)

            # Create scrape job
            keywords = json.loads(niche.keywords) if niche.keywords else []
            sites = json.loads(niche.sites_to_search) if niche.sites_to_search else []

            # Note: If no sites are specified, the multi_site_scraper will use
            # DuckDuckGo to dynamically discover sites based on the search query

            job = ScrapeJob(
                name=f"Auto: {niche.niche}",
                source_type='multi_site',
                query=niche.search_query or niche.niche,
                search_terms=','.join([niche.niche] + keywords[:5]) if keywords else niche.niche,
                exclude_terms='preview,operator,user manual,quick start,brochure,catalog',
                sites=json.dumps(sites) if sites else None,  # None triggers DuckDuckGo site discovery
                max_results=100,
                equipment_type=niche.niche.split()[0] if niche.niche else None,
                autostart_enabled=True,
                status='queued',
                queue_position=queue_position
            )

            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)

            # Update niche
            niche.scrape_job_id = job.id
            niche.status = 'job_created'
            niche.last_scraped_at = datetime.utcnow()
            self.db.commit()

            self.log('job_created', 'completed',
                    f"Created scrape job for niche: {niche.niche}",
                    {'job_id': job.id, 'niche': niche.niche})

            # Start the job immediately if autostart is enabled and no job is currently running
            if job.autostart_enabled:
                running_job = self.db.query(ScrapeJob).filter(ScrapeJob.status == 'running').first()
                if not running_job:
                    self.log('job_start', 'started', f"Starting job {job.id} immediately")
                    # Start job asynchronously
                    import threading
                    def auto_start():
                        from app.api.scrape_routes import start_next_queued_job
                        db_local = SessionLocal()
                        try:
                            start_next_queued_job(db_local, previous_job_autostart=False)
                        except Exception as e:
                            self.log('job_start', 'failed', f"Error starting job {job.id}: {str(e)}")
                        finally:
                            db_local.close()
                    
                    thread = threading.Thread(target=auto_start, daemon=True)
                    thread.start()

            return {
                'created': True,
                'reason': f"Created job {job.id} for {niche.niche}"
            }

        except Exception as e:
            self.log('job_created', 'failed', f"Error creating job for {niche.niche}: {str(e)}")
            return {
                'created': False,
                'reason': f"Error: {str(e)}"
            }

    def _evaluate_pending_manuals(self, limit: int = 10) -> int:
        """Evaluate pending manuals and return count of suitable ones"""
        from app.passive_income.database import MarketResearch

        manuals = self.db.query(Manual).filter(
            Manual.status == 'pending'
        ).limit(limit).all()

        suitable_count = 0

        for manual in manuals:
            # Check if we already have market research
            existing_research = self.db.query(MarketResearch).filter(
                MarketResearch.manual_id == manual.id
            ).first()

            if existing_research:
                # Use existing research
                suitable = existing_research.suitable == True
            else:
                # Evaluate using AI
                suitable = self._evaluate_manual_with_ai(manual)

            if suitable:
                suitable_count += 1

        return suitable_count

    def _evaluate_manual_with_ai(self, manual: Manual) -> bool:
        """Evaluate a manual using AI to determine if it's suitable for listing"""
        from groq import Groq
        from app.config import get_settings

        settings = get_settings()
        if not settings.groq_api_key:
            return False

        client = Groq(api_key=settings.groq_api_key)

        # Prepare evaluation prompt
        prompt = f"""Evaluate this PDF manual for passive income potential:

Title: {manual.title or 'Unknown'}
Source URL: {manual.source_url}
Equipment Type: {manual.equipment_type or 'Unknown'}
Manufacturer: {manual.manufacturer or 'Unknown'}
File Size: {manual.file_size or 'Unknown'} MB

Is this a genuine service/repair manual (not a preview, user guide, or brochure)?
Is there market demand for this type of content?
Is the quality likely to be good enough to sell?
Are there any legal concerns (copyright, trademark)?
What price point would work?

Return ONLY a JSON object with this format:
{{
  "suitable": true/false,
  "confidence": 0.0-1.0,
  "reason": "brief explanation",
  "suggested_price": "4.99-9.99",
  "seo_title": "optimized title for listing",
  "target_audience": "who would buy this",
  "keywords": ["keyword1", "keyword2"],
  "concerns": ["any issues to note"],
  "market_analysis": {{
    "demand": "low/medium/high",
    "competition": "low/medium/high",
    "price_range": "3.99-7.99"
  }}
}}"""

        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "Evaluate this manual"}
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            response_text = completion.choices[0].message.content
            print(f"[DEBUG] AI evaluation response: {response_text[:500]}...")
            result = json.loads(response_text)

            # Handle if it's wrapped in a key
            if isinstance(result, dict):
                # Try common wrapper keys
                for key in ['niches', 'niche_suggestions', 'suggestions', 'results', 'items']:
                    if key in result and isinstance(result[key], list):
                        result = result[key]
                        break
                else:
                    # Check if the dict itself looks like a single niche
                    if 'niche' in result or 'description' in result:
                        result = [result]

            if not isinstance(result, list):
                result = []

            suitable = False
            confidence = 0.0
            reason = "Could not evaluate"

            if isinstance(result, list) and len(result) > 0:
                item = result[0]
                suitable = item.get('suitable', False)
                confidence = item.get('confidence', 0.0)
                eval_reason = item.get('reason', 'Could not evaluate')
                suitable = suitable and confidence > 0.5

            return suitable

        except Exception as e:
            print(f"[DEBUG] Error evaluating manual with AI: {str(e)}")
            return False

    def _create_listings_for_manuals(self, count: int) -> int:
        """Create Etsy listings for suitable manuals"""
        from app.passive_income.database import PlatformListing

        # Get suitable manuals
        from sqlalchemy import desc
        manuals = self.db.query(Manual).filter(
            Manual.status == 'pending'
        ).order_by(desc(Manual.created_at)).limit(count).all()

        listings_created = 0

        for manual in manuals:
            # Check if we already have market research
            existing_research = self.db.query(MarketResearch).filter(
                MarketResearch.manual_id == manual.id
            ).first()

            if existing_research and existing_research.suitable:
                # Create listing
                listing = PlatformListing(
                    manual_id=manual.id,
                    platform_id=1,  # Etsy
                    status='draft',
                    created_at=datetime.utcnow()
                )
                self.db.add(listing)
                listings_created += 1

        self.db.commit()
        return listings_created

    def discover_niches(self) -> List[Dict]:
        """Public method to discover niches"""
        return self._discover_niches()

    def _discover_niches(self) -> List[Dict]:
        """Use AI to discover profitable niches for passive income"""
        from groq import Groq
        from app.config import get_settings

        settings = get_settings()
        if not settings.groq_api_key:
            self.log('niche_discovery', 'failed', 'GROQ_API_KEY not configured')
            return []

        # Check cache - but skip caching if we're idle and have no available niches
        last_discovery = self.get_setting('last_niche_discovery')
        discovery_interval = int(self.get_setting('niche_discovery_interval_hours', '1'))
        last_time = datetime.fromisoformat(last_discovery) if last_discovery else None
        
        # Check if we should force discovery (idle state with no work)
        force_discovery = False
        if last_discovery:
            try:
                last_time = datetime.fromisoformat(last_discovery)
                # If it's been more than the interval, allow discovery
                if datetime.utcnow() - last_time >= timedelta(hours=discovery_interval):
                    force_discovery = True
                else:
                    # Check cache
                    cached = self.get_setting('cached_niches')
                    if cached:
                        cached_niches = json.loads(cached)
                        # If cache is empty, force discovery
                        if not cached_niches or len(cached_niches) == 0:
                            force_discovery = True
                        else:
                            return cached_niches
            except:
                force_discovery = True
        else:
            # No previous discovery, force it
            force_discovery = True
        
        if not force_discovery:
            return []

        self.log('niche_discovery', 'started', 'Discovering new profitable niches')

        try:
            from groq import Groq
            from app.config import get_settings

            settings = get_settings()
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
            print(f"[DEBUG] AI niche discovery response: {response_text[:500]}...")
            niches = json.loads(response_text)

            # Handle if it's wrapped in a key (common when using json_object mode)
            if isinstance(niches, dict):
                # Try common wrapper keys
                for key in ['niches', 'niche_suggestions', 'suggestions', 'results', 'items']:
                    if key in niches and isinstance(niches[key], list):
                        niches = niches[key]
                        break
            else:
                # Check if the dict itself looks like a single niche
                if 'niche' in niches or 'description' in niches:
                    niches = [niches]

            if not isinstance(niches, list):
                niches = []

            # Store in database and cache
            for niche_data in niches:
                if not isinstance(niche_data, dict):
                    continue

                # Extract and validate fields - ensure description is never empty
                niche_name = niche_data.get('niche')
                if not niche_name:
                    continue

                description = niche_data.get('description') or niche_data.get('reason', '')
                if not description:
                    description = f"Service manuals and repair guides for {niche_name}"

                print(f"[DEBUG] Storing niche: {niche_name}, desc: {description[:50] if description else 'NONE'}")

                existing = self.db.query(NicheDiscovery).filter(
                    NicheDiscovery.niche == niche_name
                ).first()

                if not existing:
                    niche = NicheDiscovery(
                        niche=niche_name,
                        description=description,
                        search_query=niche_data.get('search_query') or niche_name,
                        potential_price=niche_data.get('potential_price', '4.99-9.99'),
                        demand_level=niche_data.get('demand_level', 'medium') or 'medium',
                        competition_level=niche_data.get('competition_level', 'medium') or 'medium',
                        keywords=json.dumps(niche_data.get('keywords', []) or []),
                        sites_to_search=json.dumps(niche_data.get('sites_to_search', []) or []),
                        reason=niche_data.get('reason') or description
                    )
                    self.db.add(niche)
                    print(f"[DEBUG] Created niche: {niche_name} with description: {description[:50]}")

            self.db.commit()

            # Cache results
            self.set_setting('cached_niches', json.dumps(niches))
            self.set_setting('last_niche_discovery', datetime.utcnow().isoformat())

            self.log('niche_discovery', 'completed', f'Discovered {len(niches)} niches')

            return niches

        except Exception as e:
            self.log('niche_discovery', 'failed', f'Error discovering niches: {str(e)}')
            return []
