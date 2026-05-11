// FocusGuard Background Script with Idle Detection & Retry Logic

const CONFIG = {
    useNativeMessaging: false,  // Disabled - using HTTP API only for store submission
    useHttpPost: true,
    serverUrl: "http://127.0.0.1:58392/api/tabs",
    statusUrl: "http://127.0.0.1:58392/api/status",
    commandUrl: "http://127.0.0.1:58392/api/command",
    blockCheckUrl: "http://127.0.0.1:58392/api/should_block",
    eventStreamUrl: "http://127.0.0.1:58392/api/events", // New endpoint for real-time events
    heartbeatIntervalMs: 30000, // Connection monitoring only (W-42)
    tabUpdateDebounceMs: 800, // Debounce event-driven tab snapshot sends
    tabSnapshotFallbackMs: 5 * 60 * 1000, // Fallback: full snapshot at least every 5 min (W-42)
    idleThresholdSec: 60, // idle if no input for 60s
    maxRetries: 3,
    retryDelayMs: 5000,
    debug: true,
    usePreemptiveBlocking: false, // Disabled - use real-time blocking with custom blocked page instead
    useRealTimeBlocking: true, // Enhanced real-time blocking with custom blocked.html page
    blockingTimeout: 500, // Max time to wait for blocking decision (ms)
    cacheBlockingDecisions: true, // Cache blocking decisions for performance
    batchEventUpdates: true, // Batch multiple tab events together
    failClosedWhenServerDown: true, // Block unknown domains when server is unreachable (8.9 defense)
    // Domains that are NEVER blocked even when server is down (productivity / essential)
    safeDomains: [
        'google.com', 'www.google.com', 'docs.google.com', 'drive.google.com',
        'mail.google.com', 'calendar.google.com', 'meet.google.com',
        'outlook.office.com', 'outlook.live.com', 'teams.microsoft.com',
        'github.com', 'stackoverflow.com', 'learn.microsoft.com',
        'wikipedia.org', 'en.wikipedia.org',
        'zoom.us', 'slack.com',
        'localhost', '127.0.0.1',
    ]
};

let focusGuardPort = null;
let isConnected = false;
let retryCount = 0;
let retryTimer = null;
let serverReachable = true; // Track server connectivity for fail-closed logic
let lastServerContact = Date.now(); // Timestamp of last successful server response
let consecutiveServerFailures = 0; // Count of consecutive server request failures

// Real-time blocking state
let blockingCache = new Map(); // Cache for blocking decisions
/** Last mode sample from syncBlockedDomainsToRules — invalidates stale block/allow cache on transition */
let lastSeenEnforcementModeKey = null;
/** Throttle DNR resync triggered from /api/should_block (Chrome vs Edge parity) */
let lastDnrResyncFromShouldBlockMs = 0;
let pendingBlocks = new Set(); // Track pending blocking decisions
let eventQueue = []; // Queue for batched events
let eventBatchTimer = null;
let lastEventTime = 0;

// Active override sessions - track when to auto-block
// Map of domain -> { tabIds: Set, startTime, checkInterval }
let activeOverrideSessions = new Map();

// Known URL shortener domains (8.7.1) — these can redirect to blocked sites
const URL_SHORTENER_DOMAINS = new Set([
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'is.gd',
    'buff.ly', 'adf.ly', 'bit.do', 'mcaf.ee', 'su.pr', 'db.tt',
    'qr.ae', 'cur.lv', 'ity.im', 'lnkd.in', 'youtu.be', 'rb.gy',
    'shorturl.at', 'tiny.cc', 'v.gd', 'x.co', 'soo.gd', 'clck.ru',
    'rebrand.ly', 'bl.ink', 'short.io', 'hyper.co',
]);

// Check if a URL is from a known shortener service
function isUrlShortener(domain) {
    if (!domain) return false;
    return URL_SHORTENER_DOMAINS.has(domain.toLowerCase());
}

// Check if a domain is in the safe-domains allowlist (never blocked even when server is down)
function isSafeDomain(domain) {
    if (!domain) return false;
    const lower = domain.toLowerCase();
    return CONFIG.safeDomains.some(safe => lower === safe || lower.endsWith('.' + safe));
}

// Update server reachability state after a request succeeds or fails
function markServerReachable() {
    serverReachable = true;
    lastServerContact = Date.now();
    consecutiveServerFailures = 0;
}

function markServerUnreachable() {
    consecutiveServerFailures++;
    // Consider server down after 2 consecutive failures
    if (consecutiveServerFailures >= 2) {
        if (serverReachable) {
            debugLog('WARNING: FocusGuard server is unreachable — fail-closed mode active');
        }
        serverReachable = false;
    }
}

function debugLog(...args) {
    if (CONFIG.debug) {
        console.log('[FocusGuard]', ...args);
    }
}

/** Invalidate URL blocking cache when enforcement mode changes (e.g. enforcing → advisory). */
function noteEnforcementModeFromServer(mode) {
    const key = mode === null || mode === undefined ? 'unknown' : String(mode);
    if (lastSeenEnforcementModeKey !== null && lastSeenEnforcementModeKey !== key) {
        blockingCache.clear();
        debugLog(`Cleared blocking decision cache (${lastSeenEnforcementModeKey} -> ${key})`);
    }
    lastSeenEnforcementModeKey = key;
}

/** Last instant DNR strip (avoids spamming updateSessionRules on rapid events) */
let lastImmediateDnrClearMs = 0;

/** Keep declarativeNetRequest aligned when server reports non-enforcing (covers missed sync_dnr / races). */
function scheduleDnrResyncFromShouldBlockResponse(data) {
    if (!data || typeof data.enforcement_mode !== 'string') {
        return;
    }
    noteEnforcementModeFromServer(data.enforcement_mode);
    if (data.enforcement_mode !== 'enforcing') {
        // DNR runs at network layer before tabs.onUpdated — must strip redirects immediately
        // when the server says advisory/tracking (async syncBlockedDomains alone can race).
        const t = Date.now();
        if (t - lastImmediateDnrClearMs > 400) {
            lastImmediateDnrClearMs = t;
            updateDynamicRules([]).catch((e) => debugLog('Immediate DNR clear (non-enforcing) failed:', e));
        }
        const now = Date.now();
        if (now - lastDnrResyncFromShouldBlockMs < 1500) {
            return;
        }
        lastDnrResyncFromShouldBlockMs = now;
        syncBlockedDomainsToRules().catch((e) =>
            debugLog('DNR resync after should_block (non-enforcing) failed:', e)
        );
    }
}

