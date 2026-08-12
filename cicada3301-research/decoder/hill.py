#!/usr/bin/env python3
"""
hill.py — Hill cipher (2x2 matrix over Z_29) for the Gematria Primus alphabet
=============================================================================
Hypothesis 10 (variant): a Hill-cipher is another classical digraphic cipher.
Encryption: c1 = (a*p1 + b*p2) mod 29,  c2 = (c*p1 + d*p2) mod 29
            (the 2x2 matrix [[a,b],[c,d]] is the key)
Decryption: requires the matrix to be invertible mod 29 (det != 0 mod 29).
            p1 = det_inv * (d*c1 - b*c2) mod 29
            p2 = det_inv * (-c*c1 + a*c2) mod 29
            where det = (a*d - b*c) mod 29 and det_inv = modinv(det, 29).

Z_29 is a prime field, so a 2x2 matrix over Z_29 is invertible iff det != 0 mod 29.
The number of invertible 2x2 matrices over Z_29 is (29^2 - 1)(29^2 - 29) = 840*812 = 681,960.

This module provides:
  - hill_encrypt(runes, [[a,b],[c,d]]) -> ciphertext runes
  - hill_decrypt(runes, [[a,b],[c,d]]) -> plaintext runes
  - matrix_inverse_mod([[a,b],[c,d]], 29) -> inverse matrix or None
  - is_invertible([[a,b],[c,d]], 29) -> bool
  - brute_force_hill(ciphertext_runes, top_k=5, sample=None) -> list of (matrix, score, plaintext)
  - hill_climb_hill(ciphertext_runes, n_starts=20, n_iters=200) -> best matrix found

References:
  - RESEARCH_DOSSIER.md §3 (cipher operations)
  - FRESH_2024_2025_FINDINGS.md §4 Hypothesis 10
"""
from __future__ import annotations
import sys
import random
import time
from typing import List, Tuple, Dict, Optional

sys.path.insert(0, "/home/z/my-project/cicada3301-research/decoder")
from gematria_primus import (
    RUNES, N_RUNES, MOD, LETTERS, DECIMALS, DEC_TO_RUNE, RUNE_TO_DEC,
    DEC_TO_LETTER, rune_to_dec, dec_to_rune, is_rune,
    clean_runes, runes_to_decimals, decimals_to_runes, runes_to_latin,
    english_score,
)

# For modular inverse, use pow(x, -1, mod) (Python 3.8+)
def modinv(x: int, m: int) -> Optional[int]:
    """Modular multiplicative inverse of x mod m. Returns None if not invertible."""
    g = gcd(x, m)
    if g != 1:
        return None
    return pow(x % m, -1, m)

def gcd(a: int, b: int) -> int:
    a = abs(a); b = abs(b)
    while b:
        a, b = b, a % b
    return a or 1


# ----------------------------------------------------------------------------
# Hill cipher core operations
# ----------------------------------------------------------------------------

def is_invertible(M: List[List[int]], mod: int = MOD) -> bool:
    """Check if 2x2 matrix M is invertible mod 29 (det coprime to 29)."""
    a, b = M[0]
    c, d = M[1]
    det = (a * d - b * c) % mod
    return det != 0 and gcd(det, mod) == 1


def matrix_inverse_mod(M: List[List[int]], mod: int = MOD) -> Optional[List[List[int]]]:
    """Inverse of 2x2 matrix M over Z_mod. Returns None if not invertible."""
    a, b = M[0]
    c, d = M[1]
    det = (a * d - b * c) % mod
    inv_det = modinv(det, mod)
    if inv_det is None:
        return None
    # Inverse of [[a,b],[c,d]] is (1/det) * [[d, -b], [-c, a]]
    return [
        [( d * inv_det) % mod, ((-b) * inv_det) % mod],
        [((-c) * inv_det) % mod, ( a * inv_det) % mod],
    ]


