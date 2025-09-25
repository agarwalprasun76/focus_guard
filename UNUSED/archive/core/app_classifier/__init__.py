"""
App Classifier Module

This module provides functionality to classify applications and determine if they should be
allowed based on the current calendar context and predefined rules.
"""

from .app_classifier import get_app_classifier, AppClassifier
from .app_categories import get_app_category, APP_CATEGORIES
from .context_rules import ContextRules

__all__ = [
    'get_app_classifier',
    'AppClassifier',
    'get_app_category',
    'APP_CATEGORIES',
    'ContextRules'
]
