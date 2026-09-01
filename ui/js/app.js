/**
 * Waqas Automation Pro v2.0.7 - Client App JS (Tauri / Web Frontend)
 * 2026 Commercial SaaS UI & Super Admin Analytics Logic
 */

const API_BASE = "http://127.0.0.1:8765/api";

// ── APP STATE ─────────────────────────────────────────────────────────────
let appState = {
    activeTab: "dashboard",
    activeCategory: "ALL",
    selectedActivityDate: new Date().toISOString().slice(0, 10),
    selectedLeadFilter: "all",
    config: {},
    stats: {},
    sessions: [],
    prompts: [],
    viralPrompts: [],
    downloads: [],
    superAdmin: {},
    superAdminUsers: [],
    isAutomationRunning: false
};

let superAdminCharts = {
    dailyActiveTrend: null,
    topCreators: null,
    statusDonut: null,
    testingLeadsTrend: null,
    testingLeadsSources: null
};

// ── CUSTOM IN-APP MODAL DIALOGS & TOASTS (REPLACES BROWSER ALERTS/CONFIRMS) ─
function showToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast-item toast-${type}`;
    
    let icon = "⚡";
    if (type === "success") icon = "✅";
    if (type === "error") icon = "❌";
    if (type === "warn") icon = "⚠️";
    if (type === "info") icon = "ℹ️";

    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-msg">${escapeHtml(message)}</div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("toast-fadeout");
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function showConfirm(title, message, options = {}) {
    return new Promise((resolve) => {
        const modal = document.getElementById("modal-saas-dialog");
        if (!modal) {
            resolve(true);
            return;
        }

        const iconEl = document.getElementById("dialog-icon");
        const titleEl = document.getElementById("dialog-title");
        const msgEl = document.getElementById("dialog-message");
        const btnCancel = document.getElementById("dialog-btn-cancel");
        const btnConfirm = document.getElementById("dialog-btn-confirm");

        if (iconEl) iconEl.textContent = options.icon || "❓";
        if (titleEl) titleEl.textContent = title;
        if (msgEl) msgEl.textContent = message;
        if (btnCancel) {
            btnCancel.textContent = options.cancelText || "Cancel";
            btnCancel.style.display = options.isAlert ? "none" : "inline-flex";
        }
        if (btnConfirm) {
            btnConfirm.textContent = options.confirmText || "Confirm";
            btnConfirm.className = options.isDanger ? "btn btn-danger" : "btn btn-primary";
        }

        const cleanup = (result) => {
            modal.classList.add("hidden");
            btnCancel.onclick = null;
            btnConfirm.onclick = null;
            resolve(result);
        };

        btnCancel.onclick = () => cleanup(false);
        btnConfirm.onclick = () => cleanup(true);

        modal.classList.remove("hidden");
    });
}

function showAlert(title, message, icon = "ℹ️") {
    return showConfirm(title, message, { isAlert: true, confirmText: "OK", icon });
}

// ── INITIALIZATION ────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initSubTabs();
    initModals();
    initCategoryChips();
    initEventHandlers();
    initUserPopoverAndAuth();
    initPasswordToggles();
    initTestingLabEvents();
    
    // Initial Data Fetch
    fetchStats();
    fetchSessions();
    fetchPrompts();
    fetchDownloads();
    fetchLogs();

    // Start Polling Interval (every 3 seconds)
    setInterval(() => {
        if (appState.activeTab === "dashboard") {
            fetchStats();
            fetchLogs();
        }
        if (appState.activeTab === "sessions") fetchSessions();
        if (appState.activeTab === "prompts") fetchPrompts();
        if (appState.activeTab === "automation") fetchAutomationStatus();
        if (appState.activeTab === "downloads") fetchDownloads();
        if (appState.activeTab === "super-admin") fetchSuperAdminData();
        
        const modalLogs = document.getElementById("modal-logs-console");
        if (modalLogs && !modalLogs.classList.contains("hidden")) {
            fetchLogs();
        }
    }, 8000);

    // Check for app updates after 3 seconds (allow UI to load first)
    setTimeout(checkForUpdate, 3000);
});

let pendingUpdateData = null;

// ── AUTO-UPDATE CHECK & 1-CLICK INSTALL ──────────────────────────────────
async function checkForUpdate(isManual = false) {
    if (isManual) {
        showToast("🔍 Checking Supabase Cloud for updates...", "info");
    }
    try {
        const res = await fetch(`${API_BASE}/check-update`);
        const data = await res.json();
        if (data.success && data.update_available) {
            pendingUpdateData = data;
            // Populate modal
            document.getElementById("update-current-ver").textContent = `v${data.current_version}`;
            document.getElementById("update-new-ver").textContent = `v${data.version}`;
            document.getElementById("update-release-notes").innerHTML = `
                <h4>📋 What's New in v${data.version}:</h4>
                <p>${(data.release_notes || "Bug fixes and performance improvements.").replace(/\n/g, "<br>")}</p>
            `;

            // If mandatory, hide skip button
            if (data.is_mandatory) {
                document.getElementById("update-skip-btn").style.display = "none";
            } else {
                document.getElementById("update-skip-btn").style.display = "inline-block";
            }

            // Show modal
            document.getElementById("update-modal-overlay").classList.remove("hidden");
        } else if (isManual) {
            showAlert("You're Up to Date! 🎉", `You are running the latest version of Waqas Automation Pro (v${data.current_version || "2.0.7"}). No new updates available on Supabase Cloud right now.`, "✅");
        }
    } catch (e) {
        console.log("Update check skipped:", e.message);
        if (isManual) {
            showAlert("Update Check Failed", `Could not connect to update server: ${e.message}`, "⚠️");
        }
    }
}

async function applyAppUpdate() {
    if (!pendingUpdateData || !pendingUpdateData.download_url) {
        showAlert("Error", "No update download URL found.", "❌");
        return;
    }

    const actionsDiv = document.getElementById("update-modal-actions");
    const progressDiv = document.getElementById("update-progress");
    const progressFill = document.getElementById("update-progress-fill");
    const progressText = document.getElementById("update-progress-text");

    // Switch to progress UI
    if (actionsDiv) actionsDiv.classList.add("hidden");
    if (progressDiv) progressDiv.classList.remove("hidden");

    let progress = 15;
    const progressTimer = setInterval(() => {
        if (progress < 85) {
            progress += 10;
            if (progressFill) progressFill.style.width = `${progress}%`;
        }
    }, 400);

    try {
        const res = await fetch(`${API_BASE}/system/apply-update`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                download_url: pendingUpdateData.download_url,
                version: pendingUpdateData.version
            })
        });

        clearInterval(progressTimer);
        const result = await res.json();

        if (result.success) {
            if (progressFill) progressFill.style.width = "100%";
            if (progressText) {
                progressText.innerHTML = "🎉 Update Installed Successfully!<br><span style='color:#a78bfa; font-size:12px;'>Restarting application in 3 seconds...</span>";
            }

            setTimeout(() => {
                window.location.reload();
            }, 3000);
        } else {
            clearInterval(progressTimer);
            if (actionsDiv) actionsDiv.classList.remove("hidden");
            if (progressDiv) progressDiv.classList.add("hidden");
            showAlert("Update Failed", result.error || "Could not apply update.", "❌");
        }
    } catch (err) {
        clearInterval(progressTimer);
        if (actionsDiv) actionsDiv.classList.remove("hidden");
        if (progressDiv) progressDiv.classList.add("hidden");
        showAlert("Update Error", `Network error applying update: ${err.message}`, "❌");
    }
}

// ── NAVIGATION & TAB SWITCHING ────────────────────────────────────────────
function initNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.dataset.tab;
            if (!targetTab) return;
            
            navItems.forEach(i => i.classList.remove("active"));
            btn.classList.add("active");

            document.querySelectorAll(".view-panel").forEach(panel => {
                panel.classList.remove("active");
            });

            const activePanel = document.getElementById(`view-${targetTab}`);
            if (activePanel) {
                activePanel.classList.add("active");
                appState.activeTab = targetTab;

                // If subtab attribute exists (e.g. for direct Super Admin tabs)
                const adminSubTab = btn.dataset.adminSubtab;
                if (adminSubTab) {
                    const subtabBtn = document.querySelector(`.subtab-btn[data-subtab="${adminSubTab}"]`);
                    if (subtabBtn) {
                        subtabBtn.click();
                    }
                }

                onTabActivated(targetTab);
            }
        });
    });

    const btnTopSync = document.getElementById("btn-top-sync-cloud");
    if (btnTopSync) {
        btnTopSync.addEventListener("click", () => {
            fetchSuperAdminData();
            showToast("Syncing SaaS cloud metrics...", "info");
        });
    }

    const headerCheckBtns = [
        document.getElementById("btn-header-check-update"),
        document.getElementById("btn-admin-check-update")
    ];
    headerCheckBtns.forEach(btn => {
        if (btn) {
            btn.addEventListener("click", () => checkForUpdate(true));
        }
    });
}

function onTabActivated(tab) {
    if (tab === "dashboard") {
        fetchStats();
        fetchLogs();
    }
    if (tab === "sessions") fetchSessions();
    if (tab === "prompts") {
        fetchPrompts();
        fetchAutomationStatus();
        fetchDownloads();
        fetchLogs();
    }
    if (tab === "viral-prompts") fetchViralPrompts();
    if (tab === "automation") fetchAutomationStatus();
    if (tab === "downloads") fetchDownloads();
    if (tab === "super-admin") fetchSuperAdminData();
}

// ── SUB-TABS NAVIGATION (SUPER ADMIN & SEEDANCE PANEL) ─────────────────────
function initSubTabs() {
    const subTabBtns = document.querySelectorAll(".subtab-btn");
    subTabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.subtab;
            if (!target) return;

            const parentBar = btn.closest(".subtab-bar");
            if (parentBar) {
                parentBar.querySelectorAll(".subtab-btn").forEach(b => b.classList.remove("active"));
            }
            btn.classList.add("active");

            // Isolate panel switching to the current view group
            const viewPanel = btn.closest(".view-panel");
            if (viewPanel) {
                viewPanel.querySelectorAll(".subtab-panel").forEach(p => p.classList.remove("active"));
            } else {
                document.querySelectorAll(".subtab-panel").forEach(p => p.classList.remove("active"));
            }

            const targetPanel = document.getElementById(`subtab-${target}`);
            if (targetPanel) {
                targetPanel.classList.add("active");
            }

            if (target === "sa-analytics") {
                renderSuperAdminCharts(appState.superAdmin);
            } else if (target === "seedance-downloads") {
                fetchDownloads();
            } else if (target === "seedance-engine") {
                fetchAutomationStatus();
                fetchLogs();
            } else if (target === "seedance-queue") {
                fetchPrompts();
            }
        });
    });
}

// ── CATEGORY CHIPS FOR VIRAL LIBRARY ──────────────────────────────────────
function initCategoryChips() {
    const chipsContainer = document.getElementById("viral-category-chips");
    if (!chipsContainer) return;

    chipsContainer.addEventListener("click", (e) => {
        const chip = e.target.closest(".chip");
        if (!chip) return;

        chipsContainer.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
        chip.classList.add("active");

        appState.activeCategory = chip.dataset.category || "ALL";
        filterAndRenderViralPrompts();
    });
}

// ── API CALLS ─────────────────────────────────────────────────────────────
async function apiRequest(endpoint, method = "GET", body = null) {
    try {
        const options = {
            method,
            headers: { "Content-Type": "application/json" }
        };
        if (body) options.body = JSON.stringify(body);

        const res = await fetch(`${API_BASE}${endpoint}`, options);
        return await res.json();
    } catch (err) {
        console.error(`API Error on ${endpoint}:`, err);
        return { success: false, error: err.message };
    }
}

// 1. STATS & DASHBOARD
async function fetchStats() {
    const res = await apiRequest("/stats");
    if (res.success && res.stats) {
        const s = res.stats;
        appState.stats = s;
        
        const userTotalVideos = (s.user_total_videos !== undefined) ? s.user_total_videos : (s.lifetime_videos || 0);
        const userTodayVideos = (s.user_today_videos !== undefined) ? s.user_today_videos : (s.completed_prompts || 0);

        animateCounter("dash-pending-prompts", s.pending_prompts || 0);
        animateCounter("dash-avail-sessions", s.available_sessions || 0);
        animateCounter("dash-completed-prompts", userTodayVideos);
        animateCounter("dash-local-lifetime", userTotalVideos);

        if (s.config) {
            appState.config = s.config;
            const sessVal = s.config.sessions_at_a_time || 3;
            const vidVal = s.config.videos_per_session || 15;
            const dirVal = s.config.default_download_dir || "";

            document.querySelectorAll(".cfg-sessions-input").forEach(el => el.value = sessVal);
            document.querySelectorAll(".cfg-videos-input").forEach(el => el.value = vidVal);
            document.querySelectorAll(".cfg-dir-input").forEach(el => el.value = dirVal);
            
            const cfgSess = document.getElementById("cfg-sessions-at-a-time");
            if (cfgSess) cfgSess.value = sessVal;
            const cfgVid = document.getElementById("cfg-videos-per-session");
            if (cfgVid) cfgVid.value = vidVal;
            const cfgDir = document.getElementById("cfg-download-dir");
            if (cfgDir) cfgDir.value = dirVal;
        }

        if (s.current_user && s.current_user.status === "Active") {
            const email = s.current_user.email || "Guest User";
            const name = s.current_user.full_name || email.split("@")[0];
            const role = s.current_user.role || "free";

            document.getElementById("user-display-name").textContent = name;
            document.getElementById("user-avatar-text").textContent = name.substring(0, 2).toUpperCase();

            const popName = document.getElementById("pop-user-name");
            const popEmail = document.getElementById("pop-user-email");
            if (popName) popName.textContent = name;
            if (popEmail) popEmail.textContent = email;

            const badgeEl = document.getElementById("user-license-badge");
            if (badgeEl) {
                if (role === "admin") {
                    badgeEl.textContent = "👑 Super Admin";
                    badgeEl.className = "license-badge badge-admin";
                } else if (role === "paid") {
                    badgeEl.textContent = "⭐ Pro Paid License";
                    badgeEl.className = "license-badge badge-paid";
                } else {
                    badgeEl.textContent = "🟢 Free License";
                    badgeEl.className = "license-badge badge-free";
                }
            }

            // Apply role-based UI separation
            applyRoleUI(role);
        } else {
            // User signed out -> Show Auth Modal
            document.getElementById("user-display-name").textContent = "Signed Out";
            document.getElementById("user-avatar-text").textContent = "??";
            const badgeEl = document.getElementById("user-license-badge");
            if (badgeEl) {
                badgeEl.textContent = "🔴 Signed Out";
                badgeEl.className = "license-badge badge-red";
            }
            applyRoleUI("signed_out");
            const modalAuth = document.getElementById("modal-auth");
            if (modalAuth && modalAuth.classList.contains("hidden")) {
                switchAuthTab("signin");
                modalAuth.classList.remove("hidden");
            }
        }

        // Render Modern Dashboard Charts
        renderDashboardCharts(s);
    }
}

// ── ROLE-BASED UI SEPARATION (ADMIN VS REGULAR CREATOR) ────────────────────
function applyRoleUI(role) {
    const isAdmin = (role === "admin");
    const userNavGroup = document.querySelector(".user-nav-group");
    const adminNavGroup = document.querySelector(".admin-nav-group");
    const userHeaderActions = document.querySelector(".user-header-actions");
    const adminHeaderActions = document.querySelector(".admin-header-actions");
    const headerTitle = document.getElementById("top-header-title");
    const headerSubtitle = document.getElementById("top-header-subtitle");

    const appVer = (appState.stats && appState.stats.app_version) ? appState.stats.app_version : "2.0.7";

    if (isAdmin) {
        document.body.classList.add("admin-mode");
        document.body.classList.remove("user-mode");

        if (userNavGroup) userNavGroup.classList.add("hidden");
        if (adminNavGroup) adminNavGroup.classList.remove("hidden");
        if (userHeaderActions) userHeaderActions.classList.add("hidden");
        if (adminHeaderActions) adminHeaderActions.classList.remove("hidden");

        if (headerTitle) headerTitle.innerHTML = `👑 Waqas Automation Pro <span class="version-tag">Admin v${appVer}</span>`;
        if (headerSubtitle) headerSubtitle.textContent = `👑 Super Admin SaaS Control & Multi-User Analytics Center`;

        // If currently in a user tab, automatically switch to Super Admin Console
        const userTabs = ["dashboard", "sessions", "prompts", "viral-prompts"];
        if (userTabs.includes(appState.activeTab)) {
            const firstAdminNav = adminNavGroup ? adminNavGroup.querySelector(".nav-item") : null;
            if (firstAdminNav) {
                firstAdminNav.click();
            } else {
                appState.activeTab = "super-admin";
                document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
                const saPanel = document.getElementById("view-super-admin");
                if (saPanel) saPanel.classList.add("active");
                fetchSuperAdminData();
            }
        }
    } else {
        document.body.classList.remove("admin-mode");
        document.body.classList.add("user-mode");

        if (userNavGroup) userNavGroup.classList.remove("hidden");
        if (adminNavGroup) adminNavGroup.classList.add("hidden");
        if (userHeaderActions) userHeaderActions.classList.remove("hidden");
        if (adminHeaderActions) adminHeaderActions.classList.add("hidden");

        if (headerTitle) headerTitle.innerHTML = `Waqas Automation Pro <span class="version-tag">v${appVer}</span>`;
        if (headerSubtitle) headerSubtitle.textContent = `Multi-Session Dola AI & Facebook Automation SaaS`;

        // If currently in Super Admin tab, switch back to user dashboard
        if (appState.activeTab === "super-admin") {
            const userDashNav = userNavGroup ? userNavGroup.querySelector(".nav-item[data-tab='dashboard']") : null;
            if (userDashNav) {
                userDashNav.click();
            } else {
                appState.activeTab = "dashboard";
                document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
                const dashPanel = document.getElementById("view-dashboard");
                if (dashPanel) dashPanel.classList.add("active");
                fetchStats();
            }
        }
    }
}

function animateCounter(elementId, targetValue) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.textContent = targetValue;
}

// 2. SESSIONS
async function fetchSessions() {
    const res = await apiRequest("/sessions");
    if (res.success && res.sessions) {
        appState.sessions = res.sessions;
        renderSessions(res.sessions);
    }
}

function renderSessions(sessions) {
    const summaryEl = document.getElementById("sess-summary-count");
    const headingAvailEl = document.getElementById("heading-available-sessions");
    const headingExpEl = document.getElementById("heading-expired-sessions");
    const tbodyAvail = document.getElementById("tbody-available-sessions");
    const tbodyExp = document.getElementById("tbody-expired-sessions");

    if (!tbodyAvail && !tbodyExp) {
        const container = document.getElementById("sessions-container");
        if (!container) return;
        if (!sessions || sessions.length === 0) {
            container.innerHTML = `
                <div class="glass-card full-width" style="grid-column: 1 / -1;">
                    <p style="text-align: center; color: var(--text-muted); padding: 30px;">
                        📂 No active browser session profiles found.<br>Click <strong>"Add New Session"</strong> above to register your Dola AI or Facebook session profile.
                    </p>
                </div>`;
            return;
        }
        container.innerHTML = sessions.map(s => `
            <div class="glass-card">
                <div class="flex-between" style="margin-bottom: 12px;">
                    <h3 style="color: #ffffff;">🔑 ${escapeHtml(s.name)}</h3>
                    <span class="badge ${s.status === 'Available' ? 'badge-green' : 'badge-yellow'}">${s.status}</span>
                </div>
                <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 16px; line-height: 1.5;">
                    Engine: <strong style="color: var(--accent);">${s.session_type || 'Dola AI Pro'}</strong><br>
                    Registered: ${s.created_at ? s.created_at.substring(0, 10) : 'Active Session'}
                </p>
                <div class="card-footer-actions">
                    <button class="btn btn-danger btn-sm" onclick="deleteSession(${s.id})">🗑️ Delete</button>
                </div>
            </div>
        `).join("");
        return;
    }

    const available = (sessions || []).filter(s => (s.status || 'Available') === 'Available');
    const expired = (sessions || []).filter(s => (s.status || 'Available') !== 'Available');

    if (summaryEl) {
        summaryEl.textContent = `${available.length} Available | ${expired.length} Expired (${sessions ? sessions.length : 0} Total)`;
    }
    if (headingAvailEl) {
        headingAvailEl.innerHTML = `🟢 Available Sessions (${available.length})`;
    }
    if (headingExpEl) {
        headingExpEl.innerHTML = `🔴 Expired / Disabled Sessions (${expired.length})`;
    }

    if (tbodyAvail) {
        if (available.length === 0) {
            tbodyAvail.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted); padding: 24px;">No available sessions registered. Click "➕ Add Session" or "📥 Import JSON" to add.</td></tr>`;
        } else {
            tbodyAvail.innerHTML = available.map((s, idx) => `
                <tr>
                    <td style="text-align: center;"><input type="checkbox" class="sess-chk" data-id="${s.id}"></td>
                    <td style="text-align: center; color: var(--text-muted);">${idx + 1}</td>
                    <td style="text-align: center; font-family: var(--font-mono); color: var(--accent);">#${s.id}</td>
                    <td style="font-weight: 600;">🔑 ${escapeHtml(s.name)}</td>
                    <td style="text-align: center;"><span class="badge badge-cyan">${s.videos_left ?? 15} / 15</span></td>
                    <td style="text-align: center;"><span class="badge badge-green">${s.status || 'Available'}</span></td>
                    <td style="text-align: right;">
                        <div class="action-btn-group">
                            <button class="btn btn-secondary btn-xs" onclick="openSessionBrowser(${s.id})" title="Launch browser session">🔍 Open</button>
                            <button class="btn btn-warning btn-xs" onclick="toggleSessionStatus(${s.id}, 'Expired')" title="Mark as Expired">⚠️ Expire</button>
                            <button class="btn btn-danger btn-xs" onclick="deleteSession(${s.id})">🗑️ Delete</button>
                        </div>
                    </td>
                </tr>
            `).join("");
        }
    }

    if (tbodyExp) {
        if (expired.length === 0) {
            tbodyExp.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted); padding: 24px;">No expired sessions.</td></tr>`;
        } else {
            tbodyExp.innerHTML = expired.map((s, idx) => `
                <tr>
                    <td style="text-align: center;"><input type="checkbox" class="sess-chk" data-id="${s.id}"></td>
                    <td style="text-align: center; color: var(--text-muted);">${idx + 1}</td>
                    <td style="text-align: center; font-family: var(--font-mono); color: var(--text-muted);">#${s.id}</td>
                    <td style="font-weight: 600; text-decoration: line-through; opacity: 0.7;">🔑 ${escapeHtml(s.name)}</td>
                    <td style="text-align: center;"><span class="badge badge-red">${s.videos_left ?? 0}</span></td>
                    <td style="text-align: center;"><span class="badge badge-red">${s.status || 'Expired'}</span></td>
                    <td style="text-align: right;">
                        <div class="action-btn-group">
                            <button class="btn btn-secondary btn-xs" onclick="openSessionBrowser(${s.id})" title="Launch browser session">🔍 Open</button>
                            <button class="btn btn-success btn-xs" onclick="toggleSessionStatus(${s.id}, 'Available')" title="Mark as Available">🟢 Reactivate</button>
                            <button class="btn btn-danger btn-xs" onclick="deleteSession(${s.id})">🗑️ Delete</button>
                        </div>
                    </td>
                </tr>
            `).join("");
        }
    }
}

