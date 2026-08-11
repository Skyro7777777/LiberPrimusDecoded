#!/usr/bin/env python3
"""
verify_zeckendorf.py
====================
Test the CicadaSolvers claim that the 5×5 magic square on LP1 page 15.jpg
is "reconstructable via Zeckendorf's theorem" and is "the value array for a
prime-index recurrence relation of pseudo-Fibonacci form" (FRESH §2.6).

Note: The dossier does not contain a magic square on LP1 page 15.jpg itself.
The dossier does contain explicit 5×5 magic squares on:
  - LP1 page 5.jpg  ("Some Wisdom"): magic constant = 1033 (prime)
  - LP1 page 16.jpg ("An Instruction"): magic constant = 3301 (prime, Cicada's name)

We test BOTH squares against the Zeckendorf and prime-index recurrence claims.

Zeckendorf's theorem: every positive integer has a unique representation as a
sum of non-consecutive Fibonacci numbers (1, 2, 3, 5, 8, 13, 21, ...).
The interesting test is NOT whether each value has such a representation
(trivially true), but whether the decompositions form a STRUCTURED pattern:
  - Same number of terms per cell?
  - Terms drawn from a restricted Fibonacci subset?
  - Coefficient matrix has low rank / recognizable form?

Also tests the prime-index recurrence hypothesis:
  - a[i][j] = prime(i*5 + j + offset) for some offset?
  - a[i][j] = prime(i*5 + j + offset) + fib(some function)?
  - Linear combination of primes and Fibonacci numbers?

Outputs:
  - prints results to stdout
  - appends a "## 8. 15.jpg Zeckendorf reconstruction test" section to
    /home/z/my-project/cicada3301-research/compiled/PRIME_FIB_VERIFICATION.md
"""
from __future__ import annotations
import os, sys, json
from typing import List, Tuple, Dict, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gematria_primus as gp  # noqa: E402

COMP_DIR = "/home/z/my-project/cicada3301-research/compiled"

# ============================================================================
# 1. THE 5×5 MAGIC SQUARES (extracted from solved_pages.json / dossier §4)
# ============================================================================

# Page 16.jpg magic square (full numeric, from solved_pages.json §74.jpg-16.jpg raw_section)
# Each row sums to 3301 — the magic constant = Cicada's name
PAGE_16_SQUARE = [
    [434, 1311, 312, 278, 966],
    [204, 812, 934, 280, 1071],
    [626, 620, 809, 620, 626],
    [1071, 280, 934, 812, 204],
    [966, 278, 312, 1311, 434],
]

# Page 5.jpg magic square: mixed runes & numbers, but the gematria-prime-sum of
# the rune-words gives the missing numbers. From dossier §4 / solved_pages.json.
# Each row/col/diag sums to 1033 (prime).
# Values verified by direct rune->prime computation:
#   SHADOWS=341, AETHEREAL=366, BUFFERS=199, VOID=130, CARNAL=320,
#   OBSCURA=245, FORM=91, MOBIUS=226, ANALOG=320, MOURNFUL=199, CABAL=341.
PAGE_5_SQUARE = [
    [272, 138, 341, 131, 151],
    [366, 199, 130, 320,  18],
    [226, 245,  91, 245, 226],
    [ 18, 320, 130, 199, 366],
    [151, 131, 341, 138, 272],
]
# Verified: every row, column, and both main diagonals sum to 1033.

SQUARES = {
    "page_5_some_wisdom":  (PAGE_5_SQUARE, 1033),
    "page_16_instruction": (PAGE_16_SQUARE, 3301),
}


# ============================================================================
# 2. ZECKENDORF DECOMPOSITION
# ============================================================================
def fibs_up_to(n: int) -> List[int]:
    """All Fibonacci numbers (1,2,3,5,8,13,...) <= n."""
    out = [1, 2]
    while out[-1] + out[-2] <= n:
        out.append(out[-1] + out[-2])
    return out


def zeckendorf(n: int) -> List[int]:
    """Return the Zeckendorf representation of n as a list of Fibonacci numbers.

    Standard greedy algorithm: pick the largest Fibonacci <= n, subtract, repeat.
    Returns a strictly-decreasing list of non-consecutive Fibonacci numbers
    (using the convention F(1)=1, F(2)=2, F(3)=3, F(4)=5, ...; we exclude the
    leading 1,1 duplication).
    """
    if n <= 0:
        return []
    parts = []
    fibs = fibs_up_to(n)
    # Walk from largest down
    for f in reversed(fibs):
        if f <= n:
            parts.append(f)
            n -= f
    return parts  # already non-consecutive by construction


def is_non_consecutive_fib_set(parts: List[int]) -> bool:
    """Verify that no two parts are consecutive Fibonacci numbers."""
    fibs = fibs_up_to(max(parts) * 2 + 1) if parts else []
    idxs = sorted(fibs.index(p) for p in parts)
    for i in range(len(idxs) - 1):
        if idxs[i+1] - idxs[i] < 2:
            return False
    return True


# ============================================================================
# 3. PRIME-INDEX RECURRENCE TESTS
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
        if is_prime(c):
            primes.append(c)
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


def fib_at(n: int) -> int:
    """n-th Fibonacci (1-indexed): fib_at(1)=1, fib_at(2)=1, fib_at(3)=2, ..."""
    if n < 1: raise ValueError
    a, b = 1, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return a


