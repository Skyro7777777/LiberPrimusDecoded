#!/usr/bin/env python3
"""
delimiter_codebook_attack.py
============================
Wave-7 / Phase E — Task p6d

Three cipher models targeting the LP2 unsolved corpus (pages 17-55, 8,739 runes):

  Model 1 — DELIMITER-STATE CIPHER
    Key advances only at delimiter positions; same key value used between delimiters.
    Two variants tested:
      V1 "advance": ki = (ki+1) % len(key) on each delimiter.
      V2 "reset":    ki = delimiter_count % len(key) on each rune.
    Tested against all 20 KEY_CANDIDATES.

  Model 2 — LP1 SOLVED PAGES AS BOOK CIPHER CODEBOOK
    Codebook = concatenated plaintext of all 13 solved LP1 pages (~5,800 runes).
    Variants:
      B1 single-rune -> Nth WORD (mod codebook size) -> first letter
      B2 rune-pair   -> Nth WORD (mod)              -> first letter
      B3 rune-pair   -> (Nth rune of codebook)      -> first letter (positional)
      B4 gematria-sum of each rune-word -> Nth word -> whole word

  Model 3 — DELIMITER-SEQUENCE-AS-KEYSTREAM
    Sequence of delimiter TYPES (/, •, ·, ., -, _, =, *, %, &, $, #) in order;
    map each to value 0..N; use as keystream.
    Try a few mapping permutations.

Scoring: english_score() from gematria_primus.py (random-baseline max ~74, P99 = 74.36).
Break threshold: score > 75.

Outputs:
  decoder/delimiter_codebook_results.json  (full results)
  compiled/DELIMITER_CODEBOOK_RESULTS.md    (human-readable report)
"""
from __future__ import annotations
import json, os, sys, itertools, re
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gematria_primus import (
    RUNES, LETTERS, DECIMALS, RUNE_TO_DEC, DEC_TO_LETTER,
    is_rune, rune_to_dec, dec_to_letter, dec_to_rune,
    runes_to_decimals, runes_to_latin, english_score, KEY_CANDIDATES,
    clean_runes, DELIMITERS,
)

# ============================================================================
# LOAD DATA
# ============================================================================
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_unsolved_corpus() -> str:
    """Return unsolved LP2 corpus (pages 17-55) with delimiters preserved."""
    with open(os.path.join(ROOT, 'decoder', 'translit_pages_with_delims.json')) as f:
        d = json.load(f)
    pages = [f'{i}.jpg' for i in range(17, 56)]
    text = ''.join(d[p] for p in pages if p in d)
    return text

def load_lp1_codebook() -> Tuple[List[str], str, str]:
    """Return (rune_list, plaintext_str, runes_str) from solved LP1 pages.

    NOTE: LP1 solved-page plaintext is Cicada-English (no word breaks, V-for-U),
    so the "wordlist" is actually a list of individual LETTERS (one per rune position).
    This gives a ~3,163-letter codebook (vs the ~6,000-rune ciphertext, since LP1
    uses multi-letter runes TH, NG, EA etc which collapse to single Latin letters).
    """
    with open(os.path.join(ROOT, 'decoder', 'lp1_plaintext_codebook.json')) as f:
        pt = json.load(f)
    # Concatenate all plaintext in canonical solved-page order
    order = ['01.jpg','03.jpg','04.jpg','05.jpg','06.jpg','09.jpg',
             '10.jpg','13.jpg','14.jpg','16.jpg','73.jpg','74.jpg']
    full_pt = ''.join(pt[p] for p in order if p in pt)
    # Codebook = list of individual letters (rune positions)
    letters = [c.upper() for c in full_pt if c.isalpha()]
    return letters, full_pt, full_pt

# ============================================================================
# MODEL 1 — DELIMITER-STATE CIPHER
# ============================================================================
def is_delim(ch: str) -> bool:
    return not is_rune(ch)

def delimiter_state_v1(ciphertext: str, key_runes: str) -> str:
    """Variant 1: ki advances by 1 (mod len(key)) at each delimiter."""
    key_decs = runes_to_decimals(key_runes)
    if not key_decs:
        return ""
    ki = 0
    out = []
    for ch in ciphertext:
        if is_delim(ch):
            ki = (ki + 1) % len(key_decs)
            out.append(ch)  # preserve delim
            continue
        pt = (rune_to_dec(ch) - key_decs[ki]) % 29
        out.append(dec_to_letter(pt))
    return ''.join(out)