/** Origin of the tab server (e.g. http://127.0.0.1:58392) derived from CONFIG.serverUrl. */
function getTabServerOrigin() {
    try {
        return new URL(CONFIG.serverUrl).origin;
    } catch (e) {
        return 'http://127.0.0.1:58392';
    }
}

/**
 * Current enforcement mode from deployment config (tracking | advisory | enforcing).
 * Returns null if the tab server cannot be reached (caller should avoid assuming enforcing).
 */
async function fetchEnforcementMode() {
    let lastErr = null;
    for (let attempt = 0; attempt < 3; attempt++) {
        try {
            const r = await fetch(`${getTabServerOrigin()}/api/enforcement_mode`, {
                headers: { 'Cache-Control': 'no-cache' },
            });
            if (!r.ok) {
                debugLog(`fetchEnforcementMode: HTTP ${r.status} (attempt ${attempt + 1})`);
                lastErr = new Error(`HTTP ${r.status}`);
            } else {
                const j = await r.json();
                const m = j.enforcement_mode;
                return typeof m === 'string' ? m : null;
            }
        } catch (e) {
            lastErr = e;
            debugLog(`fetchEnforcementMode attempt ${attempt + 1} failed:`, e);
        }
        await new Promise((resolve) => setTimeout(resolve, 90 * (attempt + 1)));
    }
    debugLog('fetchEnforcementMode failed after retries:', lastErr);
    return null;
}

function updateIcon(connected) {
    const iconPath = connected
        ? { "16": "icons/icon16.png", "48": "icons/icon48.png" }
        : { "16": "icons/icon16_gray.png", "48": "icons/icon48_gray.png" };
    chrome.action.setIcon({ path: iconPath });
}

// Connect to native host (with retry)
function connectNativeHost() {
    if (focusGuardPort || retryTimer) return;

    try {
        debugLog("Attempting native host connection...");
        focusGuardPort = chrome.runtime.connectNative('com.focusguard.native');

        focusGuardPort.onDisconnect.addListener(() => {
            const err = chrome.runtime.lastError;
            debugLog('Native host disconnected:', err ? err.message : 'No error');
            focusGuardPort = null;

            if (retryCount < CONFIG.maxRetries) {
                retryCount++;
                debugLog(`Retrying connection in ${CONFIG.retryDelayMs}ms (attempt ${retryCount})`);
                retryTimer = setTimeout(() => {
                    retryTimer = null;
                    connectNativeHost();
                }, CONFIG.retryDelayMs);
            } else {
                debugLog("Max retries reached. Giving up for now.");
            }
        });

        focusGuardPort.onMessage.addListener((msg) => {
            debugLog('Message from native host:', msg);
        });

        retryCount = 0;
        debugLog("Connected to native host.");
    } catch (err) {
        debugLog("Error connecting to native host:", err);
        focusGuardPort = null;
    }
}

// Get tab info
function getAllTabs(callback) {
    chrome.tabs.query({}, function (tabs) {
        if (chrome.runtime.lastError) {
            debugLog('Error getting tabs:', chrome.runtime.lastError);
            callback([]);
            return;
        }

        const tabData = tabs.map(tab => ({
            id: tab.id,
            windowId: tab.windowId,
            url: tab.url,
            title: tab.title,
            active: tab.active,
            pinned: tab.pinned,
            lastAccessed: tab.lastAccessed,
            incognito: tab.incognito
        }));

        callback(tabData);
    });
}

// Send tab data to native host or server
function sendTabData() {
    getAllTabs(function(tabs) {
        const browserInfo = {
            name: navigator.userAgent.includes('Edg') ? 'Microsoft Edge' : 'Google Chrome',
            version: navigator.userAgent,
            platform: navigator.platform
        };
        const payload = {
            browser: browserInfo,
            tabs: tabs,
            timestamp: Date.now()
        };
        let sent = false;
        // Send to native host using persistent port
        if (CONFIG.useNativeMessaging) {
            connectNativeHost();
            if (focusGuardPort) {
                try {
                    focusGuardPort.postMessage({ type: "snapshot", tabs: tabs });
                    debugLog('Sent tab data to native host.');
                    sent = true;
                } catch (err) {
                    debugLog('Native messaging error:', err);
                }
            } else {
                debugLog('Native host port not connected.');
            }
        }
        // Send to HTTP server
        if (CONFIG.useHttpPost) {
            fetch(CONFIG.serverUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            })
            .then(response => {
                if (!response.ok) throw new Error(`Server returned ${response.status}`);
                debugLog('Sent tab data to server.');
                sent = true;
            })
            .catch(err => {
                debugLog('HTTP POST error:', err);
            });
        }
        updateIcon(sent);
        isConnected = sent;
    });
}

// Handle tab close command
function closeTab(tabId) {
    if (!tabId) {
        debugLog('Error: No tab ID provided for closing');
        return false;
    }
    
    // Add detailed logging
    debugLog(`Attempting to close tab with ID: ${tabId} (type: ${typeof tabId})`);
    
    try {
        // Convert tabId to number if it's a string
        if (typeof tabId === 'string') {
            debugLog(`Converting tabId from string to number: ${tabId}`);
            tabId = parseInt(tabId, 10);
            if (isNaN(tabId)) {
                debugLog('Error: tabId is not a valid number');
                return false;
            }
            debugLog(`Converted tabId to number: ${tabId}`);
        }
        
        // First check if the tab exists
        chrome.tabs.query({}, (tabs) => {
            const tabExists = tabs.some(tab => tab.id === tabId);
            debugLog(`Tab ${tabId} exists check: ${tabExists}`);
            
            if (!tabExists) {
                debugLog(`Tab ${tabId} does not exist in this browser`);
                return false;
            }
            
            // Tab exists, try to close it
            chrome.tabs.remove(tabId, () => {
                if (chrome.runtime.lastError) {
                    debugLog(`Error closing tab ${tabId}: ${JSON.stringify(chrome.runtime.lastError)}`);
                    return false;
                }
                debugLog(`Successfully closed tab ${tabId}`);
                return true;
            });
        });
        
        return true; // Return true to indicate the command was processed
    } catch (err) {
        debugLog(`Error closing tab ${tabId}: ${err.message}`);
        return false;
    }
}

