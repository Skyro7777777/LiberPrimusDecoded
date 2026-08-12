#!/usr/bin/env python3
"""
first_diff_masc.py — First-Difference Autokey + MASC Hill-Climber
=================================================================
THE most promising attack based on aldegonde's analysis:

The cipher is:
1. First-difference: D[i] = (C[i] - C[i-1]) % 29   (ciphertext autokey)
2. MASC: P[i] = perm[D[i]]   (monoalphabetic substitution on the differences)

The permutation `perm` is the key. It maps difference values (0-28) to plaintext runes.
For doublet suppression, perm[0] should map to a RARE rune (NG=21, W=7, TH=2).

This is a 29! search space, but hill-climbable with quadgram fitness.

The aldegonde library has Runeglish quadgrams (464K entries) for scoring.
"""
import sys, os, json, random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, PRIMES, N_RUNES, MOD,
    runes_to_decimals, decimals_to_runes, decimals_to_latin, runes_to_latin,
)

# Load Runeglish quadgrams from aldegonde
QUADGRAMS_PATH = os.path.join(os.path.dirname(__file__), "..", "solvers", "aldegonde", "src", "aldegonde", "data", "ngrams", "runeglish", "quadgrams.txt")
TRIGRAMS_PATH = os.path.join(os.path.dirname(__file__), "..", "solvers", "aldegonde", "src", "aldegonde", "data", "ngrams", "runeglish", "trigrams.txt")
BIGRAMS_PATH = os.path.join(os.path.dirname(__file__), "..", "solvers", "aldegonde", "src", "aldegonde", "data", "ngrams", "runeglish", "bigrams.txt")

def load_ngrams(path):
    grams = {}
    if not os.path.exists(path):
        return grams
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                gram, count = parts[0], int(parts[1])
                grams[gram] = count
    return grams

QUADGRAMS = load_ngrams(QUADGRAMS_PATH)
TRIGRAMS = load_ngrams(TRIGRAMS_PATH)
BIGRAMS = load_ngrams(BIGRAMS_PATH)

# Compute log probabilities
import math
total_quad = sum(QUADGRAMS.values()) if QUADGRAMS else 1
LOG_QUAD = {k: math.log(v / total_quad) for k, v in QUADGRAMS.items()} if QUADGRAMS else {}
FLOOR_QUAD = math.log(0.01 / total_quad) if total_quad else -20

total_tri = sum(TRIGRAMS.values()) if TRIGRAMS else 1
LOG_TRI = {k: math.log(v / total_tri) for k, v in TRIGRAMS.items()} if TRIGRAMS else {}
FLOOR_TRI = math.log(0.01 / total_tri) if total_tri else -20


def quadgram_score(rune_str):
    """Score a rune string using Runeglish quadgram log-probabilities."""
    if len(rune_str) < 4:
        return FLOOR_QUAD * len(rune_str)
    score = 0
    for i in range(len(rune_str) - 3):
        gram = rune_str[i:i+4]
        score += LOG_QUAD.get(gram, FLOOR_QUAD)
    return score

def trigram_score(rune_str):
    """Score using trigrams."""
    if len(rune_str) < 3:
        return FLOOR_TRI * len(rune_str)
    score = 0
    for i in range(len(rune_str) - 2):
        gram = rune_str[i:i+3]
        score += LOG_TRI.get(gram, FLOOR_TRI)
    return score


def first_differences(ct_decs, primer_dec):
    """Compute D[i] = (C[i] - C[i-1]) % 29, with D[0] = (C[0] - primer) % 29."""
    diffs = []
    prev = primer_dec
    for c in ct_decs:
        diffs.append((c - prev) % MOD)
        prev = c
    return diffs


def apply_masc(diffs, perm):
    """Apply permutation: P[i] = perm[D[i]]."""
    return [perm[d] for d in diffs]


def decrypt(ct_runes, primer_rune, perm):
    """Full decryption: first-diff + MASC."""
    ct_decs = runes_to_decimals(ct_runes)
    primer_dec = RUNE_TO_DEC[primer_rune]
    diffs = first_differences(ct_decs, primer_dec)
    pt_decs = apply_masc(diffs, perm)
    return decimals_to_runes(pt_decs)


