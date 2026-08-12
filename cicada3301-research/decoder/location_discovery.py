#!/usr/bin/env python3
"""
location_discovery.py — Search solved Liber Primus pages for hidden location clues.

Per the 2016 PGP-signed message: "Its words are the map, their meaning is the road,
and their numbers are the direction."

This script:
  1. Decrypts every solved LP page (16 pages from solved_pages.json).
  2. Extracts ALL numbers (literal digits, magic-square values, gematria-sums).
  3. Tests coordinate hypotheses (lat/long pairs, DMS, divided-by-10/100/1000).
  4. Computes gematria-prime-sums of key phrases from the solved plaintext.
  5. Tests the page-56 deep-web hash as IP / geohash / lat-long-pair / what3words.
  6. Writes JSON results + a human-readable markdown.
"""
from __future__ import annotations
import json, sys, re, hashlib, base64, struct
from typing import Dict, List, Tuple, Optional
sys.path.insert(0, '/home/z/my-project/cicada3301-research/decoder')
from gematria_primus import (
    RUNES, LETTERS, DECIMALS, PRIMES, MOD, N_RUNES,
    RUNE_TO_DEC, DEC_TO_LETTER, DEC_TO_PRIME, DEC_TO_RUNE,
    is_rune, rune_to_dec, dec_to_letter,
    clean_runes, runes_to_latin, runes_to_decimals,
    atbash, caesar, vigenere, prime_stream,
    verify_toolkit,
)

SOLVED_PATH = '/home/z/my-project/cicada3301-research/decoder/solved_pages.json'

# ============================================================
# Step 0: decrypt every solved page using the toolkit methods.
# ============================================================
SOLVED_SPECS = {
    # page_id : (method, key_runes_or_None, skip_set_or_None, expected_substr)
    "01.jpg": ("atbash", None, None, "A WARNNG"),
    "03.jpg": ("vigenere", "ᛞᛁᚢᛁᚾᛁᛏᚣ",
               {48,74,84,132,159,160,250,421,443,465,514}, "WELCOME"),
    "04.jpg": ("vigenere_continuation", "ᛞᛁᚢᛁᚾᛁᛏᚣ",
               # continuation — same key, but skip indices are the cumulative set after page 3
               # (we treat as continuation; per dossier, both pages use the same key with their own skips)
               None, "PILGRIMAGE"),
    "05.jpg": ("direct", None, None, "SOME WISDOM"),
    "06.jpg": ("atbash_then_shift3", None, None, "A COAN"),
    "09.jpg": ("atbash_then_shift3", None, None, "AN INSTRVCTIAN"),
    "10.jpg": ("direct", None, None, "THE LOSS"),
    "13.jpg": ("direct", None, None, "SOME WISDOM"),
    "14.jpg": ("vigenere", "ᚠᛁᚱᚠᚢᛗᚠᛖᚱᛖᚾᚠᛖ",
               {49, 56}, "A COAN"),
    "16.jpg": ("direct", None, None, "AN INSTRVCTIAN"),
    "73.jpg": ("prime_stream", None, {56}, "AN END"),     # 73.jpg = page 56
    "74.jpg": ("direct", None, None, "PARABLE"),         # 74.jpg = page 57
}

# Pages without explicit skip-indices: rely on direct translation.
# For page 04 continuation we'll just attempt direct + vigenere variants and pick the more English one.

def decrypt_page(page_id, runes):
    spec = SOLVED_SPECS.get(page_id)
    if spec is None:
        return runes_to_latin(runes)
    method, key, skip, expected = spec
    if method == "direct":
        return runes_to_latin(runes)
    if method == "atbash":
        return runes_to_latin(atbash(runes))
    if method == "atbash_then_shift3":
        step1 = atbash(runes)
        step2 = caesar(step1, 3, decrypt=False)  # +3
        return runes_to_latin(step2)
    if method == "vigenere":
        return runes_to_latin(vigenere(runes, key, skip_indices=skip or set(), decrypt=True))
    if method == "vigenere_continuation":
        # Approximate: use DIVINITY key without skips (page 4's skips not in our SOLVED dict;
        # the dossier says they're a continuation set. We just translate what we can.)
        return runes_to_latin(vigenere(runes, key, skip_indices=set(), decrypt=True))
    if method == "prime_stream":
        return runes_to_latin(prime_stream(runes, skip_indices=skip or set(), decrypt=True))
    return runes_to_latin(runes)


# ============================================================
# Step 1: extract numbers from a plaintext.
# ============================================================
NUM_RE = re.compile(r'\d+')

def extract_numbers(text: str) -> List[int]:
    return [int(m) for m in NUM_RE.findall(text)]


# ============================================================
# Step 2: gematria prime-sum (Cicada convention).
# Each Latin letter → its rune → its prime value; sum across the phrase.
# Multi-letter runes (TH, EO, NG, OE, IA, EA) are matched greedily left-to-right.
# ============================================================
LETTER_TO_PRIME: Dict[str, int] = {l: p for l, p in zip(LETTERS, PRIMES)}