// Process commands from FocusGuard
function processCommand(command) {
    debugLog('Processing command:', command);
    
    if (!command || !command.action) {
        debugLog('Invalid command format');
        return false;
    }
    
    switch (command.action) {
        case 'close_tab':
            if (command.data && command.data.tabId) {
                return closeTab(command.data.tabId);
            } else {
                debugLog('Missing tabId in close_tab command');
                return false;
            }
        case 'sync_dnr':
            // Server queued this after enforcement_mode changed — refresh DNR + cache invalidation immediately
            syncBlockedDomainsToRules().catch((e) => debugLog('sync_dnr failed:', e));
            return true;
        default:
            debugLog('Unknown command action:', command.action);
            return false;
    }
}

// W-42: Event-driven tab updates + 30s heartbeat (no 5s polling)
let tabUpdateDebounceTimer = null;
function scheduleTabDataSend() {
    if (tabUpdateDebounceTimer) clearTimeout(tabUpdateDebounceTimer);
    tabUpdateDebounceTimer = setTimeout(() => {
        tabUpdateDebounceTimer = null;
        sendTabData();
    }, CONFIG.tabUpdateDebounceMs);
}

// Lightweight connection check for heartbeat (no full tab payload)
function heartbeatConnectionCheck() {
    if (!CONFIG.useHttpPost) return;
    fetch(CONFIG.statusUrl, { method: 'GET', headers: { 'Cache-Control': 'no-cache' } })
        .then(response => {
            if (response.ok) {
                markServerReachable();
                updateIcon(true);
            } else {
                markServerUnreachable();
                updateIcon(false);
            }
        })
        .catch(() => {
            markServerUnreachable();
            updateIcon(false);
        });
}

function startEventDrivenUpdates() {
    sendTabData(); // Once on boot
    setInterval(heartbeatConnectionCheck, CONFIG.heartbeatIntervalMs);
    // Fallback: ensure full tab snapshot at least every 5 min for dashboard/monitoring
    setInterval(sendTabData, CONFIG.tabSnapshotFallbackMs);
}

// Initial boot
chrome.runtime.onInstalled.addListener(startEventDrivenUpdates);
chrome.runtime.onStartup.addListener(startEventDrivenUpdates);

// Tab event listeners drive full snapshot (debounced) — W-42
chrome.tabs.onRemoved.addListener((tabId, removeInfo) => {
    queueTabEvent('tab_removed', { tabId, removeInfo });
    scheduleTabDataSend();
});

chrome.tabs.onActivated.addListener((activeInfo) => {
    queueTabEvent('tab_activated', activeInfo);
    scheduleTabDataSend();
});

chrome.windows.onFocusChanged.addListener((windowId) => {
    queueTabEvent('window_focus_changed', { windowId });
});

// Manual trigger on icon click
chrome.action.onClicked.addListener(() => sendTabData());

// Setup HTTP command listener
function startCommandListener() {
    // Poll for commands every 2 seconds
    chrome.alarms.create('commandCheck', { periodInMinutes: 2/60 });
}

