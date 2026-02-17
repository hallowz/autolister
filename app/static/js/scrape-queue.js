/**
 * Scrape Queue Page JavaScript
 */

// Global state
let scrapeJobs = [];
let currentEditingJobId = null;
let autostartEnabled = false;
let currentScrapeInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    refreshQueue();
    refreshCurrentScrape();
    refreshAutostartStatus();
    // Auto-refresh current scrape every 5 seconds
    currentScrapeInterval = setInterval(refreshCurrentScrape, 5000);
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
        refreshAutostartStatus();
    } catch (error) {
        console.error('Error refreshing queue:', error);
        showError('Failed to refresh queue. Please try again.');
    }
}

/**
 * Refresh the current scrape status
 */
async function refreshCurrentScrape() {
    try {
        const response = await fetch('/api/scrape-jobs/current-scrape');
        if (!response.ok) throw new Error('Failed to fetch current scrape');
        
        const data = await response.json();
        renderCurrentScrape(data);
    } catch (error) {
        console.error('Error refreshing current scrape:', error);
    }
}

/**
 * Render the current scrape status
 */
function renderCurrentScrape(data) {
    const container = document.getElementById('current-scrape-container');
    
    if (!data.running || !data.job) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="bi bi-pause-circle fs-1"></i>
                <p class="mt-2">No scrape job currently running</p>
            </div>
        `;
        return;
    }
    
    const job = data.job;
    container.innerHTML = `
        <div class="current-scrape">
            <div class="row">
                <div class="col-md-8">
                    <h5 class="mb-2">${escapeHtml(job.name)}</h5>
                    <div class="scrape-details">
                        <span class="badge bg-primary">${getSourceTypeLabel(job.source_type)}</span>
                        <span class="text-muted ms-2"><i class="bi bi-search"></i> ${escapeHtml(job.query)}</span>
                        <span class="text-muted ms-2"><i class="bi bi-list-ol"></i> Max: ${job.max_results}</span>
                    </div>
                </div>
                <div class="col-md-4 text-end">
                    <div class="progress-indicator">
                        <div class="progress">
                            <div class="progress-bar progress-bar-striped progress-bar-animated"
                                 style="width: ${job.progress || 0}%"
                                 id="current-scrape-progress"></div>
                        </div>
                        <small class="text-muted">${job.progress || 0}% Complete</small>
                    </div>
                </div>
            </div>
            <div class="mt-2">
                <small class="text-muted">
                    <i class="bi bi-clock"></i> Started: ${formatDate(job.created_at)}
                    ${job.updated_at !== job.created_at ? ` | Updated: ${formatDate(job.updated_at)}` : ''}
                </small>
            </div>
        </div>
    `;
}

/**
 * Toggle autostart for queued jobs
 */
async function toggleAutostart() {
    try {
        const response = await fetch('/api/scrape-jobs/toggle-autostart', {
            method: 'POST'
        });
        if (!response.ok) throw new Error('Failed to toggle autostart');
        
        const data = await response.json();
        autostartEnabled = data.autostart_enabled;
        updateAutostartButton();
        showSuccess(data.message);
    } catch (error) {
        console.error('Error toggling autostart:', error);
        showError('Failed to toggle autostart. Please try again.');
    }
}

/**
 * Refresh autostart status from first queued job
 */
function refreshAutostartStatus() {
    const firstQueuedJob = scrapeJobs.find(j => j.status === 'queued');
    if (firstQueuedJob) {
        autostartEnabled = firstQueuedJob.autostart_enabled || false;
        updateAutostartButton();
    }
}

/**
 * Update autostart button appearance
 */
function updateAutostartButton() {
    const btn = document.getElementById('autostart-toggle-btn');
    const status = document.getElementById('autostart-status');
    
    if (autostartEnabled) {
        btn.classList.remove('btn-outline-secondary');
        btn.classList.add('btn-success');
        status.textContent = 'On';
    } else {
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-secondary');
        status.textContent = 'Off';
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
                            ${job.status === 'queued' && job.autostart_enabled ? `<span class="badge bg-success"><i class="bi bi-play-circle"></i> Autostart</span>` : ''}
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
    const jobName = document.getElementById('aiJobName').value.trim();
    
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
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || 'Failed to generate configuration');
        }
        
        const config = await response.json();
        
        // Populate AI-generated fields
        document.getElementById('aiGeneratedJobName').value = jobName || config.name || '';
        document.getElementById('aiGeneratedSourceType').value = config.source_type || 'search';
        document.getElementById('aiGeneratedQuery').value = config.query || '';
        document.getElementById('aiGeneratedMaxResults').value = config.max_results || 10;
        document.getElementById('aiGeneratedSearchTerms').value = config.search_terms || '';
        document.getElementById('aiGeneratedExcludeTerms').value = config.exclude_terms || '';
        document.getElementById('aiGeneratedMinPages').value = config.min_pages || 5;
        document.getElementById('aiGeneratedTraversalPattern').value = config.traversal_pattern || '';
        document.getElementById('aiGeneratedEquipmentType').value = config.equipment_type || '';
        document.getElementById('aiGeneratedManufacturer').value = config.manufacturer || '';
        
        // Show the result section with generated config
        // Note: The form fields are already in the HTML, we just need to show the result div
        resultDiv.style.display = 'block';
        
    } catch (error) {
        console.error('Error generating config:', error);
        showError(`Failed to generate configuration: ${error.message}`);
    } finally {
        loadingDiv.style.display = 'none';
        generateBtn.disabled = false;
    }
}

/**
 * Create a new scrape job
 */
async function createScrapeJob() {
    // Check which tab is active
    const aiTab = document.querySelector('#ai-tab').classList.contains('active');
    
    let jobData;
    
    if (aiTab) {
        // Use AI-generated form
        jobData = {
            name: document.getElementById('aiGeneratedJobName').value.trim(),
            source_type: document.getElementById('aiGeneratedSourceType').value,
            query: document.getElementById('aiGeneratedQuery').value.trim(),
            max_results: parseInt(document.getElementById('aiGeneratedMaxResults').value) || 10,
            scheduled_time: document.getElementById('aiGeneratedScheduleTime').value || null,
            schedule_frequency: document.getElementById('aiGeneratedScheduleFrequency').value || null,
            equipment_type: document.getElementById('aiGeneratedEquipmentType').value.trim() || null,
            manufacturer: document.getElementById('aiGeneratedManufacturer').value.trim() || null,
            autostart_enabled: document.getElementById('autostartEnabled').checked || false
        };
    } else {
        // Use manual form
        jobData = {
            name: document.getElementById('jobName').value.trim(),
            source_type: document.getElementById('sourceType').value,
            query: document.getElementById('searchQuery').value.trim(),
            max_results: parseInt(document.getElementById('maxResults').value) || 10,
            scheduled_time: document.getElementById('scheduleTime').value || null,
            schedule_frequency: document.getElementById('scheduleFrequency').value || null,
            equipment_type: document.getElementById('equipmentType').value.trim() || null,
            manufacturer: document.getElementById('manufacturer').value.trim() || null,
            autostart_enabled: document.getElementById('autostartEnabled').checked || false
        };
    }
    
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
        
        // Reset forms
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
