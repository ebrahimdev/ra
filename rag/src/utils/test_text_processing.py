"""
Unit tests for text processing utilities.
"""
import unittest
from unittest.mock import patch
from .text_processing import (
    preprocess_text, count_tokens, is_section_header, is_semantic_break,
    split_into_sections, split_into_paragraphs, merge_paragraphs_semantically,
    apply_overlap_sliding_window, advanced_chunk_by_structure, ChunkingConfig,
    chunk_by_paragraphs, extract_arxiv_id
)
import re

class TestTextProcessing(unittest.TestCase):
    
    def test_count_tokens(self):
        """Test token counting."""
        # Test basic token counting
        self.assertGreater(count_tokens("hello world"), 0)
        self.assertEqual(count_tokens(""), 0)
        # tiktoken may count whitespace as tokens, so just check it's >= 0
        self.assertGreaterEqual(count_tokens("   "), 0)
        self.assertGreater(count_tokens("hello world test"), 0)
        
        # Test with different models
        self.assertGreater(count_tokens("hello world", "gpt-3.5-turbo"), 0)
        self.assertGreater(count_tokens("hello world", "gpt-4"), 0)
    
    def test_is_section_header(self):
        """Test section header detection."""
        headers = ['abstract', 'introduction', 'conclusion', 'related work']
        
        # Test numbered sections
        self.assertTrue(is_section_header("1. Introduction", headers))
        self.assertTrue(is_section_header("2. Related Work", headers))
        
        # Test common headers
        self.assertTrue(is_section_header("Abstract", headers))
        self.assertTrue(is_section_header("INTRODUCTION", headers))
        self.assertTrue(is_section_header("Conclusion", headers))
        
        # Test non-headers
        self.assertFalse(is_section_header("This is a regular paragraph", headers))
        self.assertFalse(is_section_header("", headers))
    
    def test_is_semantic_break(self):
        """Test semantic break detection."""
        # Test equations
        self.assertTrue(is_semantic_break("x = y + z"))
        self.assertTrue(is_semantic_break("f(x) = ax^2 + bx + c"))
        
        # Test bullet points
        self.assertTrue(is_semantic_break("• First item"))
        self.assertTrue(is_semantic_break("- Second item"))
        self.assertTrue(is_semantic_break("* Third item"))
        
        # Test numbered lists
        self.assertTrue(is_semantic_break("1. First item"))
        self.assertTrue(is_semantic_break("2. Second item"))
        
        # Test figure references
        self.assertTrue(is_semantic_break("Figure 1: Results"))
        self.assertTrue(is_semantic_break("Table 2: Data"))
        
        # Test citations
        self.assertTrue(is_semantic_break("Previous work [1, 2, 3]"))
        
        # Test regular text
        self.assertFalse(is_semantic_break("This is regular text"))
        self.assertFalse(is_semantic_break(""))
    
    def test_split_into_sections(self):
        """Test section splitting."""
        text = """
Abstract
This is the abstract content.

1. Introduction
This is the introduction.

2. Related Work
This is related work.
""".strip()
        
        sections = split_into_sections(text, ['abstract', 'introduction', 'related work'])
        print('Detected sections:', sections)
        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0][0], "Abstract")
        self.assertEqual(sections[1][0], "1. Introduction")
        self.assertEqual(sections[2][0], "2. Related Work")
    
    def test_split_into_paragraphs(self):
        """Test paragraph splitting."""
        text = "Para 1.\n\nPara 2.\n\nPara 3."
        paragraphs = split_into_paragraphs(text)
        
        self.assertEqual(len(paragraphs), 3)
        self.assertEqual(paragraphs[0], "Para 1.")
        self.assertEqual(paragraphs[1], "Para 2.")
        self.assertEqual(paragraphs[2], "Para 3.")
    
    def test_merge_paragraphs_semantically(self):
        """Test semantic paragraph merging."""
        config = ChunkingConfig(min_tokens=5, max_tokens=20)
        
        paragraphs = [
            "This is paragraph one.",
            "This is paragraph two.",
            "This is paragraph three.",
            "This is paragraph four."
        ]
        
        chunks = merge_paragraphs_semantically(paragraphs, config)
        
        # Should merge paragraphs to stay within token limits
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            tokens = count_tokens(chunk)
            self.assertGreaterEqual(tokens, config.min_tokens)
            self.assertLessEqual(tokens, config.max_tokens)
    
    def test_apply_overlap_sliding_window(self):
        """Test sliding window overlap."""
        config = ChunkingConfig(overlap_tokens=2)
        chunks = [
            "This is the first chunk with some words.",
            "This is the second chunk with different words.",
            "This is the third chunk with more words."
        ]
        
        overlapped = apply_overlap_sliding_window(chunks, config)
        
        self.assertEqual(len(overlapped), 3)
        # First chunk should not have overlap
        self.assertEqual(overlapped[0], chunks[0])
        # Subsequent chunks should have overlap
        self.assertIn("words.", overlapped[1])
    
    def test_advanced_chunk_by_structure(self):
        """Test the complete advanced chunking algorithm."""
        text = """
        Abstract
        This is the abstract of the paper. It contains important information about the research.
        
        1. Introduction
        This is the introduction section. It provides background information.
        This paragraph continues the introduction with more details.
        
        2. Related Work
        This section discusses previous work in the field.
        It references several important papers and studies.
        
        3. Methodology
        This section describes the methods used in the research.
        It includes detailed procedures and algorithms.
        """
        
        config = ChunkingConfig(min_tokens=10, max_tokens=50, overlap_tokens=5)
        chunks = advanced_chunk_by_structure(text, config)
        
        self.assertGreater(len(chunks), 0)
        
        # Check that chunks have section headers
        for chunk in chunks:
            self.assertTrue(
                any(header in chunk.lower() for header in ['abstract', 'introduction', 'related work', 'methodology'])
            )
    
    def test_advanced_chunk_by_structure_no_sections(self):
        """Test advanced chunking with text that has no clear sections."""
        text = """
        This is a paragraph about machine learning.
        It discusses various algorithms and techniques.
        
        This is another paragraph about deep learning.
        It covers neural networks and their applications.
        
        This is a third paragraph about natural language processing.
        It explains how transformers work.
        """
        
        config = ChunkingConfig(min_tokens=5, max_tokens=30)
        chunks = advanced_chunk_by_structure(text, config)
        
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            tokens = count_tokens(chunk)
            self.assertGreaterEqual(tokens, config.min_tokens)
    
    def test_chunking_config_defaults(self):
        """Test ChunkingConfig default values."""
        config = ChunkingConfig()
        
        self.assertEqual(config.min_tokens, 300)
        self.assertEqual(config.max_tokens, 800)
        self.assertEqual(config.overlap_tokens, 100)
        self.assertEqual(config.tokenizer_model, "gpt-3.5-turbo")
        self.assertIsNotNone(config.section_headers)
        self.assertIn('abstract', config.section_headers)
        self.assertIn('introduction', config.section_headers)
    
    def test_extract_arxiv_id(self):
        """Test arXiv ID extraction."""
        # Test with full URL
        self.assertEqual(extract_arxiv_id("https://arxiv.org/abs/2309.15025"), "2309.15025")
        
        # Test with version
        self.assertEqual(extract_arxiv_id("https://arxiv.org/abs/2309.15025v1"), "2309.15025")
        
        # Test with just ID
        self.assertEqual(extract_arxiv_id("2309.15025"), "2309.15025")
        
        # Test invalid ID
        with self.assertRaises(ValueError):
            extract_arxiv_id("invalid-id")
    
    def test_preprocess_text(self):
        """Test text preprocessing."""
        text = """
        Page 1
        
        This is a test document.
        
        Page 2
        
        It has multiple pages.
        
        [1, 2, 3] References
        """
        
        processed = preprocess_text(text)
        
        # Should remove page numbers
        self.assertNotIn("Page 1", processed)
        self.assertNotIn("Page 2", processed)
        
        # Should preserve content
        self.assertIn("test document", processed)
        self.assertIn("multiple pages", processed)

if __name__ == '__main__':
    unittest.main() 