// Check for commands
function checkForCommands() {
    if (!CONFIG.useHttpPost) return;
    
    // Get browser name for command filtering
    const browserName = navigator.userAgent.includes('Edg') ? 'Microsoft Edge' : 'Google Chrome';
    debugLog(`Checking for commands for browser: ${browserName}`);
    
    // Add browser name as query parameter
    const commandUrlWithBrowser = `${CONFIG.commandUrl}?browser=${encodeURIComponent(browserName)}`;
    
    debugLog(`Fetching commands from: ${commandUrlWithBrowser}`);
    
    fetch(commandUrlWithBrowser)
        .then(response => {
            if (!response.ok) throw new Error(`Server returned ${response.status}`);
            debugLog(`Command response received with status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            debugLog(`Command data received: ${JSON.stringify(data)}`);
            const commands = data.commands || [];
            if (commands.length > 0) {
                debugLog(`Received ${commands.length} commands for ${browserName}: ${JSON.stringify(commands)}`);
                
                // Process each command
                commands.forEach(command => {
                    debugLog(`Processing command: ${JSON.stringify(command)} for browser: ${browserName}`);
                    const result = processCommand(command);
                    debugLog(`Command processing result: ${result}`);
                });
                
                // Acknowledge commands were processed
                const ackPayload = { status: "processed", browser: browserName };
                debugLog(`Sending acknowledgment: ${JSON.stringify(ackPayload)}`);
                
                fetch(CONFIG.commandUrl, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(ackPayload)
                })
                .then(response => {
                    debugLog(`Acknowledgment response status: ${response.status}`);
                    return response.text();
                })
                .then(text => debugLog(`Acknowledgment response: ${text}`))
                .catch(err => debugLog('Error acknowledging commands:', err));
            } else {
                debugLog(`No commands found for ${browserName}`);
            }
        })
        .catch(err => {
            debugLog(`Error checking for commands for ${browserName}:`, err);
        });
}

// Add command check to alarm listener (tabUpdate removed — W-42 event-driven)
chrome.alarms.onAlarm.addListener(alarm => {
    if (alarm.name === 'commandCheck') {
        checkForCommands();
    }
});

// Start command listener on initialization
startCommandListener();

// Preemptive blocking functionality
let blockRules = [];
let blockRuleId = 1;

// Initialize preemptive blocking — always syncs known-blocked domains as
// declarativeNetRequest redirect rules for instant network-layer blocking.
// This eliminates the redirect race (8.3.1) and works alongside real-time blocking.
async function initPreemptiveBlocking() {
    // Clear dynamic + session rules on startup (session redirects can survive reload in Chrome)
    try {
        await updateDynamicRules([]);
        debugLog('Startup: cleared declarativeNetRequest dynamic + session rules');
    } catch (err) {
        debugLog('Error clearing declarativeNetRequest rules on startup:', err);
    }

    debugLog('Initializing declarativeNetRequest domain sync (defense-in-depth)');
    
    // Create alarm to periodically sync blocked domains (every 5 min)
    chrome.alarms.create('syncBlockedDomains', { periodInMinutes: 5 });
    
    // Initial sync
    syncBlockedDomainsToRules();
    
    // Legacy preemptive blocking (server-pushed rules)
    if (CONFIG.usePreemptiveBlocking) {
        chrome.alarms.create('updateBlockRules', { periodInMinutes: 5 });
        updateBlockRules();
    }
}

// Sync blocked domains from server's domain overview into declarativeNetRequest rules.
// This provides instant blocking for ALL known-blocked domains without waiting for
// the real-time fetch per navigation.
//
// IMPORTANT (Day 8 Part B): Only **enforcing** mode may install network-layer DNR redirects.
// In advisory/tracking, `GET /api/should_block` already suppresses hard blocks — but DNR would
// still redirect main_frame navigations unless we clear rules here (Chrome vs Edge parity).
async function syncBlockedDomainsToRules() {
    try {
        const mode = await fetchEnforcementMode();
        noteEnforcementModeFromServer(mode);
        if (mode !== 'enforcing') {
            debugLog(
                `declarativeNetRequest: clearing dynamic rules (enforcement_mode=${mode === null ? 'unknown' : mode}; DNR only when enforcing)`
            );
            await updateDynamicRules([]);
            if (mode !== null) {
                markServerReachable();
            } else {
                markServerUnreachable();
            }
            return;
        }

        const response = await fetch(
            `${CONFIG.serverUrl.replace('/api/tabs', '/api/domains/overview')}?include_blocked=true`,
            { headers: { 'Cache-Control': 'no-cache' } }
        );
        
        if (!response.ok) {
            debugLog(`Failed to fetch domains for declarativeNetRequest sync: ${response.status}`);
            markServerUnreachable();
            // If mode flipped to advisory/tracking while overview failed, clear stale DNR (Chrome/Edge parity)
            try {
                const modeRetry = await fetchEnforcementMode();
                if (modeRetry !== 'enforcing') {
                    await updateDynamicRules([]);
                }
            } catch (_) {
                /* ignore */
            }
            return;
        }
        
        markServerReachable();
        const data = await response.json();
        
        // Collect domains that are blocked
        const blockedDomains = [];
        if (data.domains) {
            for (const d of data.domains) {
                if (d.status === 'blocked') {
                    blockedDomains.push(d.domain);
                }
            }
        }
        
        if (blockedDomains.length === 0) {
            debugLog('No blocked domains to sync to declarativeNetRequest (clearing stale DNR rules)');
            await updateDynamicRules([]);
            return;
        }
        
        // Build redirect rules — redirect to our blocked.html page
        const blockedPageUrl = chrome.runtime.getURL('blocked.html');
        const rules = blockedDomains.map((domain, index) => ({
            id: 10000 + index,  // Use high IDs to avoid collision with legacy rules
            priority: 1,
            action: {
                type: 'redirect',
                redirect: {
                    regexSubstitution: `${blockedPageUrl}?url=\\0&domain=${encodeURIComponent(domain)}&reason=${encodeURIComponent('Blocked by FocusGuard')}`
                }
            },
            condition: {
                regexFilter: `^https?://([^/]*\\.)?${domain.replace(/\./g, '\\.')}(/.*)?$`,
                resourceTypes: ['main_frame']
            }
        }));
        
        // Cap at Chrome's limit of 5000 dynamic rules
        const cappedRules = rules.slice(0, 5000);
        
        await updateDynamicRules(cappedRules);
        debugLog(`Synced ${cappedRules.length} blocked domains to declarativeNetRequest rules`);
        
    } catch (err) {
        debugLog('Error syncing blocked domains to declarativeNetRequest:', err);
        markServerUnreachable();
        try {
            const modeRetry = await fetchEnforcementMode();
            if (modeRetry !== 'enforcing') {
                await updateDynamicRules([]);
            }
        } catch (_) {
            /* ignore */
        }
    }
}

// Update block rules from server (legacy preemptive path — must respect enforcement mode like syncBlockedDomainsToRules)
async function updateBlockRules() {
    if (!CONFIG.usePreemptiveBlocking) return;

    const mode = await fetchEnforcementMode();
    if (mode !== 'enforcing') {
        debugLog(
            `updateBlockRules: skipping legacy preemptive DNR (enforcement_mode=${mode === null ? 'unknown' : mode})`
        );
        return;
    }

    debugLog('Updating block rules from server');

    const browserName = navigator.userAgent.includes('Edg') ? 'Microsoft Edge' : 'Google Chrome';

    try {
        const response = await fetch(
            `${CONFIG.blockCheckUrl}/rules?browser=${encodeURIComponent(browserName)}`
        );
        if (!response.ok) throw new Error(`Server returned ${response.status}`);
        const data = await response.json();
        debugLog(`Received ${data.rules ? data.rules.length : 0} block rules`);

        if (data.rules && data.rules.length > 0) {
            const blockedPageUrl = chrome.runtime.getURL('blocked.html');
            const newRules = data.rules.map((rule, index) => ({
                id: blockRuleId + index,
                priority: 1,
                action: {
                    type: 'redirect',
                    redirect: {
                        regexSubstitution: `${blockedPageUrl}?url=\\0&domain=${encodeURIComponent(rule.domain)}&reason=${encodeURIComponent(rule.reason || 'Blocked by FocusGuard')}`
                    }
                },
                condition: {
                    regexFilter: `^https?://([^/]*\\.)?${rule.domain.replace(/\./g, '\\.')}(/.*)?$`,
                    resourceTypes: ['main_frame']
                }
            }));
            await updateDynamicRules(newRules);
            blockRules = newRules;
            blockRuleId += newRules.length;
        }
    } catch (err) {
        debugLog('Error updating block rules:', err);
    }
}

// Update dynamic rules in declarativeNetRequest (also clears session rules — Chrome can hold redirects there)
async function updateDynamicRules(newRules) {
    try {
        const existingRules = await chrome.declarativeNetRequest.getDynamicRules();
        const existingRuleIds = existingRules.map((rule) => rule.id);

        await chrome.declarativeNetRequest.updateDynamicRules({
            removeRuleIds: existingRuleIds,
            addRules: newRules,
        });

        try {
            if (
                chrome.declarativeNetRequest.getSessionRules &&
                chrome.declarativeNetRequest.updateSessionRules
            ) {
                const sessionRules = await chrome.declarativeNetRequest.getSessionRules();
                const sessionIds = sessionRules.map((r) => r.id);
                if (sessionIds.length > 0) {
                    await chrome.declarativeNetRequest.updateSessionRules({
                        removeRuleIds: sessionIds,
                        addRules: [],
                    });
                    debugLog(`declarativeNetRequest: removed ${sessionIds.length} session rule(s)`);
                }
            }
        } catch (sessErr) {
            debugLog('declarativeNetRequest session rule cleanup skipped:', sessErr);
        }

        debugLog(`declarativeNetRequest: ${newRules.length} dynamic rule(s) active`);
    } catch (err) {
        debugLog('Error updating dynamic rules:', err);
    }
}