def delimiter_state_v2(ciphertext: str, key_runes: str) -> str:
    """Variant 2: ki = delimiter_count % len(key) on each rune."""
    key_decs = runes_to_decimals(key_runes)
    if not key_decs:
        return ""
    delim_count = 0
    out = []
    for ch in ciphertext:
        if is_delim(ch):
            delim_count += 1
            out.append(ch)
            continue
        ki = delim_count % len(key_decs)
        pt = (rune_to_dec(ch) - key_decs[ki]) % 29
        out.append(dec_to_letter(pt))
    return ''.join(out)

def score_text(text: str, n: int = 500) -> float:
    """Score english-likeness on first n runes/letters."""
    # Take first n rune-equivalent tokens (strip delimiters for scoring)
    letters = ''.join(c for c in text if c.isalpha())
    return english_score(letters[:n])

def snippet(text: str, n: int = 80) -> str:
    letters = ''.join(c for c in text if c.isalpha())
    return letters[:n]

# ============================================================================
# MODEL 2 — LP1 AS CODEBOOK
# ============================================================================
def book_cipher_v1_single_rune_to_word(ciphertext: str, codebook_letters: List[str]) -> str:
    """Each rune -> Nth letter of codebook (mod size) -> that letter.
    Codebook size = ~3163 letters (LP1 solved plaintext)."""
    decs = runes_to_decimals(clean_runes(ciphertext))
    n = len(codebook_letters)
    out = []
    for d in decs:
        out.append(codebook_letters[d % n])
    return ''.join(out)

def book_cipher_v2_pair_to_word(ciphertext: str, codebook_letters: List[str]) -> str:
    """Each rune-pair (29*29=841 values) -> Nth letter of codebook (mod size)."""
    decs = runes_to_decimals(clean_runes(ciphertext))
    n = len(codebook_letters)
    out = []
    for i in range(0, len(decs) - 1, 2):
        idx = (decs[i] * 29 + decs[i+1]) % n
        out.append(codebook_letters[idx])
    if len(decs) % 2 == 1:
        out.append(codebook_letters[decs[-1] % n])
    return ''.join(out)

def book_cipher_v3_pair_to_rune_position(ciphertext: str, codebook_pt: str) -> str:
    """Each rune-pair -> (word_idx*29 + letter_idx) -> single char of codebook_pt.
    Same as v2 but indexes raw plaintext string (not letter list).
    Effectively same as v2 but kept for backward-compat with original spec."""
    decs = runes_to_decimals(clean_runes(ciphertext))
    pt = codebook_pt.upper()
    out = []
    for i in range(0, len(decs) - 1, 2):
        pos = (decs[i] * 29 + decs[i+1]) % len(pt)
        out.append(pt[pos])
    if len(decs) % 2 == 1:
        out.append(pt[decs[-1] % len(pt)])
    return ''.join(out)

def book_cipher_v4_gematria_sum_per_word(ciphertext: str, codebook_letters: List[str]) -> str:
    """Each rune-word -> (gematria-sum + length) mod codebook_size -> Nth letter.
    Returns one output letter per rune-word (NOT one per rune)."""
    words = re.split(r'[^'+re.escape(RUNES)+r']+', ciphertext)
    words = [w for w in words if w]
    n = len(codebook_letters)
    out = []
    for w in words:
        s = sum(rune_to_dec(r) for r in w) % 29
        idx = (s + len(w)) % n
        out.append(codebook_letters[idx])
    return ''.join(out)

# ============================================================================
# MODEL 3 — DELIMITER-SEQUENCE AS KEYSTREAM
# ============================================================================
DELIM_TYPES = [' ', '\n', '\t', '/', '•', '·', '.', '-', '_', '=', '*', '%', '&', '$', '#', '§']

def extract_delim_sequence(ciphertext: str) -> List[str]:
    """Return list of delimiter chars (canonical DELIMITERS only) in order of appearance.
    Filters out page metadata (digits, letters from '17.jpg', etc.)."""
    return [c for c in ciphertext if (not is_rune(c)) and (c in DELIMITERS)]

