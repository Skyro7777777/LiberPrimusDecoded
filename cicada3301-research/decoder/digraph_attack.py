#!/usr/bin/env python3
"""
digraph_attack.py — Run all digraphic cipher attacks on the unsolved LP2 corpus
==============================================================================
Implements the full Task p2d attack plan:

PART A: Playfair (6x5 matrix, 29 runes + filler) — implemented in playfair.py
PART B: Playfair with 10+ candidate keys, decrypt first 200 runes (100 pairs).
PART C: Hill cipher (2x2 over Z_29) — magic-square sub-blocks + brute force + hill climbing.
PART D: Two-rune function decrypter — 8 variants.

Outputs:
  /home/z/my-project/cicada3301-research/decoder/digraph_results.json   (raw results)
  Results are then summarized in DIGRAPHIC_CIPHER_RESULTS.md.
"""
from __future__ import annotations
import sys
import json
import time
from typing import List, Dict, Tuple

sys.path.insert(0, "/home/z/my-project/cicada3301-research/decoder")
from gematria_primus import (
    RUNES, MOD, LETTERS, DEC_TO_RUNE, RUNE_TO_DEC, DEC_TO_LETTER,
    rune_to_dec, dec_to_rune, is_rune,
    clean_runes, runes_to_decimals, decimals_to_runes, runes_to_latin,
    english_score, KEY_CANDIDATES,
)
from playfair import build_matrix, matrix_to_str, playfair_decrypt, playfair_decrypt_to_latin, FILLER
from hill import (
    hill_decrypt, hill_encrypt, is_invertible, matrix_inverse_mod,
    brute_force_hill, hill_climb_hill, magic_square_sub_blocks, MAGIC_SQUARE_16,
)
from two_rune_functions import (
    TWO_RUNE_FUNCTIONS, apply_two_rune_function, test_all_two_rune_functions,
)

# ----------------------------------------------------------------------------
# Load the unsolved LP2 corpus
# ----------------------------------------------------------------------------
def load_corpus():
    with open("/home/z/my-project/cicada3301-research/decoder/unsolved_pages.json") as f:
        pages = json.load(f)
    # Filter to unsolved pages and concatenate runes
    unsolved = [p for p in pages if not p.get("is_solved", False)]
    corpus = "".join(p["runes"] for p in unsolved)
    return corpus, unsolved


def load_solved_page_runes(page_id: str):
    """Get runes of a specific solved page (e.g., '74.jpg' for the parable)."""
    with open("/home/z/my-project/cicada3301-research/decoder/solved_pages.json") as f:
        pages = json.load(f)
    for p in pages:
        if p.get("page_id") == page_id:
            return p["runes"]
    return None


# ----------------------------------------------------------------------------
# PART A & B — Playfair attacks
# ----------------------------------------------------------------------------

