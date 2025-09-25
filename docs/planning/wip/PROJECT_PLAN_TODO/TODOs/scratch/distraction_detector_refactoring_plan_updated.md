# Distraction Detector Refactoring Plan (Updated)

## Overview

This document outlines the updated plan for implementing the distraction detector module in the `core_v2` architecture. The focus is on building a clean, modular implementation that leverages the improved architecture and abstractions in core_v2 without worrying about legacy adapters or parallel implementation.

## Current Implementation Analysis

### Existing Components in `core/distraction_detector`

1. **DistractionDetector** (`distraction_detector.py`)
   - Main class for detecting distractions
   - Uses rule-based detection system
   - Integrates with domain classifier for URL categorization
   - Provides alerting and logging callbacks
   - Tracks distraction state over time

2. **DistractionRule** (Base class for distraction detection rules)
   - `AreaIncreaseRule`: Detects window area increases
   - `ContextSwitchRule`: Detects context switches between applications
   - `URLRule` (`url_rule.py`): Detects distracting URLs in browser windows

3. **BrowserTabTracker** (`browser_tracker.py`)
   - Tracks browser tabs and their productivity status
   - Integrates with browser extensions for tab tracking
   - Classifies domains as productive or distracting
   - Maintains state of browser tabs

### Dependencies on core_v2 Modules

1. **Domain Classification**
   - `core_v2/classification/base.py`: Defines the `Classifier` abstract base class
   - `core_v2/classification/domain_classifier.py`: Implements `StandardDomainClassifier`
   - `core_v2/domain/models.py`: Defines `Domain` and `Category` models
   - `core_v2/domain/constants.py`: Defines category mappings

2. **Configuration**
   - `core_v2/config/interfaces.py`: Defines `ConfigProvider` and related interfaces
   - `core_v2/config/manager.py`: Implements `ConfigurationManager`
   - Supports schema-based validation and change notifications

3. **Browser Integration**
   - Will use `core_v2/browser` module for browser extension integration
   - Leverages event-based communication for tab updates

## Design Goals for core_v2 Distraction Detector

1. **Modularity**
   - Clear separation of concerns (detection, rules, tracking)
   - Pluggable rule system for different distraction types
   - Support for different alerting mechanisms

2. **Type Safety and Validation**
   - Strong typing for all components
   - Validation of inputs and outputs
   - Clear error handling

3. **Extensibility**
   - Easy to add new distraction detection rules
   - Support for custom alerting mechanisms
   - Configurable thresholds and behaviors

4. **Integration with core_v2**
   - Leverage `core_v2/classification` for domain classification
   - Use `core_v2/domain` models for domain representation
   - Integrate with `core_v2/config` for configuration

5. **Testability**
   - Comprehensive unit tests
   - Mocking of external dependencies
   - Clear interfaces for testing

## Architecture Design

### Core Components

1. **DistractionDetector**
   - Central manager for distraction detection
   - Coordinates rule evaluation and alerting
   - Maintains distraction state

2. **DistractionRule Interface**
   - Abstract interface for distraction rules
   - Standard implementations for common rules
   - Support for custom rules

3. **BrowserActivityTracker**
   - Tracks browser activity and tab state
   - Integrates with browser extension
   - Provides browser activity events

4. **DistractionAlert**
   - Represents a distraction alert
   - Contains metadata about the distraction
   - Supports different alert levels

5. **AlertHandler Interface**
   - Abstract interface for handling alerts
   - Implementations for different alert mechanisms
   - Support for alert escalation

### Directory Structure

```
core_v2/
  distraction/
    __init__.py
    interfaces.py      # Core interfaces
    models.py          # Data models
    detector.py        # DistractionDetector implementation
    factory.py         # Factory for creating detector instances
    config.py          # Configuration schemas
    rules/
      __init__.py
      base.py          # Base rule implementation
      url_rule.py      # URL-based distraction rule
      context_rule.py  # Context switch rule
      area_rule.py     # Window area rule
    trackers/
      __init__.py
      browser.py       # Browser activity tracker
      application.py   # Application activity tracker
    handlers/
      __init__.py
      notification.py  # Notification alert handler
      blocking.py      # Content blocking handler
    utils/
      __init__.py
      state.py         # State management utilities
```

