#!/usr/bin/env python3
"""
magicsquare_deeptest.py — Magic-Square Deep Dive + Cross-Page Chain
====================================================================
Task ID: p6b
Subagent: Magic-square deep dive + cross-page chained-key schedules

Part A — 14 magic-square derivations × 9 chapters × 3 cipher modes = 378 tests
Part B — Cross-page chained-key schedules (chain types A, B, C, D)
Part C — Prime-index recurrence reconstruction
Part D — Hill-cipher 5x5 tests
"""
from __future__ import annotations
import json, os, sys, time, math
from typing import List, Dict, Tuple, Optional, Iterable
from collections import Counter
import itertools

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
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

# ============================================================================
# DATA LOAD
# ============================================================================
def load_unsolved_pages():
    with open(os.path.join(HERE, "unsolved_pages.json")) as f:
        return json.load(f)
def load_solved_pages():
    with open(os.path.join(HERE, "solved_pages.json")) as f:
        return json.load(f)

UNSOLVED = load_unsolved_pages()
SOLVED   = load_solved_pages()

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
CHAPTER_NAMES = [c[0] for c in CHAPTERS]
FIRST_200 = {name: runes[:200] for name, runes in CHAPTERS}
FIRST_300 = {name: runes[:300] for name, runes in CHAPTERS}

# ============================================================================
# MAGIC SQUARES (VERIFIED VALUES — see verify_zeckendorf.py)
# ============================================================================
# Page 5 magic square (magic constant = 1033, prime):
# Reconstructed rune-word values from CicadaSolvers' gematria-prime-sum computation.
PAGE5_SQUARE = [
    [272, 138, 341, 131, 151],
    [366, 199, 130, 320,  18],
    [226, 245,  91, 245, 226],
    [ 18, 320, 130, 199, 366],
    [151, 131, 341, 138, 272],
]
# Page 16 magic square (magic constant = 3301 = Cicada's number, prime):
PAGE16_SQUARE = [
    [434, 1311, 312, 278, 966],
    [204, 812, 934, 280, 1071],
    [626, 620, 809, 620, 626],
    [1071, 280, 934, 812, 204],
    [966, 278, 312, 1311, 434],
]

# ============================================================================
# PRIME + FIB HELPERS (needed for Part C)
# ============================================================================
def is_prime(n: int) -> bool:
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    d = 3
    while d * d <= n:
        if n % d == 0: return False
        d += 2
    return True

def nth_prime(n: int) -> int:
    if n < 1: raise ValueError
    primes = []
    c = 2
    while len(primes) < n:
        if is_prime(c): primes.append(c)
        c += 1 if c == 2 else 2
    return primes[-1]

def prime_index_of(value: int) -> int:
    if not is_prime(value): return -1
    primes = []
    c = 2
    while True:
        if is_prime(c):
            primes.append(c)
            if c == value: return len(primes)
            if c > value: return -1
        c += 1 if c == 2 else 2

def fibs_up_to(n: int) -> List[int]:
    out = [1, 2]
    while out[-1] + out[-2] <= n:
        out.append(out[-1] + out[-2])
    return out

def fib_at(n: int) -> int:
    if n < 1: raise ValueError
    a, b = 1, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return a

def zeckendorf(n: int) -> List[int]:
    """Greedy non-consecutive Fibonacci decomposition."""
    if n <= 0: return []
    parts = []
    fibs = fibs_up_to(n)
    for f in reversed(fibs):
        if f <= n:
            parts.append(f)
            n -= f
    return parts

def fib_index(f_val: int) -> int:
    """Return Fibonacci index (1-based, F(1)=1, F(2)=1, F(3)=2, ...) of f_val or -1."""
    if f_val < 1: return -1
    a, b = 1, 1
    idx = 1
    while a <= f_val:
        if a == f_val: return idx
        a, b = b, a + b
        idx += 1
    return -1

# ============================================================================
# PART A — 14 MAGIC-SQUARE DERIVATIONS
# ============================================================================
def flatten_row_major(sq): return [v for row in sq for v in row]
def flatten_col_major(sq): return [sq[r][c] for c in range(5) for r in range(5)]

def flatten_spiral_inward(sq):
    """Start top-left, go right, down, left, up, etc."""
    out = []
    rows = [list(r) for r in sq]
    while rows:
        out.extend(rows.pop(0))           # top row left→right
        if rows and rows[0]:
            for r in rows:
                out.append(r.pop())       # right column top→bottom
        if rows:
            out.extend(rows.pop()[::-1])  # bottom row right→left
        if rows and rows[0]:
            for r in reversed(rows):
                if r:
                    out.append(r.pop(0))  # left column bottom→top
    return out

def flatten_spiral_outward(sq):
    """Spiral outward from center."""
    inward = flatten_spiral_inward(sq)
    return inward[::-1]

