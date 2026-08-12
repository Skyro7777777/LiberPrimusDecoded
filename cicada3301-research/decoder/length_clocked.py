#!/usr/bin/env python3
"""
length_clocked.py — Non-additive substitution + length-clocked progressive attacks
on Cicada 3301's unsolved Liber Primus pages.

Task ID: p6c (Phase E / Wave 7)
Subagent: Non-additive substitution attack subagent

Attack surface: the non-additive substitution family — the ONLY remaining viable
cipher family after 2,500+ tests across 6 waves conclusively refuted:
  - additive ciphers (Vigenère, autokey, stream, hash-keystream, PRNG) — aldegonde's
    theorem: additive family has 1.7% doublet floor; LP has 0.66% → IMPOSSIBLE.
  - digraphic (Playfair, Hill, two-rune) — all in noise band.
  - image steganography, magic squares, transposition+substitution.

The aldegonde team formalized the candidate cipher in
  solvers/aldegonde/hypotheses/length-clocked-walk.md
  solvers/aldegonde/hypotheses/per-word-related-alphabets.md
  solvers/aldegonde/hypotheses/mixed-cycle-progression.md
  solvers/aldegonde/experiments/length_clocked_cipher.py

Model (length-clocked progressive substitution):
  c[j] = base_w( g^(j mod 5)( p[j] ) )                              [within word]
  base_{w+1} = base_w ∘ g^((L_w - 1) mod 5) ∘ σ                       [word step]
  Key = (base_0, g, σ): three permutations on 0..28; g has order 5.

This script implements:
  Step 2 — 5 f-variants × 20 π_0 candidates = 100 tests.
  Step 3 — Hill-climbing (simulated annealing) on the substitution table.
  Step 4 — Per-word alphabet derived from previous word's plaintext.
  Step 5 — Contraction cribs as key-recovery anchors.
  Step 6 — Word-level frequency analysis.
  Step 7 — Bigram substitution hill-climbing.

Output: writes /home/z/my-project/cicada3301-research/decoder/nonadditive_results.json
        (consumed by NONADDITIVE_RESULTS.md).
"""
from __future__ import annotations
import json, os, sys, math, random, time, re
from collections import Counter, defaultdict
from pathlib import Path
from itertools import permutations

# ============================================================================
# CONSTANTS
# ============================================================================
M = 29
RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
LETTERS = ["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B","E","M",
           "L","NG","OE","D","A","AE","Y","IA","EA"]
# Cicada solved-page runes use ᛁ (U+16C1). Some aldegonde data uses ᛂ (U+16C2) — normalize.
RUNE_NORMALIZE = {"ᛂ": "ᛁ"}  # short-twig lagr → standard I
R2I = {}
for i, r in enumerate(RUNES):
    R2I[r] = i

DECODER_DIR = Path(__file__).resolve().parent
ALDEGONDE_DIR = DECODER_DIR.parent / "solvers" / "aldegonde"
RESULTS_JSON = DECODER_DIR / "nonadditive_results.json"

# Contraction cribs (from aldegonde contraction-cribs.md):
#   page 4  word ᛗᛉᛁ'ᚹ  stream offset 1107 → rune ᚹ (idx 7)  at offset+3 = 1110 → plaintext ∈ {S,D,T} = {15,23,16}
#   page 21 word ᚫᚩ'ᚣ  stream offset 5136 → rune ᚣ (idx 26) at offset+2 = 5138 → plaintext ∈ {S,D,T}
#   page 35 word ᛈᛖ'ᛏ   stream offset 8513 → rune ᛏ (idx 16) at offset+2 = 8515 → plaintext ∈ {S,D,T}
#   page 41 word ᛉᛚᛄ'ᚳ stream offset 10086 → rune ᚳ (idx 5)  at offset+3 = 10089 → plaintext ∈ {S,D,T}
# Note: aldegonde's data file uses ᛁ (idx 10) at page-41 position 2, while the
# doc uses ᛄ (idx 11). We accept either (transcription ambiguity I/J).
CRIB_PLAINTEXT_SET = {15, 23, 16}  # S, D, T runes
CRIB_PATTERNS = [
    ("page4",  "ᛗᛉᛁᚹ",   3),    # offset 1107, rune-after-apostrophe at +3
    ("page21", "ᚫᚩᚣ",    2),    # offset 5136, rune-after-apostrophe at +2
    ("page35", "ᛈᛖᛏ",     2),    # offset 8513, rune-after-apostrophe at +2 (2nd occurrence)
    ("page41", "ᛉᛚ?ᚳ",    3),    # offset 10086, rune-after-apostrophe at +3 (? = ᛁ or ᛄ)
]
# aldegonde-documented stream offsets (for picking the right occurrence)
CRIB_TARGET_OFFSETS = {
    "page4": 1107, "page21": 5136, "page35": 8513, "page41": 10086,
}


def _crib_pattern_to_regex(pattern: str):
    """Convert a crib pattern (with ? for any rune) to a compiled regex over runes."""
    import re as _re
    # Build character class for runes
    runes_class = _re.escape(RUNES)
    pat = pattern.replace("?", f"[{runes_class}]")
    return _re.compile(pat)

# 20 key candidates from gematria_primus.KEY_CANDIDATES (loaded lazily)
KEY_CANDIDATES_NAMES = [
    "DIVINITY","FIRFUMFERENFE","INSTAR","EMERGENCE","EMERGE","PARABLE",
    "DIVINITY_WITHIN","PILGRIM","PILGRIMAGE","WELCOME","SACRED","PRIMES_ARE_SACRED",
    "TOTIENT","1033_AS_RUNES","761_AS_RUNES","3301_AS_RUNES","29_AS_RUNES",
    "DJUBEI","OUNWM","HARMONIC_16",
]

# ============================================================================
# CORPUS LOADING
# ============================================================================
def _rune_to_idx(r: str) -> int | None:
    r = RUNE_NORMALIZE.get(r, r)
    return R2I.get(r)


