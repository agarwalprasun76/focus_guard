# Domain Classification and Blocking System Refactoring Plan

## Overview

This document outlines the detailed plan for refactoring the domain classification and blocking system in Focus Guard. The goal is to create a more modular, maintainable, and extensible architecture while preserving the existing business logic and functionality.

## Current Architecture

The current system consists of several interconnected components:

1. **Domain Classifier** (`domain_classifier.py`): Classifies domains into categories
2. **Domain Configuration** (`domain_config.py`): Centralized domain category definitions
3. **Domain Excluder** (`domain_excluder.py`): Excludes domains based on StevenBlack hosts
4. **Classifier Blocker API** (`classifier_blocker_api.py`): Integration layer for blocking decisions
5. **YouTube Classifier** (`youtube_classifier.py`): Specialized classifier for YouTube content

## Identified Issues

1. **Tight Coupling**: Components are tightly coupled with direct imports
2. **Inconsistent Abstraction Levels**: Mixing of high and low-level concerns
3. **Multiple Sources of Truth**: Domain categories, exclusion lists, whitelist in different places
4. **Complex Decision Flow**: Multiple layers of decision-making with hardcoded precedence
5. **Limited Extensibility**: Adding new classification methods requires modifying existing code
6. **Caching Inconsistencies**: Multiple caching mechanisms with different TTLs
7. **Error Handling**: Inconsistent error handling across components
8. **Configuration Management**: Static configuration in code

## Refactoring Strategy

We will create a new `core_v2` module with a clean, modular architecture while preserving the existing business logic. The approach is:

1. Create a clean directory structure with clear separation of concerns
2. Define clean interfaces for all components
3. Port existing functionality to the new structure
4. Create adapters for complex components like the YouTube classifier
5. Improve incrementally, focusing on modularity and testability

## Directory Structure

```
core_v2/
├── __init__.py
├── domain/                 # Domain models and core entities
│   ├── __init__.py
│   ├── models.py           # Core domain models (Domain, Category, etc.)
│   └── constants.py        # Constants from existing code
├── classification/         # Classification services
│   ├── __init__.py
│   ├── base.py             # Base classifier interface
│   ├── domain_classifier.py # Port of existing domain classifier
│   └── classifiers/        # Specialized classifiers
│       ├── __init__.py
│       ├── youtube.py      # Adapter for existing YouTube classifier
│       └── registry.py     # Classifier registry
├── blocking/              # Blocking strategies
│   ├── __init__.py
│   ├── base.py            # Base blocking strategy interface
│   ├── category_blocker.py # Port of existing category blocking
│   ├── domain_excluder.py  # Port of existing domain excluder
│   └── pipeline.py        # Decision pipeline
├── config/                # Configuration management
│   ├── __init__.py
│   └── loader.py          # Configuration loader
├── cache/                 # Caching services
│   ├── __init__.py
│   └── memory_cache.py    # In-memory cache implementation
├── utils/                 # Utility functions
│   ├── __init__.py
│   └── domain_utils.py    # Port of existing domain utilities
└── api.py                 # Main API entry point
```

## Detailed Implementation Plan

### Phase 1: Foundation (Core Structure and Interfaces)

1. **Create Directory Structure**
   - Set up the `core_v2` directory and subdirectories
   - Create empty `__init__.py` files for each package

2. **Define Core Domain Models**
   - Create `domain/models.py` with:
     - `Domain` class for normalized domains
     - `Category` class for domain categories
     - `ClassificationResult` class for standardized results
     - `TabInfo` class for tab information

3. **Define Base Interfaces**
   - Create `classification/base.py` with:
     - `Classifier` interface for all classifiers
     - `DomainClassifier` interface for domain classifiers
   - Create `blocking/base.py` with:
     - `BlockingStrategy` interface for blocking strategies
     - `BlockingPipeline` class for executing strategies

4. **Create Configuration Loader**
   - Create `config/loader.py` with:
     - `ConfigLoader` class for loading and managing configuration
     - Methods to access domain categories, whitelist, etc.

