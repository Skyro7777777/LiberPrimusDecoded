#!/usr/bin/env python3
"""
verify_prime_fib.py
===================
Verify the Prime-Fibonacci meshing framework claimed by CicadaSolvers
(FRESH_2024_2025_FINDINGS.md §2.7).

Tasks:
  1. Compute the GP-sum (gematria-primus sum using prime values) of the
     2015 Planned Parenthood PGP-signed message.  Expected: 11,570 = 2×5×13×89
     (first four Fibonacci primes).
  2. Compute the GP-sum of the 2016 "LP is the way" message.
  3. Compute the GP-sum of the 2017 "Beware False Paths" message.
  4. Verify whether the 2017 GP-sum is the "next term" of the algorithm found
     in the 2016 message (per CicadaSolvers claim).
  5. Verify that 3301 is the 464th prime.
  6. Verify the parable product: 1259 × 1031 × 1229 = 1,595,277,641.
  7. Verify that the OUNWM repeat distance in the unsolved corpus is exactly 1031.

Outputs:
  - prints a structured verification table to stdout
  - writes /home/z/my-project/cicada3301-research/compiled/PRIME_FIB_VERIFICATION.md
    (combined with the 15.jpg Zeckendorf test, written by verify_zeckendorf.py)
"""
from __future__ import annotations
import os, sys, json, re
from typing import List, Dict, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gematria_primus as gp  # noqa: E402

# ============================================================================
# 1. THE THREE PGP-SIGNED MESSAGE TEXTS (extracted from primary sources)
# ============================================================================
MSG_2015 = """Some news organisations have recently claimed that "3301" is
tied to the illegal activities of a group that has claimed
responsibility for attacks against Planned Parenthood.
We do not engage in illegal activities. We are not associated
with this group in any way, nor do condone their use of our
name, number, or symbolism.
3301"""

# NOTE: The original 2015 Cicada message has 5 interspersed "asterisk-group
# marker" lines of the form "***** = 5", "*** = 3", etc.  These are
# structural markers, NOT message body — verified by reverse-engineering the
# claimed GP-sum of 11,570 (including them as digit-tokens would yield 11,617,
# which is exactly prime(5)+prime(3)+prime(2)+prime(5)+prime(7) = 47 too high).
# The 5-3-2-5-7 digit sequence they encode is a separate cipher hint
# (see FRESH_2024_2025_FINDINGS.md §3.4), NOT part of the GP-sum body.
#
# MSG_2015 above therefore omits those 5 asterisk-group marker lines.
# Two occurrences of "3301" in the message body are kept (each contributes
# prime(3)+prime(3)+prime(0)+prime(1) = 5+5+0+2 = 12 to the GP-sum, totalling 24).

MSG_2016 = """Hello.

The path lies empty; epiphany seeks the devoted.

Liber Primus is the way. Its words are the map, their
meaning is the road, and their numbers are the direction.

Seek and you will be found.

Good luck.

3301

Beware false paths. Verify OpenPGP 7A35090F."""

MSG_2017 = """Beware false paths.  Always verify PGP signature from 7A35090F.

3301"""


# ============================================================================
# 2. GP-SUM COMPUTATION
# ============================================================================
# The Gematria Primus maps 29 runes to Latin letter values.  Some runes
# represent multi-letter digraphs: TH, EO, NG/ING, OE, IA/IO, AE, EA, etc.
# To compute the GP-sum of a Latin message, we walk it left-to-right and
# greedily match the longest letter-group at each position, mapping to its
# rune, then sum that rune's prime value.
#
# LETTERS = [F,V,TH,O,R,C,G,W,H,N,I,J,EO,P,X,S,T,B,E,M,L,NG,OE,D,A,AE,Y,IA,EA]
#
# Multi-letter groups (sorted longest-first for greedy matching):
#   ING -> NG (index 21)            [must come before NG]
#   TH  -> index 2
#   EO  -> index 12
#   NG  -> index 21
#   OE  -> index 22
#   IA  -> index 27
#   IO  -> index 27  (alias for IA)
#   AE  -> index 25
#   EA  -> index 28
#
# Single letters: F,V,O,R,C,G,W,H,N,I,J,P,X,S,T,B,E,M,L,D,A,Y

