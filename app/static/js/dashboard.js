// AutoLister Dashboard JavaScript

// API Base URL
const API_BASE = '/api';

// Global state
let currentTab = 'pending';
let refreshInterval = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadPendingManuals();
    loadProcessingManuals();
    loadReadyManuals();
    loadAllManuals();
    loadFileListings();
    
    // Set up auto-refresh
    startAutoRefresh();
    
    // Set up tab change handlers
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            currentTab = event.target.getAttribute('data-bs-target').replace('#', '');
            // Refresh all data when tab changes
            refreshAllData();
        });
    });
});

// Start auto-refresh
function startAutoRefresh() {
    refreshInterval = setInterval(function() {
        loadStats();
        if (currentTab === 'pending') {
            loadPendingManuals();
        } else if (currentTab === 'processing') {
            loadProcessingManuals();
        } else if (currentTab === 'ready') {
            loadReadyManuals();
        }
    }, 30000); // Refresh every 30 seconds
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const stats = await response.json();
        
        document.getElementById('total-manuals').textContent = stats.total_manuals;
        document.getElementById('pending-manuals').textContent = stats.pending_manuals;
        document.getElementById('file-listings').textContent = stats.file_listings || 0;
        document.getElementById('pending-count').textContent = stats.pending_manuals;
        document.getElementById('processing-count').textContent = stats.downloaded_manuals || 0;
        document.getElementById('ready-count').textContent = stats.processed_manuals || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load pending manuals
async function loadPendingManuals() {
    const container = document.getElementById('pending-list');
    
    try {
        const response = await fetch(`${API_BASE}/pending`);
        const manuals = await response.json();
        
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
        
        let html = '<div class="row">';
        manuals.forEach(manual => {
            html += createManualCard(manual, true);
        });
        html += '</div>';
        
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                Error loading pending manuals: ${error.message}
            </div>
        `;
    }
}

// Load all manuals
async function loadAllManuals() {
    const container = document.getElementById('manuals-list');
    
    try {
        const response = await fetch(`${API_BASE}/manuals`);
        const manuals = await response.json();
        
        if (manuals.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-file-earmark"></i>
                    <h5>No manuals found</h5>
                    <p>Start the scraper to discover manuals.</p>
                </div>
            `;
            return;
        }
        
        let html = '<div class="row">';
        manuals.forEach(manual => {
            html += createManualCard(manual, false);
        });
        html += '</div>';
        
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                Error loading manuals: ${error.message}
            </div>
        `;
    }
}

// Load processing manuals
async function loadProcessingManuals() {
    const container = document.getElementById('processing-list');
    
    try {
        const response = await fetch(`${API_BASE}/manuals?status=downloaded`);
        const manuals = await response.json();
        
        if (manuals.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-gear"></i>
                    <h5>No processing manuals</h5>
                    <p>Manuals will appear here after being downloaded.</p>
                </div>
            `;
            return;
        }
        
        let html = '<div class="row">';
        manuals.forEach(manual => {
            html += createProcessingCard(manual);
        });
        html += '</div>';
        
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                Error loading processing manuals: ${error.message}
            </div>
        `;
    }
}

// Load ready-to-list manuals
async function loadReadyManuals() {
    const container = document.getElementById('ready-list');
    
    try {
        const response = await fetch(`${API_BASE}/manuals?status=processed`);
        const manuals = await response.json();
        
        if (manuals.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-check-circle"></i>
                    <h5>No ready manuals</h5>
                    <p>Process manuals to make them ready for listing.</p>
                </div>
            `;
            return;
        }
        
        let html = '<div class="row">';
        manuals.forEach(manual => {
            html += createReadyCard(manual);
        });
        html += '</div>';
        
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                Error loading ready manuals: ${error.message}
            </div>
        `;
    }
}

// Load Etsy listings
async function loadListings() {
    const container = document.getElementById('listings-list');
    
    try {
        const response = await fetch(`${API_BASE}/listings`);
        const listings = await response.json();
        
        if (listings.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-shop"></i>
                    <h5>No listings found</h5>
                    <p>Process and list manuals to create Etsy listings.</p>
                </div>
            `;
            return;
        }
        
        let html = '<div class="table-responsive"><table class="table table-hover">';
        html += `
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Price</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
        `;
        
        listings.forEach(listing => {
            html += createListingRow(listing);
        });
        
        html += '</tbody></table></div>';
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                Error loading listings: ${error.message}
            </div>
        `;
    }
}

// Create manual card HTML
function createManualCard(manual, isPending) {
    const statusClass = manual.status;
    const statusLabel = manual.status.charAt(0).toUpperCase() + manual.status.slice(1);
    
    return `
        <div class="col-md-6 col-lg-4">
            <div class="card manual-card ${statusClass} fade-in">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span>${manual.title || 'Untitled Manual'}</span>
                    <span class="badge status-badge ${statusClass}">${statusLabel}</span>
                </div>
                <div class="card-body">
                    <dl class="manual-details row">
                        ${manual.manufacturer ? `
                            <dt class="col-sm-4">Manufacturer:</dt>
                            <dd class="col-sm-8">${manual.manufacturer}</dd>
                        ` : ''}
                        ${manual.model ? `
                            <dt class="col-sm-4">Model:</dt>
                            <dd class="col-sm-8">${manual.model}</dd>
                        ` : ''}
                        ${manual.year ? `
                            <dt class="col-sm-4">Year:</dt>
                            <dd class="col-sm-8">${manual.year}</dd>
                        ` : ''}
                        <dt class="col-sm-4">Source:</dt>
                        <dd class="col-sm-8">${manual.source_type}</dd>
                        <dt class="col-sm-4">Created:</dt>
                        <dd class="col-sm-8">${new Date(manual.created_at).toLocaleDateString()}</dd>
                    </dl>
                    <a href="${manual.source_url}" target="_blank" class="source-url">
                        <i class="bi bi-link-45deg"></i> View Source
                    </a>
                </div>
                <div class="card-footer">
                    ${isPending ? createPendingActions(manual.id) : createManualActions(manual)}
                </div>
            </div>
        </div>
    `;
}

// Create pending action buttons
function createPendingActions(manualId) {
    return `
        <div class="d-flex gap-2">
            <button class="btn btn-approve flex-grow-1" onclick="approveManual(${manualId})">
                <i class="bi bi-check-circle"></i> Approve
            </button>
            <button class="btn btn-reject" onclick="rejectManual(${manualId})">
                <i class="bi bi-x-circle"></i> Reject
            </button>
        </div>
    `;
}

// Create manual action buttons
function createManualActions(manual) {
    let actions = '';
    
    switch (manual.status) {
        case 'approved':
            actions = `
                <div class="d-flex gap-2">
                    <button class="btn btn-primary flex-grow-1" onclick="downloadManual(${manual.id})">
                        <i class="bi bi-download"></i> Download
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteManual(${manual.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;
            break;
        case 'downloaded':
            actions = `
                <div class="d-flex gap-2">
                    <button class="btn btn-primary flex-grow-1" onclick="processManual(${manual.id})">
                        <i class="bi bi-gear"></i> Process
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteManual(${manual.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;
            break;
        case 'processed':
            actions = `
                <div class="d-flex flex-column gap-2">
                    <button class="btn btn-success w-100" onclick="downloadResources(${manual.id})">
                        <i class="bi bi-download"></i> Download Resources
                    </button>
                    <div class="d-flex gap-2">
                        <button class="btn btn-primary flex-grow-1" onclick="markAsListed(${manual.id})">
                            <i class="bi bi-check-circle"></i> Mark Listed
                        </button>
                        <button class="btn btn-outline-danger" onclick="deleteManual(${manual.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            `;
            break;
        case 'listed':
            actions = `
                <div class="d-flex gap-2">
                    <button class="btn btn-secondary flex-grow-1" disabled>
                        <i class="bi bi-check-circle"></i> Listed
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteManual(${manual.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;
            break;
        case 'error':
            actions = `
                <div class="d-flex gap-2">
                    <button class="btn btn-outline-danger flex-grow-1" onclick="showManualDetails(${manual.id})">
                        <i class="bi bi-exclamation-triangle"></i> View Error
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteManual(${manual.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;
            break;
        default:
            actions = `<span class="text-muted">No actions available</span>`;
    }
    
    return actions;
}

// Create processing card HTML
function createProcessingCard(manual) {
    return `
        <div class="col-md-6 col-lg-4">
            <div class="card manual-card downloaded fade-in">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span>${manual.title || 'Untitled Manual'}</span>
                    <span class="badge status-badge downloaded">Downloaded</span>
                </div>
                <div class="card-body">
                    <dl class="manual-details row">
                        ${manual.manufacturer ? `
                            <dt class="col-sm-4">Manufacturer:</dt>
                            <dd class="col-sm-8">${manual.manufacturer}</dd>
                        ` : ''}
                        ${manual.model ? `
                            <dt class="col-sm-4">Model:</dt>
                            <dd class="col-sm-8">${manual.model}</dd>
                        ` : ''}
                        ${manual.year ? `
                            <dt class="col-sm-4">Year:</dt>
                            <dd class="col-sm-8">${manual.year}</dd>
                        ` : ''}
                        <dt class="col-sm-4">Source:</dt>
                        <dd class="col-sm-8">${manual.source_type}</dd>
                        <dt class="col-sm-4">Created:</dt>
                        <dd class="col-sm-8">${new Date(manual.created_at).toLocaleDateString()}</dd>
                    </dl>
                    <a href="${manual.source_url}" target="_blank" class="source-url">
                        <i class="bi bi-link-45deg"></i> View Source
                    </a>
                </div>
                <div class="card-footer">
                    <div class="d-flex gap-2">
                        <button class="btn btn-primary flex-grow-1" onclick="processManual(${manual.id})">
                            <i class="bi bi-gear"></i> Process
                        </button>
                        <button class="btn btn-outline-danger" onclick="deleteManual(${manual.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Create ready-to-list card HTML
function createReadyCard(manual) {
    return `
        <div class="col-md-6 col-lg-4">
            <div class="card manual-card processed fade-in">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span>${manual.title || 'Untitled Manual'}</span>
                    <span class="badge status-badge processed">Ready</span>
                </div>
                <div class="card-body">
                    <dl class="manual-details row">
                        ${manual.manufacturer ? `
                            <dt class="col-sm-4">Manufacturer:</dt>
                            <dd class="col-sm-8">${manual.manufacturer}</dd>
                        ` : ''}
                        ${manual.model ? `
                            <dt class="col-sm-4">Model:</dt>
                            <dd class="col-sm-8">${manual.model}</dd>
                        ` : ''}
                        ${manual.year ? `
                            <dt class="col-sm-4">Year:</dt>
                            <dd class="col-sm-8">${manual.year}</dd>
                        ` : ''}
                        <dt class="col-sm-4">Source:</dt>
                        <dd class="col-sm-8">${manual.source_type}</dd>
                        <dt class="col-sm-4">Created:</dt>
                        <dd class="col-sm-8">${new Date(manual.created_at).toLocaleDateString()}</dd>
                    </dl>
                    <a href="${manual.source_url}" target="_blank" class="source-url">
                        <i class="bi bi-link-45deg"></i> View Source
                    </a>
                </div>
                <div class="card-footer">
                    <div class="d-flex flex-column gap-2">
                        <button class="btn btn-success w-100" onclick="downloadResources(${manual.id})">
                            <i class="bi bi-download"></i> Download Resources
                        </button>
                        <div class="d-flex gap-2">
                            <button class="btn btn-primary flex-grow-1" onclick="markAsListed(${manual.id})">
                                <i class="bi bi-check-circle"></i> Mark Listed
                            </button>
                            <button class="btn btn-outline-danger" onclick="deleteManual(${manual.id})">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Create listing row HTML
function createListingRow(listing) {
    const statusClass = listing.status;
    const statusLabel = listing.status.charAt(0).toUpperCase() + listing.status.slice(1);
    
    return `
        <tr>
            <td>${listing.id}</td>
            <td>${listing.title.substring(0, 50)}${listing.title.length > 50 ? '...' : ''}</td>
            <td>$${listing.price.toFixed(2)}</td>
            <td><span class="badge status-badge ${statusClass}">${statusLabel}</span></td>
            <td>${new Date(listing.created_at).toLocaleDateString()}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="viewListingFiles('${listing.id}')">
                    <i class="bi bi-folder"></i> Files
                </button>
                ${listing.status === 'draft' ? `
                    <button class="btn btn-sm btn-success" onclick="activateListing(${listing.id})">
                        <i class="bi bi-play-circle"></i> Activate
                    </button>
                ` : ''}
                ${listing.status === 'active' ? `
                    <button class="btn btn-sm btn-warning" onclick="deactivateListing(${listing.id})">
                        <i class="bi bi-pause-circle"></i> Deactivate
                    </button>
                ` : ''}
            </td>
        </tr>
    `;
}

// Approve manual
async function approveManual(manualId) {
    try {
        showToast('Approving and downloading manual...', 'info');
        
        const response = await fetch(`${API_BASE}/pending/${manualId}/approve`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast(data.message || 'Manual approved and downloaded!', 'success');
            loadPendingManuals();
            loadProcessingManuals();
            loadReadyManuals();
            loadAllManuals();
            loadStats();
        } else {
            showToast('Failed to approve manual', 'error');
        }
    } catch (error) {
        showToast('Error approving manual: ' + error.message, 'error');
    }
}

// Reject manual
async function rejectManual(manualId) {
    try {
        const response = await fetch(`${API_BASE}/pending/${manualId}/reject`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showToast('Manual rejected', 'warning');
            loadPendingManuals();
            loadStats();
        } else {
            showToast('Failed to reject manual', 'error');
        }
    } catch (error) {
        showToast('Error rejecting manual: ' + error.message, 'error');
    }
}

// Delete manual
async function deleteManual(manualId) {
    if (!confirm('Are you sure you want to delete this manual? This cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/manuals/${manualId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast('Manual deleted successfully', 'success');
            loadPendingManuals();
            loadProcessingManuals();
            loadReadyManuals();
            loadAllManuals();
            loadStats();
        } else {
            showToast('Failed to delete manual', 'error');
        }
    } catch (error) {
        showToast('Error deleting manual: ' + error.message, 'error');
    }
}

// Mark manual as listed
async function markAsListed(manualId) {
    try {
        const response = await fetch(`${API_BASE}/manuals/${manualId}/mark-listed`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showToast('Manual marked as listed!', 'success');
            loadReadyManuals();
            loadAllManuals();
            loadListings();
            loadStats();
        } else {
            showToast('Failed to mark manual as listed', 'error');
        }
    } catch (error) {
        showToast('Error marking manual as listed: ' + error.message, 'error');
    }
}

// Download manual
async function downloadManual(manualId) {
    try {
        showToast('Downloading manual...', 'info');
        
        const response = await fetch(`${API_BASE}/manuals/${manualId}/download`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast('Manual downloaded successfully!', 'success');
            loadAllManuals();
            loadStats();
        } else {
            showToast('Failed to download manual', 'error');
        }
    } catch (error) {
        showToast('Error downloading manual: ' + error.message, 'error');
    }
}

// Process manual
async function processManual(manualId) {
    try {
        showToast('Processing manual...', 'info');
        
        const response = await fetch(`${API_BASE}/manuals/${manualId}/process`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showToast('Manual processed successfully!', 'success');
            // Refresh all data when processing completes
            refreshAllData();
        } else {
            showToast('Failed to process manual', 'error');
        }
    } catch (error) {
        showToast('Error processing manual: ' + error.message, 'error');
    }
}

// List on Etsy
async function listOnEtsy(manualId) {
    try {
        showToast('Creating Etsy listing...', 'info');
        
        const response = await fetch(`${API_BASE}/manuals/${manualId}/list`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast('Etsy listing created!', 'success');
            loadAllManuals();
            loadListings();
            loadStats();
        } else {
            showToast('Failed to create Etsy listing', 'error');
        }
    } catch (error) {
        showToast('Error creating listing: ' + error.message, 'error');
    }
}

// Download resources (PDF, images, README) for manual upload
async function downloadResources(manualId) {
    try {
        showToast('Downloading resources...', 'info');
        
        const response = await fetch(`${API_BASE}/manuals/${manualId}/download-resources`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `manual_${manualId}_resources.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showToast('Resources downloaded!', 'success');
        } else {
            showToast('Failed to download resources', 'error');
        }
    } catch (error) {
        showToast('Error downloading resources: ' + error.message, 'error');
    }
}

// Activate listing
async function activateListing(listingId) {
    try {
        const response = await fetch(`${API_BASE}/listings/${listingId}/activate`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showToast('Listing activated!', 'success');
            loadListings();
            loadStats();
        } else {
            showToast('Failed to activate listing', 'error');
        }
    } catch (error) {
        showToast('Error activating listing: ' + error.message, 'error');
    }
}

// Deactivate listing
async function deactivateListing(listingId) {
    try {
        const response = await fetch(`${API_BASE}/listings/${listingId}/deactivate`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showToast('Listing deactivated', 'warning');
            loadListings();
            loadStats();
        } else {
            showToast('Failed to deactivate listing', 'error');
        }
    } catch (error) {
        showToast('Error deactivating listing: ' + error.message, 'error');
    }
}

// Show manual details
async function showManualDetails(manualId) {
    try {
        const response = await fetch(`${API_BASE}/manuals/${manualId}`);
        const manual = await response.json();
        
        const modalTitle = document.getElementById('manualModalTitle');
        const modalBody = document.getElementById('manualModalBody');
        const modalFooter = document.getElementById('manualModalFooter');
        
        modalTitle.textContent = manual.title || 'Manual Details';
        
        modalBody.innerHTML = `
            <dl class="manual-details">
                <dt>Status:</dt>
                <dd><span class="badge status-badge ${manual.status}">${manual.status}</span></dd>
                <dt>Source URL:</dt>
                <dd><a href="${manual.source_url}" target="_blank">${manual.source_url}</a></dd>
                <dt>Source Type:</dt>
                <dd>${manual.source_type}</dd>
                ${manual.manufacturer ? `<dt>Manufacturer:</dt><dd>${manual.manufacturer}</dd>` : ''}
                ${manual.model ? `<dt>Model:</dt><dd>${manual.model}</dd>` : ''}
                ${manual.year ? `<dt>Year:</dt><dd>${manual.year}</dd>` : ''}
                <dt>Created:</dt>
                <dd>${new Date(manual.created_at).toLocaleString()}</dd>
                <dt>Updated:</dt>
                <dd>${new Date(manual.updated_at).toLocaleString()}</dd>
                ${manual.error_message ? `
                    <dt>Error:</dt>
                    <dd class="text-danger">${manual.error_message}</dd>
                ` : ''}
            </dl>
        `;
        
        modalFooter.innerHTML = `
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
        `;
        
        const modal = new bootstrap.Modal(document.getElementById('manualModal'));
        modal.show();
    } catch (error) {
        showToast('Error loading manual details', 'error');
    }
}

// Refresh all data
function refreshAllData() {
    loadStats();
    loadPendingManuals();
    loadProcessingManuals();
    loadReadyManuals();
    loadAllManuals();
    loadFileListings();
}

// Refresh pending manuals
function refreshPending() {
    loadPendingManuals();
    showToast('Refreshed!', 'info');
}

// Search manuals
function searchManuals() {
    const searchTerm = document.getElementById('manuals-search').value;
    // TODO: Implement search functionality
    showToast('Search not yet implemented', 'warning');
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('liveToast');
    const toastTitle = document.getElementById('toast-title');
    const toastMessage = document.getElementById('toast-message');
    
    toast.className = 'toast';
    toast.classList.add(type);
    
    toastTitle.textContent = type.charAt(0).toUpperCase() + type.slice(1);
    toastMessage.textContent = message;
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// Load file listings
async function loadFileListings() {
    const container = document.getElementById('listings-list');
    
    try {
        const response = await fetch(`${API_BASE}/files/listings`);
        const data = await response.json();
        
        if (data.listings && data.listings.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-file-earmark"></i>
                    <h5>No file listings found</h5>
                    <p>Process manuals to create file listings.</p>
                </div>
            `;
            return;
        }
        
        let html = '<div class="table-responsive"><table class="table table-hover">';
        html += `
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Price</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
        `;
        
        data.listings.forEach(listing => {
            const statusClass = listing.status;
            const statusLabel = listing.status.charAt(0).toUpperCase() + listing.status.slice(1);
            
            html += `
                <tr>
                    <td>${listing.id}</td>
                    <td>${listing.title.substring(0, 50)}${listing.title.length > 50 ? '...' : ''}</td>
                    <td>$${listing.price.toFixed(2)}</td>
                    <td><span class="badge status-badge ${statusClass}">${statusLabel}</span></td>
                    <td>${new Date(listing.created_at).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewListingFiles('${listing.id}')">
                            <i class="bi bi-folder"></i> Files
                        </button>
                        <button class="btn btn-sm btn-outline-success" onclick="updateListingStatus('${listing.id}', 'uploaded')">
                            <i class="bi bi-check-circle"></i> Mark Uploaded
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteListing('${listing.id}')">
                            <i class="bi bi-trash"></i> Delete
                        </button>
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
        container.innerHTML = html;
        
    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                Error loading file listings: ${error.message}
            </div>
        `;
    }
}

// View listing files
function viewListingFiles(listingId) {
    // Open file listing details modal
    // For now, just show a toast
    showToast('File details feature - check data/listings directory', 'info');
}

// Update listing status
async function updateListingStatus(listingId, status) {
    try {
        const response = await fetch(`${API_BASE}/files/listings/${listingId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: status })
        });
        
        if (response.ok) {
            showToast('Listing status updated', 'success');
            loadFileListings();
        } else {
            showToast('Failed to update listing status', 'error');
        }
    } catch (error) {
        showToast('Error updating listing status: ' + error.message, 'error');
    }
}

// Delete listing
async function deleteListing(listingId) {
    if (!confirm('Are you sure you want to delete this listing?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/files/listings/${listingId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast('Listing deleted successfully', 'success');
            loadFileListings();
        } else {
            showToast('Failed to delete listing', 'error');
        }
    } catch (error) {
        showToast('Error deleting listing: ' + error.message, 'error');
    }
}


// Export CSV
async function exportCSV() {
    try {
        const response = await fetch(`${API_BASE}/files/export/csv`);
        const data = await response.json();
        
        if (data.path) {
            // Create download link
            const filename = data.path.split('/').pop();
            window.location.href = `/api/files/download/${filename}`;
            
            showToast('CSV exported successfully', 'success');
        } else {
            showToast('Failed to export CSV', 'error');
        }
    } catch (error) {
        showToast('Error exporting CSV: ' + error.message, 'error');
    }
}


// ==================== Scraping Control Functions ====================

// Start scraping
async function startScraping() {
    console.log('startScraping() called');
    try {
        const response = await fetch(`${API_BASE}/scraping/start`, {
            method: 'POST'
        });
        const data = await response.json();
        console.log('Start scraping response:', data);
        
        if (data.status === 'running') {
            showToast('Scraping started successfully', 'success');
            updateScrapingButtons(true);
            showScrapingStatus();
            startScrapingStatusPolling();
        } else {
            showToast('Failed to start scraping', 'error');
        }
    } catch (error) {
        console.error('Error starting scraping:', error);
        showToast('Error starting scraping: ' + error.message, 'error');
    }
}

// Stop scraping
async function stopScraping() {
    console.log('stopScraping() called');
    try {
        const response = await fetch(`${API_BASE}/scraping/stop`, {
            method: 'POST'
        });
        const data = await response.json();
        console.log('Stop scraping response:', data);
        
        if (data.status === 'stopped') {
            showToast('Scraping stopped', 'info');
            updateScrapingButtons(false);
        } else {
            showToast('Failed to stop scraping', 'error');
        }
    } catch (error) {
        console.error('Error stopping scraping:', error);
        showToast('Error stopping scraping: ' + error.message, 'error');
    }
}

// Update scraping buttons state
function updateScrapingButtons(isRunning) {
    const startBtn = document.getElementById('start-scraping-btn');
    const stopBtn = document.getElementById('stop-scraping-btn');
    const statusBadge = document.getElementById('scraping-status-badge');
    
    if (isRunning) {
        startBtn.disabled = true;
        stopBtn.disabled = false;
        if (statusBadge) {
            statusBadge.textContent = 'Running';
            statusBadge.className = 'badge bg-success';
        }
    } else {
        startBtn.disabled = false;
        stopBtn.disabled = true;
        if (statusBadge) {
            statusBadge.textContent = 'Idle';
            statusBadge.className = 'badge bg-secondary';
        }
    }
}

// Toggle scraping status panel
function toggleScrapingStatus() {
    const statusSection = document.getElementById('scraping-status-section');
    if (statusSection.style.display === 'none') {
        statusSection.style.display = 'block';
        loadScrapingStatus();
    } else {
        statusSection.style.display = 'none';
    }
}

// Show scraping status panel
function showScrapingStatus() {
    const statusSection = document.getElementById('scraping-status-section');
    statusSection.style.display = 'block';
}

// Load scraping status
async function loadScrapingStatus() {
    try {
        const response = await fetch(`${API_BASE}/scraping/status`);
        const data = await response.json();
        
        updateScrapingButtons(data.running);
        displayScrapingLogs(data.logs);
        
        return data.running;
    } catch (error) {
        console.error('Error loading scraping status:', error);
        return false;
    }
}

// Display scraping logs
function displayScrapingLogs(logs) {
    const logsContainer = document.getElementById('scraping-logs');
    
    if (!logs || logs.length === 0) {
        logsContainer.innerHTML = '<div class="text-muted">No logs yet. Start scraping to see output.</div>';
        return;
    }
    
    let html = '';
    logs.forEach(log => {
        const time = new Date(log.time).toLocaleTimeString();
        html += `<div class="log-entry">
            <span class="log-time">[${time}]</span>
            <span class="log-message">${log.message}</span>
        </div>`;
    });
    
    logsContainer.innerHTML = html;
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

// Start polling for scraping status
let scrapingStatusInterval = null;

function startScrapingStatusPolling() {
    if (scrapingStatusInterval) {
        clearInterval(scrapingStatusInterval);
    }
    
    scrapingStatusInterval = setInterval(async () => {
        const isRunning = await loadScrapingStatus();
        if (!isRunning) {
            stopScrapingStatusPolling();
        }
    }, 2000); // Poll every 2 seconds
}

// Stop polling for scraping status
function stopScrapingStatusPolling() {
    if (scrapingStatusInterval) {
        clearInterval(scrapingStatusInterval);
        scrapingStatusInterval = null;
    }
}

// Show all scraping logs in modal
async function showScrapingLogs() {
    console.log('showScrapingLogs() called');
    const modal = new bootstrap.Modal(document.getElementById('logsModal'));
    const logsContainer = document.getElementById('all-logs');
    
    logsContainer.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    
    modal.show();
    
    try {
        const response = await fetch(`${API_BASE}/scraping/logs`);
        const logs = await response.json();
        
        if (logs.length === 0) {
            logsContainer.innerHTML = '<div class="text-muted">No logs found.</div>';
            return;
        }
        
        let html = '<div class="log-list">';
        logs.forEach(log => {
            const time = new Date(log.created_at).toLocaleString();
            const statusClass = log.status === 'completed' ? 'text-success' :
                               log.status === 'failed' ? 'text-danger' : 'text-info';
            
            html += `
                <div class="log-item card mb-2">
                    <div class="card-body py-2">
                        <div class="d-flex justify-content-between">
                            <span class="badge ${statusClass}">${log.stage}</span>
                            <small class="text-muted">${time}</small>
                        </div>
                        <div class="mt-1">${log.message}</div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        logsContainer.innerHTML = html;
    } catch (error) {
        logsContainer.innerHTML = `
            <div class="alert alert-danger">
                Error loading logs: ${error.message}
            </div>
        `;
    }
}


// ==================== PDF Upload Functions ====================

// Upload PDF file
async function uploadPDF() {
    console.log('uploadPDF() called');
    const fileInput = document.getElementById('pdfFile');
    const progressDiv = document.getElementById('uploadProgress');
    const resultDiv = document.getElementById('uploadResult');
    
    const file = fileInput.files[0];
    
    if (!file) {
        console.log('No file selected');
        showToast('Please select a PDF file', 'error');
        return;
    }
    
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showToast('Only PDF files are allowed', 'error');
        return;
    }
    
    // Show progress
    progressDiv.classList.remove('d-none');
    resultDiv.innerHTML = '';
    
    try {
        // Read file as ArrayBuffer
        const arrayBuffer = await file.arrayBuffer();
        const bytes = new Uint8Array(arrayBuffer);
        
        // Convert to base64 for upload
        const binaryString = bytes.reduce((acc, byte) => acc + String.fromCharCode(byte), '');
        const base64 = btoa(binaryString);
        
        // Upload to server
        const response = await fetch(`${API_BASE}/upload/pdf`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file: base64,
                filename: file.name
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <strong>Success!</strong> PDF uploaded successfully.<br>
                    Manual ID: ${data.manual_id}<br>
                    Filename: ${data.filename}
                </div>
            `;
            showToast('PDF uploaded successfully', 'success');
            
            // Refresh pending manuals
            loadPendingManuals();
            loadStats();
            
            // Close modal after delay
            setTimeout(() => {
                const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
                modal.hide();
                // Reset form
                document.getElementById('uploadForm').reset();
                progressDiv.classList.add('d-none');
                resultDiv.innerHTML = '';
            }, 2000);
        } else {
            throw new Error(data.detail || 'Upload failed');
        }
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="alert alert-danger">
                <strong>Error:</strong> ${error.message}
            </div>
        `;
        showToast('Error uploading PDF: ' + error.message, 'error');
    } finally {
        progressDiv.classList.add('d-none');
    }
}