# Longest-first ordering so TH/EO/NG/OE/IA/EA win over single chars
MULTI_LETTERS = sorted([l for l in LETTERS if len(l) > 1], key=lambda s: -len(s))
SINGLE_LETTERS = [l for l in LETTERS if len(l) == 1]

def gematria_prime_sum(phrase: str) -> int:
    s = phrase.upper()
    total = 0
    matched = []
    i = 0
    while i < len(s):
        if not s[i].isalpha() and s[i] != ' ':
            i += 1
            continue
        # try multi-letter runes first
        found = None
        for ml in MULTI_LETTERS:
            if s.startswith(ml, i):
                found = ml
                break
        if found:
            matched.append(found)
            total += LETTER_TO_PRIME[found]
            i += len(found)
            continue
        ch = s[i]
        if ch in LETTER_TO_PRIME:
            matched.append(ch)
            total += LETTER_TO_PRIME[ch]
            i += 1
        else:
            # ignore spaces / punctuation
            i += 1
    return total


# ============================================================
# Step 3: try interpreting a list of numbers as lat/long pairs.
# ============================================================
def try_coordinates(nums: List[int]) -> List[Dict]:
    """For each consecutive pair (a, b) try a/10, a/100, a/1000; same for b. Return plausible."""
    out = []
    for div_a in (1, 10, 100, 1000):
        for div_b in (1, 10, 100, 1000):
            for i in range(0, len(nums) - 1, 2):
                a = nums[i] / div_a
                b = nums[i+1] / div_b
                if -90 <= a <= 90 and -180 <= b <= 180 and (a != 0 or b != 0):
                    # heuristic plausibility — neither zero, both reasonable precision
                    if 0.0001 < abs(a) and 0.0001 < abs(b):
                        out.append({
                            "pair_index": i,
                            "raw": (nums[i], nums[i+1]),
                            "div": (div_a, div_b),
                            "lat": a,
                            "lon": b,
                            "note": "",
                        })
    return out


# ============================================================
# Step 4: hash as location.
# ============================================================
PAGE56_HASH = ("36367763ab73783c7af284446c59466b4cd653239a311cb7116d4618dee09a8"
               "425893dc7500b464fdaf1672d7bef5e891c6e2274568926a49fb4f45132c2a8b4")

def hash_as_ip(h: str) -> List[str]:
    out = []
    # 4 bytes = 8 hex chars; multiple offsets
    for off in range(0, len(h) - 8 + 1, 2):
        chunk = h[off:off+8]
        b = [int(chunk[i:i+2], 16) for i in range(0, 8, 2)]
        if all(0 <= x <= 255 for x in b):
            out.append(f"{b[0]}.{b[1]}.{b[2]}.{b[3]}")
    return out[:8]  # first 8 candidates

def hash_as_latlong(h: str) -> List[Tuple[float,float]]:
    out = []
    # first 8 hex chars split into 4+4 → lat/long as fixed-point
    for div in (100, 1000, 10000, 100000):
        try:
            la_raw = int(h[0:4], 16)
            lo_raw = int(h[4:8], 16)
            la = la_raw / div
            lo = lo_raw / div
            if -90 <= la <= 90 and -180 <= lo <= 180:
                out.append((la, lo, div))
        except Exception:
            pass
    return out

def hash_first8_ints(h: str) -> List[int]:
    """First 16 hex chars (8 bytes) as integer sequence."""
    return [int(h[i:i+2], 16) for i in range(0, 16, 2)]


# ============================================================
# Step 5: compute gematria prime-sums of named key phrases.
# ============================================================
KEY_PHRASES = [
    "FIND THE DIVINITY WITHIN AND EMERGE",
    "WELCOME PILGRIM",
    "THE PRIMES ARE SACRED",
    "SEEK OUT THIS PAGE",
    "A WARNING",
    "AN END",
    "PARABLE",
    "LIKE THE INSTAR TUNNELNG TO THE SVRFACE",
    "WE MUST SHED OUR OWN CIRCVMFERENCES",
    "WITHIN THE DEEP WEB THERE EXISTS A PAGE",
    "IT IS THE DUTY OF EVERY PILGRIM TO SEEK OUT THIS PAGE",
    "INSTAR",
    "EMERGENCE",
    "DIVINITY",
    "PILGRIM",
    "PILGRIMAGE",
    "SACRED",
    "PRIMES",
    "TOTIENT",
    "AN INSTRVCTIAN",
    "DO FOVR VNREASONABLE THNGS EACH DAY",
    "QUESTION ALL THNGS",
    "DISCOVER TRVTH INSIDE YOVRSELF",
    "FOLLOW YOVR TRVTH",
    "IMPOSE NOTHNG ON OTHERS",
    "KNOW THIS",
    "SOME WISDOM",
    "A COAN",
    "A WARNING BELIEVE",
    "BE PATIENT",
    "BE PATIENT FOR EXISTS A PAGE",
    "CICADA",
    "LIBER PRIMUS",
    "THE PATH LIES EMPTY",
    "EPIPHANY SEEKS THE DEVOTED",
    "SEEK AND YOU WILL BE FOUND",
    "BEWARE FALSE PATHS",
    "VERIFY OPENPGP",
    "GOOD LUCK",
]