# ============================================================================
# 4. MAIN TEST
# ============================================================================
def main():
    print("=" * 78)
    print("ZECKENDORF / PRIME-INDEX RECONSTRUCTION TEST (FRESH §2.6)")
    print("=" * 78)

    report_lines: List[str] = []

    def out(s=""):
        print(s)
        report_lines.append(s)

    for sq_name, (square, magic_const) in SQUARES.items():
        out(f"\n### Magic square: {sq_name}")
        out(f"Magic constant (sum of each row/col/diag): {magic_const}\n")

        # Print square
        out("Square:")
        for row in square:
            out("  " + " ".join(f"{v:5d}" for v in row))

        # Verify magic property
        row_sums = [sum(r) for r in square]
        col_sums = [sum(square[i][j] for i in range(5)) for j in range(5)]
        diag1 = sum(square[i][i] for i in range(5))
        diag2 = sum(square[i][4-i] for i in range(5))
        out(f"\nRow sums: {row_sums}")
        out(f"Col sums: {col_sums}")
        out(f"Diag sums: main={diag1}, anti={diag2}")
        is_magic = all(s == magic_const for s in row_sums + col_sums + [diag1, diag2])
        out(f"Is magic (all rows/cols/diags sum to {magic_const}): {is_magic}")

        # ---- Zeckendorf decompositions ----
        out("\nZeckendorf decompositions (each cell as sum of non-consecutive Fibs):")
        all_parts: List[List[int]] = []
        all_n_terms: List[int] = []
        for i, row in enumerate(square):
            for j, v in enumerate(row):
                parts = zeckendorf(v)
                all_parts.append(parts)
                all_n_terms.append(len(parts))
                noncons = is_non_consecutive_fib_set(parts)
                out(f"  cell[{i}][{j}] = {v:5d}  = {' + '.join(str(p) for p in parts):30s}  "
                    f"(n_terms={len(parts)}, non-consecutive={noncons})")
        # Aggregate stats
        from collections import Counter
        term_counts = Counter(all_n_terms)
        out(f"\nTerm-count distribution: {dict(sorted(term_counts.items()))}")
        all_fibs_used = sorted(set(f for parts in all_parts for f in parts))
        out(f"Distinct Fibonacci numbers used across all 25 cells: {all_fibs_used}")
        out(f"Number of distinct Fibs: {len(all_fibs_used)}")
        # Are all 25 cells decompositions restricted to a small Fib subset?
        # The "structured pattern" hypothesis predicts yes (small subset, uniform n_terms).
        # Reality: any positive integer has a Zeckendorf decomposition, but the
        # subset being small (say <= 12 distinct values out of ~16 Fibs <= max_cell)
        # would indicate deliberate selection.

        # ---- Prime-index recurrence tests ----
        out("\nPrime-index recurrence tests:")
        # Test 1: a[i][j] = prime(i*5 + j + offset)?
        for offset in range(-5, 50):
            matches = sum(1 for i in range(5) for j in range(5)
                          if prime_index_of(square[i][j]) == i*5 + j + offset)
            if matches >= 20:
                out(f"  Test 1 (a[i][j] = prime(i*5+j+offset), offset={offset}): "
                    f"{matches}/25 cells match")
        # Default report:
        max_offset_match = max(range(-5, 50),
                              key=lambda o: sum(1 for i in range(5) for j in range(5)
                                                if prime_index_of(square[i][j]) == i*5 + j + o))
        m1 = sum(1 for i in range(5) for j in range(5)
                 if prime_index_of(square[i][j]) == i*5 + j + max_offset_match)
        out(f"  Test 1 (a[i][j] = prime(i*5+j+offset), best offset={max_offset_match}): {m1}/25 cells match")

        # Test 2: a[i][j] = prime(i*5 + j + offset) + fib(k)?
        # For each cell, check if a[i][j] - prime(i*5+j+offset) is a Fibonacci number.
        for offset in [-5, 0, 1, 5, 12, 23, 88, 89]:  # representative offsets
            matches = 0
            for i in range(5):
                for j in range(5):
                    p_idx = i*5 + j + offset
                    if p_idx < 1: continue
                    p = nth_prime(p_idx)
                    diff = square[i][j] - p
                    if diff > 0 and diff in fibs_up_to(2000):
                        matches += 1
            if matches >= 15:
                out(f"  Test 2 (a[i][j] = prime(i*5+j+{offset}) + fib(k)): "
                    f"{matches}/25 cells match")

        # Test 3: are all cells PRIME themselves? (the dossier mentions "primes are sacred")
        n_primes = sum(1 for row in square for v in row if is_prime(v))
        out(f"  Test 3 (all cells prime?): {n_primes}/25 cells are prime")

        # Test 4: is each cell a product of two primes?
        n_semiprime = 0
        for row in square:
            for v in row:
                # find any prime divisor
                d = 2
                factors = []
                n = v
                while d * d <= n:
                    while n % d == 0:
                        factors.append(d); n //= d
                    d += 1
                if n > 1:
                    factors.append(n)
                if len(factors) == 2:
                    n_semiprime += 1
        out(f"  Test 4 (cells that are semiprime p*q?): {n_semiprime}/25")

        # Test 5: are the cells near 3301/5 = 660.2 or 1033/5 = 206.6?
        avg = sum(sum(r) for r in square) / 25
        out(f"  Test 5 (cell-value mean): {avg:.1f}  (vs. magic_const/5 = {magic_const/5:.1f})")

        # Test 6: prime-index of magic constant
        pi_magic = prime_index_of(magic_const)
        out(f"  Test 6 (magic constant {magic_const} prime?): {is_prime(magic_const)}, "
            f"prime index = {pi_magic if pi_magic > 0 else 'N/A'}")

    # ---- Save report ----
    out_path = os.path.join(COMP_DIR, "PRIME_FIB_VERIFICATION.md")
    # Append to existing file
    with open(out_path, "a", encoding="utf-8") as fp:
        fp.write("\n\n")
        fp.write("\n".join(report_lines))
    print(f"\nZeckendorf results appended to: {out_path}")


if __name__ == "__main__":
    main()
