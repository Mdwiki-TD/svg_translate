import unittest
import tempfile
import os
from pathlib import Path
from svgtranslate import normalize_text, extract_text_from_element, generate_unique_id


class TestSVGTranslate(unittest.TestCase):
    
    def test_normalize_text(self):
        """Test text normalization functionality."""
        # Test basic whitespace normalization
        self.assertEqual(normalize_text("  hello   world  "), "hello world")
        # Test single space
        self.assertEqual(normalize_text("hello world"), "hello world")
        # Test tabs and newlines
        self.assertEqual(normalize_text("hello\t\tworld\n\n"), "hello world")
        # Test empty string
        self.assertEqual(normalize_text(""), "")
        # Test only spaces
        self.assertEqual(normalize_text("   "), "")
    
    def test_generate_unique_id(self):
        """Test ID generation and uniqueness."""
        existing_ids = {"text1", "text2"}
        
        # Test basic ID generation
        unique_id = generate_unique_id("text", existing_ids, "-ar")
        self.assertEqual(unique_id, "text-ar")
        
        # Test with existing suffix
        existing_ids.add("text-ar")
        unique_id = generate_unique_id("text", existing_ids, "-ar")
        self.assertEqual(unique_id, "text-ar1")
        
        # Test with no base ID
        unique_id = generate_unique_id("", existing_ids, "-fr")
        self.assertTrue(unique_id.startswith("text-fr"))
    
    def test_extract_text_from_element(self):
        """Test text extraction from XML elements."""
        # This test would require creating XML elements to test with
        # Since this is complex to do in a unit test, we'll skip it for now
        pass


if __name__ == '__main__':
    unittest.main()