def hill_encrypt(runes: str, M: List[List[int]]) -> str:
    """
    Encrypt runes with 2x2 Hill matrix M = [[a,b],[c,d]].
    c1 = (a*p1 + b*p2) mod 29, c2 = (c*p1 + d*p2) mod 29.
    Pads odd-length input with ᚠ (decimal 0).
    """
    a, b = M[0]
    c, d = M[1]
    decs = runes_to_decimals(clean_runes(runes))
    if len(decs) % 2 == 1:
        decs.append(0)  # pad with ᚠ
    out = []
    for i in range(0, len(decs), 2):
        p1, p2 = decs[i], decs[i + 1]
        out.append((a * p1 + b * p2) % MOD)
        out.append((c * p1 + d * p2) % MOD)
    return decimals_to_runes(out)


def hill_decrypt(runes: str, M: List[List[int]]) -> str:
    """
    Decrypt runes with 2x2 Hill matrix M = [[a,b],[c,d]] (M is the ENCRYPTION matrix;
    we compute its inverse to decrypt).
    Pads odd-length input with ᚠ (decimal 0).
    """
    inv = matrix_inverse_mod(M, MOD)
    if inv is None:
        raise ValueError("Matrix is not invertible mod 29")
    a, b = inv[0]
    c, d = inv[1]
    decs = runes_to_decimals(clean_runes(runes))
    if len(decs) % 2 == 1:
        decs.append(0)  # pad with ᚠ
    out = []
    for i in range(0, len(decs), 2):
        c1, c2 = decs[i], decs[i + 1]
        out.append((a * c1 + b * c2) % MOD)
        out.append((c * c1 + d * c2) % MOD)
    return decimals_to_runes(out)


# ----------------------------------------------------------------------------
# Brute-force search: iterate over all invertible 2x2 matrices
# ----------------------------------------------------------------------------

