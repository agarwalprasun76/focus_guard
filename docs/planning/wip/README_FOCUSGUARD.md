# Focus Guard Core Architecture

This document provides a comprehensive overview of the Focus Guard core architecture, detailing all modules, their relationships, and how they work together to create a unified productivity and focus management system.

## 🎯 Project Overview

Focus Guard is a sophisticated productivity application that combines domain classification, intelligent blocking, browser integration, and user activity monitoring to help users maintain focus and reduce digital distractions.

## 🏗️ Architecture Overview

The system follows a modular, event-driven architecture with the following key characteristics:
- **Component-Based**: Each module is a self-contained component with clear interfaces
- **Event-Driven**: Communication between components happens via an event bus
- **Lifecycle Managed**: Components have defined initialization, startup, and shutdown sequences
- **Configuration-Driven**: Behavior is controlled through a unified configuration system
- **Extensible**: New components and strategies can be added without modifying existing code

## 📊 Module Architecture Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    FocusGuardCoordinator                        │
│                  (Central Orchestrator)                        │
└─────────────────┬───────────────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼───┐   ┌───▼───┐   ┌───▼───┐
│ API   │   │ Browser│   │ Activity│
│ Server│   │ Monitor│   │ Monitor │
└───┬───┘   └───┬───┘   └───┬───┘
    │             │             │
┌───▼───┐   ┌───▼───┐   ┌───▼───┐
│ Classifier│   │ Distraction│   │ Alert   │
│ Component│   │ Detector  │   │ System  │
└─────────┘   └─────────┘   └─────────┘
```

## 🔧 Core Modules Deep Dive

### 1. API Module (`api/`) - The Programmatic Interface
**Purpose**: Provides the main programmatic interface for domain classification and blocking functionality.

**Key Components**:
- **ClassifierBlockerAPI**: The central API class integrating all functionality
- **Server Components**: HTTP server for remote API access
- **Singleton Instance**: Global `api` instance for easy access

**Core Capabilities**:
- Domain classification with caching
- Context-aware classification with metadata
- Blocking decision making
- Configuration reloading without restart
- Comprehensive error handling and logging

**Usage Example**:
```python
from focus_guard.core.api.api import api

# Classify a domain
category = api.classify_domain("facebook.com")

# Check if URL should be blocked
should_block = api.should_block_tab("https://facebook.com")

