// Blocked page script for FocusGuard
const SERVER_URL = 'http://127.0.0.1:58392';
const SAVED_LINKS_PAGE_URL = 'http://127.0.0.1:58393/admin/saved-links';

// Parse URL parameters
const urlParams = new URLSearchParams(window.location.search);
const blockedUrl = urlParams.get('url') || '';
const blockedDomain = urlParams.get('domain') || extractDomain(blockedUrl) || 'Unknown';
const blockReason = urlParams.get('reason') || 'This site is considered a distraction.';

// Update page content
document.getElementById('blockedDomain').textContent = blockedDomain;
document.getElementById('blockReason').textContent = blockReason;

function openSavedLinksPage(event) {
    if (event) {
        event.preventDefault();
    }
    try {
        if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.create) {
            chrome.tabs.create({ url: SAVED_LINKS_PAGE_URL });
            return;
        }
    } catch (err) {
        console.log('Could not open saved links via extension tab API:', err);
    }
    window.open(SAVED_LINKS_PAGE_URL, '_blank', 'noopener');
}

// Fetch and display personalized context
async function loadPersonalizedContext() {
    try {
        const response = await fetch(`${SERVER_URL}/api/popup_context?domain=${encodeURIComponent(blockedDomain)}`);
        if (!response.ok) return;
        const ctx = await response.json();

        // --- Greeting banner ---
        if (ctx.greeting) {
            const banner = document.getElementById('personalBanner');
            document.getElementById('greeting').textContent = ctx.greeting;
            banner.style.display = 'block';
        }

        // --- Focus stats row ---
        const showAny = ctx.show_streak || ctx.show_focus_score;
        if (showAny) {
            const row = document.getElementById('focusStatsRow');
            row.style.display = 'flex';

            // Streak
            if (ctx.show_streak) {
                document.getElementById('streakValue').textContent = ctx.streak_days || 0;
            } else {
                document.getElementById('streakStat').style.display = 'none';
            }

            // Focus score ring
            if (ctx.show_focus_score) {
                const score = ctx.focus_score || 0;
                document.getElementById('scoreText').textContent = score;
                document.getElementById('scoreArc').setAttribute('stroke-dasharray', `${score}, 100`);
                // Color the arc based on score
                const arc = document.getElementById('scoreArc');
                if (score >= 70) arc.style.stroke = '#4caf50';
                else if (score >= 40) arc.style.stroke = '#ffc107';
                else arc.style.stroke = '#e94560';

                document.getElementById('blocksValue').textContent = ctx.blocks_today || 0;
            } else {
                document.getElementById('scoreStat').style.display = 'none';
                document.getElementById('blocksStat').style.display = 'none';
            }
        }

        // --- Motivational quote ---
        if (ctx.show_motivational_message && ctx.motivational_message) {
            const quoteEl = document.getElementById('motivationalQuote');
            document.getElementById('quoteText').textContent = ctx.motivational_message;
            quoteEl.style.display = 'block';
        }
    } catch (err) {
        console.log('Could not load personalized context:', err);
    }
}

// Load personalized context when page loads
document.addEventListener('DOMContentLoaded', loadPersonalizedContext);

// Fetch and display usage stats
async function loadUsageStats() {
    try {
        // Get master distraction budget first
        const masterResponse = await fetch(`${SERVER_URL}/api/distraction/budget`);
        const masterData = await masterResponse.json();
        updateMasterBudgetDisplay(masterData);
        
        // Get domain usage stats
        const usageResponse = await fetch(`${SERVER_URL}/api/domain/usage?domain=${encodeURIComponent(blockedDomain)}`);
        const usageData = await usageResponse.json();
        
        // Get domain rule
        const ruleResponse = await fetch(`${SERVER_URL}/api/domain/rules?domain=${encodeURIComponent(blockedDomain)}`);
        const ruleData = await ruleResponse.json();
        
        // Get override eligibility
        const checkResponse = await fetch(`${SERVER_URL}/api/override?domain=${encodeURIComponent(blockedDomain)}`);
        const checkData = await checkResponse.json();
        
        updateStatsDisplay(usageData, ruleData, checkData, masterData);
    } catch (err) {
        console.log('Could not load usage stats:', err);
        document.getElementById('statsPanel').style.display = 'none';
        document.getElementById('masterBudgetPanel').style.display = 'none';
    }
}

