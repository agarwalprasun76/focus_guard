# Cache Module

The cache module provides in-memory caching solutions for temporary data storage with automatic expiration and performance monitoring.

## Overview

This module implements lightweight, in-memory caching for Focus Guard components that need to:
- Store computed values temporarily
- Reduce redundant expensive operations
- Monitor cache performance and hit rates
- Automatically expire stale data

## Key Components

### MemoryCache
The primary caching class providing:
- **TTL Support**: Automatic expiration of cache entries
- **Generic Typing**: Type-safe caching for any data type
- **Statistics**: Hit/miss tracking and cache performance metrics
- **Cleanup**: Automatic and manual cleanup of expired entries
- **Thread Safety**: Safe concurrent access patterns

## Features

- **Configurable TTL**: Per-entry or default expiration times
- **Hit/Miss Tracking**: Performance monitoring capabilities
- **Automatic Cleanup**: Expired entries are removed automatically
- **Statistics**: Detailed cache usage metrics
- **Generic Support**: Works with any data type
- **Lightweight**: Minimal memory and CPU overhead

## Usage

### Basic Usage
```python
from focus_guard.core.cache.memory_cache import MemoryCache

# Create a cache with 1-hour default TTL
cache = MemoryCache[str](default_ttl=3600)

# Store a value
cache.set("user_preference", "work_mode")

# Retrieve a value
value = cache.get("user_preference")
print(value)  # Output: "work_mode"

# Store with custom TTL
cache.set("temporary_data", "expires_soon", ttl=60)
```

### Advanced Usage
```python
# Cache expensive computations
def expensive_classification(domain):
    # Simulate expensive operation
    return f"classified_{domain}"

# Use get_or_set for automatic caching
result = cache.get_or_set(
    "facebook.com", 
    lambda: expensive_classification("facebook.com")
)

# Monitor cache performance
stats = cache.stats()
print(f"Cache hits: {stats['hits']}")
print(f"Cache misses: {stats['misses']}")
print(f"Valid entries: {stats['valid_entries']}")
```

### Cache Management
```python
# Manual cleanup of expired entries
removed_count = cache.cleanup()
print(f"Removed {removed_count} expired entries")

# Clear entire cache
cache.clear()

# Update default TTL
cache.set_default_ttl(7200)  # 2 hours
```

## Integration Patterns

### Classification Caching
```python
# Cache domain classification results
classification_cache = MemoryCache[Category](default_ttl=3600)

# Check cache before expensive classification
category = classification_cache.get(domain_name)
if category is None:
    category = perform_classification(domain_name)
    classification_cache.set(domain_name, category)
```

### API Response Caching
```python
# Cache API responses
api_cache = MemoryCache[Dict](default_ttl=300)

def get_user_preferences(user_id):
    cached_prefs = api_cache.get(f"user_prefs_{user_id}")
    if cached_prefs is None:
        cached_prefs = fetch_user_preferences(user_id)
        api_cache.set(f"user_prefs_{user_id}", cached_prefs)
    return cached_prefs
```

## Performance Characteristics

- **O(1) Operations**: All cache operations are constant time
- **Memory Efficient**: Only stores active entries
- **Automatic Cleanup**: No manual memory management required
- **Statistics**: Built-in performance monitoring
- **Thread Safe**: Safe for concurrent access patterns

## Best Practices

1. **Choose Appropriate TTL**: Balance freshness vs. performance
2. **Use Descriptive Keys**: Include context in cache keys
3. **Monitor Statistics**: Track hit/miss ratios for optimization
4. **Cleanup Regularly**: Periodically clean expired entries
5. **Generic Typing**: Use type hints for better IDE support

## Integration Points

- **Classification**: Cache domain classification results
- **API**: Cache expensive API responses
- **Configuration**: Cache configuration lookups
- **Blocking**: Cache blocking decisions
- **Domain**: Cache domain information queries

## Dependencies

- **Standard Library**: Uses only Python standard library modules
- **No External Dependencies**: Lightweight and portable
- **Type Hints**: Full typing support for better development experience
