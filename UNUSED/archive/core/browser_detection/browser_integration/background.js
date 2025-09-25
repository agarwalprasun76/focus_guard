// browser_extension/background.js
const SERVER_URL = "http://127.0.0.1:5000/api/tabs";
const RETRY_DELAY = 5000; // 5 seconds
const UPDATE_INTERVAL = 5000; // 5 seconds

let isConnected = false;
let retryCount = 0;
const MAX_RETRIES = 3;

// Update extension icon based on connection status
function updateIcon(connected) {
    const iconPath = connected ? "icons/icon48.png" : "icons/icon48-disconnected.png";
    chrome.browserAction.setIcon({ path: iconPath });
}

// Send tab data to the server
async function sendTabData() {
    try {
        const tabs = await chrome.tabs.query({});
        const browserInfo = {
            name: "Microsoft Edge",
            version: navigator.userAgent,
            platform: navigator.platform
        };

        const tabData = tabs.map(tab => ({
            id: tab.id,
            windowId: tab.windowId,
            url: tab.url,
            title: tab.title,
            active: tab.active,
            pinned: tab.pinned,
            lastAccessed: tab.lastAccessed
        }));

        const response = await fetch(SERVER_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                browser: browserInfo,
                tabs: tabData,
                timestamp: Date.now()
            })
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        // Reset retry count on success
        retryCount = 0;
        
        // Update connection status
        if (!isConnected) {
            isConnected = true;
            updateIcon(true);
            console.log("Connected to FocusGuard server");
        }
        
        return true;
    } catch (error) {
        console.error("Error sending tab data:", error);
        
        // Update connection status
        if (isConnected) {
            isConnected = false;
            updateIcon(false);
            console.log("Disconnected from FocusGuard server");
        }
        
        // Implement exponential backoff
        retryCount++;
        if (retryCount <= MAX_RETRIES) {
            const delay = RETRY_DELAY * Math.pow(2, retryCount - 1);
            console.log(`Retrying in ${delay/1000} seconds... (${retryCount}/${MAX_RETRIES})`);
            setTimeout(sendTabData, delay);
        } else {
            console.log("Max retries reached. Will retry on next interval.");
        }
        
        return false;
    }
}

// Check server connection
async function checkConnection() {
    try {
        const response = await fetch("http://127.0.0.1:5000/api/status");
        return response.ok;
    } catch (error) {
        return false;
    }
}

// Initialize
async function init() {
    // Initial connection check
    const connected = await checkConnection();
    updateIcon(connected);
    isConnected = connected;
    
    // Start periodic updates
    setInterval(sendTabData, UPDATE_INTERVAL);
    
    // Also send immediately
    sendTabData();
}

// Listen for installation/update
chrome.runtime.onInstalled.addListener(init);
chrome.runtime.onStartup.addListener(init);

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getConnectionStatus") {
        sendResponse({ connected: isConnected });
    }
});