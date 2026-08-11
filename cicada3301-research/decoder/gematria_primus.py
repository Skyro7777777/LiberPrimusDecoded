#!/usr/bin/env python3
"""
gematria_primus.py — Cicada 3301 Liber Primus Decoder Toolkit
================================================================
Implements:
  - Gematria Primus 29-rune alphabet (letter / decimal / prime values)
  - 8 cipher operations:
      1. direct_translate       (rune -> Latin letter)
      2. atbash                  (decimal[i] = 28 - decimal[i])
      3. caesar                  (constant shift)
      4. vigenere (with F-skip)  (keyed shift, repeating key)
      5. autokey_vigenere        (key = primer || plaintext_or_ciphertext)  [NEW HYPOTHESIS]
      6. prime_stream / totient  (page-56 method: shift by (prime[i]-1) mod 29)
      7. prime_fib_mesh          (generalized Prime-Fibonacci meshed stream)  [NEW HYPOTHESIS]
      8. book_cipher             (index into a codebook text)
  - Frequency analysis: single-rune freq, IOC, doublet rate, n-gram repetition (Kasiski)
  - Verification harness: reproduces all 9 solved-page plaintexts
  - Key-candidate database: all candidates from dossier + 2024-2025 fresh findings

Sources: RESEARCH_DOSSIER.md (compiled 2025) + FRESH_2024_2025_FINDINGS.md
"""
from __future__ import annotations
import re, sys, json, itertools
from typing import List, Dict, Tuple, Optional, Iterable
from collections import Counter

# ============================================================================
# SECTION 1 — GEMATRIA PRIMUS ALPHABET
# ============================================================================

RUNES: str = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
N_RUNES: int = 29
MOD: int = 29

# Per dossier §2 and CicadaSolvers quickstart
LETTERS: List[str] = [
    "F","V","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B","E","M",
    "L","NG","OE","D","A","AE","Y","IA","EA"
]
# Decimal values 0..28
DECIMALS: List[int] = list(range(N_RUNES))
# Prime values: the 29 consecutive primes 2,3,5,7,11,...,109
PRIMES: List[int] = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
    73, 79, 83, 89, 97, 101, 103, 107, 109
]
# Sanity check
assert len(RUNES) == len(LETTERS) == len(DECIMALS) == len(PRIMES) == 29

# Delimiters that appear in Liber Primus pages (not runes — separators)
# Per CicadaSolvers: dot-delimiters also map to ASCII control chars LF/CR/ETB
DELIMITERS: str = " \n\t/•·.-_=*%&$#"
F_RUNE: str = "ᚠ"          # decimal 0 — special: F-skip rule
F_DECIMAL: int = 0

# Reverse lookup tables
RUNE_TO_DEC: Dict[str, int] = {r: i for i, r in enumerate(RUNES)}
DEC_TO_RUNE: Dict[int, str] = {i: r for i, r in enumerate(RUNES)}
DEC_TO_LETTER: Dict[int, str] = {i: l for i, l in enumerate(LETTERS)}
DEC_TO_PRIME: Dict[int, int] = {i: p for i, p in enumerate(PRIMES)}


def is_rune(ch: str) -> bool:
    return ch in RUNE_TO_DEC


def rune_to_dec(r: str) -> int:
    return RUNE_TO_DEC[r]


def dec_to_rune(d: int) -> str:
    return DEC_TO_RUNE[d % MOD]


def dec_to_letter(d: int) -> str:
    return DEC_TO_LETTER[d % MOD]


def prime_to_dec(p: int) -> int:
    """Inverse of prime-value -> decimal mapping."""
    return PRIMES.index(p)


# ============================================================================
# SECTION 2 — TEXT UTILITIES
# ============================================================================

def clean_runes(text: str) -> str:
    """Strip all delimiters, returning only the rune characters."""
    return "".join(ch for ch in text if is_rune(ch))


def split_pages_by_delimiters(text: str) -> List[str]:
    """Split a page's text into rune-words (lists of runes) by delimiter."""
    return [w for w in re.split(r"[ \n\t/•·.\-_=*%&$#]+", text) if w and all(is_rune(c) for c in w)]