5. **Create Utility Functions**
   - Port essential utilities to `utils/domain_utils.py`:
     - Domain normalization
     - Domain validation
     - URL parsing

### Phase 2: Core Classification (Domain and Category Classification)

1. **Port Domain Classifier**
   - Create `classification/domain_classifier.py` with:
     - `StandardDomainClassifier` class that implements `DomainClassifier`
     - Port the core classification logic from existing code
     - Adapt to use the new domain models

2. **Create Classifier Registry**
   - Create `classification/classifiers/registry.py` with:
     - `ClassifierRegistry` class for managing classifiers
     - Methods to register and retrieve classifiers by priority

3. **Port Domain Configuration**
   - Create `domain/constants.py` with:
     - Domain categories from `domain_config.py`
     - Whitelist domains
     - Application domains

4. **Implement Caching**
   - Create `cache/memory_cache.py` with:
     - `MemoryCache` class for in-memory caching
     - TTL support for cached items
     - Methods to get, set, and clear cache

### Phase 3: Specialized Classification (YouTube and Context-Aware)

1. **Create YouTube Classifier Adapter**
   - Create `classification/classifiers/youtube.py` with:
     - `YouTubeClassifierAdapter` class that adapts the existing YouTube classifier
     - Methods to map between old and new data structures
     - Preserve the existing classification logic

2. **Port Content-Aware Classification**
   - Create adapters for other specialized classifiers
   - Ensure they work with the new interfaces

### Phase 4: Blocking Strategies

1. **Port Domain Excluder**
   - Create `blocking/domain_excluder.py` with:
     - `DomainExcluderStrategy` class that implements `BlockingStrategy`
     - Port the existing domain exclusion logic
     - Adapt to use the new domain models

2. **Implement Category Blocker**
   - Create `blocking/category_blocker.py` with:
     - `CategoryBlockingStrategy` class that implements `BlockingStrategy`
     - Logic to block based on domain category

3. **Create Blocking Pipeline**
   - Implement `blocking/pipeline.py` with:
     - Methods to execute multiple blocking strategies
     - Priority-based decision making

### Phase 5: Main API and Integration

1. **Create Main API**
   - Implement `api.py` with:
     - `ClassifierBlockerAPI` class as the main entry point
     - Methods to classify domains and determine if tabs should be blocked
     - Integration with classifier registry and blocking pipeline

2. **Testing Strategy**
   - Implement comprehensive unit and integration tests
   - Create test fixtures and mocks for external dependencies
   - Ensure compatibility with existing tests
   - Use test-driven development where appropriate

### Phase 6: Migration and Cleanup

1. **Update Application to Use New API**
   - Modify the main application to use the new `core_v2` module
   - Ensure backward compatibility where needed

2. **Documentation**
   - Update documentation to reflect the new architecture
   - Add examples and usage guidelines

3. **Performance Optimization**
   - Identify and address any performance bottlenecks
   - Optimize caching strategies

## Task Tracking

| Task | Status | Notes |
|------|--------|-------|
| Create directory structure | Not Started | |
| Define core domain models | Not Started | |
| Define base interfaces | Not Started | |
| Create configuration loader | Not Started | |
| Port domain utilities | Not Started | |
| Port domain classifier | Not Started | |
| Create classifier registry | Not Started | |
| Port domain configuration | Not Started | |
| Implement caching | Not Started | |
| Create YouTube classifier adapter | Not Started | |
| Port domain excluder | Not Started | |
| Implement category blocker | Not Started | |
| Create blocking pipeline | Not Started | |
| Create main API | Not Started | |
| Write tests | Not Started | |
| Update application | Not Started | |
| Update documentation | Not Started | |
| Performance optimization | Not Started | |

## Key Design Principles

1. **Separation of Concerns**: Each component has a single responsibility
2. **Interface-Based Design**: Components interact through well-defined interfaces
3. **Dependency Inversion**: High-level modules don't depend on low-level modules
4. **Open/Closed Principle**: Open for extension, closed for modification
5. **Composition Over Inheritance**: Favor composition over inheritance for flexibility

## Migration Strategy

