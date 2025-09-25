# Blocking System

The blocking system provides a comprehensive framework for managing and enforcing access control policies across applications and domains in Focus Guard. It has been recently updated with improved error handling, better test coverage, and enhanced functionality.

## Overview

This system implements a flexible and extensible policy engine that can:
- Enforce time-based access restrictions
- Block domains and applications based on configurable rules
- Handle user overrides and temporary access grants
- Integrate with the activity monitoring system
- Support both domain-level and application-level blocking

## Key Components

### Core Components
- **Policy Engine**: Robust evaluation of resources against registered policies with circuit breaker protection
- **Event Handler**: Processes blocking-related events and triggers actions with improved error handling
- **Blocking Manager**: Main entry point with enhanced policy management and event handling
- **Policies**: Configurable rules with support for time-based, domain-based, and application-based blocking
- **Blocking Pipeline**: Strategy-based pipeline for flexible and extensible blocking decisions

### Policy Types
- **Time-based Policies**: Restrict access during specific time periods
- **Domain Policies**: Control access based on domain names and patterns
- **Application Policies**: Manage application access and usage
- **Content Policies**: Filter content based on classification

## Features

- **Flexible Policy Management**: Create, update, and remove blocking policies at runtime
- **Time-based Restrictions**: Define blocking rules based on time of day and day of week
- **Domain and Application Control**: Block or allow specific domains and applications
- **Graceful Degradation**: Circuit breaker pattern prevents cascading failures
- **Comprehensive Event System**: Detailed event tracking and notification system
- **Extensible Architecture**: Easy to add new blocking strategies and policies
- **Thread-safe Operations**: Safe for concurrent access from multiple threads

## Getting Started

### Prerequisites

- Python 3.8+
- Focus Guard core dependencies
- Required packages (see `requirements.txt`)

### Initialization

```python
from focus_guard.core.blocking.manager import BlockingManager
from focus_guard.core.blocking.events import EventType

# Create a new blocking manager
blocking_manager = BlockingManager()

# Enable the blocking system
blocking_manager.enable_blocking()

# Register an event callback
def on_blocking_event(event):
    if event.event_type == EventType.RESOURCE_ACCESS_BLOCKED:
        print(f"Blocked access to {event.resource_id}: {event.reason}")

blocking_manager.register_callback(EventType.RESOURCE_ACCESS_BLOCKED, on_blocking_event)
```

## Policy Management

### Policy Lifecycle

1. **Creation**: Define policies with specific rules and priorities
2. **Registration**: Add policies to the blocking manager
3. **Evaluation**: Policies are evaluated when checking resource access
4. **Removal**: Policies can be removed when no longer needed
5. **Persistence**: Save and load policy configurations

### Policy Types

#### Time-based Policy

```python
from focus_guard.core.blocking.policies.time_based import TimeBasedBlockingPolicy

# Create a policy that blocks access during work hours (9 AM to 5 PM, Mon-Fri)
work_hours_policy = TimeBasedBlockingPolicy.create(
    name="Work Hours Block",
    time_ranges=[
        {"start": "09:00", "end": "17:00"}
    ],
    days_of_week={0, 1, 2, 3, 4},  # Monday to Friday
    timezone="local",
    description="Blocks access during work hours",
    priority=10
)

# Add the policy to the blocking manager
blocking_manager.add_policy(work_hours_policy)
```

#### Domain-based Policy

```python
from focus_guard.core.blocking.policies.domain import DomainBlockingPolicy
from focus_guard.core.domain.models import Category

# Create a policy that blocks social media domains
social_media_policy = DomainBlockingPolicy.create(
    name="Block Social Media",
    blocked_categories={
        Category.SOCIAL_MEDIA
    },
    blocked_domains={
        "facebook.com",
        "twitter.com",
        "instagram.com"
    },
    description="Blocks access to social media platforms",
    priority=20
)

# Add the policy to the blocking manager
blocking_manager.add_policy(social_media_policy)
```

#### Application Policy

