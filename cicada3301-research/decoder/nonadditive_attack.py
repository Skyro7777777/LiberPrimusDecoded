#!/usr/bin/env python3
"""
nonadditive_attack.py — Test 3 non-additive per-word progressive substitution models.
Task ID: p6c.  Wave-7 / Phase E.

Rationale: Additive ciphers (Vigenère/autokey/PRNG) all rejected (LAG5_CRIBDRAG_RESULTS).
This module tests NON-ADDITIVE per-word models where the alphabet changes after each word
based on the plaintext of that word — eliminating the additive doublet floor (1.7%)
that LP's 0.66% rate rules out.

Three models (per task spec):
  M1: alphabet rotated by previous word's plaintext gematria-sum
  M2: alphabet atbashed if previous word-length is prime, else rotated by 1
  M3: alphabet rotated by previous word-length
"""
import json, sys, re
from collections import Counter
from typing import List

sys.path.insert(0, '/home/z/my-project/cicada3301-research/decoder')
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, MOD, is_rune,
    rune_to_dec, dec_to_rune, decimals_to_latin, english_score,
    KEY_CANDIDATES, clean_runes, runes_to_decimals
)

# ============================================================================
# LOAD UNSOLVED CORPUS (with delimiters preserved)
# ============================================================================
TRANSLIT_PATH = '/home/z/my-project/cicada3301-research/raw/primary/primary_translit.txt'

def load_unsolved_corpus_with_delims() -> str:
    """Concatenate wiki pages 17-55 (unsolved LP2 corpus), preserving delimiters."""
    s = open(TRANSLIT_PATH).read()
    markers = list(re.finditer(r'\b(\d+)\.jpg\b', s))
    content_markers = [m for m in markers if m.start() > 3700]
    pages = {}
    for i, m in enumerate(content_markers):
        pid = m.group(1) + '.jpg'
        start = m.end()
        end = content_markers[i+1].start() if i+1 < len(content_markers) else len(s)
        pages[pid] = s[start:end]
    combined = ''
    for pid_num in range(17, 56):  # unsolved LP2 pages
        pid = f'{pid_num}.jpg'
        if pid in pages:
            combined += pages[pid] + '\n'
    return combined

# Delimiter set per task spec (note: § is the chapter-marker, & is paragraph, $ is segment)
DELIMS = "/•·.-_=*%&$#§ \n\t"

def split_words(text: str) -> List[List[int]]:
    """Split a delim-preserved stream into rune-words (lists of decimal values)."""
    words = []
    cur = []
    for ch in text:
        if is_rune(ch):
            cur.append(rune_to_dec(ch))
        else:
            if cur:
                words.append(cur)
                cur = []
    if cur:
        words.append(cur)
    return words

def take_first_n_runes_with_words(text: str, n: int) -> List[List[int]]:
    """Return list of rune-words covering the first N runes (rune-only count)."""
    words = split_words(text)
    out = []
    total = 0
    for w in words:
        out.append(w)
        total += len(w)
        if total >= n:
            break
    return out

# ============================================================================
# INITIAL ALPHABET DERIVATIONS
# ============================================================================
def identity_alphabet() -> List[int]:
    return list(range(MOD))

def keyword_alphabet(key_runes: str) -> List[int]:
    """Standard keyword-derived substitution alphabet.
    Unique runes of key (in order of first appearance), then remaining runes in canonical order.
    Returns a LIST of decimals where position i is the rune-index that maps to plain-index i.
    """
    seen = []
    for r in key_runes:
        if is_rune(r):
            d = rune_to_dec(r)
            if d not in seen:
                seen.append(d)
    rest = [d for d in range(MOD) if d not in seen]
    return seen + rest

def derive_alphabets() -> dict:
    """Build the 4 initial alphabets per task spec."""
    DIVINITY = KEY_CANDIDATES['DIVINITY']              # ᛞᛁᚢᛁᚾᛁᛏᚣ
    FIRFUM   = KEY_CANDIDATES['FIRFUMFERENFE']         # ᚠᛁᚱᚠᚢᛗᚠᛖᚱᛖᚾᚠᛖ
    PARABLE  = KEY_CANDIDATES['PARABLE']               # ᛈᚪᚱᚪᛒᛚᛖ
    return {
        'identity':           identity_alphabet(),
        'DIVINITY-derived':   keyword_alphabet(DIVINITY),
        'FIRFUMFERENFE-derived': keyword_alphabet(FIRFUM),
        'parable-derived':    keyword_alphabet(PARABLE),
    }

# ============================================================================
# CIPHER MODELS
# ============================================================================
def is_prime(n: int) -> bool:
    if n < 2: return False
    if n < 4: return True
    if n % 2 == 0: return False
    i = 3
    while i*i <= n:
        if n % i == 0: return False
        i += 2
    return True

def model1_gematria_shift(words: List[List[int]], alphabet0: List[int]) -> List[int]:
    """M1: alphabet rotated by previous word's plaintext gematria-sum."""
    alphabet = list(alphabet0)
    plaintext = []
    for word_decs in words:
        pt_word = [(c - alphabet[i]) % MOD for i, c in enumerate(word_decs)]
        plaintext.extend(pt_word)
        shift = sum(pt_word) % MOD
        alphabet = alphabet[shift:] + alphabet[:shift]
    return plaintext

