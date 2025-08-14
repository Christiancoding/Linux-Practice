// Global Appearance Settings Management
function setTheme(themeName) {
    console.log('Setting theme to:', themeName);
    document.documentElement.setAttribute('data-theme', themeName);
    localStorage.setItem('theme', themeName);
    
    // Also save to appSettings for consistency
    const settings = JSON.parse(localStorage.getItem('appSettings') || '{}');
    settings.theme = themeName;
    localStorage.setItem('appSettings', JSON.stringify(settings));
    
    // Update theme buttons if they exist
    document.querySelectorAll('.theme-option').forEach(btn => btn.classList.remove('active'));
    const themeButton = document.querySelector(`.theme-option[onclick="setTheme('${themeName}')"]`);
    if (themeButton) themeButton.classList.add('active');
    
    // Update theme icon
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.className = themeName === 'dark' ? 'fas fa-moon' : 
                             themeName === 'light' ? 'fas fa-sun' : 'fas fa-star';
    }
}

// Load all appearance settings globally
function loadGlobalAppearanceSettings() {
    console.log('Loading global appearance settings from app.js...');
    const settings = JSON.parse(localStorage.getItem('appSettings') || '{}');
    
    // Load theme (fallback to old theme storage)
    const savedTheme = settings.theme || localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
    
    // Load accent color
    const savedAccentColor = settings.accentColor || '#7c3aed';
    document.documentElement.style.setProperty('--primary-color', savedAccentColor);
    document.documentElement.style.setProperty('--accent-color', savedAccentColor);
    document.documentElement.style.setProperty('--gradient-primary', `linear-gradient(135deg, ${savedAccentColor}, ${savedAccentColor}88)`);
    
    // Load font size
    const savedFontSize = settings.fontSize || 100;
    document.documentElement.style.setProperty('--base-font-size', savedFontSize + '%');
    
    // Load animation settings
    const animationsEnabled = settings.animations !== false; // Default to enabled
    const reduceMotion = settings.reduceMotion === true; // Default to disabled
    
    document.body.classList.toggle('no-animations', !animationsEnabled);
    document.body.classList.toggle('reduce-motion', reduceMotion);
    
    console.log('Applied global settings:', {
        theme: savedTheme,
        accentColor: savedAccentColor,
        fontSize: savedFontSize + '%',
        animations: animationsEnabled,
        reduceMotion: reduceMotion
    });
}
// Global Analytics Tracking
class AnalyticsTracker {
    constructor() {
        this.sessionStart = Date.now();
        this.pageLoadStart = performance.now();
        this.userId = this.getUserId();
        this.sessionId = this.generateSessionId();
        this.interactions = [];
        this.errors = [];
        this.performanceMetrics = {};
        this.deviceInfo = this.collectDeviceInfo();
        
        this.initializeTracking();
    }
    