// Enhanced blocking decision with caching and timeout
async function shouldBlockUrl(url, tabId = null) {
    if (!CONFIG.useRealTimeBlocking || !url) return false;
    
    try {
        // Extract domain from URL
        const domain = new URL(url).hostname;
        
        // Check cache first for performance (key includes enforcement mode to avoid cross-mode stale entries)
        const modeKey = lastSeenEnforcementModeKey !== null ? lastSeenEnforcementModeKey : 'unknown';
        const cacheKey = `${domain}:${url}:${modeKey}`;
        if (CONFIG.cacheBlockingDecisions && blockingCache.has(cacheKey)) {
            const cached = blockingCache.get(cacheKey);
            const age = Date.now() - cached.timestamp;
            if (age < 30000) { // Cache for 30 seconds
                debugLog(`Using cached blocking decision for ${domain}: ${cached.shouldBlock}`);
                return cached.shouldBlock;
            }
        }
        
        // Prevent duplicate requests for the same URL
        if (pendingBlocks.has(cacheKey)) {
            debugLog(`Blocking decision already pending for ${domain}`);
            return false; // Default to not blocking while pending
        }
        
        pendingBlocks.add(cacheKey);
        
        // Get browser name for filtering
        const browserName = navigator.userAgent.includes('Edg') ? 'Microsoft Edge' : 'Google Chrome';
        
        // Create AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONFIG.blockingTimeout);
        
        try {
            // Query server for blocking decision with timeout
            const response = await fetch(
                `${CONFIG.blockCheckUrl}?url=${encodeURIComponent(url)}&domain=${encodeURIComponent(domain)}&browser=${encodeURIComponent(browserName)}&tabId=${tabId || ''}`,
                { 
                    signal: controller.signal,
                    headers: {
                        'Cache-Control': 'no-cache',
                        'X-Request-Priority': 'high'
                    }
                }
            );
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                debugLog(`Server returned ${response.status} for blocking check`);
                markServerUnreachable();
                // Fail-closed: block non-safe domains when server returns errors
                if (CONFIG.failClosedWhenServerDown && !isSafeDomain(domain)) {
                    debugLog(`FAIL-CLOSED: Blocking ${domain} (server error, not in safe list)`);
                    return true;
                }
                return false;
            }
            
            markServerReachable();
            const data = await response.json();
            scheduleDnrResyncFromShouldBlockResponse(data);
            const shouldBlock = data.should_block === true;
            
            // Cache the decision
            if (CONFIG.cacheBlockingDecisions) {
                blockingCache.set(cacheKey, {
                    shouldBlock,
                    timestamp: Date.now(),
                    reason: data.reason || 'unknown'
                });
                
                // Limit cache size
                if (blockingCache.size > 1000) {
                    const oldestKey = blockingCache.keys().next().value;
                    blockingCache.delete(oldestKey);
                }
            }
            
            debugLog(`Blocking decision for ${domain}: ${shouldBlock} (${data.reason || 'no reason'})`);
            return shouldBlock;
            
        } catch (fetchError) {
            clearTimeout(timeoutId);
            markServerUnreachable();
            if (fetchError.name === 'AbortError') {
                debugLog(`Blocking check timed out for ${domain} after ${CONFIG.blockingTimeout}ms`);
            } else {
                debugLog(`Error in blocking check for ${domain}:`, fetchError);
            }
            // Fail-closed: block non-safe domains when server is unreachable
            if (CONFIG.failClosedWhenServerDown && !isSafeDomain(domain)) {
                debugLog(`FAIL-CLOSED: Blocking ${domain} (server unreachable, not in safe list)`);
                return true;
            }
            return false;
        } finally {
            pendingBlocks.delete(cacheKey);
        }
        
    } catch (err) {
        debugLog('Error checking if URL should be blocked:', err);
        // Fail-closed for parse errors on non-safe domains
        if (CONFIG.failClosedWhenServerDown && !serverReachable) {
            return true;
        }
        return false;
    }
}

// Get the blocked page URL with parameters
function getBlockedPageUrl(originalUrl, domain, reason) {
    const blockedPage = chrome.runtime.getURL('blocked.html');
    const params = new URLSearchParams({
        url: originalUrl || '',
        domain: domain || '',
        reason: reason || 'This site is considered a distraction.'
    });
    return `${blockedPage}?${params.toString()}`;
}

// Redirect to blocked page instead of closing tab
async function redirectToBlockedPage(tabId, url, reason) {
    try {
        const domain = new URL(url).hostname;
        const blockedUrl = getBlockedPageUrl(url, domain, reason);
        await chrome.tabs.update(tabId, { url: blockedUrl });
        debugLog(`Redirected tab ${tabId} to blocked page for ${domain}`);
        queueTabEvent('tab_blocked', { tabId, url, domain, reason, action: 'redirect' });
        return true;
    } catch (err) {
        debugLog(`Error redirecting tab ${tabId}:`, err);
        return false;
    }
}

// Track active overrides locally (synced with server)
const activeOverrides = new Map(); // domain -> { expiry_time, override_id }

// Check if domain has an active override
async function checkOverride(domain) {
    try {
        const response = await fetch(
            `${CONFIG.serverUrl.replace('/api/tabs', '/api/override')}?domain=${encodeURIComponent(domain)}`,
            { headers: { 'Cache-Control': 'no-cache' } }
        );
        if (!response.ok) return { hasOverride: false };
        const data = await response.json();
        
        if (data.has_override) {
            activeOverrides.set(domain, {
                expiry_time: data.override.expiry_time,
                override_id: data.override.id
            });
        } else {
            activeOverrides.delete(domain);
        }
        
        return { hasOverride: data.has_override, override: data.override };
    } catch (err) {
        debugLog('Error checking override:', err);
        return { hasOverride: false };
    }
}