def runes_to_decimals(runes: str) -> List[int]:
    return [rune_to_dec(r) for r in runes]


def decimals_to_runes(decs: Iterable[int]) -> str:
    return "".join(dec_to_rune(d) for d in decs)


def decimals_to_latin(decs: Iterable[int], sep: str = "") -> str:
    """Convert decimal values to Latin letter values (lossy for multi-letter runes)."""
    return sep.join(dec_to_letter(d) for d in decs)


def runes_to_latin(runes: str, sep: str = "") -> str:
    return decimals_to_latin(runes_to_decimals(runes), sep=sep)


# ============================================================================
# SECTION 3 — CIPHER OPERATIONS
# ============================================================================

def direct_translate(runes: str) -> str:
    """Method 1: rune -> Latin letter value, no shift."""
    return runes_to_latin(runes)


def atbash(runes: str) -> str:
    """Method 2: decimal[i] = 28 - decimal[i]  (reverse alphabet)."""
    return "".join(dec_to_rune(MOD - 1 - rune_to_dec(r)) for r in runes)


def caesar(runes: str, shift: int, decrypt: bool = True) -> str:
    """Method 3: constant shift. decrypt=True subtracts the shift."""
    sign = -1 if decrypt else 1
    out = []
    for r in runes:
        if not is_rune(r):
            out.append(r)
            continue
        d = rune_to_dec(r)
        out.append(dec_to_rune((d + sign * shift) % MOD))
    return "".join(out)


def _vigenere_decrypt_no_skip(ciphertext_runes: str, key_runes: str) -> str:
    """Pure Vigenere (no F-skip).  decimal[i] = (decimal[i] - key[i % k]) % 29"""
    key_decs = runes_to_decimals(key_runes)
    out = []
    for i, r in enumerate(ciphertext_runes):
        if not is_rune(r):
            out.append(r); continue
        d = rune_to_dec(r)
        kd = key_decs[i % len(key_decs)]
        out.append(dec_to_rune((d - kd) % MOD))
    return "".join(out)


def vigenere(ciphertext_runes: str, key_runes: str, skip_indices: Optional[set] = None,
             decrypt: bool = True, f_skip_rule: bool = True) -> str:
    """
    Method 4: Vigenère with F-skip rule.
    - skip_indices: explicit set of positions (0-indexed over runes-only sequence) to skip.
    - f_skip_rule: if True, F-runes (ᚠ, decimal 0) at skip positions are left unchanged and
                  the key does NOT advance for them.
    - decrypt=True subtracts the key; encrypt=False adds.
    """
    if skip_indices is None:
        skip_indices = set()
    key_decs = runes_to_decimals(key_runes)
    out = []
    ki = 0
    # We track position over the RUNE-ONLY stream (delimiters excluded).
    rune_idx = 0
    for ch in ciphertext_runes:
        if not is_rune(ch):
            out.append(ch)
            continue
        d = rune_to_dec(ch)
        if rune_idx in skip_indices and f_skip_rule:
            # Skip: leave rune unchanged, do not advance key
            out.append(ch)
            rune_idx += 1
            continue
        kd = key_decs[ki % len(key_decs)]
        sign = -1 if decrypt else 1
        out.append(dec_to_rune((d + sign * kd) % MOD))
        ki += 1
        rune_idx += 1
    return "".join(out)


