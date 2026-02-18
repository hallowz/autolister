# Passive Income Dashboard - Integration Guide

## Overview

The Passive Income Dashboard extends AutoLister with autonomous multi-platform listing capabilities. It enables you to:

- **Multi-Platform Listing**: Automatically list processed PDFs on multiple platforms (Etsy, Gumroad, Payhip, etc.)
- **Autonomous Operation**: Run background tasks that list, sync, and manage listings without manual intervention
- **Action Queue**: Handle situations requiring human input (account setup, CAPTCHA, manual listing)
- **Revenue Tracking**: Monitor sales and revenue across all platforms
- **SEO Optimization**: Auto-generate platform-specific SEO titles and tags

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Passive Income Dashboard                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │  Platforms  │ │  Listings   │ │   Actions   │ │   Revenue   │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Autonomous Agent                                  │
│  - Auto-list processed manuals                                       │
│  - Sync sales/revenue data                                          │
│  - Handle action timeouts                                           │
│  - Auto-adjust pricing                                              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Platform Integrations                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │  Etsy   │ │ Gumroad │ │ Payhip  │ │  eBay   │ │  More   │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

## Database Models

### Platform
Tracks listing platforms and their configuration.

```python
class Platform:
    name: str              # 'etsy', 'gumroad', 'payhip'
    display_name: str      # 'Etsy', 'Gumroad', 'Payhip'
    platform_type: str     # 'digital_download', 'marketplace'
    is_active: bool        # Whether to use this platform
    is_free: bool          # No upfront costs
    supports_api_listing: bool
    credentials: str       # JSON encrypted credentials
    credentials_status: str # 'not_configured', 'pending', 'verified', 'error'
    total_revenue: float
    listing_count: int
```

### PlatformListing
Tracks individual listings across platforms.

```python
class PlatformListing:
    manual_id: int         # Link to Manual
    platform_id: int       # Link to Platform
    title: str             # SEO-optimized title
    price: float
    status: str            # 'pending', 'listed', 'active', 'error'
    platform_listing_id: str # External platform ID
    platform_url: str      # URL to listing
    sales: int
    revenue: float
```

### ActionQueue
Tracks actions requiring human intervention.

```python
class ActionQueue:
    action_type: str       # 'account_setup', 'verification', 'manual_listing'
    title: str
    description: str
    prompt: str            # What to ask the user
    input_type: str        # 'text', 'url', 'confirmation'
    status: str            # 'pending', 'completed', 'cancelled'
    user_response: str
```

### Revenue
Tracks sales and revenue.

```python
class Revenue:
    listing_id: int
    platform_id: int
    transaction_id: str
    amount: float
    fee: float
    net_amount: float
    transaction_date: datetime
```

## API Endpoints

### Platforms
- `GET /api/passive-income/platforms` - List all platforms
- `POST /api/passive-income/platforms/{id}/configure` - Configure credentials
- `POST /api/passive-income/platforms/{id}/activate` - Activate platform
- `POST /api/passive-income/platforms/{id}/deactivate` - Deactivate platform
- `POST /api/passive-income/platforms/{id}/sync` - Sync sales data

### Dashboard Stats
- `GET /api/passive-income/stats` - Get dashboard statistics
- `GET /api/passive-income/revenue` - Get revenue summary

### Action Queue
- `GET /api/passive-income/actions` - List pending actions
- `POST /api/passive-income/actions/{id}/resolve` - Resolve an action
- `POST /api/passive-income/actions/{id}/cancel` - Cancel an action

### Listings
- `GET /api/passive-income/listings` - List all platform listings
- `POST /api/passive-income/listings/{id}/retry` - Retry failed listing

### Agent Control
- `POST /api/passive-income/agent/run` - Run agent cycle manually

## Celery Tasks

Add these to your Celery beat schedule:

```python
CELERYBEAT_SCHEDULE = {
    'run-passive-income-agent': {
        'task': 'app.tasks.jobs.run_passive_income_agent',
        'schedule': 1800.0,  # Every 30 minutes
    },
    'sync-platform-sales': {
        'task': 'app.tasks.jobs.sync_platform_sales',
        'schedule': 3600.0,  # Every hour
    },
    'auto-list-processed-manuals': {
        'task': 'app.tasks.jobs.auto_list_processed_manuals',
        'schedule': 600.0,  # Every 10 minutes
    },
}
```

## Platform Configuration

### Etsy
```python
credentials = {
    'api_key': 'your-api-key',
    'api_secret': 'your-api-secret',
    'access_token': 'your-access-token',
    'shop_id': 'your-shop-id'
}
```

### Gumroad
```python
credentials = {
    'api_token': 'your-api-token'
}
```

### Payhip
Payhip does not have a public API, so it requires manual listing. The system will create action queue items when listings need to be created.

## Frontend Dashboard

Access the dashboard at: `http://your-server:8000/passive-income`

Features:
- **Platform Cards**: View status, revenue, listing count for each platform
- **Action Queue**: View and respond to actions requiring human input
- **Listings Table**: View all cross-platform listings with status
- **Revenue Analytics**: View revenue by platform

## Autonomous Agent

The agent runs these tasks automatically:

1. **Process Pending Listings**
   - Finds processed manuals without platform listings
   - Lists them on all active platforms with API support

2. **Sync Platform Data**
   - Pulls sales/revenue data from connected platforms
   - Updates revenue records and listing stats

3. **Check Action Timeouts**
   - Marks expired actions as timed out

4. **Auto-Adjust Pricing**
   - Reduces prices for listings with views but no sales

## Adding New Platforms

1. Create a new platform class in `app/passive_income/platforms/`:

```python
from app.passive_income.platforms.base import BasePlatform, PlatformStatus, ListingResult

class NewPlatform(BasePlatform):
    name = "newplatform"
    display_name = "New Platform"
    supports_api_listing = True  # or False
    
    def check_status(self) -> PlatformStatus:
        # Implement connection check
        pass
    
    def create_listing(self, title, description, price, ...) -> ListingResult:
        # Implement listing creation
        pass
    
    # Implement other required methods...
```

2. Register the platform in `app/passive_income/platforms/__init__.py`

3. Add default platform entry in `init_default_platforms()`

## Workflow Example

1. **Manual is processed** (status = 'processed')

2. **Agent runs** (every 30 minutes):
   - Finds processed manual
   - For each active platform:
     - Creates PlatformListing record
     - Attempts API listing
     - If success: Updates status to 'listed'
     - If needs auth: Creates action queue item
     - If manual required: Creates action queue item

3. **User handles action**:
   - Dashboard shows "Action Required" badge
   - User responds (provides credentials, confirms listing)
   - Agent resumes work

4. **Revenue tracking**:
   - Agent syncs sales data hourly
   - Revenue records created
   - Stats updated on dashboard

## Security Notes

- Platform credentials are stored as JSON in the database
- In production, encrypt credentials before storage
- Never expose API tokens in client-side code
- Use environment variables for sensitive configuration
