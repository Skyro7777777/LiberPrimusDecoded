#!/usr/bin/env python3
"""
extract_pages.py — Extract all Liber Primus pages as clean rune strings.

Reads /home/z/my-project/cicada3301-research/raw/liber_primus.txt
Writes:
  - /home/z/my-project/cicada3301-research/decoder/solved_pages.json   (9 solved)
  - /home/z/my-project/cicada3301-research/decoder/unsolved_pages.json (56 unsolved)
  - /home/z/my-project/cicada3301-research/decoder/all_pages.json      (75 total)
"""
import re, json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from gematria_primus import RUNES, RUNE_TO_DEC, is_rune, DELIMITERS

LP_TXT = "/home/z/my-project/cicada3301-research/raw/liber_primus.txt"

def parse_liber_primus(text: str):
    """
    Parse the scream314 liber_primus.md plain-text into a list of page records.
    Each page record: {page_id, title, key_hint, runes, has_outguess}
    The markdown structure is:
      ## <title> - <filenames>
      **Key:** <hint>
          <rune block indented 4 spaces>
      Outguess: ...
    Rune blocks are always 4-space-indented lines containing rune characters.
    """
    pages = []
    # Split on page headers (## at start of line)
    sections = re.split(r'\n## ', '\n' + text)
    for section in sections[1:]:
        lines = section.split('\n')
        header = lines[0].strip()
        body = '\n'.join(lines[1:])
        # Extract page id from header (first filename-like token)
        page_id_match = re.search(r'(\d+\.jpg)', header)
        if not page_id_match:
            continue
        primary_id = page_id_match.group(1)
        # Extract Key hint (single line after **Key:**)
        key_match = re.search(r'\*\*Key:\*\*\s*(.+)', body)
        key_hint = key_match.group(1).strip() if key_match else ""
        # Extract ALL 4-space-indented lines that contain rune characters.
        # This catches rune blocks regardless of whether 'Runes:' label is present.
        rune_lines = []
        for line in lines[1:]:
            # 4-space indent (or more) and contains at least one rune
            if re.match(r'^    ', line) and any(is_rune(c) for c in line):
                rune_lines.append(line.strip())
        runes_raw = '\n'.join(rune_lines)
        # Clean: keep only rune characters
        runes_clean = "".join(c for c in runes_raw if is_rune(c))
        # Outguess?
        has_outguess = 'Outguess' in body
        # Determine if this page is solved (has a known key/method) or unsolved
        key_lower = key_hint.lower()
        is_solved = bool(key_hint) and '?' not in key_hint[:10]
        if key_hint.strip() == '?' or key_hint.startswith('?'):
            is_solved = False
        # Pages with default/reversed/shift/vigenere/phi key hints are solved
        solved_keywords = ['substitution', 'shift', 'vigenere', 'divinity', 'firfumferenfe',
                           'phi', 'prime', 'default gematria', 'reversed gematria',
                           'continuation of key', 'forward gematria', 'down forward',
                           'up forward', 'down reversed', 'cleartext', 'written in cleartext']
        if any(kw in key_lower for kw in solved_keywords):
            is_solved = True
        pages.append({
            "page_id": primary_id,
            "header": header,
            "key_hint": key_hint,
            "is_solved": is_solved,
            "runes": runes_clean,
            "n_runes": len(runes_clean),
            "has_outguess": has_outguess,
            "raw_section": section[:500],
        })
    return pages


def main():
    with open(LP_TXT) as f:
        text = f.read()
    pages = parse_liber_primus(text)
    print(f"Parsed {len(pages)} page sections from liber_primus.txt")
    solved = [p for p in pages if p["is_solved"] and p["runes"]]
    unsolved = [p for p in pages if not p["is_solved"] and p["runes"]]
    no_runes = [p for p in pages if not p["runes"]]
    print(f"  Solved (with runes):   {len(solved)}")
    print(f"  Unsolved (with runes): {len(unsolved)}")
    print(f"  No runes (cover/index): {len(no_runes)}")
    print()
    print("=== SOLVED PAGES ===")
    for p in solved:
        print(f"  {p['page_id']:12s}  runes={p['n_runes']:5d}  key={p['key_hint'][:60]}")
    print()
    print("=== UNSOLVED PAGES (first 10) ===")
    for p in unsolved[:10]:
        print(f"  {p['page_id']:12s}  runes={p['n_runes']:5d}  key={p['key_hint'][:40]}  runes[:40]={p['runes'][:40]}")
    print(f"  ... ({len(unsolved)} total)")
    print()
    print("=== NO-RUNES PAGES ===")
    for p in no_runes:
        print(f"  {p['page_id']:12s}  header={p['header'][:50]}")

    # Write outputs
    out_dir = os.path.dirname(__file__)
    with open(os.path.join(out_dir, "all_pages.json"), "w") as f:
        json.dump(pages, f, indent=2, ensure_ascii=False)
    with open(os.path.join(out_dir, "solved_pages.json"), "w") as f:
        json.dump(solved, f, indent=2, ensure_ascii=False)
    with open(os.path.join(out_dir, "unsolved_pages.json"), "w") as f:
        json.dump(unsolved, f, indent=2, ensure_ascii=False)
    print(f"\nWrote all_pages.json, solved_pages.json, unsolved_pages.json to {out_dir}")


if __name__ == "__main__":
    main()
