"""
Domain category classifier that maps domains to categories using configuration.
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List

from focus_guard.core.domain.models import Domain, Category, Classification

logger = logging.getLogger(__name__)


class DomainCategoryClassifier:
    """Classifier that maps domains to categories using configuration data."""
    
    def __init__(self, config_path: Optional[str] = None, name: str = "domain_category"):
        """Initialize the domain category classifier.
        
        Args:
            config_path: Optional path to app config file
            name: Name of the classifier
        """
        self._name = name
        self._config_path = config_path or self._get_default_config_path()
        self._domain_categories = {}
        self._load_domain_categories()
    
    @property
    def name(self) -> str:
        """Get the classifier name."""
        return self._name
    
    def _get_default_config_path(self) -> str:
        """Get the default path to app config file."""
        # Look for app_config.json in the config directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up to focus_guard root, then to config
        config_dir = os.path.join(current_dir, "..", "..", "..", "..", "config")
        config_path = os.path.join(config_dir, "app_config.json")
        return os.path.normpath(config_path)
    
    def _load_domain_categories(self):
        """Load domain categories from configuration."""
        try:
            logger.info(f"Loading domain categories from: {self._config_path}")
            
            if not os.path.exists(self._config_path):
                logger.error(f"Config file not found: {self._config_path}")
                return
            
            with open(self._config_path, 'r') as f:
                config = json.load(f)
            
            # Get distraction categories from app config
            distraction_categories = config.get("distraction_categories", {})
            logger.info(f"Raw distraction_categories from config: {distraction_categories}")
            
            # Build reverse mapping: domain -> category
            for category_name, domains in distraction_categories.items():
                logger.info(f"Processing category '{category_name}' with domains: {domains}")
                for domain in domains:
                    # Clean domain (remove protocols, paths, etc.)
                    clean_domain = domain.lower().strip()
                    if clean_domain.startswith(('http://', 'https://')):
                        clean_domain = clean_domain.split('://', 1)[1]
                    if '/' in clean_domain:
                        clean_domain = clean_domain.split('/', 1)[0]
                    
                    self._domain_categories[clean_domain] = category_name
                    logger.info(f"Mapped domain '{clean_domain}' -> '{category_name}'")
            
            logger.info(f"Loaded {len(self._domain_categories)} domain mappings")
            logger.info(f"Domain mappings: {self._domain_categories}")
            
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
        
        # Check if domain contains any of the mapped domains
        for mapped_domain, category_name in self._domain_categories.items():
            if mapped_domain in domain_value or domain_value in mapped_domain:
                category = self._map_category_name(category_name)
                
                return Classification(
                    domain=domain,
                    category=category,
                    confidence=0.8,
                    metadata={
                        'method': 'domain_category_partial_match',
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
