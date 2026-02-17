# How Pending Manuals for Approval Works

## Overview

This document explains the complete flow of how the program displays and manages pending manuals for approval.

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Manual Table                                                        │  │
│  │  - id                                                              │  │
│  │  - source_url                                                       │  │
│  │  - source_type ('multi_site')                                        │  │
│  │  - title                                                            │  │
│  │  - status ('pending', 'approved', 'rejected', 'downloaded', etc.)     │  │
│  │  - pdf_path                                                         │  │
│  │  - manufacturer, model, year                                         │  │
│  │  - created_at, updated_at                                           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │
                                    │ Read/Write
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                              │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Multi-Site Scraper (app/tasks/jobs.py)                         │  │
│  │    ┌─────────────────────────────────────────────────────────────┐   │  │
│  │    │ run_multi_site_scraping_job()                              │   │  │
│  │    │   - Scrapes configured sites for PDFs                      │   │  │
│  │    │   - Filters by search terms, exclude terms, file size      │   │  │
│  │    │   - Checks for duplicate URLs                               │   │  │
│  │    │   - Creates Manual records with status='pending'            │   │  │
│  │    │   - Commits to database                                     │   │  │
│  │    └─────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                      │
│                                    │ Writes to DB                         │
│                                    │                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 2. API Endpoints (app/api/routes.py)                               │  │
│  │    ┌─────────────────────────────────────────────────────────────┐   │  │
│  │    │ GET /api/pending                                          │   │  │
│  │    │   - Queries: Manual.status == 'pending'                    │   │  │
│  │    │   - Orders by: created_at DESC                             │   │  │
│  │    │   - Returns: List[ManualResponse]                          │   │  │
│  │    └─────────────────────────────────────────────────────────────┘   │  │
│  │    ┌─────────────────────────────────────────────────────────────┐   │  │
│  │    │ POST /api/pending/{manual_id}/approve                      │   │  │
│  │    │   - Downloads PDF from source_url                         │   │  │
│  │    │   - Updates status to 'downloaded'                        │   │  │
│  │    │   - Adds to processing queue                              │   │  │
│  │    │   - Returns: success message                              │   │  │
│  │    └─────────────────────────────────────────────────────────────┘   │  │
│  │    ┌─────────────────────────────────────────────────────────────┐   │  │
│  │    │ POST /api/pending/{manual_id}/reject                       │   │  │
│  │    │   - Updates status to 'rejected'                          │   │  │
│  │    │   - Returns: success message                              │   │  │
│  │    └─────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ HTTP API
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Browser)                              │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Dashboard HTML (app/static/index.html)                               │  │
│  │   - Tab: "Pending Manuals for Approval"                             │  │
│  │   - Container: <div id="pending-list">                              │  │
│  │   - Shows loading spinner initially                                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                      │
│                                    │                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Dashboard JavaScript (app/static/js/dashboard.js)                      │  │
│  │   ┌──────────────────────────────────────────────────────────────┐   │  │
│  │   │ On Page Load (DOMContentLoaded)                              │   │  │
│  │   │   - loadPendingManuals() is called                          │   │  │
│  │   │   - Auto-refresh every 5 seconds when on pending tab         │   │  │
│  │   └──────────────────────────────────────────────────────────────┘   │  │
│  │   ┌──────────────────────────────────────────────────────────────┐   │  │
│  │   │ loadPendingManuals()                                        │   │  │
│  │   │   1. Fetch: GET /api/pending                               │   │  │
│  │   │   2. Parse JSON response                                    │   │  │
│  │   │   3. If empty: Show "No pending manuals" message            │   │  │
│  │   │   4. If data: Call createManualCard() for each manual      │   │  │
│  │   │   5. Insert HTML into <div id="pending-list">              │   │  │
│  │   └──────────────────────────────────────────────────────────────┘   │  │
│  │   ┌──────────────────────────────────────────────────────────────┐   │  │
│  │   │ createManualCard(manual, isPending=true)                     │   │  │
│  │   │   - Creates HTML card with manual details                   │   │  │
│  │   │   - Shows: title, manufacturer, model, year, source, date   │   │  │
│  │   │   - Adds approve/reject buttons via createPendingActions()   │   │  │
│  │   └──────────────────────────────────────────────────────────────┘   │  │
│  │   ┌──────────────────────────────────────────────────────────────┐   │  │
│  │   │ approveManual(manualId)                                    │   │  │
│  │   │   1. POST: /api/pending/{manual_id}/approve              │   │  │
│  │   │   2. Show toast message                                   │   │  │
│  │   │   3. Reload all data sections                             │   │  │
│  │   └──────────────────────────────────────────────────────────────┘   │  │
│  │   ┌──────────────────────────────────────────────────────────────┐   │  │
│  │   │ rejectManual(manualId)                                     │   │  │
│  │   │   1. POST: /api/pending/{manual_id}/reject               │   │  │
│  │   │   2. Show toast message                                   │   │  │
│  │   │   3. Reload pending and stats                             │   │  │
│  │   └──────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Step-by-Step Flow

