/**
 * Scrape Queue Page JavaScript
 */

// Global state
let scrapeJobs = [];
let currentEditingJobId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    refreshQueue();
    // Auto-refresh every 30 seconds
    setInterval(refreshQueue, 30000);
});

/**
 * Refresh the scrape job queue
 */
async function refreshQueue() {
    try {
        const response = await fetch('/api/scrape-jobs');
        if (!response.ok) throw new Error('Failed to fetch jobs');
        
        const data = await response.json();
        scrapeJobs = data.jobs || [];
        
        updateStats(data.stats);
        renderQueue();
    } catch (error) {
        console.error('Error refreshing queue:', error);
        showError('Failed to refresh queue. Please try again.');
    }
}

/**
 * Update statistics display
 */
function updateStats(stats) {
    document.getElementById('queued-jobs').textContent = stats.queued || 0;
    document.getElementById('scheduled-jobs').textContent = stats.scheduled || 0;
    document.getElementById('completed-jobs').textContent = stats.completed || 0;
    document.getElementById('failed-jobs').textContent = stats.failed || 0;
}

/**
 * Render the job queue
 */
function renderQueue() {
    const container = document.getElementById('queue-container');
    
    if (scrapeJobs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-inbox"></i>
                <p>No jobs in queue. Create a new scrape job to get started.</p>
                <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#newJobModal">
                    <i class="bi bi-plus-lg"></i> New Scrape Job
                </button>
            </div>
        `;
        return;
    }
    
    // Sort jobs: queued first (by position), then scheduled (by time), then completed/failed
    const sortedJobs = [...scrapeJobs].sort((a, b) => {
        if (a.status === 'queued' && b.status === 'queued') {
            return (a.queue_position || 0) - (b.queue_position || 0);
        }
        if (a.status === 'queued') return -1;
        if (b.status === 'queued') return 1;
        
        if (a.status === 'scheduled' && b.status === 'scheduled') {
            return new Date(a.scheduled_time) - new Date(b.scheduled_time);
        }
        if (a.status === 'scheduled') return -1;
        if (b.status === 'scheduled') return 1;
        
        return new Date(b.created_at) - new Date(a.created_at);
    });
    
    container.innerHTML = `
        <div class="queue-list">
            ${sortedJobs.map(job => renderJobCard(job)).join('')}
        </div>
    `;
}

/**
 * Render a single job card
 */
function renderJobCard(job) {
    const statusClass = job.status;
    const statusLabel = getStatusLabel(job.status);
    const scheduleInfo = getScheduledInfo(job);
    
    return `
        <div class="card job-card ${statusClass}" data-job-id="${job.id}">
            <div class="card-body">
                <div class="job-card-content">
                    <div class="job-card-main">
                        <div class="job-card-header">
                            <h5 class="job-card-title">${escapeHtml(job.name)}</h5>
                            <span class="status-badge ${statusClass}">${statusLabel}</span>
                            ${job.queue_position ? `<span class="badge bg-secondary">Position: ${job.queue_position}</span>` : ''}
                        </div>
                        <div class="job-card-meta">
                            <span><i class="bi bi-globe"></i> ${getSourceTypeLabel(job.source_type)}</span>
                            <span><i class="bi bi-search"></i> ${escapeHtml(job.query)}</span>
                            <span><i class="bi bi-list-ol"></i> Max: ${job.max_results}</span>
                            ${scheduleInfo}
                            <span><i class="bi bi-clock"></i> Created: ${formatDate(job.created_at)}</span>
                        </div>
                        ${job.equipment_type || job.manufacturer ? `
                            <div class="job-card-meta mt-2">
                                ${job.equipment_type ? `<span><i class="bi bi-box-seam"></i> ${escapeHtml(job.equipment_type)}</span>` : ''}
                                ${job.manufacturer ? `<span><i class="bi bi-building"></i> ${escapeHtml(job.manufacturer)}</span>` : ''}
                            </div>
                        ` : ''}
                        ${job.status === 'running' && job.progress ? `
                            <div class="job-progress">
                                <div class="job-progress-bar" style="width: ${job.progress}%"></div>
                            </div>
                        ` : ''}
                        ${job.error_message ? `
                            <div class="alert alert-danger mt-2 mb-0">
                                <small><i class="bi bi-exclamation-triangle"></i> ${escapeHtml(job.error_message)}</small>
                            </div>
                        ` : ''}
                    </div>
                    <div class="job-actions">
                        ${job.status === 'queued' ? `
                            <button class="btn btn-outline-primary btn-sm" onclick="runJobNow(${job.id})" title="Run Now">
                                <i class="bi bi-play-fill"></i>
                            </button>
                        ` : ''}
                        ${job.status === 'running' ? `
                            <button class="btn btn-outline-danger btn-sm" onclick="stopJob(${job.id})" title="Stop">
                                <i class="bi bi-stop-fill"></i>
                            </button>
                        ` : ''}
                        <button class="btn btn-outline-secondary btn-sm" onclick="editJob(${job.id})" title="Edit">
                            <i class="bi bi-pencil"></i>
                        </button>
                        ${job.status !== 'running' ? `
                            <button class="btn btn-outline-danger btn-sm" onclick="deleteJob(${job.id})" title="Delete">
                                <i class="bi bi-trash"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Get status label
 */
function getStatusLabel(status) {
    const labels = {
        'queued': 'Queued',
        'scheduled': 'Scheduled',
        'running': 'Running',
        'completed': 'Completed',
        'failed': 'Failed'
    };
    return labels[status] || status;
}

/**
 * Get source type label
 */
function getSourceTypeLabel(type) {
    const labels = {
        'search': 'Search Engine',
        'forum': 'Forums',
        'manual_site': 'Manual Sites',
        'gdrive': 'Google Drive'
    };
    return labels[type] || type;
}

/**
 * Get scheduled info HTML
 */
function getScheduledInfo(job) {
    if (!job.scheduled_time) return '';
    
    const date = new Date(job.scheduled_time);
    const frequencyLabel = job.schedule_frequency ? `<span class="frequency-badge ${job.schedule_frequency}">${job.schedule_frequency}</span>` : '';
    
    return `
        <span><i class="bi bi-calendar-event"></i> ${formatDate(job.scheduled_time)} ${frequencyLabel}</span>
    `;
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Generate scrape configuration using AI
 */
async function generateScrapeConfig() {
    const prompt = document.getElementById('aiPrompt').value.trim();
    
    if (!prompt) {
        showError('Please enter a description of what you want to scrape.');
        return;
    }
    
    const loadingDiv = document.getElementById('aiLoading');
    const resultDiv = document.getElementById('aiResult');
    const generateBtn = document.getElementById('generateConfigBtn');
    
    loadingDiv.style.display = 'flex';
    resultDiv.style.display = 'none';
    generateBtn.disabled = true;
    
    try {
        const response = await fetch('/api/scrape-jobs/generate-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt })
        });
        
        if (!response.ok) throw new Error('Failed to generate configuration');
        
        const config = await response.json();
        
        // Populate the manual form with generated config
        document.getElementById('jobName').value = config.name || '';
        document.getElementById('sourceType').value = config.source_type || 'search';
        document.getElementById('searchQuery').value = config.query || '';
        document.getElementById('maxResults').value = config.max_results || 10;
        document.getElementById('equipmentType').value = config.equipment_type || '';
        document.getElementById('manufacturer').value = config.manufacturer || '';
        
        // Switch to manual tab to show the generated config
        const manualTab = new bootstrap.Tab(document.querySelector('#manual-tab'));
        manualTab.show();
        
        resultDiv.innerHTML = `
            <div class="alert alert-success">
                <h6><i class="bi bi-check-circle"></i> Configuration Generated!</h6>
                <p class="mb-0">Review and adjust the settings below, then click "Create Job".</p>
            </div>
            <div class="config-preview">
                <h6>Generated Configuration:</h6>
                <div class="config-item">
                    <span class="config-label">Name:</span>
                    <span class="config-value">${escapeHtml(config.name || 'N/A')}</span>
                </div>
                <div class="config-item">
                    <span class="config-label">Source:</span>
                    <span class="config-value">${getSourceTypeLabel(config.source_type)}</span>
                </div>
                <div class="config-item">
                    <span class="config-label">Query:</span>
                    <span class="config-value">${escapeHtml(config.query || 'N/A')}</span>
                </div>
                <div class="config-item">
                    <span class="config-label">Max Results:</span>
                    <span class="config-value">${config.max_results || 10}</span>
                </div>
                ${config.equipment_type ? `
                <div class="config-item">
                    <span class="config-label">Equipment Type:</span>
                    <span class="config-value">${escapeHtml(config.equipment_type)}</span>
                </div>
                ` : ''}
                ${config.manufacturer ? `
                <div class="config-item">
                    <span class="config-label">Manufacturer:</span>
                    <span class="config-value">${escapeHtml(config.manufacturer)}</span>
                </div>
                ` : ''}
            </div>
        `;
        resultDiv.style.display = 'block';
        
    } catch (error) {
        console.error('Error generating config:', error);
        showError('Failed to generate configuration. Please try again.');
    } finally {
        loadingDiv.style.display = 'none';
        generateBtn.disabled = false;
    }
}

/**
 * Create a new scrape job
 */
async function createScrapeJob() {
    const jobData = {
        name: document.getElementById('jobName').value.trim(),
        source_type: document.getElementById('sourceType').value,
        query: document.getElementById('searchQuery').value.trim(),
        max_results: parseInt(document.getElementById('maxResults').value) || 10,
        scheduled_time: document.getElementById('scheduleTime').value || null,
        schedule_frequency: document.getElementById('scheduleFrequency').value || null,
        equipment_type: document.getElementById('equipmentType').value.trim() || null,
        manufacturer: document.getElementById('manufacturer').value.trim() || null
    };
    
    if (!jobData.name) {
        showError('Please enter a job name.');
        return;
    }
    
    if (!jobData.query) {
        showError('Please enter a search query.');
        return;
    }
    
    try {
        const response = await fetch('/api/scrape-jobs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(jobData)
        });
        
        if (!response.ok) throw new Error('Failed to create job');
        
        // Close modal and refresh
        const modal = bootstrap.Modal.getInstance(document.getElementById('newJobModal'));
        modal.hide();
        
        // Reset form
        document.getElementById('manualJobForm').reset();
        document.getElementById('aiJobForm').reset();
        document.getElementById('aiResult').style.display = 'none';
        
        refreshQueue();
        showSuccess('Scrape job created successfully!');
        
    } catch (error) {
        console.error('Error creating job:', error);
        showError('Failed to create scrape job. Please try again.');
    }
}

/**
 * Edit a scrape job
 */
function editJob(jobId) {
    const job = scrapeJobs.find(j => j.id === jobId);
    if (!job) return;
    
    currentEditingJobId = jobId;
    
    document.getElementById('editJobId').value = job.id;
    document.getElementById('editJobName').value = job.name;
    document.getElementById('editSourceType').value = job.source_type;
    document.getElementById('editSearchQuery').value = job.query;
    document.getElementById('editMaxResults').value = job.max_results;
    document.getElementById('editScheduleTime').value = job.scheduled_time ? job.scheduled_time.slice(0, 16) : '';
    document.getElementById('editScheduleFrequency').value = job.schedule_frequency || '';
    document.getElementById('editEquipmentType').value = job.equipment_type || '';
    document.getElementById('editManufacturer').value = job.manufacturer || '';
    
    const modal = new bootstrap.Modal(document.getElementById('editJobModal'));
    modal.show();
}

/**
 * Update a scrape job
 */
async function updateScrapeJob() {
    const jobId = currentEditingJobId;
    
    const jobData = {
        name: document.getElementById('editJobName').value.trim(),
        source_type: document.getElementById('editSourceType').value,
        query: document.getElementById('editSearchQuery').value.trim(),
        max_results: parseInt(document.getElementById('editMaxResults').value) || 10,
        scheduled_time: document.getElementById('editScheduleTime').value || null,
        schedule_frequency: document.getElementById('editScheduleFrequency').value || null,
        equipment_type: document.getElementById('editEquipmentType').value.trim() || null,
        manufacturer: document.getElementById('editManufacturer').value.trim() || null
    };
    
    if (!jobData.name) {
        showError('Please enter a job name.');
        return;
    }
    
    if (!jobData.query) {
        showError('Please enter a search query.');
        return;
    }
    
    try {
        const response = await fetch(`/api/scrape-jobs/${jobId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(jobData)
        });
        
        if (!response.ok) throw new Error('Failed to update job');
        
        // Close modal and refresh
        const modal = bootstrap.Modal.getInstance(document.getElementById('editJobModal'));
        modal.hide();
        
        currentEditingJobId = null;
        refreshQueue();
        showSuccess('Scrape job updated successfully!');
        
    } catch (error) {
        console.error('Error updating job:', error);
        showError('Failed to update scrape job. Please try again.');
    }
}

