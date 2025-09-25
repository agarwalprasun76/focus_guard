"""
Specialized Classifiers Package

This package contains specialized content classifiers for different types of content
such as entertainment, publications, Google Drive, YouTube, etc.
"""

from .entertainment_classifier import EntertainmentClassifier, entertainment_classifier
from .publication_classifier import PublicationClassifier, publication_classifier
from .google_drive_classifier import GoogleDriveClassifier, google_drive_classifier
from .link_classifier import LinkClassifier, link_classifier
from .youtube_classifier import YouTubeClassifier, youtube_classifier
from .keyword_classifier import KeywordClassifier, keyword_classifier

# Export all classifiers
__all__ = [
    'EntertainmentClassifier', 'entertainment_classifier',
    'PublicationClassifier', 'publication_classifier',
    'GoogleDriveClassifier', 'google_drive_classifier',
    'YouTubeClassifier', 'youtube_classifier',
    'KeywordClassifier', 'keyword_classifier',
    'LinkClassifier', 'link_classifier'
]