1. **Parallel Development**: Develop the new system alongside the existing one
2. **Incremental Testing**: Test each component as it's developed
3. **Feature Parity**: Ensure the new system has all the features of the existing one
4. **Gradual Adoption**: Update consumers one at a time to use the new API
5. **Final Cutover**: Once everything is working, remove the old implementation

## Comprehensive Testing Strategy

### Unit Testing Approach

#### 1. Test Coverage Goals
- Aim for >90% code coverage for all new code
- Focus on testing business logic rather than just line coverage
- Each class and function should have dedicated tests

#### 2. Unit Test Organization

| Component | Test File | Test Focus |
|-----------|-----------|------------|
| `domain/models.py` | `tests/unit/core_v2/domain/test_models.py` | Domain model validation, normalization, and behavior |
| `classification/base.py` | `tests/unit/core_v2/classification/test_base.py` | Interface contracts and base functionality |
| `classification/domain_classifier.py` | `tests/unit/core_v2/classification/test_domain_classifier.py` | Domain classification logic |
| `classification/classifiers/youtube.py` | `tests/unit/core_v2/classification/classifiers/test_youtube.py` | YouTube-specific classification logic |
| `blocking/base.py` | `tests/unit/core_v2/blocking/test_base.py` | Blocking strategy interfaces |
| `blocking/domain_excluder.py` | `tests/unit/core_v2/blocking/test_domain_excluder.py` | Domain exclusion logic |
| `blocking/category_blocker.py` | `tests/unit/core_v2/blocking/test_category_blocker.py` | Category-based blocking rules |
| `blocking/pipeline.py` | `tests/unit/core_v2/blocking/test_pipeline.py` | Pipeline execution and priority handling |
| `config/loader.py` | `tests/unit/core_v2/config/test_loader.py` | Configuration loading and validation |
| `cache/memory_cache.py` | `tests/unit/core_v2/cache/test_memory_cache.py` | Cache operations and TTL handling |
| `utils/domain_utils.py` | `tests/unit/core_v2/utils/test_domain_utils.py` | Domain utility functions |
| `api.py` | `tests/unit/core_v2/test_api.py` | API functionality and integration |

#### 3. Test Fixtures and Mocks

1. **Domain Test Fixtures**:
   - Create fixtures for various domain types (valid, invalid, subdomains)
   - Define fixtures for different categories

2. **Configuration Fixtures**:
   - Mock configuration files with various settings
   - Test different configuration scenarios

3. **Classification Mocks**:
   - Mock classifiers for testing the registry and pipeline
   - Create fake classification results for testing decisions

4. **External Dependencies**:
   - Mock StevenBlack hosts file for domain excluder tests
   - Mock YouTube metadata for YouTube classifier tests
   - Mock LLM and OpenAI responses

#### 4. Test-Driven Development

1. **Interface Tests First**:
   - Write tests for interfaces before implementing concrete classes
   - Ensure all implementations satisfy interface contracts

2. **Edge Case Coverage**:
   - Test boundary conditions (empty domains, malformed URLs)
   - Test error handling and recovery
   - Test cache expiration and invalidation

3. **Performance Tests**:
   - Test caching behavior
   - Benchmark classification and blocking operations
   - Ensure memory usage is within acceptable limits

### Integration Testing Approach

#### 1. Integration Test Scope

| Test Scope | Test File | Description |
|------------|-----------|-------------|
| Classification Pipeline | `tests/integration/core_v2/test_classification_pipeline.py` | End-to-end classification process |
| Blocking Pipeline | `tests/integration/core_v2/test_blocking_pipeline.py` | Complete blocking decision flow |
| YouTube Classification | `tests/integration/core_v2/test_youtube_classification.py` | YouTube-specific classification with real metadata |
| Configuration Integration | `tests/integration/core_v2/test_config_integration.py` | Configuration changes affecting system behavior |
| API Integration | `tests/integration/core_v2/test_api_integration.py` | Complete API functionality with real components |

#### 2. Integration Test Strategies

1. **Component Integration Tests**:
   - Test interactions between closely related components
   - Verify correct data flow between components
   - Test error propagation between components