def model2_atbash_prime(words: List[List[int]], alphabet0: List[int]) -> List[int]:
    """M2: atbash if word-length is prime, else rotate by 1."""
    alphabet = list(alphabet0)
    plaintext = []
    for word_decs in words:
        pt_word = [(c - alphabet[i]) % MOD for i, c in enumerate(word_decs)]
        plaintext.extend(pt_word)
        if is_prime(len(word_decs)):
            alphabet = [MOD - 1 - a for a in alphabet]
        else:
            alphabet = alphabet[1:] + alphabet[:1]
    return plaintext

def model3_length_clocked(words: List[List[int]], alphabet0: List[int]) -> List[int]:
    """M3: alphabet advances by word-length after each word."""
    alphabet = list(alphabet0)
    plaintext = []
    for word_decs in words:
        pt_word = [(c - alphabet[i]) % MOD for i, c in enumerate(word_decs)]
        plaintext.extend(pt_word)
        L = len(word_decs) % MOD
        alphabet = alphabet[L:] + alphabet[:L]
    return plaintext

MODELS = {
    'M1_gematria_shift': model1_gematria_shift,
    'M2_atbash_prime':   model2_atbash_prime,
    'M3_length_clocked': model3_length_clocked,
}

# ============================================================================
# RUN ALL 12 TESTS
# ============================================================================
def main():
    print("=" * 72)
    print("NON-ADDITIVE PER-WORD PROGRESSIVE SUBSTITUTION ATTACK")
    print("=" * 72)

    corpus = load_unsolved_corpus_with_delims()
    n_runes_total = sum(1 for c in corpus if is_rune(c))
    print(f"Unsolved corpus: {n_runes_total} runes (wiki pages 17-55)")

    # First 500 runes split into words
    words_500 = take_first_n_runes_with_words(corpus, 500)
    actual_n = sum(len(w) for w in words_500)
    print(f"First-500-rune window: {len(words_500)} words, {actual_n} runes")

    alphabets = derive_alphabets()
    for name, alpha in alphabets.items():
        print(f"  alphabet '{name}': {len(alpha)} entries, first 8 = {alpha[:8]}")

    results = []
    print()
    print("=" * 72)
    print(f"{'Model':<22} {'Alphabet':<24} {'Score':>7}  Plaintext (first 80)")
    print("=" * 72)
    for mname, mfn in MODELS.items():
        for aname, alpha in alphabets.items():
            pt_decs = mfn(words_500, alpha)
            pt_latin = decimals_to_latin(pt_decs)
            score = english_score(pt_latin)
            snippet = pt_latin[:80].replace('\n', ' ')
            results.append({
                'model': mname, 'alphabet': aname, 'score': round(score, 3),
                'snippet': snippet,
            })
            star = ' <== BREAKTHROUGH' if score > 75 else ''
            print(f"{mname:<22} {aname:<24} {score:>7.3f}  {snippet}{star}")
    print()

    # Save JSON
    with open('/home/z/my-project/cicada3301-research/decoder/nonadditive_results.json', 'w') as f:
        json.dump({
            'corpus_runes': n_runes_total,
            'window_runes': actual_n,
            'window_words': len(words_500),
            'results': results,
        }, f, indent=2)

    # ========================================================================
    # WORD-LENGTH DISTRIBUTION
    # ========================================================================
    print("=" * 72)
    print("WORD-LENGTH DISTRIBUTION (full unsolved corpus)")
    print("=" * 72)
    all_words = split_words(corpus)
    lens = [len(w) for w in all_words]
    lc = Counter(lens)
    print(f"{'Len':>4} {'Count':>6} {'Pct':>7}  Bar")
    for L in sorted(lc.keys()):
        pct = 100 * lc[L] / len(lens)
        bar = '█' * int(pct)
        print(f"{L:>4} {lc[L]:>6} {pct:>6.2f}%  {bar}")
    print(f"Total words: {len(lens)}, mean length: {sum(lens)/len(lens):.3f}")
    print()

    # ========================================================================
    # TOP-10 MOST-REPEATED RUNE-WORDS
    # ========================================================================
    print("=" * 72)
    print("TOP-10 MOST-REPEATED RUNE-WORDS (full unsolved corpus)")
    print("=" * 72)
    word_strs = [''.join(DEC_TO_RUNE[d] for d in w) for w in all_words]
    wc = Counter(word_strs)
    print(f"{'Rank':>4} {'Count':>6} {'Word':<30} {'Latin':<30}")
    for i, (w, c) in enumerate(wc.most_common(10), 1):
        lat = ''.join(DEC_TO_LETTER[d] for d in [RUNE_TO_DEC[r] for r in w])
        print(f"{i:>4} {c:>6} {w:<30} {lat:<30}")

    # Save distribution + top words
    with open('/home/z/my-project/cicada3301-research/decoder/nonadditive_wordstats.json', 'w') as f:
        json.dump({
            'n_words': len(all_words),
            'mean_len': sum(lens)/len(lens),
            'length_dist': {str(k): v for k, v in sorted(lc.items())},
            'top_words': [(w, c) for w, c in wc.most_common(20)],
        }, f, indent=2, ensure_ascii=False)

    print()
    print("Saved: decoder/nonadditive_results.json, decoder/nonadditive_wordstats.json")
    return results

if __name__ == '__main__':
    main()
