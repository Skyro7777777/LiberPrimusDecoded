#!/usr/bin/env python3
"""
d4_symmetry_analysis.py — Task p8f
Exhaustive D4 symmetry analysis of page-16 + page-5 magic squares.

D4 group (8 elements):
  e   = identity
  r90 = rotate 90° clockwise
  r180= rotate 180°
  r270= rotate 270° (== r90^3)
  h   = reflect horizontal (top<->bottom)
  v   = reflect vertical (left<->right)
  d   = reflect across main diagonal
  a   = reflect across anti-diagonal

For each symmetry:
  - Apply to 5x5 square -> flattened 25 values
  - mod 29 -> rune sequence (primer)
  - Test Vigenere, autokey-PT, autokey-CT on first 300 runes of unsolved corpus
  - Score with english_score

Then:
  - Prime-index interpretation (find prime-index i with prime(i)=V if V is prime, use i as rune idx)
  - Gematria-Primus letter readings (row-major, col-major, spiral, diag) for each D4 transform
  - 809-center analysis: (V-809) mod 29, (V XOR 809) mod 29
  - Hill-5 cipher: square mod 29 as 5x5 key matrix
  - Page-5 square: repeat all analyses
"""
from __future__ import annotations
import sys, json, itertools
from typing import List, Tuple, Dict
import numpy as np

sys.path.insert(0, "/home/z/my-project/cicada3301-research/decoder")
from gematria_primus import (
    RUNES, N_RUNES, MOD, LETTERS, DECIMALS, DEC_TO_RUNE, RUNE_TO_DEC,
    DEC_TO_LETTER, rune_to_dec, dec_to_rune, is_rune,
    clean_runes, runes_to_decimals, decimals_to_runes, runes_to_latin,
    vigenere, autokey_vigenere, english_score,
)

# ============================================================
# Page-16 magic square (magic constant = 3301)
# ============================================================
P16 = np.array([
    [434, 1311, 312, 278, 966],
    [204, 812, 934, 280, 1071],
    [626, 620, 809, 620, 626],
    [1071, 280, 934, 812, 204],
    [966, 278, 312, 1311, 434],
], dtype=int)

# Page-5 magic square (magic constant = 1033)
# Numbers only (rune-words are mnemonic labels; values are the real cells)
P5 = np.array([
    [272, 138, 341, 131, 151],
    [366, 199, 130, 320,  18],
    [226, 245,  91, 245, 226],
    [ 18, 320, 130, 199, 366],
    [151, 131, 341, 138, 272],
], dtype=int)

# ============================================================
# D4 group operations
# ============================================================
def d4_e(m):      return m.copy()
def d4_r90(m):    return np.rot90(m, k=-1)  # 90° CW
def d4_r180(m):   return np.rot90(m, k=2)
def d4_r270(m):   return np.rot90(m, k=-3)  # 270° CW = 90° CCW
def d4_h(m):      return np.flipud(m)       # reflect horizontal (top<->bottom)
def d4_v(m):      return np.fliplr(m)       # reflect vertical (left<->right)
def d4_d(m):      return m.T                # reflect across main diag
def d4_a(m):      return np.flipud(np.fliplr(m)).T  # anti-diag reflect

D4_OPS = [
    ("e",    d4_e),
    ("r90",  d4_r90),
    ("r180", d4_r180),
    ("r270", d4_r270),
    ("h",    d4_h),
    ("v",    d4_v),
    ("d",    d4_d),
    ("a",    d4_a),
]

# ============================================================
# Reading orders (in addition to D4 transforms)
# ============================================================
def spiral_in(m):
    """Spiral inward starting top-left, going right, down, left, up, ..."""
    out = []
    rows, cols = m.shape
    top, bottom, left, right = 0, rows-1, 0, cols-1
    while top <= bottom and left <= right:
        for j in range(left, right+1): out.append(m[top, j])
        top += 1
        for i in range(top, bottom+1): out.append(m[i, right])
        right -= 1
        if top <= bottom:
            for j in range(right, left-1, -1): out.append(m[bottom, j])
            bottom -= 1
        if left <= right:
            for i in range(bottom, top-1, -1): out.append(m[i, left])
            left += 1
    return np.array(out)

