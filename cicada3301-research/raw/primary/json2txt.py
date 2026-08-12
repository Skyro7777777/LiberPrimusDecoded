#!/usr/bin/env python3
"""Convert page_reader JSON output to clean plain text."""
import json
import sys
import re
from pathlib import Path

def html_to_text(html: str) -> str:
    """Strip HTML tags, decode entities, normalize whitespace, keep main content."""
    # Remove script/style elements entirely
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL|re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL|re.IGNORECASE)
    # Replace <br> with newline
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    # Replace block-level closing tags with newline
    html = re.sub(r'</(p|div|h[1-6]|li|tr|td|th|section|article|header|footer|nav|ul|ol|table)>', '\n', html, flags=re.IGNORECASE)
    # Strip remaining tags
    html = re.sub(r'<[^>]+>', '', html)
    # Decode common HTML entities
    import html as htmllib
    html = htmllib.unescape(html)
    # Normalize whitespace
    html = re.sub(r'[ \t]+', ' ', html)
    html = re.sub(r'\n{3,}', '\n\n', html)
    return html.strip()

def extract_text(json_path: Path) -> str:
    d = json.loads(json_path.read_text())
    data = d.get('data', {})
    title = data.get('title', '')
    url = data.get('url', '')
    desc = data.get('description', '')
    html = data.get('html', '')
    text = html_to_text(html)
    return f"URL: {url}\nTITLE: {title}\nDESCRIPTION: {desc}\n\n{text}\n"

if __name__ == '__main__':
    for path in sys.argv[1:]:
        out = Path(path).with_suffix('.txt')
        try:
            text = extract_text(Path(path))
            out.write_text(text)
            print(f"OK {path} -> {out} ({len(text)} chars)")
        except Exception as e:
            print(f"ERR {path}: {e}")
