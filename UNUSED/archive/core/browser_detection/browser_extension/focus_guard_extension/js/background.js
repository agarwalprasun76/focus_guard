/**
 * FocusGuard Tab Tracker - Background Script
 * 
 * This script runs in the background and tracks all browser tabs.
 * It sends tab information to the FocusGuard application via HTTP.
 */

// Keep service worker alive
let keepAliveInterval;

// Configuration
const config = {
  // API endpoint for sending tab data to FocusGuard
  apiEndpoint: 'http://localhost:5000/api/tabs',
  // How often to send updates (in milliseconds)
  updateInterval: 5000,
  // Whether to log debug information
  debug: true,
  // Connection test endpoint
  statusEndpoint: 'http://localhost:5000/api/status',
  // Connection retry settings
  maxRetries: 3,
  retryDelay: 2000
};

// State
let tabsState = {};
let updateTimer = null;

/**
 * Log messages if debug is enabled
 */
function debugLog(...args) {
  if (config.debug) {
    console.log('[FocusGuard]', ...args);
  }
}

/**
 * Get information about all tabs
 */
async function getAllTabs() {
  try {
    const tabs = await chrome.tabs.query({});
    if (chrome.runtime.lastError) {
      throw new Error(chrome.runtime.lastError.message || 'Unknown error accessing tabs');
    }
    
    const tabsInfo = tabs.map(tab => ({
      id: tab.id,
      url: tab.url,
      title: tab.title,
      active: tab.active,
      windowId: tab.windowId,
      timestamp: Date.now()
    }));
    
    return tabsInfo;
  } catch (error) {
    debugLog('Error getting tabs:', error);
    // Send error to popup for user feedback
    chrome.runtime.sendMessage({
      type: 'error',
      message: 'Failed to get tabs: ' + (error.message || 'Unknown error')
    });
    return [];
  }
}

/**
 * Check if the FocusGuard server is reachable
 */
async function checkServerConnection() {
  try {
    debugLog('Checking server connection...');
    const response = await fetch(config.statusEndpoint, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      cache: 'no-store'
    });

    if (!response.ok) {
      throw new Error(`Server returned status: ${response.status}`);
    }

    const data = await response.json();
    debugLog('Server status:', data);
    return { connected: true, data };
  } catch (error) {
    debugLog('Server connection error:', error);
    return { 
      connected: false, 
      error: error.message,
      timestamp: Date.now()
    };
  }
}

/**
 * Send tab data to FocusGuard with retry logic
 */
async function sendTabsToFocusGuard(tabs, retryCount = 0) {
  if (!tabs || !Array.isArray(tabs)) {
    debugLog('Invalid tabs data received');
    return { success: false, error: 'Invalid tabs data' };
  }

  const browserInfo = getBrowserInfo();
  const tabData = {
    browser: browserInfo,
    tabs: tabs,
    timestamp: Date.now(),
    extensionVersion: chrome.runtime.getManifest().version
  };

  try {
    debugLog(`Sending ${tabs.length} tabs to FocusGuard (attempt ${retryCount + 1}/${config.maxRetries})`);
    
    const response = await fetch(config.apiEndpoint, {
      method: 'POST',
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Extension-Version': chrome.runtime.getManifest().version
      },
      body: JSON.stringify(tabData),
      credentials: 'same-origin',
      cache: 'no-store',
      referrerPolicy: 'no-referrer'
    });
    
    const responseData = await response.json();
    
    if (!response.ok) {
      throw new Error(`Server error: ${response.status} - ${JSON.stringify(responseData)}`);
    }
    
    debugLog('Successfully sent tab data:', responseData);
    return { success: true, data: responseData };
  } catch (error) {
    debugLog(`Error sending tab data (attempt ${retryCount + 1}):`, error);
    
    if (retryCount < config.maxRetries - 1) {
      debugLog(`Retrying in ${config.retryDelay}ms...`);
      await new Promise(resolve => setTimeout(resolve, config.retryDelay));
      return sendTabsToFocusGuard(tabs, retryCount + 1);
    }
    
    return { 
      success: false, 
      error: error.message,
      lastAttempt: Date.now(),
      tabCount: tabs.length
    };
  }
}

/**
 * Get browser information
 */