2. **Subsystem Integration Tests**:
   - Test complete classification subsystem
   - Test complete blocking subsystem
   - Test configuration subsystem with real files

3. **System Integration Tests**:
   - Test the entire system end-to-end
   - Verify system behavior matches existing functionality
   - Test with real-world examples and edge cases

#### 3. Test Data and Environments

1. **Test Data Sets**:
   - Create comprehensive domain test sets
   - Include real-world examples from production
   - Create YouTube video metadata samples

2. **Environment Configuration**:
   - Test with different configuration settings
   - Test with and without caching
   - Test with different blocking rules

3. **Performance and Load Testing**:
   - Test with large domain lists
   - Test with high-frequency classification requests
   - Measure and compare performance with existing system

### Compatibility Testing

#### 1. Existing Test Compatibility

1. **Adapter Tests**:
   - Create tests for adapters between old and new systems
   - Ensure adapters correctly translate between systems

2. **Behavior Equivalence Tests**:
   - Compare classification results between old and new systems
   - Compare blocking decisions between old and new systems
   - Ensure no regression in functionality

#### 2. API Compatibility Tests

1. **Interface Compatibility**:
   - Test that new API can be used as a drop-in replacement
   - Verify all existing API methods work correctly

2. **Error Handling Compatibility**:
   - Ensure error responses match existing behavior
   - Test error recovery and fallback mechanisms

### Continuous Integration and Testing Workflow

1. **Test Automation**:
   - Automate all tests to run on code changes
   - Set up CI/CD pipeline for continuous testing

2. **Test Reports**:
   - Generate coverage reports
   - Track test results over time
   - Monitor performance metrics

3. **Testing Workflow**:
   - Run unit tests during development
   - Run integration tests before merging
   - Run compatibility tests before releasing

### Test Implementation Plan

| Phase | Test Focus | Priority | Dependencies |
|-------|------------|----------|-------------|
| 1 | Domain models and utilities | High | None |
| 1 | Base interfaces | High | Domain models |
| 2 | Configuration loading | High | None |
| 2 | Domain classifier | Medium | Domain models, base interfaces |
| 3 | YouTube classifier | Medium | Domain models, base interfaces |
| 3 | Blocking strategies | Medium | Domain models, base interfaces |
| 4 | Pipeline integration | Medium | All components |
| 5 | API functionality | High | All components |
| 6 | System integration | High | Complete system |
| 6 | Compatibility | High | Complete system |

## Mapping Between `core` and `core_v2` Modules

This section details how each component in the current `core` module will correspond to components in the new `core_v2` module:

### Domain Classifier Components

| Current (`core`) | New (`core_v2`) | Notes |
|------------------|----------------|-------|
| `domain_classifier.py` | `classification/domain_classifier.py` | Core classification logic will be preserved but wrapped in a class implementing the `DomainClassifier` interface |
| `domain_config.py` | `domain/constants.py` and `config/loader.py` | Domain categories will be defined as constants, but loading will be handled by the config loader |
| `domain_excluder.py` | `blocking/domain_excluder.py` | Exclusion logic will be preserved but implemented as a `BlockingStrategy` |
| `domain_utils.py` | `utils/domain_utils.py` | Utility functions will be ported with minimal changes |
| `domain_whitelist.py` | `blocking/whitelist_strategy.py` | Whitelist logic will be implemented as a high-priority blocking strategy |

### Classifier Blocker API Components

| Current (`core`) | New (`core_v2`) | Notes |
|------------------|----------------|-------|
| `classifier_blocker_api.py` | `api.py` | Main API will be refactored to use the new components but maintain similar functionality |
| `TabInfo` class | `domain/models.py` | Tab information will be represented as a domain model |
| Caching in API | `cache/memory_cache.py` | Caching will be extracted to a dedicated component |
| Decision flow | `blocking/pipeline.py` | The decision flow will be implemented as a pipeline of strategies |

### YouTube Classifier Components

