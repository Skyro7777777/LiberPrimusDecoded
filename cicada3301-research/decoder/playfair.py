#!/usr/bin/env python3
"""
playfair.py — Playfair cipher for the 29-rune Gematria Primus alphabet
======================================================================
Hypothesis 10 (FRESH_2024_2025_FINDINGS.md §4): the LP2 cipher may be a Playfair-class
digraphic substitution over the 29-rune alphabet. Digraphic ciphers naturally suppress
doublets because the same plaintext symbol cannot appear twice in the same digraph in
classical Playfair — partially explaining the 5.19× doublet suppression observed in the
unsolved corpus.

ALPHABET: 29 runes (ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ) plus 1 FILLER sentinel (ᛥ) → 30 cells.

We use 'ᛥ' (Anglo-Saxon "stan" rune — NOT in the Gematria Primus alphabet) as the FILLER
sentinel so that it does NOT collide with any of the 29 runes. This ensures the matrix
position lookup is unambiguous (no rune occupies two cells).

MATRIX LAYOUT: 6 rows × 5 columns (30 cells).
  - The first 29 cells hold the runes (in key-prefix-reordered standard-alphabet order).
  - The 30th cell (row 5, col 4) holds the FILLER sentinel 'ᛥ'.

KEY CONSTRUCTION:
  - Key runes are placed first (deduplicated, first occurrence kept).
  - Remaining runes follow in standard Gematria-Primus order.
  - FILLER ('ᛥ') is appended as the 30th cell.
  - The grid is filled row-major (left→right, top→bottom).

DECRYPTION RULES for a rune-pair (a, b):
  1. SAME ROW: shift LEFT (col -= 1, wrapping).
  2. SAME COLUMN: shift UP (row -= 1, wrapping).
  3. RECTANGLE: swap columns (a_new = matrix[ra][cb], b_new = matrix[rb][ca]).

SPECIAL CASES:
  - Repeated rune in a pair: insert FILLER between them and re-pair (standard Playfair).
  - Odd-length input: append FILLER.
  - Decryption output may contain FILLER ('ᛥ') — these are stripped before scoring.

References:
  - RESEARCH_DOSSIER.md §3 (cipher operations)
  - FRESH_2024_2025_FINDINGS.md §4 Hypothesis 10
  - cicada-solvers/lp-decrypter (GitHub) — "generic LP decrypter 1: functions of two runes"
"""
from __future__ import annotations
import sys
from typing import List, Tuple, Dict, Optional

sys.path.insert(0, "/home/z/my-project/cicada3301-research/decoder")
from gematria_primus import (
    RUNES, N_RUNES, MOD, LETTERS, DECIMALS, DEC_TO_RUNE, RUNE_TO_DEC,
    DEC_TO_LETTER, rune_to_dec, dec_to_rune, is_rune,
    clean_runes, runes_to_decimals, decimals_to_runes, runes_to_latin,
    english_score,
)

# ----------------------------------------------------------------------------
# Matrix dimensions: 6 rows × 5 columns = 30 cells (29 runes + 1 sentinel filler)
# ----------------------------------------------------------------------------
ROWS: int = 6
COLS: int = 5
N_CELLS: int = ROWS * COLS              # 30

# FILLER sentinel: 'ᛥ' (stan rune) — chosen because:
#   (1) it is NOT in the 29-rune Gematria Primus alphabet (no collision);
#   (2) it is a real Unicode rune character, so it composes naturally with the matrix;
#   (3) it can be safely stripped from decrypted output without affecting any of the
#       29 real runes.
FILLER: str = "ᛥ"


def _dedup_runes(runes: str) -> str:
    """Return runes with duplicates removed (first occurrence kept)."""
    seen = set()
    out = []
    for r in runes:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return "".join(out)


