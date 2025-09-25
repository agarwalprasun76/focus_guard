# Focus Guard Classification Module

This module provides the core domain classification system for Focus Guard, enabling intelligent categorization of websites and applications to support productivity-focused filtering and monitoring.

## 🎯 Overview

The classification module determines the category of domains (websites/applications) based on their content, URL patterns, and contextual information. It supports both synchronous rule-based classification and asynchronous LLM-powered classification with a flexible, protocol-based architecture.

## 📁 Module Structure

```
focus_guard/core/classification/
├── README.md                 # This documentation file
├── __init__.py               # Package initialization
├── base.py                   # Core interfaces and synchronous pipeline
├── async_pipeline.py         # Asynchronous pipeline for async classifiers
├── sync_wrapper.py          # Sync wrapper utilities for async classifiers
├── models/                  # Domain models and data structures
│   └── __init__.py
├── classifiers/             # Individual classifier implementations
│   ├── __init__.py
│   ├── domains/             # Domain-specific classifiers
│   │   ├── __init__.py
│   │   ├── base.py         # Base domain classifier interface
│   │   ├── youtube.py      # YouTube classifier (deprecated)
│   │   ├── youtube_base.py # Base YouTube classifier
│   │   ├── youtube_llm.py  # YouTube LLM classifier
│   │   ├── youtube_rules.py # YouTube rule-based classifier
│   │   ├── youtube_llm_factory.py # YouTube LLM factory
│   │   └── youtube_rules_factory.py # YouTube rules factory
│   └── llm/                # LLM-based classifiers
│       ├── __init__.py
│       ├── base_llm.py     # Base LLM classifier interface
│       └── local_llm.py    # Local LLM classifier implementation
```

## 🏗️ Architecture

### Protocol-Based Design

The module uses Python protocols (interfaces) for maximum flexibility:

- **Classifier**: Basic domain classification interface
- **ContextAwareClassifier**: Extended interface for context-aware classification
- **FlexibleClassifierAdapter**: Automatic sync/async handling

### Pipeline Architecture

#### Synchronous Pipeline (`base.py`)
```python
ClassificationPipeline
├── Handles both sync and async classifiers
├── Automatic method detection (sync/async)
├── Graceful error handling
└── Backward compatible with existing code
```

#### Asynchronous Pipeline (`async_pipeline.py`)
```python
AsyncClassificationPipeline
├── Full async/await support
├── Non-blocking I/O operations
├── Concurrent classifier execution
└── Ideal for LLM-heavy workloads
```

## 🔧 Core Components

### Classifier Interface

```python
class Classifier(Protocol):
    """Flexible classifier supporting both sync and async methods."""
    
    @property
    def name(self) -> str
    def classify(self, domain: Domain) -> Optional[Category]
    # Can be sync or async method
```

### Context-Aware Classifier

```python
class ContextAwareClassifier(Classifier, Protocol):
    """Extended classifier with context support."""
    
    def classify_with_context(
        self, 
        domain: Domain, 
        context: Dict[str, Any]
    ) -> Optional[Classification]
    # Can be sync or async method
```

### Classification Result

```python
@dataclass
class Classification:
    domain: Domain
    category: Category
    confidence: float
    metadata: Dict[str, Any]
```

## 🚀 Usage Examples

### Basic Usage (Synchronous)

```python
from focus_guard.core.classification.base import ClassificationPipeline, ClassifierRegistry

# Create registry and pipeline
registry = ClassifierRegistry()
pipeline = ClassificationPipeline(registry)

# Register classifiers
pipeline.add_classifier("youtube_rule_based")
pipeline.add_classifier("youtube_llm")

# Classify a domain
result = pipeline.classify(
    Domain("youtube.com"),
    context={"url": "https://youtube.com/watch?v=123", "title": "Tutorial"}
)
```

### Async Usage

```python
from focus_guard.core.classification.async_pipeline import AsyncClassificationPipeline

# Create async pipeline
async_pipeline = AsyncClassificationPipeline(registry)

# Async classification
result = await async_pipeline.classify(
    Domain("youtube.com"),
    context={"url": "https://youtube.com/watch?v=123"}
)
```

### Adding Custom Classifiers

