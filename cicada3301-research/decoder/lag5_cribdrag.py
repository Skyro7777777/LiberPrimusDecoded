#!/usr/bin/env python3
"""
Phase E: Lag-5 paired-coincidence crib-drag (Zodiac-340 method)
================================================================
Combines:
  - aldegonde lag-5 attack (already run, max z=+3.56 on page 36)
  - Contraction cribs at pages 4, 21, 35, 41 (4 lone apostrophes)
  - Zodiac-340 transposition + crib-drag
  - Additive cipher with reset:N interrupter (exhaustive N)
  - Custom lag-5 paired-coincidence attack

Treats LP2 as a candidate Zodiac-340-class cipher:
  1. high-order coincidence analysis (aldegonde lag-5)
  2. transposition + substitution hypothesis
  3. crib-drag with known Cicada-emitted plaintext candidates
"""
from __future__ import annotations
import sys, os, json, math, random, statistics
from collections import Counter
from typing import List, Dict, Tuple, Optional, Iterable

# Add decoder path
sys.path.insert(0, '/home/z/my-project/cicada3301-research/decoder')
sys.path.insert(0, '/home/z/my-project/cicada3301-research/solvers/aldegonde/src')

from gematria_primus import (
    RUNES, LETTERS, DECIMALS, PRIMES, MOD, N_RUNES,
    rune_to_dec, dec_to_rune, runes_to_decimals, decimals_to_runes,
    runes_to_latin, is_rune, atbash, caesar, vigenere, autokey_vigenere,
    prime_stream, english_score, KEY_CANDIDATES
)
from aldegonde import c3301

ALDEGONDE_RUNES = c3301.CICADA_ALPHABET
ALDEGONDE_LETTERS = c3301.CICADA_ENGLISH_ALPHABET
R2I = {r: i for i, r in enumerate(ALDEGONDE_RUNES)}
R2I["ᛂ"] = R2I["ᛄ"]  # alias the ngram-table variant J rune

# Use aldegonde's ngram tables for scoring
NGRAM_DIR = '/home/z/my-project/cicada3301-research/solvers/aldegonde/src/aldegonde/data/ngrams/runeglish'

def load_ngrams(fname: str) -> dict:
    table = {}
    path = os.path.join(NGRAM_DIR, fname)
    with open(path, encoding='utf-8') as f:
        for line in f:
            gram, count = line.split()
            table[tuple(R2I[ch] for ch in gram)] = int(count)
    return table

UNIGRAMS = load_ngrams('unigrams.txt')
UNITOTAL = sum(UNIGRAMS.values())
UNIPROB = [UNIGRAMS.get((i,), 1) / UNITOTAL for i in range(29)]

BIGRAMS = load_ngrams('bigrams.txt')
BITOTAL = sum(BIGRAMS.values())

TRIGRAMS = load_ngrams('trigrams.txt')
TRITOTAL = sum(TRIGRAMS.values())
TRILOG = {k: math.log10(v / TRITOTAL) for k, v in TRIGRAMS.items()}
TRIFLOOR = math.log10(0.01 / TRITOTAL)

def trigram_score(seq: List[int]) -> float:
    if len(seq) < 3:
        return 0.0
    total = sum(TRILOG.get(tuple(seq[i:i+3]), TRIFLOOR) for i in range(len(seq) - 2))
    return total / (len(seq) - 2)


# ============================================================================
# DATA LOADING
# ============================================================================
DATA_PATH = '/home/z/my-project/cicada3301-research/solvers/aldegonde/data/page0-58.txt'

def load_pages() -> List[List[int]]:
    """Load 55 unsolved pages (0..54) as rune-index sequences."""
    with open(DATA_PATH, encoding='utf-8') as f:
        raw = f.read()
    pages = []
    for raw_page in raw.split('%')[:56]:
        runes = []
        for ch in raw_page.replace('/', '').replace('\n', ''):
            if ch in R2I:
                runes.append(R2I[ch])
        pages.append(runes)
    return pages

def load_page_marks() -> List[dict]:
    """Load pages with word/sentence starts and apostrophe positions."""
    with open(DATA_PATH, encoding='utf-8') as f:
        raw = f.read()
    pages = []
    for raw_page in raw.split('%')[:56]:
        runes = []
        wstarts = []
        sstarts = []
        apos = []
        new_word = True
        new_sent = True
        for ch in raw_page.replace('/', '').replace('\n', ''):
            if ch in R2I:
                runes.append(R2I[ch])
                wstarts.append(new_word)
                sstarts.append(new_sent)
                new_word = new_sent = False
            elif ch == "'":
                apos.append(len(runes))
            elif ch in '①.,;:!?':
                new_word = True
                if ch in '.④':
                    new_sent = True
        pages.append({'runes': runes, 'wstart': wstarts, 'sstart': sstarts, 'apos': apos})
    return pages

