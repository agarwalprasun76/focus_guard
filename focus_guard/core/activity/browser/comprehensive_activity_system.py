"""
Comprehensive Activity System: Complete Activity Monitoring, Blocking, and Browser Control

This module provides a comprehensive activity management system that combines:
- Activity monitoring with idle detection and usage tracking
- Application blocking system with policy enforcement
- Enhanced browser integration with tab-level control and domain blocking

The system provides end-to-end activity monitoring and enforcement capabilities.
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

from focus_guard.core.activity.enhanced_monitor import EnhancedActivityMonitor
from focus_guard.core.activity.blocking.blocking_system import BlockingSystem
from focus_guard.core.activity.blocking.models import BlockingPolicy, BlockingAction
from focus_guard.core.activity.browser.enhanced_browser_monitor import EnhancedBrowserMonitor
from focus_guard.core.activity.browser.enhanced_domain_blocker import (
    EnhancedDomainBlocker, URLPattern, BlockingRule,
    create_social_media_patterns, create_entertainment_patterns, 
    create_gaming_patterns, create_work_productivity_exceptions
)
from focus_guard.core.browser.integration.browser_integration import BrowserIntegration
from focus_guard.core.browser.models.tab import Tab
from focus_guard.core.tab_server_endpoint import resolve_tab_server_base_url

logger = logging.getLogger(__name__)


class ComprehensiveActivitySystem:
    """
    Complete Phase 3 integrated system combining activity monitoring, application blocking,
    and enhanced browser integration.
    
    This system provides:
    - Real-time activity monitoring with idle detection
    - Application-level blocking policies
    - Browser tab monitoring and control
    - Domain-specific blocking with URL pattern matching
    - Multi-browser support
    - Comprehensive reporting and statistics
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the Phase 3 integrated system.
        
        Args:
            config: Configuration dictionary for system components
        """
        self.config = config or {}
        
        # Initialize Phase 1: Activity monitoring
        from focus_guard.core.activity.idle_detector import IdleConfiguration
        idle_config = IdleConfiguration(
            short_idle_threshold=self.config.get('idle_short_threshold', 30),
            medium_idle_threshold=self.config.get('idle_medium_threshold', 300),
            long_idle_threshold=self.config.get('idle_long_threshold', 1800)
        )
        self.activity_monitor = EnhancedActivityMonitor(
            idle_config=idle_config,
            polling_interval=self.config.get('activity_polling_interval', 2.0)
        )
        
        # Initialize Phase 2: Application blocking
        from focus_guard.core.activity.blocking.notification_manager import NotificationConfig
        notification_config = NotificationConfig(
            show_warnings=self.config.get('show_warnings', True),
            show_blocks=self.config.get('show_blocks', True),
            notification_timeout=self.config.get('notification_timeout', 5),
            sound_enabled=self.config.get('sound_enabled', False)
        )
        self.blocking_system = BlockingSystem(notification_config)
        
        # Initialize Phase 3: Browser integration
        self.browser_integration = BrowserIntegration(
            tab_server_url=self.config.get('tab_server_url', resolve_tab_server_base_url()),
            auto_start=self.config.get('auto_start_tab_server', True)
        )
        
        self.domain_blocker = EnhancedDomainBlocker(
            extension_server_url=self.config.get('extension_server_url', 'http://localhost:8000')
        )
        
        self.browser_monitor = EnhancedBrowserMonitor(
            blocking_system=self.blocking_system,
            browser_integration=self.browser_integration,
            tab_blocker=self.domain_blocker,
            polling_interval=self.config.get('browser_polling_interval', 2.0)
        )
        
        # System state
        self._running = False
        self._start_time = None
        
        # Integration callbacks and statistics
        self._setup_integration_callbacks()
        self.integration_stats = {
            'total_tab_blocks': 0,
            'total_app_blocks': 0,
            'total_warnings': 0,
            'policies_triggered': {},
            'browsers_monitored': set(),
            'domains_blocked': set()
        }
    
    def _setup_integration_callbacks(self):
        """Setup integration callbacks between components."""
        # Activity monitor -> Browser monitor integration
        self.activity_monitor.add_activity_callback(self._on_window_activity)
        self.activity_monitor.add_idle_callback(self._on_idle_state_change)
        
        # Browser monitor -> Statistics integration
        self.browser_monitor.add_tab_opened_callback(self._on_tab_opened)
        self.browser_monitor.add_tab_closed_callback(self._on_tab_closed)
        self.browser_monitor.add_tab_blocked_callback(self._on_tab_blocked)
        self.browser_monitor.add_tab_warned_callback(self._on_tab_warned)
        
        # Blocking system -> Domain blocker integration
        self.blocking_system.application_blocker.add_block_callback(self._on_app_blocked)
        self.blocking_system.application_blocker.add_warning_callback(self._on_app_warned)
    
    def _on_window_activity(self, window_info):
        """Handle window activity events."""
        # Check if it's a browser window and sync with browser monitor
        if window_info and window_info.app_name in ['chrome', 'firefox', 'edge', 'safari']:
            self.integration_stats['browsers_monitored'].add(window_info.app_name)
    
    def _on_idle_state_change(self, idle_event):
        """Handle idle state changes."""
        # Could implement idle-based browser policy adjustments
        logger.debug(f"Idle state changed: {idle_event}")
    
    def _on_tab_opened(self, tab: Tab):
        """Handle tab opened events."""
        logger.debug(f"Tab opened: {tab.url}")
    
    def _on_tab_closed(self, tab: Tab):
        """Handle tab closed events."""
        logger.debug(f"Tab closed: {tab.url}")
    
    def _on_tab_blocked(self, tab: Tab, decision):
        """Handle tab blocked events."""
        self.integration_stats['total_tab_blocks'] += 1
        if tab.domain:
            self.integration_stats['domains_blocked'].add(tab.domain)
        if decision.policy_name:
            policy_key = f"tab_{decision.policy_name}"
            self.integration_stats['policies_triggered'][policy_key] = \
                self.integration_stats['policies_triggered'].get(policy_key, 0) + 1
        
        logger.info(f"Tab blocked: {tab.url} (Policy: {decision.policy_name})")
    
    def _on_tab_warned(self, tab: Tab, decision):
        """Handle tab warned events."""
        self.integration_stats['total_warnings'] += 1
        if decision.policy_name:
            policy_key = f"tab_warn_{decision.policy_name}"
            self.integration_stats['policies_triggered'][policy_key] = \
                self.integration_stats['policies_triggered'].get(policy_key, 0) + 1
        
        logger.info(f"Tab warning: {tab.url} (Policy: {decision.policy_name})")
    
    def _on_app_blocked(self, block_event):
        """Handle application blocked events."""
        self.integration_stats['total_app_blocks'] += 1
        policy_key = f"app_{block_event.policy_name}" if hasattr(block_event, 'policy_name') else "app_unknown"
        self.integration_stats['policies_triggered'][policy_key] = \
            self.integration_stats['policies_triggered'].get(policy_key, 0) + 1
        
        logger.info(f"Application blocked: {block_event.app_name}")
    
    def _on_app_warned(self, warning_event):
        """Handle application warning events."""
        self.integration_stats['total_warnings'] += 1
        logger.info(f"Application warning: {warning_event.app_name}")
    
    def start(self):
        """Start the complete Phase 3 integrated system."""
        if self._running:
            logger.warning("Phase 3 integrated system is already running")
            return
        
        logger.info("Starting Phase 3 integrated system...")
        self._running = True
        self._start_time = datetime.now()
        
        try:
            # Start Phase 1: Activity monitoring
            logger.info("Starting activity monitoring...")
            self.activity_monitor.start_monitoring()
            
            # Start Phase 2: Application blocking
            logger.info("Starting application blocking...")
            self.blocking_system.start()
            
            # Start Phase 3: Browser integration
            logger.info("Starting browser integration...")
            self.browser_monitor.start_monitoring()
            
            logger.info("Phase 3 integrated system started successfully")
            
        except Exception as e:
            logger.error(f"Error starting Phase 3 integrated system: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop the complete Phase 3 integrated system."""
        if not self._running:
            return
        
        logger.info("Stopping Phase 3 integrated system...")
        self._running = False
        
        try:
            # Stop components in reverse order
            self.browser_monitor.stop_monitoring()
            self.blocking_system.stop()
            self.activity_monitor.stop_monitoring()
            
            logger.info("Phase 3 integrated system stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping Phase 3 integrated system: {e}")
    
    def create_comprehensive_policies(self):
        """Create comprehensive blocking policies for all phases."""
        logger.info("Creating comprehensive blocking policies...")
        
        # Phase 2: Application-level policies
        self._create_application_policies()
        
        # Phase 3: Browser-specific policies
        self._create_browser_policies()
        
        # Sync policies with domain blocker
        self._sync_policies_with_domain_blocker()
        
        logger.info("Comprehensive policies created successfully")
    
    def _create_application_policies(self):
        """Create application-level blocking policies."""
        # Social media applications
        social_media_policy = BlockingPolicy(
            name="Social Media Applications",
            description="Block social media applications during work hours",
            app_patterns=["chrome", "firefox", "edge"],
            domain_patterns=["facebook.com", "twitter.com", "instagram.com", "tiktok.com", "snapchat.com"],
            action=BlockingAction.BLOCK,
            grace_period_seconds=30,
            warning_message="Social media is blocked during work hours to maintain productivity.",
            override_allowed=True,
            override_duration_minutes=15
        )
        
        # Gaming applications
        gaming_policy = BlockingPolicy(
            name="Gaming Applications",
            description="Block gaming applications and platforms",
            app_patterns=["steam", "origin", "uplay", "battlenet", "epicgames", "minecraft", "roblox"],
            domain_patterns=["steam.com", "epicgames.com", "battle.net", "minecraft.net", "roblox.com"],
            action=BlockingAction.BLOCK,
            grace_period_seconds=15,
            warning_message="Gaming applications are blocked during work hours.",
            override_allowed=True,
            override_duration_minutes=30
        )
        
        # Entertainment with warnings
        entertainment_policy = BlockingPolicy(
            name="Entertainment Content",
            description="Warn about entertainment content consumption",
            app_patterns=["netflix", "spotify", "vlc", "discord"],
            domain_patterns=["youtube.com", "netflix.com", "twitch.tv", "hulu.com", "disney.com"],
            action=BlockingAction.WARN,
            grace_period_seconds=60,
            warning_message="Entertainment content may impact your productivity.",
            override_allowed=True,
            override_duration_minutes=20
        )
        
        # Add policies to blocking system
        self.blocking_system.add_policy(social_media_policy)
        self.blocking_system.add_policy(gaming_policy)
        self.blocking_system.add_policy(entertainment_policy)
    
    def _create_browser_policies(self):
        """Create browser-specific blocking rules."""
        # Social media blocking rule
        social_media_rule = BlockingRule(
            name="Social Media Sites",
            action=BlockingAction.BLOCK,
            patterns=create_social_media_patterns(),
            time_restrictions=[(9, 17)],  # 9 AM to 5 PM
            exception_patterns=create_work_productivity_exceptions(),
            grace_period=30,
            warning_message="Social media sites are blocked during work hours."
        )
        
        # Entertainment warning rule
        entertainment_rule = BlockingRule(
            name="Entertainment Sites",
            action=BlockingAction.WARN,
            patterns=create_entertainment_patterns(),
            time_restrictions=[(9, 17)],  # 9 AM to 5 PM
            grace_period=60,
            warning_message="Entertainment content may reduce productivity."
        )
        
        # Gaming strict blocking
        gaming_rule = BlockingRule(
            name="Gaming Sites",
            action=BlockingAction.BLOCK,
            patterns=create_gaming_patterns(),
            grace_period=15,
            warning_message="Gaming sites are blocked."
        )
        
        # Add rules to domain blocker
        self.domain_blocker.add_blocking_rule(social_media_rule)
        self.domain_blocker.add_blocking_rule(entertainment_rule)
        self.domain_blocker.add_blocking_rule(gaming_rule)
    
    def _sync_policies_with_domain_blocker(self):
        """Sync Phase 2 policies with Phase 3 domain blocker."""
        policies = self.blocking_system.list_policies()
        self.domain_blocker.sync_with_policies(policies)
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the entire Phase 3 system."""
        return {
            'system': {
                'running': self._running,
                'start_time': self._start_time.isoformat() if self._start_time else None,
                'uptime_seconds': (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
            },
            'phase1_activity_monitoring': self.activity_monitor.get_comprehensive_status(),
            'phase2_application_blocking': self.blocking_system.get_system_status(),
            'phase3_browser_integration': {
                'browser_monitor': self.browser_monitor.get_comprehensive_status(),
                'domain_blocker': self.domain_blocker.get_comprehensive_statistics(),
                'browser_integration': {
                    'active': hasattr(self.browser_integration, 'is_running') and self.browser_integration.is_running(),
                    'tab_server_url': self.browser_integration._tab_server_url
                }
            },
            'integration_statistics': {
                **self.integration_stats,
                'browsers_monitored': list(self.integration_stats['browsers_monitored']),
                'domains_blocked': list(self.integration_stats['domains_blocked'])
            }
        }
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics for the integrated system."""
        status = self.get_comprehensive_status()
        
        return {
            'system_active': self._running,
            'uptime_minutes': round(status['system']['uptime_seconds'] / 60, 1),
            'total_policies': len(self.blocking_system.list_policies()),
            'total_blocking_rules': len(self.domain_blocker.get_blocking_rules()),
            'active_tabs': len(self.browser_monitor.get_active_tabs()),
            'total_blocks': (
                self.integration_stats['total_tab_blocks'] + 
                self.integration_stats['total_app_blocks']
            ),
            'total_warnings': self.integration_stats['total_warnings'],
            'browsers_monitored': len(self.integration_stats['browsers_monitored']),
            'domains_blocked': len(self.integration_stats['domains_blocked']),
            'idle_state': self.activity_monitor.get_idle_state().value if hasattr(self.activity_monitor, 'get_idle_state') else 'unknown'
        }
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export complete system configuration."""
        return {
            'system_config': self.config,
            'blocking_policies': self.blocking_system.export_configuration(),
            'blocking_rules': {
                name: {
                    'name': rule.name,
                    'action': rule.action.value,
                    'patterns': [{'pattern': p.pattern, 'type': p.pattern_type} for p in rule.patterns],
                    'time_restrictions': rule.time_restrictions,
                    'grace_period': rule.grace_period,
                    'warning_message': rule.warning_message
                }
                for name, rule in self.domain_blocker.get_blocking_rules().items()
            },
            'export_timestamp': datetime.now().isoformat()
        }
    
    def import_configuration(self, config: Dict[str, Any]):
        """Import complete system configuration."""
        logger.info("Importing Phase 3 system configuration...")
        
        # Import blocking policies
        if 'blocking_policies' in config:
            self.blocking_system.import_configuration(config['blocking_policies'])
        
        # Import blocking rules
        if 'blocking_rules' in config:
            for rule_name, rule_data in config['blocking_rules'].items():
                patterns = [
                    URLPattern(p['pattern'], p['type']) 
                    for p in rule_data.get('patterns', [])
                ]
                
                rule = BlockingRule(
                    name=rule_data['name'],
                    action=BlockingAction(rule_data['action']),
                    patterns=patterns,
                    time_restrictions=rule_data.get('time_restrictions', []),
                    grace_period=rule_data.get('grace_period', 0),
                    warning_message=rule_data.get('warning_message')
                )
                
                self.domain_blocker.add_blocking_rule(rule)
        
        # Sync policies with domain blocker
        self._sync_policies_with_domain_blocker()
        
        logger.info("Phase 3 system configuration imported successfully")
    
    def is_healthy(self) -> bool:
        """Check if the entire system is healthy."""
        if not self._running:
            return False
        
        try:
            # Check each component
            activity_healthy = hasattr(self.activity_monitor, 'is_active') and self.activity_monitor.is_active()
            blocking_healthy = self.blocking_system.is_active()
            browser_healthy = self.browser_monitor.is_monitoring()
            
            return activity_healthy and blocking_healthy and browser_healthy
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return False