/**
 * Delete a scrape job
 */
async function deleteJob(jobId) {
    if (!confirm('Are you sure you want to delete this scrape job?')) return;
    
    try {
        const response = await fetch(`/api/scrape-jobs/${jobId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Failed to delete job');
        
        refreshQueue();
        showSuccess('Scrape job deleted successfully!');
        
    } catch (error) {
        console.error('Error deleting job:', error);
        showError('Failed to delete scrape job. Please try again.');
    }
}

/**
 * Run a job immediately
 */
async function runJobNow(jobId) {
    try {
        const response = await fetch(`/api/scrape-jobs/${jobId}/run`, {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error('Failed to run job');
        
        refreshQueue();
        showSuccess('Job started successfully!');
        
    } catch (error) {
        console.error('Error running job:', error);
        showError('Failed to run job. Please try again.');
    }
}

/**
 * Stop a running job
 */
async function stopJob(jobId) {
    try {
        const response = await fetch(`/api/scrape-jobs/${jobId}/stop`, {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error('Failed to stop job');
        
        refreshQueue();
        showSuccess('Job stopped successfully!');
        
    } catch (error) {
        console.error('Error stopping job:', error);
        showError('Failed to stop job. Please try again.');
    }
}

/**
 * Show success toast
 */
function showSuccess(message) {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-success border-0';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi bi-check-circle me-2"></i>${escapeHtml(message)}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    showToast(toast);
}

/**
 * Show error toast
 */
function showError(message) {
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-danger border-0';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi bi-exclamation-circle me-2"></i>${escapeHtml(message)}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    showToast(toast);
}

/**
 * Show toast
 */
function showToast(toastElement) {
    // Create toast container if it doesn't exist
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }
    
    container.appendChild(toastElement);
    
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}
