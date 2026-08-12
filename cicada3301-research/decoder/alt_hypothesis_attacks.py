#!/usr/bin/env python3
"""
alt_hypothesis_attacks.py — Phase C+D attacks on 56 unsolved LP2 pages
=====================================================================
Tests fundamentally different hypotheses that waves 1-5 did not explore:
  A: Per-page different ciphers (9 chapters × 7 methods = 63 tests)
  B: Runes as codebook indices (6 codebooks × 2 modes)
  C: Gematria-sums as the actual message
  D: Non-linear page reading orders (6 orderings)
  E: Page-number-based keys (5 derivations)
  F: Magic-square-cell-based keys
  G: Cross-page chained keys
  H: Delimiter sequence as the message
"""
from __future__ import annotations
import json, os, re, sys
from typing import List, Dict, Tuple, Optional, Iterable
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gematria_primus import (
    RUNES, LETTERS, PRIMES, DECIMALS, N_RUNES, MOD,
    RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, DEC_TO_PRIME,
    is_rune, rune_to_dec, dec_to_rune, dec_to_letter,
    clean_runes, split_pages_by_delimiters, runes_to_decimals, decimals_to_runes,
    decimals_to_latin, runes_to_latin,
    direct_translate, atbash, caesar, vigenere, autokey_vigenere,
    prime_stream, prime_fib_mesh, book_cipher,
    frequency_analysis, english_score,
    KEY_CANDIDATES, _nth_prime, _nth_fib,
)

DECODER_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR     = os.path.join(os.path.dirname(DECODER_DIR), "raw")
COMP_DIR    = os.path.join(os.path.dirname(DECODER_DIR), "compiled")

# ============================================================================
# SECTION 1 — LOAD DATA
# ============================================================================
def load_unsolved_pages():
    with open(os.path.join(DECODER_DIR, "unsolved_pages.json")) as f:
        return json.load(f)

def load_solved_pages():
    with open(os.path.join(DECODER_DIR, "solved_pages.json")) as f:
        return json.load(f)

UNSOLVED = load_unsolved_pages()
SOLVED   = load_solved_pages()

# Index unsolved pages by page_id
UNSOLVED_BY_ID = {p["page_id"]: p for p in UNSOLVED}

# ============================================================================
# SECTION 2 — CHAPTER GROUPINGS (per task spec)
# ============================================================================
# Indices into UNSOLVED list (verified via reading the JSON)
# entry 0: 17.jpg-19.jpg = LP2 pages 0-2 (Cross)        729 runes
# entry 1: 20.jpg         = LP2 page 3 (Spirals part1)   812 runes
# entry 2: 23.jpg-24.jpg  = LP2 pages 6-7 (Spirals part2) 333 runes
# entry 3: 25.jpg-31.jpg  = LP2 pages 8-14 (Branches)    1729 runes
# entry 4: 32.jpg title   = LP2 page 15 (Möbius title)     9 runes
# entry 5: 32-39.jpg      = LP2 pages 15-22 (Möbius)     1894 runes
# entry 6: 40-43.jpg      = LP2 pages 23-26 (Mayfly)     1021 runes
# entry 7: 44-49.jpg      = LP2 pages 27-32 (Wing/Tree)  1433 runes
# entry 8: 50.jpg         = LP2 page 33 (Cuneiform start)  91 runes
# entry 9: 50-56.jpg      = LP2 pages 33-39 (Cuneiform) 1468 runes
# entry 10: 56.jpg        = LP2 page 39 (already counted in entry 9)
# entry 11: 57.jpg        = LP2 pages 40-53 (Spiral/Branches) 3008 runes
# entry 12: 71.jpg        = LP2 page 54 (Hollow)          308 runes
CHAPTERS = [
    ("Cross",          UNSOLVED[0]["runes"]),
    ("Spirals",        UNSOLVED[1]["runes"] + UNSOLVED[2]["runes"]),
    ("Branches",       UNSOLVED[3]["runes"]),
    ("Mobius",         UNSOLVED[5]["runes"]),
    ("Mayfly",         UNSOLVED[6]["runes"]),
    ("Wing_Tree",      UNSOLVED[7]["runes"]),
    ("Cuneiform",      UNSOLVED[9]["runes"]),
    ("Spiral_Branches",UNSOLVED[11]["runes"]),
    ("Hollow",         UNSOLVED[12]["runes"]),
]
print(f"# Loaded {len(CHAPTERS)} chapters:")
for name, runes in CHAPTERS:
    print(f"#   {name:18s} {len(runes):5d} runes")
print(f"# Total: {sum(len(r) for _, r in CHAPTERS)} runes")

# First 200 runes of each chapter (for scoring)
FIRST_200 = {name: runes[:200] for name, runes in CHAPTERS}


