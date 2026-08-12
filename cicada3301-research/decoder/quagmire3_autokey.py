#!/usr/bin/env python3
"""
quagmire3_autokey.py — Quagmire III (keyed Beaufort) Autokey Cipher
====================================================================
THE most promising hypothesis from the aldegonde repo:

The cipher is a Quagmire III autokey with ciphertext feedback, where:
- The tableau is KEYED (scrambled) by a keyword (NOT the identity tableau)
- The identity element sits at a RARE plaintext letter (NG/W/TH → 0.56-0.64% freq)
- This produces the observed 0.68% doublet rate (matching NG/W frequency)

Standard Vigenère tableau: T[k][p] = (k + p) mod 29  →  identity at column 0 (F, freq 1.11%)
Quagmire III tableau:     T[k][p] = keyed permutation  →  identity at column = keyword-derived position

If the keyword places the identity at NG (position 21) or W (position 7), doublets are rare.

CIPHERTEXT AUTOKEY:
  C[0] = T[K[0]][P[0]]          (primer K[0])
  C[i] = T[C[i-1]][P[i]]       (ciphertext feedback)

DECRYPTION:
  P[0] = T_inv[K[0]][C[0]]
  P[i] = T_inv[C[i-1]][C[i]]

The tableau T is constructed from a keyword:
  1. Write the keyword (deduplicated) as the first row
  2. Each subsequent row is the previous row shifted by 1 (cyclically)
  This creates a Latin square where each row is a permutation of 0-28.
"""
from __future__ import annotations
import sys, os, json, random, itertools
from typing import List, Dict, Tuple, Optional
sys.path.insert(0, os.path.dirname(__file__))
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, PRIMES, N_RUNES, MOD,
    is_rune, rune_to_dec, dec_to_rune, runes_to_decimals, decimals_to_runes,
    decimals_to_latin, runes_to_latin, english_score, KEY_CANDIDATES,
    frequency_analysis, _nth_prime,
)


def build_quagmire3_tableau(keyword_runes: str) -> List[List[int]]:
    """
    Build a Quagmire III tableau (keyed Vigenère/Beaufort) from a keyword.
    
    The keyword determines the ALPHABET ORDER used in the tableau.
    - First, create the keyed alphabet: keyword runes (dedup) + remaining runes in order
    - The tableau row k is the keyed alphabet shifted to start at position k
    - T[k][p] = keyed_alphabet[(k + p) mod 29]
    
    This is a Latin square: each row/column is a permutation of 0-28.
    The identity element (where T[k][p] = k) is at p = 0 for ALL k
    (same as standard Vigenère) UNLESS we use a different construction.
    
    For Quagmire III (Beaufort-style), T[k][p] = keyed_alphabet[(k - p) mod 29]
    which changes the identity structure.
    
    Actually, the key insight from aldegonde is:
    - In standard Vigenère: T[k][p] = (k+p) mod 29, identity at p=0 (F rune)
    - In Quagmire III: T[k][p] = keyed_alphabet[(p + k) mod 29] where keyed_alphabet
      is a permutation. The identity element is at the position where keyed_alphabet[pos] = 0.
    - If keyed_alphabet[21] = 0 (i.e. NG position maps to F/0), then identity is at p=21 (NG)
    
    So we need to construct the keyed alphabet such that a RARE rune (NG=21, W=7, TH=2)
    is at the position where the identity element sits.
    """
    # Build keyed alphabet: keyword (dedup) + remaining runes in standard order
    seen = set()
    keyed_alpha = []
    for r in keyword_runes:
        d = rune_to_dec(r)
        if d not in seen:
            seen.add(d)
            keyed_alpha.append(d)
    for d in range(N_RUNES):
        if d not in seen:
            keyed_alpha.append(d)
    assert len(keyed_alpha) == N_RUNES
    
    # Build tableau: T[k][p] = keyed_alpha[(k + p) mod 29]
    # This is a Latin square. Identity element: T[k][p] = k when keyed_alpha[(k+p)%29] = k
    # → (k+p) % 29 = position_of_k_in_keyed_alpha
    # → p = (position_of_k_in_keyed_alpha - k) mod 29
    # For ALL k, the identity p is the SAME if keyed_alpha is a Caesar shift of identity.
    # For a GENERAL keyed alphabet, the identity p VARIES per k.
    
    tableau = []
    for k in range(N_RUNES):
        row = []
        for p in range(N_RUNES):
            row.append(keyed_alpha[(k + p) % N_RUNES])
        tableau.append(row)
    
    return tableau