// Enhanced blocking check that returns reason
async function shouldBlockUrlWithReason(url, tabId = null) {
    if (!CONFIG.useRealTimeBlocking || !url) {
        debugLog(`Blocking check skipped: useRealTimeBlocking=${CONFIG.useRealTimeBlocking}, url=${url}`);
        return { shouldBlock: false, reason: '' };
    }
    
    try {
        const domain = new URL(url).hostname;
        debugLog(`Checking if should block: ${domain} (${url})`);
        
        // First check if there's an active override for this domain
        try {
            const overrideCheck = await checkOverride(domain);
            if (overrideCheck.hasOverride) {
                debugLog(`Domain ${domain} has active override, allowing access`);
                return { shouldBlock: false, reason: '', hasOverride: true, override: overrideCheck.override };
            }
        } catch (overrideErr) {
            debugLog(`Override check failed (continuing with block check): ${overrideErr}`);
        }
        
        const modeKey = lastSeenEnforcementModeKey !== null ? lastSeenEnforcementModeKey : 'unknown';
        const cacheKey = `${domain}:${url}:${modeKey}`;
        const isShortener = isUrlShortener(domain);
        
        // URL shorteners (8.7.1): skip cache since destination is unknown
        // In fail-closed mode, block shorteners outright
        if (isShortener && !serverReachable && CONFIG.failClosedWhenServerDown) {
            debugLog(`FAIL-CLOSED: Blocking URL shortener ${domain} (server unreachable, destination unknown)`);
            return { shouldBlock: true, reason: 'URL shortener blocked — FocusGuard server unreachable' };
        }
        
        // Check cache (skip for shorteners — destination changes per link)
        if (!isShortener && CONFIG.cacheBlockingDecisions && blockingCache.has(cacheKey)) {
            const cached = blockingCache.get(cacheKey);
            if (Date.now() - cached.timestamp < 30000) {
                debugLog(`Using cached blocking decision for ${domain}: shouldBlock=${cached.shouldBlock}`);
                return { shouldBlock: cached.shouldBlock, reason: cached.reason };
            }
        }
        
        debugLog(`Fetching blocking decision from server for ${domain}...`);
        
        // Get tab info for title and referrer (if tabId available)
        let title = '';
        let referrer = '';
        const browserName = navigator.userAgent.includes('Edg') ? 'Microsoft Edge' : 'Google Chrome';
        if (tabId) {
            try {
                const tab = await chrome.tabs.get(tabId);
                title = tab.title || '';
                // Try to get referrer from tab's opener or from navigation history
                if (tab.openerTabId) {
                    try {
                        const openerTab = await chrome.tabs.get(tab.openerTabId);
                        referrer = openerTab.url || '';
                    } catch (e) {
                        debugLog('Could not get opener tab:', e);
                    }
                }
            } catch (e) {
                debugLog('Could not get tab info:', e);
            }
        }
        
        const response = await fetch(
            `${CONFIG.blockCheckUrl}?url=${encodeURIComponent(url)}&domain=${encodeURIComponent(domain)}&title=${encodeURIComponent(title)}&tabId=${tabId || ''}&referrer=${encodeURIComponent(referrer)}&browser=${encodeURIComponent(browserName)}`,
            { headers: { 'Cache-Control': 'no-cache' } }
        );
        
        if (!response.ok) {
            debugLog(`Server returned error: ${response.status}`);
            markServerUnreachable();
            // Fail-closed: block non-safe domains when server returns errors
            if (CONFIG.failClosedWhenServerDown && !isSafeDomain(domain)) {
                debugLog(`FAIL-CLOSED: Blocking ${domain} (server error, not in safe list)`);
                return { shouldBlock: true, reason: 'FocusGuard server unreachable — blocked for safety' };
            }
            return { shouldBlock: false, reason: '' };
        }
        
        markServerReachable();
        const data = await response.json();
        debugLog(
            `Server response for ${domain}: should_block=${data.should_block}, reason=${data.reason}, enforcement_mode=${data.enforcement_mode || 'n/a'}`
        );
        scheduleDnrResyncFromShouldBlockResponse(data);
        const result = { 
            shouldBlock: data.should_block === true, 
            reason: data.reason || 'Blocked by FocusGuard' 
        };
        
        // Cache result
        if (CONFIG.cacheBlockingDecisions) {
            blockingCache.set(cacheKey, { ...result, timestamp: Date.now() });
        }
        
        return result;
    } catch (err) {
        debugLog('Error in blocking check:', err);
        markServerUnreachable();
        // Fail-closed: block non-safe domains when server is unreachable
        try {
            const domain = new URL(url).hostname;
            if (CONFIG.failClosedWhenServerDown && !isSafeDomain(domain)) {
                debugLog(`FAIL-CLOSED: Blocking ${domain} (server unreachable, not in safe list)`);
                return { shouldBlock: true, reason: 'FocusGuard server unreachable — blocked for safety' };
            }
        } catch (_) {}
        return { shouldBlock: false, reason: '' };
    }
}

// Enhanced tab creation listener with real-time event streaming
chrome.tabs.onCreated.addListener(async (tab) => {
    queueTabEvent('tab_created', tab);
    scheduleTabDataSend();

    if (!CONFIG.useRealTimeBlocking || !tab.url || tab.url.startsWith('chrome') || tab.url.startsWith('edge')) return;
    
    debugLog(`New tab created: ${tab.url} (ID: ${tab.id})`);
    
    const result = await shouldBlockUrlWithReason(tab.url, tab.id);
    
    if (result.shouldBlock) {
        debugLog(`Blocking newly created tab: ${tab.url}`);
        await redirectToBlockedPage(tab.id, tab.url, result.reason);
    }
});

// Enhanced tab update listener with real-time event streaming
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
    // Send real-time event for significant changes
    if (changeInfo.url || changeInfo.status === 'complete') {
        queueTabEvent('tab_updated', { tabId, changeInfo, tab });
        scheduleTabDataSend();
    }

    if (!CONFIG.useRealTimeBlocking) return;
    
    // Check blocking on URL change OR when loading starts (to catch navigations)
    const urlToCheck = changeInfo.url || (changeInfo.status === 'loading' && tab.url);
    
    if (!urlToCheck) return;
    
    // Skip browser internal pages
    if (urlToCheck.startsWith('chrome') || urlToCheck.startsWith('edge') || urlToCheck.startsWith('about:')) return;
    
    // Skip if already on blocked page
    if (urlToCheck.includes('blocked.html')) return;
    
    debugLog(`Tab ${tabId} navigating to: ${urlToCheck} (status: ${changeInfo.status})`);
    
    const result = await shouldBlockUrlWithReason(urlToCheck, tabId);
    
    if (result.shouldBlock) {
        debugLog(`Blocking navigation to URL: ${urlToCheck}`);
        await redirectToBlockedPage(tabId, urlToCheck, result.reason);
    }
});