# ============================================================================
# SECTION 3 — HYPOTHESIS A: PER-PAGE DIFFERENT CIPHERS (9 × 7 = 63 tests)
# ============================================================================
DIVINITY_KEY = "ᛞᛁᚢᛁᚾᛁᛏᚣ"
FIRFUMFERENFE_KEY = "ᚠᛁᚱᚠᚢᛗᚠᛖᚱᛖᚾᚠᛖ"
PARABLE_KEY = "ᛈᚪᚱᚪᛒᛚᛖ"  # PARABLE
INSTAR_PRIMER = KEY_CANDIDATES["INSTAR"]

def method_atbash(runes):
    return runes_to_latin(atbash(runes))

def method_atbash_shift3(runes):
    # Koan-1: Atbash then +3
    s1 = atbash(runes)
    s2 = caesar(s1, 3, decrypt=False)
    return runes_to_latin(s2)

def method_vigenere_divinity(runes, skip=False):
    # Try with no skip (simpler)
    out = vigenere(runes, DIVINITY_KEY, skip_indices=set() if not skip else None,
                   decrypt=True, f_skip_rule=skip)
    return runes_to_latin(out)

def method_vigenere_firfumferenfe(runes, skip=False):
    out = vigenere(runes, FIRFUMFERENFE_KEY, skip_indices=set() if not skip else None,
                   decrypt=True, f_skip_rule=skip)
    return runes_to_latin(out)

def method_direct(runes):
    return runes_to_latin(runes)

def method_prime_stream(runes):
    return runes_to_latin(prime_stream(runes, decrypt=True))

def method_autokey_divinity(runes, mode="plaintext"):
    return runes_to_latin(autokey_vigenere(runes, DIVINITY_KEY, mode=mode, decrypt=True))

def method_autokey_firfumferenfe(runes, mode="plaintext"):
    return runes_to_latin(autokey_vigenere(runes, FIRFUMFERENFE_KEY, mode=mode, decrypt=True))

def method_autokey_parable(runes, mode="plaintext"):
    return runes_to_latin(autokey_vigenere(runes, PARABLE_KEY, mode=mode, decrypt=True))


METHODS = [
    ("atbash",                    method_atbash),
    ("vigenere_DIVINITY_noskip",  lambda r: method_vigenere_divinity(r, skip=False)),
    ("vigenere_DIVINITY_fskip",   lambda r: method_vigenere_divinity(r, skip=True)),
    ("vigenere_FIRFUMFERENFE_noskip", lambda r: method_vigenere_firfumferenfe(r, skip=False)),
    ("vigenere_FIRFUMFERENFE_fskip",  lambda r: method_vigenere_firfumferenfe(r, skip=True)),
    ("direct_translate",          method_direct),
    ("prime_stream",              method_prime_stream),
    ("atbash_shift3",             method_atbash_shift3),
    ("autokey_DIVINITY_plaintext",   lambda r: method_autokey_divinity(r, "plaintext")),
    ("autokey_DIVINITY_ciphertext",   lambda r: method_autokey_divinity(r, "ciphertext")),
    ("autokey_FIRFUMFERENFE_plaintext",   lambda r: method_autokey_firfumferenfe(r, "plaintext")),
    ("autokey_FIRFUMFERENFE_ciphertext",   lambda r: method_autokey_firfumferenfe(r, "ciphertext")),
    ("autokey_PARABLE_plaintext",   lambda r: method_autokey_parable(r, "plaintext")),
    ("autokey_PARABLE_ciphertext",   lambda r: method_autokey_parable(r, "ciphertext")),
]

def hypothesis_a():
    """63+ tests: 9 chapters × 14 method variants (more than 7 for completeness)."""
    results = []
    for chapter_name, _ in CHAPTERS:
        runes_200 = FIRST_200[chapter_name]
        for method_name, fn in METHODS:
            try:
                pt = fn(runes_200)
                score = english_score(pt)
                results.append({
                    "chapter": chapter_name,
                    "method": method_name,
                    "score": round(score, 2),
                    "snippet": pt[:80],
                })
            except Exception as e:
                results.append({
                    "chapter": chapter_name, "method": method_name,
                    "score": -999, "snippet": f"ERROR: {e}",
                })
    results.sort(key=lambda r: -r["score"])
    return results


# ============================================================================
# SECTION 4 — HYPOTHESIS B: RUNES AS CODEBOOK INDICES
# ============================================================================
def load_codebook(name):
    """Load a codebook text and return list of words."""
    path = os.path.join(RAW_DIR, f"codebook_{name}.txt")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    # Split on whitespace
    words = re.findall(r"[A-Za-z]+", text)
    return words

CODEBOOKS = {}
for name in ["liber_al", "agrippa", "mabinogion", "self_reliance", "instar_emergence"]:
    CODEBOOKS[name] = load_codebook(name)
    print(f"# Codebook {name}: {len(CODEBOOKS[name])} words")

# Also build codebook from solved LP1 pages themselves (concatenated plaintexts)
# Use the solved_pages.json raw text — we'll just use the runes themselves as plaintext.
SOLVED_LP1_RUNES = "".join(p["runes"] for p in SOLVED)
CODEBOOKS["lp1_solved_runes"] = list(SOLVED_LP1_RUNES)  # each rune as a "word"