def brute_force_hill(ciphertext_runes: str, top_k: int = 5,
                     sample_size: Optional[int] = None,
                     verbose: bool = False) -> List[Tuple[List[List[int]], float, str]]:
    """
    Brute-force search over all invertible 2x2 matrices over Z_29.
    For each matrix, decrypt the ciphertext and score with english_score.
    Return the top_k matrices by score, with their score and latin plaintext.

    If sample_size is given, sample that many random matrices instead of iterating all.
    Total invertible matrices = (29^2-1)*(29^2-29) = 840*812 = 681,960.

    Each iteration: ~200-300 microseconds in pure Python.
    Full brute-force: ~3-4 minutes.
    Sample 50k: ~15 seconds.
    """
    decs = runes_to_decimals(clean_runes(ciphertext_runes))
    if len(decs) % 2 == 1:
        decs.append(0)
    pairs = [(decs[i], decs[i + 1]) for i in range(0, len(decs), 2)]
    n_pairs = len(pairs)

    # Precompute LETTERS lookup as a list (faster than dict)
    LETTERS_LUT = LETTERS  # index by decimal value 0..28

    if sample_size is None:
        # Full brute-force: iterate a, b, c, d over 0..28
        iterator = ((a, b, c, d) for a in range(MOD) for b in range(MOD)
                                for c in range(MOD) for d in range(MOD))
        total = MOD ** 4  # 707,281
    else:
        iterator = [(random.randint(0, MOD - 1), random.randint(0, MOD - 1),
                     random.randint(0, MOD - 1), random.randint(0, MOD - 1))
                    for _ in range(sample_size)]
        total = sample_size

    results: List[Tuple[List[List[int]], float, str]] = []
    start = time.time()
    count = 0
    for a, b, c, d in iterator:
        det = (a * d - b * c) % MOD
        if det == 0:
            count += 1
            continue
        inv_det = pow(det, -1, MOD)
        # Inverse matrix: [[d*inv, -b*inv], [-c*inv, a*inv]]
        ia = ( d * inv_det) % MOD
        ib = ((-b) * inv_det) % MOD
        ic = ((-c) * inv_det) % MOD
        idd = ( a * inv_det) % MOD
        # Decrypt all pairs
        out_decs = []
        for c1, c2 in pairs:
            out_decs.append((ia * c1 + ib * c2) % MOD)
            out_decs.append((ic * c1 + idd * c2) % MOD)
        # Convert to latin
        try:
            pt_latin = "".join(LETTERS_LUT[d] for d in out_decs)
        except IndexError:
            count += 1
            continue
        score = english_score(pt_latin)
        results.append(([[a, b], [c, d]], score, pt_latin))
        count += 1
        if verbose and count % 50000 == 0:
            elapsed = time.time() - start
            pct = 100.0 * count / total
            print(f"  [{count}/{total}] {pct:.1f}%  elapsed={elapsed:.1f}s  "
                  f"best={max(r[1] for r in results):.2f}")

    # Sort by score descending, return top_k
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def hill_climb_hill(ciphertext_runes: str, n_starts: int = 20,
                    n_iters: int = 200, seed: Optional[int] = None) -> Tuple[List[List[int]], float, str]:
    """
    Hill-climbing search: start from a random invertible matrix and iteratively mutate it
    to maximize english_score. Returns the best matrix found.

    This is a fallback for when the full brute-force is too slow.
    """
    if seed is not None:
        random.seed(seed)

    decs = runes_to_decimals(clean_runes(ciphertext_runes))
    if len(decs) % 2 == 1:
        decs.append(0)
    pairs = [(decs[i], decs[i + 1]) for i in range(0, len(decs), 2)]
    LETTERS_LUT = LETTERS

    def score_matrix(M):
        a, b = M[0]
        c, d = M[1]
        det = (a * d - b * c) % MOD
        if det == 0:
            return -1e9, ""
        inv_det = pow(det, -1, MOD)
        ia = ( d * inv_det) % MOD
        ib = ((-b) * inv_det) % MOD
        ic = ((-c) * inv_det) % MOD
        idd = ( a * inv_det) % MOD
        out = []
        for c1, c2 in pairs:
            out.append(LETTERS_LUT[(ia * c1 + ib * c2) % MOD])
            out.append(LETTERS_LUT[(ic * c1 + idd * c2) % MOD])
        pt_latin = "".join(out)
        return english_score(pt_latin), pt_latin

    def random_matrix():
        while True:
            M = [[random.randint(0, MOD - 1) for _ in range(2)] for _ in range(2)]
            if is_invertible(M):
                return M

    best_M = None
    best_score = -1e9
    best_pt = ""
    for _ in range(n_starts):
        M = random_matrix()
        cur_score, _ = score_matrix(M)
        for _ in range(n_iters):
            # Mutate: change one element
            i, j = random.randint(0, 1), random.randint(0, 1)
            old = M[i][j]
            new_val = random.randint(0, MOD - 1)
            M[i][j] = new_val
            if not is_invertible(M):
                M[i][j] = old
                continue
            new_score, new_pt = score_matrix(M)
            if new_score > cur_score:
                cur_score = new_score
                if new_score > best_score:
                    best_score = new_score
                    best_M = [row[:] for row in M]
                    best_pt = new_pt
            else:
                M[i][j] = old
    return best_M, best_score, best_pt


# ----------------------------------------------------------------------------
# Magic-square sub-blocks (Cicada-emitted 2x2 matrices)
# ----------------------------------------------------------------------------
# These are the 2x2 sub-blocks of the page-16 magic square:
#   434 1311 312 278 966
#   204 812 934 280 1071
#   626 620 809 620 626
#   1071 280 934 812 204
#   966 278 312 1311 434
# All values reduced mod 29 to fit the Z_29 field.
MAGIC_SQUARE_16 = [
    [434, 1311, 312, 278, 966],
    [204, 812, 934, 280, 1071],
    [626, 620, 809, 620, 626],
    [1071, 280, 934, 812, 204],
    [966, 278, 312, 1311, 434],
]

