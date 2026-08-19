document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const form = document.getElementById('research-form');
    const btnStart = document.getElementById('btn-start');
    const queryInput = document.getElementById('query-input');
    const fastModelSelect = document.getElementById('fast-model');
    const strongModelSelect = document.getElementById('strong-model');
    const maxRoundsInput = document.getElementById('max-rounds');
    const maxSourcesInput = document.getElementById('max-sources');

    const heroEmptyState = document.getElementById('hero-empty-state');
    const markdownBody = document.getElementById('markdown-body');
    const telemetryLog = document.getElementById('telemetry-log');
    const statusDot = document.getElementById('status-dot');

    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-content-pane');
    const auditScoreBadge = document.getElementById('audit-score-badge');

    const claimsTableBody = document.querySelector('#claims-table tbody');
    const evidenceCountTag = document.getElementById('evidence-count-tag');
    const contradictionsContainer = document.getElementById('contradictions-container');

    const exportPdfBtn = document.getElementById('export-pdf-btn');
    const exportMdBtn = document.getElementById('export-md-btn');
    const recentSessionsList = document.getElementById('recent-sessions-list');
    const recentTitleDisplay = document.getElementById('recent-title-display');

    const settingsModal = document.getElementById('settings-modal');
    const btnOpenSettings = document.getElementById('btn-open-settings');
    const btnCloseSettings = document.getElementById('btn-close-settings');
    const btnNewQuery = document.getElementById('btn-new-query');

    const followupInput = document.getElementById('followup-input');
    const btnSendFollowup = document.getElementById('btn-send-followup');

    // User Auth DOM Elements
    const btnOpenAuth = document.getElementById('btn-open-auth');
    const authModal = document.getElementById('auth-modal');
    const btnCloseAuth = document.getElementById('btn-close-auth');
    const btnTabLogin = document.getElementById('btn-tab-login');
    const btnTabSignup = document.getElementById('btn-tab-signup');
    const groupSignupName = document.getElementById('group-signup-name');
    const authForm = document.getElementById('auth-form');
    const authName = document.getElementById('auth-name');
    const authEmail = document.getElementById('auth-email');
    const authPassword = document.getElementById('auth-password');
    const btnAuthSubmit = document.getElementById('btn-auth-submit');
    const authErrorAlert = document.getElementById('auth-error-alert');
    const btnGoogleLogin = document.getElementById('btn-google-login');
    const userProfileMenu = document.getElementById('user-profile-menu');
    const userNameDisplay = document.getElementById('user-name-display');
    const btnLogout = document.getElementById('btn-logout');

    // Mobile View Switcher Elements
    const studioWorkspace = document.getElementById('studio-workspace');
    const btnMobileForm = document.getElementById('btn-mobile-form');
    const btnMobileReport = document.getElementById('btn-mobile-report');

    let currentSessionId = null;
    let pollInterval = null;
    let currentUser = null;
    let authMode = 'login'; // 'login' or 'signup'

    // --- Authentication Helpers ---
    function getAuthToken() {
        return localStorage.getItem('deepresearch_auth_token') || '';
    }

    function setAuthToken(token) {
        localStorage.setItem('deepresearch_auth_token', token);
    }

    function clearAuthToken() {
        localStorage.removeItem('deepresearch_auth_token');
    }

    async function fetchWithAuth(url, options = {}) {
        const token = getAuthToken();
        options.headers = options.headers || {};
        if (token) {
            options.headers['Authorization'] = `Bearer ${token}`;
        }
        return fetch(url, options);
    }

    async function checkCurrentUser() {
        try {
            const token = getAuthToken();
            if (!token) {
                renderLoggedOutState();
                return;
            }

            const resp = await fetchWithAuth('/api/auth/me');
            if (resp.ok) {
                const data = await resp.json();
                if (data.user) {
                    currentUser = data.user;
                    renderLoggedInState(currentUser);
                } else {
                    clearAuthToken();
                    renderLoggedOutState();
                }
            } else {
                clearAuthToken();
                renderLoggedOutState();
            }
        } catch (err) {
            console.error('Error checking user session:', err);
            renderLoggedOutState();
        }
    }

    const btnBannerLogin = document.getElementById('btn-banner-login');
    const bannerUserName = document.getElementById('banner-user-name');
    const bannerUserDesc = document.getElementById('banner-user-desc');

    function renderLoggedInState(user) {
        if (btnOpenAuth) btnOpenAuth.style.display = 'none';
        if (userProfileMenu) userProfileMenu.style.display = 'flex';
        if (userNameDisplay) userNameDisplay.textContent = user.name || user.email.split('@')[0];
        if (bannerUserName) bannerUserName.textContent = `Logged in: ${user.name || user.email.split('@')[0]}`;
        if (bannerUserDesc) bannerUserDesc.textContent = "Private workspace active";
        if (btnBannerLogin) btnBannerLogin.style.display = 'none';
    }

    function renderLoggedOutState() {
        currentUser = null;
        if (btnOpenAuth) btnOpenAuth.style.display = 'flex';
        if (userProfileMenu) userProfileMenu.style.display = 'none';
        if (bannerUserName) bannerUserName.textContent = "Guest Mode (Shared)";
        if (bannerUserDesc) bannerUserDesc.textContent = "Sign in to save private reports";
        if (btnBannerLogin) {
            btnBannerLogin.style.display = 'inline-flex';
            btnBannerLogin.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Sign In';
        }
    }

    // Auth Modal Handlers
    if (btnOpenAuth && authModal) {
        btnOpenAuth.addEventListener('click', () => {
            authModal.classList.add('open');
            authErrorAlert.style.display = 'none';
        });
    }

    if (btnBannerLogin && authModal) {
        btnBannerLogin.addEventListener('click', () => {
            authModal.classList.add('open');
            authErrorAlert.style.display = 'none';
        });
    }

    if (btnCloseAuth && authModal) {
        btnCloseAuth.addEventListener('click', () => authModal.classList.remove('open'));
    }

    if (authModal) {
        authModal.addEventListener('click', (e) => {
            if (e.target === authModal) authModal.classList.remove('open');
        });
    }

    if (btnTabLogin && btnTabSignup) {
        btnTabLogin.addEventListener('click', () => {
            authMode = 'login';
            btnTabLogin.classList.add('active');
            btnTabSignup.classList.remove('active');
            if (groupSignupName) groupSignupName.style.display = 'none';
            if (btnAuthSubmit) btnAuthSubmit.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Sign In to Account';
            authErrorAlert.style.display = 'none';
        });

        btnTabSignup.addEventListener('click', () => {
            authMode = 'signup';
            btnTabSignup.classList.add('active');
            btnTabLogin.classList.remove('active');
            if (groupSignupName) groupSignupName.style.display = 'block';
            if (btnAuthSubmit) btnAuthSubmit.innerHTML = '<i class="fa-solid fa-user-plus"></i> Create My Account';
            authErrorAlert.style.display = 'none';
        });
    }

    if (authForm) {
        authForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            authErrorAlert.style.display = 'none';
            btnAuthSubmit.disabled = true;
            btnAuthSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Authenticating...';

            const email = authEmail.value.trim();
            const password = authPassword.value;
            const name = authName ? authName.value.trim() : '';

            const endpoint = authMode === 'signup' ? '/api/auth/signup' : '/api/auth/login';
            const payload = authMode === 'signup' ? { name, email, password } : { email, password };

            try {
                const resp = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await resp.json();

                if (!resp.ok) {
                    throw new Error(data.detail || 'Authentication failed');
                }

                setAuthToken(data.token);
                currentUser = data.user;
                renderLoggedInState(currentUser);
                authModal.classList.remove('open');
                authForm.reset();
                
                // Refresh sessions history for this account
                loadSessionsHistory();

            } catch (err) {
                authErrorAlert.textContent = err.message;
                authErrorAlert.style.display = 'block';
            } finally {
                btnAuthSubmit.disabled = false;
                btnAuthSubmit.innerHTML = authMode === 'signup' 
                    ? '<i class="fa-solid fa-user-plus"></i> Create My Account' 
                    : '<i class="fa-solid fa-right-to-bracket"></i> Sign In to Account';
            }
        });
    }

    // Google 1-Click Sign-In
    if (btnGoogleLogin) {
        btnGoogleLogin.addEventListener('click', async () => {
            const googleEmail = prompt("Sign in with Google - Enter your Google email:", currentUser ? currentUser.email : "user@gmail.com");
            if (!googleEmail || !googleEmail.includes('@')) return;

            try {
                const resp = await fetch('/api/auth/google', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: googleEmail,
                        name: googleEmail.split('@')[0].replace(/[._]/g, ' '),
                        google_id: `g_${Date.now()}`
                    })
                });

                if (resp.ok) {
                    const data = await resp.json();
                    setAuthToken(data.token);
                    currentUser = data.user;
                    renderLoggedInState(currentUser);
                    if (authModal) authModal.classList.remove('open');
                    loadSessionsHistory();
                } else {
                    const err = await resp.json();
                    alert(err.detail || "Google login failed");
                }
            } catch (err) {
                alert("Google sign-in error: " + err.message);
            }
        });
    }

    // Logout
    if (btnLogout) {
        btnLogout.addEventListener('click', async () => {
            clearAuthToken();
            renderLoggedOutState();
            recentSessionsList.innerHTML = '<div class="text-muted" style="font-size:0.8rem; padding:0.5rem;">Signed out. Log in to view saved reports.</div>';
            currentSessionId = null;
            heroEmptyState.style.display = 'block';
            markdownBody.style.display = 'none';
        });
    }

    // Mobile View Switcher (Form vs Report)
    if (btnMobileForm && btnMobileReport && studioWorkspace) {
        btnMobileForm.addEventListener('click', () => {
            btnMobileForm.classList.add('active');
            btnMobileReport.classList.remove('active');
            studioWorkspace.classList.remove('view-report');
            studioWorkspace.classList.add('view-form');
        });

        btnMobileReport.addEventListener('click', () => {
            btnMobileReport.classList.add('active');
            btnMobileForm.classList.remove('active');
            studioWorkspace.classList.remove('view-form');
            studioWorkspace.classList.add('view-report');
        });
    }

    // Speed Mode Toggle Buttons
    const speedButtons = document.querySelectorAll('.speed-btn');
    speedButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            speedButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Tab Switching
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            const targetPane = document.getElementById(btn.dataset.tab);
            if (targetPane) targetPane.classList.add('active');
        });
    });

    // Modal Settings Toggle
    if (btnOpenSettings && settingsModal) {
        btnOpenSettings.addEventListener('click', () => {
            settingsModal.classList.add('open');
            loadNvidiaModels();
        });
    }
    if (btnCloseSettings && settingsModal) {
        btnCloseSettings.addEventListener('click', () => settingsModal.classList.remove('open'));
    }
    if (settingsModal) {
        settingsModal.addEventListener('click', (e) => {
            if (e.target === settingsModal) settingsModal.classList.remove('open');
        });
    }

    // Dynamic NVIDIA API Models Fetcher
    async function loadNvidiaModels() {
        try {
            const resp = await fetch('/api/models');
            if (!resp.ok) return;
            const data = await resp.json();

            if (data.categorized && Object.keys(data.categorized).length > 0) {
                fastModelSelect.innerHTML = '';
                strongModelSelect.innerHTML = '';

                const defaultFast = 'meta/llama-3.1-8b-instruct';
                const defaultStrong = 'meta/llama-3.3-70b-instruct';

                const priority = ['meta', 'deepseek-ai', 'nvidia', 'mistralai', 'google', 'qwen', 'microsoft', 'ibm', '01-ai'];
                const providers = Object.keys(data.categorized).sort((a, b) => {
                    const idxA = priority.indexOf(a) !== -1 ? priority.indexOf(a) : 99;
                    const idxB = priority.indexOf(b) !== -1 ? priority.indexOf(b) : 99;
                    return idxA - idxB;
                });

                providers.forEach(provider => {
                    const groupFast = document.createElement('optgroup');
                    groupFast.label = `--- ${provider.toUpperCase()} ---`;

                    const groupStrong = document.createElement('optgroup');
                    groupStrong.label = `--- ${provider.toUpperCase()} ---`;

                    data.categorized[provider].forEach(modelId => {
                        const optF = document.createElement('option');
                        optF.value = modelId;
                        optF.textContent = modelId;
                        if (modelId === defaultFast) optF.selected = true;
                        groupFast.appendChild(optF);

                        const optS = document.createElement('option');
                        optS.value = modelId;
                        optS.textContent = modelId;
                        if (modelId === defaultStrong) optS.selected = true;
                        groupStrong.appendChild(optS);
                    });

                    fastModelSelect.appendChild(groupFast);
                    strongModelSelect.appendChild(groupStrong);
                });
            }
        } catch (err) {
            console.error('Failed to load NVIDIA models:', err);
        }
    }

    // New Research Task Button
    if (btnNewQuery) {
        btnNewQuery.addEventListener('click', () => {
            if (pollInterval) clearInterval(pollInterval);
            currentSessionId = null;
            queryInput.value = '';
            queryInput.focus();
            heroEmptyState.style.display = 'block';
            markdownBody.style.display = 'none';
            auditScoreBadge.style.display = 'none';
            telemetryLog.innerHTML = `
                <div class="timeline-step done">
                    <div class="step-icon"><i class="fa-solid fa-check"></i></div>
                    <div class="step-content">
                        <span class="step-title">System Ready</span>
                        <span class="step-desc">Awaiting research query input</span>
                    </div>
                </div>
            `;
        });
    }

    // Quick Presets
    window.loadPreset = function(queryText) {
        queryInput.value = queryText;
        form.dispatchEvent(new Event('submit'));
    };

    // Follow-up Input Action
    if (btnSendFollowup && followupInput) {
        btnSendFollowup.addEventListener('click', () => {
            const val = followupInput.value.trim();
            if (val) {
                queryInput.value = val;
                followupInput.value = '';
                form.dispatchEvent(new Event('submit'));
            }
        });
        followupInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                btnSendFollowup.click();
            }
        });
    }

    const btnConfirmLaunch = document.getElementById('btn-confirm-launch');
    const btnCancelSettings = document.getElementById('btn-cancel-settings');

    let researchStartTime = null;

    // Form Submit -> Directly executes research launch immediately without opening modal popup
    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const query = queryInput.value.trim();
            if (!query) return;

            executeResearchLaunch(query);
        });
    }

    if (btnConfirmLaunch) {
        btnConfirmLaunch.addEventListener('click', () => {
            if (settingsModal) settingsModal.classList.remove('open');
            const query = queryInput.value.trim();
            if (query) {
                executeResearchLaunch(query);
            }
        });
    }

    if (btnCancelSettings) {
        btnCancelSettings.addEventListener('click', () => {
            if (settingsModal) settingsModal.classList.remove('open');
        });
    }

    async function executeResearchLaunch(query) {
        researchStartTime = Date.now();
        btnStart.disabled = true;
        btnStart.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Researching...';
        if (statusDot) statusDot.style.background = '#f59e0b';
        if (recentTitleDisplay) recentTitleDisplay.textContent = query.length > 22 ? query.slice(0, 20) + '...' : query;

        // Show Hero Loading View
        heroEmptyState.style.display = 'none';
        markdownBody.style.display = 'block';
        markdownBody.innerHTML = `
            <div class="hero-empty-state">
                <div class="hero-badge"><i class="fa-solid fa-atom fa-spin-pulse"></i> Deep Research Active</div>
                <h2>Autonomous AI Lead Researcher at work...</h2>
                <p>Executing multi-round search, scraping authority domains, extracting atomic claims, and preparing publication report for: <strong>"${query}"</strong></p>
            </div>
        `;

        telemetryLog.innerHTML = `
            <div class="timeline-step done">
                <div class="step-icon"><i class="fa-solid fa-spinner fa-spin"></i></div>
                <div class="step-content">
                    <span class="step-title">Research Pipeline Initialized</span>
                    <span class="step-desc">Target topic: ${query}</span>
                </div>
            </div>
        `;

        let selectedMode = 'turbo';
        const activeSpeedBtn = document.querySelector('.speed-btn.active');
        if (activeSpeedBtn) selectedMode = activeSpeedBtn.getAttribute('data-mode') || 'turbo';

        let roundsVal = 1;
        let sourcesVal = 15; // Set rich default sources
        if (selectedMode === 'standard') {
            roundsVal = 2;
            sourcesVal = 22;
        } else if (selectedMode === 'deep') {
            roundsVal = 4;
            sourcesVal = 35;
        }

        const suggestionsInput = document.getElementById('suggestions-input');
        const modalSuggestionsInput = document.getElementById('modal-suggestions-input');
        if (suggestionsInput && modalSuggestionsInput) {
            suggestionsInput.addEventListener('input', () => { modalSuggestionsInput.value = suggestionsInput.value; });
            modalSuggestionsInput.addEventListener('input', () => { suggestionsInput.value = modalSuggestionsInput.value; });
        }

        const targetPagesInput = document.getElementById('target-pages-input');
        const modalTargetPages = document.getElementById('modal-target-pages');
        if (targetPagesInput && modalTargetPages) {
            targetPagesInput.addEventListener('change', () => { modalTargetPages.value = targetPagesInput.value; });
            modalTargetPages.addEventListener('change', () => { targetPagesInput.value = modalTargetPages.value; });
        }

        // Automatically switch mobile view to report on mobile screens
        if (window.innerWidth <= 992 && btnMobileReport) {
            btnMobileReport.click();
        }

        try {
            const payload = {
                query: query,
                fast_model: fastModelSelect.value,
                strong_model: strongModelSelect.value,
                max_rounds: roundsVal,
                max_sources: sourcesVal,
                user_suggestions: suggestionsVal,
                target_pages: targetPagesVal
            };

            const resp = await fetchWithAuth('/api/research', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!resp.ok) throw new Error('Failed to start research task');

            const data = await resp.json();
            currentSessionId = data.session_id;

            startPolling(currentSessionId);
            loadSessionsHistory();
        } catch (err) {
            alert(`Error: ${err.message}`);
            btnStart.disabled = false;
            btnStart.innerHTML = '<i class="fa-solid fa-rocket"></i> Launch Research Engine';
        }
    }

    // Polling Function
    function startPolling(sessionId) {
        if (pollInterval) clearInterval(pollInterval);
        fetchStatus(sessionId);
        pollInterval = setInterval(() => fetchStatus(sessionId), 1200);
    }

    async function fetchStatus(sessionId) {
        try {
            const resp = await fetch(`/api/research/${sessionId}`);
            if (!resp.ok) return;

            const statusData = await resp.json();
            updateTelemetryLogs(statusData);
            updateProgressView(statusData);

            if (statusData.status === 'completed' || statusData.status === 'failed') {
                if (pollInterval) clearInterval(pollInterval);
                btnStart.disabled = false;
                btnStart.innerHTML = '<i class="fa-solid fa-rocket"></i> Launch Research Engine';
                if (statusDot) statusDot.style.background = statusData.status === 'completed' ? '#10b981' : '#ef4444';

                if (statusData.status === 'completed') {
                    loadFinalReport(sessionId);
                    loadEvidenceStore(sessionId);
                    loadContradictions(sessionId);
                }
            }
        } catch (err) {
            console.error('Polling error:', err);
        }
    }

    function updateProgressView(data) {
        if (data.status === 'completed') return;

        if (!researchStartTime) researchStartTime = Date.now();
        const secondsElapsed = Math.floor((Date.now() - researchStartTime) / 1000);
        const mm = String(Math.floor(secondsElapsed / 60)).padStart(2, '0');
        const ss = String(secondsElapsed % 60).padStart(2, '0');

        const pct = data.progress_percentage || 15;
        const baseEta = data.estimated_seconds_remaining || 15;
        const dynamicEta = Math.max(2, baseEta - Math.floor((secondsElapsed % 10) / 2));
        const stageName = (data.stage || 'researching').toUpperCase().replace(/_/g, ' ');

        markdownBody.style.display = 'block';
        heroEmptyState.style.display = 'none';

        const logsList = (data.logs || []).slice(-6);

        markdownBody.innerHTML = `
            <div class="hero-empty-state">
                <div class="hero-badge"><i class="fa-solid fa-atom fa-spin-pulse"></i> Autonomous Deep Research Active</div>
                <h2>Synthesizing Publication-Grade Research...</h2>
                <p style="margin-bottom:1.2rem;">Target Topic: <strong>"${data.query}"</strong></p>

                <div class="live-progress-container">
                    <div class="progress-header">
                        <span class="progress-stage-title"><i class="fa-solid fa-circle-notch fa-spin text-warning"></i> Stage: ${stageName}</span>
                        <span class="progress-percent-text">${pct}% Complete</span>
                    </div>

                    <div class="progress-bar-track">
                        <div class="progress-bar-fill" style="width: ${pct}%;"></div>
                    </div>

                    <div class="progress-footer-stats">
                        <span class="elapsed-badge-pill"><i class="fa-solid fa-stopwatch"></i> Elapsed: ${mm}:${ss}</span>
                        <span><i class="fa-solid fa-database"></i> ${data.total_sources || 0} Sources | ${data.total_claims || 0} Claims</span>
                        <span class="eta-badge-pill"><i class="fa-solid fa-clock"></i> ETA: ~${dynamicEta}s remaining</span>
                    </div>

                    <!-- CENTER SCREEN LIVE TELEMETRY TERMINAL -->
                    <div class="center-telemetry-box">
                        <div class="telemetry-box-header">
                            <span><i class="fa-solid fa-terminal"></i> Live Telemetry Feed (Real-Time Activity)</span>
                            <span style="color:#10b981;"><i class="fa-solid fa-circle-dot fa-beat-fade"></i> Live Stream</span>
                        </div>
                        <div class="center-log-feed">
                            ${logsList.length > 0 ? logsList.map(l => `
                                <div class="center-log-row">
                                    <span class="log-tag">[${l.stage}]</span>
                                    <span class="log-msg">${l.message}</span>
                                </div>
                            `).join('') : '<div class="center-log-row"><span class="log-msg">Initializing real-time stream...</span></div>'}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // Telemetry Timeline Update
    function updateTelemetryLogs(data) {
        if (data.logs && data.logs.length > 0) {
            telemetryLog.innerHTML = data.logs.slice(-15).map(log => `
                <div class="timeline-step done">
                    <div class="step-icon"><i class="fa-solid fa-circle-check"></i></div>
                    <div class="step-content">
                        <span class="step-title">[${log.stage}]</span>
                        <span class="step-desc">${log.message}</span>
                    </div>
                </div>
            `).join('');
            telemetryLog.scrollTop = telemetryLog.scrollHeight;
        }
    }

    // Load Synthesized Markdown Report
    async function loadFinalReport(sessionId) {
        try {
            const resp = await fetch(`/api/research/${sessionId}/report`);
            if (!resp.ok) return;
            const reportData = await resp.json();

            const mdContent = reportData.markdown_content || reportData.markdown;

            if (mdContent) {
                markdownBody.innerHTML = marked.parse(mdContent);
                auditScoreBadge.style.display = 'inline-flex';
                
                // Update Word Count telemetry chip
                const wordsCount = mdContent.trim().split(/\s+/).filter(Boolean).length;
                const reportWordsVal = document.getElementById('report-words-val');
                if (reportWordsVal) reportWordsVal.textContent = wordsCount.toLocaleString();

                const pdfUrl = `/api/research/${sessionId}/download/pdf`;
                const mdUrl = `/api/research/${sessionId}/download/md`;

                // Enable Prominent PDF Download Buttons
                const btnDownloadPdfTop = document.getElementById('btn-download-pdf-top');
                const reportTopBar = document.getElementById('report-top-bar');
                if (btnDownloadPdfTop && reportTopBar) {
                    btnDownloadPdfTop.href = pdfUrl;
                    reportTopBar.style.display = 'flex';
                }

                const btnDownloadPdfNav = document.getElementById('btn-download-pdf-nav');
                if (btnDownloadPdfNav) {
                    btnDownloadPdfNav.href = pdfUrl;
                    btnDownloadPdfNav.style.display = 'inline-flex';
                }

                // Enable Export Studio Buttons
                exportPdfBtn.href = pdfUrl;
                exportPdfBtn.classList.remove('disabled');

                exportMdBtn.href = mdUrl;
                exportMdBtn.classList.remove('disabled');

                // Wire up Copy Markdown Button
                const btnCopyReport = document.getElementById('btn-copy-report');
                if (btnCopyReport) {
                    btnCopyReport.onclick = async () => {
                        try {
                            await navigator.clipboard.writeText(mdContent);
                            const origHTML = btnCopyReport.innerHTML;
                            btnCopyReport.innerHTML = '<i class="fa-solid fa-check text-success"></i> Copied!';
                            setTimeout(() => { btnCopyReport.innerHTML = origHTML; }, 2000);
                        } catch (e) {
                            console.warn('Clipboard write failed:', e);
                        }
                    };
                }
            }
        } catch (err) {
            console.error('Failed loading final report:', err);
        }
    }

    // Live WYSIWYG Editing & Word Customization Handler
    let isEditMode = false;
    const btnToggleEdit = document.getElementById('btn-toggle-edit');
    const btnSaveEdit = document.getElementById('btn-save-edit');
    const editBtnText = document.getElementById('edit-btn-text');
    const reportStatusBadge = document.getElementById('report-status-badge');
    const editHintBanner = document.getElementById('edit-hint-banner');

    if (btnToggleEdit) {
        btnToggleEdit.addEventListener('click', () => {
            isEditMode = !isEditMode;
            if (isEditMode) {
                markdownBody.setAttribute('contenteditable', 'true');
                markdownBody.focus();
                btnToggleEdit.classList.add('active');
                if (editBtnText) editBtnText.textContent = 'Editing Mode (Active)';
                if (btnSaveEdit) btnSaveEdit.style.display = 'inline-flex';
                if (reportStatusBadge) reportStatusBadge.innerHTML = '<i class="fa-solid fa-pen text-warning"></i> Editing Mode';
                if (editHintBanner) editHintBanner.style.display = 'flex';
            } else {
                markdownBody.removeAttribute('contenteditable');
                btnToggleEdit.classList.remove('active');
                if (editBtnText) editBtnText.textContent = 'Edit Words';
                if (reportStatusBadge) reportStatusBadge.innerHTML = '<i class="fa-solid fa-circle-check text-emerald"></i> Publication Ready';
                if (editHintBanner) editHintBanner.style.display = 'none';
            }
        });
    }

    function htmlToMarkdown(root) {
        function nodeToMd(node) {
            if (node.nodeType === Node.TEXT_NODE) {
                return node.nodeValue;
            }
            if (node.nodeType !== Node.ELEMENT_NODE) {
                return '';
            }

            const tag = node.tagName.toLowerCase();
            let childrenMd = Array.from(node.childNodes).map(nodeToMd).join('');

            switch (tag) {
                case 'h1':
                    return `\n# ${childrenMd.trim()}\n\n`;
                case 'h2':
                    return `\n## ${childrenMd.trim()}\n\n`;
                case 'h3':
                    return `\n### ${childrenMd.trim()}\n\n`;
                case 'h4':
                    return `\n#### ${childrenMd.trim()}\n\n`;
                case 'h5':
                    return `\n##### ${childrenMd.trim()}\n\n`;
                case 'h6':
                    return `\n###### ${childrenMd.trim()}\n\n`;
                case 'p':
                    return `\n${childrenMd.trim()}\n\n`;
                case 'strong':
                case 'b':
                    return `**${childrenMd}**`;
                case 'em':
                case 'i':
                    return `*${childrenMd}*`;
                case 'code':
                    return `\`${childrenMd}\``;
                case 'pre':
                    return `\n\`\`\`\n${childrenMd.trim()}\n\`\`\`\n\n`;
                case 'blockquote':
                    return `\n> ${childrenMd.trim().replace(/\n/g, '\n> ')}\n\n`;
                case 'ul':
                    return `\n${childrenMd}\n`;
                case 'ol':
                    return `\n${childrenMd}\n`;
                case 'li': {
                    const isOrdered = node.parentElement && node.parentElement.tagName.toLowerCase() === 'ol';
                    const index = Array.from(node.parentElement ? node.parentElement.children : []).indexOf(node) + 1;
                    const prefix = isOrdered ? `${index}. ` : `- `;
                    return `${prefix}${childrenMd.trim()}\n`;
                }
                case 'table': {
                    const rows = Array.from(node.querySelectorAll('tr'));
                    if (rows.length === 0) return '';
                    let tableMd = '\n';
                    rows.forEach((row, rIdx) => {
                        const cells = Array.from(row.querySelectorAll('th, td')).map(c => c.innerText.trim());
                        tableMd += `| ${cells.join(' | ')} |\n`;
                        if (rIdx === 0) {
                            tableMd += `| ${cells.map(() => '---').join(' | ')} |\n`;
                        }
                    });
                    return tableMd + '\n';
                }
                case 'br':
                    return '\n';
                case 'hr':
                    return '\n---\n\n';
                default:
                    return childrenMd;
            }
        }

        let result = nodeToMd(root);
        result = result.replace(/\n{3,}/g, '\n\n').trim();
        return result;
    }

    if (btnSaveEdit) {
        btnSaveEdit.addEventListener('click', async () => {
            if (!currentSessionId) return;
            btnSaveEdit.disabled = true;
            btnSaveEdit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

            const updatedMarkdown = htmlToMarkdown(markdownBody);

            try {
                const resp = await fetch(`/api/research/${currentSessionId}/report`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ markdown_content: updatedMarkdown })
                });

                if (resp.ok) {
                    btnSaveEdit.innerHTML = '<i class="fa-solid fa-check"></i> Changes Saved!';
                    if (reportStatusBadge) reportStatusBadge.innerHTML = '<i class="fa-solid fa-circle-check text-emerald"></i> Saved & PDF Updated';
                    
                    const newWords = updatedMarkdown.trim().split(/\s+/).filter(Boolean).length;
                    const reportWordsVal = document.getElementById('report-words-val');
                    if (reportWordsVal) reportWordsVal.textContent = newWords.toLocaleString();

                    // Update all PDF download button URLs with timestamp to force fresh download
                    const freshPdfUrl = `/api/research/${currentSessionId}/download/pdf?t=${Date.now()}`;
                    const btnDownloadPdfTop = document.getElementById('btn-download-pdf-top');
                    const btnDownloadPdfNav = document.getElementById('btn-download-pdf-nav');
                    if (btnDownloadPdfTop) btnDownloadPdfTop.href = freshPdfUrl;
                    if (btnDownloadPdfNav) btnDownloadPdfNav.href = freshPdfUrl;
                    if (exportPdfBtn) exportPdfBtn.href = freshPdfUrl;

                    setTimeout(() => {
                        btnSaveEdit.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Changes';
                        btnSaveEdit.disabled = false;
                    }, 2500);
                } else {
                    throw new Error('Failed to save updated report');
                }
            } catch (err) {
                alert(`Error saving report: ${err.message}`);
                btnSaveEdit.disabled = false;
                btnSaveEdit.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Changes';
            }
        });
    }

    let allLoadedClaims = [];
    const claimsSearchInput = document.getElementById('claims-search-input');

    if (claimsSearchInput) {
        claimsSearchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (!allLoadedClaims.length) return;
            const filtered = allLoadedClaims.filter(c => 
                (c.claim_text && c.claim_text.toLowerCase().includes(query)) ||
                (c.source_title && c.source_title.toLowerCase().includes(query)) ||
                (c.quote_or_paraphrase && c.quote_or_paraphrase.toLowerCase().includes(query)) ||
                (c.sub_question_tag && c.sub_question_tag.toLowerCase().includes(query))
            );
            renderClaimsTable(filtered);
        });
    }

    function renderClaimsTable(claimsList) {
        if (!claimsList || claimsList.length === 0) {
            claimsTableBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted" style="padding:2rem;">No matching facts found.</td></tr>';
            return;
        }
        claimsTableBody.innerHTML = claimsList.map(c => `
            <tr>
                <td style="max-width:220px;">
                    <strong style="color:#0f172a;">${c.source_title || 'Source'}</strong><br>
                    <a href="${c.source_url}" target="_blank" style="font-size:0.75rem; color:#2563eb; text-decoration:none; word-break:break-all;"><i class="fa-solid fa-arrow-up-right-from-square"></i> ${c.source_url}</a>
                </td>
                <td style="line-height:1.6; color:#1e293b;">${c.claim_text}</td>
                <td style="color:#475569; font-style:italic;">"${c.quote_or_paraphrase}"</td>
                <td><span class="badge-pill">${c.sub_question_tag}</span></td>
            </tr>
        `).join('');
    }

    // Load Evidence & Claims Matrix Table
    async function loadEvidenceStore(sessionId) {
        try {
            const resp = await fetch(`/api/research/${sessionId}/evidence`);
            if (!resp.ok) return;
            const data = await resp.json();

            if (data.claims && data.claims.length > 0) {
                allLoadedClaims = data.claims;
                evidenceCountTag.textContent = `${data.claims.length} Claims`;
                renderClaimsTable(allLoadedClaims);
            }
        } catch (err) {
            console.error('Failed loading evidence store:', err);
        }
    }

    // Load Contradictions & Consensus Analysis Matrix
    async function loadContradictions(sessionId) {
        try {
            const resp = await fetch(`/api/research/${sessionId}/contradictions`);
            if (!resp.ok) return;
            const data = await resp.json();

            if (data.contradictions && data.contradictions.length > 0) {
                contradictionsContainer.innerHTML = data.contradictions.map(c => {
                    const views = Array.isArray(c.conflicting_views) 
                        ? c.conflicting_views.join(' | ') 
                        : (c.conflicting_views || 'None');
                    return `
                        <div class="table-container-card" style="margin-bottom:1.5rem;">
                            <div class="table-header-bar">
                                <h3><i class="fa-solid fa-scale-balanced text-warning"></i> Topic: ${c.topic}</h3>
                            </div>
                            <p style="margin-bottom:0.8rem; color:#334155;"><strong>Consensus View:</strong> ${c.consensus_summary}</p>
                            <p style="color:#b45309;"><strong>Conflicting Views:</strong> ${views}</p>
                        </div>
                    `;
                }).join('');
            }
        } catch (err) {
            console.error('Failed loading contradictions:', err);
        }
    }

    // Load Sessions History
    async function loadSessionsHistory() {
        try {
            const resp = await fetchWithAuth('/api/sessions');
            if (!resp.ok) return;
            const data = await resp.json();
            const list = data.sessions || [];

            if (recentSessionsList) {
                if (list.length > 0) {
                    recentSessionsList.innerHTML = list.slice(0, 8).map(s => `
                        <div class="session-history-item ${s.session_id === currentSessionId ? 'active' : ''}" onclick="switchSession('${s.session_id}')">
                            <i class="fa-solid fa-file-contract"></i>
                            <span class="session-name">${s.query.length > 22 ? s.query.slice(0, 20) + '...' : s.query}</span>
                        </div>
                    `).join('');

                    if (!currentSessionId && list[0]) {
                        switchSession(list[0].session_id);
                    }
                } else {
                    recentSessionsList.innerHTML = '<div class="text-muted" style="font-size:0.8rem; padding:0.5rem;">No research tasks found yet. Start a new topic!</div>';
                }
            }
        } catch (err) {
            console.error('Error loading session history:', err);
        }
    }

    window.switchSession = function(sessionId) {
        currentSessionId = sessionId;
        heroEmptyState.style.display = 'none';
        markdownBody.style.display = 'block';
        if (window.innerWidth <= 992 && btnMobileReport) {
            btnMobileReport.click();
        }
        startPolling(sessionId);
        loadFinalReport(sessionId);
        loadEvidenceStore(sessionId);
        loadContradictions(sessionId);
    };

    // Initial Load Sequence
    (async () => {
        await checkCurrentUser();
        await loadSessionsHistory();
        await loadNvidiaModels();
    })();
});