def codebook_single_index(runes, codebook):
    """Each rune (decimal 0-28) → word[rune_dec] → first letter."""
    out = []
    for r in runes:
        if not is_rune(r): continue
        d = rune_to_dec(r)
        if d < len(codebook):
            word = codebook[d]
            out.append(word[0].upper() if word else "?")
        else:
            out.append("?")
    return "".join(out)


def codebook_pair_index(runes, codebook):
    """Each rune-pair → (r1_dec * 29 + r2_dec) → word at that index → first letter."""
    decs = [rune_to_dec(r) for r in runes if is_rune(r)]
    out = []
    i = 0
    while i + 1 < len(decs):
        idx = decs[i] * 29 + decs[i+1]
        if idx < len(codebook):
            word = codebook[idx]
            out.append(word[0].upper() if word else "?")
        else:
            out.append("?")
        i += 2
    return "".join(out)


def codebook_pair_word_idx_letter_pos(runes, codebook):
    """Each rune-pair → (word_idx=r1_dec, letter_idx=r2_dec) → that letter of word."""
    decs = [rune_to_dec(r) for r in runes if is_rune(r)]
    out = []
    i = 0
    while i + 1 < len(decs):
        w_idx, l_idx = decs[i], decs[i+1]
        if w_idx < len(codebook):
            word = codebook[w_idx]
            if l_idx < len(word):
                out.append(word[l_idx].upper())
            else:
                out.append("?")
        else:
            out.append("?")
        i += 2
    return "".join(out)


def hypothesis_b():
    results = []
    # Use first chapter (Cross) for all codebook tests — most sensitive
    test_runes = FIRST_200["Cross"]
    for cb_name, cb in CODEBOOKS.items():
        for mode_name, fn in [
            ("single_idx_first_letter", codebook_single_index),
            ("pair_idx_first_letter",    codebook_pair_index),
            ("pair_word_idx_letter_pos", codebook_pair_word_idx_letter_pos),
        ]:
            try:
                pt = fn(test_runes, cb)
                score = english_score(pt)
                results.append({
                    "codebook": cb_name,
                    "mode": mode_name,
                    "score": round(score, 2),
                    "snippet": pt[:80],
                })
            except Exception as e:
                results.append({
                    "codebook": cb_name, "mode": mode_name,
                    "score": -999, "snippet": f"ERROR: {e}",
                })
    results.sort(key=lambda r: -r["score"])
    return results


# ============================================================================
# SECTION 5 — HYPOTHESIS C: GEMATRIA-SUMS AS THE MESSAGE
# ============================================================================
def gematria_word_sum(word_runes):
    """Sum the prime values of each rune in a word."""
    return sum(PRIMES[rune_to_dec(r)] for r in word_runes if is_rune(r))

def gematria_word_decimal_sum(word_runes):
    """Sum the decimal values of each rune in a word."""
    return sum(rune_to_dec(r) for r in word_runes if is_rune(r))

def hypothesis_c():
    """For each chapter, compute gematria-sums of first 100 words. Look for patterns."""
    # Use raw_section to properly split into words
    chapter_raw = {
        "Cross":   UNSOLVED[0]["raw_section"],
        "Spirals": UNSOLVED[1]["raw_section"] + "\n" + UNSOLVED[2]["raw_section"],
        "Branches": UNSOLVED[3]["raw_section"],
        "Mobius":   UNSOLVED[5]["raw_section"],
        "Mayfly":   UNSOLVED[6]["raw_section"],
        "Wing_Tree":UNSOLVED[7]["raw_section"],
        "Cuneiform":UNSOLVED[9]["raw_section"],
        "Spiral_Branches": UNSOLVED[11]["raw_section"],
        "Hollow":   UNSOLVED[12]["raw_section"],
    }
    results = []
    for chapter_name, runes in CHAPTERS:
        raw = chapter_raw[chapter_name]
        words = split_pages_by_delimiters(raw)
        # Take first 100 words
        first_words = words[:100]
        sums_prime = [gematria_word_sum(w) for w in first_words]
        sums_dec = [gematria_word_decimal_sum(w) for w in first_words]

        # Analyze patterns
        n = len(sums_prime)
        if n == 0:
            continue

        # Are the sums themselves prime?
        prime_count = sum(1 for s in sums_prime if is_prime(s))
        # Do they factor nicely (small prime factors)?
        small_factor_count = sum(1 for s in sums_prime if has_small_prime_factor(s))

        # Treat sums as ASCII codes (mod 256 or mod 128)
        ascii_mod128 = "".join(chr(s % 128) if 32 <= (s % 128) < 127 else "?" for s in sums_prime)
        ascii_mod256 = "".join(chr(s % 256) if 32 <= (s % 256) < 127 else "?" for s in sums_prime)

        # Compass bearings: pairs of sums as (lat, long)?
        # Take pairs of decimal-sums
        coord_pairs = [(sums_dec[i], sums_dec[i+1]) for i in range(0, len(sums_dec)-1, 2)][:5]

        results.append({
            "chapter": chapter_name,
            "n_words": n,
            "first_5_prime_sums": sums_prime[:5],
            "first_5_decimal_sums": sums_dec[:5],
            "prime_count": prime_count,
            "prime_pct": round(100*prime_count/n, 1),
            "small_factor_count": small_factor_count,
            "ascii_mod128_first_60": ascii_mod128[:60],
            "ascii_mod256_first_60": ascii_mod256[:60],
            "first_5_coord_pairs": coord_pairs,
        })
    return results