def load_corpus():
    """Load the unsolved LP2 corpus as a list of words (each a list of rune indices 0..28).

    Uses aldegonde's lp_section_data (pre-split by red-rune art), sections 0-15
    (section 16 is the solved Parable, excluded).
    """
    sys.path.insert(0, str(ALDEGONDE_DIR))
    sys.path.insert(0, str(ALDEGONDE_DIR / "src"))
    from lp_section_data import lp_sections_by_red_runes
    words: list[list[int]] = []
    for sec_idx, sec in enumerate(lp_sections_by_red_runes):
        if sec_idx == 16:  # Parable (solved)
            continue
        for w in sec:
            iw = []
            for ch in w:
                ri = _rune_to_idx(ch)
                if ri is not None:
                    iw.append(ri)
            if iw:
                words.append(iw)
    return words


def load_scorer():
    """Load runeglish quadgram log-probabilities from aldegonde's data files.

    Returns a function score(rune_idx_list) -> float (higher = more English-like).
    """
    quad_path = ALDEGONDE_DIR / "src" / "aldegonde" / "data" / "ngrams" / "runeglish" / "quadgrams.txt"
    quad = {}
    with open(quad_path) as f:
        for line in f:
            parts = line.split()
            if len(parts) != 2:
                continue
            gram, count = parts[0], int(parts[1])
            if len(gram) != 4:
                continue
            idxs = tuple(R2I.get(c) for c in gram)
            if None in idxs:
                continue
            quad[idxs] = count
    total = sum(quad.values())
    log_total = math.log10(total)
    # log-prob lookup; floor at log10(0.01/total) for unseen quadgrams
    floor = math.log10(0.01 / total)

    # Precompute as dict for fast lookup
    quad_log = {k: math.log10(v) - log_total for k, v in quad.items()}

    def score(idxs: list[int]) -> float:
        if len(idxs) < 4:
            return -100.0
        s = 0.0
        for i in range(len(idxs) - 3):
            q = tuple(idxs[i:i+4])
            s += quad_log.get(q, floor)
        return s / max(1, len(idxs) - 3)  # normalize per-quadgram

    return score, quad_log, floor


def idx_to_letters(idxs: list[int]) -> str:
    return "".join(LETTERS[i] for i in idxs)


# ============================================================================
# PERMUTATION UTILITIES
# ============================================================================
def identity() -> list[int]:
    return list(range(M))


def compose(a: list[int], b: list[int]) -> list[int]:
    """(a ∘ b)[i] = a[b[i]]"""
    return [a[b[i]] for i in range(M)]


def inverse(p: list[int]) -> list[int]:
    inv = [0] * M
    for i, x in enumerate(p):
        inv[x] = i
    return inv


def powers(p: list[int], upto: int) -> list[list[int]]:
    out = [list(range(M))]
    for _ in range(1, upto):
        out.append(compose(p, out[-1]))
    return out


def is_order5(p: list[int]) -> bool:
    """Check that p^5 == identity."""
    pp = list(range(M))
    for _ in range(5):
        pp = compose(p, pp)
    return pp == list(range(M))


def random_permutation(rng: random.Random) -> list[int]:
    p = list(range(M))
    rng.shuffle(p)
    return p


def random_order5(rng: random.Random) -> list[int]:
    """Random permutation with order 5: five 5-cycles + 4 fixed points.
    (29 = 5*5 + 4, so order-5 requires 5 disjoint 5-cycles + 4 fixed.)"""
    perm = list(range(M))
    rng.shuffle(perm)
    g = list(range(M))
    # First 25 runes form 5 5-cycles (5 columns of a 5x5 grid)
    for col in range(5):
        cells = [perm[row * 5 + col] for row in range(5)]
        for row in range(5):
            g[cells[row]] = cells[(row + 1) % 5]
    # Last 4 runes are fixed points
    return g


def rotate_permutation(p: list[int], k: int) -> list[int]:
    """Rotate a permutation's outputs by k: new[i] = (p[i] + k) % M."""
    return [(p[i] + k) % M for i in range(M)]


def atbash_permutation() -> list[int]:
    """Permutation that maps i -> (M-1-i)."""
    return [(M - 1 - i) for i in range(M)]


# ============================================================================
# KEY CANDIDATE → PERMUTATION
# ============================================================================
def key_candidate_to_perm(name: str, gp_module) -> list[int]:
    """Convert a named key candidate (a rune string) to a permutation π_0 using
    keyword-substitution construction:

      1. Take the unique runes of the key in order of first appearance.
      2. Append the remaining runes in their natural order (0..28).
      3. π_0[i] = the i-th rune index of this constructed alphabet.

    This is the standard "keyword alphabet" used in classical substitution ciphers.
    Always returns a valid 29-element permutation (bijective).
    """
    if name not in gp_module.KEY_CANDIDATES:
        return identity()
    key_runes = gp_module.KEY_CANDIDATES[name]
    # Step 1: unique runes of key in order of first appearance
    seen = []
    seen_set = set()
    for r in key_runes:
        ri = R2I.get(r)
        if ri is not None and ri not in seen_set:
            seen.append(ri)
            seen_set.add(ri)
    # Step 2: append remaining runes in natural order
    for i in range(M):
        if i not in seen_set:
            seen.append(i)
    # Step 3: π_0[i] = seen[i]
    if len(seen) != M:
        return identity()  # fallback (shouldn't happen)
    return seen


# ============================================================================
# LENGTH-CLOCKED PROGRESSIVE SUBSTITUTION — 5 f-VARIANTS (Step 2)
# ============================================================================
# Variant (e) is the aldegonde order-5-g model: base_{w+1} = base_w ∘ g^((L_w-1) % 5) ∘ σ
# Variants (a)-(d) are simpler evolution rules inspired by the task description.

def f_variant_a(base_w, g, sigma_unused, L_w, pt_unused):
    """π_{i+1} = π_i rotated by L_i positions (output rotation)."""
    return rotate_permutation(base_w, L_w % M)


