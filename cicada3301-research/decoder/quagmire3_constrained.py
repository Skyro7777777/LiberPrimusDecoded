#!/usr/bin/env python3
"""
quagmire3_constrained.py — Quagmire III Autokey with Constrained Keyword
=========================================================================
The MOST specific attack in the campaign, based on aldegonde's CONFIRMED hypothesis:

1. Cipher = Quagmire III (keyed Beaufort/Vigenère) with CIPHERTEXT AUTOKEY
2. C[i] = T[C[i-1]][P[i]]  where T is a keyed tableau
3. Doublet rate = freq(identity_char in PLAINTEXT) = 0.68%
4. Identity char ∈ {NG (0.60%), W (0.64%), TH (0.56%)} — matches observed 0.68%
5. Keyword's FIRST RUNE determines the identity position → must be NG, W, or TH
6. Memory length = 1 (only previous glyph matters)
7. Boundary-transparent (no key advance at word/sentence/page breaks)

This script:
- Builds a Quagmire III tableau from a keyword starting with NG/W/TH
- Applies ciphertext autokey decryption
- Hill-climbs on the remaining keyword letters + primer
- Scores with Runeglish quadgrams from aldegonde
"""
import sys, os, json, random, math
from typing import List, Tuple, Dict, Optional
sys.path.insert(0, os.path.dirname(__file__))
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, PRIMES, N_RUNES, MOD,
    runes_to_decimals, decimals_to_runes, decimals_to_latin, runes_to_latin,
)
from first_diff_masc import QUADGRAMS, LOG_QUAD, FLOOR_QUAD, quadgram_score

# The 3 candidate identity runes (rare in Runeglish, matching 0.68% doublet rate)
IDENTITY_CANDIDATES = {
    "NG": (21, 0.60),  # ᛝ — 0.60% freq in Runeglish
    "W":  (7,  0.64),  # ᚹ — 0.64% freq
    "TH": (2,  0.56),  # ᚦ — 0.56% freq
}


def build_keyed_alphabet(keyword_runes: str) -> List[int]:
    """
    Build the keyed alphabet from a keyword.
    keyword (dedup) + remaining runes in standard order.
    Returns a list of 29 decimal values (the keyed alphabet).
    """
    seen = set()
    alpha = []
    for r in keyword_runes:
        d = RUNE_TO_DEC[r]
        if d not in seen:
            seen.add(d)
            alpha.append(d)
    for d in range(N_RUNES):
        if d not in seen:
            alpha.append(d)
    return alpha


def build_quagmire3_tableau(keyed_alpha: List[int]) -> List[List[int]]:
    """
    Build Quagmire III tableau: T[k][p] = keyed_alpha[(k + p) % 29]
    
    For ciphertext autokey: C[i] = T[C[i-1]][P[i]]
    Decryption: P[i] = T_inv[C[i-1]][C[i]]
    where T_inv[k][c] = p such that T[k][p] = c
    """
    tableau = [[keyed_alpha[(k + p) % N_RUNES] for p in range(N_RUNES)] for k in range(N_RUNES)]
    return tableau


def build_inverse_tableau(tableau: List[List[int]]) -> List[List[int]]:
    """Build inverse: T_inv[k][c] = p such that T[k][p] = c."""
    inv = [[0] * N_RUNES for _ in range(N_RUNES)]
    for k in range(N_RUNES):
        for p in range(N_RUNES):
            c = tableau[k][p]
            inv[k][c] = p
    return inv


def quagmire3_autokey_decrypt(ct_decs: List[int], primer: int,
                               keyed_alpha: List[int]) -> List[int]:
    """
    Decrypt: P[i] = T_inv[C[i-1]][C[i]]
    where T_inv is built from the keyed alphabet.
    """
    # Build inverse tableau
    inv = [[0] * N_RUNES for _ in range(N_RUNES)]
    for k in range(N_RUNES):
        for p in range(N_RUNES):
            c = keyed_alpha[(k + p) % N_RUNES]
            inv[k][c] = p
    
    pt = []
    prev = primer
    for c in ct_decs:
        p = inv[prev][c]
        pt.append(p)
        prev = c  # ciphertext feedback
    return pt


