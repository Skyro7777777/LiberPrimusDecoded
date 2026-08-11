#!/usr/bin/env python3
"""
save_results.py — Run all attacks and save consolidated results to JSON.
"""
import sys, os, json, time
from math import gcd
from collections import Counter as Ctr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_pages import LP_TXT, parse_liber_primus
from gematria_primus import (
    runes_to_decimals, decimals_to_latin, dec_to_rune, runes_to_latin,
    atbash, caesar, vigenere, autokey_vigenere, prime_fib_mesh,
    frequency_analysis, english_score, KEY_CANDIDATES,
)
from verify_and_analyze import verify_solved

DECODER_DIR = os.path.dirname(os.path.abspath(__file__))

def factorize(n):
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

def main():
    out = {}
    with open(LP_TXT) as f:
        text = f.read()
    pages = parse_liber_primus(text)
    unsolved = [p for p in pages if not p["is_solved"] and p["runes"]]
    solved = [p for p in pages if p["is_solved"] and p["runes"]]
    all_unsolved = "".join(p["runes"] for p in unsolved)
    out["n_page_sections"] = len(pages)
    out["n_unsolved_sections"] = len(unsolved)
    out["n_solved_sections"] = len(solved)
    out["n_total_unsolved_runes"] = len(all_unsolved)

    # STEP 1: VERIFY
    verify_results = verify_solved(pages)
    out["verification"] = {k: bool(v) if v is not None else None for k, v in verify_results.items()}
    out["verification_pass_count"] = sum(1 for v in verify_results.values() if v is True)
    out["verification_fail_count"] = sum(1 for v in verify_results.values() if v is False)

    # STEP 2: GLOBAL FREQUENCY
    fa = frequency_analysis(all_unsolved)
    out["global_frequency"] = {
        "n_runes": fa["n_runes"],
        "IC": fa["IC"],
        "IC_normalized": fa["IC_normalized"],
        "doublets": fa["doublets"],
        "doublet_rate": fa["doublet_rate"],
        "random_doublet_rate": fa["random_doublet_rate"],
        "doublet_suppression_factor": fa["doublet_suppression_factor"],
        "n_unique_bigrams": fa["bigrams"]["n_unique"],
        "n_unique_trigrams": fa["trigrams"]["n_unique"],
        "n_unique_quadgrams": fa["quadgrams"]["n_unique"],
        "n_repeated_quadgrams": fa["quadgrams"]["n_repeated_types"],
        "n_repeated_pentagrams": fa["pentagrams"]["n_repeated_types"],
        "n_repeated_hexagrams": fa["hexagrams"]["n_repeated_types"],
        "top_hexagrams": [
            {"gram": "".join(dec_to_rune(x) for x in g),
             "latin": decimals_to_latin(g),
             "count": c}
            for g, c in fa["hexagrams"]["top_5"]
        ],
    }
    decs = runes_to_decimals(all_unsolved)
    djubei = [23, 11, 1, 17, 18, 10]
    ounwm = [3, 1, 9, 7, 19]
    def find_all(hay, needle):
        return [i for i in range(len(hay) - len(needle) + 1)
                if all(hay[i+j] == needle[j] for j in range(len(needle)))]
    dju_pos = find_all(decs, djubei)
    oum_pos = find_all(decs, ounwm)
    out["global_frequency"]["DJUBEI_count"] = len(dju_pos)
    out["global_frequency"]["DJUBEI_positions"] = dju_pos
    out["global_frequency"]["OUNWM_count"] = len(oum_pos)
    out["global_frequency"]["OUNWM_positions"] = oum_pos
    if len(oum_pos) >= 2:
        out["global_frequency"]["OUNWM_distance"] = oum_pos[1] - oum_pos[0]

    out["per_section_frequency"] = []
    for p in unsolved:
        fa_p = frequency_analysis(p["runes"])
        out["per_section_frequency"].append({
            "page_id": p["page_id"],
            "header": p["header"],
            "n_runes": p["n_runes"],
            "IC_normalized": fa_p["IC_normalized"],
            "doublet_rate": fa_p["doublet_rate"],
            "n_repeated_quadgrams": fa_p["quadgrams"]["n_repeated_types"],
            "n_repeated_hexagrams": fa_p["hexagrams"]["n_repeated_types"],
        })

    # STEP 3a
    sample = all_unsolved[:300]
    out["step3a_direct_atbash_caesar"] = []
    pt = runes_to_latin(sample)
    out["step3a_direct_atbash_caesar"].append(
        {"method": "direct", "shift": 0, "score": english_score(pt), "plaintext": pt})
    pt = runes_to_latin(atbash(sample))
    out["step3a_direct_atbash_caesar"].append(
        {"method": "atbash", "shift": 0, "score": english_score(pt), "plaintext": pt})
    for shift in [1, 2, 3, 5, 7, 13, 15, 28]:
        pt = runes_to_latin(caesar(sample, shift, decrypt=True))
        out["step3a_direct_atbash_caesar"].append(
            {"method": "caesar_decrypt", "shift": shift, "score": english_score(pt), "plaintext": pt})
    for shift in [1, 3, 7, 13, 15, 28]:
        pt = runes_to_latin(caesar(sample, shift, decrypt=False))
        out["step3a_direct_atbash_caesar"].append(
            {"method": "caesar_encrypt", "shift": shift, "score": english_score(pt), "plaintext": pt})

    # STEP 3b
    out["step3b_vigenere"] = []
    for name, key_runes in KEY_CANDIDATES.items():
        pt = runes_to_latin(vigenere(sample, key_runes, skip_indices=set(), decrypt=True, f_skip_rule=False))
        out["step3b_vigenere"].append({"key": name, "score": english_score(pt), "plaintext": pt})
    out["step3b_vigenere_top10"] = sorted(out["step3b_vigenere"], key=lambda x: -x["score"])[:10]

    # STEP 3c
    out["step3c_autokey"] = []
    for name, key_runes in KEY_CANDIDATES.items():
        for mode in ["plaintext", "ciphertext"]:
            pt = runes_to_latin(autokey_vigenere(sample, key_runes, mode=mode, decrypt=True))
            out["step3c_autokey"].append(
                {"key": name, "mode": mode, "score": english_score(pt), "plaintext": pt})
    out["step3c_autokey_top10"] = sorted(out["step3c_autokey"], key=lambda x: -x["score"])[:10]

    # STEP 3d
    out["step3d_prime_fib"] = []
    for form in ["prime_only", "fib_only", "add", "interleave", "prime_idx_fib", "totient_sum"]:
        pt = runes_to_latin(prime_fib_mesh(sample, formulation=form, decrypt=True))
        out["step3d_prime_fib"].append({"formulation": form, "score": english_score(pt), "plaintext": pt})
    out["step3d_prime_fib_top3"] = sorted(out["step3d_prime_fib"], key=lambda x: -x["score"])[:3]

    # STEP 4: per-section best autokey
    out["step4_per_section_best_autokey"] = []
    for p in unsolved:
        sample_p = p["runes"][:300]
        if len(sample_p) < 20:
            sample_p = p["runes"]
        best = None
        for name, key_runes in KEY_CANDIDATES.items():
            for mode in ["plaintext", "ciphertext"]:
                try:
                    pt = runes_to_latin(autokey_vigenere(sample_p, key_runes, mode=mode, decrypt=True))
                    s = english_score(pt)
                    if best is None or s > best["score"]:
                        best = {
                            "page_id": p["page_id"],
                            "header": p["header"],
                            "n_runes_section": p["n_runes"],
                            "sample_size": len(sample_p),
                            "best_key": name,
                            "best_mode": mode,
                            "score": s,
                            "plaintext_snippet": pt[:80],
                        }
                except Exception:
                    pass
        if best:
            out["step4_per_section_best_autokey"].append(best)

    # STEP 5: Kasiski
    n = len(decs)
    kas_results = []
    for ng in [4, 5, 6]:
        gram_positions = {}
        for i in range(n - ng + 1):
            g = tuple(decs[i:i+ng])
            gram_positions.setdefault(g, []).append(i)
        for g, positions in gram_positions.items():
            if len(positions) >= 2:
                dists = [positions[j+1] - positions[j] for j in range(len(positions)-1)]
                g_gcd = dists[0]
                for d in dists[1:]:
                    g_gcd = gcd(g_gcd, d)
                kas_results.append({
                    "n_gram": ng,
                    "gram": "".join(dec_to_rune(x) for x in g),
                    "gram_latin": decimals_to_latin(g),
                    "positions": positions[:5],
                    "n_occurrences": len(positions),
                    "distances": dists[:5],
                    "gcd": g_gcd,
                    "factorization": factorize(g_gcd),
                })
    kas_results.sort(key=lambda r: (-r["n_gram"], -r["n_occurrences"]))
    out["step5_kasiski_top_by_ngram"] = kas_results[:25]
    kas_results.sort(key=lambda r: (-r["n_occurrences"], -r["n_gram"]))
    out["step5_kasiski_top_by_occ"] = kas_results[:30]
    gcds = [r["gcd"] for r in kas_results if r["gcd"] > 1]
    gcd_counts = Ctr(gcds)
    out["step5_kasiski_candidate_key_lengths"] = gcd_counts.most_common(15)
    out["step5_ounwm"] = {
        "n_gram": 5, "gram": "ᚩᚢᚾᚹᛗ", "gram_latin": "OUNWM",
        "positions": oum_pos, "n_occurrences": len(oum_pos),
        "distances": [oum_pos[i+1] - oum_pos[i] for i in range(len(oum_pos)-1)] if len(oum_pos) > 1 else [],
        "gcd": (oum_pos[1] - oum_pos[0]) if len(oum_pos) > 1 else None,
        "note": "1031 is prime; one of the three prime factors of 1,595,277,641 = 1259 × 1031 × 1229",
    }
    out["step5_djubei"] = {
        "n_gram": 6, "gram": "ᛞᛄᚢᛒᛖᛁ", "gram_latin": "DJUBEI",
        "positions": dju_pos, "n_occurrences": len(dju_pos),
        "distances": [dju_pos[i+1] - dju_pos[i] for i in range(len(dju_pos)-1)] if len(dju_pos) > 1 else [],
        "gcd": (dju_pos[1] - dju_pos[0]) if len(dju_pos) > 1 else None,
        "note": "dis legomenon — longest repeated 6-gram in the entire unsolved corpus",
    }

    out_path = os.path.join(DECODER_DIR, "attack_results.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Saved {out_path}")
    print(f"Verification: {out['verification_pass_count']} pass, {out['verification_fail_count']} fail")
    print(f"Autokey top score: {out['step3c_autokey_top10'][0]['score']:.2f} ({out['step3c_autokey_top10'][0]['key']} / {out['step3c_autokey_top10'][0]['mode']})")
    print(f"OUNWM distance: {out['step5_ounwm']['gcd']}")

if __name__ == "__main__":
    main()