def build_matrix(key_runes: str) -> List[List[str]]:
    """
    Construct the 6×5 Playfair matrix from a key.

    - Dedup key runes (first occurrence kept).
    - Append remaining runes of the standard alphabet in order.
    - Append FILLER ('ᛥ') as the 30th cell.

    Returns ROWS×COLS nested list matrix[row][col] = single character.
    """
    key_dedup = _dedup_runes(clean_runes(key_runes))
    placed = set(key_dedup)
    cells = list(key_dedup)
    for r in RUNES:
        if r not in placed:
            cells.append(r)
            placed.add(r)
    cells.append(FILLER)
    assert len(cells) == N_CELLS, f"matrix cells mismatch: {len(cells)} != {N_CELLS}"
    matrix = [cells[r * COLS:(r + 1) * COLS] for r in range(ROWS)]
    return matrix


def matrix_to_str(matrix: List[List[str]]) -> str:
    """Pretty-print matrix as 6 rows of 5 runes each."""
    return "\n".join(" ".join(row) for row in matrix)


def _positions(matrix: List[List[str]]) -> Dict[str, Tuple[int, int]]:
    """Return {char: (row, col)} lookup. Each cell has a unique character (no duplicates)."""
    pos = {}
    for r in range(ROWS):
        for c in range(COLS):
            ch = matrix[r][c]
            pos[ch] = (r, c)
    return pos


def _decrypt_pair(a: str, b: str, matrix: List[List[str]],
                  pos: Dict[str, Tuple[int, int]]) -> Tuple[str, str]:
    """Apply Playfair DECRYPTION rule to one pair (a, b)."""
    ra, ca = pos[a]
    rb, cb = pos[b]
    if ra == rb:
        # Same row: shift LEFT
        a_new = matrix[ra][(ca - 1) % COLS]
        b_new = matrix[rb][(cb - 1) % COLS]
    elif ca == cb:
        # Same column: shift UP
        a_new = matrix[(ra - 1) % ROWS][ca]
        b_new = matrix[(rb - 1) % ROWS][cb]
    else:
        # Rectangle: swap columns
        a_new = matrix[ra][cb]
        b_new = matrix[rb][ca]
    return a_new, b_new


def _encrypt_pair(a: str, b: str, matrix: List[List[str]],
                  pos: Dict[str, Tuple[int, int]]) -> Tuple[str, str]:
    """Apply Playfair ENCRYPTION rule to one pair (a, b)."""
    ra, ca = pos[a]
    rb, cb = pos[b]
    if ra == rb:
        a_new = matrix[ra][(ca + 1) % COLS]
        b_new = matrix[rb][(cb + 1) % COLS]
    elif ca == cb:
        a_new = matrix[(ra + 1) % ROWS][ca]
        b_new = matrix[(rb + 1) % ROWS][cb]
    else:
        a_new = matrix[ra][cb]
        b_new = matrix[rb][ca]
    return a_new, b_new


def _clean_runes_with_filler(text: str) -> str:
    """Like gematria_primus.clean_runes, but also preserves the FILLER ('ᛥ').

    The standard clean_runes() strips every character that's not one of the 29
    standard runes — which would erase our FILLER. We need a custom cleaner that
    keeps the FILLER around for the Playfair pair-up logic.
    """
    return "".join(ch for ch in text if (is_rune(ch) or ch == FILLER))


def _preprocess(plaintext_runes: str) -> str:
    """
    Standard Playfair preprocessing:
      - Insert FILLER between any pair of identical consecutive runes.
      - If final length is odd, append FILLER.
    """
    out = []
    runes = clean_runes(plaintext_runes)
    i = 0
    while i < len(runes):
        a = runes[i]
        out.append(a)
        if i + 1 < len(runes):
            b = runes[i + 1]
            if a == b:
                out.append(FILLER)
            else:
                out.append(b)
                i += 1
        i += 1
    if len(out) % 2 == 1:
        out.append(FILLER)
    return "".join(out)


def playfair_decrypt(ciphertext_runes: str, key_runes: str,
                    strip_filler: bool = True) -> str:
    """
    Decrypt a Playfair-encrypted ciphertext.

    The ciphertext is assumed to contain only the 29 standard runes (no FILLER).
    Decryption may produce FILLER ('ᛥ') characters in the output; these are stripped
    when strip_filler=True.
    """
    matrix = build_matrix(key_runes)
    pos = _positions(matrix)
    ct = _clean_runes_with_filler(ciphertext_runes)
    if len(ct) % 2 == 1:
        # Pad odd-length ciphertext with FILLER (rare; valid Playfair CTs are even-length)
        ct = ct + FILLER
    out = []
    for i in range(0, len(ct), 2):
        a, b = ct[i], ct[i + 1]
        a_new, b_new = _decrypt_pair(a, b, matrix, pos)
        out.append(a_new)
        out.append(b_new)
    pt = "".join(out)
    if strip_filler:
        pt = pt.replace(FILLER, "")
    return pt