```python
from focus_guard.core.blocking.policies.application import ApplicationBlockingPolicy

# Create a policy that blocks gaming applications
gaming_policy = ApplicationBlockingPolicy.create(
    name="Block Gaming Apps",
    blocked_applications={
        "steam.exe",
        "battle.net.exe",
        "epicgameslauncher.exe"
    },
    description="Blocks gaming applications during work hours",
    priority=30
)

# Add the policy to the blocking manager
blocking_manager.add_policy(gaming_policy)
```

```python
from focus_guard.core.blocking.policies.domain import DomainBlockingPolicy
from focus_guard.core.domain.models import Category

# Create a policy that blocks social media domains
social_media_policy = DomainBlockingPolicy.create(
    name="Block Social Media",
    blocked_categories={
        Category.SOCIAL_MEDIA
    },
    blocked_domains={
        "facebook.com",
        "twitter.com",
        "instagram.com"
    },
    description="Blocks access to social media platforms",
    priority=20
)

# Add the policy to the blocking manager
blocking_manager.add_policy(social_media_policy)
```

## Advanced Usage

### Event Handling

The blocking system emits events for important actions and state changes. You can register callbacks to handle these events:

```python
from focus_guard.core.blocking.events import EventType

def on_policy_added(event):
    print(f"Policy added: {event.policy_name} ({event.policy_type})")
    print(f"Metadata: {event.metadata}")

# Register the callback
blocking_manager.register_callback(EventType.POLICY_ADDED, on_policy_added)
```

### Error Handling and Resilience

The blocking system includes built-in error handling and circuit breakers to prevent cascading failures:

```python
# Enable circuit breaker for external service calls
blocking_manager.enable_circuit_breaker(
    failure_threshold=5,  # Number of failures before opening the circuit
    recovery_timeout=60,  # Seconds before attempting to close the circuit
)
```

### Handling Resource Access

```python
from focus_guard.core.domain.models import Domain

# Check if a domain should be blocked
decision = blocking_manager.should_block("facebook.com")
if decision.should_block:
    print(f"Access blocked by policy: {decision.policy_name}")
    print(f"Reason: {decision.reason}")

# Handle an access attempt event
blocking_manager.handle_event({
    "event_type": "resource_access_attempt",
    "resource_type": "domain",
    "resource_id": "youtube.com",
    "metadata": {
        "user_id": "user123",
        "application": "chrome"
    }
})
```

## Advanced Usage

### Policy Overrides

```python
# Request a temporary override
blocking_manager.handle_event({
    "event_type": "override_requested",
    "resource_type": "domain",
    "resource_id": "youtube.com",
    "duration_seconds": 1800,  # 30 minutes
    "reason": "Educational video"
})
```

### Custom Event Handlers

```python
# Register a custom event handler
def on_override_granted(event):
    print(f"Override granted for {event.resource_id} for {event.duration_seconds} seconds")
    print(f"Reason: {event.reason}")

blocking_manager.register_callback(
    EventType.OVERRIDE_GRANTED,
    on_override_granted
)
```

## Configuration

### Loading and Saving Configuration

```python
# Save the current configuration to a file
blocking_manager.save_config("blocking_config.json")

# Load configuration from a file
blocking_manager.load_config("blocking_config.json")
```

## Integration

### Activity Monitoring

Integrate with the activity monitoring system to automatically enforce policies based on user activity:

```python
# Example integration with activity monitoring
def on_window_focus_changed(window_info):
    # Check if the window title contains a URL
    if "http" in window_info.title:
        domain = extract_domain_from_url(window_info.title)
        if domain:
            decision = blocking_manager.should_block(domain)
            if decision.should_block:
                # Take appropriate action (e.g., close tab, show warning)
                print(f"Blocked access to {domain}: {decision.reason}")

# Register the callback with the activity monitoring system
activity_monitor.on_window_focus_changed(on_window_focus_changed)
```

## Best Practices

1. **Policy Priority**: Set appropriate priorities for policies to ensure correct evaluation order
2. **Logging**: Use the built-in logging to track blocking decisions and policy changes
3. **Testing**: 
   - Write comprehensive unit tests for custom policies
   - Test edge cases and error conditions
   - Use the provided test fixtures for integration testing