def flatten_main_diag(sq): return [sq[i][i] for i in range(5)]
def flatten_anti_diag(sq): return [sq[i][4-i] for i in range(5)]

def digits_of(v): return [int(c) for c in str(v)]
def digits_of_rev(v):
    d = digits_of(v)
    d.reverse()
    return d

def zeckendorf_indices(v):
    """Zeckendorf decomposition of v → list of Fibonacci indices (1-based)."""
    parts = zeckendorf(v)
    return [fib_index(p) for p in parts]

# XOR with row/col index (i*5+j)
def xor_with_pos(sq):
    out = []
    for i in range(5):
        for j in range(5):
            out.append(sq[i][j] ^ (i*5+j))
    return out
# Cell minus position mod 29
def minus_pos_mod29(sq):
    out = []
    for i in range(5):
        for j in range(5):
            out.append((sq[i][j] - (i*5+j)) % 29)
    return out
# Difference page16 - page5
def diff_squares(sq_a, sq_b):
    return [sq_a[i][j] - sq_b[i][j] for i in range(5) for j in range(5)]
# Product mod 29
def prod_mod29(sq_a, sq_b):
    return [(sq_a[i][j] * sq_b[i][j]) % 29 for i in range(5) for j in range(5)]

def to_runes(decs):
    return "".join(dec_to_rune(d % MOD) for d in decs)

def to_rune_digits(decs):
    """For each value, emit its decimal digits as runes (longer stream)."""
    out = []
    for v in decs:
        out.extend(digits_of(v))
    return "".join(dec_to_rune(d % MOD) for d in out)

def to_rune_digits_rev(decs):
    out = []
    for v in decs:
        d = digits_of(v)
        d.reverse()
        out.extend(d)
    return "".join(dec_to_rune(d % MOD) for d in out)

def to_rune_zeck_idx(decs):
    """Each value → its Zeckendorf Fib indices → as runes."""
    out = []
    for v in decs:
        for idx in zeckendorf_indices(v):
            out.append(idx % MOD)
    return "".join(dec_to_rune(d) for d in out)

# Build all 14 derivations as a list of (name, primer_runes_factory)
# Factory takes (square_choice) and returns a primer-rune string of >=20 runes (repeated if needed)
def build_derivations(square_choice):
    """square_choice: 'page5' or 'page16' (or 'both' for cross-square). Returns list of (name, primer_fn)."""
    sq = PAGE5_SQUARE if square_choice == "page5" else PAGE16_SQUARE
    sq_other = PAGE16_SQUARE if square_choice == "page5" else PAGE5_SQUARE
    derivs = []
    # 1. row-major mod 29
    derivs.append(("01_row_mod29", to_runes([v % 29 for v in flatten_row_major(sq)])))
    # 2. col-major mod 29
    derivs.append(("02_col_mod29", to_runes([v % 29 for v in flatten_col_major(sq)])))
    # 3. spiral-inward mod 29
    derivs.append(("03_spiral_in_mod29", to_runes([v % 29 for v in flatten_spiral_inward(sq)])))
    # 4. spiral-outward mod 29
    derivs.append(("04_spiral_out_mod29", to_runes([v % 29 for v in flatten_spiral_outward(sq)])))
    # 5a. main diagonal mod 29
    derivs.append(("05a_main_diag_mod29", to_runes([v % 29 for v in flatten_main_diag(sq)])))
    # 5b. anti-diagonal mod 29
    derivs.append(("05b_anti_diag_mod29", to_runes([v % 29 for v in flatten_anti_diag(sq)])))
    # 6. cell values as decimal digits → runes (75 runes per square)
    derivs.append(("06_decimal_digits", to_rune_digits(flatten_row_major(sq))))
    # 7. decimal digits reversed per cell
    derivs.append(("07_decimal_digits_rev", to_rune_digits_rev(flatten_row_major(sq))))
    # 8. cell values mod 29, repeated to fill 100 runes
    base = [v % 29 for v in flatten_row_major(sq)]
    derivs.append(("08_mod29_rep100", to_runes((base * 5)[:100])))
    # 9. Zeckendorf decomposition indices as runes
    derivs.append(("09_zeck_indices", to_rune_zeck_idx(flatten_row_major(sq))))
    # 10. XOR with position
    derivs.append(("10_xor_pos", to_runes([v % 29 for v in xor_with_pos(sq)])))
    # 11. cell minus position mod 29
    derivs.append(("11_minus_pos_mod29", to_runes(minus_pos_mod29(sq))))
    # 12. difference page16 - page5 (cross-square)
    derivs.append(("12_diff_squares", to_runes([v % 29 for v in diff_squares(PAGE16_SQUARE, PAGE5_SQUARE)])))
    # 13. product mod 29
    derivs.append(("13_product_mod29", to_runes(prod_mod29(PAGE16_SQUARE, PAGE5_SQUARE))))
    # 14. Hill-cipher key is handled in Part D (matrix, not a primer)
    return derivs