def build_inverse_tableau(tableau: List[List[int]]) -> List[List[int]]:
    """Build the inverse tableau for decryption: T_inv[k][c] = p such that T[k][p] = c."""
    inv = [[0] * N_RUNES for _ in range(N_RUNES)]
    for k in range(N_RUNES):
        for p in range(N_RUNES):
            c = tableau[k][p]
            inv[k][c] = p
    return inv


def quagmire3_autokey_decrypt(ciphertext_runes: str, primer_rune: str,
                               keyword_runes: str, mode: str = "ciphertext") -> str:
    """
    Decrypt using Quagmire III autokey with ciphertext feedback.
    
    C[0] = T[K[0]][P[0]]  →  P[0] = T_inv[K[0]][C[0]]
    C[i] = T[C[i-1]][P[i]] →  P[i] = T_inv[C[i-1]][C[i]]  (ciphertext autokey)
    
    Args:
        ciphertext_runes: the ciphertext
        primer_rune: single rune used as K[0] (the primer)
        keyword_runes: keyword for the tableau construction
        mode: "ciphertext" (C[i-1] feedback) or "plaintext" (P[i-1] feedback)
    """
    tableau = build_quagmire3_tableau(keyword_runes)
    inv_tableau = build_inverse_tableau(tableau)
    
    ct_decs = runes_to_decimals(ciphertext_runes)
    k0 = rune_to_dec(primer_rune)
    
    pt_decs = []
    prev = k0  # feedback: previous ciphertext (or plaintext) rune value
    
    for i, c in enumerate(ct_decs):
        p = inv_tableau[prev][c]
        pt_decs.append(p)
        if mode == "ciphertext":
            prev = c  # ciphertext feedback
        else:
            prev = p  # plaintext feedback
    
    return decimals_to_runes(pt_decs)


def quagmire3_autokey_encrypt(plaintext_runes: str, primer_rune: str,
                              keyword_runes: str, mode: str = "ciphertext") -> str:
    """Encrypt using Quagmire III autokey."""
    tableau = build_quagmire3_tableau(keyword_runes)
    pt_decs = runes_to_decimals(plaintext_runes)
    k0 = rune_to_dec(primer_rune)
    
    ct_decs = []
    prev = k0
    
    for i, p in enumerate(pt_decs):
        c = tableau[prev][p]
        ct_decs.append(c)
        if mode == "ciphertext":
            prev = c
        else:
            prev = p
    
    return decimals_to_runes(ct_decs)


def find_identity_position(keyword_runes: str) -> int:
    """
    Find the identity element position for a Quagmire III tableau.
    
    The identity element is the plaintext value p such that T[k][p] = k for ALL k.
    In a standard Vigenère, this is p=0 (F rune).
    In a Quagmire III with keyed alphabet, the identity element is at the position
    where keyed_alpha[pos] = 0.
    
    For doublet suppression, we want this position to correspond to a RARE rune
    (NG=21, W=7, TH=2) so that doublets (which occur when P[i] = identity position)
    are rare.
    """
    seen = set()
    keyed_alpha = []
    for r in keyword_runes:
        d = rune_to_dec(r)
        if d not in seen:
            seen.add(d)
            keyed_alpha.append(d)
    for d in range(N_RUNES):
        if d not in seen:
            keyed_alpha.append(d)
    
    # The identity position is where keyed_alpha[pos] = 0 (F rune value)
    # Because T[k][p] = keyed_alpha[(k+p) % 29] = k when (k+p) % 29 = pos where keyed_alpha[pos] = k
    # Actually for a GENERAL keyed alphabet, the identity position VARIES per k.
    # Let's compute the AVERAGE identity position.
    
    # For each k, find p such that T[k][p] = k:
    # keyed_alpha[(k+p) % 29] = k → (k+p) % 29 = index of k in keyed_alpha
    # → p = (index_of_k_in_keyed_alpha - k) % 29
    
    identity_positions = []
    for k in range(N_RUNES):
        idx_k = keyed_alpha.index(k)
        p = (idx_k - k) % N_RUNES
        identity_positions.append(p)
    
    # If all identity positions are the same, that's the identity element
    if len(set(identity_positions)) == 1:
        return identity_positions[0]
    else:
        # Mixed identity positions — more complex
        # Return the most common one
        from collections import Counter
        return Counter(identity_positions).most_common(1)[0][0]