# Solved-page strings (Cicada-emitted, for crib-dragging)
SOLVED_PLAINTEXTS = {
    'welcome':    'WELCOME',
    'warning':    'A WARNING',
    'wisdom':     'SOME WISDOM',
    'koan':       'A COAN',
    'parable':    'PARABLE',
    'anend':      'AN END',
    'instr':      'AN INSTRVCTIAN',
    'sacred':     'THE PRIMES ARE SACRED',
    'noedit':     'DO NOT EDIT',
    'divinity_in':'FIND THE DIVINITY WITHIN',
    'divinity':   'DIVINITY',
    'firfumferenfe':'FIRFUMFERENFE',
}

# Convert each to rune indices (runeglish mapping: drop U->V? Actually it's a known shape)
# Cicada's runeglish rules from solved pages:
#   V->U? Actually the solved-page texts show: DIUINITY for DIVINITY (V omitted).
# We just map each plaintext char to its rune index via the LETTERS table.
LET2IDX = {l: i for i, l in enumerate(ALDEGONDE_LETTERS)}

def plaintext_to_indices(text: str) -> List[int]:
    """Convert English/runeglish plaintext to rune indices using LETTERS table.
    'TH' -> 2, 'EO' -> 12, etc. Multi-letter runeglish units are matched greedily."""
    indices = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == ' ':
            i += 1
            continue
        # try 2-char runeglish unit
        if i + 1 < len(text):
            two = text[i:i+2]
            if two in LET2IDX:
                indices.append(LET2IDX[two])
                i += 2
                continue
        # 1-char
        if ch in LET2IDX:
            indices.append(LET2IDX[ch])
            i += 1
        else:
            i += 1  # skip unknown
    return indices


