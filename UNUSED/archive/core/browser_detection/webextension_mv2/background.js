// FocusGuard WebExtension Background Script (Unified)
// Sends tab info to native host (native messaging) and/or local HTTP server

console.log("FocusGuard background script loaded!");

function updateIcon(connected) {
    const iconPath = connected
        ? { "16": "icons/icon16.png", "48": "icons/icon48.png"}
        : { "16": "icons/icon16_gray.png",  "48": "icons/icon48_gray.png"};
    chrome.browserAction.setIcon({ path: iconPath });
}

const CONFIG = {
    useNativeMessaging: true, // Set to true to use native host
    useHttpPost: false,      // Set to true to send to local server
    serverUrl: "http://127.0.0.1:5000/api/tabs",
    statusUrl: "http://127.0.0.1:5000/api/status",
    updateInterval: 5000,    // ms
    debug: true
};

let isConnected = false;
let retryCount = 0;
const MAX_RETRIES = 3;
const RETRY_DELAY = 5000;

function debugLog(...args) {
    if (CONFIG.debug) {
        console.log('[FocusGuard]', ...args);
    }
}


function getAllTabs(callback) {
    chrome.tabs.query({}, function(tabs) {
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
    // Send to native host
    if (CONFIG.useNativeMessaging) {
        try {
            const port = chrome.runtime.connectNative('com.focusguard.native');
            port.postMessage({ type: "snapshot", tabs: tabs });
            port.disconnect();
            debugLog('Sent tab data to native host.');
            sent = true;
        } catch (err) {
            debugLog('Native messaging error:', err);
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
    // Update connection status
    updateIcon(sent);
    isConnected = sent;
})
}

function startPeriodicUpdates() {
    sendTabData(); // Immediately
    setInterval(sendTabData, CONFIG.updateInterval);
}

chrome.runtime.onInstalled.addListener(startPeriodicUpdates);
chrome.runtime.onStartup.addListener(startPeriodicUpdates);
// Optionally, listen for tab changes for more real-time updates
chrome.tabs.onUpdated.addListener(() => sendTabData());
chrome.tabs.onRemoved.addListener(() => sendTabData());
chrome.tabs.onCreated.addListener(() => sendTabData());

// For manual trigger (optional):
chrome.browserAction.onClicked.addListener(() => sendTabData());

debugLog('FocusGuard extension background script loaded.');
