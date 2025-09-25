import unittest
from core.blocker.domain_blocker import should_block, block_reason
from core.domain_classifier.domain_excluder import _excluded_domains

class TestDomainBlocker(unittest.TestCase):
    def setUp(self):
        # Patch _excluded_domains for predictable testing
        _excluded_domains.clear()
        _excluded_domains.update({"pornhub.com", "bet365.com", "fakenewswebsite.com"})

    def tearDown(self):
        _excluded_domains.clear()

    def test_block_reason_default(self):
        self.assertEqual(block_reason("pornhub.com"), "excluded")
        self.assertEqual(block_reason("bet365.com"), "excluded")
        self.assertIsNone(block_reason("khanacademy.org"))
        self.assertIsNone(block_reason("facebook.com"))
        self.assertIsNone(block_reason("randomsite.xyz"))

    def test_should_block_default(self):
        self.assertTrue(should_block("pornhub.com"))
        self.assertTrue(should_block("bet365.com"))
        self.assertFalse(should_block("khanacademy.org"))
        self.assertFalse(should_block("facebook.com"))
        self.assertFalse(should_block("randomsite.xyz"))

    def test_approved_only(self):
        self.assertTrue(should_block("facebook.com", approved_only=True))
        self.assertTrue(should_block("randomsite.xyz", approved_only=True))
        self.assertFalse(should_block("khanacademy.org", approved_only=True))
        self.assertFalse(should_block("artofproblemsolving.com", approved_only=True))

    def test_block_by_category(self):
        self.assertTrue(should_block("facebook.com", block_categories=["social"]))
        self.assertTrue(should_block("cnn.com", block_categories=["news"]))
        self.assertFalse(should_block("khanacademy.org", block_categories=["social"]))
        self.assertFalse(should_block("randomsite.xyz", block_categories=["news"]))

if __name__ == "__main__":
    unittest.main()
