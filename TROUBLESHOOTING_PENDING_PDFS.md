# Troubleshooting Guide: Pending PDFs Not Showing in Dashboard

## Problem
The multi-site scraper is correctly saving PDFs to the database with `status='pending'`, but they are not appearing in the dashboard's pending section.

## ⚠️ CRITICAL ISSUE: Database Lock

**Recent logs show a database lock issue that prevents pending manuals from being saved!**

### Symptoms:
- Error: `sqlite3.OperationalError: database is locked`
- Error: `UNIQUE constraint failed: scraped_sites.url`
- Scraper finds PDFs (e.g., "found 278 PDFs total") but they don't appear in database
- API endpoints return 500 errors when trying to read from database

### Root Cause:
The multi-site scraper holds a write lock on the database for too long, blocking the API from reading. When the scraper encounters an error (like the UNIQUE constraint error), the transaction is rolled back and no manuals are saved.

### Solution Applied:
1. **Fixed database concurrency** - Added WAL mode and timeout settings to [`app/database.py`](app/database.py:17)
2. **Fixed duplicate handling** - Improved error handling for scraped sites in [`app/tasks/jobs.py`](app/tasks/jobs.py:185)
3. **Separated transactions** - Split scraped site tracking and manual saving to reduce lock time

### Immediate Actions Required:
1. **Restart the application** to apply database fixes:
   ```bash
   sudo systemctl restart autolister
   ```

2. **Run the scraper again** to save the PDFs:
   ```bash
   # Either via the dashboard or manually:
   python3 scripts/manual_scrape.py
   ```

3. **Check for uncommitted data**:
   ```bash
   python3 scripts/check_uncommitted.py
   ```

## Diagnosis Steps

### Step 1: Check the Database Directly
Run the diagnostic script on the Raspberry Pi:

```bash
cd /path/to/AutoLister
python3 scripts/diagnose_pending.py
```

This will show:
- Database path and existence
- Total manuals count
- Manuals grouped by status
- Details of pending manuals
- Multi-site scraper results

### Step 2: Test the API Endpoint
Run the API test script on the Raspberry Pi:

```bash
cd /path/to/AutoLister
python3 scripts/test_pending_api.py
```

This will test the `/api/pending` endpoint and show:
- Connection status
- Response code
- Actual data returned

### Step 3: Check Browser Network Tab
1. Open the dashboard in your browser
2. Press F12 to open Developer Tools
3. Go to the Network tab
4. Refresh the page
5. Look for the `/api/pending` request
6. Check:
   - Status code (should be 200)
   - Response data (should contain pending manuals)
   - Any error messages

### Step 4: Check Application Logs
On the Raspberry Pi, check the application logs:

```bash
# If using systemd
journalctl -u autolister -f

# Or check log file
tail -f ./logs/autolister.log
```

Look for:
- Database connection errors
- API request errors
- Any exceptions related to pending manuals

## Common Issues and Solutions

### Issue 1: Database File Mismatch
**Symptoms:** Diagnostic script shows 0 pending manuals, but scraper says it's saving them.

**Possible Causes:**
- Application is using a different database file than expected
- Multiple database files exist

**Solution:**
1. Check the `.env` file for `database_path` setting
2. Verify the database path matches the one being used by the scraper
3. Check for multiple `.db` files:
   ```bash
   find . -name "*.db" -type f
   ```

### Issue 2: Application Needs Restart
**Symptoms:** Database has pending manuals, but API returns empty.

**Possible Causes:**
- Application was running before database was updated
- Database connection is stale

**Solution:**
1. Restart the application on the Raspberry Pi:
   ```bash
   # If using systemd
   sudo systemctl restart autolister
   
   # Or if running directly
   # Stop and restart the process
   ```

### Issue 3: Status Value Mismatch
**Symptoms:** Manuals exist but not with `status='pending'`.

**Possible Causes:**
- Scraper is saving with a different status value
- Status field has extra whitespace or different case

**Solution:**
1. Check the scraper code in `app/scrapers/multi_site_scraper.py`
2. Verify the exact status value being saved
3. Check for case sensitivity (should be lowercase 'pending')

### Issue 4: API Route Not Registered
**Symptoms:** API endpoint returns 404.

**Possible Causes:**
- API router not properly included in main app
- Route path is different

**Solution:**
1. Check `app/main.py` to ensure the API router is included:
   ```python
   from app.api.routes import router as api_router
   app.include_router(api_router, prefix="/api")
   ```

### Issue 5: CORS or Network Issues
**Symptoms:** Browser shows network errors when calling API.

**Possible Causes:**
- CORS not configured
- Firewall blocking requests
- Wrong host/port configuration

**Solution:**
1. Check `app/main.py` for CORS configuration
2. Verify `dashboard_host` and `dashboard_port` in `.env`
3. Ensure the application is accessible from your browser

## Manual Database Query (Advanced)

If you have access to sqlite3 on the Pi, you can query directly:

```bash
sqlite3 ./data/autolister.db "SELECT id, source_url, title, status, created_at FROM manuals WHERE status='pending' ORDER BY created_at DESC LIMIT 10;"
```

## Expected Behavior

1. **Scraper saves manual:**
   - Multi-site scraper finds PDF
   - Saves to database with `status='pending'`
   - Sets `source_type='multi_site'`

2. **Dashboard displays manual:**
   - Dashboard calls `/api/pending`
   - API returns manuals with `status='pending'`
   - JavaScript renders the manual cards

3. **User approves manual:**
   - User clicks "Approve" button
   - Status changes to `status='approved'`
   - Manual moves to processing queue

## Files to Check

- `app/scrapers/multi_site_scraper.py` - Scraper implementation
- `app/api/routes.py` - API endpoint (line 313)
- `app/static/js/dashboard.js` - Dashboard JavaScript (line 79)
- `app/database.py` - Database models
- `app/config.py` - Configuration settings
- `.env` - Environment variables

## Getting Help

If you've tried all these steps and still have issues:

1. Run both diagnostic scripts and save the output
2. Check browser console for JavaScript errors
3. Check application logs for server errors
4. Verify the multi-site scraper is actually running and finding PDFs

## Quick Verification Checklist

- [ ] Database file exists at correct path
- [ ] Application is running on the Pi
- [ ] `/api/pending` returns 200 status
- [ ] Response contains pending manuals data
- [ ] Browser console shows no errors
- [ ] Dashboard JavaScript is loading correctly
- [ ] Status value is exactly 'pending' (lowercase)
