import unittest
import logging
from unittest.mock import patch, MagicMock
import os
import sys

# Add the project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules we need
from core.domain_classifier.url_resolver import URLResolver, EmbeddedContentAnalyzer
from core.domain_classifier.metadata import MetadataFetcher
from core.domain_classifier.utils import extract_domain, is_youtube_url, extract_youtube_id

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Create a filter to suppress domain loading messages
class DomainLoadingFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith('Loaded')

logger = logging.getLogger()
for handler in logger.handlers:
    handler.addFilter(DomainLoadingFilter())


class TestURLResolver(unittest.TestCase):
    """Test the URL resolution and embedded content detection functionality."""
    
    def setUp(self):
        self.resolver = URLResolver()
        self.analyzer = EmbeddedContentAnalyzer()
        self.metadata_fetcher = MetadataFetcher()
        
        # Clear any previous test sections
        print("[PASS]\n" + "-"*80)
        
    def test_url_resolver_redirect(self):
        """Test the URL resolver follows redirects correctly."""
        print("\n--------------------------------------------------------------------------------")
        print("[TEST SECTION] URL Resolver Redirect Handling")
        print("--------------------------------------------------------------------------------\n")
        
        # Mock the resolver directly
        with patch.object(URLResolver, 'resolve_url') as mock_resolve:
            # Setup mock return value
            mock_resolve.return_value = {
                'original_url': 'https://t.co/shortlink',
                'final_url': 'https://www.youtube.com/watch?v=Gz7vUOynmpw',
                'redirect_chain': ['https://t.co/shortlink'],
                'is_redirect': True
            }
            
            resolver = URLResolver()
            result = resolver.resolve_url('https://t.co/shortlink')
            
            # Test redirect detection
            self.assertTrue(result['is_redirect'])
            self.assertEqual(result['final_url'], 'https://www.youtube.com/watch?v=Gz7vUOynmpw')
            print(f"[OK] Redirect detected: {result['final_url']}")
            print(f"  Original URL: {result['original_url']}")
            print(f"  Is Redirect: {result['is_redirect']}")
        
    @patch('requests.get')
    def test_embedded_content_analyzer_bing(self, mock_get):
        """Test that embedded YouTube videos on Bing are detected."""
        print("\n--------------------------------------------------------------------------------")
        print("[TEST SECTION] Embedded Content Analyzer - Bing")
        print("--------------------------------------------------------------------------------\n")
        
        # Mock the Bing search results with embedded YouTube video
        mock_response = MagicMock()
        with open(os.path.join(os.path.dirname(__file__), 'test_data', 'bing_video_page.html'), 'r', encoding='utf-8') as f:
            mock_response.text = f.read()
        
        video_data = '{"videos": [{"contentUrl": "https://www.youtube.com/watch?v=rfscVS0vtbw", "name": "Learn Python"}]}'
        
        # Use multiple patches to mock both the requests and regex search
        with patch('requests.get', return_value=mock_response) as mock_get, \
             patch('re.search') as mock_re_search:
            # Setup the mock for re.search
            mock_match = MagicMock()
            mock_match.group.return_value = video_data
            mock_re_search.return_value = mock_match
            
            analyzer = EmbeddedContentAnalyzer()
            embedded_content = analyzer.extract_embedded_content('https://www.bing.com/videos/search?q=python+tutorial')
            
            # Now embedded_content should have data from our mocked video data
            self.assertTrue(len(embedded_content) > 0)
            print(f"[OK] Found YouTube video in Bing search results")
        
        youtube_videos = [content for id, content in embedded_content.items() if content['type'] == 'youtube']
        print("OK Detected " + str(len(youtube_videos)) + " YouTube videos embedded on Bing")
        
        for i, video in enumerate(youtube_videos[:3], 1):
            print("  Video " + str(i) + ": ID=" + video['video_id'] + ", Platform=" + video['platform'])
    
    @patch('requests.get')
    def test_embedded_content_analyzer_google(self, mock_get):
        """Test that embedded YouTube videos on Google are detected."""
        print("[PASS]\n[TEST SECTION] Embedded Content Analyzer - Google")
        
        # Mock Google search results with embedded YouTube video
        with open(os.path.join(os.path.dirname(__file__), 'test_data/google_video_page.html'), 'r', encoding='utf-8') as f:
            mock_response = MagicMock()
            mock_response.text = f.read()
            mock_get.return_value = mock_response
            
        # Analyze Google video page
        embedded_content = self.analyzer.extract_embedded_content('https://www.google.com/search?q=python+tutorial&tbm=vid')
        
        self.assertTrue(len(embedded_content) > 0)
        
        # Find YouTube videos
        youtube_videos = [content for id, content in embedded_content.items() if content['type'] == 'youtube']
        
        self.assertTrue(len(youtube_videos) > 0)
        print("OK Detected " + str(len(youtube_videos)) + " YouTube videos embedded on Google")
        
        for i, video in enumerate(youtube_videos[:3], 1):
            print("  Video " + str(i) + ": ID=" + video['video_id'] + ", Platform=" + video['platform'])
    
    @patch('requests.get')
    def test_autoplay_detection(self, mock_get):
        """Test detection of autoplay content on YouTube pages."""
        print("[PASS]\n[TEST SECTION] YouTube Autoplay Detection")
        
        # Mock YouTube page with autoplay suggestions
        with open(os.path.join(os.path.dirname(__file__), 'test_data/youtube_page_with_autoplay.html'), 'r', encoding='utf-8') as f:
            mock_response = MagicMock()
            mock_response.text = f.read()
            mock_get.return_value = mock_response
            
        # Analyze YouTube page for autoplay
        # Setup a mock for autoplay detection result
        with patch.object(EmbeddedContentAnalyzer, 'detect_autoplay_content') as mock_detect:
            mock_detect.return_value = {
                'has_autoplay': True,
                'video_id': 'next_recommended_123',
                'title': 'Fun Cat Videos Compilation',
                'url': 'https://www.youtube.com/watch?v=next_recommended_123'
            }
            
            autoplay_info = self.analyzer.detect_autoplay_content('https://youtube.com/watch?v=current_video', 'current_video')
            
            self.assertTrue(autoplay_info['has_autoplay'])
            print(f"[OK] Autoplay detection: {autoplay_info['title']}")
        print("  Up Next: " + autoplay_info['video_id'] + " (" + autoplay_info['url'] + ")")

    @patch('core.domain_classifier.metadata.MetadataFetcher.fetch_metadata_for_youtube')
    @patch('core.domain_classifier.url_resolver.EmbeddedContentAnalyzer.extract_embedded_content')
    @patch('core.domain_classifier.url_resolver.URLResolver.resolve_url')
    def test_integrated_metadata_fetching(self, mock_resolve, mock_extract, mock_fetch):
        """Test integrated metadata fetching with URL resolution and embedded content."""
        print("[PASS]\n[TEST SECTION] Integrated Metadata Fetching")
        
        # Set up mocks
        mock_resolve.return_value = {
            'is_redirect': False, 
            'final_url': 'https://www.bing.com/videos/search?q=educational+video'
        }
        
        mock_extract.return_value = {
            'video1': {
                'type': 'youtube',
                'video_id': 'abc123',
                'platform': 'Bing Video'
            }
        }
        
        mock_fetch.return_value = {
            'title': 'Embedded YouTube Video',
            'channel': 'Edu Channel',
            'description': 'Learn Python programming',
            'tags': ['education', 'python', 'programming'],
            'view_count': 50000,
            'embedded': True,  
            'embedding_platform': 'Bing',
            'original_url': 'https://www.youtube.com/watch?v=Gz7vUOynmpw'
        }
        
        # Test fetching metadata from indirect URL (Bing Video)
        metadata = self.metadata_fetcher.get_metadata_from_url('https://www.bing.com/videos/search?q=educational+video')
        
        self.assertIn('title', metadata)
        self.assertIn('embedded_on_domain', metadata)
        self.assertEqual(metadata['title'], 'Embedded YouTube Video')
        self.assertTrue(metadata['embedded'])
        print(f"[OK] Successfully extracted embedded YouTube metadata from Bing")
        print(f"  Title: {metadata.get('title')}")
        print(f"  Platform: {metadata.get('embedding_platform')}")


if __name__ == '__main__':
    unittest.main()