async function openSessionBrowser(id) {
    showToast(`Opening browser for session #${id}...`, "info");
    const res = await apiRequest("/sessions/open-browser", "POST", { id });
    if (res.success) {
        showToast(res.message || "Browser launched successfully!", "success");
    } else {
        showAlert("Browser Launch Error", res.error || "Could not launch browser session", "❌");
    }
}

async function toggleSessionStatus(id, newStatus) {
    const res = await apiRequest("/sessions/toggle-status", "POST", { id, status: newStatus });
    if (res.success) {
        showToast(`Session #${id} status updated to ${newStatus}`, "info");
        fetchSessions();
    } else {
        showAlert("Error", res.error || "Failed to update session status", "❌");
    }
}

async function deleteSession(id) {
    const ok = await showConfirm("Delete Session Profile", "Are you sure you want to delete this session profile?", { isDanger: true, confirmText: "Delete", icon: "🗑️" });
    if (!ok) return;
    const res = await apiRequest("/sessions/delete", "POST", { id });
    if (res.success) {
        showToast("Session profile deleted successfully", "info");
        fetchSessions();
    } else {
        showAlert("Error", `Could not delete session: ${res.error}`, "❌");
    }
}


// 3. PROMPTS
async function fetchPrompts() {
    const res = await apiRequest("/prompts");
    if (res.success && res.prompts) {
        appState.prompts = res.prompts;
        renderPrompts(res.prompts);
    }
}

function renderPrompts(prompts) {
    const tbody = document.getElementById("prompts-table-body");
    if (!tbody) return;

    if (!prompts || prompts.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-muted); padding: 32px;">No prompts queued. Add custom prompts or select from Viral Prompts Vault.</td></tr>`;
        return;
    }

    tbody.innerHTML = prompts.map(p => `
        <tr>
            <td style="font-family: var(--font-mono); color: var(--text-muted);">#${p.id}</td>
            <td style="font-weight: 500; max-width: 400px; white-space: normal;">${escapeHtml(p.prompt_text)}</td>
            <td><span class="badge badge-cyan">${escapeHtml(p.category || 'General')}</span></td>
            <td><span class="badge ${p.status === 'Completed' ? 'badge-green' : (p.status === 'Pending' ? 'badge-yellow' : 'badge-red')}">${p.status}</span></td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="deletePrompt(${p.id})">Delete</button>
            </td>
        </tr>
    `).join("");
}

async function deletePrompt(id) {
    const res = await apiRequest("/prompts/delete", "POST", { id });
    if (res.success) fetchPrompts();
}

// 4. VIRAL PROMPTS
async function fetchViralPrompts(search = "") {
    const res = await apiRequest(`/viral-prompts?q=${encodeURIComponent(search)}`);
    if (res.success && res.prompts) {
        appState.viralPrompts = res.prompts;
        filterAndRenderViralPrompts();
    }
}