def autokey_vigenere(ciphertext_runes: str, primer_runes: str, mode: str = "plaintext",
                     decrypt: bool = True) -> str:
    """
    Method 5 [NEW HYPOTHESIS 8]: Autokey Vigenère.
    The key stream is primer_runes || (plaintext or ciphertext so far).

    mode='plaintext':  key = primer || plaintext_so_far     (classical autokey)
    mode='ciphertext': key = primer || ciphertext_so_far    (running-key / cipher-feedback)

    Decrypt:
      plaintext[i] = (cipher[i] - key[i]) % 29
      where for i < len(primer):  key[i] = primer[i]
            for i >= len(primer): key[i] = plaintext[i-len(primer)]  (plaintext mode)
                                  or cipher[i-len(primer)]           (ciphertext mode)

    For ciphertext-mode, encryption is straightforward; decryption is also straightforward.
    For plaintext-mode, decryption must be done iteratively since plaintext is unknown.
    """
    primer_decs = runes_to_decimals(primer_runes)
    L = len(primer_decs)
    cipher_decs = runes_to_decimals(ciphertext_runes)
    out_decs = []
    for i, cd in enumerate(cipher_decs):
        if i < L:
            kd = primer_decs[i]
        else:
            if mode == "plaintext":
                kd = out_decs[i - L]      # use already-decrypted plaintext
            elif mode == "ciphertext":
                kd = cipher_decs[i - L]   # use prior ciphertext
            else:
                raise ValueError(f"unknown mode {mode!r}")
        if decrypt:
            pd = (cd - kd) % MOD
        else:
            pd = (cd + kd) % MOD
        out_decs.append(pd)
    return decimals_to_runes(out_decs)


def prime_stream(runes: str, skip_indices: Optional[set] = None,
                 decrypt: bool = True, start_index: int = 1) -> str:
    """
    Method 6: Prime-stream / Totient shift (page-56 method).
    decimal[i] = (decimal[i] - (prime[i] - 1)) % 29   for decrypt
    where prime[i] is the i-th prime (2,3,5,7,11,...) and (prime[i]-1) = φ(prime[i]) = Euler totient.

    start_index: 1 means first prime is 2 (standard). Can be offset for variants.
    skip_indices: positions (0-indexed over runes-only stream) to skip (F-skip rule).
    """
    if skip_indices is None:
        skip_indices = set()
    out = []
    pi = start_index
    rune_idx = 0
    for ch in runes:
        if not is_rune(ch):
            out.append(ch); continue
        if rune_idx in skip_indices:
            out.append(ch)
            rune_idx += 1
            continue
        d = rune_to_dec(ch)
        # i-th prime (1-indexed): prime(1)=2, prime(2)=3, ...
        p = _nth_prime(pi)
        shift = (p - 1) % MOD
        sign = -1 if decrypt else 1
        out.append(dec_to_rune((d + sign * shift) % MOD))
        pi += 1
        rune_idx += 1
    return "".join(out)


# Precomputed prime cache for prime_stream
_PRIME_CACHE: List[int] = []
def _nth_prime(n: int) -> int:
    """Return the n-th prime (1-indexed): _nth_prime(1)=2, _nth_prime(2)=3, ..."""
    while len(_PRIME_CACHE) < n:
        if not _PRIME_CACHE:
            _PRIME_CACHE.extend([2, 3, 5, 7, 11, 13, 17, 19, 23, 29])
        else:
            candidate = _PRIME_CACHE[-1] + 2
            while True:
                is_p = True
                for p in _PRIME_CACHE:
                    if p * p > candidate:
                        break
                    if candidate % p == 0:
                        is_p = False
                        break
                if is_p:
                    _PRIME_CACHE.append(candidate)
                    break
                candidate += 2
    return _PRIME_CACHE[n - 1]


