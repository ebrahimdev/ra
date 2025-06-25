from typing import List

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

# Example usage and testing
def main():
    sample_text = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 100
    )
    print(f"Total text length: {len(sample_text)}")
    chunks = chunk_text_with_overlap(sample_text, max_length=200, overlap=50)
    print(f"Number of chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1} (length: {len(chunk)}) ---\n{chunk[:100]}...")

if __name__ == "__main__":
    main() 