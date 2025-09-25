// FocusGuard Background Script with Idle Detection & Retry Logic

const CONFIG = {
    useNativeMessaging: true,
    useHttpPost: false,
    serverUrl: "http://127.0.0.1:5000/api/tabs",
    statusUrl: "http://127.0.0.1:5000/api/status",
    updateInterval: 5000, // ms
    idleThresholdSec: 60, // idle if no input for 60s
    maxRetries: 3,
    retryDelayMs: 5000,
    debug: true
};

let focusGuardPort = null;
let isConnected = false;
let retryCount = 0;
let retryTimer = null;

function debugLog(...args) {
    if (CONFIG.debug) {
        console.log('[FocusGuard]', ...args);
    }
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
    chrome.idle.queryState(CONFIG.idleThresholdSec, function (state) {
        if (state === 'idle' || state === 'locked') {
            debugLog(`Skipping update: user is ${state}.`);
            return;
        }

        getAllTabs(function (tabs) {
            const browserInfo = {
                name: navigator.userAgent.includes('Edg') ? 'Microsoft Edge' : 'Google Chrome',
                version: navigator.userAgent,
                platform: navigator.platform
            };

            const payload = {
                type: "snapshot",
                browser: browserInfo,
                tabs: tabs,
                timestamp: Date.now()
            };

            let sent = false;

            if (CONFIG.useNativeMessaging) {
                connectNativeHost();
                if (focusGuardPort) {
                    try {
                        focusGuardPort.postMessage(payload);
                        debugLog('Sent tab data to native host.');
                        sent = true;
                    } catch (err) {
                        debugLog('Error posting message to native host:', err);
                        focusGuardPort = null;
                    }
                }
            }

            if (CONFIG.useHttpPost) {
                fetch(CONFIG.serverUrl, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                }).then(response => {
                    if (!response.ok) throw new Error(`Server returned ${response.status}`);
                    debugLog('Sent tab data to server.');
                    sent = true;
                }).catch(err => {
                    debugLog('HTTP POST error:', err);
                });
            }

            updateIcon(sent);
            isConnected = sent;
        });
    });
}

function startPeriodicUpdates() {
    sendTabData(); // Immediately
    chrome.alarms.create('tabUpdate', { periodInMinutes: CONFIG.updateInterval / 60000 });
}

// Initial boot
chrome.runtime.onInstalled.addListener(startPeriodicUpdates);
chrome.runtime.onStartup.addListener(startPeriodicUpdates);

// Alarm for periodic updates
chrome.alarms.onAlarm.addListener(alarm => {
    if (alarm.name === 'tabUpdate') {
        sendTabData();
    }
});

// Tab event listeners
chrome.tabs.onCreated.addListener(() => sendTabData());
chrome.tabs.onUpdated.addListener(() => sendTabData());
chrome.tabs.onRemoved.addListener(() => sendTabData());

// Manual trigger on icon click
chrome.action.onClicked.addListener(() => sendTabData());

debugLog('FocusGuard background script initialized.');