# ============================================================================
# PART A — Run all 14 derivations × 9 chapters × 3 cipher modes
# ============================================================================
def run_part_a():
    """Returns (results_list, total_tests)."""
    print("\n" + "="*78)
    print("PART A — 14 magic-square derivations × 9 chapters × 3 cipher modes")
    print("="*78)
    all_results = []
    for square_choice in ["page5", "page16"]:
        derivs = build_derivations(square_choice)
        for chapter_name, runes_full in CHAPTERS:
            runes_200 = runes_full[:200]
            for deriv_name, primer in derivs:
                # Vigenere no-skip
                try:
                    pt = runes_to_latin(vigenere(runes_200, primer, decrypt=True, f_skip_rule=False))
                    sc = english_score(pt)
                    all_results.append({
                        "square": square_choice,
                        "chapter": chapter_name,
                        "derivation": deriv_name,
                        "cipher": "vigenere",
                        "score": round(sc, 2),
                        "snippet": pt[:60],
                    })
                except Exception as e:
                    pass
                # autokey plaintext
                try:
                    pt = runes_to_latin(autokey_vigenere(runes_200, primer, mode="plaintext", decrypt=True))
                    sc = english_score(pt)
                    all_results.append({
                        "square": square_choice,
                        "chapter": chapter_name,
                        "derivation": deriv_name,
                        "cipher": "autokey_pt",
                        "score": round(sc, 2),
                        "snippet": pt[:60],
                    })
                except Exception as e:
                    pass
                # autokey ciphertext
                try:
                    pt = runes_to_latin(autokey_vigenere(runes_200, primer, mode="ciphertext", decrypt=True))
                    sc = english_score(pt)
                    all_results.append({
                        "square": square_choice,
                        "chapter": chapter_name,
                        "derivation": deriv_name,
                        "cipher": "autokey_ct",
                        "score": round(sc, 2),
                        "snippet": pt[:60],
                    })
                except Exception as e:
                    pass
    print(f"Part A: ran {len(all_results)} tests (14 derivs × 9 chapters × 3 modes × 2 squares = 756)")
    # Sort by score, top 20
    all_results.sort(key=lambda x: -x["score"])
    print("\nTOP 20 of Part A:")
    for i, r in enumerate(all_results[:20], 1):
        print(f"  {i:2d}. {r['score']:6.2f} | {r['square']:6s} | {r['chapter']:18s} | {r['derivation']:25s} | {r['cipher']:12s} | {r['snippet']}")
    return all_results

# ============================================================================
# PART B — CROSS-PAGE CHAINED-KEY SCHEDULES
# ============================================================================
def run_chain_type_a(primers, n_pages_to_test=5):
    """
    Chain type A: primer = P0 for page 0; primer = plaintext(page 0) for page 1; ...
    For each chain step, use chapter N's first 200 runes as ciphertext.
    """
    results = []
    # Build a list of (chapter_name, runes_300) — represent pages
    page_list = [(name, runes_full[:300]) for name, runes_full in CHAPTERS]
    for primer_name, primer in primers:
        chain_primer = primer
        for step_idx, (chapter_name, runes_300) in enumerate(page_list[:n_pages_to_test]):
            try:
                # Try Vigenere decryption with current chain_primer
                pt_runes = vigenere(runes_300, chain_primer, decrypt=True, f_skip_rule=False)
                pt = runes_to_latin(pt_runes)
                sc = english_score(pt)
                results.append({
                    "chain": "A_vigenere",
                    "primer": primer_name,
                    "step": step_idx,
                    "chapter": chapter_name,
                    "score": round(sc, 2),
                    "snippet": pt[:60],
                })
                # Next page's primer = this page's plaintext (the runes, not the Latin)
                chain_primer = pt_runes[:200] if len(pt_runes) >= 200 else pt_runes
            except Exception as e:
                pass
            # Also try autokey
            try:
                chain_primer2 = primer
                pt_runes = autokey_vigenere(runes_300, chain_primer2, mode="plaintext", decrypt=True)
                pt = runes_to_latin(pt_runes)
                sc = english_score(pt)
                results.append({
                    "chain": "A_autokey_pt",
                    "primer": primer_name,
                    "step": step_idx,
                    "chapter": chapter_name,
                    "score": round(sc, 2),
                    "snippet": pt[:60],
                })
            except Exception as e:
                pass
    return results

