"""
Text processing utilities for the RAG server.
"""
import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ChunkingConfig:
    """Configuration for advanced chunking algorithm."""
    min_tokens: int = 300
    max_tokens: int = 800
    overlap_tokens: int = 100
    tokenizer_model: str = "gpt-3.5-turbo"
    section_headers: List[str] = None
    
    def __post_init__(self):
        if self.section_headers is None:
            self.section_headers = [
                'abstract', 'introduction', 'related work', 'methodology', 
                'methods', 'experiments', 'results', 'discussion', 
                'conclusion', 'references', 'bibliography', 'appendix'
            ]

def preprocess_text(text: str) -> str:
    """
    Clean and preprocess text extracted from PDF to remove common artifacts.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
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

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Count tokens in text using tiktoken (OpenAI's tokenizer).
    
    Args:
        text: Text to count tokens for
        model: Model name for tokenizer (default: gpt-3.5-turbo)
        
    Returns:
        Token count
    """
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except (ImportError, KeyError):
        # Fallback to simple word-based counting if tiktoken fails
        logger.warning("tiktoken not available or model not found, using word-based token counting")
        return len(text.split())

def is_section_header(text: str, section_headers: List[str]) -> bool:
    """
    Check if text is a section header.
    
    Args:
        text: Text to check
        section_headers: List of section header keywords
        
    Returns:
        True if text appears to be a section header
    """
    text_stripped = text.strip()
    text_lower = text_stripped.lower()
    
    # Match exact section header (case-insensitive)
    if text_lower in section_headers:
        return True
    
    # Match numbered section headers (e.g., '1. Introduction', '2. Related Work')
    for header in section_headers:
        # Lowercase the header for matching
        header_words = header.lower().split()
        pattern = r'^\s*\d+\W*' + r'\W+'.join(map(re.escape, header_words)) + r'(\s|$)'
        if re.match(pattern, text_lower, re.IGNORECASE):
            return True
    
    # Check for all caps headers
    if text_stripped.isupper() and len(text_stripped.split()) <= 5:
        return True
    
    return False

def is_semantic_break(text: str) -> bool:
    """
    Check if text represents a semantic break that shouldn't be split.
    
    Args:
        text: Text to check
        
    Returns:
        True if this represents a semantic break
    """
    # Check for equations (simplified)
    if re.search(r'[=+\-*/\\]', text) and len(text.strip()) < 50:
        return True
    
    # Check for bullet points or numbered lists
    if re.match(r'^[\s]*[•\-\*]\s', text) or re.match(r'^[\s]*\d+\.\s', text):
        return True
    
    # Check for figure/table references
    if re.search(r'(Figure|Table)\s+\d+', text, re.IGNORECASE):
        return True
    
    # Check for citations
    if re.search(r'\[[\d,\s]+\]', text):
        return True
    
    return False

def split_into_sections(text: str, section_headers: List[str]) -> List[Tuple[str, str]]:
    """
    Split text into sections based on headers.
    
    Args:
        text: Text to split
        section_headers: List of section header keywords
        
    Returns:
        List of (section_name, section_content) tuples
    """
    lines = text.split('\n')
    sections = []
    current_section = "Unknown"
    current_content = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line is a section header
        if is_section_header(line, section_headers):
            # Save previous section
            if current_content:
                sections.append((current_section, '\n'.join(current_content)))
            
            # Start new section
            current_section = line
            current_content = []
        else:
            current_content.append(line)
    
    # Add the last section
    if current_content:
        sections.append((current_section, '\n'.join(current_content)))
    
    # If no sections were found, treat the entire text as one section
    if not sections:
        sections.append(("Content", text.strip()))
    
    return sections

def split_into_paragraphs(text: str) -> List[str]:
    """
    Split text into paragraphs.
    
    Args:
        text: Text to split
        
    Returns:
        List of paragraphs
    """
    # Split by double newlines (paragraph breaks)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    # If no double newlines, try single newlines
    if not paragraphs:
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    
    return paragraphs