# Get blocking reason
reason = api.get_blocking_reason("https://youtube.com")
```

### 2. Activity Module (`activity/`) - User Activity Monitoring
**Purpose**: Monitors and tracks user activity patterns to detect productivity states and potential distractions.

**Key Features**:
- Idle state detection
- Activity pattern analysis
- Productivity state classification
- Integration with distraction detection

**Integration Points**:
- Provides context to classification decisions
- Triggers distraction detection events
- Feeds browser blocking decisions

### 3. Alert Module (`alert/`) - User Notification System
**Purpose**: Manages user notifications and alerts for blocking events, configuration changes, and system status.

**Key Components**:
- Alert creation and management
- User notification delivery
- Alert dismissal handling
- Configuration change notifications

**Event Types**:
- Distraction detection alerts
- Configuration change notifications
- System health status updates

### 4. Browser Module (`browser/`) - Browser Integration
**Purpose**: Provides comprehensive browser integration for tab monitoring, URL extraction, and real-time blocking.

**Key Features**:
- Real-time tab monitoring
- URL extraction and domain classification
- Tab blocking and closing capabilities
- Browser extension communication
- Cross-browser compatibility

**Integration Pattern**:
- Monitors all browser tabs continuously
- Classifies domains in real-time
- Applies blocking decisions immediately
- Provides user feedback and controls

### 5. Blocking Module (`blocking/`) - Intelligent Blocking Engine
**Purpose**: Implements the blocking decision engine with configurable strategies and priorities.

**Architecture**:
- **BlockingStrategy Interface**: Abstract base for all blocking strategies
- **Strategy Registry**: Manages multiple blocking strategies
- **Blocking Pipeline**: Orchestrates strategy execution
- **Built-in Strategies**: Ready-to-use blocking approaches

**Built-in Strategies**:
- **Domain Excluder**: Uses external blocklists (priority: 100)
- **Category Blocker**: Blocks based on domain categories (priority: 90)
- **Context-Aware Strategies**: Uses additional metadata for decisions

**Blocking Reasons**:
- `CATEGORY`: Blocked due to category classification
- `DOMAIN_EXCLUDED`: Blocked by external blocklist
- `USER_BLOCKED`: Explicitly blocked by user
- `CONTENT_POLICY`: Blocked due to content policy
- `YOUTUBE_CONTENT`: Blocked due to YouTube content classification

### 6. Cache Module (`cache/`) - Performance Optimization
**Purpose**: Provides in-memory caching for expensive operations with TTL support and performance monitoring.

**Key Features**:
- **MemoryCache**: Generic, type-safe caching implementation
- **TTL Support**: Automatic expiration with configurable time-to-live
- **Performance Monitoring**: Hit/miss tracking and statistics
- **Thread Safety**: Safe concurrent access
- **Cleanup Management**: Automatic and manual cleanup

**Usage Patterns**:
- Domain classification result caching
- API response caching
- Configuration lookup caching
- User preference caching

### 7. Classification Module (`classification/`) - Domain Intelligence
**Purpose**: Provides intelligent domain classification using multiple strategies and context-aware processing.

**Classification Strategies**:
- **Rule-based Classifiers**: Pattern matching and keyword analysis
- **ML-LLM-based Classifiers**: Machine learning models for complex categorization
- **Context-aware Classifiers**: Uses additional metadata for better accuracy
- **Hybrid Approaches**: Combines multiple strategies for optimal results

**Categories**:
- **SOCIAL_MEDIA**: Facebook, Twitter, Instagram, etc.
- **ENTERTAINMENT**: YouTube, Netflix, gaming sites
- **PRODUCTIVITY**: Work-related tools and applications
- **NEWS**: News websites and aggregators
- **SHOPPING**: E-commerce and retail sites
- **WORK**: Professional and business applications

### 8. Configuration Module (`config/`) - Unified Settings Management
**Purpose**: Provides comprehensive configuration management with multiple providers, validation, and migration support.

**Configuration Architecture**:
- **ConfigProvider Interface**: Abstract base for configuration sources
- **Multiple Providers**: JSON, memory, and legacy adapters
- **Schema Validation**: JSON schema-based configuration validation
- **Migration Framework**: Version-to-version configuration migration
- **Real-time Updates**: Dynamic configuration reloading

**Provider Types**:
- **JsonConfigProvider**: File-based configuration storage
- **MemoryConfigProvider**: Volatile in-memory settings
- **LegacyJsonConfigAdapter**: Backward compatibility support

### 9. Coordinator Module (`coordinator/`) - System Orchestration
**Purpose**: The central orchestrator that manages all components, their lifecycles, and inter-component communication.

**Key Responsibilities**:
- **Component Lifecycle**: Initialize, start, stop, and shutdown all components
- **Event Management**: Handle inter-component communication via event bus
- **Health Monitoring**: Continuous health checks and status reporting
- **Dependency Management**: Resolve and manage component dependencies
- **Configuration Distribution**: Distribute configuration to all components

**Component Architecture**:
- **Activity Monitor**: Tracks user activity and system state
- **Browser Integration**: Manages browser tab monitoring
- **Distraction Detector**: Identifies and handles distraction events
- **Domain Classifier**: Provides domain categorization
- **Alert System**: Manages user notifications
- **API Server**: Provides external programmatic access

### 10. Distraction Module (`distraction/`) - Distraction Detection Engine
**Purpose**: Identifies and manages distraction events based on user behavior patterns and system state.

**Detection Capabilities**:
- **Behavioral Pattern Analysis**: Identifies distraction patterns
- **Context-aware Detection**: Uses activity and browser context
- **Real-time Processing**: Immediate distraction detection
- **Integration with Blocking**: Triggers blocking decisions

### 11. Domain Module (`domain/`) - Domain Intelligence
**Purpose**: Provides domain analysis, URL processing, and domain-specific utilities.

**Key Functions**:
- **URL Parsing**: Extract domains from complex URLs
- **Domain Normalization**: Standardize domain representations
- **Domain Categorization**: Map domains to categories
- **Domain Validation**: Ensure domain legitimacy

### 12. Utils Module (`utils/`) - Shared Utilities
**Purpose**: Central location for common utility functions and shared functionality.

**Utility Categories**:
- **Logging Helpers**: Standardized logging setup
- **Validation Utilities**: Common input validation
- **Data Processing**: Shared data transformation utilities
- **Error Handling**: Consistent error handling patterns

## 🔄 Data Flow Architecture

### Typical User Session Flow

```
1. User opens browser tab with URL
   ↓
2. Browser module detects tab open event
   ↓
3. Domain module extracts domain from URL
   ↓