| Current (`core`) | New (`core_v2`) | Notes |
|------------------|----------------|-------|
| `youtube_classifier.py` | `classification/classifiers/youtube.py` | YouTube classification logic will be preserved but wrapped in a class implementing the `Classifier` interface |
| Rule-based classification | `classification/classifiers/youtube.py` | The existing rule-based logic will be preserved |
| LLM-based classification | `classification/classifiers/youtube_llm.py` | LLM-based classification will be implemented as a separate classifier |
| OpenAI-based classification | `classification/classifiers/youtube_openai.py` | OpenAI-based classification will be implemented as a separate classifier |

## User Configuration Integration

This section details how user configuration will feed into the domain classification and blocking system:

### Configuration Sources

1. **User Config File**: The primary source of user-defined settings
   - Location: `~/.config/focus_guard/config.json` (or equivalent based on platform)
   - Format: JSON with well-defined schema
   - Updates: Monitored for changes with hot reloading

2. **Default Configuration**: Built-in defaults used when user config is not available
   - Location: `core_v2/config/defaults.py`
   - Format: Python dictionary with the same schema as the user config
   - Purpose: Provide sensible defaults and document the configuration schema

### Configuration Schema

```json
{
  "domains": {
    "categories": {
      "work": ["example.com", "work-domain.com"],
      "social": ["facebook.com", "twitter.com"],
      "entertainment": ["youtube.com", "netflix.com"],
      "education": ["coursera.org", "edx.org"],
      "shopping": ["amazon.com", "ebay.com"],
      "news": ["cnn.com", "bbc.com"],
      "email": ["gmail.com", "outlook.com"],
      "development": ["github.com", "stackoverflow.com"],
      "productivity": ["notion.so", "trello.com"]
    },
    "whitelist": ["example.org", "allowed-domain.com"],
    "custom_domains": {}
  },
  "blocking": {
    "block_categories": ["social", "entertainment"],
    "exclusion_enabled": true,
    "exclusion_categories": ["social", "gambling", "porn", "fakenews"],
    "approved_only_mode": false
  },
  "youtube": {
    "classification_method": "rule_based",  // "rule_based", "llm", "openai"
    "educational_channels": ["Khan Academy", "MIT OpenCourseWare"],
    "educational_keywords": ["tutorial", "course", "learn", "education"],
    "entertainment_keywords": ["funny", "prank", "game", "play"]
  },
  "caching": {
    "enabled": true,
    "ttl_seconds": 3600
  }
}
```

### Configuration Flow

1. **Loading Process**:
   - `ConfigLoader` loads the user config file
   - If not found or invalid, falls back to default configuration
   - Validates the configuration against the schema
   - Provides access to configuration sections via methods

2. **Domain Categories**:
   - User-defined domain categories override default categories
   - Custom domains are merged with predefined domains
   - Changes to domain categories take effect immediately when config is reloaded

3. **Whitelist Integration**:
   - User-defined whitelist is loaded by the `ConfigLoader`
   - `WhitelistStrategy` uses this list to determine if domains should be allowed
   - Whitelist has high priority in the blocking pipeline

4. **Domain Excluder Integration**:
   - User can enable/disable domain exclusion
   - User can select which exclusion categories to use
   - `DomainExcluderStrategy` uses these settings to determine exclusion behavior

5. **YouTube Classification**:
   - User can select the classification method
   - User can define educational channels and keywords
   - `YouTubeClassifier` uses these settings for classification

6. **Blocking Rules**:
   - User can specify which categories to block
   - `CategoryBlockingStrategy` uses these settings to determine blocking behavior
   - User can enable "approved only mode" where only explicitly allowed domains are accessible

### Configuration Updates

1. **Hot Reloading**:
   - `ConfigLoader` monitors the config file for changes
   - When changes are detected, configuration is reloaded
   - Components are notified of configuration changes

2. **Cache Invalidation**:
   - When configuration changes, relevant caches are invalidated
   - This ensures that classification and blocking decisions reflect the new configuration

3. **User Interface**:
   - The application provides a UI for users to modify the configuration
   - Changes are saved to the config file, triggering the reload process

## Browser Integration Strategy

This section details how the refactored domain classification and blocking system will integrate with browser tab management and blocking functionality:

### Browser Extension Integration

1. **Tab Closing Mechanism**:
   - The `core_v2` module will use the browser extension approach for tab closing instead of Chrome DevTools Protocol (CDP)
   - This avoids security warnings caused by enabling remote debugging mode
   - Integration will be through the existing browser extension infrastructure in `core/browser_detection/browser_integration` and `webextension_mv3` directories

2. **Message Protocol**:
   - Tab close messages will use a standardized format with action "close_tab"
   - Message data will include tabId, windowId, url, domain, and reason for blocking
   - This protocol will be documented in the API interfaces

3. **Integration Components**:
   - `core_v2/browser/tab_controller.py`: Interface for tab control operations
   - `core_v2/browser/extension_integration.py`: Implementation using browser extension
   - `core_v2/browser/cdp_integration.py`: Alternative implementation using CDP (for development/testing)

### Blocking Decision Flow

1. **Tab Blocking Process**:
   - Domain is extracted from tab URL
   - Domain is classified using the classification pipeline
   - Blocking decision is made using the blocking pipeline
   - If blocked, tab is closed with appropriate reason

2. **User Notification**:
   - When a tab is blocked, user is notified with the reason
   - Notification includes category or other relevant information
   - User has option to override blocking for specific domains

3. **Blocking Metrics**:
   - System tracks blocked domains and reasons
   - Metrics are used for reporting and improving classification

## Performance Optimization Strategy

This section outlines strategies for ensuring the refactored system maintains or improves performance:

### Caching Strategy

1. **Multi-Level Caching**:
   - Domain normalization results cached
   - Classification results cached with configurable TTL
   - Blocking decisions cached with shorter TTL
   - Cache invalidation on configuration changes

2. **Cache Implementation**:
   - In-memory LRU cache for frequently accessed domains
   - Persistent cache for stable classification results
   - Cache size limits to prevent memory issues

3. **Performance Metrics**:
   - Track cache hit/miss rates
   - Measure classification and blocking decision times
   - Compare performance with previous implementation

### Computational Optimization

1. **Lazy Loading**:
   - Load expensive components only when needed
   - Defer initialization of specialized classifiers

2. **Batch Processing**:
   - Process multiple domains in batch where possible
   - Share computation across similar domains

3. **Asynchronous Processing**:
   - Use async processing for non-blocking operations
   - Implement background updating of classification data

## Error Handling and Resilience

This section details how the system will handle errors and maintain resilience:

### Error Handling Strategy

1. **Graceful Degradation**:
   - If a classifier fails, fall back to simpler classifiers
   - If blocking strategy fails, use conservative default
   - Log errors but continue operation when possible

2. **Error Types and Responses**:
   - Configuration errors: Fall back to defaults
   - Classification errors: Return unknown category
   - Blocking errors: Default to not blocking (safer)
   - Integration errors: Retry with exponential backoff

3. **Monitoring and Alerting**:
   - Log all errors with appropriate context
   - Alert on persistent or critical errors
   - Track error rates and patterns

### Resilience Mechanisms

1. **Circuit Breakers**:
   - Implement circuit breakers for external dependencies
   - Automatically disable failing components temporarily
   - Restore when dependencies recover

2. **Retry Mechanisms**:
   - Implement retry with backoff for transient failures
   - Limit retries to prevent cascading failures

3. **Fallback Strategies**:
   - Define fallback behavior for each component
   - Ensure system can operate with minimal functionality

## Conclusion

This refactoring plan provides a roadmap for creating a more modular, maintainable, and extensible domain classification and blocking system while preserving the existing business logic. By following this plan, we can improve the architecture without losing the valuable work already done.

The detailed mapping between `core` and `core_v2` ensures that we preserve the valuable functionality while improving the structure. The user configuration integration plan ensures that the system remains flexible and user-configurable, with a clean separation between configuration and implementation.

The additional sections on browser integration, performance optimization, and error handling provide a comprehensive strategy for addressing all aspects of the refactoring process, ensuring that the new system is not only well-structured but also performant, resilient, and fully integrated with the browser extension infrastructure.