## Implementation Plan

### Phase 1: Core Infrastructure

1. **Define Core Interfaces**
   - Create `interfaces.py` with base interfaces
   - Define rule and handler interfaces
   - Implement basic models

2. **Implement Basic Rules**
   - Port `ContextSwitchRule` to core_v2
   - Port `AreaIncreaseRule` to core_v2
   - Create base rule implementation

3. **Create State Management**
   - Implement distraction state models
   - Create state transition logic

### Phase 2: Core Implementation

1. **Implement DistractionDetector**
   - Create main detector class
   - Implement rule evaluation logic
   - Add alert handling

2. **Implement Browser Activity Tracker**
   - Create browser activity tracker
   - Integrate with browser extension
   - Implement tab state management

3. **Implement Configuration**
   - Define configuration schemas
   - Implement configuration loading
   - Add configuration change handling

### Phase 3: URL Rule and Integration

1. **Implement URL Rule**
   - Port `URLRule` to core_v2
   - Integrate with domain classifier
   - Add URL extraction and normalization

2. **Integrate with core_v2**
   - Connect with classification system
   - Integrate with configuration system
   - Add event handling

3. **Add Testing Infrastructure**
   - Create unit tests for all components
   - Implement mocks for external dependencies
   - Test integration points

### Phase 4: Advanced Features and Optimization

1. **Implement Advanced Rules**
   - Add time-based rules
   - Add pattern-based rules
   - Support rule composition

2. **Optimize Performance**
   - Implement caching for frequent operations
   - Optimize rule evaluation
   - Reduce memory footprint

3. **Add Analytics**
   - Track distraction patterns
   - Generate distraction reports
   - Support for personalization

## Core Interface Definitions

### Distraction Rule Interface

```python
# core_v2/distraction/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from core_v2.distraction.models import DistractionAlert, DistractionState

class DistractionRule(ABC):
    """
    Interface for distraction detection rules.
    
    Rules are responsible for detecting specific types of distractions
    based on the current state and activity.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the rule."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the description of the rule."""
        pass
    
    @abstractmethod
    def should_apply(self, state: DistractionState) -> bool:
        """
        Determine if the rule should be applied to the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            True if the rule should be applied, False otherwise.
        """
        pass
    
    @abstractmethod
    def check(self, state: DistractionState) -> List[DistractionAlert]:
        """
        Check for distractions based on the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            A list of distraction alerts, or an empty list if no distractions are detected.
        """
        pass
```

### Alert Handler Interface

```python
# core_v2/distraction/interfaces.py
class AlertHandler(ABC):
    """
    Interface for handling distraction alerts.
    
    Alert handlers are responsible for responding to distraction alerts,
    such as displaying notifications, blocking content, or logging.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the handler."""
        pass
    
    @abstractmethod
    def handle(self, alert: DistractionAlert) -> None:
        """
        Handle a distraction alert.
        
        Args:
            alert: The distraction alert to handle.
        """
        pass
    
    @abstractmethod
    def can_handle(self, alert: DistractionAlert) -> bool:
        """
        Determine if the handler can handle the given alert.
        
        Args:
            alert: The distraction alert to check.
            
        Returns:
            True if the handler can handle the alert, False otherwise.
        """
        pass
```

### Distraction Detector Interface

```python
# core_v2/distraction/interfaces.py
class DistractionDetector(ABC):
    """
    Interface for distraction detection.
    
    The distraction detector is responsible for coordinating rule evaluation
    and alert handling based on the current state and activity.
    """
    
    @abstractmethod
    def add_rule(self, rule: DistractionRule) -> None:
        """
        Add a distraction rule.
        
        Args:
            rule: The rule to add.
        """
        pass
    
    @abstractmethod
    def add_alert_handler(self, handler: AlertHandler) -> None:
        """
        Add an alert handler.
        
        Args:
            handler: The handler to add.
        """
        pass
    
    @abstractmethod
    def update(self, active_window: Dict[str, Any], top_windows: List[Dict[str, Any]]) -> None:
        """
        Update the distraction detector with the current window state.
        
        Args:
            active_window: Information about the active window.
            top_windows: List of top windows.
        """
        pass
    
    @property
    @abstractmethod
    def is_distracted(self) -> bool:
        """
        Check if the user is currently distracted.
        
        Returns:
            True if the user is distracted, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_distraction_state(self) -> DistractionState:
        """
        Get the current distraction state.
        
        Returns:
            The current distraction state.
        """
        pass
```