def merge_paragraphs_semantically(paragraphs: List[str], config: ChunkingConfig) -> List[str]:
    """
    Recursively merge paragraphs while preserving semantic boundaries.
    
    Args:
        paragraphs: List of paragraphs to merge
        config: Chunking configuration
        
    Returns:
        List of merged chunks
    """
    if not paragraphs:
        return []
    
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    for i, paragraph in enumerate(paragraphs):
        paragraph_tokens = count_tokens(paragraph, config.tokenizer_model)
        
        # Check if adding this paragraph would exceed max_tokens
        if current_tokens + paragraph_tokens > config.max_tokens and current_chunk:
            # Current chunk is ready
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
            current_tokens = paragraph_tokens
        else:
            # Add to current chunk
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
            current_tokens += paragraph_tokens
    
    # Add the last chunk if it exists
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Post-process: ensure minimum token count
    final_chunks = []
    for chunk in chunks:
        chunk_tokens = count_tokens(chunk, config.tokenizer_model)
        if chunk_tokens >= config.min_tokens:
            final_chunks.append(chunk)
        elif final_chunks:
            # Merge with previous chunk if too short
            final_chunks[-1] = final_chunks[-1] + "\n\n" + chunk
    
    return final_chunks

def apply_overlap_sliding_window(chunks: List[str], config: ChunkingConfig) -> List[str]:
    """
    Apply sliding window overlap to chunks.
    
    Args:
        chunks: List of chunks
        config: Chunking configuration
        
    Returns:
        List of chunks with overlap
    """
    if not chunks or config.overlap_tokens <= 0:
        return chunks
    
    overlapped_chunks = []
    
    for i, chunk in enumerate(chunks):
        if i == 0:
            # First chunk: no overlap
            overlapped_chunks.append(chunk)
        else:
            # Add overlap from previous chunk
            prev_chunk = chunks[i-1]
            prev_words = prev_chunk.split()
            
            # Calculate overlap words
            overlap_words = max(0, len(prev_words) - config.overlap_tokens)
            overlap_text = ' '.join(prev_words[overlap_words:])
            
            # Create overlapped chunk
            overlapped_chunk = overlap_text + "\n\n" + chunk
            overlapped_chunks.append(overlapped_chunk)
    
    return overlapped_chunks