    getUserId() {
        let userId = localStorage.getItem('analytics_user_id');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('analytics_user_id', userId);
        }
        return userId;
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    collectDeviceInfo() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        return {
            userAgent: navigator.userAgent,
            language: navigator.language,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            screenResolution: `${screen.width}x${screen.height}`,
            viewportSize: `${window.innerWidth}x${window.innerHeight}`,
            pixelRatio: window.devicePixelRatio,
            platform: navigator.platform,
            cookiesEnabled: navigator.cookieEnabled,
            onlineStatus: navigator.onLine,
            cpuCores: navigator.hardwareConcurrency,
            touchSupport: 'ontouchstart' in window,
            webglSupport: !!ctx && !!ctx.getExtension,
            colorDepth: screen.colorDepth
        };
    }
    
    initializeTracking() {
        this.trackPageLoad();
        this.trackClicks();
        this.trackScrollDepth();
        this.trackFormInteractions();
        this.trackErrors();
        this.trackPerformance();
        this.trackTimeOnPage();
        this.trackNavigationPatterns();
    }
    
    trackPageLoad() {
        window.addEventListener('load', () => {
            const loadTime = performance.now() - this.pageLoadStart;
            this.performanceMetrics.pageLoadTime = loadTime;
            
            // Collect Core Web Vitals
            if ('web-vital' in window) {
                this.trackWebVitals();
            }
            
            this.sendEvent('page_load', {
                url: window.location.href,
                title: document.title,
                loadTime: loadTime,
                referrer: document.referrer
            });
        });
    }
    
    trackWebVitals() {
        // Track Core Web Vitals
        new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
                if (entry.entryType === 'paint') {
                    this.performanceMetrics[entry.name] = entry.startTime;
                }
                if (entry.entryType === 'largest-contentful-paint') {
                    this.performanceMetrics.LCP = entry.startTime;
                }
                if (entry.entryType === 'first-input') {
                    this.performanceMetrics.FID = entry.processingStart - entry.startTime;
                }
            }
        }).observe({entryTypes: ['paint', 'largest-contentful-paint', 'first-input']});
    }
    
    trackClicks() {
        document.addEventListener('click', (event) => {
            const target = event.target;
            const clickData = {
                element: target.tagName,
                class: target.className,
                id: target.id,
                text: target.textContent?.substr(0, 100),
                position: { x: event.clientX, y: event.clientY },
                timestamp: Date.now()
            };
            
            this.interactions.push({ type: 'click', data: clickData });
            this.sendEvent('user_interaction', { interaction_type: 'click', ...clickData });
        });
    }
    
    trackScrollDepth() {
        let maxScroll = 0;
        const scrollMilestones = [25, 50, 75, 100];
        const triggered = new Set();
        
        window.addEventListener('scroll', () => {
            const scrollPercent = Math.round(
                (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100
            );
            
            maxScroll = Math.max(maxScroll, scrollPercent);
            
            scrollMilestones.forEach(milestone => {
                if (scrollPercent >= milestone && !triggered.has(milestone)) {
                    triggered.add(milestone);
                    this.sendEvent('scroll_depth', { percentage: milestone });
                }
            });
        });
    }
    
    trackFormInteractions() {
        document.addEventListener('focus', (event) => {
            if (event.target.matches('input, textarea, select')) {
                this.sendEvent('form_interaction', {
                    action: 'field_focus',
                    fieldType: event.target.type,
                    fieldName: event.target.name || event.target.id
                });
            }
        });
        
        document.addEventListener('submit', (event) => {
            const form = event.target;
            if (form.tagName === 'FORM') {
                this.sendEvent('form_interaction', {
                    action: 'form_submit',
                    formId: form.id,
                    formClass: form.className
                });
            }
        });
    }
    
    trackErrors() {
        window.addEventListener('error', (event) => {
            const errorData = {
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                stack: event.error?.stack
            };
            
            this.errors.push(errorData);
            this.sendEvent('javascript_error', errorData);
        });
        
        window.addEventListener('unhandledrejection', (event) => {
            const errorData = {
                message: event.reason?.message || 'Unhandled Promise Rejection',
                stack: event.reason?.stack
            };
            
            this.errors.push(errorData);
            this.sendEvent('promise_rejection', errorData);
        });
    }
    
    trackPerformance() {
        // Track resource loading times
        window.addEventListener('load', () => {
            const resources = performance.getEntriesByType('resource');
            const slowResources = resources.filter(resource => resource.duration > 1000);
            
            if (slowResources.length > 0) {
                this.sendEvent('slow_resources', {
                    count: slowResources.length,
                    resources: slowResources.map(r => ({ name: r.name, duration: r.duration }))
                });
            }
        });
    }
    
    trackTimeOnPage() {
        this.pageVisitStart = Date.now();
        
        window.addEventListener('beforeunload', () => {
            const timeOnPage = Date.now() - this.pageVisitStart;
            this.sendEvent('page_exit', {
                timeOnPage: timeOnPage,
                interactions: this.interactions.length,
                errors: this.errors.length
            });
        });
        
        // Track active time (when page is visible and user is active)
        let activeTime = 0;
        let lastActivity = Date.now();
        let isActive = true;
        
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                if (isActive) {
                    activeTime += Date.now() - lastActivity;
                    isActive = false;
                }
            } else {
                lastActivity = Date.now();
                isActive = true;
            }
        });
        
        // Track mouse/keyboard activity
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
            document.addEventListener(event, () => {
                if (!isActive && !document.hidden) {
                    lastActivity = Date.now();
                    isActive = true;
                }
            }, { passive: true });
        });
        
        setInterval(() => {
            if (isActive && !document.hidden) {
                activeTime += 1000; // 1 second
                this.performanceMetrics.activeTime = activeTime;
            }
        }, 1000);
    }
    
    trackNavigationPatterns() {
        const navigationPattern = JSON.parse(sessionStorage.getItem('navigation_pattern') || '[]');
        navigationPattern.push({
            url: window.location.href,
            timestamp: Date.now(),
            referrer: document.referrer
        });
        
        // Keep only last 10 pages
        if (navigationPattern.length > 10) {
            navigationPattern.shift();
        }
        
        sessionStorage.setItem('navigation_pattern', JSON.stringify(navigationPattern));
    }
    
    trackQuizSession(data) {
        this.sendEvent('quiz_session', {
            questions_attempted: data.questions_attempted || 0,
            questions_correct: data.questions_correct || 0,
            session_duration: data.duration || 0,
            category: data.category || 'mixed',
            difficulty: data.difficulty || 'medium',
            completion_percentage: data.completion_percentage || 0
        });
    }
    
    trackFeatureUsage(feature, action, metadata = {}) {
        this.sendEvent('feature_usage', {
            feature: feature,
            action: action,
            ...metadata
        });
    }
    
    sendEvent(eventType, data) {
        const payload = {
            user_id: this.userId,
            session_id: this.sessionId,
            event_type: eventType,
            timestamp: Date.now(),
            url: window.location.href,
            user_agent: navigator.userAgent,
            device_info: this.deviceInfo,
            data: data
        };
        
        // Send to analytics endpoint
        fetch('/api/analytics/track', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        }).catch(error => {
            console.error('Analytics tracking error:', error);
        });
    }
    
    // Batch send events for better performance
    batchSendEvents() {
        if (this.eventQueue.length === 0) return;
        
        const events = [...this.eventQueue];
        this.eventQueue = [];
        
        fetch('/api/analytics/batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ events })
        }).catch(error => {
            console.error('Batch analytics error:', error);
            // Re-add events to queue on failure
            this.eventQueue.unshift(...events);
        });
    }
}

