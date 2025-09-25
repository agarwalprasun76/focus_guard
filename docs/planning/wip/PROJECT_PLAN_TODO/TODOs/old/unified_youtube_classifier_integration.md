# Unified YouTube Classifier Integration

## Overview

This document describes the integration of the unified YouTube classifier with the tab blocking system. The integration eliminates duplication between the context-aware classifier and YouTube classifier, leveraging the existing robust YouTube classifier infrastructure.

## Architecture Changes

### Before Refactoring

Previously, the system had two separate classification paths:

1. **Domain Classifier Path**:
   - Basic domain-based classification
   - Category-based blocking (social, entertainment, etc.)

2. **Context-Aware Classifier Path**:
   - YouTube-specific content analysis
   - LLM-based classification for YouTube videos
   - Pattern matching fallback for YouTube content

This created duplication and potential inconsistencies between the two classification systems.

### After Refactoring

The refactored architecture:

1. **Unified Classification Chain**:
   - Single entry point through `classifier_blocker_api.py`
   - Hierarchical classification for YouTube URLs:
     - First attempts YouTube-specific classification
     - Falls back to domain-based classification if needed
   - Direct domain classification for non-YouTube URLs

2. **Direct Integration**:
   - YouTube classifier is directly integrated with the classifier-blocker API
   - No compatibility layer needed
   - Clean, straightforward architecture

## API Usage

### Classifier-Blocker API

The primary interface for classification and blocking decisions is the `ClassifierBlockerAPI` class:

```python
from core.integrations.classifier_blocker_api import ClassifierBlockerAPI, TabInfo

# Initialize the API
api = ClassifierBlockerAPI()

# Create tab info
tab_info = TabInfo(
    tab_id=123,
    window_id=1,
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    domain="youtube.com",
    title="Rick Astley - Never Gonna Give You Up",
    metadata={
        "title": "Rick Astley - Never Gonna Give You Up",
        "description": "Official music video for Rick Astley - Never Gonna Give You Up",
        "channel_name": "Rick Astley",
        "tags": ["Rick Astley", "music", "pop"]
    }
)

# Get blocking decision
should_block, reason = api.should_block_tab(tab_info)
print(f"Block: {should_block}, Reason: {reason}")
```

### YouTube Classification

For direct YouTube classification:

```python
from core.domain_classifier.classifiers.youtube_classifier import youtube_classifier

# Classify a YouTube URL
result = youtube_classifier.classify(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    domain="youtube.com",
    page_content="",  # Optional HTML content
    metadata={
        "title": "Rick Astley - Never Gonna Give You Up",
        "description": "Official music video for Rick Astley - Never Gonna Give You Up",
        "channel_name": "Rick Astley",
        "tags": ["Rick Astley", "music", "pop"]
    }
)

# Check classification result
if result and 'classification' in result:
    classification = result['classification']  # 'useful', 'distraction', or 'neutral'
    confidence = result.get('confidence', 0.0)
    print(f"Classification: {classification}, Confidence: {confidence}")
```

### Direct YouTube Classification

For direct YouTube classification, use the YouTube classifier:

```python
from core.domain_classifier.classifiers.youtube_classifier import youtube_classifier

# Classify a YouTube URL
result = youtube_classifier.classify(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    domain="youtube.com",
    page_content="",  # Optional HTML content
    metadata={
        "title": "Rick Astley - Never Gonna Give You Up",
        "description": "Official music video for Rick Astley - Never Gonna Give You Up"
    }
)

# Check classification result
if result and 'classification' in result:
    classification = result['classification']  # 'useful', 'distraction', or 'neutral'
    print(f"Classification: {classification}")
```

## Integration Points

The unified classifier is integrated at the following points:

1. **Browser Extension**:
   - Preemptive blocking via `/api/should_block` endpoint
   - Sends tab metadata for context-aware classification

2. **Tab Server**:
   - Processes tab updates and new tabs
   - Calls `ClassifierBlockerAPI.should_block_tab()`

3. **Browser Tab Blocker**:
   - Uses classification results to make blocking decisions
   - Handles both preemptive and reactive blocking

## Testing

The integration is tested at multiple levels:

1. **Unit Tests**:
   - `test_context_aware_classifier.py` - Tests the YouTube classifier integration with the classifier-blocker API
   - `test_youtube_classifier.py` - Tests the YouTube classifier directly

2. **Integration Tests**:
   - `test_classifier_blocker_integration.py` - Tests the end-to-end flow

## Future Work

1. **Enhance Context Awareness**:
   - Add more metadata sources for classification
   - Improve classification accuracy with additional context

2. **Performance Optimization**:
   - Cache classification results for frequently visited URLs
   - Optimize classification chain for faster decisions

3. **Additional Classification Features**:
   - Support for more content platforms beyond YouTube
   - Integration with more specialized classifiers for different content types
