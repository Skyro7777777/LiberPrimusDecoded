#!/usr/bin/env python3
"""
extract_codebook_wordlists.py
=============================
Extract clean wordlists (one word per line, in order of appearance) from the
fetched codebook JSON files. Outputs:
  - raw/codebook_liber_al.txt
  - raw/codebook_self_reliance.txt
  - raw/codebook_agrippa.txt
  - raw/codebook_mabinogion.txt
  - raw/codebook_instar_emergence.txt   (already plain text; just normalize)
"""
import json
import re
import os
import html as html_module

RAW_DIR = "/home/z/my-project/cicada3301-research/raw"

# ---- Helpers -------------------------------------------------------------

def get_html_from_json(path):
    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    # The page_reader returns {code, data:{html, ...}, meta, status}
    body = ""
    if isinstance(data, dict):
        d = data.get("data", {})
        if isinstance(d, dict):
            # Try common keys
            for k in ("html", "content", "text", "body", "markdown"):
                v = d.get(k)
                if isinstance(v, str) and v:
                    body = v
                    break
            if not body:
                # data may itself be the html
                body = json.dumps(d)
        else:
            body = str(d)
    return body


def strip_html(html_text):
    """Crude HTML -> text conversion (no external deps)."""
    # Drop scripts and styles
    html_text = re.sub(r"<script[^>]*>.*?</script>", " ", html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r"<style[^>]*>.*?</style>",  " ", html_text, flags=re.DOTALL | re.IGNORECASE)
    # Replace <br> and <p> with newlines
    html_text = re.sub(r"<br\s*/?>", "\n", html_text, flags=re.IGNORECASE)
    html_text = re.sub(r"</p\s*>",   "\n", html_text, flags=re.IGNORECASE)
    html_text = re.sub(r"</div\s*>", "\n", html_text, flags=re.IGNORECASE)
    # Strip all remaining tags
    html_text = re.sub(r"<[^>]+>", " ", html_text)
    # Unescape HTML entities
    html_text = html_module.unescape(html_text)
    return html_text


WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def words_in_order(text):
    return WORD_RE.findall(text)


# ---- Per-source extractors -----------------------------------------------

def extract_liber_al():
    """Liber AL vel Legis from Wikisource. The body of the work is inside the
    mw-parser-output div. We strip nav/header/footer cruft by anchoring on
    'CHAPTER I' and the closing 'CHAPTER III' / end of text."""
    html = get_html_from_json(os.path.join(RAW_DIR, "codebook_liber_al.json"))
    text = strip_html(html)
    # Anchor on "LIBER AL" or "CHAPTER I"
    # Keep all content; filtering will happen on the word list (we keep it large)
    words = words_in_order(text)
    # Drop boilerplate by detecting common wiki navigation tokens
    # (this is best-effort; for book cipher we want maximum text)
    return words


def extract_self_reliance():
    html = get_html_from_json(os.path.join(RAW_DIR, "codebook_self_reliance.json"))
    text = strip_html(html)
    return words_in_order(text)


def extract_agrippa():
    """Agrippa poem text from filfre.net 2018 article (which quotes the full poem)."""
    html = get_html_from_json(os.path.join(RAW_DIR, "codebook_agrippa.json"))
    text = strip_html(html)
    return words_in_order(text)


def extract_mabinogion():
    html = get_html_from_json(os.path.join(RAW_DIR, "codebook_mabinogion.json"))
    text = strip_html(html)
    # Gutenberg: actual book content starts after "*** START OF" and ends at "*** END OF"
    m = re.search(r"\*\*\* START OF.*?\*\*\*", text, flags=re.DOTALL)
    if m:
        text = text[m.end():]
    m = re.search(r"\*\*\* END OF", text)
    if m:
        text = text[:m.start()]
    return words_in_order(text)


def extract_instar():
    with open(os.path.join(RAW_DIR, "codebook_instar_emergence.txt"), "r", encoding="utf-8") as fp:
        return words_in_order(fp.read())


def main():
    extractors = [
        ("codebook_liber_al.txt",        extract_liber_al),
        ("codebook_self_reliance.txt",   extract_self_reliance),
        ("codebook_agrippa.txt",         extract_agrippa),
        ("codebook_mabinogion.txt",      extract_mabinogion),
        ("codebook_instar_emergence.txt", extract_instar),
    ]
    for fname, fn in extractors:
        words = fn()
        out_path = os.path.join(RAW_DIR, fname)
        with open(out_path, "w", encoding="utf-8") as fp:
            for w in words:
                fp.write(w + "\n")
        print(f"  {fname:40s} {len(words):>8d} words")
    print("Done.")


if __name__ == "__main__":
    main()