def spiral_out(m):
    """Spiral outward starting from center (CW, expanding layers).
    Robust implementation: enumerate all 25 positions in spiral-out order
    starting at center (2,2), then layer 1 ring, layer 2 ring."""
    rows, cols = m.shape
    cy, cx = rows // 2, cols // 2
    out = [int(m[cy, cx])]
    # Layer 1: ring of 8 cells around center (Manhattan distance 1, then 2)
    # Use a simple BFS-like ring expansion by Manhattan distance, with CCW or CW ordering
    # For a 5x5 grid, layers are: center (1 cell), ring-1 (8 cells), ring-2 (16 cells)
    # We'll generate positions in CW order starting "above" the center
    def ring_positions(layer):
        # Returns list of (r, c) positions for ring at distance `layer` from center
        # CW: top-edge left->right, right-edge top->bottom, bottom-edge right->left, left-edge bottom->top
        positions = []
        # Top edge
        for c in range(cx - layer, cx + layer + 1):
            positions.append((cy - layer, c))
        # Right edge (skip top corner already added)
        for r in range(cy - layer + 1, cy + layer + 1):
            positions.append((r, cx + layer))
        # Bottom edge (skip right corner)
        for c in range(cx + layer - 1, cx - layer - 1, -1):
            positions.append((cy + layer, c))
        # Left edge (skip bottom and top corners)
        for r in range(cy + layer - 1, cy - layer, -1):
            positions.append((r, cx - layer))
        return positions
    for layer in range(1, max(rows, cols)):
        for r, c in ring_positions(layer):
            if 0 <= r < rows and 0 <= c < cols:
                out.append(int(m[r, c]))
    return np.array(out[:rows * cols])

# ============================================================
# Primality helpers
# ============================================================
from sympy import isprime, prime, primepi, primerange

# Precompute primes up to ~1400 (max cell = 1311)
PRIMES_TO_1400 = list(primerange(2, 1400))
PRIME_SET = set(PRIMES_TO_1400)

def prime_index(v):
    """Return 1-based index of prime v. None if v not prime."""
    if v in PRIME_SET:
        return PRIMES_TO_1400.index(v) + 1
    return None

# ============================================================
# Load unsolved corpus
# ============================================================
with open("/home/z/my-project/cicada3301-research/decoder/unsolved_pages.json") as f:
    PAGES = json.load(f)
UNSOVED_PAGES = [p for p in PAGES if not p["is_solved"]]
# Concatenate unsolved runes
CORPUS = "".join(p["runes"] for p in UNSOVED_PAGES)
CORPUS_CLEAN = clean_runes(CORPUS)
print(f"[setup] Loaded {len(UNSOVED_PAGES)} unsolved pages, total {len(CORPUS_CLEAN)} runes")
# First 300 runes
CT300 = CORPUS_CLEAN[:300]

# ============================================================
# Helper: build a rune-primer from a 25-int sequence
# ============================================================
def ints_to_rune_primer(vals: List[int], mod=29) -> str:
    return "".join(dec_to_rune(v % mod) for v in vals)

# ============================================================
# STEP 1 — D4 symmetry × 3 cipher modes × both squares
# ============================================================
def test_d4_primer(primer: str, label: str, square_name: str, results: List[Dict]):
    """Test a primer against CT300 with 3 cipher modes."""
    if len(primer) == 0:
        return
    for mode_name, decrypt_fn in [
        ("vigenere", lambda ct, k: vigenere(ct, k, skip_indices=set(), decrypt=True, f_skip_rule=False)),
        ("autokey_pt", lambda ct, k: autokey_vigenere(ct, k, mode="plaintext", decrypt=True)),
        ("autokey_ct", lambda ct, k: autokey_vigenere(ct, k, mode="ciphertext", decrypt=True)),
    ]:
        try:
            pt_runes = decrypt_fn(CT300, primer)
            pt_lat = runes_to_latin(pt_runes)
            sc = english_score(pt_lat)
            results.append({
                "square": square_name, "transform": label, "mode": mode_name,
                "score": round(sc, 3),
                "snippet": pt_lat[:80],
                "primer": primer,
            })
        except Exception as e:
            results.append({
                "square": square_name, "transform": label, "mode": mode_name,
                "score": -999, "snippet": f"ERR: {e}", "primer": primer,
            })