// Update master distraction budget display
function updateMasterBudgetDisplay(data) {
    const remainingEl = document.getElementById('masterRemaining');
    const usedEl = document.getElementById('masterUsed');
    const limitEl = document.getElementById('masterLimit');
    const sitesEl = document.getElementById('masterSites');
    const progressBar = document.getElementById('masterProgressBar');
    const progressLabel = document.getElementById('masterProgressLabel');
    const sitesContainer = document.getElementById('sitesListContainer');
    const sitesList = document.getElementById('sitesList');
    
    // Update values
    remainingEl.textContent = data.remaining_formatted || '--';
    usedEl.textContent = data.total_used_formatted || '--';
    limitEl.textContent = data.total_limit_formatted || '--';
    sitesEl.textContent = data.sites_count || '0';
    
    // Color code remaining time
    const percent = data.usage_percent || 0;
    if (data.budget_exhausted) {
        remainingEl.classList.add('danger');
        remainingEl.textContent = 'EXHAUSTED';
    } else if (percent >= 70) {
        remainingEl.classList.add('warning');
    } else {
        remainingEl.classList.add('success');
    }
    
    // Update progress bar
    progressBar.style.width = `${Math.min(100, percent)}%`;
    if (percent >= 90) {
        progressBar.style.background = '#e94560';
    } else if (percent >= 70) {
        progressBar.style.background = 'linear-gradient(90deg, #ffc107, #e94560)';
    } else {
        progressBar.style.background = 'linear-gradient(90deg, #4caf50, #667eea)';
    }
    progressLabel.textContent = `${Math.round(percent)}% of daily limit used`;
    
    // Build sites list
    const sites = data.sites_visited || [];
    if (sites.length > 0) {
        sitesContainer.style.display = 'block';
        let html = '';
        sites.forEach(site => {
            html += `
                <div style="display: flex; justify-content: space-between; padding: 6px 8px; background: rgba(255,255,255,0.03); border-radius: 4px; margin-bottom: 4px; font-size: 0.85rem;">
                    <span style="color: #ccc;">${site.domain}</span>
                    <span style="color: #667eea; font-weight: 600;">${site.active_time_formatted}</span>
                </div>
            `;
        });
        sitesList.innerHTML = html;
    }
    
    // If budget exhausted, disable override button
    if (data.budget_exhausted) {
        const overrideBtn = document.getElementById('overrideBtn');
        if (overrideBtn) {
            overrideBtn.disabled = true;
            overrideBtn.textContent = 'Daily distraction limit exhausted';
            overrideBtn.style.opacity = '0.5';
            overrideBtn.style.cursor = 'not-allowed';
        }
    }
}

// Toggle sites list visibility
let sitesListExpanded = true;
function toggleSitesList() {
    const sitesList = document.getElementById('sitesList');
    const header = document.querySelector('.sites-header');
    sitesListExpanded = !sitesListExpanded;
    sitesList.style.display = sitesListExpanded ? 'block' : 'none';
    header.textContent = sitesListExpanded ? '▼ Distraction sites visited today' : '▶ Distraction sites visited today';
}

function formatDuration(seconds) {
    if (seconds === undefined || seconds === null || isNaN(seconds)) return '--';
    seconds = Math.round(seconds);
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
    }
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
}

function updateStatsDisplay(usage, rule, check, masterData) {
    const remainingEl = document.getElementById('statRemainingTime');
    const effectiveEl = document.getElementById('statEffectiveTime');
    const overridesEl = document.getElementById('statOverrides');
    const budgetEl = document.getElementById('statBudget');
    const detailEl = document.getElementById('statsDetail');
    
    // Calculate values
    const budget = rule.max_cumulative_time_seconds || 900;
    const effectiveUsed = usage.effective_time_used || 0;
    const actualUsed = usage.total_active_seconds || 0;
    const overrideCount = usage.override_count || 0;
    const baselineOverrides = rule.max_overrides_per_day || 3;
    const remaining = Math.max(0, budget - effectiveUsed);
    const usagePercent = (effectiveUsed / budget) * 100;
    
    // Update remaining time with color coding
    remainingEl.textContent = formatDuration(remaining);
    if (remaining <= 0) {
        remainingEl.classList.add('danger');
    } else if (usagePercent >= 70) {
        remainingEl.classList.add('warning');
    } else {
        remainingEl.classList.add('success');
    }
    
    // Update effective time
    effectiveEl.textContent = formatDuration(effectiveUsed);
    if (usagePercent >= 90) {
        effectiveEl.classList.add('danger');
    } else if (usagePercent >= 70) {
        effectiveEl.classList.add('warning');
    }
    
    // Update overrides count
    overridesEl.textContent = `${overrideCount}/${baselineOverrides}`;
    if (overrideCount > baselineOverrides) {
        overridesEl.classList.add('warning');
    }
    
    // Update budget
    budgetEl.textContent = formatDuration(budget);
    
    // Build detail text
    let details = [];
    
    // Show actual vs effective if there's a penalty
    const penalty = effectiveUsed - actualUsed;
    if (penalty > 0) {
        details.push(`<div class="penalty-info">⚠️ Fragmentation penalty: +${formatDuration(penalty)} (${overrideCount - baselineOverrides} extra visits × 1min)</div>`);
    }
    
    // Show rule info
    details.push(`<div>Max per override: ${formatDuration(rule.max_override_duration_seconds || 300)}</div>`);
    
    if (remaining <= 0) {
        details.push(`<div style="color: #e94560; margin-top: 8px;"><strong>Daily budget exhausted. Try again tomorrow.</strong></div>`);
        // Disable override button
        const overrideBtn = document.getElementById('overrideBtn');
        if (overrideBtn) {
            overrideBtn.disabled = true;
            overrideBtn.textContent = 'No time remaining today';
            overrideBtn.style.opacity = '0.5';
            overrideBtn.style.cursor = 'not-allowed';
        }
    }
    
    if (details.length > 0) {
        detailEl.innerHTML = details.join('');
        detailEl.classList.remove('hidden');
    }
}