// Initialize global analytics tracker
window.analyticsTracker = new AnalyticsTracker();

// Global app functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('App.js DOMContentLoaded - initializing...');
    
    // Track page load completion
    window.analyticsTracker.sendEvent('page_ready', {
        page: window.location.pathname,
        loadTime: performance.now()
    });
    
    // Load appearance settings on every page load
    loadGlobalAppearanceSettings();

    // Initialize quiz timing if on quiz page
    if (window.location.pathname.includes('quiz')) {
        initializeQuizTiming();
    }

    // Update active nav link on every page
    updateActiveNavLink();

    // If we are on the settings page, load the settings from the server
    if (window.location.pathname.includes('settings')) {
        loadSettings();
        // Add event listeners for auto-saving settings on change
        const focusModeEl = document.getElementById('focusMode');
        const breakReminderEl = document.getElementById('breakReminder');

        if (focusModeEl) {
            focusModeEl.addEventListener('change', saveSettings);
        }
        if (breakReminderEl) {
            breakReminderEl.addEventListener('change', saveSettings);
        }
    }

    // Legacy dark mode check (for backward compatibility)
    if (localStorage.getItem('darkMode') === 'enabled') {
        document.body.classList.add('dark-mode');
    }

    // Add event listeners for buttons if they exist
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', toggleDarkMode);
    }

    const exportHistoryBtn = document.getElementById('exportHistoryBtn');
    if (exportHistoryBtn) {
        exportHistoryBtn.addEventListener('click', exportHistory);
    }

    const importHistoryBtn = document.getElementById('importHistoryBtn');
    if (importHistoryBtn) {
        importHistoryBtn.addEventListener('click', importHistory);
    }

    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', clearHistory);
    }
    
    // Add event listener for search functionality if it exists
    const searchInput = document.getElementById('searchInput');
    if(searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            const items = document.querySelectorAll('.searchable-item');
            
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                if (text.includes(query)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
});
function getNextQuestion() {
    fetch('/api/get_question')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert('Error: ' + data.error, 'danger');
                return;
            }

            if (data.quiz_complete) {
                endQuiz();
                return;
            }

            // Check for break reminder
            if (data.break_reminder) {
                showBreakReminder(data.questions_since_break, data.break_interval);
                return;
            }

            // Normal question display
            displayQuestion(data);
        })
        .catch(error => {
            console.error('Error getting next question:', error);
            showAlert('Failed to get next question', 'danger');
        });
}
function showBreakReminder(questionsSinceBreak, breakInterval) {
    // Create break reminder modal
    const modalHtml = `
        <div class="modal fade" id="breakReminderModal" tabindex="-1" aria-labelledby="breakReminderModalLabel" aria-hidden="true" data-bs-backdrop="static" data-bs-keyboard="false">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content bg-dark">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title text-info" id="breakReminderModalLabel">
                            <i class="fas fa-coffee"></i> Time for a Break!
                        </h5>
                    </div>
                    <div class="modal-body text-center">
                        <div class="mb-3">
                            <i class="fas fa-clock text-warning" style="font-size: 3rem;"></i>
                        </div>
                        <p class="mb-3">You've answered <strong>${questionsSinceBreak}</strong> questions.</p>
                        <p class="mb-3">Take a moment to rest your eyes and stretch!</p>
                        <div id="breakTimer" class="mb-3">
                            <div class="h4 text-info" id="timerDisplay">02:00</div>
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar bg-info" role="progressbar" style="width: 100%" id="timerProgress"></div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary justify-content-center">
                        <button type="button" class="btn btn-primary" onclick="skipBreak()">
                            <i class="fas fa-forward"></i> Skip Break
                        </button>
                        <button type="button" class="btn btn-success" onclick="takeBreak()" id="takeBreakBtn">
                            <i class="fas fa-play"></i> Start Break
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById('breakReminderModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('breakReminderModal'));
    modal.show();
}

function takeBreak() {
    const takeBreakBtn = document.getElementById('takeBreakBtn');
    const timerDisplay = document.getElementById('timerDisplay');
    const timerProgress = document.getElementById('timerProgress');
    
    takeBreakBtn.disabled = true;
    takeBreakBtn.innerHTML = '<i class="fas fa-pause"></i> Taking Break...';
    
    let breakDuration = 120; // 2 minutes in seconds
    let remainingTime = breakDuration;
    
    const countdown = setInterval(() => {
        const minutes = Math.floor(remainingTime / 60);
        const seconds = remainingTime % 60;
        
        timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        const progress = ((breakDuration - remainingTime) / breakDuration) * 100;
        timerProgress.style.width = progress + '%';
        
        remainingTime--;
        
        if (remainingTime < 0) {
            clearInterval(countdown);
            endBreak();
        }
    }, 1000);
}

function skipBreak() {
    acknowledgeBreak();
}

function endBreak() {
    showAlert('Break time is over! Ready to continue?', 'success');
    acknowledgeBreak();
}

function acknowledgeBreak() {
    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('breakReminderModal'));
    if (modal) {
        modal.hide();
    }
    
    // Remove modal from DOM
    setTimeout(() => {
        const modalElement = document.getElementById('breakReminderModal');
        if (modalElement) {
            modalElement.remove();
        }
    }, 300);
    
    // Notify backend that break was acknowledged
    fetch('/api/acknowledge_break', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Continue with next question
            getNextQuestion();
        } else {
            showAlert('Error acknowledging break', 'danger');
        }
    })
    .catch(error => {
        console.error('Error acknowledging break:', error);
        // Continue anyway
        getNextQuestion();
    });
}

/**
 * Updates the active state of the main navigation links based on the current URL path.
 */
function updateActiveNavLink() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');

    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

/**
 * Displays a dismissible alert message to the user.
 * @param {string} message - The message to display.
 * @param {string} type - The alert type (e.g., 'success', 'danger', 'info').
 */
function showAlert(message, type = 'info') {
    try {
        // Remove any existing alerts to prevent stacking
        const existingAlerts = document.querySelectorAll('.alert.position-fixed');
        existingAlerts.forEach(alert => alert.remove());

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        `;

        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        document.body.appendChild(alertDiv);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                const bsAlert = new bootstrap.Alert(alertDiv);
                if (bsAlert) {
                    bsAlert.close();
                } else {
                    alertDiv.remove();
                }
            }
        }, 5000);

    } catch (error) {
        console.error('Failed to show alert:', error);
        // Fallback to browser alert if the custom one fails
        alert(message);
    }
}