def is_prime(n):
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    d = 3
    while d*d <= n:
        if n % d == 0: return False
        d += 2
    return True

def has_small_prime_factor(n, threshold=50):
    """Has at least one prime factor <= threshold."""
    if n < 2: return False
    d = 2
    while d <= threshold and d*d <= n:
        if n % d == 0: return True
        d += 1
    if n > 1 and n <= threshold:
        return True
    return False


# ============================================================================
# SECTION 6 — HYPOTHESIS D: NON-LINEAR PAGE READING ORDERS
# ============================================================================
def order_chapters_by_chapter():
    """All Cross pages, then all Spirals, ... (already the order)."""
    return "".join(r for _, r in CHAPTERS)

def order_reverse():
    return "".join(r for _, r in reversed(CHAPTERS))

def order_chapter_then_within():
    """Read each chapter group's full content sequentially (same as normal)."""
    return order_chapters_by_chapter()

def order_fibonacci():
    """Pages 1, 2, 3, 5, 8, 13, 21, 34, 55, ... — but we have chapters, not pages.
    Approximate by taking chapter indices from Fibonacci-like pattern."""
    # Use the Fibonacci page indices and select chapters
    # Pages 1, 2, 3, 5, 8, 13, 21, 34, 55 mapped to chapters by simple lookup
    # Since we have only 9 chapters, we'll order by [0, 1, 1, 2, 3, 5, 8, ...]
    # Simpler: order chapters by their ordinal position taken at Fibonacci offsets
    order = [0, 1, 1, 2, 3, 5, 8, 0, 0]  # cycle through
    seen = set()
    result = []
    for idx in order:
        if idx < len(CHAPTERS):
            name, runes = CHAPTERS[idx]
            if name not in seen:
                result.append(runes)
                seen.add(name)
    # Append any remaining
    for name, runes in CHAPTERS:
        if name not in seen:
            result.append(runes)
            seen.add(name)
    return "".join(result)

def order_prime():
    """Pages 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, ..."""
    # Same idea — approximate by reordering chapters using prime page indices
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    seen = set()
    result = []
    for p in primes:
        idx = p % len(CHAPTERS)
        name, runes = CHAPTERS[idx]
        if name not in seen:
            result.append(runes)
            seen.add(name)
    for name, runes in CHAPTERS:
        if name not in seen:
            result.append(runes)
            seen.add(name)
    return "".join(result)

def order_smallest_first():
    """Sort chapters by length (smallest first)."""
    sorted_chapters = sorted(CHAPTERS, key=lambda x: len(x[1]))
    return "".join(r for _, r in sorted_chapters)

def order_largest_first():
    """Sort chapters by length (largest first)."""
    sorted_chapters = sorted(CHAPTERS, key=lambda x: -len(x[1]))
    return "".join(r for _, r in sorted_chapters)


