# Browser Extension Upgrade Plan - Week 4: Communication Reliability

## Overview

Week 4 focuses on enhancing the reliability of communication between the browser extension and the Focus Guard application. After improving test coverage in Week 3, this phase implements health checks, reconnection strategies, and evaluates WebSocket as an alternative to HTTP polling for more reliable and efficient communication.

## Detailed Tasks

### Task 4.1: Implement Health Checks

**Priority**: P0 - Critical  
**Effort**: 2 days  
**Owner**: TBD

#### Description
Implement comprehensive health check mechanisms for the tab server and browser extension to detect communication issues early and provide accurate status information.

#### Steps
1. **Design health check framework**
   - Define health check interfaces
   - Create health check strategies
   - Implement health status reporting

2. **Implement tab server health checks**
   - Add health check endpoint
   - Implement server-side diagnostics
   - Add health metrics collection

3. **Implement extension health checks**
   - Add extension health check mechanism
   - Implement client-side diagnostics
   - Add extension status reporting

4. **Implement bidirectional health verification**
   - Verify tab server can reach extension
   - Verify extension can reach tab server
   - Implement round-trip time measurement

5. **Create health monitoring dashboard**
   - Implement health status visualization
   - Add historical health data
   - Create alerts for health issues

#### Code Examples

**Health Check Interface:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime

class HealthStatus(Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheckResult:
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    
    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

class HealthCheck(ABC):
    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """Perform health check and return result."""
        pass

class TabServerHealthCheck(HealthCheck):
    def __init__(self, tab_server):
        self.tab_server = tab_server
    
    async def check_health(self) -> HealthCheckResult:
        """Check tab server health."""
        try:
            # Check if server is running
            if not self.tab_server.is_running:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message="Tab server is not running",
                    timestamp=datetime.now()
                )
            
            # Check if server is accepting connections
            # ...
            
            # Check if server can process requests
            # ...
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="Tab server is healthy",
                timestamp=datetime.now(),
                details={
                    "uptime_seconds": self.tab_server.uptime_seconds,
                    "active_connections": len(self.tab_server.active_connections),
                    "tabs_count": len(self.tab_server.get_all_tabs())
                }
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now()
            )
```

**Tab Server Health Endpoint:**
```python
from aiohttp import web
import json

class TabServer:
    # ...
    
    async def setup_routes(self):
        """Set up HTTP routes for tab server."""
        # Existing routes
        # ...
        
        # Add health check route
        self.app.router.add_get('/health', self.handle_health_check)
    
    async def handle_health_check(self, request):
        """Handle health check request."""
        health_check = TabServerHealthCheck(self)
        result = await health_check.check_health()
        
        return web.json_response({
            "status": result.status.value,
            "message": result.message,
            "timestamp": result.timestamp.isoformat(),
            "details": result.details
        })
    
    @property
    def uptime_seconds(self):
        """Get server uptime in seconds."""
        if self._start_time is None:
            return 0
        return (datetime.now() - self._start_time).total_seconds()
```

**Extension Health Check:**
```javascript
// In extension background.js

// Health check configuration
const healthCheckConfig = {
  interval: 60000,  // Check every minute
  tabServerUrl: "http://localhost:8765/health",
  timeout: 5000     // 5 second timeout
};

// Health check function
async function performHealthCheck() {
  try {
    const startTime = Date.now();
    const response = await fetch(healthCheckConfig.tabServerUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: healthCheckConfig.timeout
    });
    
    const endTime = Date.now();
    const roundTripTime = endTime - startTime;
    
    if (!response.ok) {
      console.error(`Health check failed: ${response.status} ${response.statusText}`);
      updateExtensionStatus('unhealthy', `Server returned ${response.status}`);
      return false;
    }
    
    const data = await response.json();
    
    if (data.status !== 'healthy') {
      console.warn(`Server reports unhealthy status: ${data.message}`);
      updateExtensionStatus('degraded', data.message);
      return false;
    }
    
    updateExtensionStatus('healthy', `RTT: ${roundTripTime}ms`);
    return true;
  } catch (error) {
    console.error(`Health check error: ${error.message}`);
    updateExtensionStatus('unhealthy', error.message);
    return false;
  }
}

// Update extension status
function updateExtensionStatus(status, message) {
  chrome.storage.local.set({
    'healthStatus': {
      status: status,
      message: message,
      timestamp: new Date().toISOString()
    }
  });
  
  // Update extension icon based on status
  const iconPath = status === 'healthy' 
    ? 'icons/icon_healthy.png' 
    : status === 'degraded' 
      ? 'icons/icon_degraded.png' 
      : 'icons/icon_unhealthy.png';
  
  chrome.browserAction.setIcon({ path: iconPath });
}

