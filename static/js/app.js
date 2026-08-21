
document.addEventListener('DOMContentLoaded', () => {
    // State Management
    let currentUser = null;
    let currentAuthEmail = '';
    let resendTimerInterval = null;
    let resendSecondsRemaining = 60;
    let currentSessionId = null;

    // DOM Elements - Auth Overlay & Views
    const authOverlay = document.getElementById('auth-gate-overlay');
    const authViewTitle = document.getElementById('auth-view-title');
    const authViewSubtitle = document.getElementById('auth-view-subtitle');
    const authAlertBox = document.getElementById('auth-alert-box');

    const viewSignin = document.getElementById('view-signin');
    const viewSignup = document.getElementById('view-signup');
    const viewVerify = document.getElementById('view-verify');
    const viewForgot = document.getElementById('view-forgot');
    const viewReset = document.getElementById('view-reset');

    // Forms & Inputs
    const formSignin = document.getElementById('form-signin');
    const formSignup = document.getElementById('form-signup');
    const formVerify = document.getElementById('form-verify');
    const formForgot = document.getElementById('form-forgot');
    const formReset = document.getElementById('form-reset');

    const signinEmail = document.getElementById('signin-email');
    const signinPassword = document.getElementById('signin-password');
    const signupName = document.getElementById('signup-name');
    const signupEmail = document.getElementById('signup-email');
    const signupPassword = document.getElementById('signup-password');
    const signupConfirmPassword = document.getElementById('signup-confirm-password');
    const signupPwMeter = document.getElementById('signup-pw-meter');
    const signupPwMatch = document.getElementById('signup-pw-match');
    
    const verifyMaskedEmail = document.getElementById('verify-masked-email');
    const otpInputs = document.querySelectorAll('.otp-digit-box');
    const resendCountdownText = document.getElementById('resend-countdown-text');
    const btnResendOtp = document.getElementById('btn-resend-otp');
    const forgotEmail = document.getElementById('forgot-email');
    const resetCode = document.getElementById('reset-code');
    const resetNewPassword = document.getElementById('reset-new-password');
    const resetConfirmPassword = document.getElementById('reset-confirm-password');

    // Navbar & User Profile
    const btnOpenAuth = document.getElementById('btn-open-auth');
    const userProfileMenu = document.getElementById('user-profile-menu');
    const userNameDisplay = document.getElementById('user-name-display');
    const btnLogout = document.getElementById('btn-logout');
    const bannerUserName = document.getElementById('banner-user-name');
    const bannerUserDesc = document.getElementById('banner-user-desc');
    const btnBannerLogin = document.getElementById('btn-banner-login');

    // --- Helper Functions ---
    function setAuthToken(token) {
        localStorage.setItem('deepresearch_auth_token', token);
    }

    function getAuthToken() {
        return localStorage.getItem('deepresearch_auth_token') || '';
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

    function showAuthAlert(msg, type = 'error') {
        if (!authAlertBox) return;
        authAlertBox.className = `auth-status-alert ${type}`;
        authAlertBox.innerHTML = type === 'error' 
            ? `<i class="fa-solid fa-triangle-exclamation"></i> <span>${msg}</span>`
            : `<i class="fa-solid fa-circle-check"></i> <span>${msg}</span>`;
        authAlertBox.style.display = 'flex';
    }

    function hideAuthAlert() {
        if (authAlertBox) authAlertBox.style.display = 'none';
    }

    function switchAuthView(viewName) {
        hideAuthAlert();
        [viewSignin, viewSignup, viewVerify, viewForgot, viewReset].forEach(v => {
            if (v) v.style.display = 'none';
        });

        if (viewName === 'signin') {
            viewSignin.style.display = 'block';
            authViewTitle.textContent = "Welcome Back";
            authViewSubtitle.textContent = "Sign in to your private research workspace";
            if (signinEmail) signinEmail.focus();
        } else if (viewName === 'signup') {
            viewSignup.style.display = 'block';
            authViewTitle.textContent = "Create Account";
            authViewSubtitle.textContent = "Join DeepResearch Studio to generate verified literature";
            if (signupName) signupName.focus();
        } else if (viewName === 'verify') {
            viewVerify.style.display = 'block';
            authViewTitle.textContent = "Verify Your Email";
            authViewSubtitle.textContent = "Enter the 6-digit code sent to your email";
            clearOtpInputs();
            if (otpInputs[0]) otpInputs[0].focus();
            startResendTimer(60);
        } else if (viewName === 'forgot') {
            viewForgot.style.display = 'block';
            authViewTitle.textContent = "Reset Password";
            authViewSubtitle.textContent = "We will send a 6-digit password reset code";
            if (forgotEmail) forgotEmail.focus();
        } else if (viewName === 'reset') {
            viewReset.style.display = 'block';
            authViewTitle.textContent = "Choose New Password";
            authViewSubtitle.textContent = "Enter your 6-digit reset code and new password";
            if (resetCode) resetCode.focus();
        }
    }

    // Toggle Password Visibility
    document.querySelectorAll('.btn-toggle-pw').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            const input = document.getElementById(targetId);
            if (input) {
                const isPw = input.type === 'password';
                input.type = isPw ? 'text' : 'password';
                btn.innerHTML = isPw ? '<i class="fa-solid fa-eye-slash"></i>' : '<i class="fa-solid fa-eye"></i>';
            }
        });
    });

    // Password Strength Meter
    if (signupPassword && signupPwMeter) {
        signupPassword.addEventListener('input', () => {
            const val = signupPassword.value;
            let score = 0;
            if (val.length >= 6) score += 25;
            if (val.length >= 10) score += 25;
            if (/[A-Z]/.test(val) && /[a-z]/.test(val)) score += 25;
            if (/[0-9]/.test(val) && /[^A-Za-z0-9]/.test(val)) score += 25;

            signupPwMeter.style.width = score + '%';
            if (score <= 25) signupPwMeter.style.background = '#ef4444';
            else if (score <= 75) signupPwMeter.style.background = '#f59e0b';
            else signupPwMeter.style.background = '#10b981';
        });
    }

    // Password Match Indicator
    if (signupConfirmPassword && signupPwMatch) {
        signupConfirmPassword.addEventListener('input', () => {
            const pw = signupPassword.value;
            const confirm = signupConfirmPassword.value;
            if (!confirm) {
                signupPwMatch.style.display = 'none';
                return;
            }
            signupPwMatch.style.display = 'flex';
            if (pw === confirm) {
                signupPwMatch.innerHTML = '<span style="color:#10b981;"><i class="fa-solid fa-circle-check"></i> Passwords match</span>';
            } else {
                signupPwMatch.innerHTML = '<span style="color:#ef4444;"><i class="fa-solid fa-circle-xmark"></i> Passwords do not match</span>';
            }
        });
    }

    // 6-Digit OTP Auto-Tabbing & Paste Handler
    function getOtpValue() {
        let code = '';
        otpInputs.forEach(input => { code += input.value.trim(); });
        return code;
    }

    function clearOtpInputs() {
        otpInputs.forEach(input => { input.value = ''; });
    }

    otpInputs.forEach((input, index) => {
        input.addEventListener('input', (e) => {
            const val = e.target.value;
            if (val.length > 0) {
                input.value = val[val.length - 1]; // Single digit only
                if (index < otpInputs.length - 1) {
                    otpInputs[index + 1].focus();
                }
            }
            if (getOtpValue().length === 6 && formVerify) {
                // Auto-submit when all 6 digits entered
                formVerify.dispatchEvent(new Event('submit'));
            }
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !input.value && index > 0) {
                otpInputs[index - 1].focus();
            }
        });

        input.addEventListener('paste', (e) => {
            e.preventDefault();
            const pasted = (e.clipboardData || window.clipboardData).getData('text').trim();
            if (/^\d{6}$/.test(pasted)) {
                for (let i = 0; i < 6; i++) {
                    otpInputs[i].value = pasted[i];
                }
                if (formVerify) formVerify.dispatchEvent(new Event('submit'));
            }
        });
    });

    // Resend Timer
    function startResendTimer(seconds = 60) {
        clearInterval(resendTimerInterval);
        resendSecondsRemaining = seconds;
        if (resendCountdownText) resendCountdownText.style.display = 'inline';
        if (btnResendOtp) btnResendOtp.style.display = 'none';

        resendTimerInterval = setInterval(() => {
            resendSecondsRemaining--;
            if (resendCountdownText) {
                const mins = Math.floor(resendSecondsRemaining / 60);
                const secs = resendSecondsRemaining % 60;
                resendCountdownText.textContent = `Resend code in ${mins}:${secs < 10 ? '0' : ''}${secs}`;
            }
            if (resendSecondsRemaining <= 0) {
                clearInterval(resendTimerInterval);
                if (resendCountdownText) resendCountdownText.style.display = 'none';
                if (btnResendOtp) btnResendOtp.style.display = 'inline';
            }
        }, 1000);
    }

    // View Switching Navigation Links
    const linkGotoSignup = document.getElementById('link-goto-signup');
    const linkGotoSignin = document.getElementById('link-goto-signin');
    const linkGotoForgot = document.getElementById('link-goto-forgot');
    const linkForgotToSignin = document.getElementById('link-forgot-to-signin');
    const linkResetToSignin = document.getElementById('link-reset-to-signin');
    const linkChangeEmail = document.getElementById('link-change-email');

    if (linkGotoSignup) linkGotoSignup.addEventListener('click', (e) => { e.preventDefault(); switchAuthView('signup'); });
    if (linkGotoSignin) linkGotoSignin.addEventListener('click', (e) => { e.preventDefault(); switchAuthView('signin'); });
    if (linkGotoForgot) linkGotoForgot.addEventListener('click', (e) => { e.preventDefault(); switchAuthView('forgot'); });
    if (linkForgotToSignin) linkForgotToSignin.addEventListener('click', (e) => { e.preventDefault(); switchAuthView('signin'); });
    if (linkResetToSignin) linkResetToSignin.addEventListener('click', (e) => { e.preventDefault(); switchAuthView('signin'); });
    if (linkChangeEmail) linkChangeEmail.addEventListener('click', (e) => { e.preventDefault(); switchAuthView('signup'); });

    // --- FORM HANDLERS ---

    // 1. Sign In
    if (formSignin) {
        formSignin.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideAuthAlert();
            const btn = document.getElementById('btn-submit-signin');
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Authenticating...';

            try {
                const resp = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: signinEmail.value.trim(),
                        password: signinPassword.value,
                        remember_me: document.getElementById('signin-remember').checked
                    })
                });

                const data = await resp.json();

                if (resp.status === 403 && data.needs_verification) {
                    currentAuthEmail = data.email;
                    if (verifyMaskedEmail) verifyMaskedEmail.textContent = data.masked_email || data.email;
                    switchAuthView('verify');
                    showAuthAlert(data.detail || "Please enter the 6-digit code sent to your email.", "error");
                    return;
                }

                if (!resp.ok) {
                    throw new Error(data.detail || 'Sign in failed. Please check credentials.');
                }

                setAuthToken(data.token);
                currentUser = data.user;
                renderLoggedInState(currentUser);
                authOverlay.style.display = 'none';
                loadSessionsHistory();

            } catch (err) {
                showAuthAlert(err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Sign In to Studio';
            }
        });
    }

    // 2. Sign Up
    if (formSignup) {
        formSignup.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideAuthAlert();

            if (signupPassword.value !== signupConfirmPassword.value) {
                showAuthAlert('Passwords do not match.', 'error');
                return;
            }

            const btn = document.getElementById('btn-submit-signup');
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creating Account & Sending Code...';

            try {
                const resp = await fetch('/api/auth/signup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: signupName.value.trim(),
                        email: signupEmail.value.trim(),
                        password: signupPassword.value,
                        confirm_password: signupConfirmPassword.value,
                        terms_accepted: true
                    })
                });

                const data = await resp.json();

                if (!resp.ok) {
                    throw new Error(data.detail || 'Signup failed. Please try again.');
                }

                currentAuthEmail = data.email;
                if (verifyMaskedEmail) verifyMaskedEmail.textContent = data.masked_email || data.email;
                switchAuthView('verify');
                showAuthAlert(`Verification code dispatched to ${data.masked_email || data.email}!`, 'success');

            } catch (err) {
                showAuthAlert(err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Create Account & Verify';
            }
        });
    }

    // 3. Verify OTP
    if (formVerify) {
        formVerify.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideAuthAlert();
            const code = getOtpValue();
            if (code.length !== 6) {
                showAuthAlert('Please enter all 6 digits of your verification code.', 'error');
                return;
            }

            const btn = document.getElementById('btn-submit-verify');
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying Code...';

            try {
                const resp = await fetch('/api/auth/verify-email', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: currentAuthEmail || (signinEmail ? signinEmail.value.trim() : ''),
                        code: code
                    })
                });

                const data = await resp.json();

                if (!resp.ok) {
                    throw new Error(data.detail || 'Invalid verification code.');
                }

                setAuthToken(data.token);
                currentUser = data.user;
                renderLoggedInState(currentUser);
                authOverlay.style.display = 'none';
                loadSessionsHistory();

            } catch (err) {
                showAuthAlert(err.message, 'error');
                clearOtpInputs();
                if (otpInputs[0]) otpInputs[0].focus();
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-circle-check"></i> Verify Code & Enter Studio';
            }
        });
    }

    // 4. Resend OTP
    if (btnResendOtp) {
        btnResendOtp.addEventListener('click', async () => {
            hideAuthAlert();
            try {
                const resp = await fetch('/api/auth/resend-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: currentAuthEmail })
                });
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.detail || 'Could not resend code.');
                showAuthAlert('A fresh 6-digit code has been dispatched to your email.', 'success');
                startResendTimer(60);
                clearOtpInputs();
                if (otpInputs[0]) otpInputs[0].focus();
            } catch (err) {
                showAuthAlert(err.message, 'error');
            }
        });
    }

    // 5. Forgot Password
    if (formForgot) {
        formForgot.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideAuthAlert();
            const btn = document.getElementById('btn-submit-forgot');
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending Reset Code...';

            try {
                const email = forgotEmail.value.trim();
                const resp = await fetch('/api/auth/forgot-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email })
                });
                const data = await resp.json();
                currentAuthEmail = email;
                switchAuthView('reset');
                showAuthAlert(data.message || 'If an account exists, a 6-digit reset code has been sent.', 'success');
            } catch (err) {
                showAuthAlert(err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Send Password Reset Code';
            }
        });
    }

    // 6. Reset Password
    if (formReset) {
        formReset.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideAuthAlert();

            if (resetNewPassword.value !== resetConfirmPassword.value) {
                showAuthAlert('New passwords do not match.', 'error');
                return;
            }

            const btn = document.getElementById('btn-submit-reset');
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Updating Password...';

            try {
                const resp = await fetch('/api/auth/reset-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: currentAuthEmail,
                        code: resetCode.value.trim(),
                        new_password: resetNewPassword.value,
                        confirm_password: resetConfirmPassword.value
                    })
                });

                const data = await resp.json();
                if (!resp.ok) throw new Error(data.detail || 'Password reset failed.');

                switchAuthView('signin');
                showAuthAlert('Password updated successfully! Please sign in with your new password.', 'success');

            } catch (err) {
                showAuthAlert(err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-lock-open"></i> Update Password & Sign In';
            }
        });
    }

    // 7. Google OAuth Integration (Server Popup + GIS fallback)
    document.querySelectorAll('.btn-trigger-google').forEach(btn => {
        btn.addEventListener('click', async () => {
            try {
                const resp = await fetch('/api/auth/google/url');
                if (resp.ok) {
                    const data = await resp.json();
                    if (data.url) {
                        const popup = window.open(data.url, 'GoogleOAuth', 'width=520,height=640');
                        // Poll for popup closure / token callback
                        const timer = setInterval(() => {
                            if (popup.closed) {
                                clearInterval(timer);
                                checkCurrentUser();
                            }
                        }, 800);
                        return;
                    }
                }
            } catch (e) {
                console.log("OAuth URL error:", e);
            }
            
            // Fallback: GIS Prompt
            if (window.google && window.google.accounts && window.google.accounts.id) {
                window.google.accounts.id.prompt();
            }
        });
    });

    // Check URL parameters for OAuth token return
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('auth_token')) {
        const token = urlParams.get('auth_token');
        setAuthToken(token);
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    // Check Current User on startup
    async function checkCurrentUser() {
        try {
            const token = getAuthToken();
            const resp = await fetchWithAuth('/api/auth/me');
            if (resp.ok) {
                const data = await resp.json();
                if (data.authenticated && data.user && data.user.email_verified) {
                    currentUser = data.user;
                    renderLoggedInState(currentUser);
                    if (authOverlay) authOverlay.style.display = 'none';
                    loadSessionsHistory();
                    return;
                }
            }
            
            // Not authenticated or unverified
            renderLoggedOutState();
            if (authOverlay) {
                authOverlay.style.display = 'flex';
                switchAuthView('signin');
            }
        } catch (err) {
            console.error('Session check error:', err);
            renderLoggedOutState();
            if (authOverlay) {
                authOverlay.style.display = 'flex';
                switchAuthView('signin');
            }
        }
    }

    function renderLoggedInState(user) {
        if (btnOpenAuth) btnOpenAuth.style.display = 'none';
        if (userProfileMenu) userProfileMenu.style.display = 'flex';
        if (userNameDisplay) userNameDisplay.textContent = user.name || user.email.split('@')[0];
        if (bannerUserName) bannerUserName.textContent = `Logged in: ${user.name || user.email.split('@')[0]}`;
        if (bannerUserDesc) bannerUserDesc.textContent = "Private workspace active & verified";
        if (btnBannerLogin) btnBannerLogin.style.display = 'none';
    }

    function renderLoggedOutState() {
        currentUser = null;
        if (btnOpenAuth) btnOpenAuth.style.display = 'flex';
        if (userProfileMenu) userProfileMenu.style.display = 'none';
        if (bannerUserName) bannerUserName.textContent = "Guest Mode";
        if (bannerUserDesc) bannerUserDesc.textContent = "Sign in to save private reports";
        if (btnBannerLogin) {
            btnBannerLogin.style.display = 'inline-flex';
            btnBannerLogin.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Sign In';
        }
    }

    // Logout
    if (btnLogout) {
        btnLogout.addEventListener('click', async () => {
            await fetch('/api/auth/logout', { method: 'POST' });
            clearAuthToken();
            renderLoggedOutState();
            if (authOverlay) {
                authOverlay.style.display = 'flex';
                switchAuthView('signin');
            }
        });
    }

    if (btnOpenAuth) {
        btnOpenAuth.addEventListener('click', () => {
            if (authOverlay) {
                authOverlay.style.display = 'flex';
                switchAuthView('signin');
            }
        });
    }

    if (btnBannerLogin) {
        btnBannerLogin.addEventListener('click', () => {
            if (authOverlay) {
                authOverlay.style.display = 'flex';
                switchAuthView('signin');
            }
        });
    }

    // Initialize session check immediately
    checkCurrentUser();

    // =========================================================================
    // RESEARCH STUDIO ENGINE & REPORT LOGIC
    // =========================================================================

    const form = document.getElementById('research-form');
    const queryInput = document.getElementById('query-input');
    const maxRoundsInput = document.getElementById('max-rounds');
    const maxSourcesInput = document.getElementById('max-sources');
    const fastModelSelect = document.getElementById('fast-model');
    const strongModelSelect = document.getElementById('strong-model');
    const btnLaunch = document.getElementById('btn-launch');

    const heroEmptyState = document.getElementById('hero-empty-state');
    const markdownBody = document.getElementById('markdown-body');
    const reportTitleHeading = document.getElementById('report-title-heading');
    const claimsTableBody = document.querySelector('#claims-table tbody');
    const contradictionsContainer = document.getElementById('contradictions-container');
    const liveLogContainer = document.getElementById('live-log-container');
    const evidenceCountTag = document.getElementById('evidence-count-tag');

    const statusBadge = document.getElementById('status-badge');
    const stageBadge = document.getElementById('stage-badge');
    const progressFill = document.getElementById('progress-fill');
    const progressPercent = document.getElementById('progress-percent');
    const telemetryStatRounds = document.getElementById('telemetry-stat-rounds');
    const telemetryStatSources = document.getElementById('telemetry-stat-sources');
    const telemetryStatClaims = document.getElementById('telemetry-stat-claims');
    const telemetryStatDisagreements = document.getElementById('telemetry-stat-disagreements');
    const telemetryTimer = document.getElementById('telemetry-timer');
    const currentActionText = document.getElementById('current-action-text');

    const btnDownloadPdfTop = document.getElementById('btn-download-pdf-top');
    const btnDownloadPdfHero = document.getElementById('btn-download-pdf-hero');
    const exportPdfBtn = document.getElementById('export-pdf-btn');
    const exportMdBtn = document.getElementById('export-md-btn');
    const btnCopyReport = document.getElementById('btn-copy-report');
    const btnEditReport = document.getElementById('btn-edit-report');
    const btnSaveEdit = document.getElementById('btn-save-edit');
    const editHintBanner = document.getElementById('edit-hint-banner');

    let pollInterval = null;
    let stopwatchInterval = null;
    let startTime = null;

    // Load available models from NVIDIA
    async function loadNvidiaModels() {
        try {
            const resp = await fetch('/api/nvidia/models');
            if (!resp.ok) return;
            const models = await resp.json();
            if (!models || models.length === 0) return;

            fastModelSelect.innerHTML = '';
            strongModelSelect.innerHTML = '';

            models.forEach(m => {
                const optFast = document.createElement('option');
                optFast.value = m.id;
                optFast.textContent = `${m.name} (${m.context_length})`;
                if (m.id === 'meta/llama-3.1-8b-instruct') optFast.selected = true;
                fastModelSelect.appendChild(optFast);

                const optStrong = document.createElement('option');
                optStrong.value = m.id;
                optStrong.textContent = `${m.name} (${m.context_length})`;
                if (m.id === 'meta/llama-3.3-70b-instruct') optStrong.selected = true;
                strongModelSelect.appendChild(optStrong);
            });
        } catch (e) {
            console.log('Using default model selectors:', e);
        }
    }
    loadNvidiaModels();

    // Launch Research
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const query = queryInput.value.trim();
            if (!query) return;

            btnLaunch.disabled = true;
            btnLaunch.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Initializing Agent...';
            heroEmptyState.style.display = 'none';
            markdownBody.style.display = 'none';
            liveLogContainer.innerHTML = '';

            startTime = Date.now();
            clearInterval(stopwatchInterval);
            stopwatchInterval = setInterval(() => {
                const elapsed = Math.floor((Date.now() - startTime) / 1000);
                const mins = Math.floor(elapsed / 60);
                const secs = elapsed % 60;
                if (telemetryTimer) telemetryTimer.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
            }, 1000);

            try {
                const resp = await fetchWithAuth('/api/research', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: query,
                        max_rounds: parseInt(maxRoundsInput.value) || 2,
                        max_sources: parseInt(maxSourcesInput.value) || 15,
                        fast_model: fastModelSelect.value,
                        strong_model: strongModelSelect.value
                    })
                });

                if (!resp.ok) {
                    if (resp.status === 401 || resp.status === 403) {
                        checkCurrentUser();
                        return;
                    }
                    throw new Error('Failed to launch research session');
                }

                const data = await resp.json();
                currentSessionId = data.session_id;
                startPollingStatus(currentSessionId);

            } catch (err) {
                alert('Error launching research: ' + err.message);
                btnLaunch.disabled = false;
                btnLaunch.innerHTML = '<i class="fa-solid fa-rocket"></i> Launch Research Engine';
            }
        });
    }

    function startPollingStatus(sessionId) {
        clearInterval(pollInterval);
        pollInterval = setInterval(async () => {
            try {
                const resp = await fetchWithAuth(`/api/research/${sessionId}/status`);
                if (!resp.ok) return;
                const status = await resp.json();

                if (stageBadge) stageBadge.textContent = status.stage.toUpperCase();
                if (statusBadge) statusBadge.textContent = status.status.toUpperCase();
                if (currentActionText) currentActionText.textContent = status.current_action;
                if (telemetryStatRounds) telemetryStatRounds.textContent = `${status.rounds_completed}/${status.total_rounds}`;
                if (telemetryStatSources) telemetryStatSources.textContent = status.sources_found;
                if (telemetryStatClaims) telemetryStatClaims.textContent = status.claims_extracted;
                if (telemetryStatDisagreements) telemetryStatDisagreements.textContent = status.contradictions_found;

                const percent = Math.min(100, Math.round((status.rounds_completed / status.total_rounds) * 90) + (status.status === 'completed' ? 10 : 0));
                if (progressFill) progressFill.style.width = percent + '%';
                if (progressPercent) progressPercent.textContent = percent + '%';

                if (status.status === 'completed' || status.status === 'error') {
                    clearInterval(pollInterval);
                    clearInterval(stopwatchInterval);
                    btnLaunch.disabled = false;
                    btnLaunch.innerHTML = '<i class="fa-solid fa-rocket"></i> Launch Research Engine';
                    loadFullReport(sessionId);
                    loadSessionsHistory();
                }
            } catch (e) {
                console.error('Polling error:', e);
            }
        }, 1500);
    }

    async function loadFullReport(sessionId) {
        try {
            const resp = await fetchWithAuth(`/api/research/${sessionId}/report`);
            if (!resp.ok) return;
            const data = await resp.json();

            if (data.report && data.report.markdown_content) {
                markdownBody.innerHTML = marked.parse(data.report.markdown_content);
                markdownBody.style.display = 'block';
                heroEmptyState.style.display = 'none';

                if (reportTitleHeading) reportTitleHeading.textContent = data.session.query;
                if (btnDownloadPdfTop) btnDownloadPdfTop.href = `/api/export/${sessionId}/pdf`;
                if (btnDownloadPdfHero) btnDownloadPdfHero.href = `/api/export/${sessionId}/pdf`;
                if (exportPdfBtn) { exportPdfBtn.href = `/api/export/${sessionId}/pdf`; exportPdfBtn.classList.remove('disabled'); }
                if (exportMdBtn) { exportMdBtn.href = `/api/export/${sessionId}/md`; exportMdBtn.classList.remove('disabled'); }
            }

            // Populate Evidence Table
            if (data.claims && claimsTableBody) {
                if (data.claims.length > 0) {
                    claimsTableBody.innerHTML = data.claims.map(c => `
                        <tr>
                            <td><a href="#" class="text-emerald">${c.sub_question_tag}</a></td>
                            <td><strong>${c.claim_text}</strong></td>
                            <td class="text-muted"><em>"${c.quote_or_paraphrase || ''}"</em></td>
                            <td><span class="badge-pill">${Math.round(c.confidence * 100)}%</span></td>
                        </tr>
                    `).join('');
                }
                if (evidenceCountTag) evidenceCountTag.textContent = `${data.claims.length} Claims`;
            }

        } catch (e) {
            console.error('Error loading report:', e);
        }
    }

    async function loadSessionsHistory() {
        try {
            const resp = await fetchWithAuth('/api/sessions');
            if (!resp.ok) return;
            const sessions = await resp.json();
            const recentList = document.getElementById('recent-sessions-list');
            if (!recentList) return;

            if (sessions.length === 0) {
                recentList.innerHTML = '<div class="text-muted" style="font-size:0.8rem; padding:0.5rem;">No research tasks saved yet.</div>';
                return;
            }

            recentList.innerHTML = sessions.map(s => `
                <div class="session-item" data-id="${s.session_id}" style="padding:0.6rem; border-radius:8px; cursor:pointer; margin-bottom:4px; background:rgba(30,41,59,0.5);">
                    <div style="font-weight:600; font-size:0.84rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${s.query}</div>
                    <div style="font-size:0.72rem; color:#94a3b8; display:flex; justify-content:space-between; margin-top:2px;">
                        <span>${s.status.toUpperCase()}</span>
                        <span>${new Date(s.created_at).toLocaleDateString()}</span>
                    </div>
                </div>
            `).join('');

            document.querySelectorAll('.session-item').forEach(item => {
                item.addEventListener('click', () => {
                    const sid = item.getAttribute('data-id');
                    loadFullReport(sid);
                });
            });

        } catch (e) {
            console.error('Error loading history:', e);
        }
    }

    // Tabs Navigation
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content-pane').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            const target = btn.getAttribute('data-tab');
            const pane = document.getElementById(`tab-${target}`);
            if (pane) pane.classList.add('active');
        });
    });

    // Copy Report
    if (btnCopyReport) {
        btnCopyReport.addEventListener('click', () => {
            const text = markdownBody.innerText || markdownBody.textContent;
            navigator.clipboard.writeText(text);
            btnCopyReport.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
            setTimeout(() => { btnCopyReport.innerHTML = '<i class="fa-solid fa-copy"></i> Copy'; }, 2000);
        });
    }

});