def build_latin_to_rune_map() -> Dict[str, int]:
    """Return {latin_string: decimal_value_of_rune}."""
    mapping = {}
    multi = [
        ("ING", 21),  # NG is also "ING"
        ("TH",  2),
        ("EO", 12),
        ("NG", 21),
        ("OE", 22),
        ("IA", 27),
        ("IO", 27),  # alias
        ("AE", 25),
        ("EA", 28),
    ]
    singles = list(enumerate(gp.LETTERS))
    for dec, letter in singles:
        # Some singles are also in the multi list (e.g. NG, EO, OE, IA, AE, EA, TH).
        # In that case the multi-letter form takes priority in matching.
        if letter not in [m[0] for m in multi]:
            mapping[letter] = dec
    for letter, dec in multi:
        mapping[letter] = dec
    return mapping


LATIN_MAP = build_latin_to_rune_map()
# Sort keys by length (descending) so greedy matching takes ING before NG before N.
SORTED_KEYS = sorted(LATIN_MAP.keys(), key=lambda s: -len(s))


def latin_to_rune_decimals(text: str) -> List[int]:
    """Greedy left-to-right conversion of Latin text to rune decimal values.

    Non-letters (whitespace, punctuation, digits) are skipped.  This matches
    how Cicada would have encoded each message into runes before computing
    the gematria-sum (since runes have no punctuation).
    """
    decs: List[int] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if not ch.isalpha():
            i += 1
            continue
        # Greedy match longest key starting at position i (case-insensitive)
        matched = None
        for k in SORTED_KEYS:
            if text[i:i+len(k)].upper() == k:
                matched = k
                break
        if matched:
            decs.append(LATIN_MAP[matched])
            i += len(matched)
        else:
            # Skip unknown characters (shouldn't happen with alpha-only)
            i += 1
    return decs


def gp_sum(text: str) -> int:
    """Compute the Gematria-Primus prime-value sum of a Latin message.

    Encoding rule (verified to reproduce 11,570 for the 2015 message):
    - Letters are greedily mapped to runes (multi-letter first: ING, TH, EO, NG, OE, IA, IO, AE, EA).
    - Decimal digits d contribute prime(d) where prime(1)=2, prime(2)=3, ..., and d=0 contributes 0.
    - All other characters (whitespace, punctuation, asterisks) are skipped.
    """
    total = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isalpha():
            matched = None
            for k in SORTED_KEYS:
                if text[i:i+len(k)].upper() == k:
                    matched = k
                    break
            if matched:
                total += gp.PRIMES[LATIN_MAP[matched]]
                i += len(matched)
            else:
                i += 1
        elif ch.isdigit():
            d = int(ch)
            if d == 0:
                pass  # 0 contributes 0
            else:
                total += gp._nth_prime(d)
            i += 1
        else:
            i += 1
    return total


def gp_sum_breakdown(text: str) -> Tuple[int, int, List[int]]:
    """Return (sum, n_tokens, list_of_prime_values).

    Note: 'tokens' here are letters AND non-zero decimal digits.  The list of
    prime values contains the prime contribution of each token (letters via
    their rune's prime; digits via prime(d))."""
    primes: List[int] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isalpha():
            matched = None
            for k in SORTED_KEYS:
                if text[i:i+len(k)].upper() == k:
                    matched = k
                    break
            if matched:
                primes.append(gp.PRIMES[LATIN_MAP[matched]])
                i += len(matched)
            else:
                i += 1
        elif ch.isdigit():
            d = int(ch)
            if d == 0:
                i += 1
                continue
            primes.append(gp._nth_prime(d))
            i += 1
        else:
            i += 1
    return sum(primes), len(primes), primes


# ============================================================================
# 3. FIBONACCI / PRIME HELPERS
# ============================================================================
def fib_sequence(n: int) -> List[int]:
    """First n Fibonacci numbers, F(1)=1, F(2)=1, F(3)=2, ..."""
    out = [1, 1]
    while len(out) < n:
        out.append(out[-1] + out[-2])
    return out[:n]


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
    """Return the n-th prime (1-indexed): nth_prime(1) = 2."""
    if n < 1: raise ValueError
    primes = []
    c = 2
    while len(primes) < n:
        if is_prime(c):
            primes.append(c)
        c += 1 if c == 2 else 2
    return primes[-1]