# ============================================================================
# STEP 3 — CONTRACTION CRIBS AS KNOWN-PLAINTEXT
# ============================================================================
def step3_contraction_cribs():
    """Use the 4 contraction cribs (pages 4, 21, 35, 41) as known-plaintext.

    Each crib is a rune position where the rune must decrypt to one of {S, D, T}.
    For each candidate plaintext (S/D/T), compute the implied keystream segment
    under additive and Beaufort ciphers. Test against:
    - All KEY_CANDIDATES
    - Periodic key with P=5 (lag-5 hypothesis)
    """
    print("\n" + "="*72)
    print("STEP 3 — CONTRACTION CRIBS AS KNOWN-PLAINTEXT")
    print("="*72)
    pages = load_page_marks()
    crib_data = []
    for pi, page in enumerate(pages):
        for ap in page['apos']:
            # The rune AFTER the apostrophe is the contraction tail
            if ap < len(page['runes']):
                tail_cipher_idx = page['runes'][ap]
                tail_cipher_rune = ALDEGONDE_RUNES[tail_cipher_idx]
                tail_cipher_letter = ALDEGONDE_LETTERS[tail_cipher_idx]
                crib_data.append({
                    'page': pi,
                    'local_idx': ap,
                    'cipher_idx': tail_cipher_idx,
                    'cipher_rune': tail_cipher_rune,
                    'cipher_letter': tail_cipher_letter,
                    'candidates': [15, 23, 16],  # S, D, T rune indices
                    'candidate_letters': ['S', 'D', 'T']
                })
    print(f"\nFound {len(crib_data)} contraction cribs:")
    for c in crib_data:
        print(f"  Page {c['page']:2d} idx={c['local_idx']:3d} cipher={c['cipher_rune']}({c['cipher_letter']}) "
              f"→ plaintext ∈ {{S(ᛋ), D(ᛞ), T(ᛏ)}}")

    # Test each candidate as a known-plaintext against each KEY_CANDIDATE
    print("\n--- Testing as known-plaintext against KEY_CANDIDATES ---")
    print("For each crib, compute implied keystream value for each (cipher, plaintext) pair,")
    print("then check if any KEY_CANDIDATE has that value at the corresponding phase.\n")

    best_matches = []
    for key_name, key_runes in KEY_CANDIDATES.items():
        key_decs = runes_to_decimals(key_runes)
        key_len = len(key_decs)
        # Try every possible phase (0..key_len-1) and both additive/Beaufort
        for phase in range(key_len):
            for c in crib_data:
                # global rune position is c['page'] cumulative + c['local_idx']
                # but for periodic key, only phase matters
                k_idx = (phase + c['local_idx']) % key_len
                kv = key_decs[k_idx]
                for cand_pt, cand_letter in zip(c['candidates'], c['candidate_letters']):
                    # Additive: ct = pt + kv => kv = (ct - pt) % 29
                    implied_kv_add = (c['cipher_idx'] - cand_pt) % MOD
                    # Beaufort: ct = kv - pt => kv = (ct + pt) % 29
                    implied_kv_bea = (c['cipher_idx'] + cand_pt) % MOD
                    match_add = (implied_kv_add == kv)
                    match_bea = (implied_kv_bea == kv)
                    if match_add or match_bea:
                        method = 'add' if match_add else 'bea'
                        best_matches.append({
                            'key': key_name,
                            'phase': phase,
                            'page': c['page'],
                            'local_idx': c['local_idx'],
                            'cipher_letter': c['cipher_letter'],
                            'plaintext': cand_letter,
                            'method': method,
                            'key_val_at_pos': kv,
                            'key_rune_at_pos': dec_to_rune(kv),
                        })

    # Print all matches
    if best_matches:
        print(f"  Found {len(best_matches)} (key, phase, page) matches:")
        # Aggregate by key
        by_key = {}
        for m in best_matches:
            k = (m['key'], m['phase'])
            by_key.setdefault(k, []).append(m)
        # Sort by number of matches (more matches = better)
        for (k, ph), ms in sorted(by_key.items(), key=lambda x: -len(x[1])):
            print(f"  key={k:20s} phase={ph:3d} → {len(ms)} crib matches:")
            for m in ms[:8]:
                print(f"    page {m['page']:2d} idx={m['local_idx']:3d} "
                      f"{m['cipher_letter']} → {m['plaintext']} ({m['method']}) key_pos_val={m['key_rune_at_pos']}")
    else:
        print("  NO matches against any KEY_CANDIDATE at any phase.")

    # Now try: under additive Vigenère with P=5 (the lag-5 hypothesis),
    # each crib gives 3 candidate key values at the page-local rune position mod 5.
    # The 4 cribs are on 4 different pages — so the key PHASE depends on the global rune offset.
    print("\n--- Testing as known-plaintext for period-5 Vigenère ---")
    print("For each (cipher rune position mod 5, plaintext in {S,D,T}) compute key candidates:")
    pages_cum_offset = []
    cum = 0
    pages_list = load_pages()
    for p in pages_list:
        pages_cum_offset.append(cum)
        cum += len(p)
    period5_results = {0: [], 1: [], 2: [], 3: [], 4: []}
    for c in crib_data:
        global_offset = pages_cum_offset[c['page']] + c['local_idx']
        phase5 = global_offset % 5
        for cand_pt, cand_letter in zip(c['candidates'], c['candidate_letters']):
            implied_kv_add = (c['cipher_idx'] - cand_pt) % MOD
            implied_kv_bea = (c['cipher_idx'] + cand_pt) % MOD
            period5_results[phase5].append({
                'page': c['page'],
                'local_idx': c['local_idx'],
                'global_offset': global_offset,
                'phase': phase5,
                'cipher_letter': c['cipher_letter'],
                'plaintext': cand_letter,
                'kv_add': implied_kv_add,
                'kv_add_rune': dec_to_rune(implied_kv_add),
                'kv_bea': implied_kv_bea,
                'kv_bea_rune': dec_to_rune(implied_kv_bea),
            })
    print("Phase | Additive key candidates (page idx letter→plaintext)")
    for phase in range(5):
        if not period5_results[phase]:
            print(f"  Phase {phase}: no cribs land here")
            continue
        print(f"  Phase {phase}:")
        for r in period5_results[phase]:
            print(f"    page {r['page']:2d} idx {r['local_idx']:3d} (glob {r['global_offset']:5d}) "
                  f"{r['cipher_letter']} → {r['plaintext']}  | add_k={r['kv_add_rune']}({r['kv_add']}) "
                  f"bea_k={r['kv_bea_rune']}({r['kv_bea']})")
    return best_matches, period5_results, crib_data


