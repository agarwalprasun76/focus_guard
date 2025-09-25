# API Module

The API module provides the main programmatic interface for Focus Guard's domain classification and blocking functionality.

## Overview

This module serves as the unified entry point for:
- Domain classification (categorizing websites into categories like social media, entertainment, etc.)
- Blocking decisions (determining whether to block access to specific URLs)
- Configuration management and reloading
- Integration with classifiers and blocking strategies

## Key Components

### ClassifierBlockerAPI
The main API class that integrates all components:
- **Domain Classification**: Uses registered classifiers to categorize domains
- **Blocking Logic**: Applies blocking strategies based on classification results
- **Caching**: Implements intelligent caching for performance optimization
- **Configuration**: Supports dynamic configuration reloading

### Server Components
- **server.py**: HTTP server implementation for remote API access
- **compat.py**: Backward compatibility layer for legacy API endpoints
- **api.py**: Core API functionality and integration layer

## Usage

### Basic Classification
```python
from focus_guard.core.api.api import api

# Classify a domain
category = api.classify_domain("facebook.com")
print(f"Facebook is classified as: {category}")

# Check if a URL should be blocked
should_block = api.should_block_tab("https://facebook.com")
print(f"Should block: {should_block}")
```

### Context-Aware Classification
```python
# Provide additional context for better classification
context = {
    "page_title": "Facebook - Log In or Sign Up",
    "user_agent": "Mozilla/5.0..."
}
category = api.classify_domain_with_context("facebook.com", context)
```

### Configuration Reloading
```python
# Reload configuration without restarting
api.reload_configuration()
```

## Architecture

The API follows a modular design:
1. **Classifier Registry**: Manages multiple domain classifiers
2. **Blocking Pipeline**: Coordinates blocking strategies with configurable priorities
3. **Caching Layer**: Reduces redundant classification requests
4. **Configuration System**: Supports dynamic updates and provider switching

## Integration Points

- **Classification**: Integrates with core.classification components
- **Blocking**: Uses core.blocking strategies and pipelines
- **Configuration**: Leverages core.config for settings management
- **Cache**: Utilizes core.cache for performance optimization

## Dependencies

- `focus_guard.core.classification`: Domain classification logic
- `focus_guard.core.blocking`: Blocking strategies and decision making
- `focus_guard.core.config`: Configuration management
- `focus_guard.core.cache`: Caching mechanisms