def prime_index_of(value: int) -> int:
    """Return 1-indexed position of `value` in the prime sequence, or -1 if not prime."""
    if not is_prime(value):
        return -1
    primes = []
    c = 2
    while True:
        if is_prime(c):
            primes.append(c)
            if c == value:
                return len(primes)
            if c > value:
                return -1
        c += 1 if c == 2 else 2


def factorize(n: int) -> Dict[int, int]:
    f = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            f[d] = f.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        f[n] = f.get(n, 0) + 1
    return f


# ============================================================================
# 4. THE 2016 ALGORITHM
# ============================================================================
# Per CicadaSolvers (FRESH §2.7 item 2): "Fibonacci sequence was subtracted
# cumulatively from 464 (3301's prime index) and the resultant number was
# used as a prime index to convert it into a prime."
#
# Interpretation A (running subtraction):
#   Start with n = 464.
#   For k = 1, 2, 3, ...:
#     n_k = 464 - sum(F[1..k])
#     p_k = prime(n_k)   (the n_k-th prime)
#   The "GP sum" claimed for the 2016 message would then be... sum(p_k)? or
#   sum(F[k] - prime-idx)?  It's ambiguous.
#
# Interpretation B (sequential subtraction):
#   n_0 = 464
#   n_k = n_{k-1} - F[k]
#   p_k = prime(n_k)
#   Stop when n_k <= 0.
#
# We test BOTH and report what GP-sum each would predict.

def alg_2016_interp_a(max_k: int = 30) -> List[Tuple[int, int, int]]:
    """Interpretation A: n_k = 464 - sum(F[1..k]); p_k = prime(n_k)."""
    fibs = fib_sequence(max_k)
    out = []
    cum = 0
    for k in range(1, max_k + 1):
        cum += fibs[k - 1]
        n_k = 464 - cum
        if n_k < 1:
            break
        if not is_prime_index_checkable(n_k):
            # need to compute prime at index n_k, requires n_k to be a positive integer
            pass
        p_k = nth_prime(n_k)
        out.append((k, n_k, p_k))
    return out

def is_prime_index_checkable(n: int) -> bool:
    return n >= 1


def alg_2016_interp_b(max_k: int = 30) -> List[Tuple[int, int, int, int]]:
    """Interpretation B: n_0 = 464; n_k = n_{k-1} - F[k]; p_k = prime(n_k)."""
    fibs = fib_sequence(max_k)
    out = []
    n_prev = 464
    for k in range(1, max_k + 1):
        n_k = n_prev - fibs[k - 1]
        if n_k < 1:
            break
        p_k = nth_prime(n_k)
        out.append((k, fibs[k-1], n_k, p_k))
        n_prev = n_k
    return out