4. Classification module categorizes the domain
   ↓
5. Blocking module decides whether to block
   ↓
6. Alert module notifies user of blocking decision
   ↓
7. Activity module tracks user response
   ↓
8. API provides programmatic access to all decisions
```

### Event Flow
```
Browser Event → Coordinator → Classification → Blocking → Alert → API
```

## 🎛️ Configuration Architecture

### Configuration Layers
1. **User Settings**: Personal preferences and rules
2. **System Defaults**: Application-wide defaults
3. **Provider Configs**: Strategy-specific configurations
4. **Runtime Updates**: Dynamic configuration changes

### Configuration Schema
```yaml
classification:
  cache_ttl_seconds: 3600
  strategies:
    - youtube_classifier
    - ml_classifier
  
blocking:
  strategies:
    - domain_excluder
    - category_blocker
  
alerts:
  enabled: true
  notification_types:
    - distraction_detected
    - site_blocked
```

## 🔍 Monitoring and Observability

### Health Monitoring
- **Component Health**: Individual component status
- **System Health**: Overall system status
- **Performance Metrics**: Response times and throughput
- **Error Rates**: Failure tracking and alerting

### Logging Architecture
- **Structured Logging**: JSON-formatted logs
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Context Preservation**: Request ID tracking
- **Performance Logging**: Timing information

## 🚀 Getting Started

### Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Start the coordinator
python -m focus_guard.core.coordinator.focus_guard_coordinator

# Use the API
from focus_guard.core.api.api import api
result = api.classify_domain("facebook.com")
```

### Development Setup
```bash
# Clone repository
git clone [repository-url]
cd focus_guard

# Set up development environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Run tests
pytest tests/
```

## 📚 API Reference

### Core API Methods
- `classify_domain(domain: str) -> Optional[Category]`
- `classify_domain_with_context(domain: str, context: Dict[str, Any]) -> Optional[Category]`
- `should_block_tab(url: str, metadata: Optional[Dict[str, Any]] = None) -> bool`
- `get_blocking_reason(url: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]`
- `reload_configuration() -> None`

### Configuration Management
- Configuration loading and validation
- Real-time configuration updates
- Multi-provider configuration support
- Schema validation and migration

### Event System
- Component lifecycle events
- Distraction detection events
- Browser monitoring events
- Configuration change events

## 🔧 Extension Points

### Adding New Classifiers
1. Implement the `Classifier` interface
2. Register with the classifier registry
3. Configure in settings

### Adding New Blocking Strategies
1. Implement the `BlockingStrategy` interface
2. Register with the blocking strategy registry
3. Configure priority and settings

### Adding New Components
1. Implement the `Component` interface
2. Register with the coordinator
3. Configure dependencies and settings

## 🧪 Testing

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **End-to-End Tests**: Full system workflow testing
- **Performance Tests**: Load and stress testing

### Test Structure
```
tests/
├── unit/
│   ├── test_classification.py
│   ├── test_blocking.py
│   └── test_api.py
├── integration/
│   ├── test_coordinator.py
│   └── test_configuration.py
└── e2e/
    └── test_full_workflow.py
```

## 📈 Performance Characteristics

### Caching Strategy
- **Domain Classification**: 1-hour TTL
- **API Responses**: 5-minute TTL
- **Configuration**: Immediate reload capability
- **User Preferences**: Variable TTL based on volatility

### Memory Usage
- **Cache Memory**: Proportional to unique domains encountered
- **Component Memory**: Fixed overhead per component
- **Configuration Memory**: Depends on configuration complexity

### Response Times
- **Domain Classification**: ~1-5ms (cached), ~50-200ms (uncached)
- **Blocking Decision**: ~1-10ms total pipeline time
- **Configuration Reload**: ~100-500ms depending on complexity

## 🔒 Security Considerations

### Data Privacy
- No user data collection beyond configuration
- Local processing only
- No external API calls for classification
- Secure configuration storage

### Browser Security
- Browser extension permissions limited to necessary scope
- No access to sensitive browser data
- Secure communication channels
- User consent for all monitoring

## 📞 Support and Contributing

### Getting Help
- Check individual module README.md files
- Review configuration documentation
- Examine log files for troubleshooting
- Use API documentation for integration

### Contributing
- Follow established patterns in existing modules
- Add comprehensive tests for new functionality
- Update documentation for changes
- Maintain backward compatibility when possible

---

*This README provides a comprehensive overview of the Focus Guard core architecture. For detailed information about specific modules, refer to the individual README.md files in each module directory.*