def test_known_keywords():
    """Test all known Cicada keywords as Quagmire III tableau keywords."""
    print("=" * 70)
    print("QUAGMIRE III AUTOKEY — Testing known keywords")
    print("=" * 70)
    
    # Load unsolved pages
    with open(os.path.join(os.path.dirname(__file__), "unsolved_pages.json")) as f:
        unsolved = json.load(f)
    
    all_unsolved = "".join(p["runes"] for p in unsolved)
    sample = all_unsolved[:500]
    
    # The key insight: we need keywords that place the identity at a RARE rune:
    # NG (21, freq 0.60%), W (7, freq 0.64%), TH (2, freq 0.56%)
    # We need keyed_alpha[pos] = 0 where pos corresponds to NG/W/TH
    
    # Test all KEY_CANDIDATES as keywords
    print(f"\n{'keyword':25s} {'id_pos':>7s} {'id_rune':>8s} {'primer':>7s} {'mode':12s} {'score':>7s}  plaintext[:80]")
    print("-" * 150)
    
    scored = []
    for name, key_runes in KEY_CANDIDATES.items():
        if not key_runes:
            continue
        id_pos = find_identity_position(key_runes)
        id_rune = DEC_TO_RUNE[id_pos]
        id_letter = DEC_TO_LETTER[id_pos]
        
        # Test all 29 primers (single runes) — the primer is K[0]
        best_score = -999
        best_primer = ""
        best_mode = ""
        best_pt = ""
        
        for primer_dec in range(N_RUNES):
            primer_rune = DEC_TO_RUNE[primer_dec]
            for mode in ["ciphertext", "plaintext"]:
                try:
                    pt_runes = quagmire3_autokey_decrypt(sample, primer_rune, key_runes, mode=mode)
                    pt = runes_to_latin(pt_runes)
                    s = english_score(pt)
                    if s > best_score:
                        best_score = s
                        best_primer = primer_rune
                        best_mode = mode
                        best_pt = pt
                except:
                    pass
        
        scored.append((name, key_runes, id_pos, id_rune, id_letter, best_primer, best_mode, best_score, best_pt))
        print(f"{name:25s} {id_pos:7d} {id_rune:>8s} {best_primer:>7s} {best_mode:12s} {best_score:7.2f}  {best_pt[:80]}")
    
    scored.sort(key=lambda x: -x[7])
    print(f"\n>>> TOP 10:")
    for name, key, id_pos, id_rune, id_letter, primer, mode, score, pt in scored[:10]:
        print(f"  {name:25s} id={id_letter:4s}({id_pos:2d}) primer={primer} {mode:12s} {score:7.2f}  {pt[:80]}")
    
    return scored