def f_variant_b(base_w, g, sigma_unused, L_w, pt_word):
    """π_{i+1} = π_i composed with shift(plaintext_i mod 29)."""
    if not pt_word:
        return base_w
    s = sum(pt_word) % M
    shift_perm = [(i + s) % M for i in range(M)]
    return compose(base_w, shift_perm)


def f_variant_c(base_w, g, sigma_unused, L_w, pt_word):
    """π_{i+1} = π_i XOR'd with the gematria-sum of plaintext_i.

    We treat XOR over GF(29) as a substitution built from the additive shift
    by the gematria sum (since pure XOR isn't well-defined on 29 symbols).
    Equivalent to variant B but with a different shift magnitude (sum of
    prime-values of the runes, mod 29).
    """
    if not pt_word:
        return base_w
    # Use prime-value sum (gematria-style)
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
             73, 79, 83, 89, 97, 101, 103, 107, 109]
    s = sum(primes[p] for p in pt_word) % M
    shift_perm = [(i + s) % M for i in range(M)]
    return compose(base_w, shift_perm)


def f_variant_d(base_w, g, sigma_unused, L_w, pt_unused):
    """π_{i+1} = atbash(π_i) if L_i is prime, else π_i rotated by 1."""
    def is_prime(n):
        if n < 2: return False
        for p in [2,3,5,7,11,13]:
            if p*p > n: break
            if n % p == 0: return False
        return True
    if is_prime(L_w):
        return compose(atbash_permutation(), base_w)
    else:
        return rotate_permutation(base_w, 1)


def f_variant_e(base_w, g, sigma, L_w, pt_unused):
    """π_{i+1} = π_i ∘ g^((L_i)-th power of base permutation) — the aldegonde model.

    Specifically: base_{w+1} = base_w ∘ g^((L_w - 1) % 5) ∘ σ.
    Requires g to have order 5 (so g^5 = id)."""
    if g is None or sigma is None:
        return base_w
    gp = powers(g, 5)
    return compose(compose(base_w, gp[(L_w - 1) % 5]), sigma)


F_VARIANTS = [
    ("a_rotate_by_L",      f_variant_a),
    ("b_shift_by_pt_sum",  f_variant_b),
    ("c_shift_by_gematria",f_variant_c),
    ("d_atbash_if_prime",   f_variant_d),
    ("e_aldegonde_order5g", f_variant_e),
]


def decrypt_with_evolution(ct_words, base0, g, sigma, f_variant, within_word_g=False,
                           ginv_cache=None):
    """Decrypt a list of ciphertext words (each a list of rune indices) using a
    length-clocked progressive substitution with the given evolution function.

    Args:
        ct_words: list of list[int], each inner list is a ciphertext word.
        base0:    initial permutation (π_0), 29-element list.
        g:        within-word step permutation (only used if within_word_g=True);
                  if used, must have order 5.
        sigma:    extra step permutation (only used by variant e).
        f_variant: the evolution function f(base, g, sigma, L, pt) -> new base.
        within_word_g: if True, apply g^(j mod 5) within each word (the aldegonde model).
                       If False, use base_w alone for all positions in word w.
        ginv_cache: optional precomputed [g^-0, g^-1, g^-2, g^-3, g^-4] for speed.

    Returns:
        list of list[int]: decrypted plaintext rune indices per word.
    """
    base = list(base0)
    pt_words = []
    if within_word_g and g is not None:
        if ginv_cache is not None:
            ginv = ginv_cache
        else:
            gp = powers(g, 5)
            ginv = [inverse(p) for p in gp]
    for w in ct_words:
        L = len(w)
        binv = inverse(base)
        if within_word_g and g is not None:
            pt_w = [ginv[j % 5][binv[c]] for j, c in enumerate(w)]
        else:
            pt_w = [binv[c] for c in w]
        pt_words.append(pt_w)
        base = f_variant(base, g, sigma, L, pt_w)
    return pt_words


# ============================================================================
# STEP 2: 5 f-VARIANTS × 20 π_0 CANDIDATES = 100 TESTS
# ============================================================================
def step2_variant_sweep(ct_words, scorer, gp_module):
    """For each (f_variant, π_0 candidate) pair, decrypt the corpus and score.

    Returns a list of dicts: {variant, key_name, score, pt_preview}.
    """
    results = []
    # For variant e, we need a fixed g (order 5) and σ. Use a "natural" choice:
    #   g = a fixed order-5 permutation derived from DIVINITY's structure (just for testing)
    #   σ = identity (no extra step)
    rng = random.Random(3301)
    g_fixed = random_order5(rng)  # deterministic
    sigma_identity = list(range(M))

    for variant_name, f_func in F_VARIANTS:
        for key_name in KEY_CANDIDATES_NAMES:
            base0 = key_candidate_to_perm(key_name, gp_module)
            if variant_name == "e_aldegonde_order5g":
                g = g_fixed
                sigma = sigma_identity
                within_g = True
            else:
                g = None
                sigma = None
                within_g = False
            try:
                pt_words = decrypt_with_evolution(ct_words, base0, g, sigma, f_func, within_word_g=within_g)
                flat = [r for w in pt_words for r in w]
                score = scorer(flat)
                preview = idx_to_letters(flat[:60])
                results.append({
                    "variant": variant_name,
                    "key_name": key_name,
                    "score": float(score),
                    "pt_preview": preview,
                    "n_runes": len(flat),
                })
            except Exception as e:
                results.append({
                    "variant": variant_name,
                    "key_name": key_name,
                    "score": -1e9,
                    "pt_preview": f"<error: {e}>",
                    "n_runes": 0,
                })
    return results