def delim_keystream_decrypt(ciphertext: str, delim_map: Dict[str, int]) -> str:
    """Use the delim sequence (mapped to values) as keystream, repeating."""
    seq = extract_delim_sequence(ciphertext)
    if not seq:
        return runes_to_latin(clean_runes(ciphertext))
    key_stream = [delim_map.get(c, 0) % 29 for c in seq]
    L = len(key_stream)
    out = []
    ki = 0
    for ch in ciphertext:
        if is_delim(ch):
            ki = (ki + 1) % L  # advance to next key only at delim
            out.append(ch)
            continue
        pt = (rune_to_dec(ch) - key_stream[ki]) % 29
        out.append(dec_to_letter(pt))
    return ''.join(out)

def delim_keystream_decrypt_v2(ciphertext: str, delim_map: Dict[str, int]) -> str:
    """Variant: ki = delim_count (no advance on rune); pure periodic."""
    seq = extract_delim_sequence(ciphertext)
    if not seq:
        return runes_to_latin(clean_runes(ciphertext))
    key_stream = [delim_map.get(c, 0) % 29 for c in seq]
    L = len(key_stream)
    out = []
    delim_count = 0
    for ch in ciphertext:
        if is_delim(ch):
            delim_count += 1
            out.append(ch)
            continue
        ki = delim_count % L
        pt = (rune_to_dec(ch) - key_stream[ki]) % 29
        out.append(dec_to_letter(pt))
    return ''.join(out)