## Core Models

```python
# core_v2/distraction/models.py
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class AlertLevel(Enum):
    """Alert levels for distraction alerts."""
    INFO = 0
    WARNING = 1
    CRITICAL = 2

@dataclass
class DistractionAlert:
    """
    Represents a distraction alert.
    
    Attributes:
        rule_name: The name of the rule that generated the alert.
        level: The alert level.
        message: The alert message.
        metadata: Additional metadata about the alert.
        timestamp: The time the alert was generated.
    """
    rule_name: str
    level: AlertLevel
    message: str
    metadata: Dict[str, Any]
    timestamp: datetime

@dataclass
class DistractionState:
    """
    Represents the current distraction state.
    
    Attributes:
        active_window: Information about the active window.
        top_windows: List of top windows.
        browser_tabs: Information about browser tabs.
        last_update: The time of the last update.
        distraction_history: History of distraction alerts.
    """
    active_window: Optional[Dict[str, Any]] = None
    top_windows: List[Dict[str, Any]] = None
    browser_tabs: Dict[str, Any] = None
    last_update: Optional[datetime] = None
    distraction_history: List[DistractionAlert] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.top_windows is None:
            self.top_windows = []
        if self.browser_tabs is None:
            self.browser_tabs = {}
        if self.distraction_history is None:
            self.distraction_history = []
    
    def update(self, active_window: Dict[str, Any], top_windows: List[Dict[str, Any]]) -> None:
        """
        Update the state with new window information.
        
        Args:
            active_window: Information about the active window.
            top_windows: List of top windows.
        """
        self.active_window = active_window
        self.top_windows = top_windows
        self.last_update = datetime.now()
    
    def update_browser_tabs(self, browser_tabs: Dict[str, Any]) -> None:
        """
        Update the state with new browser tab information.
        
        Args:
            browser_tabs: Information about browser tabs.
        """
        self.browser_tabs = browser_tabs
        self.last_update = datetime.now()
    
    def add_distraction_alert(self, alert: DistractionAlert) -> None:
        """
        Add a distraction alert to the history.
        
        Args:
            alert: The distraction alert to add.
        """
        self.distraction_history.append(alert)
```

## Standard Distraction Detector Implementation