# ============================================================================
# STEP 4 — ZODIAC-340 TRANSPOSITION + CRIB-DRAG
# ============================================================================
def transpose_runes(runes: List[int], shape: str, ncols: int, nrows: int) -> List[int]:
    """Apply various transpositions. Input is row-major; output is read in different order."""
    n = len(runes)
    if shape == 'row':  # identity
        return list(runes)
    if shape == 'col':  # columnar read
        out = []
        for c in range(ncols):
            for r in range(nrows):
                idx = r * ncols + c
                if idx < n:
                    out.append(runes[idx])
        return out
    if shape == 'col_rev':  # columnar bottom-to-top
        out = []
        for c in range(ncols):
            for r in range(nrows - 1, -1, -1):
                idx = r * ncols + c
                if idx < n:
                    out.append(runes[idx])
        return out
    if shape == 'diag_down':  # diagonal-down (Zodiac-340 attack vector)
        out = []
        for d in range(nrows + ncols - 1):
            r = 0 if d < ncols else d - ncols + 1
            c = d if d < ncols else ncols - 1
            while r < nrows and c >= 0:
                idx = r * ncols + c
                if idx < n:
                    out.append(runes[idx])
                r += 1
                c -= 1
        return out
    if shape == 'diag_up':  # diagonal-up
        out = []
        for d in range(nrows + ncols - 1):
            r = nrows - 1 if d < ncols else nrows - 1 - (d - ncols + 1)
            c = d if d < ncols else ncols - 1
            while r >= 0 and c >= 0:
                idx = r * ncols + c
                if idx < n:
                    out.append(runes[idx])
                r -= 1
                c -= 1
        return out
    if shape == 'spiral':  # inward spiral
        out = []
        mat = [[None] * ncols for _ in range(nrows)]
        for i, r in enumerate(runes):
            mat[i // ncols][i % ncols] = r
        top, bot, left, right = 0, nrows - 1, 0, ncols - 1
        while top <= bot and left <= right:
            for c in range(left, right + 1):
                if mat[top][c] is not None: out.append(mat[top][c])
            top += 1
            for r in range(top, bot + 1):
                if mat[r][right] is not None: out.append(mat[r][right])
            right -= 1
            if top <= bot:
                for c in range(right, left - 1, -1):
                    if mat[bot][c] is not None: out.append(mat[bot][c])
                bot -= 1
            if left <= right:
                for r in range(bot, top - 1, -1):
                    if mat[r][left] is not None: out.append(mat[r][left])
                left += 1
        return out
    if shape == 'zigzag':  # boustrophedon
        out = []
        for r in range(nrows):
            row_run = [runes[r * ncols + c] for c in range(ncols) if r * ncols + c < n]
            if r % 2 == 1:
                row_run = row_run[::-1]
            out.extend(row_run)
        return out
    return list(runes)

def step4_zodiac_transposition_cribdrag():
    """Zodiac-340 attack: transpose + crib-drag with known plaintext candidates."""
    print("\n" + "="*72)
    print("STEP 4 — ZODIAC-340 TRANSPOSITION + CRIB-DRAG")
    print("="*72)
    pages = load_pages()
    cribs = {name: plaintext_to_indices(pt) for name, pt in SOLVED_PLAINTEXTS.items()}
    print(f"\nLoaded {len(cribs)} cribs:")
    for name, idxs in cribs.items():
        print(f"  {name:20s} ({SOLVED_PLAINTEXTS[name]:30s}) → {len(idxs)} runes")

    # For each page, try transpositions: row, col, col_rev, diag_down, diag_up, spiral, zigzag
    # For each transposition, try each cipher method:
    #   - Atbash + crib-drag
    #   - Direct (substitution) + crib-drag
    #   - Vigenère with each KEY_CANDIDATE + crib-drag
    #   - Additive period-5 with crib-drag (each of 5 phase shifts)
    #   - Autokey PT/CT with each KEY_CANDIDATE

    # For each crib, slide across the (transposed, cipher-method-applied) text and check:
    #   - Does the crib match the text at any offset?
    #   - Score by exact-match count

    transposition_shapes = ['row', 'col', 'col_rev', 'diag_down', 'diag_up', 'spiral', 'zigzag']

    # To save time, only test first 8 pages and limit transpositions
    n_pages = min(8, len(pages))
    print(f"\nTesting transpositions × cipher methods × cribs on first {n_pages} pages...")
    print(f"(To save time; full sweep would be 55 × 7 × ~30 × ~15 = 173k tests)")

    hits = []
    tested = 0
    for pi in range(n_pages):
        runes = pages[pi]
        n = len(runes)
        # Try various grid dimensions (factor of n)
        # For 8 pages, sample a few shapes per page
        for shape in transposition_shapes:
            for ncols in [13, 14, 15, 19, 20, 25, 29, 56]:
                nrows = (n + ncols - 1) // ncols
                if nrows < 2 or ncols * (nrows - 1) > n:
                    continue
                if ncols * (nrows - 2) > n:  # need at least 2 full rows
                    continue
                t_runes = transpose_runes(runes, shape, ncols, nrows)
                if len(t_runes) != n:
                    continue
                # Apply cipher method, then crib-drag
                for method_name, method_fn in [
                    ('direct', lambda r: r),
                    ('atbash', lambda r: [(MOD - x - 1) if False else (MOD - 1 - x) % MOD for x in r]),
                ]:
                    pt_runes = method_fn(t_runes)
                    pt_letters = ''.join(ALDEGONDE_LETTERS[x] for x in pt_runes)
                    # crib-drag each crib across all positions
                    for crib_name, crib_indices in cribs.items():
                        crib_str = SOLVED_PLAINTEXTS[crib_name]
                        crib_len = len(crib_indices)
                        if crib_len > n:
                            continue
                        for offset in range(n - crib_len + 1):
                            match_count = sum(1 for i in range(crib_len) if pt_runes[offset + i] == crib_indices[i])
                            if match_count >= max(3, crib_len - 2):
                                hits.append({
                                    'page': pi,
                                    'shape': shape,
                                    'ncols': ncols,
                                    'method': method_name,
                                    'crib': crib_name,
                                    'offset': offset,
                                    'match': match_count,
                                    'crib_len': crib_len,
                                    'text_window': pt_letters[offset:offset + crib_len + 5]
                                })
                            tested += 1
        if pi == 0:
            print(f"  Tested {tested} (page, trans, method, crib, offset) tuples so far...")

    print(f"\nTotal tested: {tested}")
    print(f"Hits (>=3 char match): {len(hits)}")
    if hits:
        # Sort by match count
        hits.sort(key=lambda x: -x['match'])
        print("Top 15 hits:")
        for h in hits[:15]:
            print(f"  page {h['page']:2d} {h['shape']:10s} cols={h['ncols']:3d} {h['method']:7s} "
                  f"crib={h['crib']:18s} off={h['offset']:4d} match={h['match']}/{h['crib_len']} "
                  f"text={h['text_window']}")
    else:
        print("  NO hits above threshold.")

    # Also: For each page, try Vigenère with each KEY_CANDIDATE, then transpose, then crib-drag
    print("\n--- Vigenère + transposition + crib-drag (1 key, first 4 pages) ---")
    v_hits = []
    for pi in range(min(4, len(pages))):
        runes = pages[pi]
        n = len(runes)
        for key_name, key_runes in list(KEY_CANDIDATES.items())[:10]:
            key_decs = runes_to_decimals(key_runes)
            key_len = len(key_decs)
            if key_len == 0:
                continue
            # Apply Vigenère decryption
            pt_decs = [(runes[i] - key_decs[i % key_len]) % MOD for i in range(n)]
            # Then transpose
            for shape in transposition_shapes:
                for ncols in [13, 14, 19, 20, 25]:
                    nrows = (n + ncols - 1) // ncols
                    if nrows < 2:
                        continue
                    t_runes = transpose_runes(pt_decs, shape, ncols, nrows)
                    pt_letters = ''.join(ALDEGONDE_LETTERS[x] for x in t_runes)
                    # crib-drag
                    for crib_name, crib_indices in cribs.items():
                        crib_len = len(crib_indices)
                        if crib_len > n:
                            continue
                        for offset in range(n - crib_len + 1):
                            match_count = sum(1 for i in range(crib_len) if t_runes[offset + i] == crib_indices[i])
                            if match_count >= max(4, crib_len - 2):
                                v_hits.append({
                                    'page': pi,
                                    'key': key_name,
                                    'shape': shape,
                                    'ncols': ncols,
                                    'crib': crib_name,
                                    'offset': offset,
                                    'match': match_count,
                                    'crib_len': crib_len,
                                    'text': pt_letters[max(0, offset-3):offset + crib_len + 3]
                                })
    print(f"Vigenère+transposition hits (>=4 char): {len(v_hits)}")
    if v_hits:
        v_hits.sort(key=lambda x: -x['match'])
        for h in v_hits[:15]:
            print(f"  page {h['page']:2d} key={h['key']:18s} {h['shape']:10s} cols={h['ncols']:3d} "
                  f"crib={h['crib']:14s} off={h['offset']:4d} match={h['match']}/{h['crib_len']} "
                  f"text={h['text']}")
    return hits, v_hits


# ============================================================================
# STEP 5 — ADDITIVE CIPHER WITH RESET:N INTERRUPTER (EXHAUSTIVE)
# ============================================================================
def step5_additive_reset():
    """Test additive cipher with reset:N interrupter for all Cicada-significant N."""
    print("\n" + "="*72)
    print("STEP 5 — ADDITIVE CIPHER WITH RESET:N INTERRUPTER (EXHAUSTIVE)")
    print("="*72)
    pages = load_pages()
    # Cicada-significant N values
    N_values = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 56, 95, 1033, 3301, 109, 113, 127]
    print(f"Testing N values: {N_values}")
    print(f"Testing {len(KEY_CANDIDATES)} KEY_CANDIDATES per (page, N) combination\n")

    results = []
    for pi, runes in enumerate(pages):
        n = len(runes)
        for N in N_values:
            if N > n:
                continue
            for key_name, key_runes in KEY_CANDIDATES.items():
                key_decs = runes_to_decimals(key_runes)
                key_len = len(key_decs)
                if key_len == 0:
                    continue
                # Apply additive with reset:N
                # Key phase resets to 0 every N runes
                pt_decs = []
                ki = 0
                for i, r in enumerate(runes):
                    if i > 0 and i % N == 0:
                        ki = 0
                    pt_decs.append((r - key_decs[ki % key_len]) % MOD)
                    ki += 1
                pt_str = ''.join(ALDEGONDE_LETTERS[x] for x in pt_decs)
                # Score: trigram log-prob
                tri = trigram_score(pt_decs)
                # Score: english_score on letter string
                eng = english_score(pt_str)
                results.append({
                    'page': pi,
                    'N': N,
                    'key': key_name,
                    'trigram': tri,
                    'english': eng,
                    'snippet': pt_str[:60]
                })

    # Sort by trigram score
    results.sort(key=lambda x: -x['trigram'])
    print(f"Tested {len(results)} (page, N, key) combinations.")
    print(f"\nTop 10 by trigram score:")
    for r in results[:10]:
        print(f"  page {r['page']:2d} N={r['N']:4d} key={r['key']:20s} "
              f"tri={r['trigram']:+6.3f} eng={r['english']:+6.2f}  {r['snippet']}")
    print(f"\nTop 10 by english score:")
    results.sort(key=lambda x: -x['english'])
    for r in results[:10]:
        print(f"  page {r['page']:2d} N={r['N']:4d} key={r['key']:20s} "
              f"tri={r['trigram']:+6.3f} eng={r['english']:+6.2f}  {r['snippet']}")

    # Compare against null: random Latin strings of same length should score -10..0
    print(f"\nNull baseline (random text):")
    random.seed(3301)
    null_tris = []
    for _ in range(50):
        sample = [random.randrange(29) for _ in range(200)]
        null_tris.append(trigram_score(sample))
    print(f"  mean trigram={statistics.mean(null_tris):.3f} sd={statistics.stdev(null_tris):.3f}")
    print(f"  Observed best trigram: {max(r['trigram'] for r in results):.3f}")
    print(f"  z-score: {(max(r['trigram'] for r in results) - statistics.mean(null_tris)) / statistics.stdev(null_tris):.2f}")
    return results