def hill_climb_perm(ct_runes, max_iter=10000, restarts=30, use_quad=True):
    """
    Hill-climb on the permutation to maximize quadgram score.
    
    The permutation maps difference values (0-28) to plaintext rune values (0-28).
    """
    ct_decs = runes_to_decimals(ct_runes)
    sample_len = min(len(ct_decs), 1000)
    ct_decs = ct_decs[:sample_len]
    
    score_fn = quadgram_score if use_quad else trigram_score
    
    best_overall = None
    
    for restart in range(restarts):
        # Random starting permutation
        perm = list(range(N_RUNES))
        random.shuffle(perm)
        
        # Try all 29 primers, pick best
        best_primer = 0
        best_score = -1e18
        for primer in range(N_RUNES):
            diffs = first_differences(ct_decs, primer)
            pt_decs = apply_masc(diffs, perm)
            pt_runes = decimals_to_runes(pt_decs)
            s = score_fn(pt_runes)
            if s > best_score:
                best_score = s
                best_primer = primer
        
        # Hill-climb
        current_perm = perm[:]
        current_primer = best_primer
        current_score = best_score
        
        no_improve = 0
        for iteration in range(max_iter):
            # Mutate: swap two elements of the permutation
            i, j = random.sample(range(N_RUNES), 2)
            current_perm[i], current_perm[j] = current_perm[j], current_perm[i]
            
            # Also try changing primer occasionally
            if random.random() < 0.1:
                new_primer = random.randint(0, N_RUNES - 1)
            else:
                new_primer = current_primer
            
            diffs = first_differences(ct_decs, new_primer)
            pt_decs = apply_masc(diffs, current_perm)
            pt_runes = decimals_to_runes(pt_decs)
            new_score = score_fn(pt_runes)
            
            if new_score > current_score:
                current_score = new_score
                current_primer = new_primer
                no_improve = 0
                if new_score > best_score:
                    best_score = new_score
                    best_perm = current_perm[:]
                    best_primer = new_primer
                    pt_best = runes_to_latin(pt_runes)
                    if iteration % 200 == 0 or new_score > -500:
                        print(f"  r{restart:2d} it{iteration:5d}: score={new_score:8.1f}  {pt_best[:80]}")
            else:
                # Revert swap
                current_perm[i], current_perm[j] = current_perm[j], current_perm[i]
                no_improve += 1
            
            if no_improve > 2000:
                break
        
        # Get final best for this restart
        diffs = first_differences(ct_decs, best_primer)
        pt_decs = apply_masc(diffs, best_perm)
        pt_runes = decimals_to_runes(pt_decs)
        pt = runes_to_latin(pt_runes)
        
        if best_overall is None or best_score > best_overall[2]:
            best_overall = (best_perm[:], best_primer, best_score, pt, pt_runes)
        
        if restart % 5 == 0:
            print(f"  restart {restart}: best score = {best_score:.1f}")
    
    return best_overall


def test_all_primers_with_identity_perm(ct_runes):
    """Test all 29 primers with the identity permutation (baseline)."""
    print("\n=== Testing identity permutation (no MASC) ===")
    ct_decs = runes_to_decimals(ct_runes)
    sample = ct_decs[:500]
    
    for primer in range(N_RUNES):
        diffs = first_differences(sample, primer)
        pt_runes = decimals_to_runes(diffs)  # identity perm
        pt = runes_to_latin(pt_runes)
        s = quadgram_score(pt_runes)
        if primer < 5 or s > -1500:
            print(f"  primer={DEC_TO_RUNE[primer]} ({DEC_TO_LETTER[primer]:3s}): score={s:8.1f}  {pt[:60]}")


def main():
    # Load unsolved pages
    with open(os.path.join(os.path.dirname(__file__), "unsolved_pages.json")) as f:
        unsolved = json.load(f)
    
    print("=" * 70)
    print("FIRST-DIFFERENCE + MASC HILL-CLIMBER")
    print("=" * 70)
    print(f"Loaded {len(QUADGRAMS)} Runeglish quadgrams, {len(TRIGRAMS)} trigrams")
    
    # Test on the FIRST unsolved page (LP2 page 0, the "20th page" to decrypt)
    first_page = unsolved[0]
    print(f"\nTarget page: {first_page['page_id']} ({first_page['n_runes']} runes)")
    print(f"  Header: {first_page['header']}")
    
    # Step 1: Test identity permutation (baseline)
    test_all_primers_with_identity_perm(first_page["runes"])
    
    # Step 2: Hill-climb on the full unsolved corpus (first 1000 runes)
    all_unsolved = "".join(p["runes"] for p in unsolved)
    print(f"\n=== Hill-climbing on first 1000 runes of unsolved corpus ===")
    best = hill_climb_perm(all_unsolved[:1000], max_iter=8000, restarts=20, use_quad=True)
    
    perm, primer, score, pt_latin, pt_runes = best
    print(f"\n>>> BEST RESULT:")
    print(f"  Score: {score:.1f}")
    print(f"  Primer: {DEC_TO_RUNE[primer]} ({DEC_TO_LETTER[primer]})")
    print(f"  Permutation (diff→plain): {perm}")
    print(f"  perm[0] = {DEC_TO_LETTER[perm[0]]} (identity element → {DEC_TO_LETTER[perm[0]]})")
    print(f"  Plaintext (Latin): {pt_latin[:200]}")
    print(f"  Plaintext (Runes): {pt_runes[:200]}")
    
    # Step 3: Hill-climb on the first page specifically
    print(f"\n=== Hill-climbing on page {first_page['page_id']} (729 runes) ===")
    best_page = hill_climb_perm(first_page["runes"], max_iter=10000, restarts=25, use_quad=True)
    
    perm2, primer2, score2, pt_latin2, pt_runes2 = best_page
    print(f"\n>>> BEST for page {first_page['page_id']}:")
    print(f"  Score: {score2:.1f}")
    print(f"  Primer: {DEC_TO_RUNE[primer2]} ({DEC_TO_LETTER[primer2]})")
    print(f"  perm[0] = {DEC_TO_LETTER[perm2[0]]}")
    print(f"  Plaintext: {pt_latin2[:200]}")
    
    # Save results
    results = {
        "corpus_best": {
            "score": score,
            "primer": DEC_TO_LETTER[primer],
            "perm": [DEC_TO_LETTER[p] for p in perm],
            "perm_0": DEC_TO_LETTER[perm[0]],
            "plaintext_latin": pt_latin[:300],
            "plaintext_runes": pt_runes[:300],
        },
        "page0_best": {
            "score": score2,
            "primer": DEC_TO_LETTER[primer2],
            "perm": [DEC_TO_LETTER[p] for p in perm2],
            "perm_0": DEC_TO_LETTER[perm2[0]],
            "plaintext_latin": pt_latin2[:300],
            "plaintext_runes": pt_runes2[:300],
        },
    }
    with open(os.path.join(os.path.dirname(__file__), "first_diff_masc_results.json"), "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved first_diff_masc_results.json")


if __name__ == "__main__":
    main()