def run_chain_type_b(primers, n_pages_to_test=5):
    """
    Chain type B: primer = P0 for page 0; primer = (P0 + plaintext(page 0)) mod 29 for page 1; ...
    """
    results = []
    page_list = [(name, runes_full[:300]) for name, runes_full in CHAPTERS]
    for primer_name, primer in primers:
        primer_decs = runes_to_decimals(primer) if all(is_rune(c) for c in primer) else None
        if primer_decs is None: continue
        for step_idx, (chapter_name, runes_300) in enumerate(page_list[:n_pages_to_test]):
            try:
                pt_runes = vigenere(runes_300, primer, decrypt=True, f_skip_rule=False)
                pt = runes_to_latin(pt_runes)
                sc = english_score(pt)
                results.append({
                    "chain": "B_vigenere",
                    "primer": primer_name,
                    "step": step_idx,
                    "chapter": chapter_name,
                    "score": round(sc, 2),
                    "snippet": pt[:60],
                })
                # Update primer = (primer + plaintext) mod 29
                pt_decs = runes_to_decimals(pt_runes[:200]) if len(pt_runes) >= 1 else []
                new_decs = [(primer_decs[i % len(primer_decs)] + pt_decs[i]) % 29 for i in range(len(pt_decs))]
                primer = decimals_to_runes(new_decs)
            except Exception as e:
                pass
    return results

def run_chain_type_c(primers_long, n_pages=56):
    """
    Chain type C: a single key-stream runs across ALL unsolved pages concatenated,
    with the primer at the start. Use the first 600 runes (a substantial prefix).
    """
    results = []
    # Build concatenated corpus — use first 600 runes from each chapter
    concat = "".join(runes_full[:600] for _, runes_full in CHAPTERS)[:3000]
    for primer_name, primer in primers_long:
        # Vigenere
        try:
            pt = runes_to_latin(vigenere(concat[:500], primer, decrypt=True, f_skip_rule=False))
            sc = english_score(pt)
            results.append({
                "chain": "C_vigenere",
                "primer": primer_name,
                "score": round(sc, 2),
                "snippet": pt[:60],
            })
        except Exception: pass
        # Autokey plaintext
        try:
            pt = runes_to_latin(autokey_vigenere(concat[:500], primer, mode="plaintext", decrypt=True))
            sc = english_score(pt)
            results.append({
                "chain": "C_autokey_pt",
                "primer": primer_name,
                "score": round(sc, 2),
                "snippet": pt[:60],
            })
        except Exception: pass
        # Autokey ciphertext
        try:
            pt = runes_to_latin(autokey_vigenere(concat[:500], primer, mode="ciphertext", decrypt=True))
            sc = english_score(pt)
            results.append({
                "chain": "C_autokey_ct",
                "primer": primer_name,
                "score": round(sc, 2),
                "snippet": pt[:60],
            })
        except Exception: pass
    return results

def run_chain_type_d(primers, n_pages_to_test=5):
    """
    Chain type D: each chapter uses a different primer derived from the previous chapter's plaintext.
    Here we just use the first chapter's plaintext as the next primer, with different cipher modes.
    """
    results = []
    page_list = [(name, runes_full[:300]) for name, runes_full in CHAPTERS]
    for primer_name, primer in primers:
        prev_pt = primer
        for step_idx, (chapter_name, runes_300) in enumerate(page_list[:n_pages_to_test]):
            try:
                pt_runes = vigenere(runes_300, prev_pt[:200], decrypt=True, f_skip_rule=False)
                pt = runes_to_latin(pt_runes)
                sc = english_score(pt)
                results.append({
                    "chain": "D_vigenere",
                    "primer": primer_name,
                    "step": step_idx,
                    "chapter": chapter_name,
                    "score": round(sc, 2),
                    "snippet": pt[:60],
                })
                prev_pt = pt_runes[:200] if len(pt_runes) >= 200 else pt_runes
            except Exception: pass
    return results

