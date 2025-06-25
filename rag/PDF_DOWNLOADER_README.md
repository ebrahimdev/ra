# Research Paper PDF Downloader

A Python utility for downloading research papers from various sources and storing them in a local directory.

## Features

- **Multiple Source Support**: Downloads from arXiv, DOI links, bioRxiv, medRxiv, SSRN, and more
- **Automatic Filename Generation**: Creates clean, descriptive filenames based on paper titles
- **Error Handling**: Robust error handling with detailed logging
- **File Management**: Lists and manages downloaded papers
- **Flexible Usage**: Can be used as a standalone script or imported as a module

## Installation

The required dependencies are already included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from pdf_downloader import PDFDownloader

# Initialize the downloader (creates a 'papers' directory)
downloader = PDFDownloader()

# Download a paper
result = downloader.download_paper("https://arxiv.org/abs/2302.13971")
if result:
    print(f"Downloaded: {result}")
```

### Advanced Usage

```python
from pdf_downloader import PDFDownloader

# Initialize with custom directory
downloader = PDFDownloader(papers_dir="my_papers")

# Download with custom filename
result = downloader.download_paper(
    "https://arxiv.org/abs/2302.13971",
    filename="my_custom_name"
)

# List all downloaded papers
papers = downloader.list_downloaded_papers()
for paper in papers:
    print(f"{paper['filename']} - {paper['size_mb']} MB")

# Get info about a specific paper
info = downloader.get_paper_info("2302.13971v1_LLaMA_Open_and_Efficient_Foundation_Language_Mode.pdf")
if info:
    print(f"File size: {info['size_mb']} MB")
```

### Command Line Usage

Run the example script:

```bash
python example_download.py
```

Or run the main downloader directly:

```bash
python pdf_downloader.py
```

## Supported Sources

### 1. arXiv (`arxiv.org`)
- **URL Formats**: 
  - `https://arxiv.org/abs/2302.13971`
  - `https://arxiv.org/pdf/2302.13971.pdf`
- **Features**: Uses the official arXiv API for reliable downloads

### 2. DOI Links (`doi.org`)
- **URL Format**: `https://doi.org/10.1038/s41586-020-2649-2`
- **Note**: May require institutional access for some papers

### 3. Preprint Servers
- **bioRxiv**: `https://www.biorxiv.org/content/10.1101/2020.01.01.123456v1`
- **medRxiv**: `https://www.medrxiv.org/content/10.1101/2020.01.01.123456v1`
- **SSRN**: `https://papers.ssrn.com/sol3/papers.cfm?abstract_id=123456`

### 4. Generic PDF Downloads
- Works with any direct PDF URL
- Automatically detects PDF content type
- Handles various filename patterns

## File Structure

```
rag-server/
├── pdf_downloader.py          # Main downloader class
├── example_download.py        # Example usage script
├── papers/                    # Downloaded PDFs directory
│   ├── 2302.13971v1_LLaMA_Open_and_Efficient_Foundation_Language_Mode.pdf
│   └── ...
└── PDF_DOWNLOADER_README.md   # This file
```

## API Reference

### PDFDownloader Class

#### Constructor
```python
PDFDownloader(papers_dir: str = "papers")
```
- `papers_dir`: Directory to store downloaded PDFs (default: "papers")

#### Methods

##### `download_paper(url: str, filename: Optional[str] = None) -> Optional[str]`
Downloads a research paper from a URL.
- `url`: URL of the research paper
- `filename`: Optional custom filename (without extension)
- Returns: Path to downloaded PDF file, or None if failed

##### `list_downloaded_papers() -> list`
Lists all downloaded papers with metadata.
- Returns: List of dictionaries with file information

##### `get_paper_info(filename: str) -> Optional[dict]`
Gets information about a specific downloaded paper.
- `filename`: Name of the PDF file
- Returns: Dictionary with file metadata, or None if not found

## Error Handling

The downloader includes comprehensive error handling:

- **Network Errors**: Timeout and connection error handling
- **Invalid URLs**: Validation of URL formats
- **Missing Files**: Checks for file existence after download
- **Content Type Validation**: Warns if response doesn't appear to be a PDF
- **Detailed Logging**: All operations are logged for debugging

## Limitations

1. **Access Restrictions**: Some papers may require institutional access or subscriptions
2. **Rate Limiting**: Some sources may limit download frequency
3. **Google Scholar**: Doesn't provide direct PDF downloads
4. **ResearchGate**: May require authentication and has anti-scraping measures

## Examples

### Download Multiple Papers

```python
urls = [
    "https://arxiv.org/abs/2302.13971",
    "https://arxiv.org/abs/2302.13972",
    "https://doi.org/10.1038/s41586-020-2649-2"
]

downloader = PDFDownloader()
for url in urls:
    result = downloader.download_paper(url)
    if result:
        print(f"✓ Downloaded: {result}")
    else:
        print(f"✗ Failed: {url}")
```

### Batch Processing with Custom Names

```python
papers = [
    ("https://arxiv.org/abs/2302.13971", "llama_paper"),
    ("https://arxiv.org/abs/2302.13972", "gpt_paper"),
]

downloader = PDFDownloader()
for url, name in papers:
    result = downloader.download_paper(url, filename=name)
    print(f"Downloaded {name}: {result}")
```

## Contributing

To add support for new sources:

1. Add a new method to the `PDFDownloader` class (e.g., `_download_new_source`)
2. Add the domain to the `research_domains` dictionary in the constructor
3. Implement the download logic in the new method
4. Add appropriate error handling and logging

## License

This code is part of the RAG server project and follows the same licensing terms. 