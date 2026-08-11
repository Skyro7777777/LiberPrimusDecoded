#!/usr/bin/env python3
"""
fast_attacks.py — Fast cipher attacks on the 56 unsolved LP2 pages.
Skips the slow Kasiski examination; focuses on the highest-value cipher tests.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_LETTER, DEC_TO_RUNE, PRIMES, N_RUNES, MOD,
    is_rune, rune_to_dec, dec_to_rune, dec_to_letter,
    runes_to_decimals, decimals_to_runes, decimals_to_latin, runes_to_latin,
    direct_translate, atbash, caesar, vigenere, autokey_vigenere,
    prime_stream, prime_fib_mesh, book_cipher,
    frequency_analysis, english_score,
    KEY_CANDIDATES, _nth_prime, _nth_fib,
)
from extract_pages import LP_TXT, parse_liber_primus
from verify_and_analyze import verify_solved

DECODER_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(LP_TXT) as f:
        text = f.read()
    pages = parse_liber_primus(text)
    print(f"Loaded {len(pages)} page sections")

    # STEP 1 — verify (with fixed substring matching)
    verify_results = verify_solved(pages)

    # STEP 2 — frequency analysis (fast, no Kasiski)
    unsolved = [p for p in pages if not p["is_solved"] and p["runes"]]
    all_unsolved = "".join(p["runes"] for p in unsolved)
    print()
    print("=" * 70)
    print("GLOBAL FREQUENCY ANALYSIS (all 12,956 unsolved runes)")
    print("=" * 70)
    fa = frequency_analysis(all_unsolved)
    print(f"  Total runes:          {fa['n_runes']}")
    print(f"  IC (normalized):      {fa['IC_normalized']:.4f}  (random=1.0, English~1.73)")
    print(f"  Doublet rate:         {fa['doublet_rate']:.4%}  (random: {fa['random_doublet_rate']:.4%})")
    print(f"  Suppression factor:   {fa['doublet_suppression_factor']:.2f}x  (autokey if >3x)")
    print(f"  Bigrams unique:       {fa['bigrams']['n_unique']}  (random ~841)")
    print(f"  Trigrams unique:      {fa['trigrams']['n_unique']}  (random ~10050)")
    print(f"  Quadgrams unique:     {fa['quadgrams']['n_unique']}  (random ~12835)")
    print(f"  Quadgrams repeated:   {fa['quadgrams']['n_repeated_types']}  (random ~117)")
    print(f"  Pentagrams repeated:  {fa['pentagrams']['n_repeated_types']}")
    print(f"  Hexagrams repeated:   {fa['hexagrams']['n_repeated_types']}")
    print(f"  Top hexagrams (dis legomena):")
    for gram, count in fa['hexagrams']['top_5']:
        gram_str = "".join(dec_to_rune(x) for x in gram)
        gram_lat = decimals_to_latin(gram)
        print(f"    {gram_str} ({gram_lat})  x{count}")

    # STEP 3a — direct + simple shifts (sample)
    print()
    print("=" * 70)
    print("STEP 3a — DIRECT + SIMPLE SHIFTS (first 200 runes)")
    print("=" * 70)
    sample = all_unsolved[:200]
    print(f"Direct:    {runes_to_latin(sample)}")
    print(f"Atbash:    {runes_to_latin(atbash(sample))}")
    for shift in [1, 3, 7, 13, 15, 28]:
        pt = runes_to_latin(caesar(sample, shift, decrypt=True))
        s = english_score(pt)
        print(f"Caesar(-{shift:2d}): s={s:5.1f}  {pt[:70]}")

    # STEP 3b — Vigenère with all keys (no F-skip, first pass)
    print()
    print("=" * 70)
    print("STEP 3b — VIGENÈRE (no F-skip) with all key candidates [first 300 runes]")
    print("=" * 70)
    sample = all_unsolved[:300]
    print(f"{'key':25s} {'score':>7s}  plaintext[:90]")
    print("-" * 125)
    scored = []
    for name, key_runes in KEY_CANDIDATES.items():
        try:
            pt_runes = vigenere(sample, key_runes, skip_indices=set(), decrypt=True, f_skip_rule=False)
            pt = runes_to_latin(pt_runes)
            s = english_score(pt)
            scored.append((name, key_runes, s, pt))
            print(f"{name:25s} {s:7.2f}  {pt[:90]}")
        except Exception as e:
            print(f"{name:25s} ERROR: {e}")
    scored.sort(key=lambda x: -x[2])
    print(f"\n>>> TOP 5 VIGENÈRE:")
    for name, key, s, pt in scored[:5]:
        print(f"  {name:25s} {s:7.2f}  {pt[:90]}")

    # STEP 3c — Autokey Vigenère [HYPOTHESIS 8]
    print()
    print("=" * 70)
    print("STEP 3c — AUTOKEY VIGENÈRE [HYPOTHESIS 8] (first 300 runes)")
    print("=" * 70)
    print(f"{'key':25s} {'mode':12s} {'score':>7s}  plaintext[:90]")
    print("-" * 140)
    scored = []
    for name, key_runes in KEY_CANDIDATES.items():
        for mode in ["plaintext", "ciphertext"]:
            try:
                pt_runes = autokey_vigenere(sample, key_runes, mode=mode, decrypt=True)
                pt = runes_to_latin(pt_runes)
                s = english_score(pt)
                scored.append((name, mode, s, pt))
            except Exception as e:
                pass
    scored.sort(key=lambda x: -x[2])
    print(f">>> TOP 10 AUTOKEY:")
    for name, mode, s, pt in scored[:10]:
        print(f"  {name:25s} {mode:12s} {s:7.2f}  {pt[:90]}")

    # STEP 3d — Prime-Fibonacci mesh [HYPOTHESIS 9]
    print()
    print("=" * 70)
    print("STEP 3d — PRIME-FIBONACCI MESH [HYPOTHESIS 9] (first 300 runes)")
    print("=" * 70)
    formulations = ["prime_only", "fib_only", "add", "interleave",
                    "prime_idx_fib", "totient_sum"]
    scored = []
    for form in formulations:
        try:
            pt_runes = prime_fib_mesh(sample, formulation=form, decrypt=True)
            pt = runes_to_latin(pt_runes)
            s = english_score(pt)
            scored.append((form, s, pt))
            print(f"{form:20s} {s:7.2f}  {pt[:90]}")
        except Exception as e:
            print(f"{form:20s} ERROR: {e}")
    scored.sort(key=lambda x: -x[1])
    print(f"\n>>> TOP 3 PRIME-FIB:")
    for form, s, pt in scored[:3]:
        print(f"  {form:20s} {s:7.2f}  {pt[:90]}")

    # STEP 3e — Per-section best attack (find which key works best on which chapter)
    print()
    print("=" * 70)
    print("STEP 3e — PER-SECTION BEST AUTOKEY RESULT")
    print("=" * 70)
    print(f"{'section':30s} {'n':>5s} {'best_key':25s} {'mode':12s} {'score':>7s}  plaintext[:50]")
    print("-" * 140)
    for p in unsolved:
        sample = p["runes"][:200]
        best = None
        for name, key_runes in KEY_CANDIDATES.items():
            for mode in ["plaintext", "ciphertext"]:
                try:
                    pt_runes = autokey_vigenere(sample, key_runes, mode=mode, decrypt=True)
                    pt = runes_to_latin(pt_runes)
                    s = english_score(pt)
                    if best is None or s > best[3]:
                        best = (p["page_id"], name, mode, s, pt)
                except:
                    pass
        if best:
            print(f"  {best[0]:30s} {p['n_runes']:5d} {best[1]:25s} {best[2]:12s} {best[3]:7.2f}  {best[4][:50]}")

    # Save results
    results = {
        "verification": verify_results,
        "global_frequency": {
            "n_runes": fa["n_runes"],
            "IC_normalized": fa["IC_normalized"],
            "doublet_rate": fa["doublet_rate"],
            "doublet_suppression_factor": fa["doublet_suppression_factor"],
            "n_unique_bigrams": fa["bigrams"]["n_unique"],
            "n_unique_trigrams": fa["trigrams"]["n_unique"],
            "n_unique_quadgrams": fa["quadgrams"]["n_unique"],
            "n_repeated_quadgrams": fa["quadgrams"]["n_repeated_types"],
            "n_repeated_pentagrams": fa["pentagrams"]["n_repeated_types"],
            "n_repeated_hexagrams": fa["hexagrams"]["n_repeated_types"],
            "top_hexagrams": [
                {"gram": "".join(dec_to_rune(x) for x in g), "latin": decimals_to_latin(g), "count": c}
                for g, c in fa["hexagrams"]["top_5"]
            ],
        },
    }
    with open(os.path.join(DECODER_DIR, "analysis_results.json"), "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved analysis_results.json")


if __name__ == "__main__":
    main()