function filterAndRenderViralPrompts() {
    const container = document.getElementById("viral-prompts-container");
    if (!container) return;

    let filtered = appState.viralPrompts;
    if (appState.activeCategory && appState.activeCategory !== "ALL") {
        filtered = filtered.filter(p => {
            const cat = (p.category || "").toLowerCase();
            const target = appState.activeCategory.toLowerCase();
            return cat.includes(target) || target.includes(cat);
        });
    }

    if (!filtered || filtered.length === 0) {
        container.innerHTML = `
            <div class="glass-card full-width" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <p style="color: var(--text-muted);">No viral prompts match the selected category filter.</p>
            </div>`;
        return;
    }

    container.innerHTML = filtered.map(p => {
        const text = p.content || p.prompt || p.title || '';
        const previewText = text.length > 200 ? text.substring(0, 200) + "..." : text;
        const categoryName = p.category || 'Viral Library';
        const words = p.word_count || (text ? text.split(/\s+/).length : 0);
        const chars = p.char_count || text.length;

        return `
        <div class="viral-card">
            <div class="viral-card-header">
                <div class="viral-title">🔥 ${escapeHtml(p.title || 'Viral Prompt')}</div>
                <div class="viral-score">🔥 98% Score</div>
            </div>
            <div style="margin: 2px 0 6px 0;">
                <span class="badge badge-cyan">${escapeHtml(categoryName)}</span>
            </div>
            <div class="viral-body" style="font-size: 12px; color: var(--text-muted); line-height: 1.6; flex: 1; margin-bottom: 12px;">
                ${escapeHtml(previewText)}
            </div>
            <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 12px; display: flex; gap: 14px;">
                <span>📏 ${words} words</span>
                <span>🔤 ${chars} chars</span>
            </div>
            <div class="card-actions-row">
                <button class="btn btn-secondary btn-sm" id="btn-copy-${p.id}" onclick="copyViralById('${p.id}')">
                    📋 Copy Prompt
                </button>
                <button class="btn btn-accent btn-sm" onclick="addViralById('${p.id}')">
                    ➕ Add to Queue
                </button>
            </div>
        </div>`;
    }).join("");
}

async function copyViralById(promptId) {
    const item = appState.viralPrompts.find(p => p.id === promptId);
    if (!item) return;
    const text = item.content || item.prompt || item.title || '';

    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
        } else {
            const ta = document.createElement("textarea");
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            document.body.removeChild(ta);
        }

        const btn = document.getElementById(`btn-copy-${promptId}`);
        if (btn) {
            const origHTML = btn.innerHTML;
            btn.innerHTML = "✅ Copied!";
            btn.classList.add("btn-success");
            setTimeout(() => {
                btn.innerHTML = origHTML;
                btn.classList.remove("btn-success");
            }, 2000);
        }
    } catch (err) {
        showToast("Could not copy prompt: " + err.message, "error");
    }
}

async function copyAllVisibleViralPrompts() {
    let filtered = appState.viralPrompts;
    if (appState.activeCategory && appState.activeCategory !== "ALL") {
        filtered = filtered.filter(p => {
            const cat = (p.category || "").toLowerCase();
            const target = appState.activeCategory.toLowerCase();
            return cat.includes(target) || target.includes(cat);
        });
    }

    if (!filtered || filtered.length === 0) {
        return showToast("No prompts available to copy.", "warn");
    }

    const combinedText = filtered.map((p, idx) => `=== PROMPT #${idx + 1}: ${p.title} [${p.category || 'Viral'}] ===\n\n${p.content || p.prompt || p.title}\n\n`).join("--------------------------------------------------\n\n");

    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(combinedText);
        } else {
            const ta = document.createElement("textarea");
            ta.value = combinedText;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            document.body.removeChild(ta);
        }

        const btn = document.getElementById("btn-copy-all-viral");
        if (btn) {
            const origHTML = btn.innerHTML;
            btn.innerHTML = `✅ Copied ${filtered.length} Prompts!`;
            btn.classList.add("btn-success");
            setTimeout(() => {
                btn.innerHTML = origHTML;
                btn.classList.remove("btn-success");
            }, 2500);
        }
        showToast(`Copied ${filtered.length} viral prompts to clipboard`, "success");
    } catch (err) {
        showToast("Copy failed: " + err.message, "error");
    }
}

async function addViralById(promptId) {
    const item = appState.viralPrompts.find(p => p.id === promptId);
    if (!item) return;
    const text = item.content || item.prompt || item.title;
    const category = item.category || "Viral Library";

    const res = await apiRequest("/viral-prompts/add-to-queue", "POST", {
        prompts: [{ prompt: text, category }]
    });
    if (res.success) {
        showToast(`✅ "${item.title}" added to Prompt Queue!`, "success");
        fetchPrompts();
    } else {
        showAlert("Error", `Could not add prompt: ${res.error}`, "❌");
    }
}

// 5. AUTOMATION STATUS & CONTROL
async function fetchAutomationStatus() {
    const res = await apiRequest("/automation/status");
    if (res.success && res.automation) {
        const auto = res.automation;
        appState.isAutomationRunning = auto.is_running;

        const title = document.getElementById("auto-status-title");
        const btnStart = document.getElementById("btn-auto-start");
        const btnStop = document.getElementById("btn-auto-stop");
        const globalStart = document.getElementById("btn-global-start");
        const globalStop = document.getElementById("btn-global-stop");

        if (auto.is_running) {
            title.textContent = `⚡ Automation Workers Active (${auto.active_workers || 1} Threads Running)`;
            btnStart.classList.add("hidden");
            btnStop.classList.remove("hidden");
            globalStart.classList.add("hidden");
            globalStop.classList.remove("hidden");
            document.getElementById("system-status-text").textContent = "Automation Running...";
        } else {
            title.textContent = "Automation Workers Idle";
            btnStart.classList.remove("hidden");
            btnStop.classList.add("hidden");
            globalStart.classList.remove("hidden");
            globalStop.classList.add("hidden");
            document.getElementById("system-status-text").textContent = "System Ready";
        }
    }
}

async function startAutomation() {
    const res = await apiRequest("/automation/start", "POST");
    if (res.success) {
        showToast("🚀 Automation Queue started successfully!", "success");
        fetchAutomationStatus();
    } else {
        showAlert("Cannot Start Automation", res.error || "Unknown error", "⚠️");
    }
}

async function stopAutomation() {
    const res = await apiRequest("/automation/stop", "POST");
    if (res.success) {
        fetchAutomationStatus();
    }
}

// 6. DOWNLOADS & VIDEO GALLERY
let currentPlayingVideoPath = "";

async function fetchDownloads() {
    const res = await apiRequest("/downloads");
    if (res.success && res.files) {
        appState.downloads = res.files;
        renderDownloads(res.files);
    }
}