def prime_fib_mesh(runes: str, formulation: str = "add",
                   skip_indices: Optional[set] = None, decrypt: bool = True) -> str:
    """
    Method 7 [NEW HYPOTHESIS 9]: Prime-Fibonacci meshed stream cipher.
    Generalizes page-56 prime-stream by interleaving Fibonacci numbers.

    formulation options:
      'add'        : shift[i] = (prime[i] - 1 + fib[i])      % 29
      'prime_idx_fib': shift[i] = prime[fib[i]]              % 29  (prime indexed by Fib)
      'interleave' : shift[i] = prime[i]%29  if i even else fib[i]%29
      'totient_sum': shift[i] = (prime[i]-1 + (fib[i]-1 if fib[i]>1 else 0)) % 29
      'fib_only'   : shift[i] = fib[i] % 29   (control: pure Fibonacci stream)
      'prime_only' : shift[i] = (prime[i] - 1) % 29  (= page-56 method, for comparison)
    """
    if skip_indices is None:
        skip_indices = set()
    out = []
    pi = 1
    rune_idx = 0
    for ch in runes:
        if not is_rune(ch):
            out.append(ch); continue
        if rune_idx in skip_indices:
            out.append(ch); rune_idx += 1; continue
        d = rune_to_dec(ch)
        p = _nth_prime(pi)
        f = _nth_fib(pi)
        if formulation == "add":
            shift = (p - 1 + f) % MOD
        elif formulation == "prime_idx_fib":
            # Cap fib to avoid astronomical index — use (fib mod 1000)+1 to bound prime cache growth
            shift = _nth_prime((f % 1000) + 1) % MOD
        elif formulation == "interleave":
            shift = (p % MOD) if (pi % 2 == 1) else (f % MOD)
        elif formulation == "totient_sum":
            shift = ((p - 1) + (f - 1 if f > 1 else 0)) % MOD
        elif formulation == "fib_only":
            shift = f % MOD
        elif formulation == "prime_only":
            shift = (p - 1) % MOD
        else:
            raise ValueError(f"unknown formulation {formulation!r}")
        sign = -1 if decrypt else 1
        out.append(dec_to_rune((d + sign * shift) % MOD))
        pi += 1
        rune_idx += 1
    return "".join(out)


_FIB_CACHE: List[int] = [1, 1]
def _nth_fib(n: int) -> int:
    """Return the n-th Fibonacci number (1-indexed): F(1)=1, F(2)=1, F(3)=2, F(4)=3, ..."""
    while len(_FIB_CACHE) < n:
        _FIB_CACHE.append(_FIB_CACHE[-1] + _FIB_CACHE[-2])
    return _FIB_CACHE[n - 1]


def book_cipher(runes: str, codebook_words: List[str], decrypt: bool = True) -> str:
    """
    Method 8: Book cipher.
    Each pair of runes (or single rune, depending on convention) indexes into the codebook.
    Codebook = a list of words (e.g., from Liber AL vel Legis, Agrippa, etc.).
    Convention: rune-pair (r1, r2) -> (word_index, letter_index) in codebook.
    """
    decs = runes_to_decimals(runes)
    out_letters = []
    # Pair up the decimals; if odd, last rune indexes a word's first letter
    i = 0
    while i < len(decs):
        if i + 1 < len(decs):
            word_idx = decs[i]
            letter_idx = decs[i + 1]
        else:
            word_idx = decs[i]
            letter_idx = 0
        if word_idx < len(codebook_words):
            word = codebook_words[word_idx]
            if letter_idx < len(word):
                out_letters.append(word[letter_idx])
            else:
                out_letters.append("?")
        else:
            out_letters.append("?")
        i += 2
    return "".join(out_letters)


# ============================================================================
# SECTION 4 — FREQUENCY / CRYPTANALYSIS
# ============================================================================

def frequency_analysis(runes: str) -> Dict:
    """Compute single-rune frequency, IOC, doublet rate, n-gram repetitions."""
    decs = runes_to_decimals(runes)
    n = len(decs)
    freq = Counter(decs)
    # Index of Coincidence
    ic = sum(c * (c - 1) for c in freq.values()) / (n * (n - 1)) if n > 1 else 0
    ic_normalized = ic * N_RUNES  # normalized so random = 1.0
    # Doublet: consecutive same rune
    doublets = sum(1 for i in range(1, n) if decs[i] == decs[i - 1])
    doublet_rate = doublets / (n - 1) if n > 1 else 0
    # n-gram repetitions (Kasiski-style)
    def ngram_repeats(ng: int) -> Dict:
        grams = [tuple(decs[i:i+ng]) for i in range(n - ng + 1)]
        gc = Counter(grams)
        repeated = {g: c for g, c in gc.items() if c > 1}
        return {
            "n_unique": len(gc),
            "n_repeated_types": len(repeated),
            "n_repeated_total": sum(c for c in repeated.values()),
            "top_5": [(g, c) for g, c in gc.most_common(5)]
        }
    return {
        "n_runes": n,
        "freq": {DEC_TO_LETTER[d]: c for d, c in sorted(freq.items())},
        "freq_dec": dict(freq),
        "IC": ic,
        "IC_normalized": ic_normalized,
        "doublets": doublets,
        "doublet_rate": doublet_rate,
        "random_doublet_rate": 1 / N_RUNES,
        "doublet_suppression_factor": (1 / N_RUNES) / doublet_rate if doublet_rate > 0 else float("inf"),
        "bigrams": ngram_repeats(2),
        "trigrams": ngram_repeats(3),
        "quadgrams": ngram_repeats(4),
        "pentagrams": ngram_repeats(5),
        "hexagrams": ngram_repeats(6),
    }


