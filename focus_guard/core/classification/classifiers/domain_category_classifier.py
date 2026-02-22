"""
Domain category classifier that maps domains to categories using configuration.

As of Section 7 consolidation, domain categories are read from DomainConfigManager
(domain_config.json) instead of app_config.json.
"""

import logging
from typing import Dict, Any, Optional, List

from focus_guard.core.domain.models import Domain, Category, Classification

logger = logging.getLogger(__name__)


def _get_domain_config_manager():
    """Lazy import to avoid circular dependencies."""
    try:
        from focus_guard.core.domain.domain_config_manager import get_domain_config_manager
        return get_domain_config_manager()
    except Exception:
        return None


class DomainCategoryClassifier:
    """Classifier that maps domains to categories using configuration data."""
    
    def __init__(self, config_path: Optional[str] = None, name: str = "domain_category"):
        """Initialize the domain category classifier.
        
        Args:
            config_path: Deprecated, ignored. Uses DomainConfigManager.
            name: Name of the classifier
        """
        self._name = name
        self._domain_categories: Dict[str, str] = {}
        self._load_domain_categories()
    
    @property
    def name(self) -> str:
        """Get the classifier name."""
        return self._name
    
    def _load_domain_categories(self):
        """Load domain categories from DomainConfigManager."""
        try:
            mgr = _get_domain_config_manager()
            if mgr is None:
                logger.warning("DomainConfigManager not available, using empty domain mappings")
                self._domain_categories = {}
                return
            
            # Get all domain categories from the unified config
            categories = mgr.get_domain_categories()
            logger.debug(f"Loaded {len(categories)} categories from DomainConfigManager")
            
            # Build reverse mapping: domain -> category
            for category_name, domains in categories.items():
                for domain in domains:
                    clean_domain = domain.lower().strip()
                    self._domain_categories[clean_domain] = category_name
            
            logger.info(f"Loaded {len(self._domain_categories)} domain mappings from DomainConfigManager")
            
        except Exception as e:
            logger.error(f"Failed to load domain categories: {e}", exc_info=True)
            self._domain_categories = {}
    
    async def classify(self, domain: Domain, context: Optional[Dict[str, Any]] = None) -> Optional[Classification]:
        """Classify domain into category.
        
        Args:
            domain: Domain to classify
            context: Optional context (not used by this classifier)
            
        Returns:
            Classification result or None if domain not found
        """
        domain_value = domain.value.lower()
        
        # Check exact match first
        if domain_value in self._domain_categories:
            category_name = self._domain_categories[domain_value]
            category = self._map_category_name(category_name)
            
            return Classification(
                domain=domain,
                category=category,
                confidence=0.9,
                metadata={
                    'method': 'domain_category_mapping',
                    'config_category': category_name,
                    'classifier': self.name
                }
            )
        
        # Check subdomain match (e.g., stanfordohs.pronto.io matches pronto.io)
        for mapped_domain, category_name in self._domain_categories.items():
            if domain_value.endswith('.' + mapped_domain):
                category = self._map_category_name(category_name)
                
                return Classification(
                    domain=domain,
                    category=category,
                    confidence=0.85,
                    metadata={
                        'method': 'domain_category_subdomain_match',
                        'matched_domain': mapped_domain,
                        'config_category': category_name,
                        'classifier': self.name
                    }
                )
        
        # No match found
        return None
    
    def _map_category_name(self, category_name: str) -> Category:
        """Map configuration category name to Category enum.
        
        Args:
            category_name: Category name from configuration
            
        Returns:
            Corresponding Category enum value
        """
        mapping = {
            'social_media': Category.SOCIAL_MEDIA,
            'video_streaming': Category.ENTERTAINMENT,  # Map video streaming to entertainment
            'games': Category.GAMING,
            'gaming': Category.GAMING,
            'entertainment': Category.ENTERTAINMENT,
            'news': Category.NEWS,
            'shopping': Category.SHOPPING,
            'productivity': Category.PRODUCTIVITY,
            'education': Category.EDUCATION,
            'technology': Category.TECHNOLOGY,
            'finance': Category.FINANCE
        }
        
        return mapping.get(category_name.lower(), Category.UNKNOWN)
    
    def get_supported_domains(self) -> List[str]:
        """Get list of supported domains.
        
        Returns:
            List of domain names this classifier can handle
        """
        return list(self._domain_categories.keys())


def create_domain_category_classifier(config_path: Optional[str] = None) -> DomainCategoryClassifier:
    """Factory function to create a domain category classifier.
    
    Args:
        config_path: Optional path to app config file
        
    Returns:
        Configured DomainCategoryClassifier instance
    """
    return DomainCategoryClassifier(config_path)