def hypothesis_d():
    """Test 6+ orderings with autokey DIVINITY + parable, score first 300 runes."""
    orderings = [
        ("normal_chapter_order", order_chapters_by_chapter()),
        ("reverse",              order_reverse()),
        ("fibonacci",           order_fibonacci()),
        ("prime",               order_prime()),
        ("smallest_first",      order_smallest_first()),
        ("largest_first",       order_largest_first()),
    ]
    results = []
    parable_full = "ᛈᚪᚱᚪᛒᛚᛖᛚᛁᚳᛖᚦᛖᛁᚾᛋᛏᚪᚱᛏᚢᚾᚾᛖᛚᛝᛏᚩᚦᛖᛋᚢᚱᚠᚪᚳᛖᚹᛖᛗᚢᛋᛏᛋᛖᛞᚩᚢᚱᚩᚹᚾᚳᛁᚱᚳᚢᛗᚠᛖᚱᛖᚾᚳᛖᛋᚠᛁᚾᛞᚦᛖᛞᛁᚢᛁᚾᛁᛏᚣᚹᛁᚦᛁᚾᚪᚾᛞᛖᛗᛖᚱᚷᛖ"
    # ^ PARABLE LIKE THE INSTAR TUNNELING TO THE SURFACE WE MUST SHED OUR OWN CIRCUMFERENCES FIND THE DIVINITY WITHIN AND EMERGE
    for ord_name, ord_runes in orderings:
        first_300 = ord_runes[:300]
        # Test direct, atbash, vigenere DIVINITY, vigenere parable_full, autokey DIVINITY pt+ct, autokey parable pt+ct, prime_stream
        for cipher_name, fn in [
            ("direct", lambda r: runes_to_latin(r)),
            ("atbash", lambda r: runes_to_latin(atbash(r))),
            ("vigenere_DIVINITY", lambda r: runes_to_latin(vigenere(r, DIVINITY_KEY, decrypt=True))),
            ("vigenere_parable", lambda r: runes_to_latin(vigenere(r, parable_full, decrypt=True))),
            ("autokey_DIVINITY_pt", lambda r: runes_to_latin(autokey_vigenere(r, DIVINITY_KEY, mode="plaintext", decrypt=True))),
            ("autokey_DIVINITY_ct", lambda r: runes_to_latin(autokey_vigenere(r, DIVINITY_KEY, mode="ciphertext", decrypt=True))),
            ("autokey_parable_pt", lambda r: runes_to_latin(autokey_vigenere(r, parable_full, mode="plaintext", decrypt=True))),
            ("autokey_parable_ct", lambda r: runes_to_latin(autokey_vigenere(r, parable_full, mode="ciphertext", decrypt=True))),
            ("prime_stream", lambda r: runes_to_latin(prime_stream(r, decrypt=True))),
        ]:
            try:
                pt = fn(first_300)
                score = english_score(pt)
                results.append({
                    "ordering": ord_name,
                    "cipher": cipher_name,
                    "score": round(score, 2),
                    "snippet": pt[:60],
                })
            except Exception as e:
                results.append({
                    "ordering": ord_name, "cipher": cipher_name,
                    "score": -999, "snippet": f"ERROR: {e}",
                })
    results.sort(key=lambda r: -r["score"])
    return results


# ============================================================================
# SECTION 7 — HYPOTHESIS E: PAGE-NUMBER-BASED KEYS
# ============================================================================
def primer_page_digits(page_num):
    """Decimal digits of page number → runes."""
    digits = [int(c) for c in str(page_num)]
    return decimals_to_runes(digits)

def primer_nth_prime(page_num):
    """Nth prime (1-indexed) where N=page_num. e.g. page 5 → 11 → runes of "11"."""
    p = _nth_prime(page_num)
    digits = [int(c) for c in str(p)]
    return decimals_to_runes(digits)

def primer_nth_fib(page_num):
    """Nth Fibonacci number where N=page_num."""
    f = _nth_fib(page_num)
    digits = [int(c) for c in str(f)]
    return decimals_to_runes(digits)

def primer_page_repeated(page_num, length=20):
    """Page number repeated to fill a key of `length` runes."""
    s = str(page_num)
    out = []
    while len(out) < length:
        for c in s:
            out.append(int(c))
            if len(out) >= length: break
    return decimals_to_runes(out)

def primer_page_base29(page_num):
    """Page number in base-29 → runes."""
    n = page_num
    if n == 0:
        return DEC_TO_RUNE[0]
    digits = []
    while n > 0:
        digits.insert(0, n % 29)
        n //= 29
    return decimals_to_runes(digits)


def hypothesis_e():
    """Test 5 page-number-based primer derivations on first 200 runes of each chapter."""
    derivations = [
        ("page_digits", primer_page_digits),
        ("nth_prime",   primer_nth_prime),
        ("nth_fib",     primer_nth_fib),
        ("page_repeated_20", lambda p: primer_page_repeated(p, 20)),
        ("page_base29", primer_page_base29),
    ]
    # Page numbers (LP2 numbering 0..55, one per chapter representative)
    chapter_pages = {
        "Cross": 0, "Spirals": 3, "Branches": 8, "Mobius": 15, "Mayfly": 23,
        "Wing_Tree": 27, "Cuneiform": 33, "Spiral_Branches": 40, "Hollow": 54,
    }
    results = []
    for chapter_name, page_num in chapter_pages.items():
        runes_200 = FIRST_200[chapter_name]
        for deriv_name, fn in derivations:
            try:
                primer = fn(page_num)
                # Test as vigenere primer (no skip)
                pt = runes_to_latin(vigenere(runes_200, primer, decrypt=True))
                score = english_score(pt)
                results.append({
                    "chapter": chapter_name,
                    "page_num": page_num,
                    "derivation": deriv_name,
                    "primer": primer[:30],
                    "cipher": "vigenere_noskip",
                    "score": round(score, 2),
                    "snippet": pt[:60],
                })
                # Also test as autokey primer (plaintext mode)
                pt2 = runes_to_latin(autokey_vigenere(runes_200, primer, mode="plaintext", decrypt=True))
                score2 = english_score(pt2)
                results.append({
                    "chapter": chapter_name,
                    "page_num": page_num,
                    "derivation": deriv_name,
                    "primer": primer[:30],
                    "cipher": "autokey_plaintext",
                    "score": round(score2, 2),
                    "snippet": pt2[:60],
                })
            except Exception as e:
                results.append({
                    "chapter": chapter_name, "page_num": page_num,
                    "derivation": deriv_name, "cipher": "ERROR",
                    "score": -999, "snippet": str(e)[:80],
                })
    results.sort(key=lambda r: -r["score"])
    return results


