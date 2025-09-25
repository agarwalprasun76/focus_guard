# Distraction Detector Refactoring Plan

## Overview

This document outlines the plan for refactoring and integrating the `core/distraction_detector` module with the new `core_v2/classification` and `core_v2/domain` modules. The goal is to leverage the improved architecture and abstractions in core_v2 while preserving the existing functionality of the distraction detector.

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

### Dependencies on Legacy Modules

1. **Domain Classification**
   - Depends on `core/domain_classifier/domain_classifier.py` for classifying domains
   - Uses `core/domain_classifier/domain_utils.py` for domain extraction and normalization
   - Uses `core/domain_classifier/domain_config.py` for domain configuration

2. **Browser Integration**
   - Integrates with `core/browser_integration/tab_server.py` for browser extension support
   - Uses `core/browser_integration/tab_tracker_integration.py` for tab tracking

3. **Logging**
   - Uses `core/logger/logger.py` for logging

### New Architecture in core_v2

1. **Domain Classification**
   - `core_v2/classification/base.py`: Defines the `Classifier` abstract base class
   - `core_v2/classification/domain_classifier.py`: Implements `StandardDomainClassifier`
   - `core_v2/domain/models.py`: Defines `Domain` and `Category` models
   - `core_v2/domain/constants.py`: Defines category mappings

2. **Configuration**
   - `core_v2/config/loader.py`: Loads configuration with change notifications
   - Supports schema-based validation

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
    detector.py              # DistractionDetector implementation
    interfaces.py            # Core interfaces and abstract classes
    models.py                # Distraction models (Alert, State, etc.)
    rules/
      __init__.py
      base.py                # DistractionRule base class
      app_rules.py           # Application-based rules
      url_rules.py           # URL-based rules
      time_rules.py          # Time-based rules
    trackers/
      __init__.py
      browser_tracker.py     # Browser activity tracker
      app_tracker.py         # Application activity tracker
    handlers/
      __init__.py
      alert_handler.py       # AlertHandler interface
      popup_handler.py       # Popup alert handler
      log_handler.py         # Logging alert handler
    utils/
      __init__.py
      state_utils.py         # State management utilities
      detection_utils.py     # Detection utilities
```

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

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
   - Implement state persistence

### Phase 2: URL and Browser Integration (Week 1-2)

1. **Implement URL Rules**
   - Port `URLRule` to core_v2
   - Integrate with `core_v2/classification`
   - Implement domain-based rules

2. **Create Browser Tracker**
   - Port `BrowserTabTracker` to core_v2
   - Integrate with browser extension
   - Implement tab state management

3. **Implement Alert Handlers**
   - Create alert handler interface
   - Implement basic handlers (log, popup)
   - Support alert escalation

### Phase 3: Main Detector and Integration (Week 2-3)

1. **Implement DistractionDetector**
   - Port core functionality to core_v2
   - Integrate with rules and handlers
   - Implement configuration integration

2. **Create Adapters for Legacy Code**
   - Implement adapters for legacy interfaces
   - Support backward compatibility
   - Gradual migration path

3. **Add Testing Infrastructure**
   - Create unit tests for all components
   - Implement mocks for external dependencies
   - Test integration points

### Phase 4: Advanced Features and Optimization (Week 3-4)

1. **Implement Advanced Rules**
   - Add time-based rules
   - Add pattern-based rules
   - Support rule composition

2. **Optimize Performance**
   - Implement caching for frequent operations
   - Optimize rule evaluation
   - Reduce memory footprint

3. **Add Analytics Support**
   - Implement distraction analytics
   - Create reporting interfaces
   - Support data export

## Migration Strategy

### Step 1: Parallel Implementation

1. Create the new distraction detector in `core_v2/distraction`


### Step 2: Incremental Migration

1. Update one component at a time to use the new system
2. Start with rules, then trackers, then handlers
3. Finally, replace the main detector


## Code Examples

### DistractionRule Interface

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
        """
        Get the name of the rule.
        
        Returns:
            The name of the rule.
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Get the description of the rule.
        
        Returns:
            The description of the rule.
        """
        pass
    
    @abstractmethod
    def check(self, state: DistractionState) -> List[DistractionAlert]:
        """
        Check for distractions based on the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            A list of distraction alerts, or an empty list if no distractions.
        """
        pass
    
    @abstractmethod
    def should_apply(self, state: DistractionState) -> bool:
        """
        Determine if this rule should be applied to the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            True if the rule should be applied, False otherwise.
        """
        pass
```

### URLRule Implementation