def run_part_b():
    print("\n" + "="*78)
    print("PART B — Cross-page chained-key schedules")
    print("="*78)
    # Primers for chains A, B, D (short primers)
    short_primers = [
        ("DIVINITY",       KEY_CANDIDATES["DIVINITY"]),
        ("FIRFUMFERENFE",  KEY_CANDIDATES["FIRFUMFERENFE"]),
        ("PARABLE",        KEY_CANDIDATES["PARABLE"]),
        ("INSTAR",         KEY_CANDIDATES["INSTAR"]),
        ("PILGRIM",        KEY_CANDIDATES["PILGRIM"]),
        # magic-square-derived: page16 row-major mod29 (25 runes)
        ("P16_row_mod29",  to_runes([v % 29 for v in flatten_row_major(PAGE16_SQUARE)])),
        ("P5_row_mod29",   to_runes([v % 29 for v in flatten_row_major(PAGE5_SQUARE)])),
        # magic-square decimal digits (~75 runes)
        ("P16_digits",     to_rune_digits(flatten_row_major(PAGE16_SQUARE))),
        ("P5_digits",      to_rune_digits(flatten_row_major(PAGE5_SQUARE))),
    ]
    # Long primers for chain type C
    long_primers = short_primers + [
        # 75+ rune primers
        ("P16_digits_full", to_rune_digits(flatten_row_major(PAGE16_SQUARE))),
        ("P5_digits_full",  to_rune_digits(flatten_row_major(PAGE5_SQUARE))),
        ("P16_zeck_full",   to_rune_zeck_idx(flatten_row_major(PAGE16_SQUARE))),
        ("P5_zeck_full",    to_rune_zeck_idx(flatten_row_major(PAGE5_SQUARE))),
    ]
    print("Chain type A (P0 -> pt -> pt -> ...):")
    a = run_chain_type_a(short_primers, n_pages_to_test=5)
    for r in a:
        print(f"  [{r['chain']}] {r['primer']:18s} step {r['step']} {r['chapter']:18s} score={r['score']:6.2f} | {r['snippet']}")
    print("\nChain type B (primer = P0 + pt(prev) mod 29):")
    b = run_chain_type_b(short_primers, n_pages_to_test=5)
    for r in b:
        print(f"  [{r['chain']}] {r['primer']:18s} step {r['step']} {r['chapter']:18s} score={r['score']:6.2f} | {r['snippet']}")
    print("\nChain type C (single long stream, long primers):")
    c = run_chain_type_c(long_primers)
    for r in c:
        print(f"  [{r['chain']}] {r['primer']:18s} score={r['score']:6.2f} | {r['snippet']}")
    print("\nChain type D (each chapter's primer = prev chapter's pt):")
    d = run_chain_type_d(short_primers, n_pages_to_test=5)
    for r in d:
        print(f"  [{r['chain']}] {r['primer']:18s} step {r['step']} {r['chapter']:18s} score={r['score']:6.2f} | {r['snippet']}")
    all_b = a + b + c + d
    all_b.sort(key=lambda x: -x["score"])
    print("\nTOP 10 Part B:")
    for i, r in enumerate(all_b[:10], 1):
        print(f"  {i:2d}. {r['score']:6.2f} | {r.get('chain','?'):18s} | {r.get('primer','?'):18s} | {r.get('chapter','?'):18s} | {r['snippet']}")
    return all_b