# ============================================================================
# MAIN
# ============================================================================
def main():
    print('='*70)
    print('DELIMITER-CHANNEL + LP1-CODEBOOK ATTACK (Task p6d)')
    print('='*70)

    ct = load_unsolved_corpus()
    ct_runes = clean_runes(ct)
    print(f'Loaded unsolved LP2 corpus: {len(ct)} chars, {len(ct_runes)} runes')

    cb_words, cb_pt, _ = load_lp1_codebook()
    print(f'Loaded LP1 codebook: {len(cb_words)} words, {len(cb_pt)} chars')

    delim_seq = extract_delim_sequence(ct)
    from collections import Counter
    dc = Counter(delim_seq)
    print(f'Delimiter sequence: {len(delim_seq)} delimiters, types: {dict(dc)}')
    print()

    results = {'model1': [], 'model2': [], 'model3': []}

    # ===================== MODEL 1 =====================
    print('--- MODEL 1: Delimiter-state cipher (20 keys × 2 variants) ---')
    for name, key in KEY_CANDIDATES.items():
        for variant, fn in [('advance', delimiter_state_v1), ('reset', delimiter_state_v2)]:
            pt_text = fn(ct, key)
            sc = score_text(pt_text, 500)
            snip = snippet(pt_text, 80)
            results['model1'].append({
                'key': name, 'variant': variant, 'score': sc, 'snippet': snip
            })
            print(f'  {name:22s} {variant:8s} score={sc:7.3f}  {snip[:60]}')

    # ===================== MODEL 2 =====================
    print()
    print('--- MODEL 2: LP1-as-codebook (4 variants) ---')
    # Apply to first 200 runes (per task spec)
    ct200 = ct_runes[:200]
    # Reconstruct delimited version for word-based variants
    # For word-based variants, we need original delimited text trimmed to first ~200 runes
    rune_count = 0
    ct200_delim = []
    for ch in ct:
        ct200_delim.append(ch)
        if is_rune(ch):
            rune_count += 1
            if rune_count >= 200:
                break
    ct200_delim_str = ''.join(ct200_delim)

    m2_tests = [
        ('v1_single_rune_to_letter',   lambda c: book_cipher_v1_single_rune_to_word(c, cb_words)),
        ('v2_pair_to_letter',          lambda c: book_cipher_v2_pair_to_word(c, cb_words)),
        ('v3_pair_to_pt_position',     lambda c: book_cipher_v3_pair_to_rune_position(c, cb_pt)),
        ('v4_gematria_sum_per_word',   lambda c: book_cipher_v4_gematria_sum_per_word(c, cb_words)),
    ]
    for name, fn in m2_tests:
        try:
            pt_text = fn(ct200_delim_str)
            sc = score_text(pt_text, 500)  # scoring on the (shorter) output
            snip = snippet(pt_text, 80)
            results['model2'].append({
                'variant': name, 'score': sc, 'snippet': snip,
                'output_len': len(pt_text),
            })
            print(f'  {name:32s} score={sc:7.3f}  out_len={len(pt_text):5d}  {snip[:60]}')
        except Exception as e:
            results['model2'].append({'variant': name, 'error': str(e)})
            print(f'  {name:32s} ERROR: {e}')

    # ===================== MODEL 3 =====================
    print()
    print('--- MODEL 3: Delimiter-sequence-as-keystream ---')
    # Build delim_map permutations. Use distinct delim chars observed.
    observed = list(dc.keys())
    print(f'  Observed delim types: {observed}')

    # Canonical map (task spec)
    base_map = {'/':0,'•':1,'·':2,'.':3,'-':4,'_':5,'=':6,'*':7,'%':8,'&':9,'$':10,'#':11,
                ' ':12, '\n':13, '\t':14, '§':15}
    # Test a few permutations
    perms_tested = []
    # Base
    perms_tested.append(('canonical', base_map))
    # Mod-29 spread (use 0,1,2,...,15)
    perms_tested.append(('identity', {c:i for i,c in enumerate(observed)}))
    # Fibonacci-like
    fib_vals = [1,1,2,3,5,8,13,21]
    perms_tested.append(('fib_mod29', {c:fib_vals[i%len(fib_vals)] for i,c in enumerate(observed)}))
    # Primes mod 29
    primes_list = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53]
    perms_tested.append(('primes_mod29', {c:primes_list[i%len(primes_list)] for i,c in enumerate(observed)}))
    # Reverse
    perms_tested.append(('reverse', {c:(len(observed)-i) for i,c in enumerate(observed)}))
    # All-zero (control)
    perms_tested.append(('all_zero', {c:0 for c in observed}))
    # Try a few random-ish permutations on observed delims
    import random
    random.seed(3301)
    for trial in range(5):
        vals = list(range(len(observed)))
        random.shuffle(vals)
        perms_tested.append((f'rand_trial_{trial}', {c:vals[i] for i,c in enumerate(observed)}))

    for name, dm in perms_tested:
        for variant, fn in [('v1_advance', delim_keystream_decrypt), ('v2_periodic', delim_keystream_decrypt_v2)]:
            try:
                pt_text = fn(ct, dm)
                sc = score_text(pt_text, 500)
                snip = snippet(pt_text, 80)
                results['model3'].append({
                    'mapping': name, 'variant': variant, 'score': sc, 'snippet': snip,
                })
                print(f'  {name:18s} {variant:12s} score={sc:7.3f}  {snip[:60]}')
            except Exception as e:
                print(f'  {name:18s} {variant:12s} ERROR: {e}')

    # ===================== SUMMARY =====================
    print()
    print('='*70)
    print('SUMMARY')
    print('='*70)
    # Top 5 per model
    for model_name, items in results.items():
        valid = [x for x in items if 'score' in x]
        valid.sort(key=lambda x: -x['score'])
        print(f'\nTop 5 ({model_name}):')
        for x in valid[:5]:
            label = x.get('key', x.get('variant', x.get('mapping','?')))
            label2 = x.get('variant', x.get('mapping',''))
            print(f'  {label:22s} {label2:14s}  score={x["score"]:7.3f}  {x["snippet"][:60]}')
    # Overall best
    all_scores = [(m, x) for m, items in results.items() for x in items if 'score' in x]
    all_scores.sort(key=lambda t: -t[1]['score'])
    if all_scores:
        best_m, best_x = all_scores[0]
        print(f'\nOverall best: {best_m} score={best_x["score"]:.3f}  {best_x.get("snippet","")[:80]}')
        print(f'Break threshold (>75): {"YES" if best_x["score"] > 75 else "NO"}')

    # Save results
    with open(os.path.join(ROOT, 'decoder', 'delimiter_codebook_results.json'), 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print('\nSaved decoder/delimiter_codebook_results.json')

if __name__ == '__main__':
    main()
