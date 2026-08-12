#!/usr/bin/env python3
"""
run_attacks.py — Lean runner for ALL cipher attacks, writes JSON results.
Skips the slow Kasiski examination of full corpus; does Kasiski on n>=6 grams only.
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
from math import gcd

DECODER_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    t0 = time.time()
    out = {}
    with open(LP_TXT) as f:
        text = f.read()
    pages = parse_liber_primus(text)
    out["n_page_sections"] = len(pages)
    unsolved = [p for p in pages if not p["is_solved"] and p["runes"]]
    solved   = [p for p in pages if p["is_solved"] and p["runes"]]
    out["n_unsolved_sections"] = len(unsolved)
    out["n_solved_sections"] = len(solved)
    all_unsolved = "".join(p["runes"] for p in unsolved)
    out["n_total_unsolved_runes"] = len(all_unsolved)
    print(f"Loaded {len(pages)} sections; unsolved runes = {len(all_unsolved)}")

    # ---------------- STEP 1: VERIFY ----------------
    print("\n[STEP 1] Verify solved pages...")
    verify_results = verify_solved(pages)
    out["verification"] = {k: bool(v) if v is not None else None for k, v in verify_results.items()}
    out["verification_pass"] = sum(1 for v in verify_results.values() if v is True)
    out["verification_fail"] = sum(1 for v in verify_results.values() if v is False)
    out["verification_skip"] = sum(1 for v in verify_results.values() if v is None)

    # ---------------- STEP 2: GLOBAL FREQUENCY ----------------
    print("\n[STEP 2] Global frequency analysis...")
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
    # Search for DJUBEI and OUNWM specifically
    decs = runes_to_decimals(all_unsolved)
    # DJUBEI = D(23) J(11) U(1) B(17) E(18) I(10)
    djubei = [23, 11, 1, 17, 18, 10]
    # OUNWM = O(3) U(1) N(9) W(7) M(19)
    ounwm = [3, 1, 9, 7, 19]
    def count_subseq(haystack, needle):
        n, m = len(haystack), len(needle)
        cnt = 0
        positions = []
        for i in range(n - m + 1):
            if all(haystack[i+j] == needle[j] for j in range(m)):
                cnt += 1
                positions.append(i)
        return cnt, positions
    dju_cnt, dju_pos = count_subseq(decs, djubei)
    oum_cnt, oum_pos = count_subseq(decs, ounwm)
    out["global_frequency"]["DJUBEI_count"] = dju_cnt
    out["global_frequency"]["DJUBEI_positions"] = dju_pos
    out["global_frequency"]["OUNWM_count"] = oum_cnt
    out["global_frequency"]["OUNWM_positions"] = oum_pos
    if oum_cnt >= 2:
        out["global_frequency"]["OUNWM_distance"] = oum_pos[1] - oum_pos[0]
    print(f"  DJUBEI count: {dju_cnt}  positions: {dju_pos}")
    print(f"  OUNWM count:  {oum_cnt}  positions: {oum_pos}")

    # Per-section frequency
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

    # ---------------- STEP 3a: Direct + Atbash + Caesar shifts ----------------
    print("\n[STEP 3a] Direct + Atbash + Caesar shifts...")
    sample = all_unsolved[:300]
    out["step3a_direct_atbash_caesar"] = []
    pt = runes_to_latin(sample)
    out["step3a_direct_atbash_caesar"].append({
        "method": "direct",
        "shift": 0,
        "score": english_score(pt),
        "plaintext": pt,
    })
    pt = runes_to_latin(atbash(sample))
    out["step3a_direct_atbash_caesar"].append({
        "method": "atbash",
        "shift": 0,
        "score": english_score(pt),
        "plaintext": pt,
    })
    for shift in [1, 2, 3, 5, 7, 13, 15, 28]:
        pt_runes = caesar(sample, shift, decrypt=True)
        pt = runes_to_latin(pt_runes)
        out["step3a_direct_atbash_caesar"].append({
            "method": "caesar_decrypt",
            "shift": shift,
            "score": english_score(pt),
            "plaintext": pt,
        })
    # Also encrypt direction (some sources define the operation reversed)
    for shift in [1, 3, 7, 13, 15, 28]:
        pt_runes = caesar(sample, shift, decrypt=False)
        pt = runes_to_latin(pt_runes)
        out["step3a_direct_atbash_caesar"].append({
            "method": "caesar_encrypt",
            "shift": shift,
            "score": english_score(pt),
            "plaintext": pt,
        })

    # ---------------- STEP 3b: Pure Vigenère with all 20 keys ----------------
    print("\n[STEP 3b] Vigenère with all 20 keys...")
    out["step3b_vigenere"] = []
    for name, key_runes in KEY_CANDIDATES.items():
        try:
            pt_runes = vigenere(sample, key_runes, skip_indices=set(), decrypt=True, f_skip_rule=False)
            pt = runes_to_latin(pt_runes)
            s = english_score(pt)
            out["step3b_vigenere"].append({
                "key": name, "key_runes": key_runes,
                "score": s, "plaintext": pt,
            })
        except Exception as e:
            out["step3b_vigenere"].append({"key": name, "error": str(e)})
    out["step3b_vigenere_top10"] = sorted(
        [r for r in out["step3b_vigenere"] if "error" not in r],
        key=lambda x: -x["score"]
    )[:10]

    # ---------------- STEP 3c: AUTOKEY with all 20 keys × 2 modes ----------------
    print("\n[STEP 3c] Autokey Vigenère with all 20 keys × 2 modes...")
    out["step3c_autokey"] = []
    for name, key_runes in KEY_CANDIDATES.items():
        for mode in ["plaintext", "ciphertext"]:
            try:
                pt_runes = autokey_vigenere(sample, key_runes, mode=mode, decrypt=True)
                pt = runes_to_latin(pt_runes)
                s = english_score(pt)
                out["step3c_autokey"].append({
                    "key": name, "key_runes": key_runes, "mode": mode,
                    "score": s, "plaintext": pt,
                })
            except Exception as e:
                out["step3c_autokey"].append({"key": name, "mode": mode, "error": str(e)})
    out["step3c_autokey_top10"] = sorted(
        [r for r in out["step3c_autokey"] if "error" not in r],
        key=lambda x: -x["score"]
    )[:10]
    # Flag potential breaks: score > 5.0
    out["step3c_autokey_breaks"] = [
        r for r in out["step3c_autokey"] if "error" not in r and r["score"] > 5.0
    ]

    # ---------------- STEP 3d: Prime-Fib mesh — all 6 formulations ----------------
    print("\n[STEP 3d] Prime-Fibonacci meshed stream cipher (6 formulations)...")
    out["step3d_prime_fib"] = []
    for form in ["prime_only", "fib_only", "add", "interleave", "prime_idx_fib", "totient_sum"]:
        try:
            pt_runes = prime_fib_mesh(sample, formulation=form, decrypt=True)
            pt = runes_to_latin(pt_runes)
            s = english_score(pt)
            out["step3d_prime_fib"].append({
                "formulation": form, "score": s, "plaintext": pt,
            })
        except Exception as e:
            out["step3d_prime_fib"].append({"formulation": form, "error": str(e)})
    out["step3d_prime_fib_top3"] = sorted(
        [r for r in out["step3d_prime_fib"] if "error" not in r],
        key=lambda x: -x["score"]
    )[:3]

    # ---------------- STEP 4: PER-SECTION BEST AUTOKEY ----------------
    print("\n[STEP 4] Per-section best autokey result...")
    out["step4_per_section_best_autokey"] = []
    for p in unsolved:
        sample_p = p["runes"][:300]
        if len(sample_p) < 20:
            sample_p = p["runes"]  # use what's available for very short sections
        best = None
        for name, key_runes in KEY_CANDIDATES.items():
            for mode in ["plaintext", "ciphertext"]:
                try:
                    pt_runes = autokey_vigenere(sample_p, key_runes, mode=mode, decrypt=True)
                    pt = runes_to_latin(pt_runes)
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

    # ---------------- STEP 5: KASISKI (focused — repeated 5-grams and 6-grams only) ----------------
    print("\n[STEP 5] Kasiski examination (n=5,6 repeated grams with GCD)...")
    decs = runes_to_decimals(all_unsolved)
    n = len(decs)
    kas_results = []
    for ng in [5, 6]:
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
                # factorize
                f = {}
                nn = g_gcd
                dd = 2
                while dd * dd <= nn:
                    while nn % dd == 0:
                        f[dd] = f.get(dd, 0) + 1
                        nn //= dd
                    dd += 1
                if nn > 1:
                    f[nn] = f.get(nn, 0) + 1
                kas_results.append({
                    "n_gram": ng,
                    "gram": "".join(dec_to_rune(x) for x in g),
                    "gram_latin": decimals_to_latin(g),
                    "positions": positions[:5],  # first 5
                    "n_occurrences": len(positions),
                    "distances": dists[:5],
                    "gcd": g_gcd,
                    "factorization": f,
                })
    # Sort by number of occurrences descending, then by n-gram descending
    kas_results.sort(key=lambda r: (-r["n_occurrences"], -r["n_gram"], r["gcd"]))
    # Filter to those with at least 2 occurrences
    out["step5_kasiski"] = kas_results[:30]  # top 30
    # Specifically look for OUNWM (the 5-gram at distance 1031)
    out["step5_ounwm_specific"] = {
        "n_gram": 5,
        "gram": "ᚩᚢᚾᚹᛗ",
        "gram_latin": "OUNWM",
        "positions": oum_pos,
        "n_occurrences": oum_cnt,
        "distances": [oum_pos[i+1] - oum_pos[i] for i in range(len(oum_pos)-1)] if oum_cnt > 1 else [],
        "gcd": (oum_pos[1] - oum_pos[0]) if oum_cnt > 1 else None,
        "factorization_note": "1031 is prime; one of the three prime factors of 1,595,277,641 = 1259 × 1031 × 1229 (parable product)",
    }
    # Specifically look for DJUBEI
    out["step5_djubei_specific"] = {
        "n_gram": 6,
        "gram": "ᛞᛄᚢᛒᛖᛁ",
        "gram_latin": "DJUBEI",
        "positions": dju_pos,
        "n_occurrences": dju_cnt,
        "distances": [dju_pos[i+1] - dju_pos[i] for i in range(len(dju_pos)-1)] if dju_cnt > 1 else [],
    }

    # Candidate key lengths from Kasiski GCDs (smallest factor that's plausible)
    gcds = [k["gcd"] for k in kas_results if k["gcd"] > 1]
    from collections import Counter as Ctr
    gcd_counts = Ctr(gcds)
    out["step5_kasiski_candidate_key_lengths"] = gcd_counts.most_common(15)

    # ---------------- Save ----------------
    out["elapsed_seconds"] = time.time() - t0
    out_path = os.path.join(DECODER_DIR, "attack_results.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {out_path}")
    print(f"Elapsed: {out['elapsed_seconds']:.1f}s")


if __name__ == "__main__":
    main()