```python
# core_v2/distraction/detector.py
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import logging

from core_v2.distraction.interfaces import DistractionDetector, DistractionRule, AlertHandler
from core_v2.distraction.models import DistractionAlert, DistractionState
from core_v2.config.interfaces import ConfigProvider, ConfigurationManager

class StandardDistractionDetector(DistractionDetector):
    """
    Standard implementation of the distraction detector.
    
    This implementation uses a rule-based approach to detect distractions
    and delegates alert handling to registered handlers.
    """
    
    def __init__(
        self,
        config_manager: ConfigurationManager,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the distraction detector.
        
        Args:
            config_manager: The configuration manager.
            logger: Optional logger for logging.
        """
        self._config_manager = config_manager
        self._logger = logger or logging.getLogger(__name__)
        self._rules: List[DistractionRule] = []
        self._alert_handlers: List[AlertHandler] = []
        self._state = DistractionState()
        
        # Register for configuration changes
        self._config_manager.register_change_callback(
            "distraction",
            self._on_config_changed
        )
        
        # Load initial configuration
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load configuration settings."""
        config = self._config_manager.get("distraction", {})
        
        # Load distraction thresholds
        self._distraction_thresholds = config.get("thresholds", {})
        
        # Load productive and distracting categories
        self._productive_categories = config.get("productive_categories", [
            "work", "education", "productivity", "development", "email"
        ])
        self._distracting_categories = config.get("distracting_categories", [
            "social", "entertainment", "shopping"
        ])
        
        # Load domain whitelist
        self._domain_whitelist = set(config.get("domain_whitelist", []))
    
    def _on_config_changed(self) -> None:
        """Handle configuration changes."""
        self._logger.info("Configuration changed, reloading settings")
        self._load_configuration()
    
    def add_rule(self, rule: DistractionRule) -> None:
        """
        Add a distraction rule.
        
        Args:
            rule: The rule to add.
        """
        self._rules.append(rule)
    
    def add_alert_handler(self, handler: AlertHandler) -> None:
        """
        Add an alert handler.
        
        Args:
            handler: The handler to add.
        """
        self._alert_handlers.append(handler)
    
    def update(self, active_window: Dict[str, Any], top_windows: List[Dict[str, Any]]) -> None:
        """
        Update the distraction detector with the current window state.
        
        Args:
            active_window: Information about the active window.
            top_windows: List of top windows.
        """
        # Update state
        self._state.update(active_window, top_windows)
        
        # Check for distractions
        alerts = self._check_for_distractions()
        
        # Handle alerts
        for alert in alerts:
            self._handle_alert(alert)
    
    def _check_for_distractions(self) -> List[DistractionAlert]:
        """
        Check for distractions using all rules.
        
        Returns:
            A list of distraction alerts.
        """
        alerts = []
        
        # Apply each rule that should be applied
        for rule in self._rules:
            if rule.should_apply(self._state):
                rule_alerts = rule.check(self._state)
                alerts.extend(rule_alerts)
        
        return alerts
    
    def _handle_alert(self, alert: DistractionAlert) -> None:
        """
        Handle a distraction alert.
        
        Args:
            alert: The distraction alert to handle.
        """
        # Log the alert
        self._logger.info(f"Distraction detected: {alert.message}")
        
        # Add to state history
        self._state.add_distraction_alert(alert)
        
        # Call all alert handlers that can handle this alert
        for handler in self._alert_handlers:
            if handler.can_handle(alert):
                try:
                    handler.handle(alert)
                except Exception as e:
                    self._logger.error(f"Error in alert handler {handler.name}: {e}")
    
    @property
    def is_distracted(self) -> bool:
        """
        Check if the user is currently distracted.
        
        Returns:
            True if the user is distracted, False otherwise.
        """
        # Check if there are any recent alerts
        if not self._state.distraction_history:
            return False
        
        # Get the most recent alert
        last_alert = self._state.distraction_history[-1]
        
        # Check if the alert is recent enough (within the last minute)
        now = datetime.now()
        alert_age = (now - last_alert.timestamp).total_seconds()
        
        return alert_age < 60  # Consider distracted if alert is less than 60 seconds old
    
    def get_distraction_state(self) -> DistractionState:
        """
        Get the current distraction state.
        
        Returns:
            The current distraction state.
        """
        return self._state
```

## URL Rule Implementation