4. **User Feedback**: Provide clear feedback when access is blocked, including the reason and how to request an override
5. **Performance**: 
   - Cache expensive policy evaluations when possible
   - Use circuit breakers for external service calls
   - Monitor and optimize policy evaluation performance
6. **Error Handling**:
   - Implement proper error handling in custom policies
   - Use the circuit breaker pattern for external dependencies
   - Log errors with sufficient context for debugging
    @property
    def name(self) -> str:
        return "my_strategy"
    
    @property
    def priority(self) -> int:
        return 50
    
    def should_block(self, domain: Domain) -> BlockingDecision:
        # Implement your blocking logic here
        if domain.name == "example.com":
            return BlockingDecision(
                should_block=True,
                reason=BlockingReason.OTHER,
                details="Custom blocking reason"
            )
        return BlockingDecision(should_block=False)
```

### Using the Blocking Pipeline
```python
from focus_guard.core.blocking.base import BlockingStrategyRegistry, BlockingPipeline
from focus_guard.core.domain.models import Domain

# Create registry and pipeline
registry = BlockingStrategyRegistry()
pipeline = BlockingPipeline(registry)

# Register strategies
registry.register(MyBlockingStrategy())

# Make blocking decisions
domain = Domain("example.com")
decision = pipeline.should_block(domain)
print(f"Should block: {decision.should_block}")
print(f"Reason: {decision.reason}")
print(f"Details: {decision.details}")
```

### Context-Aware Blocking
```python
from focus_guard.core.blocking.base import ContextAwareBlockingStrategy

class ContextAwareStrategy(ContextAwareBlockingStrategy):
    def should_block_with_context(
        self, domain: Domain, context: Dict[str, Any]
    ) -> BlockingDecision:
        # Use context information for more sophisticated blocking
        url = context.get("url", "")
        if "malware" in url.lower():
            return BlockingDecision(should_block=True, reason=BlockingReason.CONTENT_POLICY)
        return BlockingDecision(should_block=False)
```

## Architecture

The blocking system follows a pipeline pattern:
1. **Strategy Registration**: Strategies are registered with priorities
2. **Ordered Execution**: Strategies are executed in priority order (highest first)
3. **Early Termination**: Pipeline stops at the first strategy that decides to block
4. **Context Propagation**: Context information flows through the pipeline

## Integration Points

- **Classification**: Integrates with core.classification for category-based blocking
- **Configuration**: Uses core.config for dynamic blocking rules
- **API**: Exposed through core.api for external access
- **Domain**: Works with core.domain models for domain representation

## File Structure

```
blocking/
├── __init__.py             # Package initialization
├── base.py                 # Core interfaces and base classes
├── manager.py              # BlockingManager implementation
├── pipeline.py             # Blocking pipeline implementation
├── events.py               # Event types and handlers
├── policies/               # Policy implementations
│   ├── __init__.py
│   ├── base.py            # Base policy class
│   ├── time_based.py      # Time-based policies
│   ├── domain.py          # Domain-based policies
│   └── application.py     # Application-based policies
├── strategies/            # Blocking strategies
│   ├── __init__.py
│   ├── domain_excluder.py # Domain exclusion strategy
│   └── category_blocker.py # Category-based blocking strategy
└── tests/                 # Test files
    ├── __init__.py
    ├── test_manager.py    # Tests for BlockingManager
    ├── test_pipeline.py   # Tests for BlockingPipeline
    └── test_policies/     # Tests for individual policies
```

## Testing

The blocking system includes comprehensive test coverage. To run the tests:

```bash
# Run all blocking system tests
pytest focus_guard/tests/core/blocking/

# Run tests with coverage report
pytest --cov=focus_guard.core.blocking focus_guard/tests/core/blocking/
```

## Contributing

1. Follow the existing code style and patterns
2. Write tests for new features and bug fixes
3. Update documentation when changing behavior
4. Use meaningful commit messages
5. Create pull requests with clear descriptions of changes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
