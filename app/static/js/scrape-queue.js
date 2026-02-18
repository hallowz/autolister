/**
 * Scrape Queue Page JavaScript
 */

// Global state
let scrapeJobs = [];
let currentEditingJobId = null;
let autostartEnabled = false;
let currentScrapeInterval = null;
let currentViewingJobId = null; // For job details modal

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
    const logsSection = document.getElementById('scrape-logs-section');
    
    if (!data.running || !data.job) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="bi bi-pause-circle fs-1"></i>
                <p class="mt-2">No scrape job currently running</p>
            </div>
        `;
        logsSection.style.display = 'none';
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
    
    // Show logs section when job is running
    logsSection.style.display = 'block';
    
    // Load logs for the current job
    loadScrapeLogs(job.id);
}

/**
 * Load scrape logs for a job
 */
async function loadScrapeLogs(jobId) {
    try {
        const response = await fetch(`/api/scrape-jobs/${jobId}/logs`);
        if (!response.ok) throw new Error('Failed to load logs');
        
        const data = await response.json();
        displayScrapeLogs(data.logs);
    } catch (error) {
        console.error('Error loading scrape logs:', error);
        // Don't show error toast, just log it
    }
}

/**
 * Display scrape logs
 */
function displayScrapeLogs(logs) {
    const logsContainer = document.getElementById('scrape-logs');
    
    if (!logs || logs.length === 0) {
        logsContainer.innerHTML = '<div class="text-muted">No logs yet. Start a scrape job to see output.</div>';
        return;
    }
    
    let html = '';
    logs.forEach(log => {
        const time = new Date(log.time).toLocaleTimeString();
        const messageClass = log.level ? `log-message ${log.level}` : 'log-message';
        html += `<div class="log-entry">
            <span class="log-time">[${time}]</span>
            <span class="${messageClass}">${escapeHtml(log.message)}</span>
        </div>`;
    });
    
    logsContainer.innerHTML = html;
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

/**
 * Toggle logs visibility
 */
function toggleLogs() {
    const logsContainer = document.getElementById('scrape-logs');
    const toggleIcon = document.getElementById('logs-toggle-icon');
    
    if (logsContainer.style.display === 'none') {
        logsContainer.style.display = 'block';
        toggleIcon.classList.remove('bi-chevron-down');
        toggleIcon.classList.add('bi-chevron-up');
    } else {
        logsContainer.style.display = 'none';
        toggleIcon.classList.remove('bi-chevron-up');
        toggleIcon.classList.add('bi-chevron-down');
    }
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
                        <button class="btn btn-outline-info btn-sm" onclick="viewJobDetails(${job.id})" title="View Details & Logs">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-outline-success btn-sm" onclick="cloneJob(${job.id})" title="Clone Job">
                            <i class="bi bi-copy"></i>
                        </button>
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
        'gdrive': 'Google Drive',
        'multi_site': 'Multi-Site Scraper'
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
        
        // Populate ALL AI-generated fields
        document.getElementById('aiGeneratedJobName').value = jobName || config.name || '';
        document.getElementById('aiGeneratedSourceType').value = config.source_type || 'multi_site';
        document.getElementById('aiGeneratedQuery').value = config.query || '';
        document.getElementById('aiGeneratedMaxResults').value = config.max_results || 100;
        
        // Equipment categorization
        document.getElementById('aiGeneratedEquipmentType').value = config.equipment_type || '';
        document.getElementById('aiGeneratedManufacturer').value = config.manufacturer || '';
        
        // Search/filter terms
        document.getElementById('aiGeneratedSearchTerms').value = config.search_terms || '';
        document.getElementById('aiGeneratedExcludeTerms').value = config.exclude_terms || '';
        
        // File filtering
        document.getElementById('aiGeneratedMinPages').value = config.min_pages || 5;
        document.getElementById('aiGeneratedMaxPages').value = config.max_pages || '';
        document.getElementById('aiGeneratedMinFileSizeMb').value = config.min_file_size_mb || 0.5;
        document.getElementById('aiGeneratedMaxFileSizeMb').value = config.max_file_size_mb || 100;
        document.getElementById('aiGeneratedFileExtensions').value = config.file_extensions || 'pdf';
        
        // Crawling behavior
        document.getElementById('aiGeneratedMaxDepth').value = config.max_depth || 3;
        document.getElementById('aiGeneratedFollowLinks').checked = config.follow_links !== false;
        document.getElementById('aiGeneratedExtractDirectories').checked = config.extract_directories !== false;
        document.getElementById('aiGeneratedSkipDuplicates').checked = config.skip_duplicates !== false;
        
        // Sites (if provided)
        if (config.sites) {
            document.getElementById('aiGeneratedSites').value = config.sites;
        }
        
        // Exclude sites (if provided)
        if (config.exclude_sites) {
            document.getElementById('aiGeneratedExcludeSites').value = config.exclude_sites;
        }
        
        // Autostart
        document.getElementById('aiGeneratedAutostartEnabled').checked = config.autostart_enabled || false;
        
        // Show the result section
        resultDiv.style.display = 'block';
        
        // Show a summary of what was generated
        showSuccess('Configuration generated! Review the settings below.');
        
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
         const aiSourceType = document.getElementById('aiGeneratedSourceType').value;
         
         // Build base job data
         jobData = {
             name: document.getElementById('aiGeneratedJobName').value.trim(),
             source_type: aiSourceType,
             query: document.getElementById('aiGeneratedQuery').value.trim(),
             max_results: parseInt(document.getElementById('aiGeneratedMaxResults').value) || 100,
             scheduled_time: document.getElementById('aiGeneratedScheduleTime').value || null,
             schedule_frequency: document.getElementById('aiGeneratedScheduleFrequency').value || null,
             equipment_type: document.getElementById('aiGeneratedEquipmentType').value.trim() || null,
             manufacturer: document.getElementById('aiGeneratedManufacturer').value.trim() || null,
             autostart_enabled: document.getElementById('aiGeneratedAutostartEnabled').checked || false,
             // Advanced settings
             search_terms: document.getElementById('aiGeneratedSearchTerms').value.trim() || null,
             exclude_terms: document.getElementById('aiGeneratedExcludeTerms').value.trim() || null,
             min_pages: parseInt(document.getElementById('aiGeneratedMinPages').value) || null,
             max_pages: parseInt(document.getElementById('aiGeneratedMaxPages').value) || null,
             min_file_size_mb: parseFloat(document.getElementById('aiGeneratedMinFileSizeMb').value) || null,
             max_file_size_mb: parseFloat(document.getElementById('aiGeneratedMaxFileSizeMb').value) || null,
             follow_links: document.getElementById('aiGeneratedFollowLinks').checked,
             max_depth: parseInt(document.getElementById('aiGeneratedMaxDepth').value) || 2,
             extract_directories: document.getElementById('aiGeneratedExtractDirectories').checked,
             file_extensions: document.getElementById('aiGeneratedFileExtensions').value.trim() || 'pdf',
             skip_duplicates: document.getElementById('aiGeneratedSkipDuplicates').checked,
             traversal_pattern: document.getElementById('aiGeneratedTraversalPattern').value.trim() || null
         };
         
         // Add multi-site specific settings if source type is multi_site
         if (aiSourceType === 'multi_site') {
             const sitesValue = document.getElementById('aiGeneratedSites').value.trim();
             let allSites = [];
             if (sitesValue) {
                 allSites = sitesValue.split('\n').filter(s => s.trim());
             }
             jobData.sites = allSites.length > 0 ? JSON.stringify(allSites) : null;
             
             // Exclude sites
             const excludeSitesValue = document.getElementById('aiGeneratedExcludeSites').value.trim();
             let excludeSites = [];
             if (excludeSitesValue) {
                 excludeSites = excludeSitesValue.split('\n').filter(s => s.trim());
             }
             jobData.exclude_sites = excludeSites.length > 0 ? JSON.stringify(excludeSites) : null;
         }
     } else {
         // Use manual form
         const sourceType = document.getElementById('sourceType').value;
         
         if (sourceType === 'multi_site') {
             // Multi-site scraping with DuckDuckGo
             const ddgQuery = document.getElementById('ddgSearchQuery').value.trim();
             const sitesValue = document.getElementById('sites').value.trim();
             const excludeSitesValue = document.getElementById('excludeSites').value.trim();
             
             // Combine DuckDuckGo query with additional sites
             let allSites = [];
             if (sitesValue) {
                 allSites = sitesValue.split('\n').filter(s => s.trim());
             }
             
             // Parse exclude sites
             let excludeSites = [];
             if (excludeSitesValue) {
                 excludeSites = excludeSitesValue.split('\n').filter(s => s.trim());
             }
             
             jobData = {
                 name: document.getElementById('jobName').value.trim(),
                 source_type: sourceType,
                 query: ddgQuery || 'multi-site scraping',
                 max_results: parseInt(document.getElementById('maxResults').value) || 100,
                 scheduled_time: document.getElementById('scheduleTime').value || null,
                 schedule_frequency: document.getElementById('scheduleFrequency').value || null,
                 equipment_type: document.getElementById('equipmentType').value.trim() || null,
                 manufacturer: document.getElementById('manufacturer').value.trim() || null,
                 autostart_enabled: document.getElementById('autostartEnabled').checked || false,
                 // Advanced settings
                 sites: allSites.length > 0 ? JSON.stringify(allSites) : null,
                 exclude_sites: excludeSites.length > 0 ? JSON.stringify(excludeSites) : null,
                 search_terms: document.getElementById('searchTerms').value.trim() || null,
                 exclude_terms: document.getElementById('excludeTerms').value.trim() || null,
                 min_pages: parseInt(document.getElementById('minPages').value) || 5,
                 max_pages: null,
                 min_file_size_mb: parseFloat(document.getElementById('minFileSizeMb').value) || null,
                 max_file_size_mb: parseFloat(document.getElementById('maxFileSizeMb').value) || null,
                 follow_links: document.getElementById('followLinks').checked,
                 max_depth: parseInt(document.getElementById('maxDepth').value) || 2,
                 extract_directories: document.getElementById('extractDirectories').checked,
                 file_extensions: document.getElementById('fileExtensions').value.trim() || 'pdf',
                 skip_duplicates: document.getElementById('skipDuplicates').checked
             };
         } else {
             // Regular search scraping
             jobData = {
                 name: document.getElementById('jobName').value.trim(),
                 source_type: sourceType,
                 query: document.getElementById('searchQuery').value.trim(),
                 max_results: parseInt(document.getElementById('maxResults').value) || 10,
                 scheduled_time: document.getElementById('scheduleTime').value || null,
                 schedule_frequency: document.getElementById('scheduleFrequency').value || null,
                 equipment_type: document.getElementById('equipmentType').value.trim() || null,
                 manufacturer: document.getElementById('manufacturer').value.trim() || null,
                 autostart_enabled: document.getElementById('autostartEnabled').checked || false,
                 // Advanced settings
                 search_terms: document.getElementById('searchTerms').value.trim() || null,
                 exclude_terms: document.getElementById('excludeTerms').value.trim() || null,
                 min_pages: parseInt(document.getElementById('minPages').value) || 5,
                 max_pages: parseInt(document.getElementById('maxPages').value) || null,
                 min_file_size_mb: parseFloat(document.getElementById('minFileSizeMb').value) || null,
                 max_file_size_mb: parseFloat(document.getElementById('maxFileSizeMb').value) || null,
                 follow_links: document.getElementById('followLinks').checked,
                 max_depth: parseInt(document.getElementById('maxDepth').value) || 2,
                 extract_directories: document.getElementById('extractDirectories').checked,
                 file_extensions: document.getElementById('fileExtensions').value.trim() || 'pdf',
                 skip_duplicates: document.getElementById('skipDuplicates').checked
             };
         }
     }
     
     if (!jobData.name) {
         showError('Please enter a job name.');
         return;
     }
     
     // For multi-site, query is optional (DuckDuckGo will find sites if no sites provided)
     if (jobData.source_type !== 'multi_site' && !jobData.query) {
         showError('Please enter a search query.');
         return;
     }
     
     // For multi-site, sites is optional (DuckDuckGo will find sites)
     // but if provided, validate it's not empty after parsing
     if (jobData.source_type === 'multi_site' && jobData.sites) {
         try {
             const parsedSites = JSON.parse(jobData.sites);
             if (!Array.isArray(parsedSites) || parsedSites.length === 0) {
                 jobData.sites = null; // Clear if empty array
             }
         } catch (e) {
             showError('Invalid sites format.');
             return;
         }
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
async function editJob(jobId) {
    const job = scrapeJobs.find(j => j.id === jobId);
    if (!job) return;

    currentEditingJobId = jobId;

    // Show warning if job has already run
    const statusAlert = document.getElementById('editJobStatusAlert');
    const statusMessage = document.getElementById('editJobStatusMessage');

    if (job.status === 'completed' || job.status === 'failed') {
        statusAlert.style.display = 'block';
        statusAlert.className = 'alert alert-warning';
        statusMessage.textContent = `This job has already ${job.status}. Editing will create a new job configuration. Consider cloning instead.`;
    } else if (job.status === 'running') {
        statusAlert.style.display = 'block';
        statusAlert.className = 'alert alert-danger';
        statusMessage.textContent = 'This job is currently running. You cannot edit it while it is active.';
    } else {
        statusAlert.style.display = 'none';
    }

    // Load full configuration
    try {
        const response = await fetch(`/api/scrape-jobs/${jobId}/full-config`);
        if (!response.ok) throw new Error('Failed to fetch job config');
        const config = await response.json();

        // Populate all form fields
        document.getElementById('editJobId').value = config.id;
        document.getElementById('editJobName').value = config.name || '';
        document.getElementById('editSourceType').value = config.source_type || 'multi_site';

        // Query field (use as DuckDuckGo query for multi-site)
        document.getElementById('editDdgSearchQuery').value = config.query || '';

        // Sites
        if (config.sites) {
            try {
                const sites = JSON.parse(config.sites);
                document.getElementById('editSites').value = sites.join('\n');
            } catch {
                document.getElementById('editSites').value = config.sites;
            }
        } else {
            document.getElementById('editSites').value = '';
        }

        // Exclude sites
        if (config.exclude_sites) {
            try {
                const excludeSites = JSON.parse(config.exclude_sites);
                document.getElementById('editExcludeSites').value = excludeSites.join('\n');
            } catch {
                document.getElementById('editExcludeSites').value = config.exclude_sites;
            }
        } else {
            document.getElementById('editExcludeSites').value = '';
        }

        // Search & Filter settings
        document.getElementById('editMaxResults').value = config.max_results || 100;
        document.getElementById('editFileExtensions').value = config.file_extensions || 'pdf';
        document.getElementById('editSearchTerms').value = config.search_terms || '';
        document.getElementById('editExcludeTerms').value = config.exclude_terms || '';
        document.getElementById('editMinPages').value = config.min_pages || '';
        document.getElementById('editMaxPages').value = config.max_pages || '';
        document.getElementById('editMaxDepth').value = config.max_depth || 2;
        document.getElementById('editMinFileSizeMb').value = config.min_file_size_mb || '';
        document.getElementById('editMaxFileSizeMb').value = config.max_file_size_mb || '';

        // Checkboxes
        document.getElementById('editFollowLinks').checked = config.follow_links !== false;
        document.getElementById('editExtractDirectories').checked = config.extract_directories !== false;
        document.getElementById('editSkipDuplicates').checked = config.skip_duplicates !== false;

        // Categorization
        document.getElementById('editEquipmentType').value = config.equipment_type || '';
        document.getElementById('editManufacturer').value = config.manufacturer || '';

        // Scheduling
        document.getElementById('editScheduleTime').value = config.scheduled_time ? config.scheduled_time.slice(0, 16) : '';
        document.getElementById('editScheduleFrequency').value = config.schedule_frequency || '';
        document.getElementById('editAutostartEnabled').checked = config.autostart_enabled || false;

        // Toggle multi-site fields visibility
        toggleEditMultiSiteFields();

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('editJobModal'));
        modal.show();

    } catch (error) {
        console.error('Error loading job for edit:', error);
        showError('Failed to load job configuration for editing.');
    }
}

/**
 * Toggle multi-site fields in edit modal
 */
function toggleEditMultiSiteFields() {
    const sourceType = document.getElementById('editSourceType').value;
    const multiSiteFields = document.getElementById('editMultiSiteFields');

    if (sourceType === 'multi_site') {
        multiSiteFields.style.display = 'block';
    } else {
        multiSiteFields.style.display = 'none';
    }
}

/**
 * Update a scrape job
 */
async function updateScrapeJob() {
    const jobId = currentEditingJobId;

    // Get the job to check status
    const job = scrapeJobs.find(j => j.id === jobId);

    // Parse sites from textarea
    const sitesValue = document.getElementById('editSites').value.trim();
    let sites = null;
    if (sitesValue) {
        const siteLines = sitesValue.split('\n').filter(s => s.trim());
        if (siteLines.length > 0) {
            sites = JSON.stringify(siteLines);
        }
    }

    // Parse exclude sites from textarea
    const excludeSitesValue = document.getElementById('editExcludeSites').value.trim();
    let excludeSites = null;
    if (excludeSitesValue) {
        const excludeSiteLines = excludeSitesValue.split('\n').filter(s => s.trim());
        if (excludeSiteLines.length > 0) {
            excludeSites = JSON.stringify(excludeSiteLines);
        }
    }

    const jobData = {
        name: document.getElementById('editJobName').value.trim(),
        source_type: document.getElementById('editSourceType').value,
        query: document.getElementById('editDdgSearchQuery').value.trim(),
        max_results: parseInt(document.getElementById('editMaxResults').value) || 100,
        scheduled_time: document.getElementById('editScheduleTime').value || null,
        schedule_frequency: document.getElementById('editScheduleFrequency').value || null,
        equipment_type: document.getElementById('editEquipmentType').value.trim() || null,
        manufacturer: document.getElementById('editManufacturer').value.trim() || null,
        autostart_enabled: document.getElementById('editAutostartEnabled').checked,
        // Advanced settings
        sites: sites,
        exclude_sites: excludeSites,
        search_terms: document.getElementById('editSearchTerms').value.trim() || null,
        exclude_terms: document.getElementById('editExcludeTerms').value.trim() || null,
        min_pages: parseInt(document.getElementById('editMinPages').value) || null,
        max_pages: parseInt(document.getElementById('editMaxPages').value) || null,
        min_file_size_mb: parseFloat(document.getElementById('editMinFileSizeMb').value) || null,
        max_file_size_mb: parseFloat(document.getElementById('editMaxFileSizeMb').value) || null,
        follow_links: document.getElementById('editFollowLinks').checked,
        max_depth: parseInt(document.getElementById('editMaxDepth').value) || 2,
        extract_directories: document.getElementById('editExtractDirectories').checked,
        file_extensions: document.getElementById('editFileExtensions').value.trim() || 'pdf',
        skip_duplicates: document.getElementById('editSkipDuplicates').checked
    };

    if (!jobData.name) {
        showError('Please enter a job name.');
        return;
    }

    if (!jobData.query) {
        showError('Please enter a search query.');
        return;
    }

    // Check if job has already run - if so, show confirmation
    if (job && (job.status === 'completed' || job.status === 'failed')) {
        if (!confirm('This job has already run. Saving will update the configuration, but won\'t re-run the job. Consider cloning to create a new job with these settings. Continue?')) {
            return;
        }
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
 * Clone a scrape job
 */
async function cloneJob(jobId) {
    try {
        const response = await fetch(`/api/scrape-jobs/${jobId}/clone`, {
            method: 'POST'
        });

        if (!response.ok) throw new Error('Failed to clone job');

        const newJob = await response.json();
        refreshQueue();
        showSuccess(`Job cloned successfully! New job: ${newJob.name}`);

    } catch (error) {
        console.error('Error cloning job:', error);
        showError('Failed to clone job. Please try again.');
    }
}

/**
 * View job details and logs
 */
async function viewJobDetails(jobId) {
    currentViewingJobId = jobId;

    try {
        // Fetch full job config
        const configResponse = await fetch(`/api/scrape-jobs/${jobId}/full-config`);
        if (!configResponse.ok) throw new Error('Failed to fetch job config');
        const config = await configResponse.json();

        // Fetch job logs
        const logsResponse = await fetch(`/api/scrape-jobs/${jobId}/logs`);
        if (!logsResponse.ok) throw new Error('Failed to fetch job logs');
        const logsData = await logsResponse.json();

        // Render job configuration
        renderJobConfigDetails(config);

        // Render logs
        renderJobLogs(logsData.logs);

        // Update clone button in modal
        document.getElementById('cloneFromDetailsBtn').onclick = () => {
            bootstrap.Modal.getInstance(document.getElementById('jobDetailsModal')).hide();
            cloneJob(jobId);
        };

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('jobDetailsModal'));
        modal.show();

    } catch (error) {
        console.error('Error viewing job details:', error);
        showError('Failed to load job details. Please try again.');
    }
}

/**
 * Render job configuration details in modal
 */
function renderJobConfigDetails(config) {
    const container = document.getElementById('jobConfigDetails');

    const formatValue = (value) => {
        if (value === null || value === undefined || value === '') return '<span class="text-muted">Not set</span>';
        return escapeHtml(String(value));
    };

    container.innerHTML = `
        <div class="col-md-6">
            <table class="table table-sm">
                <tbody>
                    <tr><th>Name</th><td>${formatValue(config.name)}</td></tr>
                    <tr><th>Status</th><td><span class="badge bg-${getStatusBadgeClass(config.status)}">${getStatusLabel(config.status)}</span></td></tr>
                    <tr><th>Source Type</th><td>${formatValue(getSourceTypeLabel(config.source_type))}</td></tr>
                    <tr><th>Query</th><td><code>${formatValue(config.query)}</code></td></tr>
                    <tr><th>Max Results</th><td>${formatValue(config.max_results)}</td></tr>
                    <tr><th>Equipment Type</th><td>${formatValue(config.equipment_type)}</td></tr>
                    <tr><th>Manufacturer</th><td>${formatValue(config.manufacturer)}</td></tr>
                </tbody>
            </table>
        </div>
        <div class="col-md-6">
            <table class="table table-sm">
                <tbody>
                    <tr><th>Search Terms</th><td>${formatValue(config.search_terms)}</td></tr>
                    <tr><th>Exclude Terms</th><td>${formatValue(config.exclude_terms)}</td></tr>
                    <tr><th>File Extensions</th><td>${formatValue(config.file_extensions)}</td></tr>
                    <tr><th>Min Pages</th><td>${formatValue(config.min_pages)}</td></tr>
                    <tr><th>Max Pages</th><td>${formatValue(config.max_pages)}</td></tr>
                    <tr><th>File Size (MB)</th><td>${formatValue(config.min_file_size_mb)} - ${formatValue(config.max_file_size_mb)}</td></tr>
                    <tr><th>Max Depth</th><td>${formatValue(config.max_depth)}</td></tr>
                    <tr><th>Follow Links</th><td>${config.follow_links ? '<i class="bi bi-check-circle text-success"></i>' : '<i class="bi bi-x-circle text-danger"></i>'}</td></tr>
                    <tr><th>Extract Directories</th><td>${config.extract_directories ? '<i class="bi bi-check-circle text-success"></i>' : '<i class="bi bi-x-circle text-danger"></i>'}</td></tr>
                    <tr><th>Skip Duplicates</th><td>${config.skip_duplicates ? '<i class="bi bi-check-circle text-success"></i>' : '<i class="bi bi-x-circle text-danger"></i>'}</td></tr>
                    <tr><th>Autostart</th><td>${config.autostart_enabled ? '<i class="bi bi-check-circle text-success"></i>' : '<i class="bi bi-x-circle text-danger"></i>'}</td></tr>
                </tbody>
            </table>
        </div>
        ${config.sites ? `
        <div class="col-12 mt-2">
            <strong>Sites:</strong>
            <pre class="bg-light p-2 mt-1" style="max-height: 150px; overflow-y: auto;">${escapeHtml(config.sites)}</pre>
        </div>
        ` : ''}
        ${config.exclude_sites ? `
        <div class="col-12 mt-2">
            <strong>Excluded Sites:</strong>
            <pre class="bg-light p-2 mt-1" style="max-height: 150px; overflow-y: auto;">${escapeHtml(config.exclude_sites)}</pre>
        </div>
        ` : ''}
        ${config.error_message ? `
        <div class="col-12 mt-2">
            <div class="alert alert-danger mb-0">
                <strong>Error:</strong> ${escapeHtml(config.error_message)}
            </div>
        </div>
        ` : ''}
    `;
}

/**
 * Get badge class for status
 */
function getStatusBadgeClass(status) {
    const classes = {
        'queued': 'secondary',
        'scheduled': 'info',
        'running': 'primary',
        'completed': 'success',
        'failed': 'danger'
    };
    return classes[status] || 'secondary';
}

/**
 * Render job logs in modal
 */
function renderJobLogs(logs) {
    const container = document.getElementById('jobLogsContainer');

    if (!logs || logs.length === 0) {
        container.innerHTML = '<div class="text-muted">No logs available for this job.</div>';
        return;
    }

    let html = '';
    logs.forEach(log => {
        const time = new Date(log.time).toLocaleTimeString();
        const messageClass = log.level ? `log-message ${log.level}` : 'log-message';
        html += `<div class="log-entry">
            <span class="log-time">[${time}]</span>
            <span class="${messageClass}">${escapeHtml(log.message)}</span>
        </div>`;
    });

    container.innerHTML = html;
    container.scrollTop = container.scrollHeight;
}

/**
 * Populate form with existing job config for editing
 */
async function populateFormWithJob(jobId) {
    try {
        const response = await fetch(`/api/scrape-jobs/${jobId}/full-config`);
        if (!response.ok) throw new Error('Failed to fetch job config');
        const config = await response.json();

        // Populate manual form fields
        document.getElementById('jobName').value = config.name || '';
        document.getElementById('sourceType').value = config.source_type || 'multi_site';
        document.getElementById('ddgSearchQuery').value = config.query || '';
        document.getElementById('maxResults').value = config.max_results || 100;
        document.getElementById('searchTerms').value = config.search_terms || '';
        document.getElementById('excludeTerms').value = config.exclude_terms || '';
        document.getElementById('minPages').value = config.min_pages || 5;
        document.getElementById('equipmentType').value = config.equipment_type || '';
        document.getElementById('manufacturer').value = config.manufacturer || '';
        document.getElementById('autostartEnabled').checked = config.autostart_enabled || false;
        document.getElementById('maxDepth').value = config.max_depth || 2;
        document.getElementById('followLinks').checked = config.follow_links !== false;
        document.getElementById('extractDirectories').checked = config.extract_directories !== false;
        document.getElementById('skipDuplicates').checked = config.skip_duplicates !== false;
        document.getElementById('fileExtensions').value = config.file_extensions || 'pdf';
        document.getElementById('minFileSizeMb').value = config.min_file_size_mb || '';
        document.getElementById('maxFileSizeMb').value = config.max_file_size_mb || '';

        // Handle sites (JSON array or string)
        if (config.sites) {
            try {
                const sites = JSON.parse(config.sites);
                document.getElementById('sites').value = sites.join('\n');
            } catch {
                document.getElementById('sites').value = config.sites;
            }
        }

        // Toggle multi-site fields visibility
        toggleMultiSiteFields();

        // Switch to manual tab
        document.querySelector('#manual-tab').click();

        // Show success message
        showSuccess('Job configuration loaded. Modify as needed and click Create Job.');

    } catch (error) {
        console.error('Error loading job config:', error);
        showError('Failed to load job configuration. Please try again.');
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

/**
 * Toggle multi-site fields visibility based on source type
 */
function toggleMultiSiteFields() {
    const sourceType = document.getElementById('sourceType').value;
    const multiSiteFields = document.getElementById('multiSiteFields');
    const searchQueryFields = document.getElementById('searchQueryFields');
    
    if (sourceType === 'multi_site') {
        multiSiteFields.style.display = 'block';
        searchQueryFields.style.display = 'none';
    } else {
        multiSiteFields.style.display = 'none';
        searchQueryFields.style.display = 'block';
    }
}