```python
# core_v2/distraction/rules/url_rules.py
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from core_v2.distraction.interfaces import DistractionRule
from core_v2.distraction.models import DistractionAlert, DistractionState, AlertLevel
from core_v2.classification.domain_classifier import StandardDomainClassifier
from core_v2.domain.models import Domain, Category
from core_v2.utils.domain_utils import extract_domain_from_url

class URLRule(DistractionRule):
    """
    Rule for detecting distractions based on URLs in browser windows.
    
    This rule checks if the active window contains a URL that is classified
    as a distraction based on its domain category.
    """
    
    def __init__(
        self,
        domain_classifier: StandardDomainClassifier,
        productive_categories: Optional[List[str]] = None,
        distracting_categories: Optional[List[str]] = None,
        domain_whitelist: Optional[Set[str]] = None
    ):
        """
        Initialize the URL rule.
        
        Args:
            domain_classifier: The domain classifier to use.
            productive_categories: List of domain categories considered productive.
            distracting_categories: List of domain categories considered distracting.
            domain_whitelist: Set of domains that are always allowed.
        """
        self._domain_classifier = domain_classifier
        self._productive_categories = productive_categories or [
            "work", "education", "productivity", "development", "email"
        ]
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
        Determine if this rule should be applied to the current state.
        
        Args:
            state: The current distraction state.
            
        Returns:
            True if the active window is a browser, False otherwise.
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
            A list of distraction alerts, or an empty list if no distractions.
        """
        alerts = []
        
        # Skip if rule should not apply
        if not self.should_apply(state):
            return alerts
            
        active_window = state.active_window
        window_title = active_window.get('window_title', '')
        
        # Extract URL from window title
        url = self._extract_url_from_title(window_title)
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
            if classification and classification.category_str in self._distracting_categories:
                alert = DistractionAlert(
                    source="url",
                    level=AlertLevel.WARNING,
                    message=f"Distracting website detected: {domain_str} ({classification.category_str})",
                    metadata={
                        "url": url,
                        "domain": domain_str,
                        "category": classification.category_str,
                        "window_title": window_title,
                        "app_name": active_window.get('app_name', '')
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
        Check if an application is a browser.
        
        Args:
            app_name: The name of the application.
            
        Returns:
            True if the application is a browser, False otherwise.
        """
        browsers = [
            "chrome", "firefox", "edge", "msedge", "opera", "safari",
            "brave", "vivaldi", "chromium"
        ]
        return any(browser in app_name for browser in browsers)
    
    def _extract_url_from_title(self, title: str) -> Optional[str]:
        """
        Extract a URL from a window title.
        
        Args:
            title: The window title.
            
        Returns:
            The URL if found, None otherwise.
        """
        # Implementation of URL extraction logic
        # This would use regex or other methods to extract URLs from titles
        pass
```

### DistractionDetector Implementation

```python
# core_v2/distraction/detector.py
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime
import logging

from core_v2.distraction.interfaces import DistractionRule
from core_v2.distraction.models import DistractionAlert, DistractionState, AlertLevel
from core_v2.config.loader import ConfigurationLoader

class DistractionDetector:
    """
    Detector for identifying distractions based on user activity.
    
    This class coordinates the evaluation of distraction rules and
    the handling of distraction alerts.
    """
    
    def __init__(
        self,
        config_loader: ConfigurationLoader,
        rules: Optional[List[DistractionRule]] = None,
        alert_handlers: Optional[List[Callable[[DistractionAlert], None]]] = None
    ):
        """
        Initialize the distraction detector.
        
        Args:
            config_loader: The configuration loader to use.
            rules: List of distraction rules to apply.
            alert_handlers: List of handlers for distraction alerts.
        """
        self._config_loader = config_loader
        self._rules = rules or []
        self._alert_handlers = alert_handlers or []
        self._state = DistractionState()
        self._logger = logging.getLogger("core_v2.distraction.detector")
        
        # Load configuration
        self._load_configuration()
        
        # Register for configuration changes
        self._config_loader.register_change_callback(self._on_config_changed)
    
    def _load_configuration(self) -> None:
        """Load configuration settings."""
        config = self._config_loader.distraction_detection
        
        # Load allowed apps
        self._allowed_apps = set(config.get("allowed_apps", []))
        
        # Load distraction thresholds
        self._distraction_thresholds = config.get("distraction_thresholds", {})
        
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
    
    def add_alert_handler(self, handler: Callable[[DistractionAlert], None]) -> None:
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
        
        # Call all alert handlers
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self._logger.error(f"Error in alert handler: {e}")
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

## Conclusion

This refactoring plan outlines a comprehensive approach to modernizing the distraction detector in FocusGuard. By integrating with the core_v2 modules and leveraging their improved architecture, we can significantly enhance the functionality, maintainability, and extensibility of the distraction detection system.

The phased implementation approach allows for incremental migration with minimal disruption to existing functionality, while the flexible architecture ensures that the system can grow and adapt to future requirements.
