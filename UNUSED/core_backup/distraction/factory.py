"""
Factory for creating distraction detector components.

This module provides a factory for creating and assembling
distraction detector components with proper configuration and dependencies.
"""

from typing import Dict, Any, Optional, List
import logging

from core_v2.distraction.interfaces import DistractionDetector, DistractionRule, AlertHandler, BrowserActivityTracker
from core_v2.distraction.detector import StandardDistractionDetector
from core_v2.distraction.rules.url_rule import URLRule
from core_v2.distraction.rules.context_rule import ContextSwitchRule
from core_v2.distraction.rules.area_rule import AreaIncreaseRule
from core_v2.distraction.trackers.browser_tracker import StandardBrowserTracker
from core_v2.distraction.handlers.notification_handler import NotificationHandler
from core_v2.distraction.handlers.blocking_handler import BlockingHandler
from core_v2.distraction.config import DistractionConfig, get_default_config
from core_v2.distraction.models import AlertLevel

from core_v2.config.interfaces import ConfigurationManager
from core_v2.classification.base import ContextAwareClassifier
from core_v2.browser.interfaces import BrowserIntegrationInterface
from core_v2.alert.providers.base import AlertProvider


class DistractionDetectorFactory:
    """
    Factory for creating distraction detector components.
    
    This factory creates and assembles distraction detector components
    with proper configuration and dependencies.
    """
    
    def __init__(
        self,
        config_manager: ConfigurationManager,
        domain_classifier: ContextAwareClassifier,
        browser_integration: BrowserIntegrationInterface,
        alert_provider: AlertProvider,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the factory.
        
        Args:
            config_manager: The configuration manager.
            domain_classifier: The domain classifier.
            browser_integration: The browser integration.
            alert_provider: The alert provider for notifications.
            logger: Optional logger for logging.
        """
        self._config_manager = config_manager
        self._domain_classifier = domain_classifier
        self._browser_integration = browser_integration
        self._alert_provider = alert_provider
        self._logger = logger or logging.getLogger(__name__)
        
        # Ensure distraction config exists
        self._ensure_config()
    
    def _ensure_config(self) -> None:
        """Ensure distraction configuration exists."""
        if not self._config_manager.has("distraction"):
            # Create default configuration
            default_config = get_default_config()
            self._config_manager.set("distraction", default_config)
    
    def create_detector(self) -> DistractionDetector:
        """
        Create a distraction detector with all components.
        
        Returns:
            A fully configured distraction detector.
        """
        # Create detector
        detector = StandardDistractionDetector(
            config_manager=self._config_manager,
            logger=self._logger
        )
        
        # Add rules
        for rule in self._create_rules():
            detector.add_rule(rule)
        
        # Add alert handlers
        for handler in self._create_handlers():
            detector.add_alert_handler(handler)
        
        # Create and connect browser tracker
        browser_tracker = self._create_browser_tracker()
        
        # Register detector as callback for browser tracker
        browser_tracker.register_state_update_callback(
            lambda browser_state: detector.update(
                detector.get_distraction_state().active_window,
                detector.get_distraction_state().top_windows
            )
        )
        
        return detector
    
    def _create_rules(self) -> List[DistractionRule]:
        """
        Create distraction rules.
        
        Returns:
            A list of distraction rules.
        """
        rules = []
        
        # Get configuration
        config = self._config_manager.get("distraction", {})
        rule_configs = config.get("rules", {})
        
        # Create URL rule
        url_rule_config = rule_configs.get("url_rule", {})
        if url_rule_config.get("enabled", True):
            distracting_categories = url_rule_config.get("distracting_categories", [
                "social", "entertainment", "shopping"
            ])
            domain_whitelist = set(url_rule_config.get("domain_whitelist", []))
            
            url_rule = URLRule(
                domain_classifier=self._domain_classifier,
                distracting_categories=distracting_categories,
                domain_whitelist=domain_whitelist,
                rule_config=url_rule_config
            )
            rules.append(url_rule)
        
        # Create context switch rule
        context_rule_config = rule_configs.get("context_switch_rule", {})
        if context_rule_config.get("enabled", True):
            switch_threshold = context_rule_config.get("switch_threshold", 5)
            time_window_seconds = context_rule_config.get("time_window_seconds", 60)
            
            context_rule = ContextSwitchRule(
                switch_threshold=switch_threshold,
                time_window_seconds=time_window_seconds,
                rule_config=context_rule_config
            )
            rules.append(context_rule)
        
        # Create area increase rule
        area_rule_config = rule_configs.get("area_increase_rule", {})
        if area_rule_config.get("enabled", True):
            area_threshold = area_rule_config.get("area_threshold", 50.0)
            min_area = area_rule_config.get("min_area", 100000)
            
            area_rule = AreaIncreaseRule(
                area_threshold=area_threshold,
                min_area=min_area,
                rule_config=area_rule_config
            )
            rules.append(area_rule)
        
        return rules
    
    def _create_handlers(self) -> List[AlertHandler]:
        """
        Create alert handlers.
        
        Returns:
            A list of alert handlers.
        """
        handlers = []
        
        # Get configuration
        config = self._config_manager.get("distraction", {})
        handler_configs = config.get("handlers", {})
        
        # Create notification handler
        notification_config = handler_configs.get("notification", {})
        if notification_config.get("enabled", True):
            min_level_str = notification_config.get("min_level", "WARNING")
            min_level = AlertLevel[min_level_str]
            cooldown_seconds = notification_config.get("cooldown_seconds", 60)
            
            notification_handler = NotificationHandler(
                alert_provider=self._alert_provider,
                min_level=min_level,
                cooldown_seconds=cooldown_seconds,
                logger=self._logger
            )
            handlers.append(notification_handler)
        
        # Create blocking handler
        blocking_config = handler_configs.get("blocking", {})
        if blocking_config.get("enabled", True):
            min_level_str = blocking_config.get("min_level", "CRITICAL")
            min_level = AlertLevel[min_level_str]
            block_duration_seconds = blocking_config.get("block_duration_seconds", 300)
            
            blocking_handler = BlockingHandler(
                browser_integration=self._browser_integration,
                min_level=min_level,
                block_duration_seconds=block_duration_seconds,
                logger=self._logger
            )
            handlers.append(blocking_handler)
        
        return handlers
    
    def _create_browser_tracker(self) -> BrowserActivityTracker:
        """
        Create a browser activity tracker.
        
        Returns:
            A browser activity tracker.
        """
        return StandardBrowserTracker(
            browser_integration=self._browser_integration,
            domain_classifier=self._domain_classifier,
            logger=self._logger
        )