// Enhanced alarm listener with event queue flushing
chrome.alarms.onAlarm.addListener(alarm => {
    if (alarm.name === 'syncBlockedDomains') {
        syncBlockedDomainsToRules();
    } else if (alarm.name === 'updateBlockRules') {
        updateBlockRules();
    } else if (alarm.name === 'flushEvents') {
        flushEventQueue();
    } else if (alarm.name === 'tickUsageTracker') {
        tickUsageTracker();
    }
});

// Create alarm for periodic event flushing (fallback)
chrome.alarms.create('flushEvents', { periodInMinutes: 0.5 }); // Every 30 seconds

// Chrome alarms have a minimum of 1 minute, so we use setInterval for more frequent checks
// Create alarm for usage tracker tick (every minute as backup)
chrome.alarms.create('tickUsageTracker', { periodInMinutes: 1 }); // Every 1 minute (backup)

// Use setInterval for more frequent override expiry checks (every 5 seconds)
setInterval(() => {
    if (activeOverrideSessions.size > 0) {
        tickUsageTracker();
    }
}, 5000); // Every 5 seconds when there are active sessions

// Track window focus state for active/inactive time tracking
let lastActiveTabId = null;
let lastActiveWindowId = null;

// Window focus changed - track active state
chrome.windows.onFocusChanged.addListener(async (windowId) => {
    if (windowId === chrome.windows.WINDOW_ID_NONE) {
        // Browser lost focus - all tabs inactive
        debugLog('Browser window lost focus');
        if (lastActiveTabId) {
            await updateTabActiveState(lastActiveTabId, false);
        }
        lastActiveWindowId = null;
    } else {
        lastActiveWindowId = windowId;
        // Get active tab in this window
        try {
            const tabs = await chrome.tabs.query({ active: true, windowId: windowId });
            if (tabs.length > 0) {
                const tab = tabs[0];
                if (lastActiveTabId && lastActiveTabId !== tab.id) {
                    await updateTabActiveState(lastActiveTabId, false);
                }
                lastActiveTabId = tab.id;
                await updateTabActiveState(tab.id, true);
                debugLog(`Window ${windowId} focused, active tab: ${tab.id}`);
            }
        } catch (err) {
            debugLog('Error getting active tab on window focus:', err);
        }
    }
});

// Tab activated - track which tab is active
chrome.tabs.onActivated.addListener(async (activeInfo) => {
    debugLog(`Tab activated: ${activeInfo.tabId} in window ${activeInfo.windowId}`);
    
    // Deactivate previous tab
    if (lastActiveTabId && lastActiveTabId !== activeInfo.tabId) {
        await updateTabActiveState(lastActiveTabId, false);
    }
    
    // Activate new tab (only if window is focused)
    if (lastActiveWindowId === activeInfo.windowId || lastActiveWindowId === null) {
        lastActiveTabId = activeInfo.tabId;
        await updateTabActiveState(activeInfo.tabId, true);
    }
});

// Update tab active state on server
async function updateTabActiveState(tabId, isActive) {
    if (!CONFIG.useHttpPost) return;
    
    try {
        await fetch(`${CONFIG.serverUrl.replace('/api/tabs', '/api/domain/active')}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tab_id: tabId, is_active: isActive })
        });
    } catch (err) {
        // Silent fail - not critical
    }
}

// Tick the usage tracker (called every second)
async function tickUsageTracker() {
    // Check active override sessions for expiry
    for (const [domain, session] of activeOverrideSessions.entries()) {
        await checkOverrideSessionExpiry(domain, session);
    }
}

// Check if an override session has expired and block if needed
async function checkOverrideSessionExpiry(domain, session) {
    try {
        const response = await fetch(`${CONFIG.serverUrl.replace('/api/tabs', '/api/override')}?domain=${encodeURIComponent(domain)}`);
        const result = await response.json();
        
        if (!result.has_override) {
            // Override expired - block all tabs with this domain
            debugLog(`Override expired for ${domain}, blocking tabs`);
            
            for (const tabId of session.tabIds) {
                try {
                    const tab = await chrome.tabs.get(tabId);
                    if (tab && tab.url) {
                        const tabDomain = extractDomain(tab.url);
                        if (tabDomain === domain || tabDomain.endsWith('.' + domain)) {
                            // Redirect to blocked page
                            await redirectToBlockedPage(tabId, tab.url, result.expired_reason || 'Session time expired');
                        }
                    }
                } catch (e) {
                    // Tab may have been closed
                }
            }
            
            // Clean up session
            activeOverrideSessions.delete(domain);
        }
    } catch (err) {
        debugLog('Error checking override expiry:', err);
    }
}

// Start tracking an override session and notify server
async function startOverrideSession(domain, tabId) {
    if (!activeOverrideSessions.has(domain)) {
        activeOverrideSessions.set(domain, {
            tabIds: new Set(),
            startTime: Date.now(),
            usageStarted: false
        });
    }
    const session = activeOverrideSessions.get(domain);
    session.tabIds.add(tabId);
    
    // Notify server to start usage tracking (this increments the override count)
    if (!session.usageStarted) {
        try {
            const response = await fetch(`${CONFIG.serverUrl.replace('/api/tabs', '/api/override/start')}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ domain: domain, tab_id: String(tabId) })
            });
            const result = await response.json();
            if (result.started) {
                session.usageStarted = true;
                debugLog(`Started override usage for ${domain}, tab ${tabId}, daily count: ${result.daily_count}`);
            }
        } catch (err) {
            debugLog('Error starting override usage:', err);
        }
    }
    
    debugLog(`Tracking override session for ${domain}, tab ${tabId}`);
}

// Stop tracking an override session for a tab
function stopOverrideSessionTab(domain, tabId) {
    const session = activeOverrideSessions.get(domain);
    if (session) {
        session.tabIds.delete(tabId);
        if (session.tabIds.size === 0) {
            activeOverrideSessions.delete(domain);
            debugLog(`Ended override session for ${domain} (no more tabs)`);
        }
    }
}

// NOTE: override_granted messages are handled by the unified listener below (near overriddenTabs).