### 1. Scraper Finds and Saves Manuals

**File:** [`app/tasks/jobs.py`](app/tasks/jobs.py:92)

```python
@shared_task(name="app.tasks.jobs.run_multi_site_scraping_job")
def run_multi_site_scraping_job(...):
    # 1. Scrape sites for PDFs
    results = multi_site_scraper.search(log_callback=log)
    
    # 2. For each result:
    for result in results:
        # Check if URL already exists
        existing = db.query(Manual).filter(
            Manual.source_url == result.url
        ).first()
        
        if not existing:
            # Create manual with status='pending'
            manual = Manual(
                source_url=result.url,
                source_type=result.source_type,
                title=result.title,
                status='pending'  # ← KEY: Sets status to 'pending'
            )
            db.add(manual)
    
    # 3. Commit to database
    db.commit()
```

**Result:** Manuals are saved to database with `status='pending'`

---

### 2. Dashboard Loads Pending Manuals

**File:** [`app/static/js/dashboard.js`](app/static/js/dashboard.js:75)

```javascript
// Called on page load and every 5 seconds
async function loadPendingManuals() {
    const container = document.getElementById('pending-list');
    
    // 1. Fetch from API
    const response = await fetch(`${API_BASE}/pending`);
    const manuals = await response.json();
    
    // 2. If no manuals, show empty state
    if (manuals.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-inbox"></i>
                <h5>No pending manuals</h5>
                <p>All caught up! No manuals waiting for approval.</p>
            </div>
        `;
        return;
    }
    
    // 3. Create HTML for each manual
    let html = '<div class="row">';
    manuals.forEach(manual => {
        html += createManualCard(manual, true);
    });
    html += '</div>';
    
    // 4. Insert into DOM
    container.innerHTML = html;
}
```

---

### 3. API Returns Pending Manuals

**File:** [`app/api/routes.py`](app/api/routes.py:313)

```python
@router.get("/pending", response_model=List[ManualResponse])
def get_pending_manuals(db: Session = Depends(get_db)):
    """Get all pending manuals for approval"""
    # Query for manuals with status='pending'
    manuals = db.query(Manual).filter(
        Manual.status == 'pending'
    ).order_by(Manual.created_at.desc()).all()
    
    return manuals
```

**Result:** Returns JSON array of manuals with `status='pending'`

---

### 4. Manual Card is Rendered

**File:** [`app/static/js/dashboard.js`](app/static/js/dashboard.js:500)

```javascript
function createManualCard(manual, isPending) {
    return `
        <div class="col-md-6 col-lg-4">
            <div class="card manual-card ${manual.status}">
                <div class="card-header">
                    <span>${manual.title || 'Untitled Manual'}</span>
                    <span class="badge">${manual.status}</span>
                </div>
                <div class="card-body">
                    <!-- Manual details: manufacturer, model, year, etc. -->
                </div>
                <div class="card-footer">
                    ${isPending ? createPendingActions(manual.id) : ...}
                </div>
            </div>
        </div>
    `;
}