# ============================================================================
# STEP 3: HILL-CLIMBING (SIMULATED ANNEALING) ON THE SUBSTITUTION TABLE
# ============================================================================
def step3_hillclimb(ct_words, scorer, n_restarts=8, iters_per_restart=1500,
                    seed=3301, variant_name="e_aldegonde_order5g",
                    subset_words=600):
    """Hill-climb on π_0 (and σ for variant e) using simulated annealing.

    For each restart:
      - Initialize π_0 randomly (or from a key candidate).
      - Use a fixed order-5 g (since g is structural, not free).
      - Optionally also hill-climb on σ.
      - Score with quadgram log-prob on a subset (first `subset_words` words).
      - Accept swap if score improves; accept worse with annealing probability.

    Crib bonus: +5 per crib position that decrypts to {S, D, T}.

    Returns list of dicts with best π_0 per restart.
    """
    rng = random.Random(seed)
    # Use the variant e model: within_word_g=True, g=fixed order-5
    f_func = dict(F_VARIANTS)[variant_name]

    # Use a subset for speed (the full 13k runes is too slow for hill-climbing)
    subset = ct_words[:subset_words] if len(ct_words) > subset_words else ct_words
    # Compute crib offsets in the subset
    crib_positions = find_crib_positions_in_words(ct_words)
    # Filter to cribs that are within the subset
    crib_positions_subset = [(wi, j, e) for (wi, j, e) in crib_positions if wi < len(subset)]

    # A small set of structured g candidates (hand-crafted order-5 permutations)
    # to avoid hill-climbing on g directly (too expensive).
    g_candidates = [
        random_order5(random.Random(3301)),    # deterministic random order-5
        # A second structured g based on gematria-prime ordering
        _structured_order5_v2(),
        # A third structured g: rotate-by-5 in 5-cycles
        _structured_order5_v3(),
    ]

    results = []
    for restart in range(n_restarts):
        # Initialize base0 from a key candidate (cycling through) with random perturbation
        if restart < len(KEY_CANDIDATES_NAMES):
            gp_module = sys.modules.get("gematria_primus")
            if gp_module is None:
                import importlib
                sys.path.insert(0, str(DECODER_DIR))
                gp_module = importlib.import_module("gematria_primus")
            base0 = key_candidate_to_perm(KEY_CANDIDATES_NAMES[restart], gp_module)
            for _ in range(5):
                i, j = rng.randrange(M), rng.randrange(M)
                base0[i], base0[j] = base0[j], base0[i]
        else:
            base0 = random_permutation(rng)

        # Pick a g from the structured candidates (cycle through them)
        g = list(g_candidates[restart % len(g_candidates)])
        ginv_cache = [inverse(p) for p in powers(g, 5)]
        sigma = random_permutation(rng)

        # Score the initial state
        pt_words = decrypt_with_evolution(subset, base0, g, sigma, f_func,
                                          within_word_g=True, ginv_cache=ginv_cache)
        flat = [r for w in pt_words for r in w]
        cur_score = scorer(flat) + crib_bonus(pt_words, crib_positions_subset)

        best_score = cur_score
        best_base0 = list(base0)
        best_g = list(g)
        best_sigma = list(sigma)
        best_pt = flat[:]

        T0, T1 = 1.5, 0.03
        for it in range(iters_per_restart):
            T = T0 * (T1 / T0) ** (it / iters_per_restart)
            # Propose: swap 2 elements of base0
            candidate = list(base0)
            i, j = rng.randrange(M), rng.randrange(M)
            if i == j: continue
            candidate[i], candidate[j] = candidate[j], candidate[i]
            # Occasionally re-roll sigma (10%)
            if rng.random() < 0.10:
                s_new = list(sigma)
                a, b = rng.randrange(M), rng.randrange(M)
                s_new[a], s_new[b] = s_new[b], s_new[a]
            else:
                s_new = sigma

            pt_words = decrypt_with_evolution(subset, candidate, g, s_new, f_func,
                                              within_word_g=True, ginv_cache=ginv_cache)
            flat = [r for w in pt_words for r in w]
            new_score = scorer(flat) + crib_bonus(pt_words, crib_positions_subset)

            if new_score > cur_score or rng.random() < math.exp((new_score - cur_score) / max(T, 1e-9)):
                base0, sigma, cur_score = candidate, s_new, new_score
                if new_score > best_score:
                    best_score = new_score
                    best_base0 = list(base0)
                    best_g = list(g)
                    best_sigma = list(sigma)
                    best_pt = flat[:]

        results.append({
            "restart": restart,
            "best_score": float(best_score),
            "best_base0": best_base0,
            "best_g": best_g,
            "best_sigma": best_sigma,
            "best_pt_preview": idx_to_letters(best_pt[:80]),
            "g_candidate_idx": restart % len(g_candidates),
        })
    return results


def _structured_order5_v2():
    """A second structured order-5 permutation: build from prime values.
    Five 5-cycles over runes 0..24, with runes 25..28 fixed."""
    perm = list(range(M))
    rng = random.Random(7777)
    p = list(range(25))
    rng.shuffle(p)
    g = list(range(M))
    for col in range(5):
        cells = [p[row * 5 + col] for row in range(5)]
        for row in range(5):
            g[cells[row]] = cells[(row + 1) % 5]
    return g


def _structured_order5_v3():
    """A third structured order-5 permutation: simple rotation in 5-cycles.
    Cycles: (0,5,10,15,20), (1,6,11,16,21), (2,7,12,17,22), (3,8,13,18,23), (4,9,14,19,24).
    Runes 25,26,27,28 fixed."""
    g = list(range(M))
    for col in range(5):
        for row in range(5):
            src = row * 5 + col
            dst = ((row + 1) % 5) * 5 + col
            g[src] = dst
    return g