def run_step1(results: List[Dict]):
    print("\n=== STEP 1: D4 × 3 modes × both squares ===")
    for sq_name, sq in [("page16", P16), ("page5", P5)]:
        for d4_name, d4_op in D4_OPS:
            transformed = d4_op(sq)
            vals = transformed.flatten().tolist()
            primer = ints_to_rune_primer(vals)
            test_d4_primer(primer, f"d4_{d4_name}_rowmod29", sq_name, results)
            # Also spiral-in on transformed
            sp_in = spiral_in(transformed)
            primer_sp = ints_to_rune_primer(sp_in.tolist())
            test_d4_primer(primer_sp, f"d4_{d4_name}_spiral_in", sq_name, results)

# ============================================================
# STEP 2 — Prime-index interpretation
# ============================================================
def run_step2(results: List[Dict]):
    print("\n=== STEP 2: Prime-index interpretation ===")
    for sq_name, sq in [("page16", P16), ("page5", P5)]:
        # For each cell V: if V is prime, find prime_index(V); use that index mod 29 as rune
        # Cells with non-prime values: try (a) skip them, (b) use V mod 29 directly
        flat = sq.flatten()
        # Variant A: only prime cells (skip non-primes)
        prime_cells = [(v, prime_index(v)) for v in flat if v in PRIME_SET]
        primer_a = "".join(dec_to_rune(idx % MOD) for _, idx in prime_cells if idx is not None)
        test_d4_primer(primer_a, f"prime_idx_only", sq_name, results)
        # Variant B: use V mod 29 if V not prime, prime_index(V) mod 29 if V is prime
        primer_b_chars = []
        for v in flat:
            if v in PRIME_SET:
                pi = prime_index(v)
                primer_b_chars.append(dec_to_rune(pi % MOD))
            else:
                primer_b_chars.append(dec_to_rune(v % MOD))
        primer_b = "".join(primer_b_chars)
        test_d4_primer(primer_b, f"prime_idx_or_v_mod29", sq_name, results)
        # Variant C: prime_index(V) mod 29 for all primes; if V not prime, try nearest prime's index
        # Skip for simplicity

        # Also apply D4 transforms to prime-index interpretation
        for d4_name, d4_op in D4_OPS:
            transformed = d4_op(sq).flatten()
            # For each cell: if prime, use index mod 29; else use V mod 29
            chars = []
            for v in transformed:
                if v in PRIME_SET:
                    pi = prime_index(v)
                    chars.append(dec_to_rune(pi % MOD))
                else:
                    chars.append(dec_to_rune(v % MOD))
            primer = "".join(chars)
            test_d4_primer(primer, f"d4_{d4_name}_prime_idx_or_v_mod29", sq_name, results)

# ============================================================
# STEP 3 — Gematria-Primus letter readings
# ============================================================
def run_step3(results: List[Dict]):
    print("\n=== STEP 3: Gematria-Primus letter readings (V mod 29 -> rune -> Latin) ===")
    for sq_name, sq in [("page16", P16), ("page5", P5)]:
        for d4_name, d4_op in D4_OPS:
            transformed = d4_op(sq)
            vals = transformed.flatten().tolist()
            # mod 29 -> rune -> latin letters
            primer = ints_to_rune_primer(vals)
            latin = runes_to_latin(primer)
            # Score the latin as a self-contained message
            sc = english_score(latin)
            results.append({
                "square": sq_name, "transform": f"d4_{d4_name}_latin_reading",
                "mode": "direct", "score": round(sc, 3),
                "snippet": latin, "primer": primer,
            })
        # Also test spiral orders
        for sp_name, sp_fn in [("spiral_in", spiral_in), ("spiral_out", spiral_out)]:
            vals = sp_fn(sq).tolist()
            primer = ints_to_rune_primer(vals)
            latin = runes_to_latin(primer)
            sc = english_score(latin)
            results.append({
                "square": sq_name, "transform": f"{sp_name}_latin_reading",
                "mode": "direct", "score": round(sc, 3),
                "snippet": latin, "primer": primer,
            })

