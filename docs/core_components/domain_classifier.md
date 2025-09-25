# Domain Classifier Module

## Overview

The `core/domain_classifier` module provides comprehensive functionality for classifying, filtering, and managing web domains and links. It is designed to help applications distinguish between useful, distracting, and neutral web content, supporting productivity tools, parental controls, and research environments.

This module includes:
- Domain classification and categorization
- Pattern-based link classification (e.g., YouTube, Google Drive, GitHub)
- Metadata-based content analysis
- Whitelisting and exclusion mechanisms
- Utility functions for domain extraction and normalization

## Main Components

### 1. `domain_classifier.py`
- **Purpose:** Classifies domains into categories (e.g., work, social, education).
- **Key Functions:**
  - `classify_domain(domain: str) -> Optional[str]`: Returns the category for a given domain or URL.
  - Uses configuration from `domain_config.py`.

### 2. `link_classifier.py`
- **Purpose:** Classifies full URLs/links as `useful`, `distraction`, or `neutral`.
- **Key Features:**
  - Pattern-based and metadata-based classification.
  - Handles YouTube, Google Drive, GitHub, and generic web links.
  - Uses keyword scoring and OpenGraph/YouTube/Drive metadata.
  - Provides a singleton instance for easy import: `link_classifier`.
- **Key Methods:**
  - `classify_link(url: str, domain: str) -> Dict[str, Any]`
  - `_normalize_url(url: str) -> str`
  - `_classify_with_metadata(metadata: Dict, source: str) -> Dict`

### 3. `metadata.py`
- **Purpose:** Fetches and parses metadata from various sources (YouTube, Google Drive, generic web pages).
- **Key Classes:**
  - `MetadataFetcher`: Main class for metadata retrieval.
  - Singleton instance: `metadata_fetcher`.

### 4. `domain_config.py`
- **Purpose:** Central configuration for domain categories, whitelists, and application names.
- **Structure:**
  - `DomainConfig`: TypedDict for config structure.
  - Includes categories like `work`, `social`, `education`, and more.

### 5. `domain_whitelist.py`
- **Purpose:** Maintains a set of always-allowed (whitelisted) domains.
- **Key Functions:**
  - `domain_whitelist(domain: str) -> bool`
  - `get_whitelisted_domains() -> Set[str]`
  - `add_to_whitelist(domain: str)`
  - `remove_from_whitelist(domain: str)`

### 6. `domain_utils.py`
- **Purpose:** Utility functions for domain handling.
- **Key Functions:**
  - `normalize_domain(domain: str) -> str`
  - `is_valid_domain(domain: str) -> bool`
  - `extract_domain_from_url(url: str) -> str`
  - `is_subdomain(domain: str, parent: str) -> bool`
  - `get_domain_parts(domain: str) -> List[str]`

### 7. `domain_excluder.py` & `filter_domain.py`
- **Purpose:**
  - `domain_excluder.py`: Identifies and blocks excluded domains (e.g., gambling, adult sites).
  - `filter_domain.py`: Combines exclusion, whitelisting, and classification for a full filtering pipeline.

## Usage Examples

### Classify a Domain
```python
from core.domain_classifier import classify_domain
category = classify_domain("github.com")  # e.g., 'work'
```

### Classify a Link
```python
from core.domain_classifier.link_classifier import link_classifier
result = link_classifier.classify_link(
    "https://www.youtube.com/watch?v=abc123", "youtube.com"
)
print(result["classification"])  # 'distraction', 'useful', or 'neutral'
```

### Check if a Domain is Whitelisted
```python
from core.domain_classifier import domain_whitelist
print(domain_whitelist("google.com"))  # True or False
```

## Testing

Unit tests are provided in `tests/domain_classifier/`. Run with:
```bash
pytest tests/domain_classifier/
```

## Enhanced URL Resolution & Embedded Content Analysis

### 8. `url_resolver.py`
- **Purpose:** Resolves URLs and analyzes embedded content across platforms.
- **Key Classes:**
  - `URLResolver`: Follows redirects to identify final destination URLs.
  - `EmbeddedContentAnalyzer`: Detects embedded media content on third-party sites.
- **Key Features:**
  - Follows URL redirects (shortened links like t.co, bit.ly)
  - Detects YouTube videos embedded on platforms like Bing and Google search results
  - Identifies autoplay content that may be distracting
  - Preserves embedding context in metadata

