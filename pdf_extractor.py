"""
PDF text extraction module.
Extracts text from PDF files while preserving document structure.
"""

from pypdf import PdfReader
from pathlib import Path
import sys


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF file while preserving structure.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text with preserved structure (paragraphs, line breaks)
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        Exception: If PDF reading fails
    """
    pdf_path_obj = Path(pdf_path)
    
    # Validate file exists
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Validate it's a PDF file
    if pdf_path_obj.suffix.lower() != '.pdf':
        raise ValueError(f"File is not a PDF: {pdf_path}")
    
    try:
        reader = PdfReader(pdf_path)
        text_parts = []
        
        # Extract text from each page
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text()
                if page_text.strip():  # Only add non-empty pages
                    text_parts.append(page_text)
            except Exception as e:
                # Log page extraction error but continue with other pages
                print(f"Warning: Could not extract text from page {page_num}: {e}", 
                      file=sys.stderr)
        
        if not text_parts:
            raise ValueError("No text could be extracted from the PDF")
        
        # Join pages with double newline to preserve structure
        full_text = "\n\n".join(text_parts)
        
        return full_text
        
    except Exception as e:
        raise Exception(f"Error reading PDF file: {e}")