# ============================================================
# STEP 4 — 809-center analysis
# ============================================================
def run_step4(results: List[Dict]):
    print("\n=== STEP 4: 809-center analysis ===")
    center = 809
    for sq_name, sq in [("page16", P16)]:
        # Primality check for all 25 cells
        prime_cells = []
        for i in range(5):
            for j in range(5):
                v = sq[i, j]
                if isprime(v):
                    pi = prime_index(v)
                    prime_cells.append((i, j, v, pi))
        print(f"  [{sq_name}] primes in square ({len(prime_cells)}):")
        for i, j, v, pi in prime_cells:
            print(f"    [{i}][{j}] = {v} (prime #{pi})")

        # Variant A: (V - 809) mod 29 -> rune, read row-major
        for d4_name, d4_op in D4_OPS:
            transformed = d4_op(sq).flatten()
            primer_a = "".join(dec_to_rune((v - center) % MOD) for v in transformed)
            test_d4_primer(primer_a, f"d4_{d4_name}_minus_809_mod29", sq_name, results)
            # Variant B: (V XOR 809) mod 29 -> rune
            primer_b = "".join(dec_to_rune((v ^ center) % MOD) for v in transformed)
            test_d4_primer(primer_b, f"d4_{d4_name}_xor_809_mod29", sq_name, results)
            # Variant C: distance from center (Manhattan) * prime(809_idx=140) - V mod 29
            cy, cx = 2, 2
            # Distance-weighted variant
            primer_c_chars = []
            for i in range(5):
                for j in range(5):
                    pass  # use the transformed flatten instead
            # Variant D: V mod prime_index(809) = V mod 140
            # 140 mod 29 = 140 - 4*29 = 140 - 116 = 24. So same as mod 29 effectively, skip.
            # Variant E: (V mod 809) mod 29 (subtract 809 once if V > 809)
            primer_e = "".join(dec_to_rune((v % center) % MOD) for v in transformed)
            test_d4_primer(primer_e, f"d4_{d4_name}_mod809_then_mod29", sq_name, results)

        # Also test: read the latin letters directly (no cipher applied) for variant A
        for d4_name, d4_op in D4_OPS:
            transformed = d4_op(sq).flatten()
            primer_minus = "".join(dec_to_rune((v - center) % MOD) for v in transformed)
            latin = runes_to_latin(primer_minus)
            sc = english_score(latin)
            results.append({
                "square": sq_name, "transform": f"d4_{d4_name}_minus809_latin",
                "mode": "direct", "score": round(sc, 3),
                "snippet": latin, "primer": primer_minus,
            })
            primer_xor = "".join(dec_to_rune((v ^ center) % MOD) for v in transformed)
            latin2 = runes_to_latin(primer_xor)
            sc2 = english_score(latin2)
            results.append({
                "square": sq_name, "transform": f"d4_{d4_name}_xor809_latin",
                "mode": "direct", "score": round(sc2, 3),
                "snippet": latin2, "primer": primer_xor,
            })

# ============================================================
# STEP 5 — Hill-5 cipher
# ============================================================
def hill5_decrypt(ct_runes: str, M: np.ndarray, decrypt: bool = True) -> str:
    """5x5 Hill cipher. M is 5x5 encryption matrix mod 29.
    If decrypt=True, compute M^-1 and apply it; if False, apply M directly.
    Pads to multiple of 5 with ᚠ.
    """
    M = M % MOD
    if decrypt:
        # Compute inverse mod 29
        try:
            Minv = matrix_inverse_mod_5x5(M, MOD)
        except Exception as e:
            raise ValueError(f"Not invertible: {e}")
    else:
        Minv = M
    decs = runes_to_decimals(clean_runes(ct_runes))
    while len(decs) % 5 != 0:
        decs.append(0)
    out = []
    for i in range(0, len(decs), 5):
        block = np.array(decs[i:i+5], dtype=int)
        out_block = (Minv @ block) % MOD
        out.extend(out_block.tolist())
    return decimals_to_runes(out)

def matrix_inverse_mod_5x5(M: np.ndarray, mod: int) -> np.ndarray:
    """Compute inverse of 5x5 matrix mod p (p prime) using Gauss-Jordan."""
    n = M.shape[0]
    A = np.zeros((n, 2*n), dtype=int)
    A[:, :n] = M % mod
    for i in range(n):
        A[i, n+i] = 1
    for col in range(n):
        # find pivot
        pivot = -1
        for r in range(col, n):
            if A[r, col] % mod != 0:
                pivot = r
                break
        if pivot == -1:
            raise ValueError("singular matrix")
        if pivot != col:
            A[[col, pivot]] = A[[pivot, col]]
        # normalize pivot row
        inv_p = pow(int(A[col, col]), -1, mod)
        A[col] = (A[col] * inv_p) % mod
        # eliminate other rows
        for r in range(n):
            if r != col and A[r, col] != 0:
                factor = A[r, col]
                A[r] = (A[r] - factor * A[col]) % mod
    return A[:, n:].astype(int)