# ============================================================================
# PART C — PRIME-INDEX RECURRENCE RECONSTRUCTION
# ============================================================================
def run_part_c():
    """
    Try to find a recurrence of form:
      a[i][j] = c1*prime(idx1) + c2*prime(idx2) + c3*fib(idx3)
      a[i][j] = prime(i*5+j) + fib(i+j)
      a[i][j] = fib(prime(i)*5 + j)
    That generates the page-16 magic square.
    If we find one, use its parameters as a primer key.
    """
    print("\n" + "="*78)
    print("PART C — Prime-index recurrence reconstruction")
    print("="*78)
    report = []
    def log(s):
        print(s); report.append(s)

    # ----- Page 16 square -----
    for sq_name, sq in [("page_16", PAGE16_SQUARE), ("page_5", PAGE5_SQUARE)]:
        log(f"\n----- Square: {sq_name} -----")
        # Test 1: a[i][j] = prime(i*5+j+offset)?
        best_offset, best_match = 0, 0
        for offset in range(-10, 200):
            m = sum(1 for i in range(5) for j in range(5)
                    if prime_index_of(sq[i][j]) == i*5 + j + offset)
            if m > best_match:
                best_match = m; best_offset = offset
        log(f"  Test 1 (a[i][j] = prime(i*5+j+{best_offset})): {best_match}/25 cells match")

        # Test 2: a[i][j] = prime(i*5+j+offset) + fib(k)?
        # Check if a[i][j] - prime(i*5+j+offset) is a Fibonacci number
        best_off2, best_match2 = 0, 0
        for offset in range(-10, 100):
            m = 0
            for i in range(5):
                for j in range(5):
                    p_idx = i*5 + j + offset
                    if p_idx < 1: continue
                    p = nth_prime(p_idx)
                    diff = sq[i][j] - p
                    if diff > 0 and diff in fibs_up_to(2000):
                        m += 1
            if m > best_match2:
                best_match2 = m; best_off2 = offset
        log(f"  Test 2 (a[i][j] = prime(i*5+j+{best_off2}) + fib(k)): {best_match2}/25 cells match")

        # Test 3: a[i][j] = prime(i+offset) + prime(j+offset) (linear additive)
        best_off3, best_match3 = 0, 0
        for offset in range(-5, 200):
            m = sum(1 for i in range(5) for j in range(5)
                    if (i+offset >= 1 and j+offset >= 1 and
                        nth_prime(i+offset) + nth_prime(j+offset) == sq[i][j]))
            if m > best_match3:
                best_match3 = m; best_off3 = offset
        log(f"  Test 3 (a[i][j] = prime(i+{best_off3}) + prime(j+{best_off3})): {best_match3}/25 cells match")

        # Test 4: a[i][j] = fib(i+off) + fib(j+off) + prime(i*j+off) (3-term)
        # We test a small grid of offsets
        best = {"match": 0, "params": None}
        for off_i in range(1, 30):
            for off_j in range(1, 30):
                for off_p in range(-5, 30):
                    m = 0
                    for i in range(5):
                        for j in range(5):
                            try:
                                val = fib_at(i+off_i) + fib_at(j+off_j)
                                if i*j+off_p >= 1:
                                    val += nth_prime(i*j+off_p)
                                if val == sq[i][j]:
                                    m += 1
                            except Exception:
                                pass
                    if m > best["match"]:
                        best = {"match": m, "params": (off_i, off_j, off_p)}
        log(f"  Test 4 (a[i][j] = fib(i+oi) + fib(j+oj) + prime(i*j+op)): {best['match']}/25, params={best['params']}")

        # Test 5: a[i][j] = c1*prime(i*5+j+off) + c2*fib(i+j+off2)?
        # Try a small linear-regression-like brute force on c1, c2, off
        best5 = {"match": 0, "params": None}
        for c1 in range(1, 50):
            for c2 in range(0, 100):
                for off in range(-5, 30):
                    m = 0
                    for i in range(5):
                        for j in range(5):
                            try:
                                pi = i*5 + j + off
                                if pi < 1: continue
                                val = c1 * nth_prime(pi) + c2 * fib_at(i+j+1)
                                if val == sq[i][j]:
                                    m += 1
                            except Exception:
                                pass
                    if m > best5["match"]:
                        best5 = {"match": m, "params": (c1, c2, off)}
            # quick exit if we found something
            if best5["match"] >= 20:
                break
        log(f"  Test 5 (a[i][j] = c1*prime(i*5+j+off) + c2*fib(i+j+1)): {best5['match']}/25, params={best5['params']}")

        # Test 6: a[i][j] = prime(fib(i)*5 + j)?
        m = 0
        for i in range(5):
            for j in range(5):
                try:
                    p_idx = fib_at(i+1)*5 + j
                    if p_idx >= 1 and nth_prime(p_idx) == sq[i][j]:
                        m += 1
                except Exception: pass
        log(f"  Test 6 (a[i][j] = prime(fib(i+1)*5 + j)): {m}/25 cells match")

        # Test 7: a[i][j] = nth_prime(fib_at(i+j+1))?
        m = 0
        for i in range(5):
            for j in range(5):
                try:
                    p_idx = fib_at(i+j+1)
                    if p_idx >= 1 and nth_prime(p_idx) == sq[i][j]:
                        m += 1
                except Exception: pass
        log(f"  Test 7 (a[i][j] = prime(fib(i+j+1))): {m}/25 cells match")

        # Test 8: a[i][j] mod 29 — distribution
        mod29 = [sq[i][j] % 29 for i in range(5) for j in range(5)]
        log(f"  Test 8 (cells mod 29): {mod29}")
        log(f"  Unique: {sorted(set(mod29))} ({len(set(mod29))} distinct)")

        # Test 9: Zeckendorf term counts and indices
        all_indices = []
        term_counts = Counter()
        for i in range(5):
            for j in range(5):
                parts = zeckendorf(sq[i][j])
                term_counts[len(parts)] += 1
                for p in parts:
                    all_indices.append(fib_index(p))
        log(f"  Test 9 (Zeckendorf term-count distribution): {dict(sorted(term_counts.items()))}")
        log(f"  Distinct Fib indices used: {sorted(set(all_indices))}")

        # Test 10: a[i][j] - sum_of_row_zeros — symmetry
        # Check if square has 180-degree rotational symmetry
        rot_match = all(sq[i][j] == sq[4-i][4-j] for i in range(5) for j in range(5))
        log(f"  Test 10 (180° rotational symmetry): {rot_match}")

    log("\n----- If a recurrence was found, would test as primer here -----")
    # Even if no exact match, try the BEST candidate params as a primer anyway
    # Use the prime(i*5+j+best_offset) sequence for page 16 as a primer
    sq16 = PAGE16_SQUARE
    best_offset, best_match = 0, 0
    for offset in range(-10, 200):
        m = sum(1 for i in range(5) for j in range(5)
                if prime_index_of(sq16[i][j]) == i*5 + j + offset)
        if m > best_match:
            best_match = m; best_offset = offset
    log(f"\nBest prime-index offset for page 16: {best_offset} (matches {best_match}/25)")
    # Build primer from prime(i*5+j+best_offset) mod 29
    primer_decs = []
    for i in range(5):
        for j in range(5):
            p_idx = i*5 + j + best_offset
            if p_idx >= 1:
                primer_decs.append(nth_prime(p_idx) % 29)
            else:
                primer_decs.append(0)
    primer = "".join(dec_to_rune(d) for d in primer_decs)
    log(f"Primer (prime(i*5+j+{best_offset}) mod 29): {primer[:30]}...")
    # Score on each chapter
    log("\nScoring this prime-index primer on each chapter (Vigenere + autokey):")
    chain_c_results = []
    for chapter_name, runes_full in CHAPTERS:
        runes_200 = runes_full[:200]
        try:
            pt = runes_to_latin(vigenere(runes_200, primer, decrypt=True, f_skip_rule=False))
            sc = english_score(pt)
            chain_c_results.append((chapter_name, "vigenere", sc, pt[:60]))
            log(f"  {chapter_name:18s} vigenere  : {sc:6.2f} | {pt[:60]}")
        except Exception as e: pass
        try:
            pt = runes_to_latin(autokey_vigenere(runes_200, primer, mode="plaintext", decrypt=True))
            sc = english_score(pt)
            chain_c_results.append((chapter_name, "autokey_pt", sc, pt[:60]))
            log(f"  {chapter_name:18s} autokey_pt: {sc:6.2f} | {pt[:60]}")
        except Exception as e: pass
    return {"report": report, "best_offset": best_offset, "primer": primer,
            "results": chain_c_results}