// --- Settings Management (API-driven) ---

/**
 * Saves settings to the backend by calling the /api/save_settings endpoint.
 */
function saveSettings() {
    // Track settings interaction
    if (window.analyticsTracker) {
        window.analyticsTracker.trackFeatureUsage('settings', 'save');
    }
    const elements = {
        focusMode: document.getElementById('focusMode'),
        breakReminder: document.getElementById('breakReminder'),
        debugMode: document.getElementById('debugMode'),
        pointsPerQuestion: document.getElementById('pointsPerQuestion'),
        streakBonus: document.getElementById('streakBonus'),
        maxStreakBonus: document.getElementById('maxStreakBonus')
    };

    // Check if we're on the settings page
    if (!elements.focusMode || !elements.breakReminder) {
        console.error('Settings elements not found on this page.');
        return;
    }

    const settings = {
        focusMode: elements.focusMode.checked,
        breakReminder: parseInt(elements.breakReminder.value) || 10,
        debugMode: elements.debugMode?.checked || false,
        pointsPerQuestion: parseInt(elements.pointsPerQuestion?.value) || 10,
        streakBonus: parseInt(elements.streakBonus?.value) || 5,
        maxStreakBonus: parseInt(elements.maxStreakBonus?.value) || 50
    };

    // Client-side validation
    if (settings.maxStreakBonus < settings.streakBonus) {
        showAlert('Max Streak Bonus cannot be less than Streak Bonus. Adjusting automatically.', 'warning');
        settings.maxStreakBonus = settings.streakBonus;
        if (elements.maxStreakBonus) {
            elements.maxStreakBonus.value = settings.maxStreakBonus;
        }
    }

    fetch('/api/save_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Settings saved successfully!', 'success');
            
            // Update form with server-validated values
            if (data.settings) {
                populateSettingsForm(data.settings);
            }
        } else {
            showAlert('Failed to save settings: ' + (data.error || 'Unknown server error'), 'danger');
        }
    })
    .catch(error => {
        console.error('Error saving settings:', error);
        showAlert('An error occurred while saving settings.', 'danger');
    });
}
/**
 * Populates the settings form with values from the provided settings object.
 * @param {Object} settings - The settings object containing values to populate the form.
 */
