"""
Domain classifier implementation.

This module provides the implementation of the domain classifier, which
categorizes domains based on predefined rules and configurations.
"""

from typing import Optional, Dict, List, Set, Tuple
import logging

from core_v2.classification.base import Classifier
from core_v2.domain.models import Domain, Category
from core_v2.config.loader import ConfigurationLoader
from core_v2.utils.domain_utils import (
    normalize_domain,
    is_valid_domain,
    get_domain_parts,
    is_ip_address,
    is_localhost
)
from core_v2.domain.constants import CATEGORY_TO_ENUM_MAPPING


class StandardDomainClassifier(Classifier):
    """
    Standard domain classifier implementation.
    
    This classifier categorizes domains based on predefined rules and
    configurations loaded from the configuration system.
    """
    
    def __init__(self, config_loader: ConfigurationLoader):
        """
        Initialize the domain classifier.
        
        Args:
            config_loader: The configuration loader to use.
        """
        self._config_loader = config_loader
        # Store both the string category from config and the mapped Category enum
        self._domain_cache: Dict[str, Tuple[str, Optional[Category]]] = {}
        self._logger = logging.getLogger("core_v2.classification.domain_classifier")
        
        # Build the domain cache
        self._rebuild_cache()
        
        # Register for configuration changes
        self._config_loader.register_change_callback(self._on_config_changed)
    
    def _map_string_category_to_enum(self, category_str: str) -> Optional[Category]:
        """
        Map a string category from configuration to a Category enum value.
        
        Args:
            category_str: The string category from configuration.
            
        Returns:
            The corresponding Category enum value, or None if not found.
        """
        try:
            # First try direct mapping through CATEGORY_TO_ENUM_MAPPING
            if category_str in CATEGORY_TO_ENUM_MAPPING:
                enum_str = CATEGORY_TO_ENUM_MAPPING[category_str]
                return Category[enum_str]
            
            # Fall back to direct conversion if not in mapping
            return Category.from_string(category_str.upper())
        except (ValueError, KeyError) as e:
            self._logger.warning(f"Failed to map category string '{category_str}' to enum: {e}")
            return None
    
    def _rebuild_cache(self) -> None:
        """Rebuild the domain cache from the configuration."""
        self._domain_cache.clear()
        
        # Get categories from configuration
        categories = self._config_loader.domain_categories
        
        # Build cache for faster lookups
        for category_str, domains in categories.categories.items():
            # Map the string category to a Category enum value
            category_enum = self._map_string_category_to_enum(category_str)
            
            for domain in domains:
                normalized = normalize_domain(domain)
                if normalized:
                    # Store both the original string category and the mapped enum
                    self._domain_cache[normalized] = (category_str, category_enum)
        
        self._logger.info(f"Domain cache rebuilt with {len(self._domain_cache)} entries")
        self._logger.debug(f"Domain cache contents: {self._domain_cache}")
    
    def _on_config_changed(self) -> None:
        """Handle configuration changes."""
        self._logger.info("Configuration changed, rebuilding domain cache")
        self._rebuild_cache()
    
    @property
    def name(self) -> str:
        """
        Get the name of the classifier.
        
        Returns:
            The classifier name.
        """
        return "standard_domain_classifier"
    
    def classify(self, domain: Domain) -> Optional[Category]:
        """
        Classify a domain into a category.
        
        Args:
            domain: The domain to classify.
            
        Returns:
            The category of the domain, or None if it couldn't be classified.
        """
        # Log the classification attempt
        self._logger.info(f"Classifying domain: {domain.value}")
        
        # Skip classification for IP addresses and localhost
        if is_ip_address(domain.value) or is_localhost(domain.value):
            self._logger.info(f"Skipping classification for special domain: {domain.value}")
            return None
        
        # Check exact match first (fast path)
        if domain.value in self._domain_cache:
            _, category_enum = self._domain_cache[domain.value]
            if category_enum:
                self._logger.info(f"Domain {domain.value} found in cache with category: {category_enum.name}")
                return category_enum
            else:
                self._logger.warning(f"Domain {domain.value} found in cache but has no valid category enum")
                return None
        
        # Check subdomains
        domain_parts = get_domain_parts(domain.value)
        for i in range(1, len(domain_parts)):
            parent_domain = '.'.join(domain_parts[i:])
            if parent_domain in self._domain_cache:
                _, category_enum = self._domain_cache[parent_domain]
                if category_enum:
                    self._logger.info(f"Domain {domain.value} matched to parent domain {parent_domain} with category: {category_enum.name}")
                    return category_enum
                else:
                    self._logger.warning(f"Domain {domain.value} matched to parent domain {parent_domain} but has no valid category enum")
                    continue
        
        self._logger.warning(f"Domain {domain.value} not found in any category")
        return None
    
    def get_all_domains(self) -> Dict[str, List[str]]:
        """
        Get all domains organized by category.
        
        Returns:
            Dictionary mapping categories to lists of domains.
        """
        categories = self._config_loader.domain_categories
        return categories.categories
    
    def get_all_categories(self) -> List[str]:
        """
        Get a list of all available domain categories.
        
        Returns:
            List of category names.
        """
        categories = self._config_loader.domain_categories
        return list(categories.categories.keys())