# ============================================================================
# PART D — HILL-CIPHER 5x5 TESTS
# ============================================================================
def mat_det_5x5_mod29(M):
    """Compute determinant of 5x5 matrix M over Z_29 using cofactor expansion (small size)."""
    # Recursive cofactor expansion
    n = len(M)
    if n == 1:
        return M[0][0] % MOD
    if n == 2:
        return (M[0][0]*M[1][1] - M[0][1]*M[1][0]) % MOD
    det = 0
    for j in range(n):
        # minor: remove row 0, col j
        minor = [row[:j] + row[j+1:] for row in M[1:]]
        sign = (-1)**j
        det = (det + sign * M[0][j] * mat_det_5x5_mod29(minor)) % MOD
    return det % MOD

def modinv(a, m):
    """Modular inverse via extended Euclid."""
    a = a % m
    if a == 0: return None
    g, x, _ = extended_gcd(a, m)
    if g != 1: return None
    return x % m

def extended_gcd(a, b):
    if a == 0:
        return (b, 0, 1)
    g, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return (g, x, y)

def mat_inverse_5x5_mod29(M):
    """Compute inverse of 5x5 matrix M over Z_29. Returns None if not invertible."""
    det = mat_det_5x5_mod29(M)
    det_inv = modinv(det, MOD)
    if det_inv is None:
        return None
    # Compute cofactor matrix
    n = len(M)
    cof = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            minor = [row[:j] + row[j+1:] for k, row in enumerate(M) if k != i]
            sign = (-1)**(i+j)
            cof[i][j] = (sign * mat_det_5x5_mod29(minor)) % MOD
    # Adjugate = transpose of cofactor
    adj = [[cof[j][i] for j in range(n)] for i in range(n)]
    # Inverse = det_inv * adjugate
    inv = [[(det_inv * adj[i][j]) % MOD for j in range(n)] for i in range(n)]
    return inv

def mat_vec_mult_mod29(M, v):
    n = len(M)
    return [sum(M[i][j] * v[j] for j in range(n)) % MOD for i in range(n)]

def hill_decrypt_5x5(ciphertext_decs, key_matrix):
    """Hill cipher decrypt: plaintext = key_matrix_inv * ciphertext_block mod 29.
       Ciphertext_decs length must be multiple of 5. Returns plaintext decs."""
    inv = mat_inverse_5x5_mod29(key_matrix)
    if inv is None:
        return None
    out = []
    for i in range(0, len(ciphertext_decs), 5):
        block = ciphertext_decs[i:i+5]
        if len(block) < 5: break
        out.extend(mat_vec_mult_mod29(inv, block))
    return out

def hill_encrypt_5x5(plaintext_decs, key_matrix):
    out = []
    for i in range(0, len(plaintext_decs), 5):
        block = plaintext_decs[i:i+5]
        if len(block) < 5: break
        out.extend(mat_vec_mult_mod29(key_matrix, block))
    return out