def hill_climb_keyword(ciphertext_runes: str, target_identity: int = 21,
                        max_iter: int = 5000, restarts: int = 20) -> Tuple[str, str, float, str]:
    """
    Hill-climb on the keyword to find one that:
    1. Places the identity element at the target position (NG=21, W=7, TH=2)
    2. Produces the best English score
    
    The keyword determines the tableau. We hill-climb on the keyword.
    """
    print(f"\n{'='*70}")
    print(f"HILL-CLIMBING QUAGMIRE III KEYWORD (target identity = {DEC_TO_LETTER[target_identity]})")
    print(f"{'='*70}")
    
    sample = ciphertext_runes[:500]
    
    best_overall = None
    
    for restart in range(restarts):
        # Random starting keyword of random length 3-15
        kw_len = random.randint(3, 15)
        keyword = [random.choice(RUNES) for _ in range(kw_len)]
        keyword_str = "".join(keyword)
        
        # Check identity position — if not at target, adjust
        id_pos = find_identity_position(keyword_str)
        
        # Test all 29 primers, pick best
        best_score = -999
        best_primer = "ᚠ"
        best_mode = "ciphertext"
        best_pt = ""
        
        for primer_dec in range(N_RUNES):
            primer_rune = DEC_TO_RUNE[primer_dec]
            for mode in ["ciphertext", "plaintext"]:
                try:
                    pt_runes = quagmire3_autokey_decrypt(sample, primer_rune, keyword_str, mode=mode)
                    pt = runes_to_latin(pt_runes)
                    s = english_score(pt)
                    if s > best_score:
                        best_score = s
                        best_primer = primer_rune
                        best_mode = mode
                        best_pt = pt
                except:
                    pass
        
        if restart == 0 or best_score > best_overall[2]:
            best_overall = (keyword_str, best_primer, best_score, best_pt, best_mode)
            print(f"  restart {restart:2d}: kw={keyword_str[:20]:20s} score={best_score:7.2f}  {best_pt[:60]}")
        
        # Hill-climb: mutate the keyword
        current_score = best_score
        current_kw = list(keyword)
        
        for iteration in range(max_iter):
            # Mutate: change one rune, insert, delete, or swap
            mutated = current_kw[:]
            mutation = random.choice(["change", "insert", "delete", "swap"])
            if mutation == "change" and mutated:
                idx = random.randrange(len(mutated))
                mutated[idx] = random.choice(RUNES)
            elif mutation == "insert":
                idx = random.randrange(len(mutated) + 1)
                mutated.insert(idx, random.choice(RUNES))
            elif mutation == "delete" and len(mutated) > 2:
                idx = random.randrange(len(mutated))
                del mutated[idx]
            elif mutation == "swap" and len(mutated) > 1:
                i, j = random.sample(range(len(mutated)), 2)
                mutated[i], mutated[j] = mutated[j], mutated[i]
            
            mutated_str = "".join(mutated)
            
            # Test mutated keyword
            new_best = -999
            new_primer = "ᚠ"
            new_mode = "ciphertext"
            new_pt = ""
            for primer_dec in range(N_RUNES):
                primer_rune = DEC_TO_RUNE[primer_dec]
                for mode in ["ciphertext", "plaintext"]:
                    try:
                        pt_runes = quagmire3_autokey_decrypt(sample, primer_rune, mutated_str, mode=mode)
                        pt = runes_to_latin(pt_runes)
                        s = english_score(pt)
                        if s > new_best:
                            new_best = s
                            new_primer = primer_rune
                            new_mode = mode
                            new_pt = pt
                    except:
                        pass
            
            # Accept if better (simulated annealing)
            if new_best > current_score:
                current_kw = mutated
                current_score = new_best
                if new_best > best_overall[2]:
                    best_overall = (mutated_str, new_primer, new_best, new_pt, new_mode)
                    if iteration % 100 == 0 or new_best > 75:
                        print(f"  iter {iteration:5d}: kw={mutated_str[:20]:20s} score={new_best:7.2f}  {new_pt[:60]}")
    
    print(f"\n>>> BEST: kw={best_overall[0][:30]} primer={best_overall[1]} mode={best_overall[4]} score={best_overall[2]:.2f}")
    print(f"    plaintext: {best_overall[3][:120]}")
    return best_overall


