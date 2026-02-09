#!/usr/bin/env python3
"""
Test script to verify SEC filing text extraction is working properly
"""
import sys
sys.path.insert(0, '.')
from app.services.sec_service import SECService
from dotenv import load_dotenv
import os

os.chdir('/Users/taro.serigano/Library/CloudStorage/OneDrive-TMNA/Documents/test-app/backend')
load_dotenv()

sec = SECService()

# Test with the September 2024 10-K we saw in the HTML earlier
test_url = "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/0000320193-24-000123-index.htm"

print("=" * 80)
print("Testing SEC Filing Text Extraction")
print("=" * 80)
print(f"\nFetching from: {test_url}")

text = sec.fetch_filing_text(test_url)

print(f"\nExtracted text length: {len(text):,} characters")
print(f"Word count (approx): {len(text.split()):,}")

# Check for key business content
keywords = {
    "Financial": ["revenue", "sales", "profit", "earnings", "income"],
    "Products": ["iPhone", "iPad", "Mac", "Watch", "AirPods"],
    "Business": ["business", "products", "services", "customers", "market"],
    "Risks": ["risk", "competition", "regulatory", "legal"],
}

print("\n" + "-" * 80)
print("Keyword Analysis:")
print("-" * 80)
for category, words in keywords.items():
    print(f"\n{category}:")
    for word in words:
        count = text.lower().count(word.lower())
        print(f"  {word:15s}: {count:4d} mentions")

# Show sample text
print("\n" + "=" * 80)
print("Sample Text (first 1000 characters):")
print("=" * 80)
print(text[:1000])

# Check for section headers
print("\n" + "=" * 80)
print("Looking for Section Headers:")
print("=" * 80)
section_markers = [
    "Item 1", "Item 1A", "Item 7", "Business", "Risk Factors", 
    "Management's Discussion", "Financial Statements"
]
for marker in section_markers:
    if marker.lower() in text.lower():
        idx = text.lower().find(marker.lower())
        print(f"✓ Found '{marker}' at position {idx:,}")
    else:
        print(f"✗ Not found: '{marker}'")

print("\n" + "=" * 80)