// Load stats when page loads
document.addEventListener('DOMContentLoaded', loadUsageStats);

// Play beep sound on load
function playBeep() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.frequency.value = 440; // Hz (A4 note)
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.3);

        // Second beep
        setTimeout(() => {
            const osc2 = audioContext.createOscillator();
            const gain2 = audioContext.createGain();
            osc2.connect(gain2);
            gain2.connect(audioContext.destination);
            osc2.frequency.value = 523; // Hz (C5 note)
            osc2.type = 'sine';
            gain2.gain.setValueAtTime(0.3, audioContext.currentTime);
            gain2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
            osc2.start(audioContext.currentTime);
            osc2.stop(audioContext.currentTime + 0.3);
        }, 150);
    } catch (e) {
        console.log('Could not play beep sound:', e);
    }
}

// Play beep when page loads
document.addEventListener('DOMContentLoaded', playBeep);

function extractDomain(url) {
    try {
        return new URL(url).hostname;
    } catch {
        return null;
    }
}

function goBack() {
    // Try to go back in history, but skip blocked pages
    if (window.history.length > 2) {
        window.history.go(-2); // Go back 2 steps to skip the blocked URL
    } else {
        // Open a new tab or go to a safe page
        window.location.href = 'https://www.google.com';
    }
}

function showOverrideModal() {
    document.getElementById('overrideModal').classList.add('visible');
    document.getElementById('warningText').classList.add('visible');
}

function hideOverrideModal() {
    document.getElementById('overrideModal').classList.remove('visible');
}

async function confirmOverride() {
    const proceedBtn = document.getElementById('proceedBtn');
    proceedBtn.textContent = 'Requesting...';
    proceedBtn.disabled = true;

    try {
        // Request override from server
        const response = await fetch(`${SERVER_URL}/api/override`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                domain: blockedDomain,
                url: blockedUrl,
                block_reason: blockReason,
                browser: navigator.userAgent.includes('Edg') ? 'edge' : 'chrome',
                request_reason: 'User requested override'
            })
        });

        const result = await response.json();

        if (result.granted) {
            // Override granted - notify extension and navigate
            const override = result.override;
            const sessionDuration = result.session_duration_seconds || override.duration_seconds || 300;
            const sessionMin = Math.ceil(sessionDuration / 60);
            
            // Send message to extension about the override with session duration
            // Compute expiry_time in epoch seconds for the background script's expiry tracker
            const expiryTime = (Date.now() / 1000) + sessionDuration;
            if (typeof chrome !== 'undefined' && chrome.runtime) {
                chrome.runtime.sendMessage({
                    action: 'override_granted',
                    domain: blockedDomain,
                    session_duration_seconds: sessionDuration,
                    expiry_time: expiryTime,
                    override_id: override.id
                });
            }
            
            // Show brief success message then navigate
            proceedBtn.textContent = `Access granted for ${sessionMin} min`;
            setTimeout(() => {
                window.location.href = blockedUrl;
            }, 500);
        } else {
            // Override denied
            proceedBtn.textContent = 'Denied';
            alert(result.message || 'Override request denied.');
            setTimeout(() => {
                proceedBtn.textContent = 'Proceed Anyway';
                proceedBtn.disabled = false;
            }, 2000);
        }
    } catch (err) {
        console.error('Failed to request override:', err);
        proceedBtn.textContent = 'Error - Try Again';
        proceedBtn.disabled = false;
        alert('Could not connect to FocusGuard server. Make sure it is running.');
    }
}