def advanced_chunk_by_structure(text: str, config: Optional[ChunkingConfig] = None) -> List[str]:
    """
    Advanced chunking algorithm with structure awareness and semantic preservation.
    
    Args:
        text: Text to chunk
        config: Chunking configuration (uses defaults if None)
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    if config is None:
        config = ChunkingConfig()
    
    # Step 1: Preprocess text
    text = preprocess_text(text)
    
    # Step 2: Split into sections
    sections = split_into_sections(text, config.section_headers)
    
    all_chunks = []
    
    for section_name, section_content in sections:
        if not section_content.strip():
            continue
            
        # Step 3: Split section into paragraphs
        paragraphs = split_into_paragraphs(section_content)
        
        if not paragraphs:
            continue
        
        # Step 4: Recursively merge paragraphs semantically
        section_chunks = merge_paragraphs_semantically(paragraphs, config)
        
        # Step 5: Add section metadata to chunks
        for chunk in section_chunks:
            # Add section header as prefix if chunk doesn't start with it
            if not chunk.lower().startswith(section_name.lower()):
                chunk = f"[{section_name}]\n\n{chunk}"
            all_chunks.append(chunk)
    
    # If no chunks were created through section-based chunking, fall back to paragraph-based
    if not all_chunks:
        paragraphs = split_into_paragraphs(text)
        if paragraphs:
            all_chunks = merge_paragraphs_semantically(paragraphs, config)
    
    # Step 6: Apply sliding window overlap if configured
    if config.overlap_tokens > 0 and all_chunks:
        all_chunks = apply_overlap_sliding_window(all_chunks, config)
    
    return all_chunks

def chunk_text_with_overlap(text: str, max_length: int = 1500, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: The input text to chunk.
        max_length: Maximum number of characters per chunk.
        overlap: Number of characters to overlap between consecutive chunks.
    
    Returns:
        List of text chunks.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + max_length, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == text_length:
            break
        start = end - overlap  # move back by overlap for next chunk
        if start < 0:
            start = 0
    return chunks

def chunk_by_paragraphs(text: str, max_chars: int = 1500) -> List[str]:
    """
    Split text into chunks by paragraphs, with preprocessing to clean the text.
    
    Args:
        text: Text to chunk
        max_chars: Maximum characters per chunk
        
    Returns:
        List of text chunks
    """
    # Preprocess text to remove common PDF artifacts
    text = preprocess_text(text)
    
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    
    for p in paragraphs:
        p = p.strip()
        if not p:  # Skip empty paragraphs
            continue
            
        if len(current) + len(p) < max_chars:
            if current:
                current += "\n\n" + p
            else:
                current = p
        else:
            if current.strip():  # Just check if not empty
                chunks.append(current.strip())
            current = p
    
    # Add the last chunk if it exists
    if current.strip():
        chunks.append(current.strip())
    
    return chunks

def extract_arxiv_id(input_str: str) -> str:
    """
    Extract arXiv ID from various input formats.
    
    Args:
        input_str: Input string that may contain arXiv ID
        
    Returns:
        Extracted arXiv ID or empty string
    """
    # Pattern for arXiv IDs: 4 digits, dot, 4-5 digits
    pattern = r'(\d{4}\.\d{4,5})'
    match = re.search(pattern, input_str)
    return match.group(1) if match else ""

def create_fine_chunks(text: str, min_chars: int = 300, max_chars: int = 500, 
                      min_sentences: int = 1, max_sentences: int = 3) -> List[str]:
    """
    Create fine-grained chunks based on sentences for citation suggestion and sentence-level similarity.
    
    Args:
        text: Text to chunk
        min_chars: Minimum characters per chunk
        max_chars: Maximum characters per chunk
        min_sentences: Minimum sentences per chunk
        max_sentences: Maximum sentences per chunk
        
    Returns:
        List of fine chunks
    """
    if not text:
        return []
    
    # Split text into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return []
    
    chunks = []
    current_chunk = ""
    current_sentences = 0
    
    for sentence in sentences:
        # Check if adding this sentence would exceed limits
        potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
        
        # Check character limits
        if len(potential_chunk) > max_chars and current_chunk:
            # Current chunk is ready
            if len(current_chunk) >= min_chars and current_sentences >= min_sentences:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
            current_sentences = 1
        else:
            # Check sentence limits
            if current_sentences >= max_sentences and current_chunk:
                # Current chunk is ready
                if len(current_chunk) >= min_chars:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
                current_sentences = 1
            else:
                # Add to current chunk
                current_chunk = potential_chunk
                current_sentences += 1
    
    # Add the last chunk if it meets minimum requirements
    if current_chunk and len(current_chunk) >= min_chars and current_sentences >= min_sentences:
        chunks.append(current_chunk.strip())
    
    return chunks

def create_coarse_chunks(text: str, min_chars: int = 1000, max_chars: int = 1500,
                        min_tokens: int = 300, max_tokens: int = 512) -> List[str]:
    """
    Create coarse-grained chunks for question answering and summarization.
    
    Args:
        text: Text to chunk
        min_chars: Minimum characters per chunk
        max_chars: Maximum characters per chunk
        min_tokens: Minimum tokens per chunk
        max_tokens: Maximum tokens per chunk
        
    Returns:
        List of coarse chunks
    """
    if not text:
        return []
    
    # Use the existing advanced chunking with custom configuration
    config = ChunkingConfig(
        min_tokens=min_tokens,
        max_tokens=max_tokens,
        overlap_tokens=50,  # Small overlap for coarse chunks
        tokenizer_model="gpt-3.5-turbo"
    )
    
    # Get chunks using advanced chunking
    chunks = advanced_chunk_by_structure(text, config)
    
    # Post-process to ensure character limits
    final_chunks = []
    for chunk in chunks:
        chunk_chars = len(chunk)
        chunk_tokens = count_tokens(chunk, config.tokenizer_model)
        
        # Check if chunk meets requirements
        if (chunk_chars >= min_chars and chunk_chars <= max_chars and 
            chunk_tokens >= min_tokens and chunk_tokens <= max_tokens):
            final_chunks.append(chunk)
        elif chunk_chars > max_chars:
            # Split oversized chunks
            sub_chunks = chunk_text_with_overlap(chunk, max_chars, 100)
            final_chunks.extend(sub_chunks)
        elif chunk_chars < min_chars and final_chunks:
            # Merge with previous chunk if too short
            final_chunks[-1] = final_chunks[-1] + "\n\n" + chunk
    
    return final_chunks 