```python
from focus_guard.core.classification.base import ClassifierRegistry

# Register a custom classifier
registry.register(MyCustomClassifier())

# Use with existing pipeline
pipeline.add_classifier("my_custom_classifier")
```

## 🧪 Testing

The module includes comprehensive tests:

- **74 tests passing** ✅
- **7 tests skipped** (due to missing LLM dependencies)
- **0 failing tests** ✅

### Test Categories

- **Unit Tests**: Individual classifier functionality
- **Integration Tests**: Pipeline behavior and classifier interactions
- **Protocol Tests**: Interface compliance verification
- **Mock Tests**: External dependency handling

### Running Tests

```bash
# Run all classification tests
python -m pytest focus_guard/tests/core/classification/ -v

# Run specific test categories
python -m pytest focus_guard/tests/core/classification/test_base.py -v
python -m pytest focus_guard/tests/core/classification/test_integration.py -v
```

## 🎯 Classification Categories

The system supports these categories:

- **SOCIAL_MEDIA**: Social platforms and communication
- **ENTERTAINMENT**: Streaming, gaming, and entertainment
- **EDUCATION**: Learning platforms and educational content
- **PRODUCTIVITY**: Work-related tools and applications
- **SHOPPING**: E-commerce and shopping sites
- **NEWS**: News websites and current events
- **ADULT**: Adult content and mature themes

## 🔧 Configuration

### Environment Variables

```bash
# LLM Configuration
FOCUS_GUARD_LLM_API_KEY=your_api_key
FOCUS_GUARD_LLM_MODEL=gpt-3.5-turbo
FOCUS_GUARD_LLM_TIMEOUT=30

# Classification Settings
FOCUS_GUARD_CACHE_TTL=3600
FOCUS_GUARD_MAX_CLASSIFIERS=10
```

### Registry Configuration

```python
# Configure classifier registry
registry = ClassifierRegistry()
registry.set_config({
    "cache_ttl": 3600,
    "max_classifiers": 10,
    "timeout": 30
})
```

## 🔄 Migration Guide

### From Sync to Async

The flexible architecture allows gradual migration:

1. **Keep existing sync classifiers** - they continue to work unchanged
2. **Add async classifiers** - new async classifiers work alongside sync ones
3. **Use sync wrappers** - wrap async classifiers for sync contexts if needed
4. **Gradual transition** - migrate to async pipeline when ready

### Example Migration

```python
# Before: Sync only
class MySyncClassifier:
    def classify(self, domain: Domain) -> Optional[Category]:
        return Category.PRODUCTIVITY

# After: Flexible (can be sync or async)
class MyFlexibleClassifier:
    async def classify(self, domain: Domain) -> Optional[Category]:
        # Can now use async operations
        return await some_async_classification(domain)
```

## 📊 Performance Considerations

### Sync Classifiers
- **Pros**: Simple, no event loop management, predictable
- **Cons**: May block on I/O operations
- **Use Case**: Rule-based classification, simple pattern matching

### Async Classifiers
- **Pros**: Non-blocking I/O, better for LLM operations, scalable
- **Cons**: More complex, requires async context
- **Use Case**: LLM-powered classification, external API calls

## 🔍 Troubleshooting

### Common Issues

1. **Async/Sync Mismatch**: Use flexible classifier interface
2. **Missing Dependencies**: Install optional LLM dependencies
3. **Timeout Issues**: Adjust timeout settings
4. **Registry Issues**: Ensure classifiers are properly registered

### Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('focus_guard.classification')
```

## 🤝 Contributing

When adding new classifiers:

1. **Follow protocol interfaces** - implement required methods
2. **Add comprehensive tests** - include both unit and integration tests
3. **Document classifier behavior** - explain classification logic
4. **Handle edge cases** - provide graceful error handling

## 📈 Future Enhancements

- **Machine learning classifiers** - ML-based classification models
- **Real-time learning** - adaptive classification based on user behavior
- **Multi-language support** - international domain classification
- **Performance monitoring** - classification accuracy and latency metrics

## 🔗 Related Modules

- **focus_guard.core.domain**: Domain models and data structures
- **focus_guard.core.events**: Event system for classification notifications
- **focus_guard.core.cache**: Caching layer for classification results
- **focus_guard.core.config**: Configuration management for classifiers