# ============================================================================
# SECTION 8 — HYPOTHESIS F: MAGIC-SQUARE-CELL-BASED KEYS
# ============================================================================
# Page 5 magic square (sums to 1033):
#   272 138 SHADOWS 131 151
#   AETHEREAL BUFFERS VOID CARNAL 18
#   226 OBSCURA FORM 245 MOBIUS
#   18 ANALOG VOID MOURNFUL AETHEREAL
#   151 131 CABAL 138 272
# Numerical values only (replace runes with their decimal sums):
PAGE5_SQUARE = [
    [272, 138, None, 131, 151],   # SHADOWS = ?
    [None, None, None, None, 18], # AETHEREAL BUFFERS VOID CARNAL
    [226, None, None, 245, None], # OBSCURA FORM MOBIUS
    [18, None, None, None, None], # ANALOG VOID MOURNFUL AETHEREAL
    [151, 131, None, 138, 272],
]
# Compute missing entries: each row/col/diag must sum to 1033
# Row 0: 272+138+x+131+151 = 1033 → x = 341
# Row 1: x+x+x+x+18 = 1033 → 4x = 1015 → not integer, so magic square has mixed values
# This is the LP1 page-5 "magic square" — use the visible numbers only:
PAGE5_VALUES = [272, 138, 131, 151, 18, 226, 245, 18, 151, 131, 138, 272]
# Page 16 magic square (sums to 5485 = 5 × 1097, or 5×55×19... actually 1033 × 5.31 not integer):
# 434 1311 312 278 966  → sum = 3301 (oh! 434+1311+312+278+966 = 3301, the Cicada number!)
# 204 812 934 280 1071  → 3301
# 626 620 809 620 626  → 3301
# 1071 280 934 812 204  → 3301
# 966 278 312 1311 434  → 3301
# Total = 16505 = 5 × 3301
PAGE16_SQUARE = [
    [434, 1311, 312, 278, 966],
    [204, 812, 934, 280, 1071],
    [626, 620, 809, 620, 626],
    [1071, 280, 934, 812, 204],
    [966, 278, 312, 1311, 434],
]