function populateSettingsForm(settings) {
    const elements = {
        focusMode: document.getElementById('focusMode'),
        breakReminder: document.getElementById('breakReminder'),
        debugMode: document.getElementById('debugMode'),
        pointsPerQuestion: document.getElementById('pointsPerQuestion'),
        streakBonus: document.getElementById('streakBonus'),
        maxStreakBonus: document.getElementById('maxStreakBonus')
    };

    if (elements.focusMode) elements.focusMode.checked = settings.focusMode || false;
    if (elements.breakReminder) elements.breakReminder.value = settings.breakReminder || 10;
    if (elements.debugMode) elements.debugMode.checked = settings.debugMode || false;
    if (elements.pointsPerQuestion) elements.pointsPerQuestion.value = settings.pointsPerQuestion || 10;
    if (elements.streakBonus) elements.streakBonus.value = settings.streakBonus || 5;
    if (elements.maxStreakBonus) elements.maxStreakBonus.value = settings.maxStreakBonus || 50;
}

/**
 * Enhanced settings loading with comprehensive defaults
 */
function loadSettings() {
    fetch('/api/load_settings')
    .then(response => response.json())
    .then(data => {
        if (data.success && data.settings) {
            populateSettingsForm(data.settings);
        } else {
            showAlert('Could not load current settings from server.', 'warning');
        }
    })
    .catch(error => {
        console.error('Error loading settings:', error);
        showAlert('An error occurred while loading settings.', 'danger');
    });
}