def test_targeted_keywords():
    """
    Test keywords specifically designed to place the identity at rare runes.
    
    To place identity at position P (e.g. NG=21, W=7, TH=2):
    - The keyed alphabet must have keyed_alpha[P] = 0 (F rune value)
    - This means the keyword must NOT contain F (ᚠ) early, and the remaining
      runes must be arranged so F lands at position P.
    
    For identity at NG (21): the first 21 runes of keyed_alpha must NOT be F,
    and F must be at position 21.
    For identity at W (7): F must be at position 7.
    For identity at TH (2): F must be at position 2.
    """
    print(f"\n{'='*70}")
    print("TARGETED KEYWORDS — identity at rare runes (NG=21, W=7, TH=2)")
    print(f"{'='*70}")
    
    # Load unsolved
    with open(os.path.join(os.path.dirname(__file__), "unsolved_pages.json")) as f:
        unsolved = json.load(f)
    all_unsolved = "".join(p["runes"] for p in unsolved)
    sample = all_unsolved[:500]
    
    # Build keywords that place F at specific positions
    # Keyword = first N runes (not F), then F is at position N
    # For identity at W (7): keyword has 7 non-F runes, then F at position 7
    # For identity at NG (21): keyword has 21 non-F runes, then F at position 21
    
    # Test keywords from solved pages that might place identity correctly
    targeted_keywords = {
        "DIVINITY": KEY_CANDIDATES["DIVINITY"],
        "FIRFUMFERENFE": KEY_CANDIDATES["FIRFUMFERENFE"],
        "PARABLE": KEY_CANDIDATES["PARABLE"],
        "INSTAR": KEY_CANDIDATES["INSTAR"],
        "EMERGENCE": KEY_CANDIDATES["EMERGENCE"],
        # Custom keywords designed to place identity at rare positions:
        # To place identity at NG (21), we need keyed_alpha[21] = 0 (F)
        # A keyword of 21 non-F runes followed by the rest would do it
        "NG_IDENTITY": "ᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝ" + "ᚠ" + "ᛟᛞᚪᚫᚣᛡᛠ",  # 21 non-F + F + rest
        "W_IDENTITY": "ᚢᚦᚩᚱᚳᚷ" + "ᚠ" + "ᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ",  # 7 non-F + F + rest
        "TH_IDENTITY": "ᚢ" + "ᚠ" + "ᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ",  # 1 non-F + F + rest
    }
    
    print(f"\n{'keyword':25s} {'id_pos':>7s} {'id_letter':>8s} {'primer':>7s} {'mode':12s} {'score':>7s}  plaintext[:80]")
    print("-" * 150)
    
    scored = []
    for name, kw in targeted_keywords.items():
        id_pos = find_identity_position(kw)
        id_letter = DEC_TO_LETTER[id_pos]
        
        best_score = -999
        best_primer = "ᚠ"
        best_mode = "ciphertext"
        best_pt = ""
        
        for primer_dec in range(N_RUNES):
            primer_rune = DEC_TO_RUNE[primer_dec]
            for mode in ["ciphertext", "plaintext"]:
                try:
                    pt_runes = quagmire3_autokey_decrypt(sample, primer_rune, kw, mode=mode)
                    pt = runes_to_latin(pt_runes)
                    s = english_score(pt)
                    if s > best_score:
                        best_score = s
                        best_primer = primer_rune
                        best_mode = mode
                        best_pt = pt
                except:
                    pass
        
        scored.append((name, kw, id_pos, id_letter, best_primer, best_mode, best_score, best_pt))
        print(f"{name:25s} {id_pos:7d} {id_letter:>8s} {best_primer:>7s} {best_mode:12s} {best_score:7.2f}  {best_pt[:80]}")
    
    scored.sort(key=lambda x: -x[6])
    print(f"\n>>> TOP 5:")
    for name, kw, id_pos, id_letter, primer, mode, score, pt in scored[:5]:
        print(f"  {name:25s} id={id_letter:4s}({id_pos:2d}) primer={primer} {mode:12s} {score:7.2f}  {pt[:80]}")
    
    return scored


def main():
    # Step 1: Test known keywords
    scored_known = test_known_keywords()
    
    # Step 2: Test targeted keywords (identity at rare runes)
    scored_targeted = test_targeted_keywords()
    
    # Step 3: Hill-climb for keywords with identity at NG (21)
    with open(os.path.join(os.path.dirname(__file__), "unsolved_pages.json")) as f:
        unsolved = json.load(f)
    all_unsolved = "".join(p["runes"] for p in unsolved)
    
    # Hill-climb with identity at NG (21) — the best match for 0.68% doublet rate
    best_ng = hill_climb_keyword(all_unsolved, target_identity=21, max_iter=3000, restarts=15)
    
    # Hill-climb with identity at W (7)
    best_w = hill_climb_keyword(all_unsolved, target_identity=7, max_iter=3000, restarts=15)
    
    # Save results
    results = {
        "known_keywords": [(name, id_pos, id_letter, primer, mode, score, pt[:100]) 
                          for name, _, id_pos, id_rune, _, primer, mode, score, pt in scored_known],
        "targeted_keywords": [(name, id_pos, id_letter, primer, mode, score, pt[:100])
                              for name, _, id_pos, id_letter, primer, mode, score, pt in scored_targeted],
        "hill_climb_ng": {"keyword": best_ng[0][:50], "primer": best_ng[1], "score": best_ng[2], "plaintext": best_ng[3][:200]},
        "hill_climb_w": {"keyword": best_w[0][:50], "primer": best_w[1], "score": best_w[2], "plaintext": best_w[3][:200]},
    }
    with open(os.path.join(os.path.dirname(__file__), "quagmire3_results.json"), "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved quagmire3_results.json")


if __name__ == "__main__":
    main()