def page16_cell_value(idx):
    """Cell (row, col) for index 0..24, wrapping for >=25."""
    idx = idx % 25
    return PAGE16_SQUARE[idx // 5][idx % 5]

def page5_cell_value(idx):
    """Use PAGE5_VALUES list (cyclic) — only 12 known values."""
    return PAGE5_VALUES[idx % len(PAGE5_VALUES)]

def primer_page16_square(page_num, length=20):
    """Use page-N mod 25 → cell → decimal digits → runes."""
    out = []
    for i in range(length):
        v = page16_cell_value(page_num + i)
        for c in str(v):
            out.append(int(c))
            if len(out) >= length: break
        if len(out) >= length: break
    return decimals_to_runes(out[:length])

def primer_page5_square(page_num, length=20):
    out = []
    for i in range(length):
        v = page5_cell_value(page_num + i)
        for c in str(v):
            out.append(int(c))
            if len(out) >= length: break
        if len(out) >= length: break
    return decimals_to_runes(out[:length])

def primer_page16_mod29(page_num, length=20):
    """Use square cell value mod 29 as rune decimals directly."""
    out = []
    for i in range(length):
        v = page16_cell_value(page_num + i) % 29
        out.append(v)
    return decimals_to_runes(out)


def hypothesis_f():
    """Magic-square-cell-based keys for each chapter."""
    chapter_pages = {
        "Cross": 0, "Spirals": 3, "Branches": 8, "Mobius": 15, "Mayfly": 23,
        "Wing_Tree": 27, "Cuneiform": 33, "Spiral_Branches": 40, "Hollow": 54,
    }
    derivations = [
        ("page16_digits",  primer_page16_square),
        ("page5_digits",   primer_page5_square),
        ("page16_mod29",   primer_page16_mod29),
    ]
    results = []
    for chapter_name, page_num in chapter_pages.items():
        runes_200 = FIRST_200[chapter_name]
        for deriv_name, fn in derivations:
            try:
                primer = fn(page_num)
                pt = runes_to_latin(vigenere(runes_200, primer, decrypt=True))
                score = english_score(pt)
                results.append({
                    "chapter": chapter_name, "page_num": page_num,
                    "derivation": deriv_name, "primer": primer[:30],
                    "cipher": "vigenere_noskip",
                    "score": round(score, 2),
                    "snippet": pt[:60],
                })
                pt2 = runes_to_latin(autokey_vigenere(runes_200, primer, mode="plaintext", decrypt=True))
                score2 = english_score(pt2)
                results.append({
                    "chapter": chapter_name, "page_num": page_num,
                    "derivation": deriv_name, "primer": primer[:30],
                    "cipher": "autokey_plaintext",
                    "score": round(score2, 2),
                    "snippet": pt2[:60],
                })
            except Exception as e:
                results.append({
                    "chapter": chapter_name, "page_num": page_num,
                    "derivation": deriv_name, "cipher": "ERROR",
                    "score": -999, "snippet": str(e)[:80],
                })
    results.sort(key=lambda r: -r["score"])
    return results


# ============================================================================
# SECTION 9 — HYPOTHESIS G: CROSS-PAGE CHAINED KEYS
# ============================================================================
def hypothesis_g():
    """
    Page N's plaintext becomes page N+1's key.
    Test various initial primers for chapter 0 (Cross).
    """
    # We test on chapter-level (not page-level) since we have 9 chapters concatenated
    # as if they were "pages". Use first 200 runes of each chapter in sequence.
    # For simplicity, we just test the FIRST chapter with various primers, then chain.
    # In practice, we'd need to test the full chain but it's expensive.
    # Implement: primer → decrypt chapter 0 → use first 100 runes of result as primer for chapter 1, etc.
    primers = [
        ("DIVINITY", DIVINITY_KEY),
        ("FIRFUMFERENFE", FIRFUMFERENFE_KEY),
        ("PARABLE", PARABLE_KEY),
        ("INSTAR", INSTAR_PRIMER),
    ]
    results = []
    for primer_name, primer_runes in primers:
        try:
            # Decrypt chapter 0 with this primer (autokey plaintext mode)
            ch0_runes = CHAPTERS[0][1][:200]
            ch0_pt_runes = autokey_vigenere(ch0_runes, primer_runes, mode="plaintext", decrypt=True)
            # Use first 50 of ch0_pt as primer for ch1
            new_primer = ch0_pt_runes[:50]
            ch1_runes = CHAPTERS[1][1][:200]
            ch1_pt_runes = autokey_vigenere(ch1_runes, new_primer, mode="plaintext", decrypt=True)
            pt = runes_to_latin(ch1_pt_runes)
            score = english_score(pt)
            results.append({
                "primer0": primer_name,
                "method": "autokey_plaintext_chain",
                "score": round(score, 2),
                "snippet": pt[:80],
            })
            # Also try vigenere (no autokey) with the chained primer
            ch1_pt_v = vigenere(ch1_runes, new_primer, decrypt=True)
            pt_v = runes_to_latin(ch1_pt_v)
            score_v = english_score(pt_v)
            results.append({
                "primer0": primer_name,
                "method": "vigenere_chain",
                "score": round(score_v, 2),
                "snippet": pt_v[:80],
            })
        except Exception as e:
            results.append({
                "primer0": primer_name, "method": "ERROR",
                "score": -999, "snippet": str(e)[:80],
            })
    results.sort(key=lambda r: -r["score"])
    return results


# ============================================================================
# SECTION 10 — HYPOTHESIS H: DELIMITERS AS THE MESSAGE
# ============================================================================
def extract_delimiters(raw_text):
    """Extract the sequence of delimiter chars from raw text (excluding whitespace)."""
    delims = []
    for ch in raw_text:
        if not is_rune(ch) and ch not in " \n\t" and ch in "/•·.-_=*%&$#":
            delims.append(ch)
    return delims

def hypothesis_h():
    """Extract delimiter sequences from each chapter's raw text. Try mappings."""
    # Pull raw text for each chapter
    chapter_raw = {
        "Cross":   UNSOLVED[0]["raw_section"],
        "Spirals": UNSOLVED[1]["raw_section"] + "\n" + UNSOLVED[2]["raw_section"],
        "Branches": UNSOLVED[3]["raw_section"],
        "Mobius":   UNSOLVED[5]["raw_section"],
        "Mayfly":   UNSOLVED[6]["raw_section"],
        "Wing_Tree":UNSOLVED[7]["raw_section"],
        "Cuneiform":UNSOLVED[9]["raw_section"],
        "Spiral_Branches": UNSOLVED[11]["raw_section"],
        "Hollow":   UNSOLVED[12]["raw_section"],
    }
    results = []
    # Define a few mappings
    DELIM_CHARS = "/•·.-_=*%&$#"
    mappings = [
        ("ordinal_0_to_11", {c: i for i, c in enumerate(DELIM_CHARS)}),
        ("ordinal_mod10",   {c: i % 10 for i, c in enumerate(DELIM_CHARS)}),
        ("mod29_rune",      {c: i % 29 for i, c in enumerate(DELIM_CHARS)}),  # treat as rune decimals
        ("plus_65_to_letter", {c: chr(65 + i) for i, c in enumerate(DELIM_CHARS)}),  # A,B,C,...
        ("plus_32_printable", {c: chr(32 + i) for i, c in enumerate(DELIM_CHARS)}),  # space, !, "...
        ("raw_byte_direct", {c: ord(c) for c in DELIM_CHARS}),  # actual unicode codepoint
    ]
    for chapter_name, raw in chapter_raw.items():
        delims = extract_delimiters(raw)
        if not delims:
            results.append({
                "chapter": chapter_name,
                "n_delims": 0,
                "note": "no delimiters in raw text",
            })
            continue
        for map_name, mapping in mappings:
            if map_name == "plus_65_to_letter" or map_name == "plus_32_printable":
                ascii_str = "".join(mapping.get(d, "?") for d in delims)
            elif map_name == "raw_byte_direct":
                vals = [mapping.get(d, 0) for d in delims]
                ascii_str = "".join(chr(v) if 32 <= v < 127 else "?" for v in vals)
            else:
                vals = [mapping.get(d, -1) for d in delims]
                # Treat as ASCII mod 128
                ascii_str = "".join(chr(v % 128) if 32 <= (v % 128) < 127 else "?" for v in vals)
            # Score — most ASCII text would be readable if delimiters ARE the message
            score = english_score(ascii_str)
            results.append({
                "chapter": chapter_name,
                "n_delims": len(delims),
                "mapping": map_name,
                "score": round(score, 2),
                "first_30_vals": [mapping.get(d, -1) for d in delims[:30]] if map_name not in ("plus_65_to_letter", "plus_32_printable") else None,
                "first_60_ascii": ascii_str[:60],
                "first_10_delims": "".join(delims[:10]),
            })
    results.sort(key=lambda r: -r.get("score", -999))
    return results


# ============================================================================
# SECTION 11 — RUN ALL
# ============================================================================
def main():
    print("\n" + "="*70)
    print("ALT-HYPOTHESIS ATTACKS — Phase C+D")
    print("="*70)

    all_results = {}

    print("\n[Hypothesis A] Per-page different ciphers (9 chapters × 14 methods = 126 tests)")
    hA = hypothesis_a()
    all_results["A"] = hA
    print(f"  Ran {len(hA)} tests. Top 10:")
    for r in hA[:10]:
        print(f"    {r['score']:7.2f}  {r['chapter']:18s} {r['method']:30s}  {r['snippet'][:40]}")

    print("\n[Hypothesis B] Runes as codebook indices (5 codebooks × 3 modes = 15 tests)")
    hB = hypothesis_b()
    all_results["B"] = hB
    print(f"  Ran {len(hB)} tests. Top 10:")
    for r in hB[:10]:
        print(f"    {r['score']:7.2f}  {r['codebook']:25s} {r['mode']:30s}  {r['snippet'][:40]}")

    print("\n[Hypothesis C] Gematria-sums as the message")
    hC = hypothesis_c()
    all_results["C"] = hC
    for r in hC:
        print(f"  {r['chapter']:18s} sums[prime]={r['first_5_prime_sums']} dec={r['first_5_decimal_sums']} primes={r['prime_pct']}%")

    print("\n[Hypothesis D] Non-linear reading orders (6 × 9 = 54 tests)")
    hD = hypothesis_d()
    all_results["D"] = hD
    print(f"  Ran {len(hD)} tests. Top 10:")
    for r in hD[:10]:
        print(f"    {r['score']:7.2f}  {r['ordering']:18s} {r['cipher']:30s}  {r['snippet'][:40]}")

    print("\n[Hypothesis E] Page-number-based keys (9 × 5 × 2 = 90 tests)")
    hE = hypothesis_e()
    all_results["E"] = hE
    print(f"  Ran {len(hE)} tests. Top 10:")
    for r in hE[:10]:
        print(f"    {r['score']:7.2f}  {r['chapter']:18s} {r['derivation']:25s} {r['cipher']:18s}  {r['snippet'][:40]}")

    print("\n[Hypothesis F] Magic-square-cell keys (9 × 3 × 2 = 54 tests)")
    hF = hypothesis_f()
    all_results["F"] = hF
    print(f"  Ran {len(hF)} tests. Top 10:")
    for r in hF[:10]:
        print(f"    {r['score']:7.2f}  {r['chapter']:18s} {r['derivation']:18s} {r['cipher']:18s}  {r['snippet'][:40]}")

    print("\n[Hypothesis G] Cross-page chained keys")
    hG = hypothesis_g()
    all_results["G"] = hG
    for r in hG:
        print(f"    {r['score']:7.2f}  primer={r['primer0']:14s} method={r['method']:25s}  {r['snippet'][:40]}")

    print("\n[Hypothesis H] Delimiters as message")
    hH = hypothesis_h()
    all_results["H"] = hH
    for r in hH[:10]:
        if r.get("n_delims", 0) > 0:
            print(f"  {r['chapter']:18s} n={r['n_delims']:4d}  {r['mapping']:18s} score={r['score']:6.2f}  ascii={r['first_60_ascii'][:40]}")
        else:
            print(f"  {r['chapter']:18s}  {r.get('note','')}")

    # Save JSON
    out_path = os.path.join(DECODER_DIR, "alt_hypothesis_results.json")
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    # Compute total tests
    total_tests = (len(hA) + len(hB) + len(hC) + len(hD) + len(hE) + len(hF) + len(hG) + len(hH))
    print(f"\nTotal tests run: {total_tests}")
    return all_results


if __name__ == "__main__":
    main()