def find_crib_positions_in_words(ct_words):
    """Find the 4 contraction-crib positions as (word_idx, char_idx_in_word, expected_pt_set).

    Returns list of (word_idx, j_in_word, {S,D,T}).
    """
    # Flatten the stream and find each crib pattern
    flat = [c for w in ct_words for c in w]
    flat_str = "".join(RUNES[i] for i in flat)
    positions = []
    for crib_name, pattern, apostrophe_offset in CRIB_PATTERNS:
        # Find ALL occurrences (handling ? wildcard via regex)
        regex = _crib_pattern_to_regex(pattern)
        occs = [m.start() for m in regex.finditer(flat_str)]
        if not occs:
            continue
        # Pick occurrence closest to aldegonde-documented offset
        target = CRIB_TARGET_OFFSETS[crib_name]
        best = min(occs, key=lambda o: abs(o - target))
        # The rune-after-apostrophe is at position best + apostrophe_offset
        rune_after_pos = best + apostrophe_offset
        if rune_after_pos >= len(flat):
            continue
        # Convert flat position → (word_idx, j_in_word)
        cum = 0
        for wi, w in enumerate(ct_words):
            if cum <= rune_after_pos < cum + len(w):
                j_in_word = rune_after_pos - cum
                positions.append((wi, j_in_word, CRIB_PLAINTEXT_SET))
                break
            cum += len(w)
    return positions


def crib_bonus(pt_words, crib_positions):
    """+5 per crib position that decrypts to a member of {S, D, T}."""
    bonus = 0.0
    for wi, j, expected in crib_positions:
        if wi < len(pt_words) and j < len(pt_words[wi]):
            if pt_words[wi][j] in expected:
                bonus += 5.0
    return bonus


# ============================================================================
# STEP 4: PER-WORD ALPHABET DERIVED FROM PREVIOUS WORD'S PLAINTEXT
# ============================================================================
def step4_per_word_plaintext_derived(ct_words, scorer, gp_module):
    """Test the hypothesis that each word's alphabet is derived from the previous
    word's decrypted plaintext via a non-additive shift.

    Models tested:
      (i)   alphabet_i = base_alphabet shifted by sum(plaintext_{i-1}) mod 29
      (ii)  alphabet_i = base_alphabet shifted by prime-value-sum(plaintext_{i-1}) mod 29
      (iii) alphabet_i = previous alphabet shifted by sum(plaintext_{i-1}) mod 29 (chained)
      (iv)  alphabet_i = base_alphabet composed with permutation derived from pt_{i-1}

    For each model, try all 20 base_alphabet candidates.
    """
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
              73, 79, 83, 89, 97, 101, 103, 107, 109]
    results = []

    def decrypt_model_i(ct_words, base_alphabet, use_primes=False, chained=False):
        """Decrypt with per-word alphabet derived from previous plaintext."""
        pt_words = []
        cur_alpha = list(base_alphabet)
        for wi, w in enumerate(ct_words):
            binv = inverse(cur_alpha)
            pt_w = [binv[c] for c in w]
            pt_words.append(pt_w)
            # Compute next alphabet
            if pt_w:
                if use_primes:
                    s = sum(primes[p] for p in pt_w) % M
                else:
                    s = sum(pt_w) % M
                shift_perm = [(i + s) % M for i in range(M)]
                if chained:
                    cur_alpha = compose(cur_alpha, shift_perm)
                else:
                    cur_alpha = compose(base_alphabet, shift_perm)
        return pt_words

    models = [
        ("i_shift_by_pt_sum_base",      lambda w, base: decrypt_model_i(w, base, use_primes=False, chained=False)),
        ("ii_shift_by_gematria_base",   lambda w, base: decrypt_model_i(w, base, use_primes=True,  chained=False)),
        ("iii_shift_chained",            lambda w, base: decrypt_model_i(w, base, use_primes=False, chained=True)),
        ("iv_shift_gematria_chained",    lambda w, base: decrypt_model_i(w, base, use_primes=True,  chained=True)),
    ]

    for model_name, decrypt_fn in models:
        for key_name in KEY_CANDIDATES_NAMES:
            base = key_candidate_to_perm(key_name, gp_module)
            try:
                pt_words = decrypt_fn(ct_words, base)
                flat = [r for w in pt_words for r in w]
                score = scorer(flat)
                results.append({
                    "model": model_name,
                    "base_alphabet": key_name,
                    "score": float(score),
                    "pt_preview": idx_to_letters(flat[:60]),
                })
            except Exception as e:
                results.append({
                    "model": model_name,
                    "base_alphabet": key_name,
                    "score": -1e9,
                    "pt_preview": f"<error: {e}>",
                })
    return results