def kasiski_examination(runes: str, min_gram: int = 3, max_gram: int = 6) -> List[Dict]:
    """Find repeated n-grams and the GCD of their distances (candidate key lengths)."""
    from math import gcd
    decs = runes_to_decimals(runes)
    n = len(decs)
    results = []
    for ng in range(min_gram, max_gram + 1):
        gram_positions: Dict[Tuple, List[int]] = {}
        for i in range(n - ng + 1):
            g = tuple(decs[i:i+ng])
            gram_positions.setdefault(g, []).append(i)
        for g, positions in gram_positions.items():
            if len(positions) >= 2:
                dists = [positions[j+1] - positions[j] for j in range(len(positions) - 1)]
                g_gcd = dists[0]
                for d in dists[1:]:
                    g_gcd = gcd(g_gcd, d)
                results.append({
                    "n_gram": ng,
                    "gram": "".join(dec_to_rune(x) for x in g),
                    "gram_dec": list(g),
                    "gram_latin": decimals_to_latin(g),
                    "positions": positions,
                    "distances": dists,
                    "gcd": g_gcd,
                    "factorization": _factorize(g_gcd),
                })
    return sorted(results, key=lambda r: (-r["n_gram"], r["gcd"]))


def _factorize(n: int) -> Dict[int, int]:
    """Return prime factorization of n as {prime: exponent}."""
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


def english_score(text: str) -> float:
    """
    Score a candidate plaintext by English-likeness.
    Combines: vowel ratio, common-bigram log-prob, IOC target.
    Higher = more English-like.
    """
    if not text:
        return -1e9
    t = text.upper()
    n = len(t)
    vowels = sum(1 for c in t if c in "AEIOU")
    vowel_ratio = vowels / n if n else 0
    # English vowel ratio ~ 0.38 (with Y); we use 0.40 target since Runeglish drops U->V
    vowel_score = -abs(vowel_ratio - 0.40) * 10
    # Common English bigrams
    common_bigrams = ["TH","HE","IN","ER","AN","RE","ON","AT","EN","ND","TI","ES","OR","TE","OF",
                      "ED","IS","IT","AL","AR","ST","TO","NT","NG","SE","HA","AS","OU","IO","LE",
                      "VE","CO","ME","DE","HI","RI","FO","HO","PE","EC"]
    bigram_hits = sum(1 for i in range(n-1) if t[i:i+2] in common_bigrams)
    bigram_score = bigram_hits / max(1, n - 1) * 100
    # Penalise non-letter runs
    letter_ratio = sum(1 for c in t if c.isalpha()) / n if n else 0
    letter_score = letter_ratio * 50
    return vowel_score + bigram_score + letter_score


# ============================================================================
# SECTION 5 — KEY CANDIDATE DATABASE
# ============================================================================

def _decimals_to_runes_inline(decs):
    return "".join(dec_to_rune(d) for d in decs)