// --- History Management (Import/Export/Clear) ---

/**
 * Initiates the export of study history by redirecting to the API endpoint.
 */
function exportHistory() {
    // Track export feature usage
    if (window.analyticsTracker) {
        window.analyticsTracker.trackFeatureUsage('data_export', 'history_export');
    }
    // This creates a link and clicks it to trigger the download from the backend endpoint
    const link = document.createElement('a');
    link.href = '/api/export_history';
    link.download = `linux_plus_export_${new Date().toISOString().slice(0,10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showAlert('Study history export started.', 'info');
}

/**
 * Handles the import of study history from a JSON file.
 */
function importHistory() {
    // Track import feature usage
    if (window.analyticsTracker) {
        window.analyticsTracker.trackFeatureUsage('data_import', 'history_import');
    }
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = function(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const data = JSON.parse(e.target.result);
                fetch('/api/import_history', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                }).then(response => {
                    if (response.ok) {
                        showAlert('Study history imported successfully', 'success');
                         // Optionally, refresh the page or statistics view
                    } else {
                        showAlert('Failed to import study history', 'danger');
                    }
                });
            } catch (error) {
                showAlert('Invalid file format. Please select a valid JSON file.', 'danger');
            }
        };
        
        reader.readAsText(file);
    };
    
    input.click();
}

/**
 * Initiates clearing of all statistics after user confirmation.
 */
function clearHistory() {
    // Track data clearing
    if (window.analyticsTracker) {
        window.analyticsTracker.trackFeatureUsage('data_management', 'clear_history');
    }
    if (confirm('Are you sure you want to clear ALL study history? This action cannot be undone.')) {
        fetch('/api/clear_statistics', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Study history cleared successfully!', 'success');
                    // Refresh the status display after clearing
                    if (typeof updateGameStatus === 'function') {
                        updateGameStatus();
                    }
                    // Reload the page after a short delay to ensure everything updates
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    showAlert('Failed to clear study history: ' + (data.error || 'Unknown error'), 'danger');
                }
            })
            .catch(error => {
                console.error('Error clearing history:', error);
                showAlert('Failed to clear study history', 'danger');
            });
    }
}

/**
 * Toggles dark mode for the application and saves the user's preference.
 */
function toggleDarkMode() {
    // Track theme change
    if (window.analyticsTracker) {
        const newMode = !document.body.classList.contains('dark-mode') ? 'dark' : 'light';
        window.analyticsTracker.trackFeatureUsage('appearance', 'theme_toggle', { mode: newMode });
    }
    const body = document.body;
    body.classList.toggle('dark-mode');
    
    // Save preference in localStorage
    if (body.classList.contains('dark-mode')) {
        localStorage.setItem('darkMode', 'enabled');
    } else {
        localStorage.setItem('darkMode', 'disabled');
    }
}

// --- Performance Utilities ---

/**
 * Creates a debounced function that delays invoking `func` until after `wait` milliseconds have elapsed
 * since the last time the debounced function was invoked.
 * @param {Function} func - The function to debounce.
 * @param {number} wait - The number of milliseconds to delay.
 * @returns {Function} The new debounced function.
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
// Export/Import functionality
function exportQuestionsMarkdown() {
    showToast('Preparing Markdown export...', 'info');
    
    // Create a temporary link element to trigger download
    window.location.href = '/export/qa/md';
    
    setTimeout(() => {
        showToast('Markdown export started! Check your downloads.', 'success');
    }, 1000);
}

function exportQuestionsJSON() {
    showToast('Preparing JSON export...', 'info');
    
    // Create a temporary link element to trigger download
    window.location.href = '/export/qa/json';
    
    setTimeout(() => {
        showToast('JSON export started! Check your downloads.', 'success');
    }, 1000);
}

function updateQuestionCount() {
    // Try both possible element IDs for compatibility
    const questionCountElement = document.getElementById('question-count') || 
                                 document.getElementById('question-counter');
    
    // Only proceed if the element exists
    if (!questionCountElement) {
        console.log('Question count element not found in the DOM');
        return;
    }
    
    fetch('/api/question-count')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update text content appropriately based on element type
                if (questionCountElement.id === 'question-counter') {
                    // This is the badge element, keep existing format
                    const currentText = questionCountElement.textContent;
                    if (currentText.includes('of')) {
                        const parts = currentText.split(' of ');
                        questionCountElement.textContent = `${parts[0]} of ${data.count}`;
                    }
                } else {
                    // This is a plain count element
                    questionCountElement.textContent = data.count;
                }
            }
        })
        .catch(error => {
            console.error('Error fetching question count:', error);
            if (questionCountElement.id === 'question-counter') {
                // Don't update badge format on error
                return;
            }
            questionCountElement.textContent = 'Unknown';
        });
}

// Toast notification system (if not already present)
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} position-fixed`;
    toast.style.cssText = `
        top: 20px; 
        right: 20px; 
        z-index: 9999; 
        min-width: 300px;
        animation: slideIn 0.3s ease-out;
    `;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        ${message}
        <button type="button" class="btn-close float-end" onclick="this.parentElement.remove()"></button>
    `;
    
    // Add CSS animation if not present
    if (!document.getElementById('toast-styles')) {
        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideIn 0.3s ease-out reverse';
            setTimeout(() => toast.remove(), 300);
        }
    }, 3000);
}

// Update question count on page load
document.addEventListener('DOMContentLoaded', function() {
    updateQuestionCount();
});

// Quiz timing functionality
let quizStartTime = 0;
let questionsAnswered = 0;

function initializeQuizTiming() {
    quizStartTime = Date.now();
    questionsAnswered = 0;
    
    // Hook into existing quiz completion (if it exists)
    const originalCompleteQuiz = window.completeQuiz;
    if (originalCompleteQuiz) {
        window.completeQuiz = function() {
            trackQuizCompletion();
            return originalCompleteQuiz.apply(this, arguments);
        };
    }
}

function trackQuizCompletion() {
    if (quizStartTime > 0 && questionsAnswered > 0) {
        const endTime = Date.now();
        const sessionDuration = Math.round((endTime - quizStartTime) / 1000); // Convert to seconds
        
        // Enhanced quiz completion tracking
        const quizData = {
            duration: sessionDuration,
            questions: questionsAnswered,
            questions_attempted: questionsAnswered,
            session_start: new Date(quizStartTime).toISOString(),
            session_end: new Date(endTime).toISOString(),
            completion_percentage: 100 // Assuming completed
        };
        
        // Send to analytics tracker
        if (window.analyticsTracker) {
            window.analyticsTracker.trackQuizSession(quizData);
        }
        
        // Send actual session duration to backend
        fetch('/api/update-session-time', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(quizData)
        }).catch(error => {
            console.log('Note: Could not update session time:', error);
        });
    }
}

function incrementQuestionCount() {
    questionsAnswered++;
    
    // Track question interaction
    if (window.analyticsTracker) {
        window.analyticsTracker.sendEvent('question_interaction', {
            question_number: questionsAnswered,
            session_duration: quizStartTime ? Date.now() - quizStartTime : 0
        });
    }
}