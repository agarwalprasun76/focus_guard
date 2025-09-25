// FocusGuard Background Script with Idle Detection & Retry Logic

const CONFIG = {
    useNativeMessaging: true,
    useHttpPost: true,
    serverUrl: "http://127.0.0.1:5000/api/tabs",
    statusUrl: "http://127.0.0.1:5000/api/status",
    commandUrl: "http://127.0.0.1:5000/api/command", // New endpoint for commands
    blockCheckUrl: "http://127.0.0.1:5000/api/should_block", // New endpoint for preemptive blocking
    updateInterval: 5000, // ms
    idleThresholdSec: 60, // idle if no input for 60s
    maxRetries: 3,
    retryDelayMs: 5000,
    debug: true,
    usePreemptiveBlocking: true // Enable preemptive blocking
};

let focusGuardPort = null;
let isConnected = false;
let retryCount = 0;
let retryTimer = null;

function connectNativeHost() {
    if (focusGuardPort) return;
    debugLog('Connecting to native host...');
    focusGuardPort = chrome.runtime.connectNative('com.focusguard.native');
    isConnected = true;
    focusGuardPort.onDisconnect.addListener(() => {
        debugLog('Native host disconnected.');
        focusGuardPort = null;
        isConnected = false;
        // Optionally, try to reconnect after a delay
        setTimeout(connectNativeHost, CONFIG.retryDelayMs);
    });
}

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
        default:
            debugLog('Unknown command action:', command.action);
            return false;
    }
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

// Add command check to alarm listener
chrome.alarms.onAlarm.addListener(alarm => {
    if (alarm.name === 'tabUpdate') {
        sendTabData();
    } else if (alarm.name === 'commandCheck') {
        checkForCommands();
    }
});

// Start command listener on initialization
startCommandListener();

// Preemptive blocking functionality
let blockRules = [];
let blockRuleId = 1;

// Initialize preemptive blocking
function initPreemptiveBlocking() {
    if (!CONFIG.usePreemptiveBlocking) {
        debugLog('Preemptive blocking is disabled');
        return;
    }
    
    debugLog('Initializing preemptive blocking');
    
    // Create alarm to periodically update block rules
    chrome.alarms.create('updateBlockRules', { periodInMinutes: 5 });
    
    // Initial update of block rules
    updateBlockRules();
}

// Update block rules from server
function updateBlockRules() {
    if (!CONFIG.usePreemptiveBlocking) return;
    
    debugLog('Updating block rules from server');
    
    // Get browser name for filtering
    const browserName = navigator.userAgent.includes('Edg') ? 'Microsoft Edge' : 'Google Chrome';
    
    // Fetch block rules from server
    fetch(`${CONFIG.blockCheckUrl}/rules?browser=${encodeURIComponent(browserName)}`)
        .then(response => {
            if (!response.ok) throw new Error(`Server returned ${response.status}`);
            return response.json();
        })
        .then(data => {
            debugLog(`Received ${data.rules ? data.rules.length : 0} block rules`);
            
            if (data.rules && data.rules.length > 0) {
                // Convert server rules to declarativeNetRequest rules
                const newRules = data.rules.map((rule, index) => ({
                    id: blockRuleId + index,
                    priority: 1,
                    action: { type: 'block' },
                    condition: {
                        urlFilter: rule.domain,
                        resourceTypes: ['main_frame']
                    }
                }));
                
                // Update rules
                updateDynamicRules(newRules);
                blockRules = newRules;
                blockRuleId += newRules.length;
            }
        })
        .catch(err => {
            debugLog('Error updating block rules:', err);
        });
}

// Update dynamic rules in declarativeNetRequest
async function updateDynamicRules(newRules) {
    try {
        // Get existing rules
        const existingRules = await chrome.declarativeNetRequest.getDynamicRules();
        const existingRuleIds = existingRules.map(rule => rule.id);
        
        // Update rules (remove old, add new)
        await chrome.declarativeNetRequest.updateDynamicRules({
            removeRuleIds: existingRuleIds,
            addRules: newRules
        });
        
        debugLog(`Updated ${newRules.length} block rules`);
    } catch (err) {
        debugLog('Error updating dynamic rules:', err);
    }
}

// Check if a URL should be blocked (for use in tabs.onCreated listener)
async function shouldBlockUrl(url) {
    if (!CONFIG.usePreemptiveBlocking || !url) return false;
    
    try {
        // Extract domain from URL
        const domain = new URL(url).hostname;
        
        // Get browser name for filtering
        const browserName = navigator.userAgent.includes('Edg') ? 'Microsoft Edge' : 'Google Chrome';
        
        // Query server for blocking decision
        const response = await fetch(
            `${CONFIG.blockCheckUrl}?url=${encodeURIComponent(url)}&domain=${encodeURIComponent(domain)}&browser=${encodeURIComponent(browserName)}`
        );
        
        if (!response.ok) return false;
        
        const data = await response.json();
        return data.should_block === true;
    } catch (err) {
        debugLog('Error checking if URL should be blocked:', err);
        return false;
    }
}

// Add listener for tab creation to handle cases where declarativeNetRequest might not catch
chrome.tabs.onCreated.addListener(async (tab) => {
    if (!CONFIG.usePreemptiveBlocking || !tab.url || tab.url.startsWith('chrome')) return;
    
    const shouldBlock = await shouldBlockUrl(tab.url);
    
    if (shouldBlock) {
        debugLog(`Blocking newly created tab with URL: ${tab.url}`);
        chrome.tabs.remove(tab.id);
    }
});

// Add listener for tab updates to catch navigation to blocked sites
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
    if (!CONFIG.usePreemptiveBlocking || !changeInfo.url) return;
    
    const shouldBlock = await shouldBlockUrl(changeInfo.url);
    
    if (shouldBlock) {
        debugLog(`Blocking navigation to URL: ${changeInfo.url}`);
        chrome.tabs.remove(tabId);
    }
});

// Add block rule update to alarm listener
chrome.alarms.onAlarm.addListener(alarm => {
    if (alarm.name === 'updateBlockRules') {
        updateBlockRules();
    }
});

// Initialize preemptive blocking
initPreemptiveBlocking();

debugLog('FocusGuard background script initialized.');