def magic_square_sub_blocks() -> List[Tuple[str, List[List[int]]]]:
    """
    All 2x2 contiguous sub-blocks of the page-16 magic square, reduced mod 29.
    Used as candidate Hill cipher matrices (per task spec).
    """
    blocks = []
    for i in range(4):
        for j in range(4):
            block = [
                [MAGIC_SQUARE_16[i][j] % MOD, MAGIC_SQUARE_16[i][j + 1] % MOD],
                [MAGIC_SQUARE_16[i + 1][j] % MOD, MAGIC_SQUARE_16[i + 1][j + 1] % MOD],
            ]
            name = f"MS16[{i},{j}]"
            blocks.append((name, block))
    # Also include 2x2 corners
    corners = [
        ("MS16_topleft", [[434 % MOD, 966 % MOD], [1071 % MOD, 204 % MOD]]),
        ("MS16_toprite", [[312 % MOD, 966 % MOD], [934 % MOD, 1071 % MOD]]),
        ("MS16_botleft", [[1071 % MOD, 204 % MOD], [966 % MOD, 434 % MOD]]),
        ("MS16_botrite", [[934 % MOD, 1071 % MOD], [312 % MOD, 434 % MOD]]),
    ]
    blocks.extend(corners)
    return blocks


# ----------------------------------------------------------------------------
# Self-test / demo
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("HILL CIPHER — 2x2 MATRIX OVER Z_29")
    print("=" * 70)
    print()

    # Self-test 1: round-trip
    print("Self-test 1: encrypt/decrypt round-trip with matrix [[3,5],[1,7]]")
    M = [[3, 5], [1, 7]]
    print(f"  det = {(3*7 - 5*1) % MOD} (coprime to {MOD}? {gcd((3*7-5*1)%MOD, MOD) == 1})")
    pt = "ᛈᚪᚱᚪᛒᛚᛖᚹᛖᛚᚳᚩᛗᛖ"  # PARABLE WELCOME
    ct = hill_encrypt(pt, M)
    pt_back = hill_decrypt(ct, M)
    pt_clean = clean_runes(pt)
    pt_back_clean = clean_runes(pt_back)
    print(f"  plaintext : {pt_clean} ({len(pt_clean)} runes)")
    print(f"  ciphertext: {ct} ({len(ct)} runes)")
    print(f"  decrypted : {pt_back_clean} ({len(pt_back_clean)} runes)")
    print(f"  round-trip OK: {pt_clean == pt_back_clean}")
    print()

    # Self-test 2: small brute-force demo (sample 5k)
    print("Self-test 2: brute-force Hill on first 200 runes of unsolved corpus (sample 5000)")
    import json
    with open("/home/z/my-project/cicada3301-research/decoder/unsolved_pages.json") as f:
        pages = json.load(f)
    corpus = "".join(p["runes"] for p in pages if not p.get("is_solved", False))
    ct = corpus[:200]
    top5 = brute_force_hill(ct, top_k=5, sample_size=5000, verbose=True)
    print("Top 5 matrices by english_score:")
    for i, (M, score, pt_latin) in enumerate(top5):
        print(f"  {i+1}. M={M}  score={score:.4f}")
        print(f"     PT[:80]: {pt_latin[:80]}")
    print()

    # Self-test 3: hill climbing
    print("Self-test 3: hill-climbing Hill on first 200 runes (20 starts, 200 iters)")
    best_M, best_score, best_pt = hill_climb_hill(ct, n_starts=20, n_iters=200, seed=42)
    print(f"  best M = {best_M}")
    print(f"  best score = {best_score:.4f}")
    print(f"  best PT[:80] = {best_pt[:80]}")
    print()

    # Self-test 4: magic-square sub-blocks
    print("Self-test 4: magic-square sub-blocks as Hill matrices")
    for name, M in magic_square_sub_blocks():
        det = (M[0][0] * M[1][1] - M[0][1] * M[1][0]) % MOD
        if det == 0:
            print(f"  {name}: M={M}  det=0 (NOT invertible)")
            continue
        try:
            pt_latin = runes_to_latin(hill_decrypt(ct, M))
            score = english_score(pt_latin)
            print(f"  {name}: M={M}  det={det}  score={score:.4f}  PT[:60]={pt_latin[:60]}")
        except Exception as e:
            print(f"  {name}: M={M}  det={det}  ERROR: {e}")
    print()
    print("Done.")