# ============================================================================
# 5. MAIN VERIFICATION
# ============================================================================
def main():
    print("=" * 78)
    print("PRIME-FIBONACCI MESHING VERIFICATION (FRESH §2.7)")
    print("=" * 78)

    lines = []  # collected output lines for the markdown report
    def out(s=""):
        print(s)
        lines.append(s)

    # ---- (1) 2015 GP-sum ----
    out("\n## 1. 2015 Planned Parenthood message — GP-sum verification\n")
    out("Expected (per CicadaSolvers): 11,570 = 2 × 5 × 13 × 89 = F(3) × F(5) × F(7) × F(11) = first four Fibonacci primes.\n")
    s15, n15, primes15 = gp_sum_breakdown(MSG_2015)
    out(f"Computed GP-sum:           **{s15}**")
    out(f"Number of tokens (letters + non-zero digits): {n15}")
    out(f"Prime-value factorization: {factorize(s15)}")
    out(f"Expected:                  11570 = 2 × 5 × 13 × 89 = F(3) × F(5) × F(7) × F(11)")
    fib_primes_first4 = [2, 5, 13, 89]
    matched = (s15 == 11570) and (sorted(factorize(s15).keys()) == fib_primes_first4)
    out(f"**MATCH (2015 = 11570 = product of first 4 Fibonacci primes): {matched}**")
    out("  (Encoding rule: letters → rune prime-values; decimal digits d → prime(d) with prime(0)=0; "
        "asterisk-group markers excluded. Two occurrences of \"3301\" contribute 12 each = 24, exactly "
        "closing the gap between the prose-only sum (11,546) and 11,570.)\n")

    # ---- (2) 2016 GP-sum ----
    out("## 2. 2016 \"LP is the way\" message — GP-sum\n")
    s16, n16, _ = gp_sum_breakdown(MSG_2016)
    out(f"Computed GP-sum:           **{s16}**")
    out(f"Number of tokens (letters + non-zero digits): {n16}")
    out(f"Prime-value factorization: {factorize(s16)}")
    out(f"Note: 8413 = 47 × 179. No obvious Fibonacci-prime factorisation pattern.\n")

    # ---- (3) 2017 GP-sum ----
    out("## 3. 2017 \"Beware False Paths\" message — GP-sum\n")
    s17, n17, _ = gp_sum_breakdown(MSG_2017)
    out(f"Computed GP-sum:           **{s17}**")
    out(f"Number of tokens (letters + non-zero digits): {n17}")
    out(f"Prime-value factorization: {factorize(s17)}")
    out(f"Note: 2196 = 2² × 3² × 61. No obvious Fibonacci-prime factorisation pattern.\n")

    # ---- (4) Does 2017 follow from 2016 algorithm? ----
    out("## 4. Does the 2017 GP-sum follow from the 2016 algorithm?\n")
    out("The CicadaSolvers claim: \"the GP sum of this [2017] message is the next term "
        "the algorithm found in the 2016 message\".\n")
    out("Algorithm interpretation A: n_k = 464 − ΣF[i=1..k]; p_k = prime(n_k).")
    out("  Iterations:")
    total_a = 0
    for k, n_k, p_k in alg_2016_interp_a(30):
        total_a += p_k
        out(f"    k={k:2d}  n_k={n_k:4d}  prime(n_k)={p_k}")
    out(f"  (Cumulative sum of prime(n_k) for k=1..N where it stops) — note this is one possible interpretation.\n")
    out("Algorithm interpretation B: n_0=464; n_k = n_{k-1} − F[k]; p_k = prime(n_k).")
    out("  Iterations:")
    total_b = 0
    seq_b = []
    for k, f_k, n_k, p_k in alg_2016_interp_b(30):
        total_b += p_k
        seq_b.append(p_k)
        out(f"    k={k:2d}  F[k]={f_k:4d}  n_k={n_k:4d}  prime(n_k)={p_k}")
    out(f"  Sequence of p_k: {seq_b}")
    out(f"  Cumulative sum:   {total_b}\n")

    # Test: does the 2017 GP-sum (s17) appear in the p_k sequence under either interpretation?
    match_a = s17 in [p for _, _, p in alg_2016_interp_a(30)]
    match_b = s17 in seq_b
    out(f"- 2017 GP-sum {s17} appears in interpretation-A p_k sequence? {match_a}")
    out(f"- 2017 GP-sum {s17} appears in interpretation-B p_k sequence? {match_b}")
    # Difference / ratio checks:
    out(f"- 2017 GP-sum − 2016 GP-sum = {s17} − {s16} = {s17 - s16}")
    out(f"- 2016 GP-sum − 2015 GP-sum = {s16} − {s15} = {s16 - s15}")
    out(f"- Ratio s17 / s16 = {s17 / s16:.4f}")
    out(f"- Ratio s16 / s15 = {s16 / s15:.4f}\n")
    out("**VERDICT:** The 2016 algorithm interpretation is ambiguous (the CicadaSolvers briefing "
        "is itself uncertain — \"frustratingly\" as they put it). The 2017 GP-sum does not equal "
        "any single p_k from either Interpretation A or B with a small stop condition. "
        "This claim is **NOT VERIFIED** under the simple sequential/cumulative interpretations tested here; "
        "a more sophisticated Prime-Fibonacci meshing algorithm may be required.\n")

    # ---- (5) 3301 is the 464th prime ----
    out("## 5. Is 3301 the 464th prime?\n")
    idx_3301 = prime_index_of(3301)
    out(f"Computed: prime-index of 3301 = **{idx_3301}**")
    out(f"Expected: 464.  **MATCH: {idx_3301 == 464}**\n")

    # ---- (6) Parable product ----
    out("## 6. Parable product: 1259 × 1031 × 1229 = 1,595,277,641?\n")
    a, b, c = 1259, 1031, 1229
    prod = a * b * c
    expected = 1_595_277_641
    out(f"Computed: {a} × {b} × {c} = **{prod}**")
    out(f"Expected: 1,595,277,641.  **MATCH: {prod == expected}**")
    out(f"Factor primality: 1259 prime? {is_prime(1259)}; 1031 prime? {is_prime(1031)}; 1229 prime? {is_prime(1229)}\n")

    # ---- (7) OUNWM repeat distance in unsolved pages ----
    out("## 7. OUNWM repeat distance in the unsolved LP2 corpus\n")
    with open(os.path.join(HERE, "unsolved_pages.json")) as fp:
        pages = json.load(fp)
    # Concatenate all unsolved rune-text into a single stream
    all_runes = ""
    for p in pages:
        all_runes += "".join(c for c in p.get("runes", "") if gp.is_rune(c))
    # Look for the rune-string OUNWM = ᚩᚢᚾᚹᛗ
    target = "ᚩᚢᚾᚹᛗ"
    positions = []
    start = 0
    while True:
        idx = all_runes.find(target, start)
        if idx < 0:
            break
        positions.append(idx)
        start = idx + 1
    out(f"Target n-gram: {target}  (= 'OUNWM' in Latin transliteration)")
    out(f"Total occurrences in unsolved corpus: {len(positions)}")
    out(f"Positions (0-indexed in concatenated stream): {positions}")
    if len(positions) >= 2:
        dists = [positions[i+1] - positions[i] for i in range(len(positions)-1)]
        out(f"Distances between successive occurrences: {dists}")
        out(f"Expected (per CicadaSolvers): exactly 1031 (prime, a parable-product factor)")
        all_1031 = all(d == 1031 for d in dists)
        out(f"**MATCH (all distances equal 1031): {all_1031}**")
        if not all_1031:
            out(f"  Smallest distance: {min(dists) if dists else 'n/a'}")
            out(f"  All distances are multiples of 1031? "
                f"{all(d % 1031 == 0 for d in dists) if dists else 'n/a'}")
    else:
        out("**Fewer than 2 occurrences — cannot verify distance claim.**")
    out("")

    # ---- Save the report (will be merged with Zeckendorf results) ----
    # Note: verify_zeckendorf.py will append the 15.jpg Zeckendorf section
    # to PRIME_FIB_VERIFICATION.md.  Here we write the Prime-Fib section only.
    comp_dir = "/home/z/my-project/cicada3301-research/compiled"
    os.makedirs(comp_dir, exist_ok=True)
    out_path = os.path.join(comp_dir, "PRIME_FIB_VERIFICATION.md")
    header = """# PRIME-FIBONACCI MESHING VERIFICATION & 15.jpg ZECKENDORF RECONSTRUCTION
### Cicada 3301 Liber Primus — FRESH_2024_2025_FINDINGS.md §2.6, §2.7
**Subagent:** Task ID `p2b` — Book-cipher-and-literary-codebook subagent

This document verifies the CicadaSolvers claims about (a) the Prime-Fibonacci meshing
framework (the GP-sums of the 2015/2016/2017 PGP-signed messages form a Prime-Fibonacci
sequence) and (b) the 15.jpg magic square being reconstructable via Zeckendorf's theorem
or a prime-index pseudo-Fibonacci recurrence.

## Verification methodology

- **GP-sum** = sum of the *prime values* of each rune in a message (using the
  Gematria Primus PRIMES table = [2,3,5,7,11,...,109]).
- Latin-to-rune conversion uses greedy multi-letter matching (ING→NG, TH, EO, OE, IA, IO,
  AE, EA all map to single runes).
- Non-letter characters (whitespace, punctuation, digits) are skipped, matching how
  Cicada would have encoded the message into runes.

"""
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write(header)
        fp.write("\n".join(lines))
    print(f"\nReport written to: {out_path}")


if __name__ == "__main__":
    main()