// ---------------------------------------------------------------------------
// Saved Links Badge
// ---------------------------------------------------------------------------
async function loadSavedLinksCount() {
    try {
        const response = await fetch(`${SERVER_URL}/api/saved_links/stats`);
        if (!response.ok) return;
        const stats = await response.json();
        const unviewed = stats.unviewed || 0;
        if (unviewed > 0) {
            document.getElementById('savedLinksCount').textContent = unviewed;
            document.getElementById('savedLinksBadge').style.display = 'block';
        }
    } catch (err) {
        console.log('Could not load saved links count:', err);
    }
}

document.addEventListener('DOMContentLoaded', loadSavedLinksCount);

// ---------------------------------------------------------------------------
// Save for Later
// ---------------------------------------------------------------------------
function showSaveForm() {
    document.getElementById('saveForLaterForm').style.display = 'block';
    document.getElementById('saveForLaterBtn').style.display = 'none';
    document.getElementById('saveLinkComment').focus();
}

function hideSaveForm() {
    document.getElementById('saveForLaterForm').style.display = 'none';
    document.getElementById('saveForLaterBtn').style.display = '';
}

function showSaveFeedback(message, isError) {
    const el = document.getElementById('saveFeedback');
    el.textContent = message;
    el.style.display = 'block';
    el.style.background = isError ? 'rgba(233, 69, 96, 0.15)' : 'rgba(76, 175, 80, 0.15)';
    el.style.color = isError ? '#e94560' : '#4caf50';
    el.style.border = isError ? '1px solid rgba(233, 69, 96, 0.3)' : '1px solid rgba(76, 175, 80, 0.3)';
    setTimeout(() => { el.style.display = 'none'; }, 4000);
}

async function confirmSaveLink() {
    const comment = (document.getElementById('saveLinkComment').value || '').trim();
    const confirmBtn = document.getElementById('confirmSaveBtn');
    confirmBtn.textContent = 'Saving...';
    confirmBtn.disabled = true;

    try {
        const response = await fetch(`${SERVER_URL}/api/saved_links`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: blockedUrl,
                domain: blockedDomain,
                title: document.title || blockedDomain,
                category: blockReason,
                comment: comment,
            }),
        });

        if (response.ok) {
            hideSaveForm();
            showSaveFeedback('✅ Link saved! You can view it from the dashboard during your break.', false);
            // Disable the save button to prevent duplicates
            const saveBtn = document.getElementById('saveForLaterBtn');
            saveBtn.textContent = '✅ Saved';
            saveBtn.disabled = true;
            saveBtn.style.opacity = '0.6';
            saveBtn.style.cursor = 'default';
        } else {
            const err = await response.json().catch(() => ({}));
            showSaveFeedback('Failed to save: ' + (err.error || 'Unknown error'), true);
        }
    } catch (err) {
        console.error('Failed to save link:', err);
        showSaveFeedback('Could not connect to FocusGuard server.', true);
    } finally {
        confirmBtn.textContent = 'Save Link';
        confirmBtn.disabled = false;
    }
}

// Attach event listeners after DOM loads
document.addEventListener('DOMContentLoaded', () => {
    // Go Back button
    const goBackBtn = document.getElementById('goBackBtn');
    if (goBackBtn) {
        goBackBtn.addEventListener('click', goBack);
    }
    
    // Override button
    const overrideBtn = document.getElementById('overrideBtn');
    if (overrideBtn) {
        overrideBtn.addEventListener('click', showOverrideModal);
    }
    
    // Modal cancel button
    const cancelBtn = document.getElementById('cancelBtn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', hideOverrideModal);
    }
    
    // Modal proceed button
    const proceedBtn = document.getElementById('proceedBtn');
    if (proceedBtn) {
        proceedBtn.addEventListener('click', confirmOverride);
    }

    // Save for Later button
    const saveForLaterBtn = document.getElementById('saveForLaterBtn');
    if (saveForLaterBtn) {
        saveForLaterBtn.addEventListener('click', showSaveForm);
    }

    // Cancel save button
    const cancelSaveBtn = document.getElementById('cancelSaveBtn');
    if (cancelSaveBtn) {
        cancelSaveBtn.addEventListener('click', hideSaveForm);
    }

    // Confirm save button
    const confirmSaveBtn = document.getElementById('confirmSaveBtn');
    if (confirmSaveBtn) {
        confirmSaveBtn.addEventListener('click', confirmSaveLink);
    }

    const openSavedLinksLink = document.getElementById('openSavedLinksLink');
    if (openSavedLinksLink) {
        openSavedLinksLink.addEventListener('click', openSavedLinksPage);
    }
});
