/**
 * FocusGuard Tab Tracker - Popup Script
 * 
 * This script handles the popup UI for the extension.
 */

// DOM elements
const statusElement = document.getElementById('status');
const tabsCountElement = document.getElementById('tabsCount');
const apiEndpointInput = document.getElementById('apiEndpoint');
const updateIntervalInput = document.getElementById('updateInterval');
const debugModeCheckbox = document.getElementById('debugMode');
const saveSettingsButton = document.getElementById('saveSettings');
const lastUpdatedElement = document.createElement('div');
lastUpdatedElement.className = 'last-updated';
document.querySelector('.tabs-count').appendChild(lastUpdatedElement);

// Default settings
const defaultSettings = {
  apiEndpoint: 'http://localhost:5000/api/tabs',
  updateInterval: 5000,
  debug: true
};

// Connection state
let connectionState = {
  connected: false,
  lastError: null,
  lastUpdate: null
};

/**
 * Update the connection status display
 */
async function updateConnectionStatus() {
  try {
    // Show loading state
    statusElement.className = 'status';
    statusElement.textContent = 'Checking connection...';
    
    // Get the current settings
    const settings = await chrome.storage.sync.get(['apiEndpoint']);
    const apiEndpoint = settings.apiEndpoint || defaultSettings.apiEndpoint;
    
    // Try to connect to the API
    const response = await fetch(apiEndpoint.replace('/tabs', '/status'), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      credentials: 'same-origin',
      cache: 'no-store'
    });
    
    const data = await response.json();
    
    if (response.ok && data && data.status === 'ok') {
      connectionState.connected = true;
      connectionState.lastError = null;
      statusElement.className = 'status connected';
      statusElement.textContent = `Connected to FocusGuard ${data.version || ''}`.trim();
      updateLastUpdated();
    } else {
      throw new Error(data?.error || 'Invalid response from server');
    }
  } catch (error) {
    connectionState.connected = false;
    connectionState.lastError = error.message;
    statusElement.className = 'status disconnected';
    statusElement.textContent = `Connection Error: ${error.message || 'Unknown error'}`;
    console.error('Connection error:', error);
  }
}

/**
 * Update the tabs count display
 */
async function updateTabsCount() {
  try {
    const tabs = await chrome.tabs.query({});
    if (chrome.runtime.lastError) {
      throw new Error(chrome.runtime.lastError.message || 'Error accessing tabs');
    }
    
    tabsCountElement.textContent = tabs.length;
    updateLastUpdated();
  } catch (error) {
    console.error('Error getting tabs count:', error);
    tabsCountElement.textContent = '?';
    showError(error.message || 'Failed to get tab count');
  }
}

/**
 * Update the last updated timestamp
 */
function updateLastUpdated() {
  const now = new Date();
  connectionState.lastUpdate = now;
  lastUpdatedElement.textContent = `Last updated: ${now.toLocaleTimeString()}`;
}

/**
 * Show error message to user
 */
function showError(message) {
  const errorElement = document.createElement('div');
  errorElement.className = 'error-message';
  errorElement.textContent = message;
  
  // Remove any existing error messages
  document.querySelectorAll('.error-message').forEach(el => el.remove());
  
  // Add the new error message
  statusElement.after(errorElement);
  
  // Auto-remove after 5 seconds
  setTimeout(() => {
    errorElement.remove();
  }, 5000);
}

/**
 * Load settings from storage
 */
async function loadSettings() {
  try {
    const settings = await chrome.storage.sync.get([
      'apiEndpoint',
      'updateInterval',
      'debug'
    ]);
    
    apiEndpointInput.value = settings.apiEndpoint || defaultSettings.apiEndpoint;
    updateIntervalInput.value = settings.updateInterval || defaultSettings.updateInterval;
    debugModeCheckbox.checked = settings.debug !== undefined ? settings.debug : defaultSettings.debug;
  } catch (error) {
    console.error('Error loading settings:', error);
    
    // Use defaults
    apiEndpointInput.value = defaultSettings.apiEndpoint;
    updateIntervalInput.value = defaultSettings.updateInterval;
    debugModeCheckbox.checked = defaultSettings.debug;
  }
}

/**
 * Save settings to storage
 */
async function saveSettings() {
  try {
    const settings = {
      apiEndpoint: apiEndpointInput.value,
      updateInterval: parseInt(updateIntervalInput.value, 10),
      debug: debugModeCheckbox.checked
    };
    
    await chrome.storage.sync.set(settings);
    
    // Notify the background script that settings have changed
    chrome.runtime.sendMessage({ type: 'settingsUpdated', settings });
    
    // Update status
    statusElement.textContent = 'Settings saved!';
    setTimeout(() => {
      updateConnectionStatus();
    }, 1500);
  } catch (error) {
    console.error('Error saving settings:', error);
    statusElement.className = 'status disconnected';
    statusElement.textContent = 'Error saving settings';
  }
}

// Event listeners
saveSettingsButton.addEventListener('click', saveSettings);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'error') {
      showError(message.message);
    } else if (message.type === 'status') {
      updateConnectionStatus();
    }
  });

  // Request status update from background script
  function requestStatusUpdate() {
    chrome.runtime.sendMessage({ type: 'getStatus' }, (response) => {
      if (chrome.runtime.lastError) {
        console.error('Error getting status:', chrome.runtime.lastError);
        return;
      }
      if (response) {
        updateConnectionStatus();
      }
    });
  }

  // Initialize
  async function init() {
    await loadSettings();
    updateTabsCount();
    requestStatusUpdate();
    
    // Set up periodic refresh
    setInterval(() => {
      updateTabsCount();
      requestStatusUpdate();
    }, 30000); // Every 30 seconds
  }

  // Start the extension
  init();
});
