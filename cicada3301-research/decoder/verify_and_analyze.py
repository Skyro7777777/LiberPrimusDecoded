#!/usr/bin/env python3
"""
verify_and_analyze.py — Verify toolkit against solved pages, then analyze unsolved pages.

Step 1: Verify all 12 solved pages decrypt to their expected plaintexts.
Step 2: Run frequency/IOC/doublet/Kasiski analysis on the 56 unsolved LP2 pages.
Step 3: Test all cipher methods + all key candidates against unsolved pages.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_LETTER, DEC_TO_RUNE, PRIMES, N_RUNES, MOD,
    is_rune, rune_to_dec, dec_to_rune, dec_to_letter,
    runes_to_decimals, decimals_to_runes, decimals_to_latin, runes_to_latin,
    direct_translate, atbash, caesar, vigenere, autokey_vigenere,
    prime_stream, prime_fib_mesh, book_cipher,
    frequency_analysis, kasiski_examination, english_score,
    KEY_CANDIDATES, _nth_prime, _nth_fib,
)
from extract_pages import LP_TXT, parse_liber_primus

DECODER_DIR = os.path.dirname(os.path.abspath(__file__))


def load_pages():
    with open(LP_TXT) as f:
        text = f.read()
    pages = parse_liber_primus(text)
    return pages


# ============================================================================
# STEP 1 — VERIFY SOLVED PAGES
# ============================================================================

def verify_solved(pages):
    """Verify the toolkit reproduces all solved-page plaintexts."""
    print("=" * 70)
    print("STEP 1 — VERIFY SOLVED PAGES")
    print("=" * 70)
    results = {}
    for p in pages:
        if not p["is_solved"] or not p["runes"]:
            continue
        pid = p["page_id"]
        ct = p["runes"]
        key_hint = p["key_hint"]
        print(f"\n[{pid}] key_hint: {key_hint[:80]}")
        print(f"  runes: {len(ct)}")

        # Determine method from key_hint
        kh = key_hint.lower()
        try:
            if "reversed gematria" in kh and "shift 3" in kh:
                # Pages 6-9: Atbash + shift 3
                step1 = atbash(ct)
                pt_runes = caesar(step1, 3, decrypt=False)  # +3 shift (encrypt direction = undo)
                pt = runes_to_latin(pt_runes)
                method = "atbash + caesar(+3)"
            elif "substitution with reversed gematria" in kh or "reversed gematria" in kh and "shift" not in kh:
                # Page 1 (Warning): Atbash only
                pt_runes = atbash(ct)
                pt = runes_to_latin(pt_runes)
                method = "atbash"
            elif "divinity" in kh:
                # Pages 3-4: Vigenère with DIVINITY key + F-skip
                # F-skip indices from dossier: {48, 74, 84, 132, 159, 160, 250, 421, 443, 465, 514}
                skip = {48, 74, 84, 132, 159, 160, 250, 421, 443, 465, 514}
                key = "ᛞᛁᚢᛁᚾᛁᛏᚣ"
                pt_runes = vigenere(ct, key, skip_indices=skip, decrypt=True)
                pt = runes_to_latin(pt_runes)
                method = "vigenere(DIVINITY, F-skip)"
            elif "continuation of key" in kh:
                # Page 4: continuation of DIVINITY
                skip = {48, 74, 84, 132, 159, 160, 250, 421, 443, 465, 514}
                key = "ᛞᛁᚢᛁᚾᛁᛏᚣ"
                pt_runes = vigenere(ct, key, skip_indices=skip, decrypt=True)
                pt = runes_to_latin(pt_runes)
                method = "vigenere(DIVINITY continuation)"
            elif "firfumferenfe" in kh or "29, 19, 25" in kh:
                # Pages 14-15: Vigenère with FIRFUMFERENFE + F-skip {49, 56}
                skip = {49, 56}
                key = "ᚠᛁᚱᚠᚢᛗᚠᛖᚱᛖᚾᚠᛖ"
                pt_runes = vigenere(ct, key, skip_indices=skip, decrypt=True)
                pt = runes_to_latin(pt_runes)
                method = "vigenere(FIRFUMFERENFE, F-skip)"
            elif "default gematria" in kh:
                # Pages 5, 10, 13, 16, 74: direct translation
                pt = runes_to_latin(ct)
                method = "direct"
            elif "phi(prime)" in kh or "phi (prime)" in kh:
                # Page 56 (73.jpg): prime-stream / totient
                skip = {56}  # 57th rune, 0-indexed 56
                pt_runes = prime_stream(ct, skip_indices=skip, decrypt=True)
                pt = runes_to_latin(pt_runes)
                method = "prime_stream (totient, F-skip@56)"
            else:
                pt = runes_to_latin(ct)
                method = "direct (default fallback)"

            print(f"  method: {method}")
            print(f"  plaintext[:120]: {pt[:120]}")

            # Check against expected
            expected_map = {
                "01.jpg": "A WARN",          # A WARNING (spelled WARNNG in source)
                "03.jpg": "WELCOME",
                "04.jpg": "IT IS THROVGH",    # continuation of Welcome
                "05.jpg": "SOME WISDOM",
                "06.jpg": "A COAN",
                "09.jpg": "ENLIGHTENED",      # end of Koan 1
                "10.jpg": "AN INSTRVCTIAN",   # index page
                "13.jpg": "CNOW THIS",        # magic square page
                "14.jpg": "A COAN",
                "16.jpg": "AN INSTRVCTIAN",
                "73.jpg": "AN END",
                "74.jpg": "PARABLE",
            }
            expected = expected_map.get(pid, "")
            if expected:
                # Strip spaces from both — our plaintext has no delimiters
                pt_nospace = pt.upper().replace(" ", "")
                expected_nospace = expected.upper().replace(" ", "")
                passed = expected_nospace in pt_nospace
                print(f"  expected substring: '{expected}' (nospace: '{expected_nospace}')")
                print(f"  {'✓ PASS' if passed else '✗ FAIL'}")
                results[pid] = passed
            else:
                results[pid] = None
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback; traceback.print_exc()
            results[pid] = False
    print()
    print("=" * 70)
    n_pass = sum(1 for v in results.values() if v is True)
    n_fail = sum(1 for v in results.values() if v is False)
    n_skip = sum(1 for v in results.values() if v is None)
    print(f"VERIFICATION SUMMARY: {n_pass} pass, {n_fail} fail, {n_skip} skip")
    print("=" * 70)
    return results


# ============================================================================
# STEP 2 — FREQUENCY ANALYSIS OF UNSOLVED PAGES
# ============================================================================

def analyze_unsolved(pages):
    """Run full frequency/IOC/doublet/Kasiski analysis on all unsolved pages."""
    print()
    print("=" * 70)
    print("STEP 2 — FREQUENCY ANALYSIS OF UNSOLVED LP2 PAGES")
    print("=" * 70)
    unsolved = [p for p in pages if not p["is_solved"] and p["runes"]]
    print(f"Unsolved sections: {len(unsolved)}")
    total_runes = sum(p["n_runes"] for p in unsolved)
    print(f"Total unsolved runes: {total_runes}  (CicadaSolvers expected: 12956)")

    # Concatenate all unsolved runes for global analysis
    all_unsolved = "".join(p["runes"] for p in unsolved)
    print(f"Concatenated length: {len(all_unsolved)}")

    print("\n--- GLOBAL ANALYSIS (all 56 unsolved LP2 pages) ---")
    fa = frequency_analysis(all_unsolved)
    print(f"  Total runes:          {fa['n_runes']}")
    print(f"  IC (raw):             {fa['IC']:.6f}")
    print(f"  IC (normalized):      {fa['IC_normalized']:.4f}  (random=1.0, English~1.73)")
    print(f"  Doublets:             {fa['doublets']}")
    print(f"  Doublet rate:         {fa['doublet_rate']:.4%}  (random baseline: {fa['random_doublet_rate']:.4%})")
    print(f"  Suppression factor:  {fa['doublet_suppression_factor']:.2f}x  (autokey signature if >3x)")
    print(f"  Bigrams unique:       {fa['bigrams']['n_unique']}  (random ~841)")
    print(f"  Bigrams repeated:     {fa['bigrams']['n_repeated_types']}  (random ~841)")
    print(f"  Trigrams unique:      {fa['trigrams']['n_unique']}  (random ~10050)")
    print(f"  Trigrams repeated:    {fa['trigrams']['n_repeated_types']}  (random ~2433)")
    print(f"  Quadgrams unique:     {fa['quadgrams']['n_unique']}  (random ~12835)")
    print(f"  Quadgrams repeated:   {fa['quadgrams']['n_repeated_types']}  (random ~117)")
    print(f"  Pentagrams repeated:  {fa['pentagrams']['n_repeated_types']}")
    print(f"  Hexagrams repeated:   {fa['hexagrams']['n_repeated_types']}")
    print(f"  Top 5 hexagrams (dis legomena candidates):")
    for gram, count in fa['hexagrams']['top_5']:
        gram_str = "".join(dec_to_rune(x) for x in gram)
        gram_lat = decimals_to_latin(gram)
        print(f"    {gram_str} ({gram_lat})  x{count}")

    print("\n--- PER-SECTION ANALYSIS ---")
    for p in unsolved:
        fa = frequency_analysis(p["runes"])
        print(f"  {p['page_id']:30s}  n={p['n_runes']:5d}  IC={fa['IC_normalized']:.3f}  "
              f"dbl={fa['doublet_rate']:.4%}  quad_rep={fa['quadgrams']['n_repeated_types']:3d}  "
              f"hex_rep={fa['hexagrams']['n_repeated_types']:2d}")

    print("\n--- KASISKI EXAMINATION (top repeated n-grams, candidate key lengths) ---")
    kas = kasiski_examination(all_unsolved, min_gram=4, max_gram=6)
    # Filter to grams repeated >=2 times, sort by n_gram desc then gcd
    kas_filtered = [k for k in kas if len(k["positions"]) >= 2][:20]
    for k in kas_filtered:
        print(f"  {k['n_gram']}gram  {k['gram']:8s}  {k['gram_latin']:12s}  "
              f"dist={k['distances']}  gcd={k['gcd']}  fact={k['factorization']}")
    return all_unsolved, fa


# ============================================================================
# STEP 3 — CIPHER ATTACKS ON UNSOLVED PAGES
# ============================================================================

def test_direct_and_simple_shifts(runes):
    """Test direct translation, all 28 Caesar shifts, Atbash."""
    print()
    print("=" * 70)
    print("STEP 3a — DIRECT TRANSLATION + SIMPLE SHIFTS")
    print("=" * 70)
    print(f"Testing on first 200 runes of unsolved corpus...")
    sample = runes[:200]
    print(f"\nDirect translation (first 200):")
    print(f"  {runes_to_latin(sample)}")
    print(f"\nAtbash then direct:")
    print(f"  {runes_to_latin(atbash(sample))}")
    for shift in [1, 2, 3, 5, 7, 13, 15, 28]:
        pt = runes_to_latin(caesar(sample, shift, decrypt=True))
        score = english_score(pt)
        print(f"  Caesar(-{shift:2d}): score={score:6.2f}  {pt[:80]}")


def test_vigenere_all_keys(runes):
    """Test pure Vigenère with all key candidates (no F-skip — first pass)."""
    print()
    print("=" * 70)
    print("STEP 3b — VIGENÈRE WITH KEY CANDIDATES (no F-skip, first 300 runes)")
    print("=" * 70)
    sample = runes[:300]
    print(f"{'key':25s} {'score':>7s}  plaintext[:80]")
    print("-" * 110)
    scored = []
    for name, key_runes in KEY_CANDIDATES.items():
        try:
            pt_runes = vigenere(sample, key_runes, skip_indices=set(), decrypt=True, f_skip_rule=False)
            pt = runes_to_latin(pt_runes)
            score = english_score(pt)
            scored.append((name, key_runes, score, pt))
            print(f"{name:25s} {score:7.2f}  {pt[:80]}")
        except Exception as e:
            print(f"{name:25s} ERROR: {e}")
    scored.sort(key=lambda x: -x[2])
    print(f"\nTop 5 by English score:")
    for name, key, score, pt in scored[:5]:
        print(f"  {name:25s} {score:7.2f}  {pt[:80]}")


def test_autokey_all_keys(runes):
    """Test autokey Vigenère (both modes) with all key candidates."""
    print()
    print("=" * 70)
    print("STEP 3c — AUTOKEY VIGENÈRE [HYPOTHESIS 8] (first 300 runes)")
    print("=" * 70)
    sample = runes[:300]
    print(f"{'key':25s} {'mode':12s} {'score':>7s}  plaintext[:80]")
    print("-" * 130)
    scored = []
    for name, key_runes in KEY_CANDIDATES.items():
        for mode in ["plaintext", "ciphertext"]:
            try:
                pt_runes = autokey_vigenere(sample, key_runes, mode=mode, decrypt=True)
                pt = runes_to_latin(pt_runes)
                score = english_score(pt)
                scored.append((name, key_runes, mode, score, pt))
                print(f"{name:25s} {mode:12s} {score:7.2f}  {pt[:80]}")
            except Exception as e:
                print(f"{name:25s} {mode:12s} ERROR: {e}")
    scored.sort(key=lambda x: -x[3])
    print(f"\nTop 10 by English score:")
    for name, key, mode, score, pt in scored[:10]:
        print(f"  {name:25s} {mode:12s} {score:7.2f}  {pt[:80]}")


def test_prime_fib_mesh(runes):
    """Test all Prime-Fibonacci meshed stream formulations."""
    print()
    print("=" * 70)
    print("STEP 3d — PRIME-FIBONACCI MESHED STREAM [HYPOTHESIS 9] (first 300 runes)")
    print("=" * 70)
    sample = runes[:300]
    formulations = ["prime_only", "fib_only", "add", "interleave",
                    "prime_idx_fib", "totient_sum"]
    print(f"{'formulation':20s} {'score':>7s}  plaintext[:80]")
    print("-" * 110)
    scored = []
    for form in formulations:
        try:
            pt_runes = prime_fib_mesh(sample, formulation=form, decrypt=True)
            pt = runes_to_latin(pt_runes)
            score = english_score(pt)
            scored.append((form, score, pt))
            print(f"{form:20s} {score:7.2f}  {pt[:80]}")
        except Exception as e:
            print(f"{form:20s} ERROR: {e}")
    scored.sort(key=lambda x: -x[1])
    print(f"\nTop 3 by English score:")
    for form, score, pt in scored[:3]:
        print(f"  {form:20s} {score:7.2f}  {pt[:80]}")


def main():
    pages = load_pages()
    print(f"Loaded {len(pages)} page sections from liber_primus.txt")

    # STEP 1
    verify_results = verify_solved(pages)

    # STEP 2
    all_unsolved, global_fa = analyze_unsolved(pages)

    # STEP 3
    test_direct_and_simple_shifts(all_unsolved)
    test_vigenere_all_keys(all_unsolved)
    test_autokey_all_keys(all_unsolved)
    test_prime_fib_mesh(all_unsolved)

    # Save analysis
    print()
    print("=" * 70)
    print("Saving analysis to decoder/analysis_results.json ...")
    results = {
        "verification": verify_results,
        "global_frequency": {
            "n_runes": global_fa["n_runes"],
            "IC_normalized": global_fa["IC_normalized"],
            "doublet_rate": global_fa["doublet_rate"],
            "doublet_suppression_factor": global_fa["doublet_suppression_factor"],
            "n_unique_bigrams": global_fa["bigrams"]["n_unique"],
            "n_unique_trigrams": global_fa["trigrams"]["n_unique"],
            "n_unique_quadgrams": global_fa["quadgrams"]["n_unique"],
            "top_hexagrams": [
                {"gram": "".join(dec_to_rune(x) for x in g), "latin": decimals_to_latin(g), "count": c}
                for g, c in global_fa["hexagrams"]["top_5"]
            ],
        },
    }
    with open(os.path.join(DECODER_DIR, "analysis_results.json"), "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("Done.")


if __name__ == "__main__":
    main()
