import pdfminer.high_level
import logging
from pathlib import Path
from typing import Optional, Tuple
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """
    Extract text from a PDF file using pdfminer.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as string, or None if extraction failed
    """
    try:
        # Check if file exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return None
        
        # Check if file is actually a PDF
        if not pdf_path.lower().endswith('.pdf'):
            logger.warning(f"File doesn't have .pdf extension: {pdf_path}")
        
        logger.info(f"Extracting text from PDF: {pdf_path}")
        
        # Extract text using pdfminer
        text = pdfminer.high_level.extract_text(pdf_path)
        
        if not text or not text.strip():
            logger.warning(f"Extracted text is empty for: {pdf_path}")
            return None
        
        # Clean up the extracted text
        cleaned_text = clean_extracted_text(text)
        
        logger.info(f"Successfully extracted {len(cleaned_text)} characters from: {pdf_path}")
        return cleaned_text
        
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {str(e)}")
        return None

def clean_extracted_text(text: str) -> str:
    """
    Clean and preprocess extracted text from PDF.
    
    Args:
        text: Raw extracted text from PDF
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    import re
    
    # Remove excessive whitespace and normalize line breaks
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple line breaks to double
    text = re.sub(r' +', ' ', text)  # Multiple spaces to single
    
    # Remove common PDF artifacts
    text = re.sub(r'^\s*Page \d+\s*$', '', text, flags=re.MULTILINE)  # Page numbers
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)  # Standalone numbers
    
    # Remove headers and footers that appear on every page
    text = re.sub(r'^\s*[A-Z\s]{3,}\s*$', '', text, flags=re.MULTILINE)  # ALL CAPS headers
    
    # Remove common non-content lines
    text = re.sub(r'^\s*(Abstract|Introduction|Conclusion|References|Bibliography)\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Remove fragmented single-character lines
    text = re.sub(r'^\s*[a-zA-Z]\s*$', '', text, flags=re.MULTILINE)  # Single letters
    text = re.sub(r'^\s*[a-zA-Z]\s*[a-zA-Z]\s*$', '', text, flags=re.MULTILINE)  # Two letters
    text = re.sub(r'^\s*[a-zA-Z]\s*[a-zA-Z]\s*[a-zA-Z]\s*$', '', text, flags=re.MULTILINE)  # Three letters
    
    # Remove arXiv identifiers and URLs
    text = re.sub(r'https?://arxiv\.org/abs/\d+\.\d+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\d{4}\.\d{4,5}', '', text, flags=re.MULTILINE)
    
    # Remove fragmented content patterns
    text = re.sub(r'^\s*[a-zA-Z]\s*\n\s*[a-zA-Z]\s*\n\s*[a-zA-Z]', '', text, flags=re.MULTILINE | re.DOTALL)
    
    # Clean up mathematical expressions that might be broken across lines
    text = re.sub(r'([A-Za-z])\s*\n\s*([+\-*/=])', r'\1\2', text)  # Fix broken math expressions
    
    # Remove excessive punctuation
    text = re.sub(r'[.!?]{3,}', '...', text)  # Multiple punctuation to ellipsis
    
    # Normalize quotes and dashes
    text = text.replace('"', '"').replace('"', '"')  # Smart quotes to regular
    text = text.replace('–', '-').replace('—', '-')  # Em/en dashes to regular
    
    # Remove lines with too many isolated characters
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        words = line.split()
        isolated_chars = len(re.findall(r'\b[a-zA-Z]\b', line))
        if len(words) > 0 and isolated_chars <= len(words) * 0.4:
            cleaned_lines.append(line)
        elif len(words) == 0:
            continue  # Skip empty lines
        elif isolated_chars <= 2:  # Allow a few isolated chars
            cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Final cleanup: remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple line breaks to double
    text = re.sub(r' +', ' ', text)  # Multiple spaces to single
    
    return text.strip()

def extract_text_from_pdf_with_metadata(pdf_path: str) -> Optional[dict]:
    """
    Extract text from PDF and return with metadata.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary with text and metadata, or None if extraction failed
    """
    try:
        text = extract_text_from_pdf(pdf_path)
        if text is None:
            return None
        
        # Get file metadata
        file_path = Path(pdf_path)
        stat = file_path.stat()
        
        return {
            'text': text,
            'file_path': str(pdf_path),
            'file_size_bytes': stat.st_size,
            'file_size_mb': round(stat.st_size / (1024 * 1024), 2),
            'character_count': len(text),
            'word_count': len(text.split()),
            'line_count': len(text.split('\n'))
        }
        
    except Exception as e:
        logger.error(f"Failed to extract text with metadata from {pdf_path}: {str(e)}")
        return None

def extract_text_from_multiple_pdfs(pdf_paths: list) -> list:
    """
    Extract text from multiple PDF files.
    
    Args:
        pdf_paths: List of PDF file paths
        
    Returns:
        List of dictionaries with extraction results
    """
    results = []
    
    for pdf_path in pdf_paths:
        result = extract_text_from_pdf_with_metadata(pdf_path)
        if result:
            results.append(result)
        else:
            results.append({
                'file_path': pdf_path,
                'error': 'Failed to extract text',
                'text': None
            })
    
    return results

# Example usage and testing
def main():
    """Example usage of the PDF text extractor."""
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        print(f"Extracting text from: {pdf_path}")
        
        result = extract_text_from_pdf_with_metadata(pdf_path)
        if result:
            print(f"✓ Successfully extracted text")
            print(f"File: {result['file_path']}")
            print(f"Size: {result['file_size_mb']} MB")
            print(f"Characters: {result['character_count']}")
            print(f"Words: {result['word_count']}")
            print(f"Lines: {result['line_count']}")
            print("\n--- First 500 characters ---")
            print(result['text'][:500] + "..." if len(result['text']) > 500 else result['text'])
        else:
            print("✗ Failed to extract text")
    else:
        print("Usage: python pdf_text_extractor.py <path_to_pdf>")
        print("Example: python pdf_text_extractor.py papers/2302.13971v1_LLaMA_Open_and_Efficient_Foundation_Language_Mode.pdf")

if __name__ == "__main__":
    main() 