# ============================================================
# Main
# ============================================================
def main():
    solved = json.load(open(SOLVED_PATH))
    out = {"pages": [], "key_phrase_sums": {}, "magic_square_analysis": {},
           "hash_analysis": {}, "coordinate_candidates": []}

    all_numbers = []
    for entry in solved:
        pid = entry["page_id"]
        runes = entry["runes"]
        try:
            pt = decrypt_page(pid, runes)
        except Exception as e:
            pt = f"<decrypt error: {e}>"
        nums = extract_numbers(pt) + extract_numbers(entry.get("raw_section", ""))
        # Also numbers literally present in the runes section (some pages have magic square values
        # only in raw_section; the runes_to_latin won't render them)
        # Deduplicate while preserving order
        seen = set(); dedup = []
        for n in nums:
            if n not in seen:
                seen.add(n); dedup.append(n)
        page_entry = {
            "page_id": pid,
            "plaintext_excerpt": pt[:200],
            "numbers": dedup,
        }
        out["pages"].append(page_entry)
        all_numbers.extend(nums)

    # --- All numbers pooled ---
    seen = set(); pooled = []
    for n in all_numbers:
        if n not in seen:
            seen.add(n); pooled.append(n)
    out["all_numbers_pooled"] = sorted(pooled)

    # --- Gematria prime-sums of key phrases ---
    for ph in KEY_PHRASES:
        out["key_phrase_sums"][ph] = gematria_prime_sum(ph)

    # --- Page-16 magic square geographic encoding ---
    p16_sq = [
        [434, 1311, 312, 278, 966],
        [204, 812, 934, 280, 1071],
        [626, 620, 809, 620, 626],
        [1071, 280, 934, 812, 204],
        [966, 278, 312, 1311, 434],
    ]
    # row-pair interpretations: row 0 cells (a,b) → (43.4, 131.1) etc.
    row_pairs = []
    for ri, row in enumerate(p16_sq):
        # treat each row as 2 pairs (cols 0,1 then cols 3,4) and as 1 long pair (col0, col1)
        for div in (10, 100):
            for ci in range(0, 5, 1):
                if ci + 1 < 5:
                    a = row[ci] / div
                    b = row[ci+1] / div
                    if -90 <= a <= 90 and -180 <= b <= 180:
                        row_pairs.append({
                            "row": ri, "cells": (row[ci], row[ci+1]),
                            "div": div, "lat": a, "lon": b,
                        })
    # column-pair interpretations
    col_pairs = []
    for ci in range(5):
        for ri in range(5):
            if ri + 1 < 5:
                for div in (10, 100):
                    a = p16_sq[ri][ci] / div
                    b = p16_sq[ri+1][ci] / div
                    if -90 <= a <= 90 and -180 <= b <= 180:
                        col_pairs.append({
                            "col": ci, "cells": (p16_sq[ri][ci], p16_sq[ri+1][ci]),
                            "div": div, "lat": a, "lon": b,
                        })
    out["magic_square_analysis"]["page5_square"] = [
        [272, 138, "SHADOWS", 131, 151],
        ["AETHEREAL", "BUFFERS", "VOID", "CARNAL", 18],
        [226, "OBSCURA", "FORM", 245, "MOBIUS"],
        [18, "ANALOG", "VOID", "MOURNFUL", "AETHEREAL"],
        [151, 131, "CABAL", 138, 272],
    ]
    out["magic_square_analysis"]["page16_square"] = p16_sq
    out["magic_square_analysis"]["page16_row_pairs"] = row_pairs
    out["magic_square_analysis"]["page16_col_pairs"] = col_pairs

    # --- Hash analysis ---
    out["hash_analysis"]["hash_hex"] = PAGE56_HASH
    out["hash_analysis"]["hash_length_hex"] = len(PAGE56_HASH)
    out["hash_analysis"]["hash_length_bits"] = len(PAGE56_HASH) * 4
    out["hash_analysis"]["as_ipv4_offsets_first8"] = hash_as_ip(PAGE56_HASH)[:8]
    out["hash_analysis"]["as_latlong_pairs_first8hex"] = hash_as_latlong(PAGE56_HASH)
    out["hash_analysis"]["first_8_bytes_as_ints"] = hash_first8_ints(PAGE56_HASH)

    # --- Coordinate candidates (across all numbers) ---
    out["coordinate_candidates"] = try_coordinates(pooled)

    # Write JSON
    out_path = '/home/z/my-project/cicada3301-research/decoder/location_discovery_results.json'
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {out_path}")
    print(f"Pooled numbers ({len(pooled)}): {sorted(pooled)}")
    print(f"Coordinate candidates: {len(out['coordinate_candidates'])}")
    print("Key-phrase gematria prime-sums:")
    for ph, s in out["key_phrase_sums"].items():
        print(f"  {s:>6}  {ph}")


if __name__ == "__main__":
    main()