```python
# core_v2/distraction/rules/url_rule.py
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from core_v2.distraction.interfaces import DistractionRule
from core_v2.distraction.models import DistractionAlert, DistractionState, AlertLevel
from core_v2.classification.interfaces import ContextAwareClassifier
from core_v2.domain.models import Domain, Category
from core_v2.domain.utils import extract_domain_from_url

class URLRule(DistractionRule):
    """
    Rule for detecting distractions based on URLs in browser windows.
    
    This rule checks if the active window contains a URL that is classified
    as a distraction based on its domain category.
    """
    
    def __init__(
        self,
        domain_classifier: ContextAwareClassifier,
        distracting_categories: Optional[List[str]] = None,
        domain_whitelist: Optional[Set[str]] = None
    ):
        """
        Initialize the URL rule.
        
        Args:
            domain_classifier: The domain classifier to use.
            distracting_categories: List of categories considered distracting.
            domain_whitelist: Set of domains to whitelist (never considered distracting).
        """
        self._domain_classifier = domain_classifier
        self._distracting_categories = distracting_categories or [
            "social", "entertainment", "shopping"
        ]
        self._domain_whitelist = domain_whitelist or set()
        
    @property
    def name(self) -> str:
        """Get the name of the rule."""
        return "URL Rule"
    
    @property
    def description(self) -> str:
        """Get the description of the rule."""
        return "Detects distracting URLs in browser windows."
    
    def should_apply(self, state: DistractionState) -> bool:
        """
        Determine if the rule should be applied to the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            True if the rule should be applied, False otherwise.
        """
        active_window = state.active_window
        if not active_window:
            return False
            
        app_name = active_window.get('app_name', '').lower()
        return self._is_browser(app_name)
    
    def check(self, state: DistractionState) -> List[DistractionAlert]:
        """
        Check for distractions based on the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            A list of distraction alerts, or an empty list if no distractions are detected.
        """
        alerts = []
        active_window = state.active_window
        
        if not active_window:
            return alerts
            
        # Extract URL from window title or browser tabs
        url = self._extract_url_from_window(active_window, state.browser_tabs)
        if not url:
            return alerts
            
        # Extract domain from URL
        domain_str = extract_domain_from_url(url)
        if not domain_str:
            return alerts
            
        # Check if domain is whitelisted
        if domain_str in self._domain_whitelist:
            return alerts
            
        # Classify domain
        try:
            domain = Domain(domain_str)
            classification = self._domain_classifier.classify(domain)
            
            # Check if domain is in a distracting category
            category = classification.category
            if category and category.name.lower() in self._distracting_categories:
                alert = DistractionAlert(
                    rule_name=self.name,
                    level=AlertLevel.WARNING,
                    message=f"Distracting website detected: {domain_str}",
                    metadata={
                        "domain": domain_str,
                        "category": category.name,
                        "url": url
                    },
                    timestamp=datetime.now()
                )
                alerts.append(alert)
        except Exception as e:
            # Log error but don't crash
            pass
            
        return alerts
    
    def _is_browser(self, app_name: str) -> bool:
        """
        Check if the application is a browser.
        
        Args:
            app_name: The name of the application.
            
        Returns:
            True if the application is a browser, False otherwise.
        """
        browsers = ["chrome", "firefox", "edge", "opera", "safari", "brave"]
        return any(browser in app_name for browser in browsers)
    
    def _extract_url_from_window(
        self,
        window: Dict[str, Any],
        browser_tabs: Dict[str, Any]
    ) -> Optional[str]:
        """
        Extract URL from window title or browser tabs.
        
        Args:
            window: Information about the window.
            browser_tabs: Information about browser tabs.
            
        Returns:
            The extracted URL, or None if no URL could be extracted.
        """
        # First try to get URL from browser tabs if available
        if browser_tabs:
            active_tab = browser_tabs.get("active_tab")
            if active_tab and "url" in active_tab:
                return active_tab["url"]
        
        # Fall back to window title
        title = window.get("title", "")
        
        # Simple heuristic: look for http:// or https:// in the title
        if "http://" in title or "https://" in title:
            # Extract URL using simple heuristic
            parts = title.split(" ")
            for part in parts:
                if part.startswith("http://") or part.startswith("https://"):
                    return part
        
        return None
```

## Configuration Schema

```python
# core_v2/distraction/config.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from core_v2.config.models import ConfigurationSection

@dataclass
class DistractionRuleConfig(ConfigurationSection):
    """
    Configuration for a distraction rule.
    
    Attributes:
        enabled: Whether the rule is enabled.
        parameters: Rule-specific parameters.
    """
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class URLRuleConfig(DistractionRuleConfig):
    """
    Configuration for the URL rule.
    
    Attributes:
        distracting_categories: List of categories considered distracting.
        domain_whitelist: List of domains to whitelist.
    """
    distracting_categories: List[str] = field(default_factory=lambda: [
        "social", "entertainment", "shopping"
    ])
    domain_whitelist: List[str] = field(default_factory=list)

@dataclass
class DistractionThresholds(ConfigurationSection):
    """
    Configuration for distraction thresholds.
    
    Attributes:
        time_threshold: Time threshold in seconds.
        count_threshold: Count threshold.
    """
    time_threshold: int = 60
    count_threshold: int = 3

@dataclass
class DistractionConfig(ConfigurationSection):
    """
    Configuration for the distraction detector.
    
    Attributes:
        enabled: Whether distraction detection is enabled.
        thresholds: Distraction thresholds.
        rules: Rule configurations.
        productive_categories: List of categories considered productive.
        distracting_categories: List of categories considered distracting.
        domain_whitelist: List of domains to whitelist.
    """
    enabled: bool = True
    thresholds: DistractionThresholds = field(default_factory=DistractionThresholds)
    rules: Dict[str, DistractionRuleConfig] = field(default_factory=dict)
    productive_categories: List[str] = field(default_factory=lambda: [
        "work", "education", "productivity", "development", "email"
    ])
    distracting_categories: List[str] = field(default_factory=lambda: [
        "social", "entertainment", "shopping"
    ])
    domain_whitelist: List[str] = field(default_factory=list)
```