# ============================================================================
# STEP 6 — CUSTOM LAG-5 PAIRED-COINCIDENCE ATTACK
# ============================================================================
def step6_custom_lag5_attack():
    """Custom lag-5 attack: extract d1 and d4 event positions and use as plaintext constraints."""
    print("\n" + "="*72)
    print("STEP 6 — CUSTOM LAG-5 PAIRED-COINCIDENCE ATTACK")
    print("="*72)
    # Concatenate all 55 unsolved pages into one rune stream
    pages = load_pages()
    full = []
    for p in pages:
        full.extend(p)
    n = len(full)
    print(f"Total runes: {n}")

    # Compute match indicator M[i] = (full[i] == full[i+5])
    M = [full[i] == full[i+5] for i in range(n - 5)]
    print(f"Total lag-5 matches: {sum(M)} (expected ~{n//29})")

    # Find d1 events: M[i] = M[i+1] = 1
    d1_events = [i for i in range(len(M) - 1) if M[i] and M[i+1]]
    # Find d4 events: M[i] = M[i+4] = 1
    d4_events = [i for i in range(len(M) - 4) if M[i] and M[i+4]]
    print(f"d1 events: {len(d1_events)} (expected ~{(n-5)//29/29:.1f})")
    print(f"d4 events: {len(d4_events)} (expected ~{(n-5)//29/29:.1f})")

    # For each event, the ciphertext repeats a digraph at distance 5.
    # Under interpretation (c) (back-reference): P[i] = P[i-5] AND P[i+1] = P[i-4]
    # For interpretation (a) (nulls): the copied runes are NULLS (plaintext is skipped)
    # For interpretation (b) (coincidence): key repeats AND plaintext repeats

    # Try interpretation (c): under additive cipher, key[i] = key[i+5] at these positions
    # That means: (cipher[i] - cipher[i+5]) mod 29 = (plaintext[i] - plaintext[i+5]) mod 29 = 0 (since pt[i]=pt[i+5])
    # So (cipher[i] - cipher[i+5]) mod 29 = key[i+5] - key[i]
    # If we assume period-5 additive key (key[i+5]=key[i]), then (cipher[i] - cipher[i+5]) mod 29 = 0
    # But for LP, this isn't quite 0 (mono kappa-5 = 1.073), so period-5 is excluded.
    #
    # Better: under back-reference hypothesis, at the 57 event positions we have plaintext[i] = plaintext[i+5]
    # Constraint: key[i] - key[i+5] = (cipher[i] - cipher[i+5]) mod 29 (for additive)
    # These are key-relation constraints, not key-value constraints.

    print("\n--- Key-relation constraints from lag-5 events ---")
    print("At each d1 event, plaintext[i] = plaintext[i+5] AND plaintext[i+1] = plaintext[i+6]")
    print("This means: key[i] - key[i+5] = (cipher[i] - cipher[i+5]) mod 29")
    print("            key[i+1] - key[i+6] = (cipher[i+1] - cipher[i+6]) mod 29\n")

    key_relations = Counter()
    for i in d1_events:
        for offset in range(2):  # i, i+1
            cd_diff = (full[i+offset] - full[i+offset+5]) % MOD
            key_relations[cd_diff] += 1
    for i in d4_events:
        # d4 event: M[i] = M[i+4] = 1
        # i.e. full[i] = full[i+5] AND full[i+4] = full[i+9]
        for offset in [0, 4]:
            cd_diff = (full[i+offset] - full[i+offset+5]) % MOD
            key_relations[cd_diff] += 1
    print(f"Most common (key[i] - key[i+5]) mod 29 values from {sum(key_relations.values())} events:")
    for kv, count in key_relations.most_common(10):
        print(f"  key_diff = {kv:2d} (rune {ALDEGONDE_RUNES[kv]} = {ALDEGONDE_LETTERS[kv]:3s}) count = {count}")

    # If the cipher is polyalphabetic with PERIOD 5, then key[i] - key[i+5] = 0 ALWAYS
    # So all events should give key_diff = 0. Let's see if the events show this.
    zero_count = key_relations.get(0, 0)
    total_events = sum(key_relations.values())
    print(f"\n  key_diff=0 count: {zero_count}/{total_events} ({100*zero_count/total_events:.1f}%)")
    print(f"  Expected if period-5 (uniform across all key diffs): {total_events/29:.1f} per bin")
    print(f"  Ratio vs uniform: {zero_count / (total_events/29):.2f}x")

    # If period-5 holds perfectly, ALL events should be key_diff=0.
    # If the cipher is NOT period-5, then key_diff values should be uniform (1.0x baseline).
    # If mono kappa-5 is 1.073x baseline, that's ~7% of lag-5 positions are real key repeats.

    # Test: assume interpretation (a) (nulls). The 57 event positions are NULLS — skip them
    # entirely in the cipher stream. What does the remaining cipher look like?
    print("\n--- Test interpretation (a): NULLS at lag-5 event positions ---")
    # Get all positions covered by any d1 or d4 event (i, i+1, i+4, i+5, i+9)
    null_positions = set()
    for i in d1_events:
        null_positions.add(i); null_positions.add(i+1); null_positions.add(i+5); null_positions.add(i+6)
    for i in d4_events:
        null_positions.add(i); null_positions.add(i+4); null_positions.add(i+5); null_positions.add(i+9)
    print(f"Total positions flagged as NULLS: {len(null_positions)} ({100*len(null_positions)/n:.2f}% of corpus)")
    # Remove these positions, recompute IoC
    reduced = [r for i, r in enumerate(full) if i not in null_positions]
    print(f"Reduced length: {len(reduced)}")
    # Compute nIoC
    counts = Counter(reduced)
    n_red = len(reduced)
    ioc = sum(v*(v-1) for v in counts.values()) / (n_red * (n_red-1)) * MOD if n_red > 1 else 0
    print(f"Reduced nIoC: {ioc:.4f} (random baseline 1.0000)")
    # doublet rate
    doublets = sum(1 for i in range(len(reduced)-1) if reduced[i] == reduced[i+1])
    print(f"Reduced doublet rate: {doublets/(len(reduced)-1)*100:.4f}% (original 0.664%)")

    # Test: assume interpretation (c) (back-references) — at each event, the plaintext repeats.
    # Use this as a constraint: P[i] = P[i+5]. This is a soft constraint we can use to test
    # candidate decryptions.
    # Apply: Vigenère with each KEY_CANDIDATE, check if P[i] = P[i+5] holds at event positions.
    print("\n--- Test interpretation (c): back-references — check candidate keys ---")
    print("For each KEY_CANDIDATE, decrypt the corpus, count how often P[i]=P[i+5] at events.")
    base_rate = (1/29)  # null hypothesis
    print(f"  Null: P[i]=P[i+5] random = 1/29 = {base_rate:.4f}")
    print(f"  Original cipher rate: {sum(M)/len(M):.4f}")
    print(f"  Period-5 Vigenère would predict rate = 1.0 if key repeats perfectly\n")
    best_keys = []
    for key_name, key_runes in KEY_CANDIDATES.items():
        key_decs = runes_to_decimals(key_runes)
        key_len = len(key_decs)
        if key_len == 0:
            continue
        # Decrypt with Vigenère
        pt = [(full[i] - key_decs[i % key_len]) % MOD for i in range(n)]
        # Count P[i]=P[i+5] at event positions (only d1, the cleaner case)
        event_match_count = 0
        event_tested = 0
        for i in d1_events:
            for off in [0, 1]:
                if i+off < n-5:
                    if pt[i+off] == pt[i+off+5]:
                        event_match_count += 1
                    event_tested += 1
        if event_tested > 0:
            rate = event_match_count / event_tested
            best_keys.append({
                'key': key_name,
                'event_match_rate': rate,
                'tested': event_tested,
                'key_len': key_len,
            })
    best_keys.sort(key=lambda x: -x['event_match_rate'])
    print(f"Top 10 keys by event-match rate (null = {base_rate:.4f}):")
    for k in best_keys[:10]:
        print(f"  key={k['key']:20s} len={k['key_len']:2d} match_rate={k['event_match_rate']:.4f} ({k['tested']} events)")

    # Custom: hill-climb on a 5-element additive key using the 57 d1 events as constraints
    # Objective: maximize P[i]=P[i+5] at d1 events
    print("\n--- Hill-climb on 5-element additive key using d1 events as constraints ---")
    print("Objective: maximize fraction of (P[i]=P[i+5]) at d1 event positions\n")
    random.seed(3301)
    best_5keys = []
    for trial in range(10):
        key = [random.randrange(29) for _ in range(5)]
        best_obj = -1
        best_key = list(key)
        # Try all 29^5 / hill-climb: 5 cosets, each with 29 values; solve independently
        # Actually for period-5 additive, the 5 cosets decouple; we already know
        # aldegonde did this exhaustive search. So this hill-climb is mostly a sanity check.
        # Use trigram-score hill-climb instead.
        T0, T1 = 2.0, 0.1
        for it in range(2000):
            T = T0 - (T0 - T1) * it / 2000
            # Mutate one position
            new_key = list(key)
            pos = random.randrange(5)
            new_key[pos] = (new_key[pos] + random.choice([-2, -1, 1, 2])) % MOD
            # Decrypt
            pt = [(full[i] - new_key[i % 5]) % MOD for i in range(min(800, n))]
            obj = trigram_score(pt)
            if obj > trigram_score([(full[i] - key[i % 5]) % MOD for i in range(min(800, n))]):
                key = new_key
                if obj > best_obj:
                    best_obj = obj
                    best_key = list(key)
            elif random.random() < math.exp((obj - trigram_score([(full[i] - key[i % 5]) % MOD for i in range(min(800, n))])) / max(T, 1e-9)):
                key = new_key
        best_5keys.append({
            'trial': trial,
            'key': best_key,
            'score': best_obj,
            'key_letters': ''.join(ALDEGONDE_LETTERS[k] for k in best_key)
        })
    best_5keys.sort(key=lambda x: -x['score'])
    print("Top 5 hill-climb results (period-5 additive, 800 runes):")
    for k in best_5keys[:5]:
        pt_str = ''.join(ALDEGONDE_LETTERS[(full[i] - k['key'][i % 5]) % MOD] for i in range(60))
        print(f"  trial {k['trial']}: key={k['key']} ({k['key_letters']}) score={k['score']:+.3f}  pt={pt_str}")
    return {
        'd1_count': len(d1_events),
        'd4_count': len(d4_events),
        'zero_count': zero_count,
        'total_events': total_events,
        'best_keys': best_keys[:5],
        'hill_climb_top5': best_5keys[:5]
    }


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    print("=" * 72)
    print("PHASE E: LAG-5 PAIRED-COINCIDENCE CRIB-DRAG (ZODIAC-340 METHOD)")
    print("=" * 72)
    print(f"Loaded {len(KEY_CANDIDATES)} KEY_CANDIDATES from gematria_primus.py")
    print(f"Loaded aldegonde trigrams: {len(TRIGRAMS)} entries")

    step3_matches, period5_data, crib_data = step3_contraction_cribs()
    zodiac_hits, v_hits = step4_zodiac_transposition_cribdrag()
    step5_results = step5_additive_reset()
    step6_results = step6_custom_lag5_attack()

    # Save results
    summary = {
        'step3': {
            'contraction_cribs': [
                {
                    'page': c['page'],
                    'local_idx': c['local_idx'],
                    'cipher_rune': c['cipher_rune'],
                    'cipher_letter': c['cipher_letter'],
                } for c in crib_data
            ],
            'key_candidate_matches': step3_matches[:30],
        },
        'step4': {
            'transposition_cribdrag_hits': len(zodiac_hits),
            'top_zodiac_hits': zodiac_hits[:10],
            'vigenere_transposition_hits': len(v_hits),
            'top_v_hits': v_hits[:10],
        },
        'step5': {
            'top_trigram': sorted(step5_results, key=lambda x: -x['trigram'])[:10],
            'top_english': sorted(step5_results, key=lambda x: -x['english'])[:10],
        },
        'step6': step6_results,
    }
    out_path = '/home/z/my-project/cicada3301-research/decoder/lag5_cribdrag_results.json'
    with open(out_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nResults saved to {out_path}")
