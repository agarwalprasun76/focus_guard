# Distraction Detector Module

The `core_v2.distraction` module provides a modular, extensible framework for detecting and responding to distractions in the Focus Guard application.

## Architecture

The distraction detector module follows a clean, modular architecture with the following key components:

### Core Components

1. **Interfaces** (`interfaces.py`): Defines the core interfaces for the module:
   - `DistractionRule`: Interface for distraction detection rules
   - `AlertHandler`: Interface for handling distraction alerts
   - `DistractionDetector`: Interface for the main detector
   - `BrowserActivityTracker`: Interface for tracking browser activity

2. **Models** (`models.py`): Defines the core data models:
   - `AlertLevel`: Enum for alert severity (INFO, WARNING, CRITICAL)
   - `DistractionAlert`: Represents alerts with metadata and timestamp
   - `DistractionState`: Represents current state with active windows, browser tabs, and alert history

3. **Configuration** (`config.py`): Defines configuration schemas:
   - Rule-specific configurations (URL, context switch, area increase)
   - Handler configurations (notification, blocking)
   - Global distraction detector configuration

4. **Detector** (`detector.py`): Implements the main distraction detector:
   - `StandardDistractionDetector`: Coordinates rule evaluation and alert handling

### Rules

Rules detect specific types of distractions based on user activity:

1. **URL Rule** (`rules/url_rule.py`): Detects distracting websites based on domain classification
2. **Context Switch Rule** (`rules/context_rule.py`): Detects excessive context switching between applications
3. **Area Increase Rule** (`rules/area_rule.py`): Detects sudden increases in window area (e.g., maximizing video players)

### Trackers

Trackers monitor user activity and provide input to the distraction detector:

1. **Browser Tracker** (`trackers/browser_tracker.py`): Tracks browser tabs and their content

### Handlers

Handlers respond to distraction alerts:

1. **Notification Handler** (`handlers/notification_handler.py`): Displays notifications to the user
2. **Blocking Handler** (`handlers/blocking_handler.py`): Blocks distracting content

### Factory

The factory (`factory.py`) provides a convenient way to create and assemble distraction detector components with proper configuration and dependencies.

## Usage

### Basic Usage

```python
from core_v2.distraction.factory import DistractionDetectorFactory
from core_v2.config.manager import DefaultConfigurationManager
from core_v2.classification.factory import ClassifierFactory
from core_v2.browser.integration import StandardBrowserIntegration
from core_v2.alert.provider import AlertProvider

# Create dependencies
config_manager = DefaultConfigurationManager()
domain_classifier = ClassifierFactory(config_manager).create_classifier()
browser_integration = StandardBrowserIntegration()
alert_provider = AlertProvider()

# Create distraction detector factory
factory = DistractionDetectorFactory(
    config_manager=config_manager,
    domain_classifier=domain_classifier,
    browser_integration=browser_integration,
    alert_provider=alert_provider
)

# Create distraction detector
detector = factory.create_detector()

# Use the detector
# The detector will automatically receive updates from the browser tracker
# and trigger alerts when distractions are detected
```

### Custom Rules

You can create custom distraction rules by extending the `BaseDistractionRule` class:

```python
from core_v2.distraction.rules.base import BaseDistractionRule
from core_v2.distraction.models import DistractionAlert, DistractionState, AlertLevel

class CustomRule(BaseDistractionRule):
    @property
    def name(self) -> str:
        return "Custom Rule"
    
    @property
    def description(self) -> str:
        return "A custom distraction rule"
    
    def should_apply(self, state: DistractionState) -> bool:
        # Determine if the rule should be applied
        return True
    
    def check(self, state: DistractionState) -> List[DistractionAlert]:
        # Check for distractions
        alerts = []
        
        # Add alerts if distractions are detected
        if distraction_detected:
            alert = self.create_alert(
                message="Custom distraction detected",
                level=AlertLevel.WARNING,
                metadata={"key": "value"}
            )
            alerts.append(alert)
        
        return alerts
```

### Custom Handlers

You can create custom alert handlers by implementing the `AlertHandler` interface:

```python
from core_v2.distraction.interfaces import AlertHandler
from core_v2.distraction.models import DistractionAlert

class CustomHandler(AlertHandler):
    @property
    def name(self) -> str:
        return "Custom Handler"
    
    def can_handle(self, alert: DistractionAlert) -> bool:
        # Determine if the handler can handle the alert
        return True
    
    def handle(self, alert: DistractionAlert) -> None:
        # Handle the alert
        print(f"Custom handler handling alert: {alert.message}")
```

## Configuration

The distraction detector is highly configurable through the configuration system. Here's an example configuration:

```python
from core_v2.distraction.config import DistractionConfig, URLRuleConfig

# Create configuration
config = DistractionConfig(
    enabled=True,
    productive_categories=["work", "education", "productivity"],
    distracting_categories=["social", "entertainment", "shopping"],
    domain_whitelist=["example.com"]
)

# Configure URL rule
url_rule_config = URLRuleConfig(
    enabled=True,
    distracting_categories=["social", "entertainment"],
    domain_whitelist=["twitter.com"]  # Whitelist specific domains
)

# Add rule configuration
config.rules["url_rule"] = url_rule_config

# Set configuration
config_manager.set("distraction", config)
```

## Integration

The distraction detector integrates with other core_v2 modules:

1. **Classification**: Uses the domain classifier to classify websites
2. **Browser**: Uses the browser integration to track browser tabs and block distracting content
3. **Alert**: Uses the alert provider to display notifications and alerts
4. **Configuration**: Uses the configuration system for settings and dynamic reloads

## Testing

The module includes comprehensive unit tests in the `tests/core_v2/distraction` directory with a structured organization:

```
tests/core_v2/distraction/
├── handlers/                # Tests for specific handlers
│   ├── test_blocking_handler.py
│   └── test_notification_handler.py
├── rules/                   # Tests for specific rules
│   ├── test_area_rule.py
│   ├── test_base_rule.py
│   ├── test_context_rule.py
│   └── test_url_rule.py
├── trackers/                # Tests for trackers
│   └── test_browser_tracker.py
├── test_handlers.py         # Combined handler tests
├── test_models.py           # Tests for core data models
└── test_rules.py            # Combined rule tests
```

Run the tests using pytest:

```
pytest tests/core_v2/distraction
```