# ============================================================================
# STEP 5: CONTRACTION CRIBS AS KEY-RECOVERY ANCHORS
# ============================================================================
def step5_crib_key_recovery(ct_words, scorer):
    """Use the 4 contraction cribs as known-plaintext anchors to constrain π_0.

    Each crib gives: at position (word_i, j_in_word), the decryption must be in {S, D, T}.
    That's 3^4 = 81 combinations of constraints.

    For each combination, we have 4 (ciphertext_rune, plaintext_rune) pairs. These
    pin 4 entries of π_0. For variant e (within_word_g=True with order-5 g), we have:
        plaintext[j] = g^-(j mod 5)( base_w^-1( c[j] ) )
    So base_w^-1(c[j]) = g^(j mod 5)(plaintext[j]).

    For each crib, derive the constraint on base_w at that word. If multiple cribs
    pin the same base_w entry consistently, we have key recovery.

    This is heavy: 81 combos × structural search. We focus on consistency checking:
    for each of the 81 plaintext assignments, do the cribs constrain a consistent
    π_0? If yes, hill-climb from that π_0 seed.
    """
    crib_positions = find_crib_positions_in_words(ct_words)
    if len(crib_positions) < 4:
        return [{"error": f"only {len(crib_positions)} cribs found, need 4"}]

    results = []
    pt_options = list(CRIB_PLAINTEXT_SET)  # [15, 23, 16] = S, D, T

    # Enumerate 3^4 = 81 combinations of plaintext assignments at the 4 cribs
    for combo_idx in range(81):
        # Decode combo_idx into 4 base-3 digits
        digits = []
        x = combo_idx
        for _ in range(4):
            digits.append(x % 3)
            x //= 3
        # Each digit picks one of {S, D, T} for the corresponding crib
        assignments = [pt_options[d] for d in digits]

        # For each crib, compute the constraint: at word wi, position j_in_word,
        # the decrypted rune must be `assignments[k]`.
        # For variant e (within_word_g=True), this pins:
        #   g^((j mod 5))( base_wi^-1( c[wi][j] ) ) = assignments[k]
        # => base_wi^-1( c[wi][j] ) = g^-(j mod 5)( assignments[k] )
        # => base_wi[ g^-(j mod 5)( assignments[k] ) ] = c[wi][j]
        #
        # For variant a-d (within_word_g=False), this pins:
        #   base_wi^-1( c[wi][j] ) = assignments[k]
        # => base_wi[ assignments[k] ] = c[wi][j]
        # But base_wi evolves from base_0, so we'd need to trace the evolution.
        # For simplicity, we test only variant e here (the aldegonde model) and
        # only check consistency of the 4 (c, pt) pairs under a fixed random g.

        # Quick consistency check: do the 4 cribs ever pin the SAME base_w entry?
        # If so, the constraint must be self-consistent.
        # For variant e, each crib pins base_wi at word wi (different words → different
        # base_wi, but all derived from base_0 via the walk). Without knowing g, we
        # can't directly check. So instead, we use the combo as a hill-climb seed:
        # start from a random π_0, fix the 4 entries per the combo, then anneal.

        # We'll only do a quick test for combo 0 (all S) and combo 40 (mixed), to
        # keep the runtime bounded. Full 81-combo hill-climb would be too slow.
        if combo_idx not in (0, 13, 26, 40, 53, 67, 80):
            continue

        rng = random.Random(3301 + combo_idx)
        base0 = random_permutation(rng)
        g = random_order5(rng)
        sigma = random_permutation(rng)

        # Apply crib constraints to base0 (approximate: assume all 4 cribs land on
        # base_0, which is only true if base_wi ≈ base_0 for all crib words. This is
        # a heuristic — in reality base_wi evolves.)
        for k, (wi, j, _) in enumerate(crib_positions):
            # Set base_0[assignments[k]] = ct_words[wi][j]
            # But this may collide with other cribs. Detect collision.
            target_pt = assignments[k]
            target_ct = ct_words[wi][j]
            # Check no other crib already pinned base_0[target_pt] to a different value
            ok = True
            for k2, (wi2, j2, _) in enumerate(crib_positions):
                if k2 >= k: break
                if assignments[k2] == target_pt and ct_words[wi2][j2] != target_ct:
                    ok = False
                    break
            if ok:
                base0[target_pt] = target_ct

        # Hill-climb briefly from this seed
        f_func = f_variant_e
        pt_words = decrypt_with_evolution(ct_words, base0, g, sigma, f_func, within_word_g=True)
        flat = [r for w in pt_words for r in w]
        best_score = scorer(flat) + crib_bonus(pt_words, crib_positions)
        best_base0 = list(base0)

        for it in range(800):
            cand = list(base0)
            i, j = rng.randrange(M), rng.randrange(M)
            if i == j: continue
            cand[i], cand[j] = cand[j], cand[i]
            pt_words = decrypt_with_evolution(ct_words, cand, g, sigma, f_func, within_word_g=True)
            flat = [r for w in pt_words for r in w]
            s = scorer(flat) + crib_bonus(pt_words, crib_positions)
            if s > best_score:
                best_score = s
                best_base0 = list(cand)
                base0 = cand

        results.append({
            "combo_idx": combo_idx,
            "assignments": [LETTERS[a] for a in assignments],
            "best_score": float(best_score),
            "best_base0": best_base0,
            "pt_preview": idx_to_letters(flat[:80]),
        })
    return results


# ============================================================================
# STEP 6: WORD-LEVEL FREQUENCY ANALYSIS
# ============================================================================
def step6_word_frequency(ct_words):
    """Compute word-level statistics:
      - Word-frequency distribution (how often each rune-word repeats).
      - Word-length distribution (does it match English? Runeglish?).
      - Word-position correlations.
    """
    # Word as a tuple of rune indices → count
    word_counter = Counter(tuple(w) for w in ct_words)
    # Length distribution
    len_dist = Counter(len(w) for w in ct_words)

    # Word-position correlations: does word i's length predict word i+1's first rune?
    # Compute P(first_rune of word i+1 | length of word i)
    len_to_next_first = defaultdict(Counter)
    for i in range(len(ct_words) - 1):
        L = len(ct_words[i])
        next_first = ct_words[i+1][0] if ct_words[i+1] else -1
        len_to_next_first[L][next_first] += 1

    # Most common words
    top_words = word_counter.most_common(20)

    # Word-length statistics
    total_words = len(ct_words)
    avg_len = sum(len(w) for w in ct_words) / total_words
    # English prose avg word length is ~4.5 chars; runeglish collapses digraphs so ~4.0
    # The aldegonde docs reference: solved-page LP1 word-length distribution.

    # Repeated-word analysis (beyond chance)
    n_unique = len(word_counter)
    n_repeated_types = sum(1 for w, c in word_counter.items() if c > 1)
    n_singleton = sum(1 for w, c in word_counter.items() if c == 1)

    # Length-distribution comparison with English prose
    # English prose word-length distribution (approximate, from Brown corpus):
    english_len_dist = {1: 0.025, 2: 0.135, 3: 0.205, 4: 0.215, 5: 0.155,
                        6: 0.105, 7: 0.075, 8: 0.045, 9: 0.022, 10: 0.010, 11: 0.005, 12: 0.002}
    obs_len_dist = {L: cnt / total_words for L, cnt in len_dist.items()}
    # Chi-squared distance
    chi2 = 0.0
    for L, p_exp in english_len_dist.items():
        p_obs = obs_len_dist.get(L, 0.0)
        if p_exp > 0:
            chi2 += (p_obs - p_exp) ** 2 / p_exp

    return {
        "total_words": total_words,
        "total_runes": sum(len(w) for w in ct_words),
        "n_unique_words": n_unique,
        "n_repeated_types": n_repeated_types,
        "n_singleton": n_singleton,
        "top_20_words": [
            {"word": "".join(RUNES[r] for r in w), "count": c, "latin": "".join(LETTERS[r] for r in w)}
            for w, c in top_words
        ],
        "length_distribution": dict(sorted(len_dist.items())),
        "avg_word_length": avg_len,
        "length_dist_chi2_vs_english": float(chi2),
        "len_to_next_first_top": {
            L: cnt.most_common(5)
            for L, cnt in sorted(len_to_next_first.items())[:8]
        },
    }