// Start periodic health checks
setInterval(performHealthCheck, healthCheckConfig.interval);
performHealthCheck();  // Initial check
```

#### Acceptance Criteria
- [ ] Tab server health check endpoint
- [ ] Extension health check mechanism
- [ ] Bidirectional health verification
- [ ] Health status visualization
- [ ] Alerts for health issues
- [ ] Documentation of health check approach

#### Testing Strategy
- Unit tests for health check components
- Integration tests for health check system
- Tests for various health scenarios
- Verification of health status reporting

---

### Task 4.2: Implement Reconnection Strategies

**Priority**: P0 - Critical  
**Effort**: 2 days  
**Owner**: TBD

#### Description
Implement robust reconnection strategies for the browser extension and tab server to handle connection losses, browser restarts, and application restarts, ensuring continuous operation and data synchronization.

#### Steps
1. **Design reconnection framework**
   - Define reconnection interfaces
   - Create reconnection strategies
   - Implement reconnection event handling

2. **Implement extension reconnection**
   - Add connection state tracking
   - Implement exponential backoff retry
   - Add reconnection event handling

3. **Implement tab server reconnection**
   - Add connection tracking
   - Implement session recovery
   - Add reconnection event handling

4. **Implement data synchronization**
   - Add data versioning
   - Implement differential updates
   - Add conflict resolution

5. **Create reconnection monitoring**
   - Track reconnection attempts
   - Measure reconnection success rate
   - Alert on persistent connection issues

#### Code Examples

**Extension Reconnection Strategy:**
```javascript
// In extension background.js

// Reconnection configuration
const reconnectionConfig = {
  initialDelay: 1000,    // 1 second
  maxDelay: 60000,       // 1 minute
  backoffFactor: 2,      // Exponential backoff factor
  maxAttempts: 10,       // Maximum reconnection attempts
  resetAfter: 300000     // Reset attempt counter after 5 minutes of stability
};

// Connection state
let connectionState = {
  connected: false,
  lastConnected: null,
  reconnectAttempts: 0,
  reconnectTimer: null,
  lastStableConnection: null
};

// Connect to tab server
async function connectToTabServer() {
  try {
    const response = await fetch('http://localhost:8765/status', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 5000
    });
    
    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }
    
    // Connection successful
    connectionState.connected = true;
    connectionState.lastConnected = Date.now();
    
    // Reset reconnection attempts if connection has been stable
    if (connectionState.reconnectAttempts > 0) {
      console.log('Connection restored after', connectionState.reconnectAttempts, 'attempts');
    }
    
    // If connection is stable for resetAfter duration, reset attempt counter
    clearTimeout(connectionState.reconnectTimer);
    connectionState.reconnectTimer = setTimeout(() => {
      connectionState.reconnectAttempts = 0;
      connectionState.lastStableConnection = Date.now();
      console.log('Connection stable, reset reconnect attempts');
    }, reconnectionConfig.resetAfter);
    
    return true;
  } catch (error) {
    // Connection failed
    connectionState.connected = false;
    handleConnectionFailure(error);
    return false;
  }
}

// Handle connection failure
function handleConnectionFailure(error) {
  console.error('Connection to tab server failed:', error.message);
  
  // Increment reconnection attempts
  connectionState.reconnectAttempts++;
  
  if (connectionState.reconnectAttempts > reconnectionConfig.maxAttempts) {
    console.error('Maximum reconnection attempts reached');
    showReconnectionError('Unable to connect to Focus Guard. Please restart the application.');
    return;
  }
  
  // Calculate delay with exponential backoff
  const delay = Math.min(
    reconnectionConfig.initialDelay * Math.pow(reconnectionConfig.backoffFactor, connectionState.reconnectAttempts - 1),
    reconnectionConfig.maxDelay
  );
  
  console.log(`Reconnecting in ${delay}ms (attempt ${connectionState.reconnectAttempts}/${reconnectionConfig.maxAttempts})`);
  
  // Schedule reconnection attempt
  setTimeout(() => {
    connectToTabServer();
  }, delay);
}

// Show reconnection error to user
function showReconnectionError(message) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon_error.png',
    title: 'Focus Guard Connection Error',
    message: message,
    priority: 2
  });
}

