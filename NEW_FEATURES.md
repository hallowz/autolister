# AutoLister - New Features

## Database Reset & Scraped Sites Tracking

### Overview

Two new features have been added to help manage the application:

1. **Database Reset** - Clear all data and start fresh
2. **Scraped Sites Tracking** - Track which sites have been scraped to avoid duplicates

### Database Reset

**API Endpoint:** `POST /api/database/reset`

**What it does:**
- Deletes all processing logs
- Deletes all Etsy listings
- Deletes all manuals
- Deletes all scraped sites tracking
- Resets the database to a clean state

**Use cases:**
- Start fresh after testing
- Clear out bad data
- Reset after configuration changes
- Clean up before production deployment

**How to use:**
```bash
# Via API
curl -X POST http://localhost:8000/api/database/reset

# Via dashboard
# (Button to be added to dashboard UI)
```

**Warning:** This is destructive and cannot be undone!

### Scraped Sites Tracking

**New Database Model:** `ScrapedSite`

Tracks which sites have been scraped to:
- Avoid scraping the same sites repeatedly
- Identify exhausted sources (no more results)
- Track scrape frequency and history
- Block problematic sites

**API Endpoints:**

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/scraped-sites` | Get all tracked sites |
| POST | `/api/scraped-sites` | Add a new site to tracking |
| DELETE | `/api/scraped-sites/{site_id}` | Delete a tracked site |
| POST | `/api/scraped-sites/{site_id}/mark-exhausted` | Mark site as exhausted |

**Site Model Fields:**
- `id` - Unique identifier
- `url` - Full URL of the site
- `domain` - Domain name (extracted from URL)
- `first_scraped_at` - When site was first scraped
- `last_scraped_at` - Most recent scrape time
- `scrape_count` - Number of times site has been scraped
- `status` - 'active', 'exhausted', 'blocked'
- `notes` - Additional notes about the site

### How It Works

**1. Site Discovery:**
- When scraping job runs, each unique URL is tracked
- Domain is extracted from URL
- Initial scrape time is recorded

**2. Site Updates:**
- If same URL is scraped again, it updates the existing record
- Scrape count is incremented
- Last scraped time is updated

**3. Exhaustion Tracking:**
- Mark sites as 'exhausted' when no more results found
- Add notes explaining why (e.g., "No more results")
- Prevents future scraping of exhausted sites

**4. Site Management:**
- View all tracked sites via API
- Delete sites that are no longer relevant
- Block problematic sites (future feature)

### Benefits

✅ **Avoid Duplicate Scraping** - Don't waste time on same sites
✅ **Identify Exhausted Sources** - Skip sites with no results
✅ **Track Scraping History** - See when and how often sites were scraped
✅ **Better Resource Management** - Focus on productive sources
✅ **Data Analytics** - Understand which sites yield the most results

### Example Usage

**Add a site to tracking:**
```bash
curl -X POST http://localhost:8000/api/scraped-sites \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://manualslib.com",
    "notes": "Manual repository - good source"
  }'
```

**Get all tracked sites:**
```bash
curl http://localhost:8000/api/scraped-sites
```

**Mark site as exhausted:**
```bash
curl -X POST http://localhost:8000/api/scraped-sites/123/mark-exhausted
```

**Delete a site:**
```bash
curl -X DELETE http://localhost:8000/api/scraped-sites/123
```

### Integration with Scrapers

The scraped sites tracking can be integrated with scrapers to:

1. **Check Before Scraping:**
   ```python
   # Check if site has been scraped recently
   existing_site = db.query(ScrapedSite).filter(
       ScrapedSite.url == url_to_scrape,
       ScrapedSite.status != 'exhausted'
   ).first()
   
   if existing_site:
       # Skip this site
       continue
   ```

2. **Update After Scraping:**
   ```python
   # Record that we scraped this site
   scraped_site = ScrapedSite(
       url=site_url,
       domain=extract_domain(site_url),
       status='active'
   )
   db.add(scraped_site)
   db.commit()
   ```

3. **Mark Exhausted:**
   ```python
   # When no results found, mark as exhausted
   if not results:
       scraped_site.status = 'exhausted'
       scraped_site.notes = 'No more results in last scrape'
       db.commit()
   ```

### Dashboard Integration

**Future enhancements to dashboard:**

1. **Add "Scraped Sites" tab** to view and manage tracked sites
2. **Add "Reset Database" button** with confirmation dialog
3. **Show site statistics** (total sites, active, exhausted, blocked)
4. **Add site management** (delete, block, unblock)
5. **Scraping history** - timeline of when each site was scraped

### Files Modified

- [`app/database.py`](app/database.py:1) - Added `ScrapedSite` model
- [`app/api/routes.py`](app/api/routes.py:1) - Added database reset and scraped sites endpoints

### Next Steps

1. **Test the new endpoints** - Verify they work correctly
2. **Add dashboard UI** - Create buttons for reset and sites management
3. **Integrate with scrapers** - Check tracking before scraping
4. **Add analytics** - Track which sites yield the most results
5. **Update documentation** - Add examples and usage guides

The database reset and scraped sites tracking features are now available!