## Factory for Creating Distraction Detector

```python
# core_v2/distraction/factory.py
from typing import Optional, List
import logging

from core_v2.distraction.interfaces import DistractionDetector, AlertHandler
from core_v2.distraction.detector import StandardDistractionDetector
from core_v2.distraction.rules.url_rule import URLRule
from core_v2.distraction.rules.context_rule import ContextSwitchRule
from core_v2.distraction.rules.area_rule import AreaIncreaseRule
from core_v2.classification.interfaces import ContextAwareClassifier
from core_v2.config.interfaces import ConfigurationManager

class DistractionDetectorFactory:
    """
    Factory for creating distraction detector instances.
    """
    
    @staticmethod
    def create(
        config_manager: ConfigurationManager,
        domain_classifier: ContextAwareClassifier,
        alert_handlers: Optional[List[AlertHandler]] = None,
        logger: Optional[logging.Logger] = None
    ) -> DistractionDetector:
        """
        Create a distraction detector.
        
        Args:
            config_manager: The configuration manager.
            domain_classifier: The domain classifier to use.
            alert_handlers: Optional list of alert handlers.
            logger: Optional logger for logging.
            
        Returns:
            A configured distraction detector.
        """
        # Create detector
        detector = StandardDistractionDetector(config_manager, logger)
        
        # Get configuration
        config = config_manager.get("distraction", {})
        
        # Add rules
        if config.get("rules", {}).get("url_rule", {}).get("enabled", True):
            url_rule_config = config.get("rules", {}).get("url_rule", {})
            url_rule = URLRule(
                domain_classifier=domain_classifier,
                distracting_categories=url_rule_config.get(
                    "distracting_categories",
                    config.get("distracting_categories", ["social", "entertainment", "shopping"])
                ),
                domain_whitelist=set(url_rule_config.get(
                    "domain_whitelist",
                    config.get("domain_whitelist", [])
                ))
            )
            detector.add_rule(url_rule)
        
        if config.get("rules", {}).get("context_rule", {}).get("enabled", True):
            context_rule = ContextSwitchRule()
            detector.add_rule(context_rule)
        
        if config.get("rules", {}).get("area_rule", {}).get("enabled", True):
            area_rule = AreaIncreaseRule()
            detector.add_rule(area_rule)
        
        # Add alert handlers
        if alert_handlers:
            for handler in alert_handlers:
                detector.add_alert_handler(handler)
        
        return detector
```

## Benefits of the New System

1. **Improved Modularity**
   - Clear separation of concerns
   - Pluggable rule system
   - Extensible alert handling

2. **Better Integration with core_v2**
   - Leverages core_v2 domain models
   - Uses core_v2 classification system
   - Integrates with core_v2 configuration

3. **Enhanced Type Safety**
   - Strong typing throughout
   - Clear interfaces
   - Better error handling

4. **Improved Testability**
   - Mockable dependencies
   - Clear interfaces for testing
   - Comprehensive test coverage

5. **Advanced Features**
   - Support for complex rules
   - Better alert escalation
   - Improved analytics

## Implementation Roadmap

1. **Week 1: Core Infrastructure**
   - Define interfaces and models
   - Implement basic state management
   - Create configuration schemas

2. **Week 2: Core Implementation**
   - Implement StandardDistractionDetector
   - Implement basic rules (URL, Context, Area)
   - Create factory

3. **Week 3: Integration and Testing**
   - Integrate with core_v2 modules
   - Implement browser activity tracking
   - Create comprehensive tests

4. **Week 4: Advanced Features**
   - Implement advanced rules
   - Add analytics
   - Optimize performance

## Conclusion

This updated refactoring plan outlines a focused approach to implementing the distraction detector in the core_v2 architecture. By leveraging the improved architecture and abstractions in core_v2, we can create a modular, extensible, and testable distraction detection system that integrates seamlessly with the rest of the application.

The implementation roadmap provides a clear path forward, focusing on building the core infrastructure first, then implementing the main components, and finally adding advanced features and optimizations.