function createPendingActions(manualId) {
    return `
        <div class="d-flex gap-2">
            <button onclick="approveManual(${manualId})">
                <i class="bi bi-check-circle"></i> Approve
            </button>
            <button onclick="rejectManual(${manualId})">
                <i class="bi bi-x-circle"></i> Reject
            </button>
        </div>
    `;
}
```

**Result:** HTML card with approve/reject buttons is displayed

---

### 5. User Approves Manual

**File:** [`app/static/js/dashboard.js`](app/static/js/dashboard.js:794)

```javascript
async function approveManual(manualId) {
    // 1. Call approve API
    const response = await fetch(`${API_BASE}/pending/${manualId}/approve`, {
        method: 'POST'
    });
    
    // 2. Show success message
    showToast('Manual approved and downloaded!', 'success');
    
    // 3. Reload all sections
    loadPendingManuals();
    loadProcessingManuals();
    loadQueue();
    loadReadyManuals();
    loadAllManuals();
    loadStats();
}
```

---

### 6. API Downloads PDF and Updates Status

**File:** [`app/api/routes.py`](app/api/routes.py:390)

```python
@router.post("/pending/{manual_id}/approve")
def approve_manual(manual_id: int, db: Session = Depends(get_db)):
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    # 1. Download PDF
    downloader = PDFDownloader()
    pdf_path = downloader.download(
        manual.source_url,
        manual_id,
        manufacturer=manual.manufacturer,
        model=manual.model,
        year=manual.year
    )
    
    # 2. Update status to 'downloaded'
    manual.status = 'downloaded'
    manual.pdf_path = pdf_path
    db.commit()
    
    # 3. Add to processing queue
    queue_manager = ProcessingQueueManager(db)
    queue_position = queue_manager.add_to_queue(manual_id)
    
    return {
        "message": "Manual approved and added to processing queue.",
        "manual_id": manual_id,
        "status": "downloaded",
        "queue_position": queue_position
    }
```

**Result:** 
- PDF is downloaded
- Status changes from `'pending'` to `'downloaded'`
- Manual is added to processing queue
- Manual no longer appears in pending section

---

### 7. User Rejects Manual

**File:** [`app/api/routes.py`](app/api/routes.py:462)

```python
@router.post("/pending/{manual_id}/reject")
def reject_manual(manual_id: int, db: Session = Depends(get_db)):
    manual = db.query(Manual).filter(Manual.id == manual_id).first()
    
    # Update status to 'rejected'
    manual.status = 'rejected'
    db.commit()
    
    return {"message": "Manual rejected", "manual_id": manual_id}
```

**Result:**
- Status changes from `'pending'` to `'rejected'`
- Manual no longer appears in pending section

## Key Points

### Why Manuals Might Not Show

1. **Status is not 'pending'**
   - Check database: `SELECT * FROM manuals WHERE status != 'pending'`
   - If status is different, it won't appear in pending section

2. **Database lock/rollback**
   - Scraper found PDFs but transaction was rolled back
   - Check logs for "database is locked" or "UNIQUE constraint" errors

3. **All PDFs are duplicates**
   - Scraper found PDFs but all URLs already exist in database
   - Check logs for "Skipped X duplicate URLs"

4. **API endpoint error**
   - `/api/pending` returns error
   - Check browser Network tab for failed requests

5. **JavaScript error**
   - Error in dashboard JavaScript prevents rendering
   - Check browser Console for errors

### Status Flow

```
pending → approved → downloaded → processing → processed → listed
   ↓
rejected
   ↓
error
```

### Auto-Refresh

The dashboard automatically refreshes pending manuals every 5 seconds when the pending tab is active:

```javascript
// app/static/js/dashboard.js:34
function startAutoRefresh() {
    refreshInterval = setInterval(function() {
        loadStats();
        loadCurrentScrape();
        if (currentTab === 'pending') {
            loadPendingManuals();  // ← Auto-refreshes
        }
        // ...
    }, 5000);  // Every 5 seconds
}
```

## Files Involved

| Component | File | Purpose |
|-----------|------|---------|
| Scraper | `app/tasks/jobs.py:92` | Saves manuals with status='pending' |
| API Endpoint | `app/api/routes.py:313` | Returns pending manuals |
| Approve API | `app/api/routes.py:390` | Downloads PDF and updates status |
| Reject API | `app/api/routes.py:462` | Updates status to 'rejected' |
| Dashboard HTML | `app/static/index.html:167` | Pending tab container |
| Dashboard JS | `app/static/js/dashboard.js:75` | Loads and displays pending manuals |
| Manual Card | `app/static/js/dashboard.js:500` | Renders manual card HTML |
| Database Model | `app/database.py:30` | Manual table definition |