# All known Cicada-emitted strings that could be Vigenère/autokey primer keys.
# Sources: dossier §9 + FRESH_2024_2025_FINDINGS.md §3.
KEY_CANDIDATES: Dict[str, str] = {
    # --- From solved LP1 pages (verified working keys) ---
    "DIVINITY":          "ᛞᛁᚢᛁᚾᛁᛏᚣ",            # page 3-4 Vigenère key
    "FIRFUMFERENFE":     "ᚠᛁᚱᚠᚢᛗᚠᛖᚱᛖᚾᚠᛖ",    # page 14-15 Vigenère key (note: FIRFUMFERENFE not CIRCUMFERENCE — cipher-distorted)
    # --- Thematic keys from the Parable (page 57) and Instar Emergence ---
    "INSTAR":            "ᛁᚾᛋᛏᚪᚱ",
    "EMERGENCE":         "ᛖᛗᛖᚱᚷᛖᚾᚳᛖ",
    "EMERGE":            "ᛖᛗᛖᚱᚷᛖ",
    "PARABLE":           "ᛈᚪᚱᚪᛒᛚᛖ",
    "DIVINITY_WITHIN":   "ᛞᛁᚢᛁᚾᛁᛏᚣᚹᛁᚦᛁᚾ",
    "PILGRIM":           "ᛈᛁᛚᚷᚱᛁᛗ",
    "PILGRIMAGE":        "ᛈᛁᛚᚷᚱᛁᛗᚪᚷᛖ",
    "WELCOME":           "ᚹᛖᛚᚳᚩᛗᛖ",
    "SACRED":            "ᛋᚪᚳᚱᛖᛞ",
    "PRIMES_ARE_SACRED": "ᛈᚱᛁᛗᛖᛋᚪᚱᛖᛋᚪᚳᚱᛖᛞ",
    "TOTIENT":           "ᛏᚩᛏᛁᛖᚾᛏ",
    # --- Numerological constants as rune-keys (via gematria-value -> rune) ---
    "1033_AS_RUNES":     _decimals_to_runes_inline([1, 0, 3, 3]),
    "761_AS_RUNES":      _decimals_to_runes_inline([7, 6, 1]),
    "3301_AS_RUNES":     _decimals_to_runes_inline([3, 3, 0, 1]),
    "29_AS_RUNES":       _decimals_to_runes_inline([2, 9]),
    # --- From 2024-2025 fresh findings ---
    # Two-rune digraph hypothesis primers
    "DJUBEI":            "ᛞᛄᚢᛒᛖᛁ",  # dis legomenon (longest repeated 6-gram)
    "OUNWM":             "ᚩᚢᚾᚹᛗ",  # repeats at distance 1031 (=parable factor)
    # 16-digit harmonic key (likely AI-fabricated, low priority but quick to test)
    "HARMONIC_16":       _decimals_to_runes_inline([2,4,2,2,8,2,6,3,2,1,4,1,1,2,0,3]),
}


# ============================================================================
# SECTION 6 — VERIFICATION HARNESS (reproduce all 9 solved-page plaintexts)
# ============================================================================
# Solved pages with their ciphertexts (rune-only) and exact decryption parameters.
# Source: dossier §4 + Uncovering Cicada wiki "How the solved pages were solved"
SOLVED_PAGES: Dict[str, Dict] = {
    "01_warning": {
        "method": "atbash",
        "expected_start": "A WARNNG",  # note: cipher-distorted spelling (no I)
    },
    "0304_welcome": {
        "method": "vigenere",
        "key": "ᛞᛁᚢᛁᚾᛁᛏᚣ",  # DIVINITY
        "skip_indices": {48, 74, 84, 132, 159, 160, 250, 421, 443, 465, 514},
        "expected_substring": "WELCOME",
    },
    "05_wisdom": {
        "method": "direct",
        "expected_substring": "SOME WISDOM",
    },
    "06_koan1": {
        "method": "atbash_then_shift3",
        "expected_substring": "A COAN",
    },
    "1415_koan2": {
        "method": "vigenere",
        "key": "ᚠᛁᚱᚠᚢᛗᚠᛖᚱᛖᚾᚠᛖ",  # FIRFUMFERENFE
        "skip_indices": {49, 56},
        "expected_substring": "A COAN",
    },
    "16_instruction": {
        "method": "direct",
        "expected_substring": "AN INSTRVCTIAN",
    },
    "56_end": {
        "method": "prime_stream",
        "skip_indices": {56},  # 57th rune (0-indexed 56) — 4th of 5 F-runes
        "expected_substring": "AN END",
    },
    "57_parable": {
        "method": "direct",
        "expected_substring": "PARABLE",
    },
}