# Define Playfair keys per task spec.
def build_playfair_keys() -> List[Tuple[str, str]]:
    """Return list of (key_name, key_runes) tuples."""
    keys = []

    # 1. DIVINITY
    keys.append(("DIVINITY", "ᛞᛁᚢᛁᚾᛁᛏᚣ"))
    # 2. FIRFUMFERENFE
    keys.append(("FIRFUMFERENFE", "ᚠᛁᚱᚠᚢᛗᚠᛖᚱᛖᚾᚠᛖ"))
    # 3. PARABLE
    keys.append(("PARABLE", "ᛈᚪᚱᚪᛒᛚᛖ"))
    # 4. INSTAREMERGENCE (concatenated)
    keys.append(("INSTAREMERGENCE", "ᛁᚾᛋᛏᚪᚱᛖᛗᛖᚱᚷᛖᚾᚳᛖ"))
    # 5. Full parable text (from solved 74.jpg)
    parable_runes = load_solved_page_runes("74.jpg")
    if parable_runes:
        # Strip "PARABLE" header (first 7 runes ᛈᚪᚱᚪᛒᛚᛖ) to get the actual parable text
        parable_body = parable_runes[7:] if parable_runes.startswith("ᛈᚪᚱᚪᛒᛚᛖ") else parable_runes
        keys.append(("PARABLE_TEXT_FULL", parable_runes))          # 95 runes incl. header
        keys.append(("PARABLE_BODY", parable_body))                # 88 runes (body only)
    # 6. Instar Emergence poem — same as the parable body, but let's use it directly
    if parable_runes:
        keys.append(("INSTAR_EMERGENCE", parable_body))
    # 7. CIRCUMFERENCE
    keys.append(("CIRCUMFERENCE", "ᚳᛁᚱᚳᚢᛗᚠᛖᚱᛖᚾᚳᛖ"))
    # 8. WELCOME
    keys.append(("WELCOME", "ᚹᛖᛚᚳᚩᛗᛖ"))
    # 9. PRIMESACRED
    keys.append(("PRIMESACRED", "ᛈᚱᛁᛗᛖᛋᚪᚳᚱᛖᛞ"))
    # 10. Magic-square number sequences converted to runes (via mod 29)
    # Page-16 magic square (5 rows of 5 numbers each)
    ms16_rows = [
        ("MS16_ROW1", [434, 1311, 312, 278, 966]),
        ("MS16_ROW2", [204, 812, 934, 280, 1071]),
        ("MS16_ROW3", [626, 620, 809, 620, 626]),
        ("MS16_ROW4", [1071, 280, 934, 812, 204]),
        ("MS16_ROW5", [966, 278, 312, 1311, 434]),
    ]
    for name, nums in ms16_rows:
        runes = "".join(DEC_TO_RUNE[n % MOD] for n in nums)
        keys.append((name, runes))
    # Page-16 magic square as full flat sequence
    flat = [n for row in MAGIC_SQUARE_16 for n in row]
    keys.append(("MS16_FULL_FLAT", "".join(DEC_TO_RUNE[n % MOD] for n in flat)))
    # Page-5 magic square (partial — only first row of numbers known)
    keys.append(("MS5_ROW1", "".join(DEC_TO_RUNE[n % MOD] for n in [272, 138, 341, 131, 151])))

    return keys