// Clean up override sessions when tabs are closed
chrome.tabs.onRemoved.addListener((tabId, removeInfo) => {
    // Check all sessions and remove this tab
    for (const [domain, session] of activeOverrideSessions.entries()) {
        if (session.tabIds.has(tabId)) {
            stopOverrideSessionTab(domain, tabId);
        }
    }
});

// Queue tab events for batched sending
function queueTabEvent(eventType, eventData) {
    if (!CONFIG.batchEventUpdates) {
        sendTabEvent(eventType, eventData);
        return;
    }
    
    const event = {
        type: eventType,
        data: eventData,
        timestamp: Date.now(),
        browser: navigator.userAgent.includes('Edg') ? 'Microsoft Edge' : 'Google Chrome'
    };
    
    eventQueue.push(event);
    lastEventTime = Date.now();
    
    // Batch events together, but send immediately for critical events
    const criticalEvents = ['tab_blocked', 'tab_created'];
    if (criticalEvents.includes(eventType)) {
        flushEventQueue();
    } else {
        // Batch other events with a short delay
        if (eventBatchTimer) clearTimeout(eventBatchTimer);
        eventBatchTimer = setTimeout(flushEventQueue, 100); // 100ms batch window
    }
}

// Send individual tab event
function sendTabEvent(eventType, eventData) {
    if (!CONFIG.useHttpPost) return;
    
    const event = {
        type: eventType,
        data: eventData,
        timestamp: Date.now(),
        browser: navigator.userAgent.includes('Edg') ? 'Microsoft Edge' : 'Google Chrome'
    };
    
    fetch(CONFIG.eventStreamUrl, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-Event-Type': eventType
        },
        body: JSON.stringify(event)
    })
    .then(response => {
        if (!response.ok) throw new Error(`Event server returned ${response.status}`);
        debugLog(`Sent ${eventType} event to server`);
    })
    .catch(err => {
        debugLog(`Error sending ${eventType} event:`, err);
    });
}

// Flush queued events
function flushEventQueue() {
    if (eventQueue.length === 0) return;
    
    const events = [...eventQueue];
    eventQueue = [];
    
    if (eventBatchTimer) {
        clearTimeout(eventBatchTimer);
        eventBatchTimer = null;
    }
    
    if (!CONFIG.useHttpPost) return;
    
    fetch(CONFIG.eventStreamUrl, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-Event-Batch': 'true'
        },
        body: JSON.stringify({ events })
    })
    .then(response => {
        if (!response.ok) throw new Error(`Event server returned ${response.status}`);
        debugLog(`Sent batch of ${events.length} events to server`);
    })
    .catch(err => {
        debugLog(`Error sending event batch:`, err);
    });
}

// Clear old cache entries periodically
setInterval(() => {
    if (!CONFIG.cacheBlockingDecisions) return;
    
    const now = Date.now();
    for (const [key, value] of blockingCache.entries()) {
        if (now - value.timestamp > 60000) { // Remove entries older than 1 minute
            blockingCache.delete(key);
        }
    }
}, 30000); // Clean every 30 seconds

// Track tabs with overridden domains for expiry monitoring
const overriddenTabs = new Map(); // tabId -> { domain, expiry_time, override_id }

// Monitor overridden tabs and close when override expires
async function checkOverrideExpiry() {
    const now = Date.now() / 1000; // Convert to seconds to match server timestamps
    
    for (const [tabId, info] of overriddenTabs.entries()) {
        if (now > info.expiry_time) {
            debugLog(`Override expired for tab ${tabId} (${info.domain})`);
            
            try {
                // Get current tab info
                const tab = await chrome.tabs.get(tabId);
                const tabDomain = new URL(tab.url).hostname;
                
                // Only redirect if still on the overridden domain
                if (tabDomain === info.domain || tabDomain.endsWith('.' + info.domain)) {
                    debugLog(`Redirecting expired override tab ${tabId} to blocked page`);
                    await redirectToBlockedPage(tabId, tab.url, 'Override time expired');
                    queueTabEvent('override_expired', { tabId, domain: info.domain, override_id: info.override_id });
                }
            } catch (err) {
                debugLog(`Tab ${tabId} no longer exists or error:`, err);
            }
            
            overriddenTabs.delete(tabId);
        }
    }
}

// Check override expiry every 10 seconds
setInterval(checkOverrideExpiry, 10000);

// Unified listener for messages from blocked page (override_granted)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'override_granted') {
        debugLog(`Override granted for ${message.domain}, expiry: ${message.expiry_time}`);
        
        const tabId = sender.tab?.id;
        
        // Start server-side usage tracking session
        if (tabId && message.domain) {
            startOverrideSession(message.domain, tabId);
        }
        
        // Track this tab for client-side expiry monitoring
        if (sender.tab) {
            overriddenTabs.set(sender.tab.id, {
                domain: message.domain,
                expiry_time: message.expiry_time,
                override_id: message.override_id
            });
        }
        
        // Update local override cache
        activeOverrides.set(message.domain, {
            expiry_time: message.expiry_time,
            override_id: message.override_id
        });
        
        // Clear blocking cache for this domain so it gets re-checked
        for (const [key] of blockingCache.entries()) {
            if (key.includes(message.domain)) {
                blockingCache.delete(key);
            }
        }
        
        sendResponse({ success: true });
    }
    return true; // Keep channel open for async response
});

// Track when tabs navigate to overridden domains
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.url && !changeInfo.url.includes('blocked.html')) {
        try {
            const domain = new URL(changeInfo.url).hostname;
            const override = activeOverrides.get(domain);
            
            if (override && (Date.now() / 1000) < override.expiry_time) {
                // Tab navigated to an overridden domain, track it
                if (!overriddenTabs.has(tabId)) {
                    overriddenTabs.set(tabId, {
                        domain: domain,
                        expiry_time: override.expiry_time,
                        override_id: override.override_id
                    });
                    debugLog(`Tracking tab ${tabId} on overridden domain ${domain}`);
                }
            }
        } catch (err) {
            // Invalid URL, ignore
        }
    }
});

// Clean up when tabs are closed
chrome.tabs.onRemoved.addListener((tabId) => {
    overriddenTabs.delete(tabId);
});

// Initialize preemptive blocking
initPreemptiveBlocking();

debugLog('FocusGuard background script initialized with real-time blocking and override support.');
debugLog(`Configuration: Real-time blocking: ${CONFIG.useRealTimeBlocking}, Caching: ${CONFIG.cacheBlockingDecisions}, Batching: ${CONFIG.batchEventUpdates}`);
