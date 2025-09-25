import sys
import os
import asyncio
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from focus_guard.core.blocking.strategies.domain_excluder import DomainExcluderStrategy
from focus_guard.core.blocking.strategies.category_blocker import CategoryBlockerStrategy
from focus_guard.core.blocking.pipeline import BlockingPipeline
from focus_guard.core.blocking.strategies.registry import BlockingStrategyRegistry
from focus_guard.core.domain.models import Domain, Category, Classification
from focus_guard.core.config.loader import ConfigurationLoader
from focus_guard.core.classification.classifiers.domains.youtube import create_youtube_classifier

# Create a test domain class that includes classification info
@dataclass
class TestDomain(Domain):
    """Test domain class that includes classification info."""
    _category: Category = None
    _classification: Classification = None
    
    @property
    def category(self):
        return self._category
        
    @category.setter
    def category(self, value):
        self._category = value
        
    @property
    def classification(self):
        return self._classification
        
    @classification.setter
    def classification(self, value):
        self._classification = value
        if value:
            self._category = value.category

async def test_youtube_blocking():
    print("Testing YouTube domain blocking...")
    
    # Initialize the domain excluder
    excluder = DomainExcluderStrategy()
    
    # Initialize the category blocker
    config_loader = ConfigurationLoader()
    category_blocker = CategoryBlockerStrategy(config_loader)
    
    # Initialize the blocking pipeline
    registry = BlockingStrategyRegistry()
    registry.register(excluder, priority=100)
    registry.register(category_blocker, priority=50)
    pipeline = BlockingPipeline(registry)
    
    # Initialize the YouTube classifier
    youtube_classifier = create_youtube_classifier(use_llm=False, use_rules=True)
    
    # Test cases with metadata - aligned with test_youtube_enhanced.py test cases
    test_cases = [
        # Education content
        {
            "domain": "youtube.com",
            "context": {
                "url": "https://www.youtube.com/watch?v=abc123",
                "title": "Learn Python Programming",
                "channel": "Coding Academy"
            },
            "expected_category": Category.EDUCATION,
            "should_block": False
        },
        # Entertainment content
        {
            "domain": "youtube.com",
            "context": {
                "url": "https://www.youtube.com/watch?v=xyz789",
                "title": "Funny Cat Videos",
                "channel": "Funny Clips"
            },
            "expected_category": Category.ENTERTAINMENT,
            "should_block": True
        },
        # Productivity content
        {
            "domain": "youtube.com",
            "context": {
                "url": "https://www.youtube.com/watch?v=def456",
                "title": "Time Management Strategies",
                "channel": "Productivity Pro"
            },
            "expected_category": Category.PRODUCTIVITY,
            "should_block": False
        },
        # Non-YouTube domain
        {
            "domain": "example.com",
            "context": {
                "url": "https://example.com",
                "title": "Example Domain"
            },
            "expected_category": None,
            "should_block": False
        }
    ]
    
    print("\n--- Testing YouTube Classification ---")
    for case in test_cases:
        domain_obj = TestDomain(value=case["domain"])
        
        # Classify the domain
        classification = await youtube_classifier.classify(domain_obj, case["context"])
        
        # Verify classification matches expected
        if case["expected_category"] is None:
            assert classification is None, f"Expected no classification for {case['domain']}"
            print(f"Domain: {case['domain']:<20} Not classified by YouTube classifier (as expected)")
        else:
            assert classification is not None, f"Expected classification for {case['domain']}"
            assert classification.category == case["expected_category"], \
                f"Expected {case['expected_category']} but got {classification.category}"
            domain_obj.classification = classification
            domain_obj.category = classification.category
            print(f"Domain: {case['domain']:<20} Classified as: {classification.category.name}")
    
    print("\n--- Testing Blocking Decisions ---")
    for case in test_cases:
        domain_obj = TestDomain(value=case["domain"])
        
        # Classify the domain if it's a YouTube domain
        if "youtube.com" in case["domain"]:
            classification = await youtube_classifier.classify(domain_obj, case["context"])
            assert classification is not None, f"Expected classification for {case['domain']}"
            domain_obj.classification = classification
            domain_obj.category = classification.category
        
        # Test blocking decisions
        exclude_decision = excluder.should_block(domain_obj)
        category_decision = category_blocker.should_block(domain_obj)
        pipeline_decision = await pipeline.should_block(domain_obj)
        
        # Verify blocking behavior
        if case["should_block"]:
            assert category_decision.should_block, \
                f"Expected {case['domain']} to be blocked but it wasn't"
            assert pipeline_decision.should_block, \
                f"Expected {case['domain']} to be blocked in pipeline but it wasn't"
        else:
            assert not category_decision.should_block, \
                f"Expected {case['domain']} to be allowed but it was blocked"
            assert not pipeline_decision.should_block, \
                f"Expected {case['domain']} to be allowed in pipeline but it was blocked"
        
        # Print test results
        print(f"\nDomain: {case['domain']}")
        print(f"Title: {case['context'].get('title')}")
        if hasattr(domain_obj, 'category') and domain_obj.category:
            print(f"Category: {domain_obj.category.name}")
        print(f"Expected to block: {case['should_block']}")
        print(f"Category Blocker: Blocked: {category_decision.should_block} - {category_decision.reason}")
        print(f"Full Pipeline: Blocked: {pipeline_decision.should_block}")

if __name__ == "__main__":
    asyncio.run(test_youtube_blocking())
