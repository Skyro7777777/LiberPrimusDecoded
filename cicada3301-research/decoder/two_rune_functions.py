#!/usr/bin/env python3
"""
two_rune_functions.py — General two-rune function decrypter
============================================================
Per the cicada-solvers/lp-decrypter repo's vague description ("generic LP decrypter
1: functions of two runes"), implement a general two-rune function decrypter.

For each rune-pair (r1, r2) in the ciphertext, output = f(r1, r2), where f is one of:
  - f_add(r1, r2) = (r1 + r2) mod 29                -> single rune
  - f_sub(r1, r2) = (r1 - r2) mod 29                -> single rune
  - f_sub_rev(r1, r2) = (r2 - r1) mod 29            -> single rune (mirror)
  - f_mul(r1, r2) = (r1 * r2) mod 29                -> single rune (field mult in Z_29)
  - f_add2(r1, r2) = (r1 + 2*r2) mod 29             -> single rune
  - f_2add(r1, r2) = (2*r1 + r2) mod 29             -> single rune
  - f_xor(r1, r2) = r1 XOR r2 (byte-level, no mod)  -> single rune (if result in 0..28)

These collapse 2 runes -> 1 rune, so 200 input runes -> 100 output runes.
"""
from __future__ import annotations
import sys
from typing import Callable, List, Tuple, Dict

sys.path.insert(0, "/home/z/my-project/cicada3301-research/decoder")
from gematria_primus import (
    RUNES, N_RUNES, MOD, LETTERS, DECIMALS, DEC_TO_RUNE, RUNE_TO_DEC,
    DEC_TO_LETTER, rune_to_dec, dec_to_rune, is_rune,
    clean_runes, runes_to_decimals, decimals_to_runes, runes_to_latin,
    english_score,
)


# ----------------------------------------------------------------------------
# Two-rune function definitions
# ----------------------------------------------------------------------------

def f_add(r1: int, r2: int) -> int:
    """(r1 + r2) mod 29"""
    return (r1 + r2) % MOD

def f_sub(r1: int, r2: int) -> int:
    """(r1 - r2) mod 29"""
    return (r1 - r2) % MOD

def f_sub_rev(r1: int, r2: int) -> int:
    """(r2 - r1) mod 29 (mirror of f_sub)"""
    return (r2 - r1) % MOD

def f_mul(r1: int, r2: int) -> int:
    """(r1 * r2) mod 29 — field multiplication in Z_29"""
    return (r1 * r2) % MOD

def f_add2(r1: int, r2: int) -> int:
    """(r1 + 2*r2) mod 29"""
    return (r1 + 2 * r2) % MOD

def f_2add(r1: int, r2: int) -> int:
    """(2*r1 + r2) mod 29"""
    return (2 * r1 + r2) % MOD

def f_xor(r1: int, r2: int) -> int:
    """r1 XOR r2 (byte-level XOR; result used as decimal value, clamped to 0..28)."""
    x = r1 ^ r2
    if x >= MOD:
        return x % MOD  # fallback to mod 29 if XOR exceeds alphabet
    return x

def f_xor_strict(r1: int, r2: int) -> int:
    """r1 XOR r2 strictly — if result > 28, returns 0 (ᚠ) as a sentinel."""
    x = r1 ^ r2
    return x if 0 <= x < MOD else 0

# Catalog of two-rune functions
TWO_RUNE_FUNCTIONS: List[Tuple[str, Callable[[int, int], int]]] = [
    ("add",         f_add),
    ("sub",         f_sub),
    ("sub_rev",     f_sub_rev),
    ("mul",         f_mul),
    ("add_2r2",     f_add2),
    ("2r1_add",     f_2add),
    ("xor_mod29",   f_xor),
    ("xor_strict",  f_xor_strict),
]


def apply_two_rune_function(runes: str, f: Callable[[int, int], int]) -> str:
    """
    Apply two-rune function f to consecutive pairs of runes.
    200 input runes -> 100 output runes.
    If the input has odd length, the last rune is dropped (no pair partner).
    """
    decs = runes_to_decimals(clean_runes(runes))
    out = []
    for i in range(0, len(decs) - 1, 2):
        r1, r2 = decs[i], decs[i + 1]
        out.append(f(r1, r2))
    return decimals_to_runes(out)


def test_all_two_rune_functions(ciphertext_runes: str) -> List[Tuple[str, float, str]]:
    """
    Test all defined two-rune functions on the ciphertext.
    Returns a list of (function_name, english_score, latin_plaintext) tuples,
    sorted by score descending.
    """
    results = []
    for name, f in TWO_RUNE_FUNCTIONS:
        pt_runes = apply_two_rune_function(ciphertext_runes, f)
        pt_latin = runes_to_latin(pt_runes)
        score = english_score(pt_latin)
        results.append((name, score, pt_latin))
    results.sort(key=lambda x: x[1], reverse=True)
    return results


# ----------------------------------------------------------------------------
# Self-test / demo
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("TWO-RUNE FUNCTION DECRYPTER")
    print("=" * 70)
    print()
    print(f"Functions defined: {len(TWO_RUNE_FUNCTIONS)}")
    for name, f in TWO_RUNE_FUNCTIONS:
        print(f"  {name}: f(5, 7) = {f(5, 7)}")
    print()

    # Self-test: apply all to first 200 runes of unsolved corpus
    print("Apply all two-rune functions to first 200 runes of unsolved corpus (-> 100 runes):")
    import json
    with open("/home/z/my-project/cicada3301-research/decoder/unsolved_pages.json") as f:
        pages = json.load(f)
    corpus = "".join(p["runes"] for p in pages if not p.get("is_solved", False))
    ct = corpus[:200]
    results = test_all_two_rune_functions(ct)
    for name, score, pt in results:
        print(f"  {name:12s}  score={score:.4f}  PT[:80]: {pt[:80]}")
    print()
    print("Done.")