function getBrowserInfo() {
  const userAgent = navigator.userAgent;
  let browser = 'unknown';
  
  if (userAgent.includes('Edg')) {
    browser = 'edge';
  } else if (userAgent.includes('Chrome')) {
    browser = 'chrome';
  } else if (userAgent.includes('Firefox')) {
    browser = 'firefox';
  } else if (userAgent.includes('Safari')) {
    browser = 'safari';
  }
  
  return {
    name: browser,
    userAgent: userAgent,
    version: navigator.appVersion
  };
}

function updateExtensionIcon(connected) {
  try {
    const iconPath = connected ? {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    } : {
      "16": "icons/icon16_gray.png",
      "48": "icons/icon48_gray.png",
      "128": "icons/icon128_gray.png"
    };
    
    // First try to set the icon with the full path
    chrome.browserAction.setIcon({ path: iconPath }, () => {
      if (chrome.runtime.lastError) {
        console.warn('Error setting icon:', chrome.runtime.lastError);
        
        // Fallback to just the active icon if there's an error
        if (connected) {
          chrome.browserAction.setIcon({
            path: {
              "16": "icons/icon16.png"
            }
          });
        }
      }
    });
  } catch (error) {
    console.error('Error in updateExtensionIcon:', error);
  }
}

/**
 * Update tab information and send to FocusGuard
 */
async function updateTabs() {
  try {
    // First check server connection
    const serverStatus = await checkServerConnection();
    
    if (!serverStatus.connected) {
      debugLog('Cannot update tabs: Server not reachable', serverStatus.error);
      // Update extension icon to show error state
      updateExtensionIcon(false);
      return;
    }

    // Get current tabs
    const tabs = await getAllTabs();
    debugLog(`Found ${tabs.length} tabs to send`);
    
    // Send tabs to server
    const result = await sendTabsToFocusGuard(tabs);
    
    // Update extension icon based on result
    updateExtensionIcon(result.success);
    
    // Log the result
    if (result.success) {
      debugLog('Successfully updated tabs:', result.data);
    } else {
      debugLog('Failed to update tabs after retries:', result.error);
    }
    
    return result;
  } catch (error) {
    debugLog('Unexpected error in updateTabs:', error);
    updateExtensionIcon(false);
    return { success: false, error: error.message };
  }
}

/**
 * Start periodic updates
 */
function startUpdates() {
  if (updateTimer) {
    clearInterval(updateTimer);
  }
  
  // Initial update
  updateTabs();
  
  // Set up periodic updates
  updateTimer = setInterval(updateTabs, config.updateInterval);
  debugLog('Started tab tracking');
}

/**
 * Stop periodic updates
 */
function stopUpdates() {
  if (updateTimer) {
    clearInterval(updateTimer);
    updateTimer = null;
    debugLog('Stopped tab tracking');
  }
}

/**
 * Initialize the extension
 */
function initialize() {
  debugLog('Initializing FocusGuard Tab Tracker');
  
  // Set up keep-alive mechanism
  keepAliveInterval = setInterval(() => {
    debugLog('Keep-alive ping');
  }, 25000); // 25 seconds (less than 30s to prevent service worker termination)
  
  // Handle messages from popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'getStatus') {
      checkServerConnection().then(status => sendResponse(status));
      return true; // Required for async response
    }
  });
  
  // Load configuration from storage
  chrome.storage.sync.get({
    apiEndpoint: config.apiEndpoint,
    updateInterval: config.updateInterval,
    debug: config.debug
  }, (items) => {
    if (items.apiEndpoint) config.apiEndpoint = items.apiEndpoint;
    if (items.updateInterval) config.updateInterval = parseInt(items.updateInterval, 10) || 5000;
    if (items.debug !== undefined) config.debug = !!items.debug;
    
    debugLog('Starting with config:', {
      apiEndpoint: config.apiEndpoint,
      updateInterval: config.updateInterval,
      debug: config.debug
    });
    
    startUpdates();
  });
  
  // Listen for tab events
  chrome.tabs.onCreated.addListener(() => {
    debugLog('Tab created');
    updateTabs();
  });
  
  chrome.tabs.onRemoved.addListener(() => {
    debugLog('Tab removed');
    updateTabs();
  });
  
  chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' || changeInfo.title) {
      debugLog('Tab updated:', tabId, changeInfo);
      updateTabs();
    }
  });
  
  chrome.tabs.onActivated.addListener(() => {
    debugLog('Tab activated');
    updateTabs();
  });
}

// Initialize when the extension loads
initialize();