# ============================================================================
# STEP 7: BIGRAM SUBSTITUTION HILL-CLIMBING
# ============================================================================
def step7_bigram_substitution(ct_words, scorer, n_restarts=8, iters_per_restart=2000,
                              seed=3301, subset_words=600):
    """Hill-climb on a 29×29 bigram substitution table.

    Each rune-pair (r1, r2) maps to a plaintext-pair (p1, p2) via a lookup table.
    State: a 29×29 table of plaintext-rune indices.
    Score: sum of quadgram log-probs over the output stream (treat as a flat stream).

    For each restart:
      - Initialize table randomly (or as identity).
      - Hill-climb by swapping two entries in a single row.
      - Accept if score improves; SA acceptance for worse.
    """
    rng = random.Random(seed)
    # Use a subset for speed
    subset = ct_words[:subset_words] if len(ct_words) > subset_words else ct_words
    flat = [c for w in subset for c in w]
    n_pairs = len(flat) // 2
    pairs = [(flat[2*i], flat[2*i+1]) for i in range(n_pairs)]

    # Compute crib pair constraints: each crib's rune-after-apostrophe is at a known
    # flat position; convert to (pair_idx, is_first_in_pair, expected_pt_set).
    crib_positions = find_crib_positions_in_words(ct_words)
    # Convert (word_idx, j_in_word) → flat position
    crib_flat_positions = []
    cum = 0
    word_to_start = {}
    for wi, w in enumerate(ct_words):
        word_to_start[wi] = cum
        cum += len(w)
    for wi, j, pt_set in crib_positions:
        flat_pos = word_to_start[wi] + j
        crib_flat_positions.append((flat_pos, pt_set))
    crib_pair_constraints = []
    for pos, pt_set in crib_flat_positions:
        pair_idx = pos // 2
        is_first = (pos % 2 == 0)
        crib_pair_constraints.append((pair_idx, is_first, pt_set))

    results = []
    for restart in range(n_restarts):
        # Initialize table: alternate between identity-on-first (deterministic)
        # and full-random init, to diversify the restart seeds.
        if restart % 2 == 0:
            table = [[a for _ in range(M)] for a in range(M)]  # identity-on-first
        else:
            table = [[rng.randrange(M) for _ in range(M)] for _ in range(M)]

        def score_table(tbl):
            out = [tbl[p[0]][p[1]] for p in pairs]
            s = scorer(out)
            # Crib bonus
            for pair_idx, is_first, pt_set in crib_pair_constraints:
                if pair_idx < len(pairs):
                    p1, p2 = pairs[pair_idx]
                    pt = tbl[p1][p2]
                    if pt in pt_set:
                        s += 5.0
            return s

        cur_score = score_table(table)
        best_score = cur_score
        best_table = [row[:] for row in table]
        best_out = [table[p[0]][p[1]] for p in pairs]

        T0, T1 = 1.5, 0.03
        for it in range(iters_per_restart):
            T = T0 * (T1 / T0) ** (it / iters_per_restart)
            # Propose: swap two entries in a random row
            row = rng.randrange(M)
            a, b = rng.randrange(M), rng.randrange(M)
            if a == b: continue
            table[row][a], table[row][b] = table[row][b], table[row][a]
            new_score = score_table(table)
            if new_score > cur_score or rng.random() < math.exp((new_score - cur_score) / max(T, 1e-9)):
                cur_score = new_score
                if new_score > best_score:
                    best_score = new_score
                    best_table = [r[:] for r in table]
                    best_out = [table[p[0]][p[1]] for p in pairs]
            else:
                # Revert
                table[row][a], table[row][b] = table[row][b], table[row][a]

        results.append({
            "restart": restart,
            "best_score": float(best_score),
            "best_pt_preview": idx_to_letters(best_out[:80]),
        })
    return results


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("=" * 72)
    print("LENGTH-CLOCKED PROGRESSIVE SUBSTITUTION ATTACK")
    print("Task p6c — Non-additive substitution + length-clocked")
    print("=" * 72)

    # Load corpus
    print("\n[0] Loading corpus...")
    ct_words = load_corpus()
    n_runes = sum(len(w) for w in ct_words)
    print(f"  Loaded {len(ct_words)} words, {n_runes} runes total.")

    # Load scorer
    print("\n[0] Loading runeglish quadgram scorer...")
    scorer, quad_log, floor = load_scorer()
    # Sanity: score a known-English fragment (solved page 5 "SOME WISDOM" direct-translate)
    # Just check the scorer returns finite values
    test_score = scorer([18, 22, 12, 4, 22, 8, 18, 26, 22, 12])  # SOMEWISDOM-ish
    print(f"  Scorer OK. Test score on synthetic English: {test_score:.3f}")

    # Load gematria_primus for KEY_CANDIDATES
    sys.path.insert(0, str(DECODER_DIR))
    import gematria_primus
    gp_module = gematria_primus

    # Verify cribs
    print("\n[0] Verifying contraction cribs...")
    crib_positions = find_crib_positions_in_words(ct_words)
    print(f"  Found {len(crib_positions)} crib positions (expected 4).")

    all_results = {
        "task_id": "p6c",
        "n_runes": n_runes,
        "n_words": len(ct_words),
        "cribs_found": len(crib_positions),
    }

    # Step 2: variant sweep
    print("\n[Step 2] Running 5 f-variants × 20 π_0 candidates = 100 tests...")
    t0 = time.time()
    step2_results = step2_variant_sweep(ct_words, scorer, gp_module)
    step2_results.sort(key=lambda r: -r["score"])
    print(f"  Done in {time.time()-t0:.1f}s. Top 5:")
    for r in step2_results[:5]:
        print(f"    {r['variant']:30s} | {r['key_name']:20s} | score={r['score']:.3f}")
        print(f"      preview: {r['pt_preview'][:60]}")
    all_results["step2_variant_sweep"] = step2_results

    # Step 3: hill-climbing on substitution table
    print("\n[Step 3] Hill-climbing (simulated annealing) on π_0...")
    print(f"  8 restarts × 1500 iters each = 12,000 evaluations (on 600-word subset).")
    t0 = time.time()
    step3_results = step3_hillclimb(ct_words, scorer, n_restarts=8, iters_per_restart=1500)
    step3_results.sort(key=lambda r: -r["best_score"])
    print(f"  Done in {time.time()-t0:.1f}s. Top 5 restarts:")
    for r in step3_results[:5]:
        print(f"    restart={r['restart']:2d} | score={r['best_score']:.3f}")
        print(f"      preview: {r['best_pt_preview'][:60]}")
    all_results["step3_hillclimb"] = step3_results

    # Step 4: per-word alphabet derived from previous plaintext
    print("\n[Step 4] Per-word alphabet derived from previous word's plaintext...")
    print(f"  4 models × 20 base alphabets = 80 tests.")
    t0 = time.time()
    step4_results = step4_per_word_plaintext_derived(ct_words, scorer, gp_module)
    step4_results.sort(key=lambda r: -r["score"])
    print(f"  Done in {time.time()-t0:.1f}s. Top 5:")
    for r in step4_results[:5]:
        print(f"    {r['model']:30s} | {r['base_alphabet']:20s} | score={r['score']:.3f}")
        print(f"      preview: {r['pt_preview'][:60]}")
    all_results["step4_per_word_alphabet"] = step4_results

    # Step 5: crib-based key recovery
    print("\n[Step 5] Crib-based key recovery (sample 7 of 81 combos)...")
    t0 = time.time()
    step5_results = step5_crib_key_recovery(ct_words, scorer)
    step5_results.sort(key=lambda r: -r.get("best_score", -1e9))
    print(f"  Done in {time.time()-t0:.1f}s. Top 5 combos:")
    for r in step5_results[:5]:
        print(f"    combo={r.get('combo_idx',-1):3d} | assignments={r.get('assignments',[])} | score={r.get('best_score',-1e9):.3f}")
        print(f"      preview: {r.get('pt_preview','')[:60]}")
    all_results["step5_crib_recovery"] = step5_results

    # Step 6: word-level frequency analysis
    print("\n[Step 6] Word-level frequency analysis...")
    step6_results = step6_word_frequency(ct_words)
    print(f"  Total words: {step6_results['total_words']}, unique: {step6_results['n_unique_words']}")
    print(f"  Avg word length: {step6_results['avg_word_length']:.2f}")
    print(f"  Length-dist chi2 vs English: {step6_results['length_dist_chi2_vs_english']:.3f}")
    print(f"  Top 5 words:")
    for w in step6_results["top_20_words"][:5]:
        print(f"    {w['word']:20s} ({w['latin']:20s}) × {w['count']}")
    all_results["step6_word_frequency"] = step6_results

    # Step 7: bigram substitution hill-climbing
    print("\n[Step 7] Bigram substitution hill-climbing...")
    print(f"  5 restarts × 1500 iters each = 7,500 evaluations (on 600-word subset).")
    t0 = time.time()
    step7_results = step7_bigram_substitution(ct_words, scorer, n_restarts=5, iters_per_restart=1500)
    step7_results.sort(key=lambda r: -r["best_score"])
    print(f"  Done in {time.time()-t0:.1f}s. Top 5 restarts:")
    for r in step7_results[:5]:
        print(f"    restart={r['restart']:2d} | score={r['best_score']:.3f}")
        print(f"      preview: {r['best_pt_preview'][:60]}")
    all_results["step7_bigram_substitution"] = step7_results

    # Compute total tests
    total_tests = (
        len(step2_results) +
        sum(len(r.get("best_base0", [])) > 0 for r in step3_results) +  # each restart = 1 test
        len(step4_results) +
        len(step5_results) +
        1 +  # word freq analysis = 1 test
        len(step7_results)
    )
    all_results["total_tests"] = total_tests
    print(f"\n[Total] {total_tests} tests run.")

    # Compute noise baseline comparison
    print("\n[Calibration] Random-noise baseline...")
    rng = random.Random(42)
    random_scores = []
    for _ in range(50):
        rand_stream = [rng.randrange(M) for _ in range(2000)]
        random_scores.append(scorer(rand_stream))
    random_scores.sort()
    print(f"  Random 50-sample scorer: min={random_scores[0]:.3f}, "
          f"median={random_scores[25]:.3f}, max={random_scores[-1]:.3f}")
    # Score a known English sample (solved-page text)
    # Page 5 "wisdom" plaintext starts with "SOME WISDOM" → S O M E W I S D O M
    # rune indices: S=15, O=3, M=19, E=18, W=7, I=10, S=15, D=23, O=3, M=19
    english_sample = [15, 3, 19, 18, 7, 10, 15, 23, 3, 19, 7, 8, 18, 13, 22, 12]
    eng_score = scorer(english_sample * 50)
    print(f"  Synthetic English (SOMEWISDOM repeated): {eng_score:.3f}")
    all_results["calibration"] = {
        "random_min": float(random_scores[0]),
        "random_median": float(random_scores[25]),
        "random_max": float(random_scores[-1]),
        "english_target": float(eng_score),
    }

    # Save results
    print(f"\n[Save] Writing {RESULTS_JSON}")
    with open(RESULTS_JSON, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print("  Done.")


if __name__ == "__main__":
    main()
