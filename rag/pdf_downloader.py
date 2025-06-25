import os
import requests
import re
import tempfile
from urllib.parse import urlparse, urljoin
from pathlib import Path
import logging
from typing import Optional, Tuple
import arxiv
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFDownloader:
    def __init__(self, papers_dir: str = "papers"):
        """
        Initialize the PDF downloader.
        
        Args:
            papers_dir: Directory to store downloaded PDFs
        """
        self.papers_dir = Path(papers_dir)
        self.papers_dir.mkdir(exist_ok=True)
        logger.info(f"PDFs will be stored in: {self.papers_dir.absolute()}")
        
        # Common research paper domains
        self.research_domains = {
            'arxiv.org': self._download_arxiv,
            'doi.org': self._download_doi,
            'scholar.google.com': self._download_google_scholar,
            'researchgate.net': self._download_researchgate,
            'semanticscholar.org': self._download_semantic_scholar,
            'biorxiv.org': self._download_biorxiv,
            'medrxiv.org': self._download_medrxiv,
            'ssrn.com': self._download_ssrn,
        }
    
    def download_paper(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Download a research paper from a URL.
        
        Args:
            url: URL of the research paper
            filename: Optional custom filename (without extension)
            
        Returns:
            Path to downloaded PDF file, or None if failed
        """
        try:
            logger.info(f"Attempting to download paper from: {url}")
            
            # Parse URL to determine the source
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Try to find a specific handler for this domain
            for known_domain, handler in self.research_domains.items():
                if known_domain in domain:
                    logger.info(f"Using {known_domain} handler")
                    return handler(url, filename)
            
            # Fallback to generic PDF download
            logger.info("Using generic PDF download handler")
            return self._download_generic_pdf(url, filename)
            
        except Exception as e:
            logger.error(f"Failed to download paper from {url}: {str(e)}")
            return None
    
    def _download_arxiv(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download paper from arXiv."""
        try:
            # Extract arXiv ID from URL
            arxiv_id = self._extract_arxiv_id(url)
            if not arxiv_id:
                raise ValueError("Could not extract arXiv ID from URL")
            
            # Use arxiv library to download
            search = arxiv.Search(id_list=[arxiv_id])
            paper = next(search.results())
            
            # Generate filename if not provided
            if not filename:
                filename = f"{paper.get_short_id()}_{paper.title.replace(' ', '_')[:50]}"
                filename = re.sub(r'[^\w\-_.]', '', filename)  # Clean filename
            
            pdf_path = self.papers_dir / f"{filename}.pdf"
            
            # Download the PDF
            paper.download_pdf(dirpath=str(self.papers_dir), filename=f"{filename}.pdf")
            
            if pdf_path.exists():
                logger.info(f"Successfully downloaded arXiv paper: {pdf_path}")
                return str(pdf_path)
            else:
                raise FileNotFoundError("PDF file was not created")
                
        except Exception as e:
            logger.error(f"Failed to download arXiv paper: {str(e)}")
            return None
    
    def _download_doi(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download paper from DOI link."""
        try:
            # Extract DOI from URL
            doi_match = re.search(r'doi\.org/(.+)', url)
            if not doi_match:
                raise ValueError("Could not extract DOI from URL")
            
            doi = doi_match.group(1)
            
            # Try to find PDF link through DOI
            # This is a simplified approach - in practice you might need to handle different publishers
            pdf_url = f"https://doi.org/{doi}"
            
            return self._download_generic_pdf(pdf_url, filename or f"doi_{doi.replace('/', '_')}")
            
        except Exception as e:
            logger.error(f"Failed to download DOI paper: {str(e)}")
            return None
    
    def _download_google_scholar(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download paper from Google Scholar."""
        try:
            # Google Scholar doesn't provide direct PDF downloads
            # This would require more complex scraping or finding alternative sources
            logger.warning("Google Scholar doesn't provide direct PDF downloads. Try finding the paper on arXiv or publisher website.")
            return None
            
        except Exception as e:
            logger.error(f"Failed to download Google Scholar paper: {str(e)}")
            return None
    
    def _download_researchgate(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download paper from ResearchGate."""
        try:
            # ResearchGate requires authentication and has anti-scraping measures
            logger.warning("ResearchGate downloads require authentication and may be blocked.")
            return self._download_generic_pdf(url, filename)
            
        except Exception as e:
            logger.error(f"Failed to download ResearchGate paper: {str(e)}")
            return None
    
    def _download_semantic_scholar(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download paper from Semantic Scholar."""
        try:
            # Try to extract paper ID and find PDF
            paper_id_match = re.search(r'/paper/([^/]+)', url)
            if paper_id_match:
                paper_id = paper_id_match.group(1)
                # Semantic Scholar API might provide PDF links
                api_url = f"https://api.semanticscholar.org/v1/paper/{paper_id}"
                response = requests.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    if 'pdf' in data and data['pdf']:
                        return self._download_generic_pdf(data['pdf'], filename or f"semantic_{paper_id}")
            
            return self._download_generic_pdf(url, filename)
            
        except Exception as e:
            logger.error(f"Failed to download Semantic Scholar paper: {str(e)}")
            return None
    
    def _download_biorxiv(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download paper from bioRxiv."""
        try:
            # bioRxiv papers are usually available as PDFs
            return self._download_generic_pdf(url, filename)
            
        except Exception as e:
            logger.error(f"Failed to download bioRxiv paper: {str(e)}")
            return None
    
    def _download_medrxiv(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download paper from medRxiv."""
        try:
            # medRxiv papers are usually available as PDFs
            return self._download_generic_pdf(url, filename)
            
        except Exception as e:
            logger.error(f"Failed to download medRxiv paper: {str(e)}")
            return None
    
    def _download_ssrn(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download paper from SSRN."""
        try:
            # SSRN papers are usually available as PDFs
            return self._download_generic_pdf(url, filename)
            
        except Exception as e:
            logger.error(f"Failed to download SSRN paper: {str(e)}")
            return None
    
    def _download_generic_pdf(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Generic PDF download handler."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Check if response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                logger.warning(f"Response doesn't appear to be a PDF (content-type: {content_type})")
            
            # Generate filename if not provided
            if not filename:
                # Try to extract filename from URL or headers
                if 'content-disposition' in response.headers:
                    content_disp = response.headers['content-disposition']
                    filename_match = re.search(r'filename="?([^"]+)"?', content_disp)
                    if filename_match:
                        filename = filename_match.group(1).replace('.pdf', '')
                
                if not filename:
                    # Extract from URL
                    parsed_url = urlparse(url)
                    filename = Path(parsed_url.path).stem
                    if not filename:
                        filename = f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Clean filename
            filename = re.sub(r'[^\w\-_.]', '', filename)
            pdf_path = self.papers_dir / f"{filename}.pdf"
            
            # Download the file
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Successfully downloaded PDF: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"Failed to download generic PDF: {str(e)}")
            return None
    
    def _extract_arxiv_id(self, url: str) -> Optional[str]:
        """Extract arXiv ID from URL."""
        # Match patterns like 1234.5678 or 1234.5678v1
        arxiv_patterns = [
            r'(\d{4}\.\d{4,5})(v\d+)?',
            r'arxiv\.org/abs/(\d{4}\.\d{4,5})(v\d+)?',
            r'arxiv\.org/pdf/(\d{4}\.\d{4,5})(v\d+)?\.pdf'
        ]
        
        for pattern in arxiv_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def list_downloaded_papers(self) -> list:
        """List all downloaded papers."""
        pdf_files = list(self.papers_dir.glob("*.pdf"))
        papers = []
        
        for pdf_file in pdf_files:
            stat = pdf_file.stat()
            papers.append({
                'filename': pdf_file.name,
                'path': str(pdf_file),
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return papers
    
    def get_paper_info(self, filename: str) -> Optional[dict]:
        """Get information about a specific downloaded paper."""
        pdf_path = self.papers_dir / filename
        if not pdf_path.exists():
            return None
        
        stat = pdf_path.stat()
        return {
            'filename': filename,
            'path': str(pdf_path),
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        }


def main():
    """Example usage of the PDF downloader."""
    downloader = PDFDownloader()
    
    # Example URLs to test
    test_urls = [
        "https://arxiv.org/abs/2302.13971",
        "https://arxiv.org/pdf/2302.13971.pdf",
        # Add more test URLs here
    ]
    
    print("=== PDF Downloader Test ===")
    
    for url in test_urls:
        print(f"\nDownloading: {url}")
        result = downloader.download_paper(url)
        if result:
            print(f"✓ Successfully downloaded: {result}")
        else:
            print(f"✗ Failed to download: {url}")
    
    print(f"\n=== Downloaded Papers ===")
    papers = downloader.list_downloaded_papers()
    for paper in papers:
        print(f"- {paper['filename']} ({paper['size_mb']} MB)")


if __name__ == "__main__":
    main() 