def run_step5(results: List[Dict]):
    print("\n=== STEP 5: Hill-5 cipher (square as 5x5 key mod 29) ===")
    for sq_name, sq in [("page16", P16), ("page5", P5)]:
        # Test each D4 transform as a Hill key
        for d4_name, d4_op in D4_OPS:
            transformed = d4_op(sq)
            M = transformed.copy()
            # Check determinant mod 29
            try:
                det = int(round(np.linalg.det(M))) % MOD
                # The numpy det may not give exact integer; use sympy
                from sympy import Matrix
                M_sym = Matrix(M.tolist())
                det_sym = int(M_sym.det()) % MOD
                if det_sym == 0:
                    results.append({
                        "square": sq_name, "transform": f"d4_{d4_name}_hill5_decrypt",
                        "mode": "hill5", "score": -999,
                        "snippet": f"det=0 mod 29, singular", "primer": "",
                    })
                    results.append({
                        "square": sq_name, "transform": f"d4_{d4_name}_hill5_encrypt",
                        "mode": "hill5", "score": -999,
                        "snippet": f"det=0 mod 29, singular", "primer": "",
                    })
                    continue
                # Decrypt direction (apply M^-1)
                try:
                    pt_runes = hill5_decrypt(CT300[:100], M, decrypt=True)
                    pt_lat = runes_to_latin(pt_runes)
                    sc = english_score(pt_lat)
                    results.append({
                        "square": sq_name, "transform": f"d4_{d4_name}_hill5_decrypt",
                        "mode": "hill5", "score": round(sc, 3),
                        "snippet": pt_lat[:80], "primer": f"det={det_sym}",
                    })
                except Exception as e:
                    results.append({
                        "square": sq_name, "transform": f"d4_{d4_name}_hill5_decrypt",
                        "mode": "hill5", "score": -999,
                        "snippet": f"ERR decrypt: {e}", "primer": "",
                    })
                # Encrypt direction (apply M directly to CT — equivalent to using inverse as decryption)
                try:
                    pt_runes = hill5_decrypt(CT300[:100], M, decrypt=False)
                    pt_lat = runes_to_latin(pt_runes)
                    sc = english_score(pt_lat)
                    results.append({
                        "square": sq_name, "transform": f"d4_{d4_name}_hill5_encrypt",
                        "mode": "hill5", "score": round(sc, 3),
                        "snippet": pt_lat[:80], "primer": f"det={det_sym}",
                    })
                except Exception as e:
                    results.append({
                        "square": sq_name, "transform": f"d4_{d4_name}_hill5_encrypt",
                        "mode": "hill5", "score": -999,
                        "snippet": f"ERR encrypt: {e}", "primer": "",
                    })
            except Exception as e:
                results.append({
                    "square": sq_name, "transform": f"d4_{d4_name}_hill5_any",
                    "mode": "hill5", "score": -999,
                    "snippet": f"ERR: {e}", "primer": "",
                })

# ============================================================
# RUN EVERYTHING
# ============================================================
def main():
    results: List[Dict] = []
    run_step1(results)
    run_step2(results)
    run_step3(results)
    run_step4(results)
    run_step5(results)
    print(f"\n=== ALL DONE — {len(results)} test results ===")
    # Save
    with open("/home/z/my-project/cicada3301-research/decoder/d4_runs/d4_results.json", "w") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)
    # Top 30 by score
    results_sorted = sorted(results, key=lambda r: r.get("score", -999), reverse=True)
    print("\n--- TOP 30 ---")
    for i, r in enumerate(results_sorted[:30]):
        print(f"  {i+1:2d}. {r['square']:7s} | {r['transform']:45s} | {r['mode']:15s} | "
              f"{r['score']:6.2f} | {r['snippet'][:70]}")

    # Random baseline stats
    scs = [r.get("score", -999) for r in results if r.get("score", -999) > -100]
    print(f"\n  Score stats: min={min(scs):.2f}  max={max(scs):.2f}  mean={sum(scs)/len(scs):.2f}  n={len(scs)}")
    print(f"  Tests scoring > 73 (random 99.9th pctile): {sum(1 for s in scs if s > 73)}")
    print(f"  Tests scoring > 74 (random max from prior): {sum(1 for s in scs if s > 74)}")
    print(f"  Tests scoring > 80 (authentic Cicada range): {sum(1 for s in scs if s > 80)}")

if __name__ == "__main__":
    main()