def playfair_encrypt(plaintext_runes: str, key_runes: str) -> str:
    """Encrypt a plaintext under Playfair (applies preprocessing first)."""
    matrix = build_matrix(key_runes)
    pos = _positions(matrix)
    pt = _preprocess(plaintext_runes)
    out = []
    for i in range(0, len(pt), 2):
        a, b = pt[i], pt[i + 1]
        a_new, b_new = _encrypt_pair(a, b, matrix, pos)
        out.append(a_new)
        out.append(b_new)
    return "".join(out)


def playfair_decrypt_to_latin(ciphertext_runes: str, key_runes: str) -> str:
    """Decrypt and convert to Latin letters (filler stripped)."""
    pt = playfair_decrypt(ciphertext_runes, key_runes, strip_filler=True)
    return runes_to_latin(pt)


# ----------------------------------------------------------------------------
# Self-test / demo
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("PLAYFAIR CIPHER — 29-RUNE GEMATRIA PRIMUS")
    print("=" * 70)
    print(f"Matrix: {ROWS} rows × {COLS} cols = {N_CELLS} cells (29 runes + 1 sentinel)")
    print()

    # Self-test 1: identity round-trip on small texts
    print("Self-test 1: round-trip on 'PARABLE' with key DIVINITY")
    key = "ᛞᛁᚢᛁᚾᛁᛏᚣ"
    matrix = build_matrix(key)
    print(matrix_to_str(matrix))
    pt = "ᛈᚪᚱᚪᛒᛚᛖ"   # PARABLE
    ct = playfair_encrypt(pt, key)
    pt_back = playfair_decrypt(ct, key, strip_filler=False)
    pt_back_clean = pt_back.replace(FILLER, "")
    pt_clean = pt.replace(FILLER, "")
    print(f"  plaintext : {pt}")
    print(f"  ciphertext: {ct}")
    print(f"  decrypted : {pt_back}")
    print(f"  decrypted (stripped): {pt_back_clean}")
    print(f"  round-trip OK: {pt_clean == pt_back_clean}")
    print()

    # Self-test 2: another round-trip with a longer text
    print("Self-test 2: round-trip on 'WELCOME' with key PRIMESACRED")
    key = "ᛈᚱᛁᛗᛖᛋᚪᚳᚱᛖᛞ"  # PRIMESACRED
    matrix = build_matrix(key)
    print(matrix_to_str(matrix))
    pt = "ᚹᛖᛚᚳᚩᛗᛖ"  # WELCOME
    ct = playfair_encrypt(pt, key)
    pt_back = playfair_decrypt(ct, key, strip_filler=True)
    print(f"  plaintext : {pt}")
    print(f"  ciphertext: {ct}")
    print(f"  decrypted : {pt_back}")
    print(f"  round-trip OK: {pt == pt_back}")
    print()

    # Self-test 3: decrypt first 200 runes of unsolved corpus with DIVINITY
    print("Self-test 3: decrypt first 200 runes of unsolved corpus (key DIVINITY)")
    import json
    with open("/home/z/my-project/cicada3301-research/decoder/unsolved_pages.json") as f:
        pages = json.load(f)
    corpus = "".join(p["runes"] for p in pages if not p.get("is_solved", False))
    ct = corpus[:200]
    pt = playfair_decrypt(ct, "ᛞᛁᚢᛁᚾᛁᛏᚣ", strip_filler=True)
    pt_latin = runes_to_latin(pt)
    print(f"  CT[:40]   : {ct[:40]}")
    print(f"  PT[:80] latin: {pt_latin[:80]}")
    print(f"  english_score: {english_score(pt_latin):.4f}")
    print()
    print("Done.")
