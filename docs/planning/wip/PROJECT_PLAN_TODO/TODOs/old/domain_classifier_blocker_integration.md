# Domain Classifier & Blocker Integration Plan

## Overview

This document outlines the integration plan between the domain classifier and blocker modules to create a more intelligent and context-aware tab blocking system. The integration will enable:

1. **Preemptive blocking** - Prevent blacklisted tabs from opening
2. **Context-aware blocking** - Make blocking decisions based on content context (e.g., YouTube video relevance)
3. **Modular communication** - Clear API between classifier and blocker

## Current Architecture

### Domain Classifier
- Classifies domains into categories (work, social, education, etc.)
- Provides link classification (useful, distraction, neutral)
- Supports metadata-based content analysis
- Includes whitelist and exclusion mechanisms

### Blocker
- Closes browser tabs based on domain categories
- Uses either browser extension or CDP for tab management
- Supports whitelist/blacklist and category-based blocking

### Browser Integration
- Tracks browser tabs and their status
- Communicates with browser extensions
- Provides tab data to the core system

## Integration Design

### 1. Communication API

We'll create a new module `core/integrations/classifier_blocker_api.py` to serve as the communication layer between the domain classifier and blocker:

```python
class ClassifierBlockerAPI:
    """API for communication between domain classifier and tab blocker."""
    
    def __init__(self, use_context_aware=True, use_preemptive=True):
        """Initialize the API with desired features."""
        self.use_context_aware = use_context_aware
        self.use_preemptive = use_preemptive
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize required components."""
        # Import components here to avoid circular imports
        from core.domain_classifier.link_classifier import link_classifier
        from core.domain_classifier.domain_classifier import classify_domain
        from core.domain_classifier.domain_whitelist import domain_whitelist
        
        self.link_classifier = link_classifier
        self.classify_domain = classify_domain
        self.domain_whitelist = domain_whitelist
    
    def should_block_tab(self, tab_info):
        """
        Determine if a tab should be blocked based on domain classification and context.
        
        Args:
            tab_info: Dictionary containing tab information
                {
                    "url": str,
                    "domain": str,
                    "title": str,
                    "tab_id": int,
                    "window_id": int,
                    "context": dict (optional, for context-aware decisions)
                }
                
        Returns:
            dict: {
                "should_block": bool,
                "reason": str,
                "confidence": float,
                "category": str,
                "classification": str
            }
        """
        # Implementation details to be filled
        pass
    
    def evaluate_tab_context(self, tab_info):
        """
        Evaluate tab context for context-aware decisions.
        
        Args:
            tab_info: Dictionary containing tab information
                
        Returns:
            dict: Context evaluation results
        """
        # Implementation details to be filled
        pass
    
    def should_preemptively_block(self, url, domain=None):
        """
        Determine if a URL should be blocked preemptively.
        
        Args:
            url: URL to check
            domain: Optional pre-extracted domain
                
        Returns:
            dict: {
                "should_block": bool,
                "reason": str
            }
        """
        # Implementation details to be filled
        pass
```

### 2. Tab Information Structure

We'll define a standard tab information structure for communication:

```python
TabInfo = {
    # Basic information
    "tab_id": int,          # Browser tab ID
    "window_id": int,       # Browser window ID
    "url": str,             # Full URL
    "domain": str,          # Extracted domain
    "title": str,           # Tab title
    
    # Context information
    "context": {
        "previous_url": str,        # Previous URL in this tab
        "session_context": str,     # Current user session context (work, study, etc.)
        "content_type": str,        # Type of content (video, article, etc.)
        "metadata": dict,           # Content metadata (video title, description, etc.)
        "related_tabs": list,       # Related tabs in the same window
        "time_on_page": float,      # Time spent on this page
        "interaction_level": float, # User interaction level with this tab
    },
    
    # Classification results (filled by classifier)
    "classification": {
        "domain_category": str,     # Domain category (social, work, etc.)
        "content_classification": str, # Content classification (useful, distraction, neutral)
        "confidence": float,        # Confidence in classification
        "reason": str,              # Reason for classification
    }
}
```

### 3. Extension Updates for Preemptive Blocking

We'll update the browser extension to support preemptive blocking:

1. **Manifest Updates**:
   - Add `webRequest` and `webRequestBlocking` permissions
   - Add background script for request interception

2. **Background Script**:
   - Add request interception logic
   - Query the FocusGuard application for blocking decisions
   - Block requests for blacklisted domains/URLs

```javascript
// In background.js
chrome.webRequest.onBeforeRequest.addListener(
  function(details) {
    // Extract URL and domain
    const url = details.url;
    const domain = extractDomain(url);
    
    // Query FocusGuard for blocking decision
    const blockDecision = queryBlockingDecision(url, domain);
    
    // Return blocking decision
    return { cancel: blockDecision.should_block };
  },
  { urls: ["<all_urls>"] },
  ["blocking"]
);

function queryBlockingDecision(url, domain) {
  // Query the FocusGuard application via the tab server
  // This could be a synchronous request or use cached decisions
  // For performance reasons, we might want to cache common decisions
  
  // For now, implement a simple synchronous request
  const response = fetch(`http://localhost:5000/api/should_block?url=${encodeURIComponent(url)}&domain=${encodeURIComponent(domain)}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  });
  
  if (response.ok) {
    return response.json();
  }
  
  // Default to not blocking if request fails
  return { should_block: false };
}
```

### 4. Tab Server Updates

We'll update the tab server to handle preemptive blocking requests:

```python
# In tab_server_v2.py