def hill_climb_quagmire3(ct_decs: List[int], identity_rune: int,
                          max_iter: int = 15000, restarts: int = 30) -> Tuple:
    """
    Hill-climb on the keyed alphabet (29! space) with the constraint
    that the identity element sits at the given identity_rune position.
    
    The identity position is where keyed_alpha[pos] = 0 (F rune value).
    For identity at NG (21): keyed_alpha[21] = 0
    For identity at W (7):   keyed_alpha[7] = 0
    For identity at TH (2):  keyed_alpha[2] = 0
    
    This means the keyword must place F (ᚠ) at position 21/7/2 in the keyed alphabet.
    """
    sample = ct_decs[:800]  # first 800 runes for speed
    
    best_overall = None
    
    for restart in range(restarts):
        # Random keyed alphabet with F at the identity position
        alpha = list(range(1, N_RUNES))
        random.shuffle(alpha)
        alpha.insert(identity_rune, 0)  # place F at identity position
        assert alpha[identity_rune] == 0
        assert len(alpha) == N_RUNES
        
        # Try all 29 primers, pick best
        best_primer = 0
        best_score = -1e18
        for primer in range(N_RUNES):
            pt = quagmire3_autokey_decrypt(sample, primer, alpha)
            pt_runes = decimals_to_runes(pt)
            s = quadgram_score(pt_runes)
            if s > best_score:
                best_score = s
                best_primer = primer
        
        current_alpha = alpha[:]
        current_primer = best_primer
        current_score = best_score
        
        no_improve = 0
        for iteration in range(max_iter):
            # Mutate: swap two elements (NOT the identity position)
            # Choose two positions that are NOT the identity position
            positions = [i for i in range(N_RUNES) if i != identity_rune]
            i, j = random.sample(positions, 2)
            current_alpha[i], current_alpha[j] = current_alpha[j], current_alpha[i]
            
            # Occasionally try a different primer
            if random.random() < 0.05:
                new_primer = random.randint(0, N_RUNES - 1)
            else:
                new_primer = current_primer
            
            pt = quagmire3_autokey_decrypt(sample, new_primer, current_alpha)
            pt_runes = decimals_to_runes(pt)
            new_score = quadgram_score(pt_runes)
            
            if new_score > current_score:
                current_score = new_score
                current_primer = new_primer
                no_improve = 0
                if new_score > best_score:
                    best_score = new_score
                    best_alpha = current_alpha[:]
                    best_primer = new_primer
                    pt_best = runes_to_latin(pt_runes)
                    if iteration % 500 == 0 or new_score > -3000:
                        print(f"  r{restart:2d} it{iteration:5d}: score={new_score:8.1f}  {pt_best[:70]}")
            else:
                # Revert
                current_alpha[i], current_alpha[j] = current_alpha[j], current_alpha[i]
                no_improve += 1
            
            if no_improve > 3000:
                break
        
        # Final best for this restart
        pt = quagmire3_autokey_decrypt(sample, best_primer, best_alpha)
        pt_runes = decimals_to_runes(pt)
        pt_latin = runes_to_latin(pt_runes)
        
        if best_overall is None or best_score > best_overall[2]:
            best_overall = (best_alpha[:], best_primer, best_score, pt_latin, pt_runes)
        
        if restart % 5 == 0:
            print(f"  restart {restart}: best = {best_score:.1f}")
    
    return best_overall


def main():
    # Load unsolved pages
    with open(os.path.join(os.path.dirname(__file__), "unsolved_pages.json")) as f:
        unsolved = json.load(f)
    
    all_unsolved = "".join(p["runes"] for p in unsolved)
    ct_decs = runes_to_decimals(all_unsolved)
    
    print("=" * 70)
    print("QUAGMIRE III CONSTRAINED AUTOKEY ATTACK")
    print("=" * 70)
    print(f"Loaded {len(QUADGRAMS)} Runeglish quadgrams")
    print(f"Ciphertext: {len(ct_decs)} runes")
    print()
    
    # Test each identity candidate: NG (21), W (7), TH (2)
    results = {}
    for name, (id_pos, expected_rate) in IDENTITY_CANDIDATES.items():
        print(f"\n{'='*60}")
        print(f"IDENTITY = {name} (position {id_pos}, expected doublet rate {expected_rate}%)")
        print(f"{'='*60}")
        
        best = hill_climb_quagmire3(ct_decs, identity_rune=id_pos,
                                     max_iter=12000, restarts=20)
        
        alpha, primer, score, pt_latin, pt_runes = best
        print(f"\n>>> BEST for identity={name}:")
        print(f"  Score: {score:.1f}")
        print(f"  Primer: {DEC_TO_RUNE[primer]} ({DEC_TO_LETTER[primer]})")
        print(f"  Keyed alphabet: {alpha}")
        print(f"  alpha[{id_pos}] = {alpha[id_pos]} (should be 0 = F)")
        print(f"  Plaintext (Latin): {pt_latin[:200]}")
        print(f"  Plaintext (Runes): {pt_runes[:200]}")
        
        results[name] = {
            "score": score,
            "primer": DEC_TO_LETTER[primer],
            "keyed_alphabet": [DEC_TO_LETTER[a] for a in alpha],
            "plaintext_latin": pt_latin[:300],
            "plaintext_runes": pt_runes[:300],
        }
        
        # Check if it looks like English
        if score > -3000:
            print(f"\n  *** POTENTIAL BREAK! Score > -3000 ***")
            print(f"  Full plaintext: {pt_latin[:500]}")
    
    # Also test on the FIRST unsolved page specifically (the "20th page")
    print(f"\n{'='*60}")
    print("TESTING ON FIRST UNSOLVED PAGE (17.jpg / LP2 page 0)")
    print(f"{'='*60}")
    
    first_page_decs = runes_to_decimals(unsolved[0]["runes"])
    print(f"Page {unsolved[0]['page_id']}: {len(first_page_decs)} runes")
    
    for name, (id_pos, _) in IDENTITY_CANDIDATES.items():
        print(f"\n--- Identity = {name} (pos {id_pos}) ---")
        best = hill_climb_quagmire3(first_page_decs, identity_rune=id_pos,
                                     max_iter=15000, restarts=25)
        alpha, primer, score, pt_latin, pt_runes = best
        print(f"  Score: {score:.1f}, Primer: {DEC_TO_LETTER[primer]}")
        print(f"  Plaintext: {pt_latin[:200]}")
        
        results[f"page0_{name}"] = {
            "score": score,
            "primer": DEC_TO_LETTER[primer],
            "plaintext_latin": pt_latin[:300],
        }
        
        if score > -2000:
            print(f"\n  *** POTENTIAL BREAK on page 0! ***")
            print(f"  Full: {pt_latin}")
    
    # Save
    with open(os.path.join(os.path.dirname(__file__), "quagmire3_constrained_results.json"), "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved quagmire3_constrained_results.json")


if __name__ == "__main__":
    main()
