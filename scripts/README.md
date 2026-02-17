# Diagnostic Scripts for AutoLister

These scripts help diagnose issues with pending PDFs not showing in the dashboard.

## Quick Start

Run the full diagnostic to get a complete overview:

```bash
cd /path/to/AutoLister
python3 scripts/full_diagnostic.py
```

## Available Scripts

### 1. full_diagnostic.py
**Purpose:** Complete system diagnostic

**What it checks:**
- Database configuration and existence
- Total manuals count
- Manuals grouped by status and source type
- Pending manual details
- Multi-site scraper results
- Scraped sites tracking
- Potential issues (uppercase status, whitespace, duplicates)
- Recommendations

**Usage:**
```bash
python3 scripts/full_diagnostic.py
```

### 2. diagnose_pending.py
**Purpose:** Quick check of pending manuals

**What it checks:**
- Database path and existence
- Total manuals count
- Manuals by status
- Pending manual details with PDF file existence
- Multi-site scraper results

**Usage:**
```bash
python3 scripts/diagnose_pending.py
```

### 3. test_pending_api.py
**Purpose:** Test the `/api/pending` endpoint

**What it checks:**
- API endpoint connectivity
- Response status code
- Actual data returned by the API

**Usage:**
```bash
python3 scripts/test_pending_api.py
```

### 4. manual_scrape.py
**Purpose:** Manually trigger a multi-site scrape

**What it does:**
- Runs a multi-site scrape with configurable parameters
- Shows results found
- Checks database for duplicates
- Reports how many would be saved vs skipped

**Usage:**
```bash
python3 scripts/manual_scrape.py
```

**Note:** You may need to edit the `scraper_config` section at the top of the file to match your target sites and search terms.

### 5. check_uncommitted.py
**Purpose:** Check for manuals that might have been found but not committed due to database lock

**What it checks:**
- Total manuals in database
- Manuals by status and source type
- Multi-site scraper results
- Recently created manuals
- Scraped sites tracking

**Usage:**
```bash
python3 scripts/check_uncommitted.py
```

**When to use:** If you see "database is locked" errors in the logs or the scraper reports finding PDFs but none appear in the database.

## Troubleshooting Workflow

### Step 1: Run Full Diagnostic
```bash
python3 scripts/full_diagnostic.py
```

This will give you a complete picture of the system state.

### Step 2: Check API Endpoint
If the diagnostic shows pending manuals exist but they're not in the dashboard:
```bash
python3 scripts/test_pending_api.py
```

### Step 3: Test Scraper Manually
If no pending manuals exist:
```bash
python3 scripts/manual_scrape.py
```

### Step 4: Check Application Logs
```bash
# If using systemd
journalctl -u autolister -f

# Or check log file
tail -f ./logs/autolister.log
```

### Step 5: Check Browser Console
1. Open dashboard in browser
2. Press F12 to open Developer Tools
3. Go to Console tab
4. Look for JavaScript errors
5. Go to Network tab
6. Refresh the page
7. Check `/api/pending` request

## Common Issues

### Issue: No pending manuals in database
**Diagnosis:** `full_diagnostic.py` shows 0 pending manuals

**Possible causes:**
1. Multi-site scraper hasn't run
2. Scraper found no matching PDFs
3. All PDFs were skipped as duplicates
4. Scraper encountered errors

**Solution:**
1. Run `manual_scrape.py` to test the scraper
2. Check application logs for errors
3. Verify search terms match your target PDFs

### Issue: Pending manuals exist but API returns empty
**Diagnosis:** `full_diagnostic.py` shows pending manuals, but `test_pending_api.py` returns empty

**Possible causes:**
1. Application needs restart
2. Database connection issue
3. API route not registered

**Solution:**
1. Restart the application: `sudo systemctl restart autolister`
2. Check application logs for errors
3. Verify API is accessible

### Issue: API returns data but dashboard shows empty
**Diagnosis:** `test_pending_api.py` returns data, but dashboard shows "No pending manuals"

**Possible causes:**
1. JavaScript error
2. Browser caching
3. API endpoint path mismatch

**Solution:**
1. Check browser console for errors
2. Hard refresh browser (Ctrl+Shift+R)
3. Verify API_BASE in dashboard.js is '/api'

### Issue: Scraper finds PDFs but they're all skipped as duplicates
**Diagnosis:** `manual_scrape.py` shows all results as duplicates

**Possible causes:**
1. PDFs were already scraped before
2. URLs are being normalized incorrectly
3. Status was changed from 'pending' to something else

**Solution:**
1. Check the status of existing manuals with the same URLs
2. If needed, update status back to 'pending'
3. Consider clearing old data if it's stale

## Making Scripts Executable (Linux/Raspberry Pi)

```bash
chmod +x scripts/*.py
```

Then you can run them directly:
```bash
./scripts/full_diagnostic.py
```

## Getting Help

If you've tried all these steps and still have issues:

1. Save the output of `full_diagnostic.py`
2. Save the output of `test_pending_api.py`
3. Check browser console for errors
4. Check application logs
5. Provide this information when asking for help
