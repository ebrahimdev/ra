"""
PDF service for downloading and processing research papers.
"""
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
import pdfminer.high_level

from ..config import PAPERS_DIR
from ..utils.text_processing import extract_arxiv_id

logger = logging.getLogger(__name__)

class PDFService:
    """Service for downloading and processing PDF papers."""
    
    def __init__(self, papers_dir: str = PAPERS_DIR):
        """
        Initialize the PDF service.
        
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
    
    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
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
            
            logger.info(f"Successfully extracted {len(text)} characters from: {pdf_path}")
            return text
            
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {str(e)}")
            return None
    
    def download_arxiv_pdf_text(self, arxiv_id: str) -> str:
        """Download and extract text from an arXiv paper."""
        try:
            client = arxiv.Client()
            search = arxiv.Search(id_list=[arxiv_id])
            results = list(client.results(search))
            
            if not results:
                raise ValueError(f"ArXiv paper with ID {arxiv_id} not found. Please check the ID and try again.")
            
            paper = results[0]
            
            with tempfile.TemporaryDirectory() as tmpdir:
                pdf_path = f"{tmpdir}/{paper.get_short_id()}.pdf"
                
                # Use requests to download the PDF directly
                pdf_url = f"http://arxiv.org/pdf/{arxiv_id}"
                response = requests.get(pdf_url, stream=True, timeout=30)
                response.raise_for_status()
                
                with open(pdf_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                return self.extract_text_from_pdf(pdf_path)
                
        except Exception as e:
            logger.error(f"Failed to download arXiv paper {arxiv_id}: {str(e)}")
            raise ValueError(f"Failed to download arXiv paper {arxiv_id}: {str(e)}")
    
    def _download_arxiv(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download paper from arXiv."""
        try:
            arxiv_id = extract_arxiv_id(url)
            client = arxiv.Client()
            search = arxiv.Search(id_list=[arxiv_id])
            results = list(client.results(search))
            
            if not results:
                logger.error(f"ArXiv paper with ID {arxiv_id} not found")
                return None
            
            paper = results[0]
            
            if not filename:
                filename = paper.get_short_id()
            
            pdf_path = self.papers_dir / f"{filename}.pdf"
            
            # Use requests to download the PDF directly
            pdf_url = f"http://arxiv.org/pdf/{arxiv_id}"
            response = requests.get(pdf_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return str(pdf_path)
            
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
            # Generate filename if not provided
            if not filename:
                # Extract filename from URL or use timestamp
                parsed_url = urlparse(url)
                path_filename = os.path.basename(parsed_url.path)
                if path_filename and path_filename.lower().endswith('.pdf'):
                    filename = path_filename[:-4]  # Remove .pdf extension
                else:
                    filename = f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            pdf_path = self.papers_dir / f"{filename}.pdf"
            
            # Download the PDF
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                logger.info(f"Successfully downloaded PDF: {pdf_path}")
                return str(pdf_path)
            else:
                raise FileNotFoundError("PDF file was not created or is empty")
                
        except Exception as e:
            logger.error(f"Failed to download generic PDF from {url}: {str(e)}")
            return None
    
    def list_downloaded_papers(self) -> list:
        """
        List all downloaded papers.
        
        Returns:
            List of paper filenames
        """
        papers = []
        for pdf_file in self.papers_dir.glob("*.pdf"):
            papers.append(pdf_file.name)
        return sorted(papers)
    
    def get_paper_info(self, filename: str) -> Optional[dict]:
        """
        Get information about a downloaded paper.
        
        Args:
            filename: Name of the PDF file
            
        Returns:
            Dictionary with paper information, or None if not found
        """
        pdf_path = self.papers_dir / filename
        if not pdf_path.exists():
            return None
        
        try:
            stat = pdf_path.stat()
            return {
                'filename': filename,
                'file_path': str(pdf_path),
                'file_size_bytes': stat.st_size,
                'file_size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get paper info for {filename}: {str(e)}")
            return None 