def run_playfair_attacks(corpus: str, n_runes: int = 200) -> Dict:
    """Run Playfair attacks with all keys on the first n_runes of corpus."""
    keys = build_playfair_keys()
    results = []
    ct = corpus[:n_runes]
    for name, key_runes in keys:
        try:
            # Build matrix for documentation
            matrix = build_matrix(key_runes)
            matrix_str = matrix_to_str(matrix)
            # Decrypt
            pt_runes = playfair_decrypt(ct, key_runes, strip_filler=True)
            pt_latin = runes_to_latin(pt_runes)
            score = english_score(pt_latin)
            # Count fillers that were stripped (would indicate how often the cipher
            # produced a filler; lower = more "natural")
            pt_raw = playfair_decrypt(ct, key_runes, strip_filler=False)
            filler_count = pt_raw.count(FILLER)
            results.append({
                "key_name": name,
                "key_runes": key_runes,
                "key_len": len(clean_runes(key_runes)),
                "score": round(score, 4),
                "filler_count": filler_count,
                "plaintext_latin": pt_latin,
                "matrix": matrix_str,
            })
        except Exception as e:
            results.append({
                "key_name": name,
                "key_runes": key_runes,
                "error": str(e),
            })
    # Sort by score descending
    results.sort(key=lambda x: x.get("score", -1), reverse=True)
    return {"n_input_runes": n_runes, "n_pairs": n_runes // 2, "results": results}


# ----------------------------------------------------------------------------
# PART C — Hill cipher attacks
# ----------------------------------------------------------------------------

def run_hill_attacks(corpus: str, n_runes: int = 200,
                     brute_sample_size: Optional[int] = None,
                     hill_climb_starts: int = 50,
                     hill_climb_iters: int = 500,
                     brute_top_k: int = 10) -> Dict:
    """Run Hill cipher attacks: magic-square sub-blocks + brute-force + hill-climbing.

    If brute_sample_size is None (default), runs the FULL brute-force over all
    707,281 2x2 matrices (of which ~681,960 are invertible). Takes ~100 seconds.
    Otherwise samples the given number of random matrices.
    """
    ct = corpus[:n_runes]
    results = {"n_input_runes": n_runes, "n_pairs": n_runes // 2}

    # 1. Magic-square sub-blocks (16 contiguous + 4 corners)
    print("  [Hill] Testing magic-square sub-blocks...")
    ms_blocks = magic_square_sub_blocks()
    ms_results = []
    for name, M in ms_blocks:
        det = (M[0][0] * M[1][1] - M[0][1] * M[1][0]) % MOD
        if det == 0 or not is_invertible(M):
            ms_results.append({"name": name, "matrix": M, "det": det, "score": None,
                              "plaintext": None, "note": "non-invertible"})
            continue
        try:
            pt_latin = runes_to_latin(hill_decrypt(ct, M))
            score = english_score(pt_latin)
            ms_results.append({"name": name, "matrix": M, "det": det, "score": round(score, 4),
                              "plaintext": pt_latin})
        except Exception as e:
            ms_results.append({"name": name, "matrix": M, "det": det, "score": None,
                              "plaintext": None, "error": str(e)})
    ms_results.sort(key=lambda x: x.get("score", -1) if x.get("score") is not None else -1, reverse=True)
    results["magic_square_subblocks"] = ms_results

    # 2. Brute-force search (full or sampled)
    if brute_sample_size is None:
        print(f"  [Hill] FULL brute-force over all {MOD**4} matrices...")
    else:
        print(f"  [Hill] Sampled brute-force ({brute_sample_size} random matrices)...")
    t0 = time.time()
    top_results = brute_force_hill(ct, top_k=brute_top_k, sample_size=brute_sample_size, verbose=True)
    elapsed = time.time() - t0
    print(f"  [Hill]   done in {elapsed:.1f}s, top score = {top_results[0][1]:.4f}")
    results["brute_force"] = {
        "sample_size": brute_sample_size,   # None means full
        "n_matrices_tested": MOD ** 4 if brute_sample_size is None else brute_sample_size,
        "elapsed_seconds": round(elapsed, 2),
        "top": [
            {"matrix": M, "score": round(s, 4), "plaintext": pt}
            for M, s, pt in top_results
        ],
    }

    # 3. Hill climbing (heuristic search)
    print(f"  [Hill] Hill-climbing ({hill_climb_starts} starts, {hill_climb_iters} iters)...")
    t0 = time.time()
    best_M, best_score, best_pt = hill_climb_hill(
        ct, n_starts=hill_climb_starts, n_iters=hill_climb_iters, seed=42)
    elapsed = time.time() - t0
    print(f"  [Hill]   done in {elapsed:.1f}s, best score = {best_score:.4f}")
    results["hill_climbing"] = {
        "n_starts": hill_climb_starts,
        "n_iters": hill_climb_iters,
        "elapsed_seconds": round(elapsed, 2),
        "best_matrix": best_M,
        "best_score": round(best_score, 4),
        "best_plaintext": best_pt,
    }

    return results


# ----------------------------------------------------------------------------
# PART D — Two-rune function attacks
# ----------------------------------------------------------------------------

def run_two_rune_function_attacks(corpus: str, n_runes: int = 200) -> Dict:
    """Run all two-rune functions on the first n_runes of corpus."""
    ct = corpus[:n_runes]
    results = test_all_two_rune_functions(ct)
    return {
        "n_input_runes": n_runes,
        "n_pairs": n_runes // 2,
        "n_output_runes": n_runes // 2,
        "results": [
            {"function": name, "score": round(score, 4), "plaintext": pt}
            for name, score, pt in results
        ],
    }


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("DIGRAPHIC CIPHER ATTACKS — Cicada 3301 Liber Primus (Unsolved LP2)")
    print("=" * 70)
    print()

    corpus, unsolved_pages = load_corpus()
    print(f"Loaded unsolved corpus: {len(corpus)} runes across {len(unsolved_pages)} sections")
    print(f"Working on first 200 runes (100 pairs) of corpus.")
    print()

    # Take first 200 runes
    N_RUNES = 200
    ct = corpus[:N_RUNES]
    print(f"First 40 runes: {ct[:40]}")
    print()

    # ----- PART A & B: Playfair -----
    print("-" * 70)
    print("PART A & B: PLAYFAIR ATTACKS")
    print("-" * 70)
    playfair_results = run_playfair_attacks(corpus, n_runes=N_RUNES)
    print(f"Tested {len(playfair_results['results'])} Playfair keys.")
    print(f"Top 5 by english_score:")
    for i, r in enumerate(playfair_results["results"][:5]):
        print(f"  {i+1}. {r['key_name']:24s}  score={r['score']:.4f}  "
              f"keylen={r['key_len']}  fillers={r['filler_count']}")
        print(f"     PT[:80]: {r['plaintext_latin'][:80]}")
    print()

    # ----- PART C: Hill -----
    print("-" * 70)
    print("PART C: HILL CIPHER ATTACKS")
    print("-" * 70)
    hill_results = run_hill_attacks(corpus, n_runes=N_RUNES,
                                     brute_sample_size=None,    # FULL brute-force
                                     hill_climb_starts=50,
                                     hill_climb_iters=500,
                                     brute_top_k=10)
    print(f"Hill results summary:")
    print(f"  Magic-square sub-blocks: top score = "
          f"{hill_results['magic_square_subblocks'][0].get('score', 'N/A')}")
    print(f"  Full brute-force:        top score = "
          f"{hill_results['brute_force']['top'][0]['score']:.4f} "
          f"(tested {hill_results['brute_force']['n_matrices_tested']} matrices in "
          f"{hill_results['brute_force']['elapsed_seconds']}s)")
    print(f"  Hill-climbing:           top score = "
          f"{hill_results['hill_climbing']['best_score']:.4f}")
    print()

    # ----- PART D: Two-rune functions -----
    print("-" * 70)
    print("PART D: TWO-RUNE FUNCTION ATTACKS")
    print("-" * 70)
    two_rune_results = run_two_rune_function_attacks(corpus, n_runes=N_RUNES)
    print(f"Tested {len(two_rune_results['results'])} two-rune functions.")
    for r in two_rune_results["results"]:
        print(f"  {r['function']:14s}  score={r['score']:.4f}  "
              f"PT[:60]: {r['plaintext'][:60]}")
    print()

    # ----- Save consolidated results -----
    all_results = {
        "meta": {
            "corpus_total_runes": len(corpus),
            "n_input_runes": N_RUNES,
            "n_pairs": N_RUNES // 2,
            "english_score_baseline_random": 65.0,
            "english_score_threshold_english": 110.0,
            "wave1_autokey_top_score": 69.62,
        },
        "playfair": playfair_results,
        "hill": hill_results,
        "two_rune_functions": two_rune_results,
    }
    out_path = "/home/z/my-project/cicada3301-research/decoder/digraph_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"Results saved to: {out_path}")
    print()

    # ----- Quick summary of best scores -----
    print("=" * 70)
    print("OVERALL TOP SCORES PER CIPHER FAMILY")
    print("=" * 70)
    best_playfair = max(playfair_results["results"], key=lambda x: x.get("score", -1))
    best_hill_brute = max(hill_results["brute_force"]["top"],
                          key=lambda x: x["score"])
    best_hill_climb = hill_results["hill_climbing"]
    best_hill_ms = max(hill_results["magic_square_subblocks"],
                       key=lambda x: x.get("score", -1) if x.get("score") is not None else -1)
    best_two_rune = max(two_rune_results["results"], key=lambda x: x["score"])

    print(f"  Playfair (best key):     {best_playfair['key_name']:24s}  "
          f"score={best_playfair['score']:.4f}")
    print(f"  Hill (magic-square blk): {best_hill_ms['name']:24s}  "
          f"score={best_hill_ms.get('score', -1)}")
    print(f"  Hill (full brute):       matrix={best_hill_brute['matrix']}  "
          f"score={best_hill_brute['score']:.4f}")
    print(f"  Hill (hill-climbing):    matrix={best_hill_climb['best_matrix']}  "
          f"score={best_hill_climb['best_score']:.4f}")
    print(f"  Two-rune function:       {best_two_rune['function']:14s}  "
          f"score={best_two_rune['score']:.4f}")
    print()
    print(f"  Wave-1 autokey Vigenère top score (for comparison): 69.62")
    print()

    if __name__ == "__main__":
        # When run as main, also do a deeper Hill search.
        pass

if __name__ == "__main__":
    main()