### 9. `utils.py`
- **Purpose:** Utility functions for URL processing and content analysis.
- **Key Functions:**
  - `extract_domain(url: str) -> str`: Extracts domain from URLs
  - `is_youtube_url(url: str) -> bool`: Checks if a URL is YouTube
  - `extract_youtube_id(url: str) -> str`: Extracts YouTube video ID from various URL formats
  - `normalize_url(url: str) -> str`: Normalizes URLs for processing

## Autoplay Detection

The module can now identify distracting autoplay content on video sites:

```python
from core.domain_classifier.url_resolver import EmbeddedContentAnalyzer

analyzer = EmbeddedContentAnalyzer()
autoplay_info = analyzer.detect_autoplay_content(
    "https://www.youtube.com/watch?v=current_video", 
    current_video_id="current_video"
)

if autoplay_info.get('has_autoplay'):
    print(f"Autoplay detected: {autoplay_info['title']}")
```

## OpenAI Classifier Integration

### 10. `llm_classifier/openai_classifier.py`
- **Purpose:** Provides content classification using OpenAI's API for more accurate results.
- **Key Classes:**
  - `OpenAIBaseClassifier`: Base class for OpenAI API integration
  - `OpenAIYouTubeClassifier`: YouTube-specific classifier using OpenAI
- **Key Features:**
  - Uses OpenAI's GPT models for more nuanced content classification
  - Configurable model selection (tiers: default, standard, premium, fast)
  - Detailed prompt engineering and response parsing
  - Fallback to pattern-based classification if API is unavailable
  - Shared `ClassificationResult` type with local LLM classifiers

### Configuration
The OpenAI classifier is configured via a JSON file at `core/domain_classifier/llm_classifier/config/openai_config.json`:
- API key management (supports environment variables or direct configuration)
- Model tier selection (e.g., gpt-3.5-turbo, gpt-4.1-mini, etc.)
- Temperature and max token settings

### Usage Example

```python
# Import directly from the module
from core.domain_classifier.llm_classifier.openai_classifier import OpenAIYouTubeClassifier

# Create classifier instance (loads config from file)
classifier = OpenAIYouTubeClassifier()

# Classify a YouTube video
result = classifier.classify(
    "https://www.youtube.com/watch?v=example", 
    "youtube.com", 
    metadata=metadata
)

print(f"Classification: {result.label}")
print(f"Confidence: {result.score:.1f}%")
print(f"Reason: {result.reason}")
```

### Demo Script

A demonstration script is provided at `demos/domain_classifier/demo_openai_classification.py` to showcase the OpenAI classifier functionality:

```bash
python demos/domain_classifier/demo_openai_classification.py https://www.youtube.com/watch?v=example --model standard
```

The demo supports optional command-line arguments:
- `--model`: Select model tier (default, standard, premium, fast)
- `--api-key`: Provide API key directly (not recommended for production)

## Testing

Unit tests are provided in `tests/domain_classifier/`. Run with:
```bash
python -m pytest tests/domain_classifier/
```

### Test Components

The testing suite includes:

1. **URL Resolver Tests** (`test_url_resolver.py`):
   - Redirect handling and resolution
   - Embedded content detection on Bing and Google
   - Autoplay detection on YouTube pages
   - Integration with metadata fetching

2. **Mock Test Data**:
   - `bing_video_page.html`: Mock Bing video search results with embedded YouTube videos
   - `google_video_page.html`: Mock Google video search results with embedded YouTube videos
   - `youtube_page_with_autoplay.html`: YouTube page with autoplay content

3. **Test Execution**:
   - Individual test files can be run directly: `python tests/domain_classifier/test_url_resolver.py`
   - Test sections are clearly labeled in output for easier debugging

## Demo Scripts

Demo scripts are available in `demos/domain_classifier/` to showcase key features:

- `demo_url_resolution.py`: Demonstrates URL resolution and redirect handling
- `demo_embedded_content.py`: Shows embedded content detection on search engines
- `demo_classification.py`: Demonstrates full classification pipeline with metadata integration

## Extending the Module
- Add new domain categories or patterns in `domain_config.py`
- Update keyword lists or classification logic in `link_classifier.py` for new content types
- Extend embedded content detection to other platforms in `url_resolver.py`
- Extend metadata fetching in `metadata.py` for additional sources.

## Dependencies
- `requests`, `beautifulsoup4` (for metadata fetching)
- `pytest`, `unittest` (for testing)

## Authors & Contributions
- Designed for extensibility and integration with productivity or parental control systems.
- Contributions welcome! Please submit issues or pull requests for improvements.

---

For further details, refer to the docstrings in each module or contact the maintainers.