// Initial connection
connectToTabServer();
```

**Tab Server Reconnection Handling:**
```python
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, Optional

logger = logging.getLogger(__name__)

class TabServer:
    # ...
    
    def __init__(self, port=8765):
        # Existing initialization
        # ...
        
        # Connection tracking
        self._active_connections: Set[str] = set()
        self._connection_history: Dict[str, Dict] = {}
        self._last_seen: Dict[str, datetime] = {}
    
    async def handle_extension_connect(self, request):
        """Handle extension connection request."""
        data = await request.json()
        extension_id = data.get('extension_id')
        browser_type = data.get('browser_type')
        
        if not extension_id or not browser_type:
            return web.json_response({
                'success': False,
                'error': 'Missing extension_id or browser_type'
            }, status=400)
        
        # Generate connection ID
        connection_id = f"{browser_type}:{extension_id}"
        
        # Track connection
        self._active_connections.add(connection_id)
        self._last_seen[connection_id] = datetime.now()
        
        # Record connection history
        if connection_id not in self._connection_history:
            self._connection_history[connection_id] = {
                'first_seen': datetime.now(),
                'connect_count': 1,
                'disconnect_count': 0
            }
        else:
            self._connection_history[connection_id]['connect_count'] += 1
        
        logger.info(f"Extension connected: {connection_id}")
        
        # Return session information
        return web.json_response({
            'success': True,
            'connection_id': connection_id,
            'server_time': datetime.now().isoformat(),
            'session_data': self._get_session_data(connection_id)
        })
    
    async def handle_extension_disconnect(self, request):
        """Handle extension disconnection request."""
        data = await request.json()
        connection_id = data.get('connection_id')
        
        if not connection_id:
            return web.json_response({
                'success': False,
                'error': 'Missing connection_id'
            }, status=400)
        
        # Remove from active connections
        if connection_id in self._active_connections:
            self._active_connections.remove(connection_id)
        
        # Update connection history
        if connection_id in self._connection_history:
            self._connection_history[connection_id]['disconnect_count'] += 1
        
        logger.info(f"Extension disconnected: {connection_id}")
        
        return web.json_response({'success': True})
    
    def _get_session_data(self, connection_id: str) -> Dict:
        """Get session data for reconnecting extension."""
        # Return relevant session data for the extension to restore state
        return {
            'tabs': self.get_all_tabs(),
            'pending_commands': self.get_pending_commands(connection_id.split(':')[0]),
            'last_sync_time': self._last_seen.get(connection_id, datetime.now()).isoformat()
        }
    
    async def _monitor_connections(self):
        """Monitor connections and detect disconnections."""
        while self.is_running:
            now = datetime.now()
            timeout_threshold = now - timedelta(minutes=5)
            
            # Check for timed out connections
            for connection_id in list(self._active_connections):
                last_seen = self._last_seen.get(connection_id)
                if last_seen and last_seen < timeout_threshold:
                    logger.warning(f"Connection timed out: {connection_id}")
                    self._active_connections.remove(connection_id)
                    
                    # Update connection history
                    if connection_id in self._connection_history:
                        self._connection_history[connection_id]['disconnect_count'] += 1
            
            await asyncio.sleep(60)  # Check every minute
```

#### Acceptance Criteria
- [ ] Extension reconnection strategy
- [ ] Tab server connection tracking
- [ ] Data synchronization after reconnection
- [ ] Reconnection monitoring and alerts
- [ ] 95%+ reconnection success rate
- [ ] Documentation of reconnection approach

#### Testing Strategy
- Unit tests for reconnection components
- Integration tests for reconnection scenarios
- Tests for various failure modes
- Verification of data synchronization after reconnection

---

### Task 4.3: Evaluate WebSocket Alternative

**Priority**: P1 - High  
**Effort**: 3 days  
**Owner**: TBD

#### Description
Evaluate and potentially implement WebSocket as an alternative to HTTP polling for communication between the browser extension and tab server, providing more efficient, real-time communication with lower latency and overhead.

#### Steps
1. **Research WebSocket implementation**
   - Evaluate WebSocket libraries
   - Assess browser compatibility
   - Analyze performance characteristics

2. **Design WebSocket architecture**
   - Define WebSocket protocol
   - Create message format
   - Design connection management

3. **Implement server-side WebSocket**
   - Add WebSocket endpoint to tab server
   - Implement message handling
   - Add connection management

4. **Implement client-side WebSocket**
   - Add WebSocket client to extension
   - Implement message handling
   - Add connection management

5. **Implement fallback mechanism**
   - Create HTTP fallback for WebSocket failures
   - Implement automatic protocol negotiation
   - Add seamless switching between protocols

#### Code Examples

**Server-Side WebSocket Implementation:**
```python
import asyncio
import json
import logging
from aiohttp import web, WSMsgType
from typing import Dict, Set, Optional

