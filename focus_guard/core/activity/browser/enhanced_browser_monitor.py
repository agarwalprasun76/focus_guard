"""
Enhanced Browser Monitor for Phase 3: Browser Integration with Application Blocking

This module provides enhanced browser monitoring that integrates with the Phase 2 blocking system
to provide tab-level control, domain blocking, and URL pattern matching.
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import urlparse
import fnmatch

from focus_guard.core.activity.models import WindowInfo
from focus_guard.core.activity.blocking.models import BlockingPolicy, BlockingAction, BlockingDecision
from focus_guard.core.activity.blocking.blocking_system import BlockingSystem
from focus_guard.core.browser.integration.browser_integration import BrowserIntegration
from focus_guard.core.browser.integration.tab_blocker import BrowserTabBlocker
from focus_guard.core.browser.models.tab import Tab

logger = logging.getLogger(__name__)


class TabBlockingDecision:
    """Decision for tab-level blocking actions."""
    
    def __init__(self, action: BlockingAction, policy_name: str = None, reason: str = None, 
                 grace_period: int = 0, tab: Tab = None):
        self.action = action
        self.policy_name = policy_name
        self.reason = reason
        self.grace_period = grace_period
        self.tab = tab
        self.timestamp = datetime.now()
    
    def should_block(self) -> bool:
        """Check if the tab should be blocked."""
        return self.action == BlockingAction.BLOCK
    
    def should_warn(self) -> bool:
        """Check if the tab should trigger a warning."""
        return self.action == BlockingAction.WARN
    
    def should_redirect(self) -> bool:
        """Check if the tab should be redirected."""
        return self.action == BlockingAction.REDIRECT


class EnhancedBrowserMonitor:
    """
    Enhanced browser monitor that integrates browser tab monitoring with application blocking.
    
    This class combines Phase 1 (activity monitoring), Phase 2 (application blocking),
    and Phase 3 (browser integration) to provide comprehensive browser-level control.
    """
    
    def __init__(self, blocking_system: BlockingSystem, browser_integration: BrowserIntegration = None,
                 tab_blocker: BrowserTabBlocker = None, polling_interval: float = 2.0):
        """
        Initialize the enhanced browser monitor.
        
        Args:
            blocking_system: Phase 2 blocking system for policy evaluation
            browser_integration: Browser integration for tab monitoring
            tab_blocker: Tab blocker for closing/blocking tabs
            polling_interval: Interval for polling browser tabs
        """
        self.blocking_system = blocking_system
        self.browser_integration = browser_integration or BrowserIntegration()
        self.tab_blocker = tab_blocker or BrowserTabBlocker()
        self.polling_interval = polling_interval
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread = None
        self._stop_event = threading.Event()
        
        # Tab tracking
        self._active_tabs: Dict[str, Tab] = {}
        self._blocked_tabs: Dict[str, TabBlockingDecision] = {}
        self._warning_counts: Dict[str, int] = {}
        
        # Event callbacks
        self._tab_opened_callbacks: List[Callable[[Tab], None]] = []
        self._tab_closed_callbacks: List[Callable[[Tab], None]] = []
        self._tab_blocked_callbacks: List[Callable[[Tab, TabBlockingDecision], None]] = []
        self._tab_warned_callbacks: List[Callable[[Tab, TabBlockingDecision], None]] = []
        
        # Statistics
        self.stats = {
            'tabs_monitored': 0,
            'tabs_blocked': 0,
            'tabs_warned': 0,
            'domains_blocked': set(),
            'policies_triggered': {},
            'last_update': None
        }
        
        # URL pattern matching cache
        self._pattern_cache: Dict[str, Dict[str, bool]] = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_cleanup = time.time()
    
    def start_monitoring(self):
        """Start enhanced browser monitoring."""
        if self._monitoring:
            logger.warning("Enhanced browser monitor is already running")
            return
        
        logger.info("Starting enhanced browser monitoring")
        self._monitoring = True
        self._stop_event.clear()
        
        # Start the monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("Enhanced browser monitoring started")
    
    def stop_monitoring(self):
        """Stop enhanced browser monitoring."""
        if not self._monitoring:
            return
        
        logger.info("Stopping enhanced browser monitoring")
        self._monitoring = False
        self._stop_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        
        logger.info("Enhanced browser monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop for browser tabs."""
        logger.info("Enhanced browser monitor loop started")
        
        while self._monitoring and not self._stop_event.is_set():
            try:
                # Get current tabs from browser integration
                current_tabs = self._get_current_tabs()
                
                # Process tab changes
                self._process_tab_changes(current_tabs)
                
                # Evaluate blocking policies for active tabs
                self._evaluate_tab_policies(current_tabs)
                
                # Clean up expired blocks and warnings
                self._cleanup_expired_decisions()
                
                # Clean up pattern cache periodically
                self._cleanup_pattern_cache()
                
                # Update statistics
                self.stats['last_update'] = datetime.now()
                
            except Exception as e:
                logger.error(f"Error in browser monitor loop: {e}")
            
            # Wait for next polling interval
            self._stop_event.wait(self.polling_interval)
        
        logger.info("Enhanced browser monitor loop stopped")
    
    def _get_current_tabs(self) -> List[Tab]:
        """Get current browser tabs from browser integration."""
        try:
            return self.browser_integration.get_all_tabs()
        except Exception as e:
            logger.error(f"Error getting browser tabs: {e}")
            return []
    
    def _process_tab_changes(self, current_tabs: List[Tab]):
        """Process tab open/close events."""
        current_tab_ids = {tab.id for tab in current_tabs}
        previous_tab_ids = set(self._active_tabs.keys())
        
        # Detect new tabs (opened)
        new_tab_ids = current_tab_ids - previous_tab_ids
        for tab in current_tabs:
            if tab.id in new_tab_ids:
                self._on_tab_opened(tab)
        
        # Detect closed tabs
        closed_tab_ids = previous_tab_ids - current_tab_ids
        for tab_id in closed_tab_ids:
            if tab_id in self._active_tabs:
                self._on_tab_closed(self._active_tabs[tab_id])
        
        # Update active tabs
        self._active_tabs = {tab.id: tab for tab in current_tabs}
        self.stats['tabs_monitored'] = len(self._active_tabs)
    
    def _on_tab_opened(self, tab: Tab):
        """Handle tab opened event."""
        logger.debug(f"Tab opened: {tab.url}")
        
        # Notify callbacks
        for callback in self._tab_opened_callbacks:
            try:
                callback(tab)
            except Exception as e:
                logger.error(f"Error in tab opened callback: {e}")
    
    def _on_tab_closed(self, tab: Tab):
        """Handle tab closed event."""
        logger.debug(f"Tab closed: {tab.url}")
        
        # Clean up tracking data
        if tab.id in self._blocked_tabs:
            del self._blocked_tabs[tab.id]
        
        # Notify callbacks
        for callback in self._tab_closed_callbacks:
            try:
                callback(tab)
            except Exception as e:
                logger.error(f"Error in tab closed callback: {e}")
    
    def _evaluate_tab_policies(self, tabs: List[Tab]):
        """Evaluate blocking policies for all active tabs."""
        for tab in tabs:
            try:
                # Skip if tab is already blocked
                if tab.id in self._blocked_tabs:
                    continue
                
                # Create window info for policy evaluation
                window_info = self._tab_to_window_info(tab)
                
                # Evaluate against blocking policies
                decision = self._evaluate_tab_blocking(tab, window_info)
                
                # Take action based on decision
                if decision.should_block():
                    self._block_tab(tab, decision)
                elif decision.should_warn():
                    self._warn_tab(tab, decision)
                
            except Exception as e:
                logger.error(f"Error evaluating tab policy for {tab.url}: {e}")
    
    def _tab_to_window_info(self, tab: Tab) -> WindowInfo:
        """Convert tab to window info for policy evaluation."""
        return WindowInfo(
            app_name=tab.browser_id or "browser",
            window_title=tab.title or "",
            pid=str(tab.window_id) if tab.window_id else "0",
            url=tab.url,
            domain=tab.domain,
            timestamp=datetime.now()
        )
    
    def _evaluate_tab_blocking(self, tab: Tab, window_info: WindowInfo) -> TabBlockingDecision:
        """Evaluate if a tab should be blocked based on policies."""
        # First check application-level policies
        app_decision = self.blocking_system.evaluate_application(window_info)
        
        # Then check domain/URL specific policies
        domain_decision = self._evaluate_domain_policies(tab)
        
        # Combine decisions (domain takes precedence)
        if domain_decision.should_block() or app_decision.should_block():
            action = BlockingAction.BLOCK
            policy_name = domain_decision.policy_name or app_decision.policy_name
            reason = domain_decision.reason or app_decision.reason
            grace_period = max(
                getattr(domain_decision, 'grace_period', 0),
                getattr(app_decision, 'grace_period_seconds', 0)
            )
        elif domain_decision.should_warn() or app_decision.should_warn():
            action = BlockingAction.WARN
            policy_name = domain_decision.policy_name or app_decision.policy_name
            reason = domain_decision.reason or app_decision.reason
            grace_period = 0
        else:
            action = BlockingAction.ALLOW
            policy_name = None
            reason = None
            grace_period = 0
        
        # Convert to TabBlockingDecision
        return TabBlockingDecision(
            action=action,
            policy_name=policy_name,
            reason=reason,
            grace_period=grace_period,
            tab=tab
        )
    
    def _evaluate_domain_policies(self, tab: Tab) -> TabBlockingDecision:
        """Evaluate domain-specific policies for a tab."""
        if not tab.domain or not tab.url:
            return TabBlockingDecision(BlockingAction.ALLOW)
        
        # Get all policies from blocking system
        policies = self.blocking_system.list_policies()
        
        for policy in policies:
            # Check if policy matches the domain
            if policy.matches_domain(tab.domain):
                return TabBlockingDecision(
                    action=policy.action,
                    policy_name=policy.name,
                    reason=policy.warning_message or f"Domain {tab.domain} is blocked by policy {policy.name}",
                    grace_period=getattr(policy, 'grace_period_seconds', 0),
                    tab=tab
                )
        
        return TabBlockingDecision(BlockingAction.ALLOW)
    
    def _matches_domain_patterns(self, domain: str, patterns: List[str]) -> bool:
        """Check if domain matches any of the given patterns."""
        if not domain or not patterns:
            return False
        
        domain_lower = domain.lower()
        
        # Check cache first
        cache_key = f"domain:{domain_lower}"
        if cache_key in self._pattern_cache:
            for pattern in patterns:
                if pattern in self._pattern_cache[cache_key]:
                    return self._pattern_cache[cache_key][pattern]
        else:
            self._pattern_cache[cache_key] = {}
        
        # Evaluate patterns
        for pattern in patterns:
            pattern_lower = pattern.lower()
            
            # Exact match
            if domain_lower == pattern_lower:
                self._pattern_cache[cache_key][pattern] = True
                return True
            
            # Subdomain match (e.g., *.facebook.com matches www.facebook.com)
            if pattern_lower.startswith('*.'):
                base_domain = pattern_lower[2:]
                if domain_lower == base_domain or domain_lower.endswith('.' + base_domain):
                    self._pattern_cache[cache_key][pattern] = True
                    return True
            
            # Wildcard pattern matching
            if fnmatch.fnmatch(domain_lower, pattern_lower):
                self._pattern_cache[cache_key][pattern] = True
                return True
            
            # Cache negative result
            self._pattern_cache[cache_key][pattern] = False
        
        return False
    
    def _matches_url_patterns(self, url: str, patterns: List[str]) -> bool:
        """Check if URL matches any of the given patterns."""
        if not url or not patterns:
            return False
        
        url_lower = url.lower()
        
        # Check cache first
        cache_key = f"url:{url_lower}"
        if cache_key in self._pattern_cache:
            for pattern in patterns:
                if pattern in self._pattern_cache[cache_key]:
                    return self._pattern_cache[cache_key][pattern]
        else:
            self._pattern_cache[cache_key] = {}
        
        # Evaluate patterns
        for pattern in patterns:
            pattern_lower = pattern.lower()
            
            # Simple substring match
            if pattern_lower in url_lower:
                self._pattern_cache[cache_key][pattern] = True
                return True
            
            # Wildcard pattern matching
            if fnmatch.fnmatch(url_lower, pattern_lower):
                self._pattern_cache[cache_key][pattern] = True
                return True
            
            # Cache negative result
            self._pattern_cache[cache_key][pattern] = False
        
        return False
    
    def _block_tab(self, tab: Tab, decision: TabBlockingDecision):
        """Block a tab based on blocking decision."""
        logger.info(f"Blocking tab: {tab.url} (Policy: {decision.policy_name}, Reason: {decision.reason})")
        
        # Record the blocking decision
        self._blocked_tabs[tab.id] = decision
        
        # Update statistics
        self.stats['tabs_blocked'] += 1
        if tab.domain:
            self.stats['domains_blocked'].add(tab.domain)
        if decision.policy_name:
            self.stats['policies_triggered'][decision.policy_name] = \
                self.stats['policies_triggered'].get(decision.policy_name, 0) + 1
        
        # Close the tab
        success = self.tab_blocker.close_tab(tab, decision.reason)
        
        if success:
            logger.info(f"Successfully blocked tab: {tab.url}")
        else:
            logger.warning(f"Failed to block tab: {tab.url}")
        
        # Notify callbacks
        for callback in self._tab_blocked_callbacks:
            try:
                callback(tab, decision)
            except Exception as e:
                logger.error(f"Error in tab blocked callback: {e}")
    
    def _warn_tab(self, tab: Tab, decision: TabBlockingDecision):
        """Issue a warning for a tab based on blocking decision."""
        logger.info(f"Warning for tab: {tab.url} (Policy: {decision.policy_name}, Reason: {decision.reason})")
        
        # Track warning count
        tab_key = f"{tab.domain}:{tab.url}"
        self._warning_counts[tab_key] = self._warning_counts.get(tab_key, 0) + 1
        
        # Update statistics
        self.stats['tabs_warned'] += 1
        if decision.policy_name:
            self.stats['policies_triggered'][decision.policy_name] = \
                self.stats['policies_triggered'].get(decision.policy_name, 0) + 1
        
        # Notify callbacks
        for callback in self._tab_warned_callbacks:
            try:
                callback(tab, decision)
            except Exception as e:
                logger.error(f"Error in tab warned callback: {e}")
    
    def _cleanup_expired_decisions(self):
        """Clean up expired blocking decisions."""
        current_time = time.time()
        expired_tabs = []
        
        for tab_id, decision in self._blocked_tabs.items():
            # Check if grace period has expired (if applicable)
            if decision.grace_period > 0:
                decision_time = decision.timestamp.timestamp()
                if current_time - decision_time > decision.grace_period:
                    expired_tabs.append(tab_id)
        
        for tab_id in expired_tabs:
            del self._blocked_tabs[tab_id]
    
    def _cleanup_pattern_cache(self):
        """Clean up pattern matching cache periodically."""
        current_time = time.time()
        if current_time - self._last_cache_cleanup > self._cache_ttl:
            self._pattern_cache.clear()
            self._last_cache_cleanup = current_time
            logger.debug("Pattern cache cleaned up")
    
    # Event callback management
    def add_tab_opened_callback(self, callback: Callable[[Tab], None]):
        """Add callback for tab opened events."""
        self._tab_opened_callbacks.append(callback)
    
    def add_tab_closed_callback(self, callback: Callable[[Tab], None]):
        """Add callback for tab closed events."""
        self._tab_closed_callbacks.append(callback)
    
    def add_tab_blocked_callback(self, callback: Callable[[Tab, TabBlockingDecision], None]):
        """Add callback for tab blocked events."""
        self._tab_blocked_callbacks.append(callback)
    
    def add_tab_warned_callback(self, callback: Callable[[Tab, TabBlockingDecision], None]):
        """Add callback for tab warned events."""
        self._tab_warned_callbacks.append(callback)
    
    # Status and statistics
    def is_monitoring(self) -> bool:
        """Check if browser monitoring is active."""
        return self._monitoring
    
    def get_active_tabs(self) -> List[Tab]:
        """Get list of currently active tabs."""
        return list(self._active_tabs.values())
    
    def get_blocked_tabs(self) -> Dict[str, TabBlockingDecision]:
        """Get currently blocked tabs."""
        return self._blocked_tabs.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive browser monitoring statistics."""
        return {
            **self.stats,
            'domains_blocked': list(self.stats['domains_blocked']),
            'active_tabs_count': len(self._active_tabs),
            'blocked_tabs_count': len(self._blocked_tabs),
            'warning_counts': dict(self._warning_counts),
            'monitoring_active': self._monitoring
        }
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the enhanced browser monitor."""
        return {
            'monitoring': {
                'active': self._monitoring,
                'polling_interval': self.polling_interval,
                'thread_alive': self._monitor_thread.is_alive() if self._monitor_thread else False
            },
            'tabs': {
                'active_count': len(self._active_tabs),
                'blocked_count': len(self._blocked_tabs),
                'active_tabs': [
                    {
                        'id': tab.id,
                        'url': tab.url,
                        'domain': tab.domain,
                        'title': tab.title,
                        'browser': tab.browser
                    }
                    for tab in self._active_tabs.values()
                ]
            },
            'blocking': {
                'blocked_tabs': [
                    {
                        'tab_id': tab_id,
                        'policy': decision.policy_name,
                        'reason': decision.reason,
                        'timestamp': decision.timestamp.isoformat()
                    }
                    for tab_id, decision in self._blocked_tabs.items()
                ]
            },
            'statistics': self.get_statistics(),
            'integration': {
                'browser_integration_active': hasattr(self.browser_integration, 'is_running') and 
                                            self.browser_integration.is_running(),
                'blocking_system_active': self.blocking_system.is_active(),
                'policies_count': len(self.blocking_system.list_policies())
            }
        }