@app.route('/api/should_block', methods=['GET'])
def should_block():
    """Handle preemptive blocking requests from the extension."""
    url = request.args.get('url', '')
    domain = request.args.get('domain', '')
    
    # Use the classifier-blocker API to make a decision
    from core.integrations.classifier_blocker_api import classifier_blocker_api
    
    decision = classifier_blocker_api.should_preemptively_block(url, domain)
    
    return jsonify(decision)
```

### 5. Context-Aware Classification

We'll enhance the domain classifier to support context-aware decisions:

```python
# In link_classifier.py

def classify_with_context(self, url, domain, context=None):
    """
    Classify a link with additional context information.
    
    Args:
        url: URL to classify
        domain: Domain of the URL
        context: Additional context information
            {
                "previous_url": str,
                "session_context": str,
                "content_type": str,
                "metadata": dict,
                "related_tabs": list,
                "time_on_page": float,
                "interaction_level": float,
            }
            
    Returns:
        dict: Classification results
    """
    # Basic classification first
    result = self.classify_link(url, domain)
    
    # If we have context, enhance the classification
    if context:
        # Use context to refine the classification
        if context.get("content_type") == "video" and "youtube.com" in domain:
            # For YouTube videos, check if the content is relevant to the session
            session_context = context.get("session_context", "")
            metadata = context.get("metadata", {})
            
            # Use the YouTube classifier with context
            youtube_result = self._classify_youtube_with_context(url, metadata, session_context)
            
            # Update the classification based on context
            if youtube_result:
                result.update(youtube_result)
    
    return result

def _classify_youtube_with_context(self, url, metadata, session_context):
    """
    Classify a YouTube video with session context.
    
    Args:
        url: YouTube URL
        metadata: Video metadata
        session_context: Current session context
            
    Returns:
        dict: Classification results
    """
    # Extract video ID
    video_id = self._extract_youtube_id(url)
    if not video_id:
        return None
    
    # Get video metadata if not provided
    if not metadata:
        metadata = self.metadata_fetcher.fetch_youtube_metadata(video_id)
    
    # Check if video is relevant to session context
    relevance_score = self._calculate_relevance(metadata, session_context)
    
    # Determine classification based on relevance
    if relevance_score > 0.7:  # High relevance
        return {
            "classification": "useful",
            "confidence": relevance_score,
            "reason": f"Relevant to {session_context} session"
        }
    elif relevance_score > 0.3:  # Medium relevance
        return {
            "classification": "neutral",
            "confidence": relevance_score,
            "reason": f"Somewhat relevant to {session_context} session"
        }
    else:  # Low relevance
        return {
            "classification": "distraction",
            "confidence": 1.0 - relevance_score,
            "reason": f"Not relevant to {session_context} session"
        }

def _calculate_relevance(self, metadata, session_context):
    """
    Calculate relevance of content to session context.
    
    Args:
        metadata: Content metadata
        session_context: Current session context
            
    Returns:
        float: Relevance score (0-1)
    """
    # Simple keyword-based relevance for now
    # This could be enhanced with ML/NLP techniques
    
    # Extract keywords from session context
    context_keywords = set(session_context.lower().split())
    
    # Extract keywords from metadata
    title = metadata.get("title", "").lower()
    description = metadata.get("description", "").lower()
    
    # Count keyword matches
    title_words = set(title.split())
    desc_words = set(description.split())
    content_words = title_words.union(desc_words)
    
    # Calculate overlap
    if not context_keywords or not content_words:
        return 0.0
    
    matches = len(context_keywords.intersection(content_words))
    total = len(context_keywords)
    
    return min(1.0, matches / total)
```

### 6. Blocker Updates

We'll update the browser tab blocker to use the new API:

```python
# In browser_tab_blocker.py

from core.integrations.classifier_blocker_api import classifier_blocker_api

class BrowserTabBlocker:
    # ... existing code ...
    
    def should_block_tab(self, tab_info: Dict) -> bool:
        """
        Determine if a browser tab should be blocked based on its URL or domain.
        
        Args:
            tab_info: Dictionary containing tab information
            
        Returns:
            bool: True if the tab should be blocked, False otherwise
        """
        # Use the classifier-blocker API for the decision
        decision = classifier_blocker_api.should_block_tab(tab_info)
        
        if decision["should_block"]:
            logger.info(f"Tab should be blocked: {tab_info.get('url', '')} (Reason: {decision['reason']})")
            return True
        
        return False
    
    # ... existing code ...
```

## Implementation Plan

### Phase 1: Core API and Data Structures

1. Create `classifier_blocker_api.py` with basic functionality
2. Define the tab information structure
3. Update domain classifier to support context-aware classification
4. Update blocker to use the new API
5. Add unit tests for the new API

### Phase 2: Preemptive Blocking

1. Update the browser extension manifest
2. Add request interception logic to the extension
3. Update tab server to handle preemptive blocking requests
4. Test preemptive blocking functionality

### Phase 3: Context-Aware Classification

1. Enhance domain classifier with context-aware classification
2. Implement YouTube-specific context evaluation
3. Add session context tracking
4. Test context-aware blocking functionality

### Phase 4: Integration and Testing

1. Integrate all components
2. Add end-to-end tests
3. Document API usage and configuration options
4. Create demo scripts for testing

## Conclusion

This integration plan provides a robust framework for communication between the domain classifier and blocker modules. By implementing this plan, we'll achieve:

1. Preemptive blocking of blacklisted tabs
2. Context-aware blocking decisions
3. Modular and maintainable code structure

The implementation will be done in phases to ensure proper testing and validation at each step.