function renderDownloads(files) {
    const galleryGrid = document.getElementById("downloads-gallery-grid");
    const tbody = document.getElementById("downloads-table-body");
    const countBadge = document.getElementById("downloads-count-badge");
    
    if (countBadge) {
        countBadge.textContent = `${(files && files.length) || 0} Video${files && files.length === 1 ? '' : 's'}`;
    }

    if (!files || files.length === 0) {
        const emptyHtml = `
            <div class="video-empty-state" style="grid-column: 1 / -1; text-align: center; padding: 48px 20px; background: rgba(255,255,255,0.02); border-radius: var(--radius-md); border: 1px dashed var(--border-subtle);">
                <div style="font-size: 40px; margin-bottom: 12px;">🎬</div>
                <h4 style="font-size: 16px; font-weight: 700; margin-bottom: 6px; color: #ffffff;">No Videos Rendered Yet</h4>
                <p style="color: var(--text-muted); font-size: 13px; max-width: 420px; margin: 0 auto 16px auto;">
                    Generated MP4 videos will automatically appear here as interactive playable cards.
                </p>
                <button class="btn btn-primary btn-sm btn-start-automation-run" onclick="startAutomation()">🚀 Launch Queue</button>
            </div>
        `;
        if (galleryGrid) galleryGrid.innerHTML = emptyHtml;
        if (tbody) tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color: var(--text-muted); padding: 32px;">No MP4 videos generated yet.</td></tr>`;
        return;
    }

    // 1. Render Visual Video Gallery Cards
    if (galleryGrid) {
        galleryGrid.innerHTML = files.map((f, idx) => {
            const streamUrl = `${API_BASE}/video/stream?path=${encodeURIComponent(f.path)}`;
            const safeName = escapeHtml(f.name);
            const safePath = escapeHtml(f.path);
            
            return `
                <div class="video-card" data-video-path="${safePath}" data-video-name="${safeName}">
                    <div class="video-card-preview" onclick="playVideoModal('${encodeURIComponent(f.path)}', '${escapeHtml(f.name).replace(/'/g, "\\'")}', '${f.size_mb}', '${f.mtime}')">
                        <video class="video-card-thumb" src="${streamUrl}#t=0.5" preload="metadata" muted playsinline onloadedmetadata="adjustVideoCardRatio(this)"></video>
                        <div class="video-play-badge">
                            <span class="play-icon">▶</span>
                        </div>
                        <div class="video-duration-tag">${f.size_mb} MB</div>
                    </div>
                    <div class="video-card-content">
                        <div class="video-card-title" title="${safeName}">${safeName}</div>
                        <div class="video-card-meta">
                            <span>📅 ${f.mtime}</span>
                            <span class="badge badge-cyan ratio-badge" style="font-size: 10px; padding: 2px 6px;">HD MP4</span>
                        </div>
                        <div class="video-card-actions">
                            <button class="btn btn-primary btn-sm btn-play-card" onclick="playVideoModal('${encodeURIComponent(f.path)}', '${escapeHtml(f.name).replace(/'/g, "\\'")}', '${f.size_mb}', '${f.mtime}')">
                                <span>▶️</span> Play Video
                            </button>
                            <button class="btn btn-secondary btn-sm" onclick="openDownloadsFolder()" title="Show file in Explorer">
                                <span>📁</span> Folder
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join("");
    }

    // 2. Render Compact Table Rows
    if (tbody) {
        tbody.innerHTML = files.map(f => `
            <tr>
                <td style="font-weight: 700; color: var(--accent);">🎥 ${escapeHtml(f.name)}</td>
                <td style="font-family: var(--font-mono);">${f.size_mb} MB</td>
                <td style="color: var(--text-muted);">${f.mtime}</td>
                <td style="text-align: right;">
                    <button class="btn btn-primary btn-sm" onclick="playVideoModal('${encodeURIComponent(f.path)}', '${escapeHtml(f.name).replace(/'/g, "\\'")}', '${f.size_mb}', '${f.mtime}')" style="margin-right: 6px;">
                        ▶️ Play
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="openDownloadsFolder()">
                        📁 Folder
                    </button>
                </td>
            </tr>
        `).join("");
    }
}

// Dynamically adjust each card's aspect ratio to match the real video proportions (9:16 Vertical, 16:9 Landscape, 1:1 Square)
function adjustVideoCardRatio(videoEl) {
    if (!videoEl || !videoEl.videoWidth || !videoEl.videoHeight) return;
    const card = videoEl.closest(".video-card");
    if (!card) return;

    const preview = card.querySelector(".video-card-preview");
    const badge = card.querySelector(".ratio-badge");
    const ratio = videoEl.videoWidth / videoEl.videoHeight;

    if (preview) {
        if (ratio < 0.85) {
            // 9:16 Vertical Reels / Shorts
            preview.style.aspectRatio = "9 / 16";
            preview.style.maxHeight = "380px";
            card.classList.add("is-vertical");
            if (badge) {
                badge.textContent = "📱 9:16 Vertical";
                badge.className = "badge badge-purple ratio-badge";
            }
        } else if (ratio > 1.25) {
            // 16:9 Landscape
            preview.style.aspectRatio = "16 / 9";
            preview.style.maxHeight = "220px";
            card.classList.add("is-landscape");
            if (badge) {
                badge.textContent = "🖥️ 16:9 Landscape";
                badge.className = "badge badge-green ratio-badge";
            }
        } else {
            // 1:1 Square / 4:5 Portrait
            preview.style.aspectRatio = `${videoEl.videoWidth} / ${videoEl.videoHeight}`;
            preview.style.maxHeight = "280px";
            card.classList.add("is-square");
            if (badge) {
                badge.textContent = "⏹️ 1:1 Square";
                badge.className = "badge badge-cyan ratio-badge";
            }
        }
    }
}

function playVideoModal(encodedPath, fileName, sizeMb, mtime) {
    const rawPath = decodeURIComponent(encodedPath);
    currentPlayingVideoPath = rawPath;

    const modal = document.getElementById("modal-video-player");
    const modalCard = modal ? modal.querySelector(".video-player-modal-card") : null;
    const videoEl = document.getElementById("in-app-video-element");
    const titleEl = document.getElementById("video-modal-title");
    const metaEl = document.getElementById("video-modal-meta");
    const pathEl = document.getElementById("video-modal-filepath");

    if (titleEl) titleEl.textContent = fileName || "Video Playback";
    if (metaEl) metaEl.textContent = `${sizeMb ? sizeMb + ' MB' : 'MP4 Video'} • ${mtime || 'Verified Output'}`;
    if (pathEl) pathEl.textContent = `📍 ${rawPath}`;

    if (videoEl) {
        // Automatically adapt player modal dimensions to the native video aspect ratio
        videoEl.onloadedmetadata = () => {
            const ratio = videoEl.videoWidth / videoEl.videoHeight;
            if (modalCard) {
                modalCard.classList.remove("modal-vertical-video", "modal-landscape-video", "modal-square-video");
                if (ratio < 0.85) {
                    // Vertical Reel / TikTok 9:16 format
                    modalCard.classList.add("modal-vertical-video");
                    if (metaEl) metaEl.textContent = `📱 9:16 Vertical Reel (${videoEl.videoWidth}x${videoEl.videoHeight}) • ${sizeMb || ''} MB`;
                } else if (ratio > 1.25) {
                    // 16:9 Landscape format
                    modalCard.classList.add("modal-landscape-video");
                    if (metaEl) metaEl.textContent = `🖥️ 16:9 Landscape (${videoEl.videoWidth}x${videoEl.videoHeight}) • ${sizeMb || ''} MB`;
                } else {
                    modalCard.classList.add("modal-square-video");
                    if (metaEl) metaEl.textContent = `⏹️ Square Format (${videoEl.videoWidth}x${videoEl.videoHeight}) • ${sizeMb || ''} MB`;
                }
            }
        };

        videoEl.src = `${API_BASE}/video/stream?path=${encodeURIComponent(rawPath)}`;
        videoEl.load();
        videoEl.play().catch(e => console.log("Autoplay pending user gesture:", e));
    }

    if (modal) {
        modal.classList.remove("hidden");
    }
}

function closeVideoModal() {
    const modal = document.getElementById("modal-video-player");
    const videoEl = document.getElementById("in-app-video-element");
    if (videoEl) {
        videoEl.pause();
        videoEl.removeAttribute("src");
        videoEl.load();
    }
    if (modal) {
        modal.classList.add("hidden");
    }
}

async function openDownloadsFolder() {
    await apiRequest("/downloads/open", "POST");
}

// 7. LOGS
async function fetchLogs() {
    const res = await apiRequest("/logs");
    if (res.success && res.logs) {
        const consoleEl = document.getElementById("full-logs-console");
        const miniEl = document.getElementById("mini-logs-console");
        
        if (consoleEl && res.logs.length > 0) {
            consoleEl.innerHTML = res.logs.map(l => {
                let cls = "info";
                if (l.includes("WARN")) cls = "warn";
                if (l.includes("ERROR") || l.includes("CRASH") || l.includes("FAILED")) cls = "error";
                if (l.includes("SUCCESS") || l.includes("COMPLETED")) cls = "success";
                return `<div class="log-line ${cls}">${escapeHtml(l)}</div>`;
            }).join("");
            consoleEl.scrollTop = consoleEl.scrollHeight;
        }

        const miniBoxes = document.querySelectorAll(".mini-logs-box");
        if (miniBoxes.length > 0 && res.logs.length > 0) {
            const recent = res.logs.slice(-15);
            const logsHtml = recent.map(l => {
                let cls = "info";
                if (l.includes("WARN")) cls = "warn";
                if (l.includes("ERROR") || l.includes("CRASH") || l.includes("FAILED")) cls = "error";
                if (l.includes("SUCCESS") || l.includes("COMPLETED")) cls = "success";
                return `<div class="log-line ${cls}">${escapeHtml(l)}</div>`;
            }).join("");

            miniBoxes.forEach(box => {
                box.innerHTML = logsHtml;
                box.scrollTop = box.scrollHeight;
            });
        }
    }
}

// 8. SUPER ADMIN
async function fetchSuperAdminData() {
    try {
        const res = await apiRequest("/super-admin/data");
        if (res && res.success && res.super_admin) {
            const sa = res.super_admin;
            appState.superAdmin = sa;
            appState.superAdminUsers = sa.all_users || [];

            // Auto-select latest active date
            let summaryDates = Object.keys(sa.daily_summary || {}).sort().reverse();
            if (summaryDates.length === 0 && appState.superAdminUsers.length > 0) {
                const datesSet = new Set();
                appState.superAdminUsers.forEach(u => {
                    if (u.daily_activity) Object.keys(u.daily_activity).forEach(d => datesSet.add(d));
                    if (u.last_active_at && u.last_active_at.length >= 10) datesSet.add(u.last_active_at.slice(0, 10));
                });
                summaryDates = Array.from(datesSet).sort().reverse();
            }

            if ((!appState.selectedActivityDate || (!sa.daily_summary && !summaryDates.includes(appState.selectedActivityDate))) && summaryDates.length > 0) {
                appState.selectedActivityDate = summaryDates[0];
            } else if (!appState.selectedActivityDate) {
                appState.selectedActivityDate = new Date().toISOString().slice(0, 10);
            }

            const selDate = appState.selectedActivityDate;
            const datePicker = document.getElementById("sa-date-picker");
            if (datePicker) {
                datePicker.value = selDate;
            }

            // Compute metrics for selected date (Logins + Video Generations)
            let activeUsersOnDate = 0;
            let videosOnDate = 0;

            if (sa.daily_summary && sa.daily_summary[selDate]) {
                activeUsersOnDate = sa.daily_summary[selDate].active_users_count || 0;
                videosOnDate = sa.daily_summary[selDate].videos || 0;
            } else {
                appState.superAdminUsers.forEach(u => {
                    const isActive = (u.active_dates && u.active_dates.includes(selDate)) || 
                                     (u.last_active_at && u.last_active_at.startsWith(selDate)) ||
                                     (u.daily_activity && u.daily_activity[selDate] > 0);
                    const vids = (u.daily_activity && u.daily_activity[selDate]) ? u.daily_activity[selDate] : 0;
                    if (isActive) activeUsersOnDate++;
                    videosOnDate += vids;
                });
            }

            // Update KPI Counters
            animateCounter("sa-active-users-date", activeUsersOnDate);
            animateCounter("sa-videos-date", videosOnDate);
            animateCounter("sa-total-users", sa.total_users || appState.superAdminUsers.length);
            animateCounter("sa-pending-users", sa.pending_users || 0);
            animateCounter("sa-total-videos", sa.total_videos_all_time || 0);

            // Update Labels
            const activeLabel = document.getElementById("sa-active-label");
            if (activeLabel) activeLabel.textContent = `Active Users (${selDate})`;
            const videosLabel = document.getElementById("sa-videos-date-label");
            if (videosLabel) videosLabel.textContent = `Videos on ${selDate}`;
            const thDate = document.getElementById("th-date-videos");
            if (thDate) thDate.textContent = `Vids (${selDate.length >= 10 ? selDate.slice(5) : selDate})`;

            // Update Filter Chip Counts
            updateLeadFilterChipCounts(selDate);

            filterAndRenderSuperAdminTable();
            renderSuperAdminCharts(sa);
        }
    } catch (err) {
        console.error("fetchSuperAdminData error:", err);
    }
}

function updateLeadFilterChipCounts(selDate) {
    const users = appState.superAdminUsers || [];
    const cntAll = users.length;
    const cntActive = users.filter(u => {
        return (u.active_dates && u.active_dates.includes(selDate)) || 
               (u.last_active_at && u.last_active_at.startsWith(selDate)) ||
               (u.daily_activity && u.daily_activity[selDate] > 0);
    }).length;
    const cntHigh = users.filter(u => (u.total_videos || 0) >= 50).length;
    const cntPaid = users.filter(u => u.role === 'paid').length;
    const cntFree = users.filter(u => u.role === 'free').length;
    const cntPending = users.filter(u => u.status === 'Pending').length;
    const cntInactive = users.filter(u => (u.total_videos || 0) === 0).length;

    const setChip = (id, count) => {
        const el = document.getElementById(id);
        if (el) el.textContent = count;
    };

    setChip("chip-cnt-all", cntAll);
    setChip("chip-cnt-active", cntActive);
    setChip("chip-cnt-high", cntHigh);
    setChip("chip-cnt-paid", cntPaid);
    setChip("chip-cnt-free", cntFree);
    setChip("chip-cnt-pending", cntPending);
    setChip("chip-cnt-inactive", cntInactive);
}

function filterAndRenderSuperAdminTable() {
    const allUsers = appState.superAdminUsers || [];
    const selDate = appState.selectedActivityDate || new Date().toISOString().slice(0, 10);
    const filter = appState.selectedLeadFilter || "all";
    const searchInput = document.getElementById("input-sa-search");
    const query = searchInput ? searchInput.value.toLowerCase().trim() : "";

    let filtered = allUsers.filter(u => {
        // 1. Text Search match
        const matchesSearch = !query || 
            (u.email || '').toLowerCase().includes(query) || 
            (u.name || '').toLowerCase().includes(query) || 
            (u.whatsapp_number || '').toLowerCase().includes(query);
        
        if (!matchesSearch) return false;

        // 2. Lead Tag / Status Filter match
        if (filter === "active-date") {
            return (u.active_dates && u.active_dates.includes(selDate)) || 
                   (u.last_active_at && u.last_active_at.startsWith(selDate)) ||
                   (u.daily_activity && u.daily_activity[selDate] > 0);
        }
        if (filter === "high-producer") return (u.total_videos || 0) >= 50;
        if (filter === "paid") return u.role === 'paid';
        if (filter === "free") return u.role === 'free';
        if (filter === "pending") return u.status === 'Pending';
        if (filter === "inactive") return (u.total_videos || 0) === 0;
        return true;
    });

    renderSuperAdminTable(filtered);
}

function renderSuperAdminTable(users) {
    const tbody = document.getElementById("super-admin-table-body");
    if (!tbody) return;

    if (!users || users.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color: var(--text-muted); padding: 36px;">No creators found matching current filter criteria.</td></tr>`;
        return;
    }

    const selDate = appState.selectedActivityDate || new Date().toISOString().slice(0, 10);

    tbody.innerHTML = users.map(u => {
        const uRole = u.role || "free";
        const rawWa = (u.whatsapp_number || "").trim();
        const waClean = rawWa.replace(/[^0-9+]/g, "");
        const waHtml = rawWa ? `
            <a href="https://wa.me/${waClean.replace(/^\+/, '')}" target="_blank" class="wa-badge-link" title="Open WhatsApp Chat">
                <span class="wa-badge">📱 ${escapeHtml(rawWa)}</span>
            </a>` : `<span class="text-muted" style="font-size:12px;">—</span>`;

        const dateVids = (u.daily_activity && u.daily_activity[selDate]) ? u.daily_activity[selDate] : 0;
        const totalVids = u.total_videos || 0;
        const isActiveOnDate = (u.active_dates && u.active_dates.includes(selDate)) || 
                               (u.last_active_at && u.last_active_at.startsWith(selDate)) ||
                               (dateVids > 0);

        // Smart Tag based on selected date (Logins & Videos) & historical volume
        let tagHtml = '';
        if (isActiveOnDate) {
            tagHtml = `<span class="lead-tag-badge tag-daily-active">🔥 Active (${dateVids > 0 ? dateVids + ' vids' : 'Logged In'})</span>`;
        } else if (totalVids >= 50) {
            tagHtml = `<span class="lead-tag-badge tag-high-producer">⚡ High Producer</span>`;
        } else if (totalVids >= 10) {
            tagHtml = `<span class="lead-tag-badge tag-active-creator">✨ Creator</span>`;
        } else if (totalVids > 0) {
            tagHtml = `<span class="lead-tag-badge tag-low-activity">🌱 Low Activity</span>`;
        } else {
            tagHtml = `<span class="lead-tag-badge tag-inactive-lead">💤 Inactive Lead</span>`;
        }

        return `
        <tr>
            <td style="font-weight: 700; color: #ffffff;">${escapeHtml(u.email)}</td>
            <td>${escapeHtml(u.name || 'Creator')}</td>
            <td style="white-space: nowrap !important;">${waHtml}</td>
            <td>${tagHtml}</td>
            <td style="font-family: var(--font-mono); font-weight: 700; color: var(--accent);">${totalVids}</td>
            <td style="font-family: var(--font-mono); font-weight: 700; color: ${dateVids > 0 ? '#10b981' : 'var(--text-muted)'};">${dateVids}</td>
            <td>
                <span class="badge ${u.status === 'Active' ? 'badge-green' : (u.status === 'Pending' ? 'badge-yellow' : 'badge-red')}">${u.status}</span>
            </td>
            <td>
                <select class="role-select" onchange="changeUserRole('${u.user_id}', this.value)">
                    <option value="free" ${uRole === 'free' ? 'selected' : ''}>🟢 Free User</option>
                    <option value="paid" ${uRole === 'paid' ? 'selected' : ''}>⭐ Paid User</option>
                    <option value="admin" ${uRole === 'admin' ? 'selected' : ''}>👑 Admin</option>
                </select>
            </td>
            <td>
                ${u.status === 'Pending' ? `<button class="btn btn-accent btn-sm" onclick="toggleUserStatus('${u.user_id}', 'Active')">Approve</button>` : ''}
                ${u.status === 'Active' ? `<button class="btn btn-danger btn-sm" onclick="toggleUserStatus('${u.user_id}', 'Blocked')">Block</button>` : ''}
                ${u.status === 'Blocked' ? `<button class="btn btn-accent btn-sm" onclick="toggleUserStatus('${u.user_id}', 'Active')">Unblock</button>` : ''}
            </td>
        </tr>`;
    }).join("");
}

function exportCreatorsToExcel() {
    const allUsers = appState.superAdminUsers || [];
    if (!allUsers || allUsers.length === 0) {
        showToast("No creator data available to export!", "warn");
        return;
    }

    const selDate = appState.selectedActivityDate || new Date().toISOString().slice(0, 10);
    const filter = appState.selectedLeadFilter || "all";
    const searchInput = document.getElementById("input-sa-search");
    const query = searchInput ? searchInput.value.toLowerCase().trim() : "";

    // Export current filtered list so admin can download specific lead segments
    const exportUsers = allUsers.filter(u => {
        const matchesSearch = !query || 
            (u.email || '').toLowerCase().includes(query) || 
            (u.name || '').toLowerCase().includes(query) || 
            (u.whatsapp_number || '').toLowerCase().includes(query);
        if (!matchesSearch) return false;

        if (filter === "active-date") return (u.active_dates && u.active_dates.includes(selDate)) || (u.last_active_at && u.last_active_at.startsWith(selDate)) || (u.daily_activity && u.daily_activity[selDate] > 0);
        if (filter === "high-producer") return (u.total_videos || 0) >= 50;
        if (filter === "paid") return u.role === 'paid';
        if (filter === "free") return u.role === 'free';
        if (filter === "pending") return u.status === 'Pending';
        if (filter === "inactive") return (u.total_videos || 0) === 0;
        return true;
    });

    const headers = [
        "Rank", 
        "Creator Email", 
        "Full Name", 
        "WhatsApp Number", 
        "Activity Tag", 
        "Total Videos", 
        `Videos On ${selDate}`, 
        "Account Status", 
        "Assigned Role", 
        "Last Active Date", 
        "Registration Date"
    ];
    
    const rows = exportUsers.map((u, idx) => {
        const dateVids = (u.daily_activity && u.daily_activity[selDate]) ? u.daily_activity[selDate] : 0;
        const isActive = (u.active_dates && u.active_dates.includes(selDate)) || 
                         (u.last_active_at && u.last_active_at.startsWith(selDate)) || 
                         dateVids > 0;
        let tag = u.lead_tag || "Creator";
        if (isActive) tag = "Daily Active";

        return [
            idx + 1,
            `"${(u.email || '').replace(/"/g, '""')}"`,
            `"${(u.name || '').replace(/"/g, '""')}"`,
            `"${(u.whatsapp_number || '').replace(/"/g, '""')}"`,
            `"${tag}"`,
            u.total_videos || 0,
            dateVids,
            `"${(u.status || 'Pending').replace(/"/g, '""')}"`,
            `"${(u.role || 'free').replace(/"/g, '""')}"`,
            `"${(u.last_active_at || '').replace(/"/g, '""')}"`,
            `"${(u.created_at || '').replace(/"/g, '""')}"`
        ];
    });

    const csvContent = "\uFEFF" + [headers.join(","), ...rows.map(e => e.join(","))].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `Creators_Leads_Export_${filter}_${selDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    showToast(`📊 Exported ${exportUsers.length} creator leads to Excel successfully!`, "success");
}

async function changeUserRole(userId, newRole) {
    const res = await apiRequest("/super-admin/update-role", "POST", {
        user_id: userId,
        new_role: newRole
    });
    if (res.success) {
        showToast("Creator role updated successfully", "success");
        fetchSuperAdminData();
    } else {
        showAlert("Error", `Could not update role: ${res.error}`, "❌");
    }
}

function renderSuperAdminCharts(saOrUsers) {
    if (typeof Chart === "undefined") return;
    const sa = (saOrUsers && saOrUsers.all_users) ? saOrUsers : (appState.superAdmin || {});
    const users = sa.all_users || appState.superAdminUsers || [];

    // 1. Daily Active Users Trend Chart
    try {
        const ctxTrend = document.getElementById("chart-daily-active-trend");
        if (ctxTrend) {
            if (superAdminCharts.dailyActiveTrend) {
                superAdminCharts.dailyActiveTrend.destroy();
                superAdminCharts.dailyActiveTrend = null;
            }

            let dailySummary = sa.daily_summary || {};
            let sortedDates = Object.keys(dailySummary).sort();

            if (sortedDates.length === 0 && users.length > 0) {
                dailySummary = {};
                users.forEach(u => {
                    if (u.daily_activity) {
                        Object.entries(u.daily_activity).forEach(([d, count]) => {
                            if (!dailySummary[d]) dailySummary[d] = { videos: 0, active_users_count: 0, _users: new Set() };
                            dailySummary[d].videos += count;
                            dailySummary[d]._users.add(u.email || u.user_id);
                        });
                    }
                    if (u.last_active_at && u.last_active_at.length >= 10) {
                        const d = u.last_active_at.slice(0, 10);
                        if (!dailySummary[d]) dailySummary[d] = { videos: 0, active_users_count: 0, _users: new Set() };
                        dailySummary[d]._users.add(u.email || u.user_id);
                    }
                });
                Object.keys(dailySummary).forEach(d => {
                    dailySummary[d].active_users_count = dailySummary[d]._users ? dailySummary[d]._users.size : 1;
                });
                sortedDates = Object.keys(dailySummary).sort().slice(-14);
            }

            const chartDates = sortedDates.length > 0 ? sortedDates : [appState.selectedActivityDate];
            const activeData = chartDates.map(d => dailySummary[d] ? dailySummary[d].active_users_count : 0);
            const videoData = chartDates.map(d => dailySummary[d] ? dailySummary[d].videos : 0);

            superAdminCharts.dailyActiveTrend = new Chart(ctxTrend, {
                type: 'bar',
                data: {
                    labels: chartDates.map(d => (d && d.length >= 10) ? d.slice(5) : d),
                    datasets: [
                        {
                            type: 'line',
                            label: 'Daily Active Users',
                            data: activeData,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.15)',
                            borderWidth: 2.5,
                            pointBackgroundColor: '#34d399',
                            pointRadius: 4,
                            tension: 0.3,
                            yAxisID: 'y1'
                        },
                        {
                            type: 'bar',
                            label: 'Videos Generated',
                            data: videoData,
                            backgroundColor: 'rgba(139, 92, 246, 0.65)',
                            borderColor: '#8b5cf6',
                            borderWidth: 1.5,
                            borderRadius: 6,
                            yAxisID: 'y'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onHover: (event, elements, chart) => { chart.canvas.style.cursor = 'default'; },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: { color: '#94a3b8', font: { size: 11, weight: 'bold' } }
                        }
                    },
                    scales: {
                        x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
                        y: {
                            type: 'linear',
                            position: 'left',
                            ticks: { color: '#8b5cf6' },
                            grid: { color: 'rgba(255, 255, 255, 0.05)' }
                        },
                        y1: {
                            type: 'linear',
                            position: 'right',
                            ticks: { color: '#10b981', stepSize: 1 },
                            grid: { display: false }
                        }
                    }
                }
            });
        }
    } catch (e) {
        console.error("Trend chart render error:", e);
    }

    // 2. Top 10 Creators Bar Chart
    try {
        const sortedUsers = [...users].sort((a, b) => (b.total_videos || 0) - (a.total_videos || 0)).slice(0, 10);
        const labels = sortedUsers.map(u => u.name || u.email.split("@")[0]);
        const videoCounts = sortedUsers.map(u => u.total_videos || 0);

        const ctxTop = document.getElementById("chart-top-creators");
        if (ctxTop) {
            if (superAdminCharts.topCreators) {
                superAdminCharts.topCreators.destroy();
                superAdminCharts.topCreators = null;
            }
            superAdminCharts.topCreators = new Chart(ctxTop, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Total Videos Generated',
                        data: videoCounts,
                        backgroundColor: 'rgba(6, 182, 212, 0.75)',
                        borderColor: '#06b6d4',
                        borderWidth: 1.5,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onHover: (event, elements, chart) => { chart.canvas.style.cursor = 'default'; },
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { display: false } },
                        y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } }
                    }
                }
            });
        }
    } catch (e) {
        console.error("Top creators chart render error:", e);
    }

    // 3. Status Donut Chart
    try {
        const activeCount = users.filter(u => u.status === 'Active').length;
        const pendingCount = users.filter(u => u.status === 'Pending').length;
        const blockedCount = users.filter(u => u.status === 'Blocked').length;

        const ctxDonut = document.getElementById("chart-status-donut");
        if (ctxDonut) {
            if (superAdminCharts.statusDonut) {
                superAdminCharts.statusDonut.destroy();
                superAdminCharts.statusDonut = null;
            }
            superAdminCharts.statusDonut = new Chart(ctxDonut, {
                type: 'doughnut',
                data: {
                    labels: ['Active Creators', 'Pending Approvals', 'Blocked Accounts'],
                    datasets: [{
                        data: [activeCount, pendingCount, blockedCount],
                        backgroundColor: ['#10b981', '#fbbf24', '#f43f5e'],
                        borderWidth: 2,
                        borderColor: '#070913'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onHover: (event, elements, chart) => { chart.canvas.style.cursor = 'default'; },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#f8fafc', font: { size: 12, weight: 'bold' }, padding: 14 }
                        }
                    },
                    cutout: '70%'
                }
            });
        }
    } catch (e) {
        console.error("Donut chart render error:", e);
    }

    // 4. Testing Lab: Leads Generation Trend Chart
    try {
        const ctxLeadsTrend = document.getElementById("chart-testing-leads-trend");
        if (ctxLeadsTrend) {
            if (superAdminCharts.testingLeadsTrend) {
                superAdminCharts.testingLeadsTrend.destroy();
                superAdminCharts.testingLeadsTrend = null;
            }

            const leadsLabels = ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00", "00:00"];
            const rawLeadsData = [45, 82, 120, 195, 240, 310, 280, 190, 140, 95];
            const cumulativeData = [45, 127, 247, 442, 682, 992, 1272, 1462, 1602, 1697];

            superAdminCharts.testingLeadsTrend = new Chart(ctxLeadsTrend, {
                type: 'bar',
                data: {
                    labels: leadsLabels,
                    datasets: [
                        {
                            type: 'line',
                            label: 'Cumulative Ingested Leads',
                            data: cumulativeData,
                            borderColor: '#38bdf8',
                            backgroundColor: 'rgba(56, 189, 248, 0.15)',
                            borderWidth: 3,
                            pointBackgroundColor: '#38bdf8',
                            pointRadius: 4,
                            tension: 0.35,
                            yAxisID: 'y1'
                        },
                        {
                            type: 'bar',
                            label: 'Hourly Leads Discovered',
                            data: rawLeadsData,
                            backgroundColor: 'rgba(16, 185, 129, 0.7)',
                            borderColor: '#10b981',
                            borderWidth: 1.5,
                            borderRadius: 6,
                            yAxisID: 'y'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onHover: (event, elements, chart) => { chart.canvas.style.cursor = 'default'; },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: { color: '#94a3b8', font: { size: 11, weight: 'bold' } }
                        }
                    },
                    scales: {
                        x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
                        y: {
                            type: 'linear',
                            position: 'left',
                            ticks: { color: '#10b981' },
                            grid: { color: 'rgba(255, 255, 255, 0.05)' }
                        },
                        y1: {
                            type: 'linear',
                            position: 'right',
                            ticks: { color: '#38bdf8' },
                            grid: { display: false }
                        }
                    }
                }
            });
        }
    } catch (e) {
        console.error("Testing leads trend chart render error:", e);
    }

    // 5. Testing Lab: Lead Sources & Channel Breakdown Donut
    try {
        const ctxLeadsSource = document.getElementById("chart-testing-leads-sources");
        if (ctxLeadsSource) {
            if (superAdminCharts.testingLeadsSources) {
                superAdminCharts.testingLeadsSources.destroy();
                superAdminCharts.testingLeadsSources = null;
            }

            superAdminCharts.testingLeadsSources = new Chart(ctxLeadsSource, {
                type: 'doughnut',
                data: {
                    labels: ['Facebook Ads', 'Organic Reels', 'Direct Ingestion', 'Viral Seeds'],
                    datasets: [{
                        data: [540, 420, 310, 212],
                        backgroundColor: ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b'],
                        borderWidth: 2,
                        borderColor: '#070913'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onHover: (event, elements, chart) => { chart.canvas.style.cursor = 'default'; },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#f8fafc', font: { size: 11, weight: 'bold' }, padding: 10 }
                        }
                    },
                    cutout: '65%'
                }
            });
        }
    } catch (e) {
        console.error("Testing leads sources donut render error:", e);
    }
}

// ── MODERN EXECUTIVE DASHBOARD CHARTS ────────────────────────────────────
let dashboardCharts = {
    production: null,
    sessions: null
};

function renderDashboardCharts(stats) {
    if (!stats || typeof Chart === 'undefined') return;

    // 1. Video Production Velocity & Throughput Spline Gradient Chart
    try {
        const ctxProd = document.getElementById("dash-chart-production");
        if (ctxProd) {
            ctxProd.style.cursor = "default";
            if (dashboardCharts.production) {
                dashboardCharts.production.destroy();
                dashboardCharts.production = null;
            }

            // Generate last 7 days labels (e.g. "Aug 14", "Aug 15", ...)
            const daysLabels = [];
            const completedSeries = [];
            const pendingSeries = [];

            const totalCompleted = stats.user_today_videos !== undefined ? stats.user_today_videos : (stats.completed_prompts || 0);
            const pendingCount = stats.pending_prompts || 0;
            const lifetimeCount = stats.user_total_videos !== undefined ? stats.user_total_videos : (stats.lifetime_videos || 0);
            const userDaily = stats.user_daily_activity || {};

            // Update badge text
            const badgeTotal = document.getElementById("dash-chart-total-badge");
            if (badgeTotal) badgeTotal.textContent = `${lifetimeCount} Videos Generated`;
            const badgeSpeed = document.getElementById("dash-chart-speed-badge");
            if (badgeSpeed) badgeSpeed.textContent = `⚡ Seedance 2.0 Engine`;

            // Update bottom metric status
            const elEngine = document.getElementById("dash-stat-engine-status");
            if (elEngine) {
                elEngine.textContent = appState.isAutomationRunning ? "Running 🚀" : "System Ready 🟢";
                elEngine.style.color = appState.isAutomationRunning ? "#06b6d4" : "#10b981";
            }

            for (let i = 6; i >= 0; i--) {
                const d = new Date();
                d.setDate(d.getDate() - i);
                
                // Format YYYY-MM-DD
                const year = d.getFullYear();
                const month = String(d.getMonth() + 1).padStart(2, '0');
                const day = String(d.getDate()).padStart(2, '0');
                const dateKey = `${year}-${month}-${day}`;

                const label = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
                daysLabels.push(label);

                const countForDay = userDaily[dateKey] !== undefined ? userDaily[dateKey] : (i === 0 ? totalCompleted : 0);
                completedSeries.push(countForDay);
                pendingSeries.push(i === 0 ? pendingCount : 0);
            }

            const gradient1 = ctxProd.getContext("2d").createLinearGradient(0, 0, 0, 220);
            gradient1.addColorStop(0, "rgba(6, 182, 212, 0.4)");
            gradient1.addColorStop(1, "rgba(6, 182, 212, 0.0)");

            const gradient2 = ctxProd.getContext("2d").createLinearGradient(0, 0, 0, 220);
            gradient2.addColorStop(0, "rgba(168, 85, 247, 0.3)");
            gradient2.addColorStop(1, "rgba(168, 85, 247, 0.0)");

            dashboardCharts.production = new Chart(ctxProd, {
                type: 'line',
                data: {
                    labels: daysLabels,
                    datasets: [
                        {
                            label: 'Rendered Videos',
                            data: completedSeries,
                            borderColor: '#06b6d4',
                            backgroundColor: gradient1,
                            borderWidth: 2.5,
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: '#06b6d4',
                            pointBorderColor: '#ffffff',
                            pointBorderWidth: 1.5,
                            pointRadius: 4,
                            pointHoverRadius: 6
                        },
                        {
                            label: 'Queue Volume',
                            data: pendingSeries,
                            borderColor: '#a855f7',
                            backgroundColor: gradient2,
                            borderWidth: 2,
                            borderDash: [4, 4],
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: '#a855f7',
                            pointRadius: 3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onHover: (event, elements, chart) => { chart.canvas.style.cursor = 'default'; },
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            align: 'end',
                            labels: {
                                color: '#94a3b8',
                                boxWidth: 12,
                                font: { family: 'Inter', size: 11, weight: '600' }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.94)',
                            titleColor: '#ffffff',
                            bodyColor: '#e2e8f0',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            padding: 10,
                            boxPadding: 4
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#64748b', font: { family: 'Inter', size: 11 } },
                            grid: { display: false }
                        },
                        y: {
                            ticks: { color: '#64748b', font: { family: 'Inter', size: 11 } },
                            grid: { color: 'rgba(255, 255, 255, 0.04)' },
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    } catch (err) {
        console.error("Dashboard production chart error:", err);
    }

    // 2. Session Pool Health & Quota Doughnut Chart
    try {
        const ctxSess = document.getElementById("dash-chart-sessions");
        if (ctxSess) {
            if (dashboardCharts.sessions) {
                dashboardCharts.sessions.destroy();
                dashboardCharts.sessions = null;
            }

            const availCount = stats.available_sessions || 0;
            const runningCount = stats.running_sessions || 0;
            const expiredCount = stats.expired_sessions || 0;
            const disabledCount = stats.disabled_sessions || 0;

            const elAvail = document.getElementById("stat-avail-count");
            if (elAvail) elAvail.textContent = availCount;
            const elRunning = document.getElementById("stat-running-count");
            if (elRunning) elRunning.textContent = runningCount;
            const elExpired = document.getElementById("stat-expired-count");
            if (elExpired) elExpired.textContent = expiredCount + disabledCount;

            const total = availCount + runningCount + expiredCount + disabledCount;
            const dataCounts = total > 0 ? [availCount, runningCount, expiredCount + disabledCount] : [1, 0, 0];
            const bgColors = total > 0 
                ? ['#10b981', '#f59e0b', '#f43f5e'] 
                : ['rgba(16, 185, 129, 0.4)', 'rgba(245, 158, 11, 0.2)', 'rgba(244, 63, 94, 0.2)'];

            dashboardCharts.sessions = new Chart(ctxSess, {
                type: 'doughnut',
                data: {
                    labels: ['Available (Ready)', 'In-Use (Running)', 'Expired / Cooldown'],
                    datasets: [{
                        data: dataCounts,
                        backgroundColor: bgColors,
                        borderWidth: 2,
                        borderColor: '#0b0f19',
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onHover: (event, elements, chart) => { chart.canvas.style.cursor = 'default'; },
                    cutout: '72%',
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.94)',
                            titleColor: '#ffffff',
                            bodyColor: '#e2e8f0',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1
                        }
                    }
                }
            });
        }
    } catch (err) {
        console.error("Dashboard session chart error:", err);
    }
}

async function toggleUserStatus(userId, newStatus) {
    const res = await apiRequest("/super-admin/toggle-status", "POST", {
        user_id: userId,
        new_status: newStatus
    });
    if (res.success) {
        showToast(`Creator status updated to ${newStatus}`, "success");
        fetchSuperAdminData();
    } else {
        showAlert("Status Update Failed", `Error updating status: ${res.error}`, "❌");
    }
}

// ── EVENT HANDLERS & MODALS ───────────────────────────────────────────────
function initEventHandlers() {
    // Start / Stop Automation buttons
    const btnGlobStart = document.getElementById("btn-global-start");
    if (btnGlobStart) btnGlobStart.addEventListener("click", startAutomation);
    const btnGlobStop = document.getElementById("btn-global-stop");
    if (btnGlobStop) btnGlobStop.addEventListener("click", stopAutomation);
    const btnAutoStart = document.getElementById("btn-auto-start");
    if (btnAutoStart) btnAutoStart.addEventListener("click", startAutomation);
    const btnAutoStop = document.getElementById("btn-auto-stop");
    if (btnAutoStop) btnAutoStop.addEventListener("click", stopAutomation);
    const btnDashStartRun = document.getElementById("btn-dash-start-run");
    if (btnDashStartRun) btnDashStartRun.addEventListener("click", startAutomation);
    const btnPromptsStartRun = document.getElementById("btn-prompts-start-run");
    if (btnPromptsStartRun) btnPromptsStartRun.addEventListener("click", startAutomation);

    // Copy All Visible Prompts Button
    const btnCopyAll = document.getElementById("btn-copy-all-viral");
    if (btnCopyAll) {
        btnCopyAll.addEventListener("click", copyAllVisibleViralPrompts);
    }

    // Live Search on Creators Directory Table (Search by email, name, or WhatsApp)
    const inputSaSearch = document.getElementById("input-sa-search");
    if (inputSaSearch) {
        inputSaSearch.addEventListener("input", () => {
            filterAndRenderSuperAdminTable();
        });
    }

    // Date Picker for Super Admin
    const datePicker = document.getElementById("sa-date-picker");
    if (datePicker) {
        datePicker.addEventListener("change", (e) => {
            if (e.target.value) {
                appState.selectedActivityDate = e.target.value;
                document.querySelectorAll(".btn-date-chip").forEach(b => b.classList.remove("active"));
                fetchSuperAdminData();
            }
        });
    }

    // Date Shortcut Buttons
    document.querySelectorAll(".btn-date-chip").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".btn-date-chip").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            const shortcut = btn.dataset.dateshortcut;
            const now = new Date();
            if (shortcut === "today" || shortcut === "all") {
                appState.selectedActivityDate = now.toISOString().slice(0, 10);
            } else if (shortcut === "yesterday") {
                const yest = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                appState.selectedActivityDate = yest.toISOString().slice(0, 10);
            } else if (shortcut === "last7") {
                appState.selectedActivityDate = now.toISOString().slice(0, 10);
            }
            const dp = document.getElementById("sa-date-picker");
            if (dp) dp.value = appState.selectedActivityDate;
            fetchSuperAdminData();
        });
    });

    // Lead Filter Chips (All, Daily Active, High Producers, etc.)
    document.querySelectorAll(".lead-filter-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            document.querySelectorAll(".lead-filter-chip").forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            appState.selectedLeadFilter = chip.dataset.filter;
            filterAndRenderSuperAdminTable();
        });
    });

    // Export to Excel Button
    const btnExportExcel = document.getElementById("btn-export-excel");
    if (btnExportExcel) {
        btnExportExcel.addEventListener("click", exportCreatorsToExcel);
    }

    // Save Dashboard / Prompts Config Helper
    async function saveAppConfiguration(sourceSessInputId, sourceVidInputId) {
        const sessEl = document.getElementById(sourceSessInputId);
        const vidEl = document.getElementById(sourceVidInputId);
        const sessionsAtTime = parseInt(sessEl ? sessEl.value : 3) || 3;
        const videosPerSession = parseInt(vidEl ? vidEl.value : 15) || 15;
        
        const res = await apiRequest("/config/update", "POST", {
            sessions_at_a_time: sessionsAtTime,
            videos_per_session: videosPerSession
        });
        if (res.success) {
            showToast("Configuration saved successfully!", "success");
            // Sync all config inputs
            document.querySelectorAll(".cfg-sessions-input").forEach(el => el.value = sessionsAtTime);
            document.querySelectorAll(".cfg-videos-input").forEach(el => el.value = videosPerSession);
            const cfgS = document.getElementById("cfg-sessions-at-a-time");
            if (cfgS) cfgS.value = sessionsAtTime;
            const cfgV = document.getElementById("cfg-videos-per-session");
            if (cfgV) cfgV.value = videosPerSession;
        } else {
            showAlert("Config Error", `Error saving config: ${res.error}`, "❌");
        }
    }

    // Save Dashboard Config
    const btnSaveDashCfg = document.getElementById("btn-save-dash-config");
    if (btnSaveDashCfg) {
        btnSaveDashCfg.addEventListener("click", () => saveAppConfiguration("cfg-sessions-at-a-time", "cfg-videos-per-session"));
    }
    const btnSavePromptsCfg = document.getElementById("btn-save-prompts-config");
    if (btnSavePromptsCfg) {
        btnSavePromptsCfg.addEventListener("click", () => saveAppConfiguration("cfg-sessions-at-a-time-prompts", "cfg-videos-per-session-prompts"));
    }

    // Clear Logs Button
    const btnClearLogs = document.getElementById("btn-clear-logs");
    if (btnClearLogs) {
        btnClearLogs.addEventListener("click", () => {
            const consoleEl = document.getElementById("full-logs-console");
            if (consoleEl) consoleEl.innerHTML = `<div class="log-line info">Logs cleared by user.</div>`;
        });
    }
    const btnClearMainLogs = document.getElementById("btn-clear-main-logs");
    if (btnClearMainLogs) {
        btnClearMainLogs.addEventListener("click", () => {
            const logsEl = document.getElementById("logs-container");
            if (logsEl) logsEl.innerHTML = `<div class="log-line info">Console cleared by user. Standby...</div>`;
        });
    }

    // Open Directory Buttons
    document.querySelectorAll(".btn-open-downloads-dir").forEach(btn => {
        btn.addEventListener("click", openDownloadsFolder);
    });
    const btnOpenDirDash = document.getElementById("btn-open-dir-dash");
    if (btnOpenDirDash) btnOpenDirDash.addEventListener("click", openDownloadsFolder);
    const btnOpenDirPrompts = document.getElementById("btn-open-dir-prompts");
    if (btnOpenDirPrompts) btnOpenDirPrompts.addEventListener("click", openDownloadsFolder);
    const btnOpenDlDir = document.getElementById("btn-open-downloads-dir");
    if (btnOpenDlDir) btnOpenDlDir.addEventListener("click", openDownloadsFolder);

    // Video Gallery View Toggle (Grid vs Table)
    const btnViewGallery = document.getElementById("btn-view-gallery");
    const btnViewTable = document.getElementById("btn-view-table");
    const galleryGrid = document.getElementById("downloads-gallery-grid");
    const tableContainer = document.getElementById("downloads-table-container");

    if (btnViewGallery && btnViewTable) {
        btnViewGallery.addEventListener("click", () => {
            btnViewGallery.classList.add("active");
            btnViewTable.classList.remove("active");
            if (galleryGrid) galleryGrid.classList.remove("hidden");
            if (tableContainer) tableContainer.classList.add("hidden");
        });

        btnViewTable.addEventListener("click", () => {
            btnViewTable.classList.add("active");
            btnViewGallery.classList.remove("active");
            if (tableContainer) tableContainer.classList.remove("hidden");
            if (galleryGrid) galleryGrid.classList.add("hidden");
        });
    }

    const btnRefreshDownloads = document.getElementById("btn-refresh-downloads");
    if (btnRefreshDownloads) {
        btnRefreshDownloads.addEventListener("click", async () => {
            showToast("Refreshing generated video media...", "info");
            await fetchDownloads();
        });
    }

    // Search Viral Prompts
    const inputViral = document.getElementById("input-viral-search");
    if (inputViral) {
        inputViral.addEventListener("input", (e) => {
            fetchViralPrompts(e.target.value);
        });
    }

    // Clear Completed Prompts
    const btnClearCompletedPrompts = document.getElementById("btn-clear-completed-prompts");
    if (btnClearCompletedPrompts) {
        btnClearCompletedPrompts.addEventListener("click", async () => {
            const res = await apiRequest("/prompts/clear-completed", "POST", {});
            if (res.success) {
                showToast(res.message || "Completed prompts cleared successfully!", "info");
                await fetchPrompts();
                await fetchStats();
            } else {
                showAlert("Error", res.error || "Could not clear completed prompts", "❌");
            }
        });
    }

    // Clear All Prompts
    const btnClearAllPrompts = document.getElementById("btn-clear-all-prompts");
    if (btnClearAllPrompts) {
        btnClearAllPrompts.addEventListener("click", async () => {
            if (!appState.prompts || appState.prompts.length === 0) {
                return showToast("Prompt queue is already empty!", "info");
            }
            const count = appState.prompts.length;
            const ok = await showConfirm(
                "Clear All Prompts",
                `Are you sure you want to delete all ${count} prompt(s) from the queue? This will remove all currently queued prompts.`,
                { isDanger: true, confirmText: "Clear All", icon: "🗑️" }
            );
            if (!ok) return;

            const res = await apiRequest("/prompts/clear-all", "POST", {});
            if (res.success) {
                showToast(res.message || "All prompts cleared successfully!", "success");
                await fetchPrompts();
                await fetchStats();
            } else {
                showAlert("Error", res.error || "Could not clear prompts", "❌");
            }
        });
    }

    // Super Admin Refresh
    const btnRefSuper = document.getElementById("btn-refresh-super");
    if (btnRefSuper) btnRefSuper.addEventListener("click", fetchSuperAdminData);

    // Session Toolbar Events
    const btnRefSess = document.getElementById("btn-refresh-sessions");
    if (btnRefSess) btnRefSess.addEventListener("click", () => fetchSessions());

    const btnSelAllAvail = document.getElementById("btn-sess-select-all-avail");
    if (btnSelAllAvail) {
        btnSelAllAvail.addEventListener("click", () => {
            document.querySelectorAll("#tbody-available-sessions .sess-chk").forEach(c => c.checked = true);
            const headChk = document.getElementById("chk-head-avail");
            if (headChk) headChk.checked = true;
        });
    }

    const btnDeselectAll = document.getElementById("btn-sess-deselect-all");
    if (btnDeselectAll) {
        btnDeselectAll.addEventListener("click", () => {
            document.querySelectorAll(".sess-chk").forEach(c => c.checked = false);
            const headAvail = document.getElementById("chk-head-avail");
            if (headAvail) headAvail.checked = false;
            const headExp = document.getElementById("chk-head-exp");
            if (headExp) headExp.checked = false;
        });
    }

    const btnDeleteSel = document.getElementById("btn-sess-delete-selected");
    if (btnDeleteSel) {
        btnDeleteSel.addEventListener("click", async () => {
            const checkedIds = Array.from(document.querySelectorAll(".sess-chk:checked")).map(c => parseInt(c.dataset.id)).filter(Boolean);
            if (checkedIds.length === 0) {
                return showAlert("Selection Required", "Please select at least one session to delete!", "⚠️");
            }
            const ok = await showConfirm("Delete Selected Sessions", `Are you sure you want to delete ${checkedIds.length} selected session profile(s)?`, { isDanger: true, confirmText: "Delete", icon: "🗑️" });
            if (!ok) return;
            const res = await apiRequest("/sessions/bulk-delete", "POST", { ids: checkedIds });
            if (res.success) {
                showToast(`Deleted ${res.count || checkedIds.length} session profile(s)`, "info");
                fetchSessions();
            } else {
                showAlert("Error", `Could not delete sessions: ${res.error}`, "❌");
            }
        });
    }

    const chkHeadAvail = document.getElementById("chk-head-avail");
    if (chkHeadAvail) {
        chkHeadAvail.addEventListener("change", (e) => {
            document.querySelectorAll("#tbody-available-sessions .sess-chk").forEach(c => c.checked = e.target.checked);
        });
    }

    const chkHeadExp = document.getElementById("chk-head-exp");
    if (chkHeadExp) {
        chkHeadExp.addEventListener("change", (e) => {
            document.querySelectorAll("#tbody-expired-sessions .sess-chk").forEach(c => c.checked = e.target.checked);
        });
    }
}

function initPasswordToggles() {
    document.querySelectorAll(".btn-toggle-password").forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            const input = document.getElementById(targetId);
            if (!input) return;

            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";

            const eyeOpen = btn.querySelector(".eye-open");
            const eyeClosed = btn.querySelector(".eye-closed");
            if (eyeOpen && eyeClosed) {
                if (isPassword) {
                    eyeOpen.classList.add("hidden");
                    eyeClosed.classList.remove("hidden");
                } else {
                    eyeOpen.classList.remove("hidden");
                    eyeClosed.classList.add("hidden");
                }
            }
        });
    });
}

function initTestingLabEvents() {
    const btnSim = document.getElementById("btn-simulate-leads");
    const btnReset = document.getElementById("btn-reset-test-leads");
    const totalLeadsEl = document.getElementById("testing-total-leads");
    const qualifiedLeadsEl = document.getElementById("testing-qualified-leads");
    const logFeed = document.getElementById("testing-leads-log-feed");

    let currentLeads = 1482;
    let currentQualified = 386;

    if (btnSim) {
        btnSim.addEventListener("click", () => {
            currentLeads += 25;
            currentQualified += 7;
            if (totalLeadsEl) totalLeadsEl.textContent = currentLeads.toLocaleString();
            if (qualifiedLeadsEl) qualifiedLeadsEl.textContent = currentQualified.toLocaleString();

            const timeStr = new Date().toTimeString().slice(0, 8);
            if (logFeed) {
                const newLog = document.createElement("div");
                newLog.style.color = "#38bdf8";
                newLog.textContent = `[${timeStr}] ⚡ Generated 25 test leads! Ingestion pipeline active (Total: ${currentLeads})`;
                logFeed.insertBefore(newLog, logFeed.firstChild);
            }

            if (superAdminCharts && superAdminCharts.testingLeadsTrend) {
                const dataArr = superAdminCharts.testingLeadsTrend.data.datasets[1].data;
                const lastIdx = dataArr.length - 1;
                dataArr[lastIdx] = (dataArr[lastIdx] || 0) + 25;
                const cumArr = superAdminCharts.testingLeadsTrend.data.datasets[0].data;
                cumArr[cumArr.length - 1] = currentLeads;
                superAdminCharts.testingLeadsTrend.update();
            }

            showToast("⚡ 25 Test Leads Generated & Graphs Updated!", "success");
        });
    }

    if (btnReset) {
        btnReset.addEventListener("click", () => {
            currentLeads = 1482;
            currentQualified = 386;
            if (totalLeadsEl) totalLeadsEl.textContent = "1,482";
            if (qualifiedLeadsEl) qualifiedLeadsEl.textContent = "386";
            if (logFeed) {
                logFeed.innerHTML = `
                    <div style="color: #10b981;">[12:40:15] ⚡ Lead Generation Test Suite initialized in Admin Console</div>
                    <div style="color: #38bdf8;">[12:40:18] 🎯 Scraped & Verified 15 Meta / Facebook Ads leads from active sessions</div>
                    <div style="color: #a78bfa;">[12:40:22] 💎 High-intent tag applied to 8 qualified creators</div>
                    <div style="color: #f59e0b;">[12:40:25] 📊 Real-time Chart.js telemetry synchronized with Cloud Backend</div>
                `;
            }
            if (superAdminCharts && superAdminCharts.testingLeadsTrend) {
                superAdminCharts.testingLeadsTrend.data.datasets[1].data = [45, 82, 120, 195, 240, 310, 280, 190, 140, 95];
                superAdminCharts.testingLeadsTrend.data.datasets[0].data = [45, 127, 247, 442, 682, 992, 1272, 1462, 1602, 1697];
                superAdminCharts.testingLeadsTrend.update();
            }
            showToast("🔄 Test Leads Telemetry Reset", "info");
        });
    }
}

function initModals() {
    // Session Modal & Cookie File Upload
    const modalSession = document.getElementById("modal-add-session");
    const cookieFileInput = document.getElementById("modal-session-cookie-file");
    const btnBrowseCookie = document.getElementById("btn-browse-cookie-file");
    const cookieNamePreview = document.getElementById("cookie-file-name-preview");
    const sessionNameInput = document.getElementById("modal-session-name");
    const sessionCookieText = document.getElementById("modal-session-cookie");

    if (btnBrowseCookie && cookieFileInput) {
        btnBrowseCookie.addEventListener("click", () => cookieFileInput.click());
        cookieFileInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (!file) return;

            if (cookieNamePreview) cookieNamePreview.textContent = `📄 ${file.name} (${Math.round(file.size / 1024) || 1} KB)`;
            if (!sessionNameInput.value.trim()) {
                const baseName = file.name.replace(/\.[^/.]+$/, "");
                sessionNameInput.value = baseName;
            }

            const reader = new FileReader();
            reader.onload = (event) => {
                sessionCookieText.value = event.target.result;
                showToast(`Cookie file loaded: ${file.name}`, "info");
            };
            reader.readAsText(file);
        });
    }

    // Bulk Cookie Import
    const btnBulkImport = document.getElementById("btn-import-cookie-files");
    const bulkFileInput = document.getElementById("bulk-cookie-file-input");

    if (btnBulkImport && bulkFileInput) {
        btnBulkImport.addEventListener("click", () => bulkFileInput.click());
        bulkFileInput.addEventListener("change", async (e) => {
            const files = Array.from(e.target.files);
            if (files.length === 0) return;

            showToast(`Processing ${files.length} cookie file(s)...`, "info");
            let sessionsToImport = [];

            for (const file of files) {
                try {
                    const text = await file.text();
                    const baseName = file.name.replace(/\.[^/.]+$/, "");
                    sessionsToImport.push({
                        name: baseName,
                        cookie_data: text.trim()
                    });
                } catch (err) {
                    console.error(`Error reading ${file.name}:`, err);
                }
            }

            if (sessionsToImport.length > 0) {
                const res = await apiRequest("/sessions/bulk-import", "POST", { sessions: sessionsToImport });
                if (res.success) {
                    showToast(`Successfully imported ${res.count || sessionsToImport.length} session profile(s)!`, "success");
                    fetchSessions();
                } else {
                    showAlert("Bulk Import Error", res.error || "Failed to import sessions", "❌");
                }
            }
            bulkFileInput.value = "";
        });
    }

    document.getElementById("btn-open-add-session").addEventListener("click", () => {
        modalSession.classList.remove("hidden");
        sessionNameInput.value = "";
        sessionCookieText.value = "";
        if (cookieFileInput) cookieFileInput.value = "";
        if (cookieNamePreview) cookieNamePreview.textContent = "No file selected";
    });

    document.getElementById("btn-close-session-modal").addEventListener("click", () => modalSession.classList.add("hidden"));
    
    document.getElementById("btn-save-session").addEventListener("click", async () => {
        const name = sessionNameInput.value.trim();
        const cookie = sessionCookieText.value.trim();
        if (!name) return showAlert("Input Required", "Please enter a session profile name!", "⚠️");

        const res = await apiRequest("/sessions/add", "POST", { name, cookie_data: cookie });
        if (res.success) {
            modalSession.classList.add("hidden");
            sessionNameInput.value = "";
            sessionCookieText.value = "";
            if (cookieFileInput) cookieFileInput.value = "";
            if (cookieNamePreview) cookieNamePreview.textContent = "No file selected";
            showToast("Session profile added successfully", "success");
            fetchSessions();
        } else {
            showAlert("Session Error", `Error adding session: ${res.error}`, "❌");
        }
    });

    // ── PROMPT MODAL & BATCH IMPORT HANDLERS ──
    const modalPrompt = document.getElementById("modal-add-prompt");
    let pendingImportFile = null;

    function switchPromptModalTab(tabName) {
        const tabBtns = document.querySelectorAll("#prompt-modal-tabs .auth-tab-btn");
        const panels = document.querySelectorAll(".prompt-tab-panel");
        
        tabBtns.forEach(btn => {
            if (btn.dataset.ptab === tabName) btn.classList.add("active");
            else btn.classList.remove("active");
        });

        panels.forEach(p => {
            if (p.id === `ptab-panel-${tabName}`) {
                p.classList.add("active");
                p.style.display = "flex";
            } else {
                p.classList.remove("active");
                p.style.display = "none";
            }
        });
    }

    const promptTabContainer = document.getElementById("prompt-modal-tabs");
    if (promptTabContainer) {
        promptTabContainer.addEventListener("click", (e) => {
            const btn = e.target.closest(".auth-tab-btn");
            if (btn && btn.dataset.ptab) {
                switchPromptModalTab(btn.dataset.ptab);
            }
        });
    }

    const btnOpenAddPrompt = document.getElementById("btn-open-add-prompt");
    if (btnOpenAddPrompt && modalPrompt) {
        btnOpenAddPrompt.addEventListener("click", () => {
            switchPromptModalTab("paste");
            modalPrompt.classList.remove("hidden");
        });
    }

    const btnImportPromptsHeader = document.getElementById("btn-import-prompts-file");
    if (btnImportPromptsHeader && modalPrompt) {
        btnImportPromptsHeader.addEventListener("click", () => {
            switchPromptModalTab("file");
            modalPrompt.classList.remove("hidden");
        });
    }

    document.querySelectorAll(".btn-close-prompt-modal").forEach(btn => {
        btn.addEventListener("click", () => modalPrompt.classList.add("hidden"));
    });

    // 1. Quick Paste Live Counter & Submit
    const txtBulkPrompts = document.getElementById("modal-bulk-prompts-text");
    const badgeBulkCount = document.getElementById("paste-prompt-count-badge");
    const btnSaveBulk = document.getElementById("btn-save-bulk-prompts");

    if (txtBulkPrompts) {
        txtBulkPrompts.addEventListener("input", () => {
            const lines = txtBulkPrompts.value.split("\n").map(l => l.trim()).filter(Boolean);
            if (badgeBulkCount) badgeBulkCount.textContent = `${lines.length} prompt(s) detected`;
            if (btnSaveBulk) {
                btnSaveBulk.textContent = lines.length > 0 ? `⚡ Add ${lines.length} Prompts to Queue` : "⚡ Add to Queue";
            }
        });
    }

    if (btnSaveBulk) {
        btnSaveBulk.addEventListener("click", async () => {
            const rawText = txtBulkPrompts.value.trim();
            const category = document.getElementById("modal-bulk-prompt-category").value.trim() || "General";
            const lines = rawText.split("\n").map(l => l.trim()).filter(Boolean);

            if (lines.length === 0) {
                return showAlert("Input Required", "Please paste at least one prompt (one per line)!", "⚠️");
            }

            btnSaveBulk.disabled = true;
            btnSaveBulk.textContent = "Adding...";
            const res = await apiRequest("/prompts/bulk-add", "POST", { prompts: lines, category });
            btnSaveBulk.disabled = false;
            btnSaveBulk.textContent = "⚡ Add to Queue";

            if (res.success) {
                modalPrompt.classList.add("hidden");
                txtBulkPrompts.value = "";
                if (badgeBulkCount) badgeBulkCount.textContent = "0 prompts detected";
                showToast(res.message || `Successfully added ${res.added_count || lines.length} prompts to queue!`, "success");
                await fetchPrompts();
                await fetchStats();
            } else {
                showAlert("Batch Error", res.error || "Could not add prompts in batch", "❌");
            }
        });
    }

    // 2. File Upload (Excel / CSV / TXT)
    const fileDropzone = document.getElementById("prompt-file-dropzone");
    const fileInput = document.getElementById("modal-input-file");
    const filePreview = document.getElementById("file-upload-preview");
    const fileNameEl = document.getElementById("file-upload-name");
    const fileCountEl = document.getElementById("file-upload-count");
    const btnSaveFile = document.getElementById("btn-save-file-prompts");

    function handleSelectedFile(file) {
        if (!file) return;
        pendingImportFile = file;
        if (filePreview && fileNameEl) {
            fileNameEl.textContent = file.name;
            if (fileCountEl) fileCountEl.textContent = `${(file.size / 1024).toFixed(1)} KB file ready to import`;
            filePreview.style.display = "block";
        }
        if (btnSaveFile) {
            btnSaveFile.disabled = false;
            btnSaveFile.textContent = `📥 Import "${file.name}"`;
        }
    }

    if (fileDropzone && fileInput) {
        fileDropzone.addEventListener("click", () => fileInput.click());
        fileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleSelectedFile(e.target.files[0]);
            }
        });

        fileDropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            fileDropzone.style.borderColor = "var(--accent)";
            fileDropzone.style.background = "rgba(6, 182, 212, 0.12)";
        });

        fileDropzone.addEventListener("dragleave", () => {
            fileDropzone.style.borderColor = "rgba(6, 182, 212, 0.4)";
            fileDropzone.style.background = "rgba(6, 182, 212, 0.04)";
        });

        fileDropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            fileDropzone.style.borderColor = "rgba(6, 182, 212, 0.4)";
            fileDropzone.style.background = "rgba(6, 182, 212, 0.04)";
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleSelectedFile(e.dataTransfer.files[0]);
            }
        });
    }

    if (btnSaveFile) {
        btnSaveFile.addEventListener("click", async () => {
            if (!pendingImportFile) {
                return showAlert("File Required", "Please select or drop an Excel (.xlsx/.xls), CSV, or TXT file first!", "⚠️");
            }
            const category = document.getElementById("modal-file-prompt-category").value.trim() || "General";
            btnSaveFile.disabled = true;
            btnSaveFile.textContent = "Importing...";

            const reader = new FileReader();
            reader.onload = async (event) => {
                const base64Data = event.target.result.split(",")[1];
                const res = await apiRequest("/prompts/import-file", "POST", {
                    file_name: pendingImportFile.name,
                    file_data: base64Data,
                    category
                });
                btnSaveFile.disabled = false;
                btnSaveFile.textContent = "📥 Import from File";

                if (res.success) {
                    modalPrompt.classList.add("hidden");
                    pendingImportFile = null;
                    if (fileInput) fileInput.value = "";
                    if (filePreview) filePreview.style.display = "none";
                    showToast(res.message || `Imported ${res.added_count} prompt(s) successfully!`, "success");
                    await fetchPrompts();
                    await fetchStats();
                } else {
                    showAlert("Import Error", res.error || "Failed to parse and import prompts file", "❌");
                }
            };
            reader.readAsDataURL(pendingImportFile);
        });
    }

    // 3. Single Prompt Add
    const btnSaveSingle = document.getElementById("btn-save-prompt");
    if (btnSaveSingle) {
        btnSaveSingle.addEventListener("click", async () => {
            const text = document.getElementById("modal-prompt-text").value.trim();
            const category = document.getElementById("modal-prompt-category").value.trim() || "General";
            if (!text) return showAlert("Input Required", "Please enter prompt description!", "⚠️");

            const res = await apiRequest("/prompts/add", "POST", { text, category });
            if (res.success) {
                modalPrompt.classList.add("hidden");
                document.getElementById("modal-prompt-text").value = "";
                showToast("Prompt added to queue", "success");
                await fetchPrompts();
                await fetchStats();
            } else {
                showAlert("Prompt Error", `Error saving prompt: ${res.error}`, "❌");
            }
        });
    }

    // Diagnostic Logs Console Modal
    const modalLogs = document.getElementById("modal-logs-console");
    const btnOpenLogs = document.getElementById("btn-open-logs-modal");
    const miniLogs = document.getElementById("mini-logs-console");
    const btnCloseLogs = document.getElementById("btn-close-logs-modal");
    const btnCloseLogsFooter = document.getElementById("btn-close-logs-modal-footer");
    const btnClearLogsModal = document.getElementById("btn-clear-logs-modal");
    const btnCopyLogsModal = document.getElementById("btn-copy-logs-modal");

    if (modalLogs) {
        document.querySelectorAll(".btn-expand-logs").forEach(btn => {
            btn.addEventListener("click", () => {
                modalLogs.classList.remove("hidden");
                fetchLogs();
            });
        });
        if (btnOpenLogs) {
            btnOpenLogs.addEventListener("click", () => {
                modalLogs.classList.remove("hidden");
                fetchLogs();
            });
        }

        document.querySelectorAll(".clickable-logs").forEach(box => {
            box.addEventListener("click", () => {
                modalLogs.classList.remove("hidden");
                fetchLogs();
            });
        });
    }

    if (btnCloseLogs && modalLogs) {
        btnCloseLogs.addEventListener("click", () => modalLogs.classList.add("hidden"));
    }

    if (btnCloseLogsFooter && modalLogs) {
        btnCloseLogsFooter.addEventListener("click", () => modalLogs.classList.add("hidden"));
    }

    if (btnClearLogsModal) {
        btnClearLogsModal.addEventListener("click", () => {
            const fullConsole = document.getElementById("full-logs-console");
            if (fullConsole) fullConsole.innerHTML = `<div class="log-line info">Console cleared.</div>`;
            document.querySelectorAll(".mini-logs-box").forEach(box => {
                box.innerHTML = `<div class="log-line info">Console cleared.</div>`;
            });
            showToast("Logs console cleared", "info");
        });
    }

    if (btnCopyLogsModal) {
        btnCopyLogsModal.addEventListener("click", () => {
            const fullConsole = document.getElementById("full-logs-console");
            if (!fullConsole) return;
            const textToCopy = fullConsole.innerText || "";
            navigator.clipboard.writeText(textToCopy).then(() => {
                const origHtml = btnCopyLogsModal.innerHTML;
                btnCopyLogsModal.innerHTML = `<span>✅</span> Copied!`;
                setTimeout(() => {
                    btnCopyLogsModal.innerHTML = origHtml;
                }, 2000);
            });
            showToast("Copied diagnostic logs to clipboard", "success");
        });
    }

    // In-App HD Video Player Modal Handlers
    const btnCloseVideoModal = document.getElementById("btn-close-video-modal");
    const btnCloseVideoFooter = document.getElementById("btn-video-close-footer");
    const btnVideoOpenFolder = document.getElementById("btn-video-open-folder");

    if (btnCloseVideoModal) {
        btnCloseVideoModal.addEventListener("click", closeVideoModal);
    }
    if (btnCloseVideoFooter) {
        btnCloseVideoFooter.addEventListener("click", closeVideoModal);
    }
    if (btnVideoOpenFolder) {
        btnVideoOpenFolder.addEventListener("click", openDownloadsFolder);
    }

    // Universal Backdrop Click-to-Close for all Modals
    document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
        backdrop.addEventListener("click", (e) => {
            if (e.target === backdrop) {
                if (backdrop.id === "modal-video-player") {
                    closeVideoModal();
                } else {
                    backdrop.classList.add("hidden");
                }
            }
        });
    });

    // Universal Escape key listener to close active modals & popovers
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeVideoModal();
            document.querySelectorAll(".modal-backdrop").forEach(m => m.classList.add("hidden"));
            const popMenu = document.getElementById("user-popover-menu");
            if (popMenu) popMenu.classList.add("hidden");
        }
    });
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function initUserPopoverAndAuth() {
    const cardTrigger = document.getElementById("user-card-trigger");
    const popoverMenu = document.getElementById("user-popover-menu");
    const btnSwitch = document.getElementById("btn-popover-switch");
    const btnLogout = document.getElementById("btn-popover-logout");
    const modalAuth = document.getElementById("modal-auth");

    // Toggle Popover
    if (cardTrigger && popoverMenu) {
        cardTrigger.addEventListener("click", (e) => {
            if (e.target.closest(".user-popover-menu")) return;
            popoverMenu.classList.toggle("hidden");
            cardTrigger.classList.toggle("active-menu");
        });

        // Close on outside click
        document.addEventListener("click", (e) => {
            if (!cardTrigger.contains(e.target)) {
                popoverMenu.classList.add("hidden");
                cardTrigger.classList.remove("active-menu");
            }
        });
    }

    // Check for Updates Action
    const btnCheckUpdate = document.getElementById("btn-popover-check-update");
    if (btnCheckUpdate) {
        btnCheckUpdate.addEventListener("click", () => {
            if (popoverMenu) popoverMenu.classList.add("hidden");
            checkForUpdate(true);
        });
    }

    // Switch Account Action
    if (btnSwitch) {
        btnSwitch.addEventListener("click", () => {
            if (popoverMenu) popoverMenu.classList.add("hidden");
            if (modalAuth) {
                switchAuthTab("signin");
                modalAuth.classList.remove("hidden");
            }
        });
    }

    // Logout Action
    if (btnLogout) {
        btnLogout.addEventListener("click", async () => {
            const ok = await showConfirm("Sign Out Confirmation", "Are you sure you want to log out of your creator account?", { isDanger: true, confirmText: "Log Out", icon: "🚪" });
            if (!ok) return;

            if (popoverMenu) popoverMenu.classList.add("hidden");
            const res = await apiRequest("/auth/logout", "POST");
            if (res.success) {
                document.getElementById("user-display-name").textContent = "Logged Out";
                document.getElementById("user-avatar-text").textContent = "??";
                const badgeEl = document.getElementById("user-license-badge");
                if (badgeEl) {
                    badgeEl.textContent = "🔴 Signed Out";
                    badgeEl.className = "license-badge badge-red";
                }
                document.querySelectorAll(".admin-tab").forEach(el => el.classList.add("hidden"));
                showToast("Logged out successfully", "info");
                if (modalAuth) {
                    switchAuthTab("signin");
                    modalAuth.classList.remove("hidden");
                }
            }
        });
    }

    // Auth Modal Tabs (Sign In vs Sign Up)
    const authTabBtns = document.querySelectorAll(".auth-tab-btn");
    authTabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.authtab;
            switchAuthTab(target);
        });
    });

    // Close Auth Modal
    const btnCloseAuth = document.getElementById("btn-close-auth-modal");
    const btnCloseAuthSignup = document.getElementById("btn-close-auth-signup-modal");
    if (btnCloseAuth) btnCloseAuth.addEventListener("click", () => modalAuth.classList.add("hidden"));
    if (btnCloseAuthSignup) btnCloseAuthSignup.addEventListener("click", () => modalAuth.classList.add("hidden"));

    // Submit Sign In
    const btnSubmitSignin = document.getElementById("btn-submit-signin");
    if (btnSubmitSignin) {
        btnSubmitSignin.addEventListener("click", async () => {
            const email = document.getElementById("auth-signin-email").value.trim();
            const password = document.getElementById("auth-signin-password").value.trim();
            if (!email || !password) return showAlert("Input Required", "Please enter both email and password!", "⚠️");

            btnSubmitSignin.disabled = true;
            btnSubmitSignin.textContent = "⏳ Signing In...";

            const res = await apiRequest("/auth/login", "POST", { email, password });
            btnSubmitSignin.disabled = false;
            btnSubmitSignin.textContent = "🚀 Sign In";

            if (res.success) {
                showToast(`Welcome back, ${res.user ? (res.user.full_name || email) : email}!`, "success");
                modalAuth.classList.add("hidden");
                fetchStats();
            } else {
                showAlert("Sign In Failed", res.error || "Authentication failed.", "❌");
            }
        });
    }

    // Submit Sign Up
    const btnSubmitSignup = document.getElementById("btn-submit-signup");
    if (btnSubmitSignup) {
        btnSubmitSignup.addEventListener("click", async () => {
            const name = document.getElementById("auth-signup-name").value.trim();
            const email = document.getElementById("auth-signup-email").value.trim();
            const password = document.getElementById("auth-signup-password").value.trim();
            const whatsapp = document.getElementById("auth-signup-whatsapp").value.trim();

            if (!email || !password) return showAlert("Input Required", "Please enter both email and password!", "⚠️");

            btnSubmitSignup.disabled = true;
            btnSubmitSignup.textContent = "⏳ Registering...";

            const res = await apiRequest("/auth/signup", "POST", {
                email,
                password,
                full_name: name,
                whatsapp_number: whatsapp
            });

            btnSubmitSignup.disabled = false;
            btnSubmitSignup.textContent = "🎉 Create Account";

            if (res.success) {
                showAlert("Account Created", res.message || "Registration successful. Please wait for admin approval.", "🎉");
                modalAuth.classList.add("hidden");
                fetchStats();
            } else {
                showAlert("Registration Failed", res.error || "Could not register account.", "❌");
            }
        });
    }
}

function switchAuthTab(tabName) {
    document.querySelectorAll(".auth-tab-btn").forEach(b => {
        if (b.dataset.authtab === tabName) b.classList.add("active");
        else b.classList.remove("active");
    });
    document.querySelectorAll(".auth-panel").forEach(p => p.classList.remove("active"));
    const targetPanel = document.getElementById(`auth-panel-${tabName}`);
    if (targetPanel) targetPanel.classList.add("active");
}
