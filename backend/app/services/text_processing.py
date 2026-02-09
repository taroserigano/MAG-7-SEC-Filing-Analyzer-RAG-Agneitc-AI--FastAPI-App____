"""
Text processing utilities for chunking and extracting text from various formats.
OPTIMIZED: Faster chunking algorithm, reduced overhead.
"""
import re
from typing import List, Dict, Any
from pypdf import PdfReader
import logging

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,  # Reduced overlap for speed
    separator: str = " ",
    overlap: int = None,
) -> List[str]:
    """
    Split text into chunks with overlap.
    OPTIMIZED: Faster algorithm with reduced overlap.
    
    Args:
        text: Text to chunk
        chunk_size: Target size of each chunk (in characters)
        chunk_overlap: Number of overlapping characters between chunks
        separator: String to use for splitting (default: space)
        
    Returns:
        List of text chunks
    """
    if overlap is not None:
        chunk_overlap = overlap

    if not text:
        return []
    
    text_len = len(text)
    
    # Fast path for short text
    if text_len <= chunk_size:
        return [text]

    # Fast path: simple character-based chunking for no separator
    if separator not in text:
        step = max(1, chunk_size - chunk_overlap)
        return [text[i:i + chunk_size] for i in range(0, text_len, step)]
    
    # Optimized chunking with pre-allocated list
    chunks = []
    start = 0
    step = chunk_size - chunk_overlap
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        
        # Find a good break point (space) near the end
        if end < text_len:
            # Look for last space in the chunk
            last_space = text.rfind(separator, start, end)
            if last_space > start + chunk_size // 2:  # Only if reasonable break point
                end = last_space
        
        chunks.append(text[start:end])
        start = end - chunk_overlap if end < text_len else text_len
    
    return chunks


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from PDF file.
    
    Args:
        file_bytes: PDF file as bytes
        
    Returns:
        Extracted text
    """
    try:
        import io
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        full_text = "\n".join(text_parts)
        return clean_text(full_text)
        
    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        return ""


def extract_text_from_txt(file_bytes: bytes) -> str:
    """
    Extract text from TXT file.
    
    Args:
        file_bytes: TXT file as bytes
        
    Returns:
        Extracted text
    """
    try:
        text = file_bytes.decode('utf-8')
        return clean_text(text)
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode('latin-1')
            return clean_text(text)
        except Exception as e:
            logger.error(f"Error extracting TXT text: {str(e)}")
            return ""


def clean_text(text: str) -> str:
    """
    Clean and normalize text.
    
    Args:
        text: Raw text
        
    Returns:
        Cleaned text
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep common punctuation
    text = re.sub(r'[^\w\s.,;:!?()\-\'"$%&/]', '', text)
    
    # Remove URLs
    text = re.sub(r'http[s]?://\S+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    return text.strip()


def create_metadata_for_chunks(
    chunks: List[str],
    base_metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Create metadata dictionaries for each chunk.
    
    Args:
        chunks: List of text chunks
        base_metadata: Base metadata to include in all chunks
        
    Returns:
        List of metadata dicts
    """
    metadata_list = []
    
    for i, chunk in enumerate(chunks):
        metadata = {
            **base_metadata,
            "chunk_index": i,
            "chunk_length": len(chunk)
        }
        metadata_list.append(metadata)
    
    return metadata_list