def run_part_d():
    print("\n" + "="*78)
    print("PART D — Hill-cipher 5x5 tests")
    print("="*78)
    report = []
    def log(s): print(s); report.append(s)
    results = []
    for sq_name, sq in [("page5",  PAGE5_SQUARE),
                        ("page16", PAGE16_SQUARE)]:
        # Use the square as a Hill key matrix mod 29
        M = [[v % MOD for v in row] for row in sq]
        det = mat_det_5x5_mod29(M)
        det_inv = modinv(det, MOD)
        log(f"\n--- Square {sq_name} as Hill 5x5 key (mod 29) ---")
        log(f"  Determinant mod 29 = {det}  (inverse: {det_inv})")
        if det_inv is None:
            log(f"  NOT INVERTIBLE — cannot use as Hill key directly. Trying transpose & variations.")
            # Try transposed
            Mt = [[M[j][i] for j in range(5)] for i in range(5)]
            det_t = mat_det_5x5_mod29(Mt)
            log(f"  Transposed det = {det_t}")
            if modinv(det_t, MOD) is None:
                log(f"  Transposed also not invertible.")
                continue
            M_use = Mt
        else:
            M_use = M
        # Score on each chapter — first 100 runes (20 blocks of 5)
        for chapter_name, runes_full in CHAPTERS:
            runes_100 = runes_full[:100]
            ct_decs = runes_to_decimals(runes_100)
            # Decrypt with M_use as key
            pt_decs = hill_decrypt_5x5(ct_decs, M_use)
            if pt_decs is None: continue
            pt_runes = "".join(dec_to_rune(d) for d in pt_decs)
            pt = runes_to_latin(pt_runes)
            sc = english_score(pt)
            results.append({
                "square": sq_name, "chapter": chapter_name,
                "cipher": "hill5_decrypt",
                "score": round(sc, 2),
                "snippet": pt[:60],
            })
            log(f"  hill5_decrypt | {sq_name:6s} | {chapter_name:18s} | score={sc:6.2f} | {pt[:60]}")
            # Also try encrypt direction (in case the "key" is actually the inverse)
            pt_decs2 = hill_encrypt_5x5(ct_decs, M_use)
            pt_runes2 = "".join(dec_to_rune(d) for d in pt_decs2)
            pt2 = runes_to_latin(pt_runes2)
            sc2 = english_score(pt2)
            results.append({
                "square": sq_name, "chapter": chapter_name,
                "cipher": "hill5_encrypt",
                "score": round(sc2, 2),
                "snippet": pt2[:60],
            })
            log(f"  hill5_encrypt | {sq_name:6s} | {chapter_name:18s} | score={sc2:6.2f} | {pt2[:60]}")
    results.sort(key=lambda x: -x["score"])
    log("\nTOP 10 Part D:")
    for i, r in enumerate(results[:10], 1):
        log(f"  {i:2d}. {r['score']:6.2f} | {r['square']:6s} | {r['chapter']:18s} | {r['cipher']:15s} | {r['snippet']}")
    return {"report": report, "results": results}

# ============================================================================
# MAIN
# ============================================================================
def main():
    print("="*78)
    print("MAGIC-SQUARE DEEP DIVE + CROSS-PAGE CHAINED-KEY SCHEDULES")
    print("Task ID: p6b")
    print("="*78)
    print(f"# Loaded {len(CHAPTERS)} chapters, total {sum(len(r) for _, r in CHAPTERS)} runes")
    print(f"# Page 5 magic constant: {sum(PAGE5_SQUARE[0])}")
    print(f"# Page 16 magic constant: {sum(PAGE16_SQUARE[0])}")

    t0 = time.time()
    part_a_results = run_part_a()
    t1 = time.time()
    print(f"\nPart A elapsed: {t1-t0:.1f}s")

    part_b_results = run_part_b()
    t2 = time.time()
    print(f"Part B elapsed: {t2-t1:.1f}s")

    part_c_out = run_part_c()
    t3 = time.time()
    print(f"Part C elapsed: {t3-t2:.1f}s")

    part_d_out = run_part_d()
    t4 = time.time()
    print(f"Part D elapsed: {t4-t3:.1f}s")

    # Save all results to JSON
    out_json = {
        "part_a_results": part_a_results,
        "part_b_results": part_b_results,
        "part_c_report": part_c_out["report"],
        "part_c_best_offset": part_c_out["best_offset"],
        "part_c_primer": part_c_out["primer"],
        "part_c_results": part_c_out["results"],
        "part_d_report": part_d_out["report"],
        "part_d_results": part_d_out["results"],
    }
    out_path = os.path.join(HERE, "magicsquare_deeptest_results.json")
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(out_json, fp, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {out_path}")
    total = len(part_a_results) + len(part_b_results) + len(part_c_out["results"]) + len(part_d_out["results"])
    print(f"Total tests: Part A={len(part_a_results)}, Part B={len(part_b_results)}, "
          f"Part C={len(part_c_out['results'])}, Part D={len(part_d_out['results'])} → {total}")

if __name__ == "__main__":
    main()