logger = logging.getLogger(__name__)

class TabServer:
    # ...
    
    async def setup_routes(self):
        """Set up HTTP routes for tab server."""
        # Existing routes
        # ...
        
        # Add WebSocket route
        self.app.router.add_get('/ws', self.handle_websocket)
    
    async def handle_websocket(self, request):
        """Handle WebSocket connection."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        connection_id = None
        
        try:
            # Handle initial connection message
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    message_type = data.get('type')
                    
                    if message_type == 'connect':
                        # Handle connection
                        extension_id = data.get('extension_id')
                        browser_type = data.get('browser_type')
                        
                        if not extension_id or not browser_type:
                            await ws.send_json({
                                'type': 'error',
                                'error': 'Missing extension_id or browser_type'
                            })
                            continue
                        
                        # Generate connection ID
                        connection_id = f"{browser_type}:{extension_id}"
                        
                        # Track connection
                        self._ws_connections[connection_id] = ws
                        self._last_seen[connection_id] = asyncio.get_event_loop().time()
                        
                        # Send connection acknowledgment
                        await ws.send_json({
                            'type': 'connected',
                            'connection_id': connection_id,
                            'server_time': asyncio.get_event_loop().time(),
                            'session_data': self._get_session_data(connection_id)
                        })
                        
                        logger.info(f"WebSocket connected: {connection_id}")
                    
                    elif message_type == 'tabs':
                        # Handle tab data
                        if not connection_id:
                            await ws.send_json({
                                'type': 'error',
                                'error': 'Not connected'
                            })
                            continue
                        
                        # Process tab data
                        tabs_data = data.get('tabs', [])
                        browser_type = connection_id.split(':')[0]
                        
                        self._process_tabs_data(tabs_data, browser_type)
                        
                        # Update last seen time
                        self._last_seen[connection_id] = asyncio.get_event_loop().time()
                        
                        # Send acknowledgment
                        await ws.send_json({
                            'type': 'tabs_received',
                            'count': len(tabs_data)
                        })
                    
                    elif message_type == 'ping':
                        # Handle ping
                        if connection_id:
                            self._last_seen[connection_id] = asyncio.get_event_loop().time()
                        
                        # Send pong
                        await ws.send_json({
                            'type': 'pong',
                            'server_time': asyncio.get_event_loop().time()
                        })
                    
                    # Handle other message types
                    # ...
                
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        
        finally:
            # Clean up connection
            if connection_id and connection_id in self._ws_connections:
                del self._ws_connections[connection_id]
                logger.info(f"WebSocket disconnected: {connection_id}")
        
        return ws
    
    async def send_command_to_extension(self, browser_type, command):
        """Send command to extension via WebSocket if available."""
        # Find all connections for the browser type
        connections = [
            conn_id for conn_id in self._ws_connections.keys()
            if conn_id.startswith(f"{browser_type}:")
        ]
        
        if not connections:
            logger.warning(f"No WebSocket connections for browser: {browser_type}")
            # Queue command for HTTP polling fallback
            self._queue_command(browser_type, command)
            return False
        
        # Send command to all matching connections
        success = False
        for conn_id in connections:
            ws = self._ws_connections.get(conn_id)
            if ws and not ws.closed:
                try:
                    await ws.send_json({
                        'type': 'command',
                        'command': command
                    })
                    success = True
                except Exception as e:
                    logger.error(f"Failed to send command via WebSocket: {str(e)}")
        
        # If WebSocket send failed, queue for HTTP polling fallback
        if not success:
            self._queue_command(browser_type, command)
        
        return success
```

**Client-Side WebSocket Implementation:**
```javascript
// In extension background.js

// WebSocket configuration
const wsConfig = {
  url: "ws://localhost:8765/ws",
  reconnectInterval: 5000,
  pingInterval: 30000
};

// WebSocket connection
let ws = null;
let wsReconnectTimer = null;
let wsPingTimer = null;

// Connect to WebSocket
function connectWebSocket() {
  // Clear any existing connection
  if (ws) {
    ws.close();
    ws = null;
  }
  
  // Clear timers
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = null;
  }
  
  if (wsPingTimer) {
    clearInterval(wsPingTimer);
    wsPingTimer = null;
  }
  
  // Create new WebSocket connection
  ws = new WebSocket(wsConfig.url);
  
  // Connection opened
  ws.addEventListener('open', (event) => {
    console.log('WebSocket connected');
    
    // Send connection message
    ws.send(JSON.stringify({
      type: 'connect',
      extension_id: chrome.runtime.id,
      browser_type: getBrowserType(),
      version: chrome.runtime.getManifest().version
    }));
    
    // Start ping interval
    wsPingTimer = setInterval(sendPing, wsConfig.pingInterval);
  });
  
  // Listen for messages
  ws.addEventListener('message', (event) => {
    try {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  });
  
  // Connection closed
  ws.addEventListener('close', (event) => {
    console.log('WebSocket disconnected, code:', event.code, 'reason:', event.reason);
    
    // Clear ping timer
    if (wsPingTimer) {
      clearInterval(wsPingTimer);
      wsPingTimer = null;
    }
    
    // Schedule reconnection
    wsReconnectTimer = setTimeout(() => {
      console.log('Attempting to reconnect WebSocket');
      connectWebSocket();
    }, wsConfig.reconnectInterval);
    
    // Fall back to HTTP polling
    startHttpPolling();
  });
  
  // Connection error
  ws.addEventListener('error', (event) => {
    console.error('WebSocket error:', event);
  });
}

// Send ping to keep connection alive
function sendPing() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'ping',
      timestamp: Date.now()
    }));
  }
}

// Handle WebSocket messages
function handleWebSocketMessage(message) {
  const messageType = message.type;
  
  switch (messageType) {
    case 'connected':
      console.log('WebSocket connection acknowledged:', message.connection_id);
      // Process session data
      if (message.session_data) {
        processSessionData(message.session_data);
      }
      break;
      
    case 'command':
      console.log('Received command:', message.command);
      executeCommand(message.command);
      break;
      
    case 'pong':
      // Received ping response
      const latency = Date.now() - message.client_time;
      console.debug('WebSocket ping latency:', latency, 'ms');
      break;
      
    case 'error':
      console.error('WebSocket error message:', message.error);
      break;
      
    default:
      console.warn('Unknown WebSocket message type:', messageType);
  }
}

// Send tabs data via WebSocket
function sendTabsDataWebSocket(tabsData) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'tabs',
      tabs: tabsData,
      timestamp: Date.now()
    }));
    return true;
  }
  
  // Fall back to HTTP if WebSocket is not available
  return false;
}

// Start connection
connectWebSocket();
```

#### Acceptance Criteria
- [ ] WebSocket implementation for tab server
- [ ] WebSocket implementation for extension
- [ ] HTTP fallback mechanism
- [ ] Performance comparison with HTTP polling
- [ ] Documentation of WebSocket implementation
- [ ] Decision on whether to adopt WebSocket as primary protocol

#### Testing Strategy
- Unit tests for WebSocket components
- Integration tests for WebSocket communication
- Performance tests comparing WebSocket vs. HTTP
- Tests for fallback mechanism
- Verification of protocol negotiation

---

## Dependencies and Prerequisites

- Completion of Week 1, Week 2, and Week 3 tasks
- Understanding of WebSocket protocol
- Knowledge of aiohttp WebSocket implementation
- Familiarity with browser extension WebSocket API

## Risks and Mitigations

### Risk: WebSocket Browser Compatibility
- **Probability**: Low
- **Impact**: Medium
- **Mitigation**: Implement HTTP fallback, test across browser versions

### Risk: Firewall/Proxy Issues
- **Probability**: Medium
- **Impact**: High
- **Mitigation**: Implement automatic protocol negotiation, robust fallback mechanism

### Risk: Connection Stability
- **Probability**: Medium
- **Impact**: High
- **Mitigation**: Implement reconnection strategies, health checks, and monitoring

## Deliverables

1. Health check implementation
2. Reconnection strategy implementation
3. WebSocket evaluation and potential implementation
4. Documentation of communication improvements
5. Performance metrics for different communication methods

## Success Criteria

- 99%+ uptime for tab server
- 95%+ reconnection success rate
- Reduced latency compared to HTTP polling
- Seamless recovery from connection losses
- Clear documentation of communication architecture

## Next Steps for Week 5

After completing Week 4, the team will be ready to implement user experience improvements in Week 5, including better installation feedback, troubleshooting guidance, and automation of manual steps.
