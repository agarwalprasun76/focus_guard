// FocusGuard Extension Popup Script

const CONFIG = {
  serverUrl: 'http://127.0.0.1:58392',
  statusEndpoint: '/api/status',
  healthEndpoint: '/api/health',
  timeout: 3000
};

// DOM Elements
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const browserName = document.getElementById('browser-name');
const tabsCount = document.getElementById('tabs-count');
const errorContainer = document.getElementById('error-container');
const errorText = document.getElementById('error-text');
const refreshBtn = document.getElementById('refresh-btn');

// Detect browser
function detectBrowser() {
  const ua = navigator.userAgent;
  if (ua.includes('Edg')) return 'Microsoft Edge';
  if (ua.includes('Chrome')) return 'Google Chrome';
  if (ua.includes('Firefox')) return 'Firefox';
  return 'Unknown Browser';
}

// Update UI with status
function updateUI(connected, data = null, error = null) {
  if (connected && data) {
    statusDot.className = 'status-dot connected';
    statusText.textContent = 'Connected';
    
    // Find tab count
    const totalTabs = data.total_tabs || 0;
    tabsCount.textContent = totalTabs;
    
    errorContainer.style.display = 'none';
  } else {
    statusDot.className = 'status-dot disconnected';
    statusText.textContent = 'Disconnected';
    tabsCount.textContent = '-';
    
    if (error) {
      errorContainer.style.display = 'block';
      errorText.textContent = error;
    }
  }
  
  browserName.textContent = detectBrowser();
}

// Check connection status
async function checkStatus() {
  statusText.textContent = 'Checking...';
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.timeout);
    
    const response = await fetch(`${CONFIG.serverUrl}${CONFIG.statusEndpoint}`, {
      signal: controller.signal,
      headers: {
        'Cache-Control': 'no-cache'
      }
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }
    
    const data = await response.json();
    
    // Check if this browser is in connected list
    const browser = detectBrowser().toLowerCase();
    const connectedBrowsers = data.connected_browsers || [];
    const isConnected = connectedBrowsers.some(b => 
      b.connected && (
        b.browser.toLowerCase().includes('chrome') && browser.includes('chrome') ||
        b.browser.toLowerCase().includes('edge') && browser.includes('edge')
      )
    );
    
    updateUI(true, data);
    
  } catch (err) {
    console.error('Status check failed:', err);
    
    let errorMessage = 'Cannot connect to FocusGuard';
    if (err.name === 'AbortError') {
      errorMessage = 'Connection timed out. Is FocusGuard running?';
    } else if (err.message.includes('Failed to fetch')) {
      errorMessage = 'FocusGuard app not running. Please start the application.';
    }
    
    updateUI(false, null, errorMessage);
  }
}

// Get tab count from extension
async function getTabCount() {
  return new Promise((resolve) => {
    chrome.tabs.query({}, (tabs) => {
      resolve(tabs ? tabs.length : 0);
    });
  });
}

// Initialize popup
async function init() {
  browserName.textContent = detectBrowser();
  
  // Get local tab count as fallback
  const localTabCount = await getTabCount();
  tabsCount.textContent = localTabCount;
  
  // Check server status
  await checkStatus();
}

// Event listeners
refreshBtn.addEventListener('click', checkStatus);

// Initialize on load
document.addEventListener('DOMContentLoaded', init);
