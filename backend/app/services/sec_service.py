"""
SEC filings service for fetching and processing SEC documents.
"""
import re
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from bs4 import BeautifulSoup
from pathlib import Path
import hashlib
import json
import asyncio

logger = logging.getLogger(__name__)

# MAG7 ticker to CIK mapping
MAG7_CIKS = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "AMZN": "0001018724",
    "GOOG": "0001652044",  # Alphabet Inc.
    "GOOGL": "0001652044",
    "META": "0001326801",
    "NVDA": "0001045810",
    "TSLA": "0001318605"
}


class SECService:
    """Service for fetching and processing SEC filings."""
    
    def __init__(self, cache_dir: str = "./sec_cache"):
        """Initialize SEC service with caching support."""
        # Expose MAG7 mapping on the instance for tests
        self.MAG7_CIKS = MAG7_CIKS
        self.base_url = "https://www.sec.gov"
        self.headers = {
            "User-Agent": "Portfolio App contact@example.com"
        }
        # Setup cache directory
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        logger.info(f"SEC cache directory: {self.cache_dir.absolute()}")
    
    def get_cik(self, ticker: str) -> Optional[str]:
        """
        Get CIK number for a ticker symbol.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            CIK number or None
        """
        ticker_upper = ticker.upper()
        return MAG7_CIKS.get(ticker_upper)
    
    def fetch_recent_filings(
        self,
        ticker: str,
        form_types: List[str] = ["10-K", "10-Q"],
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent SEC filings for a ticker.
        
        We fetch **per form type** to avoid mixing 8-Ks or other
        irrelevant filings and then sort by filing date desc.
        """
        cik = self.get_cik(ticker)
        if not cik:
            logger.warning(f"CIK not found for ticker: {ticker}")
            return []

        filings: List[Dict[str, Any]] = []

        try:
            base_url = f"{self.base_url}/cgi-bin/browse-edgar"

            for form_type in form_types:
                params = {
                    "action": "getcompany",
                    "CIK": cik,
                    "type": form_type,  # limit to the requested form
                    "owner": "exclude",
                    "count": count,
                    "output": "atom",
                }

                response = requests.get(base_url, params=params, headers=self.headers)
                response.raise_for_status()
                content = response.text

                # Extract filing info from atom feed entries
                # Parse <filing-date>, <link>, and <title> from each <entry>
                entry_pattern = r'<entry>.*?</entry>'
                entries = re.findall(entry_pattern, content, re.DOTALL)
                
                for entry in entries:
                    # Extract filing date
                    date_match = re.search(r'<filing-date>(\d{4}-\d{2}-\d{2})</filing-date>', entry)
                    filing_date = date_match.group(1) if date_match else "unknown"
                    
                    # Extract link
                    link_match = re.search(r'<link href="([^"]+)"', entry)
                    link = link_match.group(1) if link_match else ""
                    
                    # Extract title
                    title_match = re.search(r'<title>([^<]+)</title>', entry)
                    title = title_match.group(1) if title_match else ""

                    if form_type not in title:
                        continue  # skip mismatched types
                    
                    if not link:
                        continue

                    year = int(filing_date[:4]) if filing_date != "unknown" else datetime.now().year

                    filings.append({
                        "ticker": ticker,
                        "form_type": form_type,
                        "filing_date": filing_date,
                        "title": title,
                        "link": link,
                        "year": year,
                    })

            # Sort by filing_date desc and cap per form type
            def parse_date(d: str) -> datetime:
                try:
                    return datetime.strptime(d, "%Y-%m-%d")
                except Exception:
                    return datetime.min

            filings.sort(key=lambda f: parse_date(f["filing_date"]), reverse=True)

            # Keep at most `count` per form_type
            limited: List[Dict[str, Any]] = []
            per_type_counts = {ft: 0 for ft in form_types}
            for filing in filings:
                ft = filing["form_type"]
                if per_type_counts.get(ft, 0) >= count:
                    continue
                per_type_counts[ft] += 1
                limited.append(filing)

            logger.info(f"Found {len(limited)} filings for {ticker}")
            return limited

        except Exception as e:
            logger.error(f"Error fetching SEC filings for {ticker}: {str(e)}")
            return []
    
    def fetch_filing_text(self, filing_url: str) -> str:
        """
        Fetch the text content of a SEC filing.
        
        Args:
            filing_url: URL of the filing index page
            
        Returns:
            Text content of the filing
        """
        try:
            # If this is an index page, find the actual document
            if '-index.htm' in filing_url:
                response = requests.get(filing_url, headers=self.headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for the main document (usually .htm file, not -index.htm)
                # Priority: iXBRL document, then primary .htm document
                doc_url = None
                
                # First try to find iXBRL document link
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    # Skip the interactive viewer URLs
                    if '/ix?doc=' in href:
                        # Extract the actual document URL from the viewer
                        doc_url = href.replace('/ix?doc=', '')
                        break
                    # Look for primary document (10-k.htm, 10-q.htm, aapl-DATE.htm, etc)
                    elif href.endswith('.htm') and '-index.htm' not in href:
                        # Check if this is marked as iXBRL
                        if 'iXBRL' in link.get_text():
                            doc_url = href
                            break
                        elif not doc_url:  # Save first .htm as fallback
                            doc_url = href
                
                if doc_url:
                    # Handle relative URLs
                    if doc_url.startswith('/'):
                        doc_url = f"https://www.sec.gov{doc_url}"
                    elif not doc_url.startswith('http'):
                        base_url = filing_url.rsplit('/', 1)[0]
                        doc_url = f"{base_url}/{doc_url}"
                    
                    logger.info(f"Found document URL: {doc_url}")
                    filing_url = doc_url
            
            # Fetch the actual document
            response = requests.get(filing_url, headers=self.headers)
            response.raise_for_status()
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it
            text = soup.get_text(separator=' ')
            
            # Remove excessive whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.error(f"Error fetching filing text: {str(e)}")
            return ""
    
    def extract_sections(self, text: str, form_type: str) -> Dict[str, str]:
        """
        Extract key sections from a SEC filing.
        
        For 10-K: Business, Risk Factors, MD&A, Financial Statements
        For 10-Q: MD&A, Financial Statements
        For 8-K: Current Report items
        
        Args:
            text: Full text of the filing
            form_type: Type of SEC form
            
        Returns:
            Dict mapping section names to their content
        """
        sections = {}
        
        # Skip XBRL metadata at the beginning - look for "Table of Contents" or first Item
        # This helps avoid chunking schema/metadata
        content_start = 0
        toc_match = re.search(r'Table\s+of\s+Contents', text, re.IGNORECASE)
        if toc_match:
            content_start = toc_match.start()
        else:
            # Look for "Part I" or "Item 1" as start markers
            part_match = re.search(r'(Part\s+I[^V]|PART\s+I[^V])', text)
            if part_match:
                content_start = part_match.start()
        
        # Extract narrative content (skip first content_start chars if found)
        if content_start > 1000:  # Only skip if we found a significant offset
            text = text[content_start:]
            logger.info(f"Skipped {content_start} characters of metadata")
        
        if form_type == "10-K":
            # Try to find actual section boundaries with more flexible patterns
            section_patterns = {
                "business": (
                    r'(?:Item\s*1[^A0-9]|ITEM\s*1[^A0-9])(?:\.|\s)*(?:Business|BUSINESS)(.*?)'
                    r'(?:Item\s*1A|ITEM\s*1A|Item\s*2|ITEM\s*2)'
                ),
                "risk_factors": (
                    r'(?:Item\s*1A|ITEM\s*1A)(?:\.|\s)*(?:Risk|RISK)(.*?)'
                    r'(?:Item\s*1B|ITEM\s*1B|Item\s*2|ITEM\s*2)'
                ),
                "mda": (
                    r'(?:Item\s*7[^A0-9]|ITEM\s*7[^A0-9])(?:\.|\s)*(?:Management|MANAGEMENT)(.*?)'
                    r'(?:Item\s*7A|ITEM\s*7A|Item\s*8|ITEM\s*8)'
                ),
            }
        elif form_type == "10-Q":
            section_patterns = {
                "mda": (
                    r'(?:Item\s*2|ITEM\s*2)(?:\.|\s)*(?:Management|MANAGEMENT)(.*?)'
                    r'(?:Item\s*[34]|ITEM\s*[34])'
                ),
            }
        else:
            # For other forms, return cleaned text
            sections["full_text"] = text
            return sections
        
        # Extract sections using regex
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                section_text = match.group(1).strip()
                if len(section_text) > 500:  # Only include if substantial content
                    sections[section_name] = section_text
                    logger.info(f"Extracted {section_name}: {len(section_text)} characters")
        
        # If no sections found or sections are too small, chunk the full text intelligently
        if not sections or sum(len(s) for s in sections.values()) < len(text) * 0.3:
            logger.info(f"Section extraction found limited content, using full text ({len(text)} chars)")
            sections["full_text"] = text
        
        return sections
    
    def _get_cache_key(self, ticker: str, form_type: str, filing_date: str) -> str:
        """Generate cache key for a filing."""
        key_str = f"{ticker}_{form_type}_{filing_date}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached_filing(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached filing if it exists and is not expired."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            # Check file age
            file_age_days = (datetime.now().timestamp() - cache_file.stat().st_mtime) / 86400
            
            # Expire after 90 days for 10-Q, 365 days for 10-K
            data = json.loads(cache_file.read_text())
            form_type = data.get("form_type", "")
            max_age = 365 if form_type == "10-K" else 90
            
            if file_age_days > max_age:
                logger.info(f"Cache expired for {cache_key} ({file_age_days:.0f} days old)")
                cache_file.unlink()
                return None
            
            logger.info(f"✅ Cache hit: {data.get('ticker')} {form_type} {data.get('filing_date')}")
            return data
            
        except Exception as e:
            logger.error(f"Error reading cache {cache_key}: {e}")
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]):
        """Save filing data to cache as both JSON and readable text files."""
        try:
            # Save JSON cache (for metadata + full data)
            cache_file = self.cache_dir / f"{cache_key}.json"
            cache_file.write_text(json.dumps(data, indent=2))
            
            # Save human-readable text files
            ticker = data.get('ticker', 'UNKNOWN')
            form_type = data.get('form_type', 'UNKNOWN')
            filing_date = data.get('filing_date', 'unknown')
            
            # Create readable filename
            readable_name = f"{ticker}_{form_type}_{filing_date}".replace('/', '_')
            
            # Save full text as TXT
            txt_file = self.cache_dir / f"{readable_name}.txt"
            txt_file.write_text(data.get('text', ''))
            
            # Save sections as markdown
            md_file = self.cache_dir / f"{readable_name}.md"
            md_content = self._format_as_markdown(data)
            md_file.write_text(md_content)
            
            logger.info(f"💾 Cached: {ticker} {form_type} {filing_date} (JSON + TXT + MD)")
        except Exception as e:
            logger.error(f"Error saving cache {cache_key}: {e}")
    
    def _format_as_markdown(self, data: Dict[str, Any]) -> str:
        """Format filing data as readable markdown."""
        ticker = data.get('ticker', 'UNKNOWN')
        form_type = data.get('form_type', 'UNKNOWN')
        filing_date = data.get('filing_date', 'unknown')
        filing_url = data.get('filing_url', '')
        sections = data.get('sections', {})
        text = data.get('text', '')
        
        md = f"""# {ticker} - {form_type} Filing
        
**Filing Date:** {filing_date}  
**Source:** [{filing_url}]({filing_url})  
**Cached:** {data.get('cached_at', 'unknown')}

---

"""
        
        # Add sections if they exist
        if sections and len(sections) > 1:
            md += "## Table of Contents\n\n"
            for section_name in sections.keys():
                md += f"- [{section_name.replace('_', ' ').title()}](#{section_name})\n"
            md += "\n---\n\n"
            
            for section_name, section_text in sections.items():
                md += f"## {section_name.replace('_', ' ').title()}\n\n"
                md += f"{section_text}\n\n---\n\n"
        else:
            # No sections, just full text
            md += "## Full Filing Text\n\n"
            md += text
        
        return md
    
    def get_filing_with_cache(self, ticker: str, form_type: str, filing_date: str, filing_url: str) -> Dict[str, Any]:
        """
        Get filing text with caching support.
        
        Args:
            ticker: Stock ticker
            form_type: Form type (10-K, 10-Q)
            filing_date: Filing date (YYYY-MM-DD)
            filing_url: URL to fetch from if not cached
            
        Returns:
            Dict with filing data including text and sections
        """
        cache_key = self._get_cache_key(ticker, form_type, filing_date)
        
        # Try cache first
        cached_data = self._get_cached_filing(cache_key)
        if cached_data:
            return cached_data
        
        # Cache miss - fetch from SEC
        logger.info(f"⬇️  Downloading: {ticker} {form_type} {filing_date}")
        text = self.fetch_filing_text(filing_url)
        sections = self.extract_sections(text, form_type)
        
        # Prepare data to cache
        data = {
            "ticker": ticker,
            "form_type": form_type,
            "filing_date": filing_date,
            "filing_url": filing_url,
            "text": text,
            "sections": sections,
            "cached_at": datetime.now().isoformat()
        }
        
        # Save to cache
        self._save_to_cache(cache_key, data)
        
        return data