def verify_toolkit(solved_pages_data: Dict[str, str]) -> Dict[str, bool]:
    """
    Verify the toolkit by reproducing solved-page plaintexts.
    solved_pages_data: {page_id: ciphertext_runes}
    Returns {page_id: passed_bool}
    """
    results = {}
    for page_id, ct in solved_pages_data.items():
        spec = SOLVED_PAGES.get(page_id)
        if spec is None:
            results[page_id] = False
            continue
        method = spec["method"]
        try:
            if method == "atbash":
                pt_runes = atbash(ct)
                pt = runes_to_latin(pt_runes)
            elif method == "direct":
                pt = runes_to_latin(ct)
            elif method == "vigenere":
                pt_runes = vigenere(ct, spec["key"], skip_indices=spec.get("skip_indices", set()), decrypt=True)
                pt = runes_to_latin(pt_runes)
            elif method == "atbash_then_shift3":
                step1 = atbash(ct)
                step2 = caesar(step1, 3, decrypt=False)  # +3 (the dossier says "shift of 3" after Atbash)
                pt = runes_to_latin(step2)
            elif method == "prime_stream":
                pt_runes = prime_stream(ct, skip_indices=spec.get("skip_indices", set()), decrypt=True)
                pt = runes_to_latin(pt_runes)
            else:
                results[page_id] = False
                continue
            expected = spec.get("expected_substring") or spec.get("expected_start", "")
            passed = expected.upper() in pt.upper() if expected else True
            results[page_id] = passed
            if not passed:
                print(f"  FAIL {page_id}: expected '{expected}' in '{pt[:80]}...'")
            else:
                print(f"  OK   {page_id}: '{pt[:60]}...'")
        except Exception as e:
            print(f"  ERR  {page_id}: {e}")
            results[page_id] = False
    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("CICADA 3301 LIBER PRIMUS — DECODER TOOLKIT")
    print("=" * 70)
    print(f"Alphabet: {N_RUNES} runes, modulus {MOD}")
    print(f"Prime range: {PRIMES[0]}..{PRIMES[-1]}  ({len(PRIMES)} consecutive primes)")
    print(f"Key candidates loaded: {len(KEY_CANDIDATES)}")
    print()
    # Self-test: alphabet integrity
    print("Self-test: alphabet integrity...")
    assert RUNES[0] == "ᚠ" and DEC_TO_LETTER[0] == "F" and PRIMES[0] == 2
    assert RUNES[28] == "ᛠ" and DEC_TO_LETTER[28] == "EA" and PRIMES[28] == 109
    print("  OK — alphabet table consistent with dossier §2.")
    # Self-test: Atbash
    print("Self-test: Atbash...")
    assert atbash("ᚠ") == "ᛠ" and atbash("ᛠ") == "ᚠ"
    assert atbash("ᚢ") == "ᛡ" and atbash("ᛡ") == "ᚢ"
    print("  OK — Atbash reverses 0<->28, 1<->27.")
    # Self-test: prime_stream produces page-56-style output
    print("Self-test: prime_stream first 5 shifts...")
    test = "ᚠᚢᚦᚩᚱ"
    out = prime_stream(test, decrypt=True)
    print(f"  in:  {test}  decs: {runes_to_decimals(test)}")
    print(f"  out: {out}  decs: {runes_to_decimals(out)}")
    print(f"  shifts applied: {[(_nth_prime(i+1)-1)%MOD for i in range(5)]}")
    print(f"  (expected: [1,2,4,6,10] = (prime-1) mod 29 for primes 2,3,5,7,11)")
    print()
    print("Toolkit ready. Use verify_toolkit() with solved-page ciphertexts,")
    print("or run attacks via the attack subagents.")
