# Pending PDFs Not Showing - Debug Summary

## Current Situation

The multi-site scraper is finding and saving PDF links, but they are not appearing in the "Pending Manuals for Approval" section of the dashboard.

## Code Analysis Results

### 1. Scraper Code (app/tasks/jobs.py:241)
✅ **CORRECT** - The scraper sets `status='pending'` when creating manual records:
```python
manual = Manual(
    source_url=result.url,
    source_type=result.source_type,
    title=result.title,
    equipment_type=result.equipment_type,
    manufacturer=result.manufacturer,
    model=result.model,
    year=result.year,
    status='pending'  # ✅ Correctly set to 'pending'
)
```

### 2. API Endpoint (app/api/routes.py:316)
✅ **CORRECT** - The `/api/pending` endpoint correctly queries for pending manuals:
```python
@router.get("/pending", response_model=List[ManualResponse])
def get_pending_manuals(db: Session = Depends(get_db)):
    """Get all pending manuals for approval"""
    manuals = db.query(Manual).filter(
        Manual.status == 'pending'
    ).order_by(Manual.created_at.desc()).all()
    return manuals
```

### 3. Dashboard JavaScript (app/static/js/dashboard.js:79)
✅ **CORRECT** - The dashboard correctly calls the API endpoint:
```javascript
const response = await fetch(`${API_BASE}/pending`);
const manuals = await response.json();
```

## Potential Issues

### Issue 1: Database Lock (FIXED)
**Status:** ✅ Fixed in commit 31776c9

The database was experiencing lock issues that prevented the scraper from committing transactions. This has been fixed by:
- Adding WAL mode for better concurrency
- Adding timeout settings
- Improving error handling for duplicate constraints

### Issue 2: Transaction Rollback
**Possible Cause:** If the scraper encounters an error during the save process, the entire transaction is rolled back.

**Symptoms:**
- Scraper reports "found X PDFs total"
- But "Saved Y new manuals" shows 0
- No manuals appear in database

**Debug Steps:**
1. Check application logs for errors
2. Look for "UNIQUE constraint failed" errors
3. Look for "database is locked" errors

### Issue 3: Duplicate URLs
**Possible Cause:** All found PDFs are being skipped as duplicates.

**Symptoms:**
- Scraper reports "found X PDFs total"
- But "Skipped Y duplicate URLs" equals X
- No new manuals saved

**Debug Steps:**
1. Run: `python3 scripts/check_uncommitted.py`
2. Check if URLs already exist in database
3. Check if existing manuals have different status

### Issue 4: Status Changed After Save
**Possible Cause:** Something is changing the status after the save.

**Code Review:** No automatic processing of pending manuals found. The only way status changes is:
- User manually approves/rejects
- User adds to processing queue
- Background task processes approved manuals

## Diagnostic Steps

### Step 1: Run Full Diagnostic
```bash
python3 scripts/full_diagnostic.py
```

This will show:
- Total manuals in database
- Manuals by status
- Multi-site scraper results
- Potential issues

### Step 2: Check Recent Activity
```bash
python3 scripts/check_uncommitted.py
```

This will show:
- Manuals created in last 10 minutes
- Whether multi-site results exist
- Their current status

### Step 3: Test API Endpoint
```bash
python3 scripts/test_pending_api.py
```

This will show:
- Whether the API returns data
- Response status code
- Actual data returned

### Step 4: Debug Scrape
```bash
python3 scripts/debug_scrape.py
```

This will show:
- Database state before scrape
- Detailed scrape logs
- Database state after scrape
- What was actually saved

### Step 5: Check Application Logs
```bash
# If using systemd
journalctl -u autolister -f

# Or check log file
tail -f ./logs/autolister.log
```

Look for:
- "Saved X new manuals from multi-site scraping"
- "Skipped X duplicate URLs"
- Any error messages

### Step 6: Check Browser Console
1. Open dashboard in browser
2. Press F12 to open Developer Tools
3. Go to Console tab
4. Look for JavaScript errors
5. Go to Network tab
6. Refresh the page
7. Check `/api/pending` request:
   - Status code (should be 200)
   - Response data (should contain pending manuals)
   - Any error messages

## Expected Behavior

1. **Scraper runs:**
   - Finds PDFs from configured sites
   - Checks for duplicate URLs
   - Saves new manuals with `status='pending'`
   - Logs: "Saved X new manuals from multi-site scraping"

2. **Dashboard displays:**
   - Calls `/api/pending` endpoint
   - API returns manuals with `status='pending'`
   - JavaScript renders manual cards in pending section

3. **User approves:**
   - User clicks "Approve" button
   - Status changes to `status='approved'`
   - Manual moves to processing queue

## Common Scenarios

### Scenario 1: Scraper Finds No PDFs
**Symptoms:** "Found 0 PDFs total"

**Causes:**
- No matching PDFs on configured sites
- All PDFs excluded by exclude terms
- File size filters
- Network issues

**Solution:**
1. Check search terms match target PDFs
2. Check exclude terms aren't too broad
3. Verify sites have PDFs
4. Check network connectivity

### Scenario 2: All PDFs Are Duplicates
**Symptoms:** "Found X PDFs total", "Skipped X duplicate URLs", "Saved 0 new manuals"

**Causes:**
- PDFs already exist in database
- URLs are being normalized incorrectly
- Previous scrape already found these PDFs

**Solution:**
1. Check existing manuals with same URLs
2. Check their status (might not be 'pending')
3. If needed, update status back to 'pending'

### Scenario 3: Transaction Rollback
**Symptoms:** "Found X PDFs total", but error in logs, no manuals saved

**Causes:**
- Database lock
- UNIQUE constraint error
- Other database error

**Solution:**
1. Check application logs for errors
2. Restart application to apply database fixes
3. Run scraper again

### Scenario 4: Manuals Exist But Not Pending
**Symptoms:** Manuals exist in database but have different status

**Causes:**
- Status was changed after save
- Manual was previously processed
- Bug in status assignment

**Solution:**
1. Check manual status in database
2. If wrong, update to 'pending'
3. Investigate why status changed

## Next Steps

1. **Restart the application** to apply database fixes:
   ```bash
   sudo systemctl restart autolister
   ```

2. **Run the diagnostic scripts** to understand current state:
   ```bash
   python3 scripts/full_diagnostic.py
   python3 scripts/check_uncommitted.py
   ```

3. **Run a test scrape** to see what happens:
   ```bash
   python3 scripts/debug_scrape.py
   ```

4. **Check the logs** for any errors:
   ```bash
   journalctl -u autolister -f
   ```

5. **Test the API endpoint**:
   ```bash
   python3 scripts/test_pending_api.py
   ```

6. **Check browser console** for JavaScript errors

## Files to Check

- `app/tasks/jobs.py` - Scraper implementation (line 241 sets status)
- `app/api/routes.py` - API endpoint (line 316)
- `app/static/js/dashboard.js` - Dashboard JavaScript (line 79)
- `app/database.py` - Database models and connection
- Application logs - For error messages
- Browser console - For JavaScript errors

## Getting Help

If you've tried all these steps and still have issues:

1. Save the output of all diagnostic scripts
2. Save the application logs
3. Save browser console errors
4. Save network tab results
5. Provide this information when asking for help
