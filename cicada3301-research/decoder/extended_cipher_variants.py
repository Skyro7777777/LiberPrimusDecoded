#!/usr/bin/env python3
"""
extended_cipher_variants.py — Three variants of the first-diff + MASC attack
=============================================================================

Variant 1 — Beaufort first-difference (reversed subtraction)
    D[i] = (C[i-1] - C[i]) % 29      P[i] = perm[D[i]]
Variant 2 — Plaintext-feedback autokey
    C[i] = (P[i-1] + perm[P[i]]) % 29
    Decrypt: P[i] = perm_inv[(C[i] - P[i-1]) % 29]
Variant 3 — Known-answer test on page 74 (= page 57, Parable, direct translation)
    Encrypt the Parable with first-diff + MASC using a known perm, then
    hill-climb to recover the perm. Verifies the hill-climber works.
"""
import sys, os, json, random, math, time

sys.path.insert(0, os.path.dirname(__file__))
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, N_RUNES, MOD,
    runes_to_decimals, decimals_to_runes, decimals_to_latin, runes_to_latin,
    clean_runes,
)

# ---- Load ngrams (same as first_diff_masc.py) ----
ALDE = os.path.join(os.path.dirname(__file__), "..", "solvers", "aldegonde", "src", "aldegonde", "data", "ngrams", "runeglish")
def load_ngrams(path):
    g = {}
    if not os.path.exists(path): return g
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                g[parts[0]] = int(parts[1])
    return g
QUADGRAMS = load_ngrams(os.path.join(ALDE, "quadgrams.txt"))
total_quad = sum(QUADGRAMS.values()) if QUADGRAMS else 1
LOG_QUAD = {k: math.log(v / total_quad) for k, v in QUADGRAMS.items()} if QUADGRAMS else {}
FLOOR_QUAD = math.log(0.01 / total_quad) if total_quad else -20.0

def quadgram_score(rune_str):
    if len(rune_str) < 4:
        return FLOOR_QUAD * max(1, len(rune_str))
    s = 0.0
    for i in range(len(rune_str) - 3):
        s += LOG_QUAD.get(rune_str[i:i+4], FLOOR_QUAD)
    return s

# ----------------------------------------------------------------------------
# Variant 1: Beaufort first-difference + MASC
# ----------------------------------------------------------------------------
def beaufort_diffs(ct_decs, primer_dec):
    """D[i] = (C[i-1] - C[i]) % 29, with D[0] = (primer - C[0]) % 29."""
    diffs = []
    prev = primer_dec
    for c in ct_decs:
        diffs.append((prev - c) % MOD)
        prev = c
    return diffs

def apply_masc(diffs, perm):
    return [perm[d] for d in diffs]

def hill_climb_variant1(ct_decs, max_iter=5000, restarts=10, label="V1"):
    best_overall = None
    for r in range(restarts):
        perm = list(range(N_RUNES)); random.shuffle(perm)
        # Try all primers to pick best start
        best_primer = 0; best_score = -1e18
        for primer in range(N_RUNES):
            d = beaufort_diffs(ct_decs, primer)
            pt_runes = decimals_to_runes(apply_masc(d, perm))
            s = quadgram_score(pt_runes)
            if s > best_score: best_score = s; best_primer = primer
        cur_perm = perm[:]; cur_primer = best_primer; cur_score = best_score
        best_perm = perm[:]; best_pr_l = best_primer
        no_improve = 0
        for it in range(max_iter):
            i, j = random.sample(range(N_RUNES), 2)
            cur_perm[i], cur_perm[j] = cur_perm[j], cur_perm[i]
            if random.random() < 0.1:
                new_pr = random.randint(0, N_RUNES-1)
            else:
                new_pr = cur_primer
            d = beaufort_diffs(ct_decs, new_pr)
            pt_runes = decimals_to_runes(apply_masc(d, cur_perm))
            s = quadgram_score(pt_runes)
            if s > cur_score:
                cur_score = s; cur_primer = new_pr; no_improve = 0
                if s > best_score:
                    best_score = s; best_perm = cur_perm[:]; best_pr_l = new_pr
            else:
                cur_perm[i], cur_perm[j] = cur_perm[j], cur_perm[i]
                no_improve += 1
            if no_improve > 1500: break
        d = beaufort_diffs(ct_decs, best_pr_l)
        pt_runes = decimals_to_runes(apply_masc(d, best_perm))
        pt_lat = runes_to_latin(pt_runes)
        if best_overall is None or best_score > best_overall["score"]:
            best_overall = {
                "score": best_score, "primer": DEC_TO_LETTER[best_pr_l],
                "perm": [DEC_TO_LETTER[p] for p in best_perm],
                "perm_0": DEC_TO_LETTER[best_perm[0]],
                "plaintext_latin": pt_lat,
                "plaintext_runes": pt_runes,
            }
        if r % 3 == 0:
            print(f"  [{label}] restart {r}: best_score={best_score:.1f}")
    return best_overall

# ----------------------------------------------------------------------------
# Variant 2: Plaintext-feedback autokey
#    C[i] = (P[i-1] + perm[P[i]]) % 29
#    Decrypt: P[i] = perm_inv[(C[i] - P[i-1]) % 29]
#    P[0] = perm_inv[(C[0] - primer) % 29]
# ----------------------------------------------------------------------------
def plaintext_fb_decrypt(ct_decs, primer_dec, perm):
    """perm: list where perm[plain_dec] = shift_value. perm_inv: shift_value -> plain_dec."""
    pinv = [0]*N_RUNES
    for p, v in enumerate(perm):
        pinv[v] = p
    pt = []
    prev = primer_dec
    for c in ct_decs:
        pt.append(pinv[(c - prev) % MOD])
        prev = pt[-1]
    return pt

def hill_climb_variant2(ct_decs, max_iter=5000, restarts=10, label="V2"):
    best_overall = None
    for r in range(restarts):
        perm = list(range(N_RUNES)); random.shuffle(perm)
        best_primer = 0; best_score = -1e18
        for primer in range(N_RUNES):
            pt = plaintext_fb_decrypt(ct_decs, primer, perm)
            pt_runes = decimals_to_runes(pt)
            s = quadgram_score(pt_runes)
            if s > best_score: best_score = s; best_primer = primer
        cur_perm = perm[:]; cur_primer = best_primer; cur_score = best_score
        best_perm = perm[:]; best_pr_l = best_primer
        no_improve = 0
        for it in range(max_iter):
            i, j = random.sample(range(N_RUNES), 2)
            cur_perm[i], cur_perm[j] = cur_perm[j], cur_perm[i]
            if random.random() < 0.1:
                new_pr = random.randint(0, N_RUNES-1)
            else:
                new_pr = cur_primer
            pt = plaintext_fb_decrypt(ct_decs, new_pr, cur_perm)
            pt_runes = decimals_to_runes(pt)
            s = quadgram_score(pt_runes)
            if s > cur_score:
                cur_score = s; cur_primer = new_pr; no_improve = 0
                if s > best_score:
                    best_score = s; best_perm = cur_perm[:]; best_pr_l = new_pr
            else:
                cur_perm[i], cur_perm[j] = cur_perm[j], cur_perm[i]
                no_improve += 1
            if no_improve > 1500: break
        pt = plaintext_fb_decrypt(ct_decs, best_pr_l, best_perm)
        pt_runes = decimals_to_runes(pt); pt_lat = runes_to_latin(pt_runes)
        if best_overall is None or best_score > best_overall["score"]:
            best_overall = {
                "score": best_score, "primer": DEC_TO_LETTER[best_pr_l],
                "perm": [DEC_TO_LETTER[p] for p in best_perm],
                "perm_0": DEC_TO_LETTER[best_perm[0]],
                "plaintext_latin": pt_lat,
                "plaintext_runes": pt_runes,
            }
        if r % 3 == 0:
            print(f"  [{label}] restart {r}: best_score={best_score:.1f}")
    return best_overall

# ----------------------------------------------------------------------------
# Variant 3: Known-answer test
#    Use Parable (page 74) plaintext, encrypt with first-diff + MASC using a
#    known perm + primer, then hill-climb to recover. Verifies the method.
# ----------------------------------------------------------------------------
def encrypt_first_diff_masc(pt_decs, primer_dec, perm):
    """Invert: D[i] = perm_inv[P[i]] ; C[i] = (C[i-1] + D[i]) % 29."""
    pinv = [0]*N_RUNES
    for p, v in enumerate(perm):
        pinv[v] = p
    ct = []; prev = primer_dec
    for p in pt_decs:
        d = pinv[p]
        c = (prev + d) % MOD
        ct.append(c); prev = c
    return ct

def first_diff_decrypt(ct_decs, primer_dec, perm):
    """Standard: D[i] = (C[i] - C[i-1]) % 29, P[i] = perm[D[i]]."""
    diffs = []; prev = primer_dec
    for c in ct_decs:
        diffs.append((c - prev) % MOD); prev = c
    return [perm[d] for d in diffs]

def hill_climb_known_answer(ct_decs, true_perm, true_primer, max_iter=5000, restarts=10, label="V3"):
    """Hill-climb using STANDARD first-diff (not Beaufort). Reports recovery quality."""
    # Compute the true plaintext
    true_pt = first_diff_decrypt(ct_decs, true_primer, true_perm)
    true_pt_runes = decimals_to_runes(true_pt)
    true_pt_lat = runes_to_latin(true_pt_runes)
    true_score = quadgram_score(true_pt_runes)

    best_overall = None
    for r in range(restarts):
        perm = list(range(N_RUNES)); random.shuffle(perm)
        best_primer = 0; best_score = -1e18
        for primer in range(N_RUNES):
            pt = first_diff_decrypt(ct_decs, primer, perm)
            pt_runes = decimals_to_runes(pt)
            s = quadgram_score(pt_runes)
            if s > best_score: best_score = s; best_primer = primer
        cur_perm = perm[:]; cur_primer = best_primer; cur_score = best_score
        best_perm = perm[:]; best_pr_l = best_primer
        no_improve = 0
        for it in range(max_iter):
            i, j = random.sample(range(N_RUNES), 2)
            cur_perm[i], cur_perm[j] = cur_perm[j], cur_perm[i]
            if random.random() < 0.1:
                new_pr = random.randint(0, N_RUNES-1)
            else:
                new_pr = cur_primer
            pt = first_diff_decrypt(ct_decs, new_pr, cur_perm)
            pt_runes = decimals_to_runes(pt)
            s = quadgram_score(pt_runes)
            if s > cur_score:
                cur_score = s; cur_primer = new_pr; no_improve = 0
                if s > best_score:
                    best_score = s; best_perm = cur_perm[:]; best_pr_l = new_pr
            else:
                cur_perm[i], cur_perm[j] = cur_perm[j], cur_perm[i]
                no_improve += 1
            if no_improve > 1500: break
        pt = first_diff_decrypt(ct_decs, best_pr_l, best_perm)
        pt_runes = decimals_to_runes(pt); pt_lat = runes_to_latin(pt_runes)
        # Hamming distance to true plaintext
        ham = sum(1 for a, b in zip(pt, true_pt) if a != b)
        if best_overall is None or best_score > best_overall["score"]:
            best_overall = {
                "score": best_score,
                "true_score": true_score,
                "primer": DEC_TO_LETTER[best_pr_l],
                "true_primer": DEC_TO_LETTER[true_primer],
                "perm": [DEC_TO_LETTER[p] for p in best_perm],
                "perm_0": DEC_TO_LETTER[best_perm[0]],
                "plaintext_latin": pt_lat,
                "true_plaintext_latin": true_pt_lat,
                "hamming_distance_to_true": ham,
                "n_chars": len(pt),
                "recovery_pct": round(100.0*(len(pt)-ham)/len(pt), 2),
            }
        if r % 3 == 0:
            print(f"  [{label}] restart {r}: best_score={best_score:.1f} true_score={true_score:.1f}")
    return best_overall


def main():
    t0 = time.time()
    # Load unsolved corpus
    with open(os.path.join(os.path.dirname(__file__), "unsolved_pages.json")) as f:
        unsolved = json.load(f)
    corpus_runes = "".join(p["runes"] for p in unsolved)
    # First 500 runes
    sample = clean_runes(corpus_runes)[:500]
    print(f"Corpus sample: {len(sample)} runes (first 500 of unsolved)")
    ct_decs_500 = runes_to_decimals(sample)

    # ===== VARIANT 1: Beaufort first-diff + MASC =====
    print("\n" + "="*70)
    print("VARIANT 1: Beaufort first-difference (C[i-1] - C[i]) mod 29 + MASC")
    print("="*70)
    random.seed(20250101)
    v1 = hill_climb_variant1(ct_decs_500, max_iter=5000, restarts=10, label="V1")
    print(f"\n>>> V1 BEST: score={v1['score']:.1f} primer={v1['primer']} perm[0]={v1['perm_0']}")
    print(f"    PT[:80]: {v1['plaintext_latin'][:80]}")

    # ===== VARIANT 2: Plaintext-feedback autokey =====
    print("\n" + "="*70)
    print("VARIANT 2: Plaintext-feedback autokey + MASC")
    print("="*70)
    random.seed(20250102)
    v2 = hill_climb_variant2(ct_decs_500, max_iter=5000, restarts=10, label="V2")
    print(f"\n>>> V2 BEST: score={v2['score']:.1f} primer={v2['primer']} perm[0]={v2['perm_0']}")
    print(f"    PT[:80]: {v2['plaintext_latin'][:80]}")

    # ===== VARIANT 3: Known-answer test =====
    print("\n" + "="*70)
    print("VARIANT 3: Known-answer test on Parable (page 74)")
    print("="*70)
    with open(os.path.join(os.path.dirname(__file__), "solved_pages.json")) as f:
        solved = json.load(f)
    parable_page = next(p for p in solved if p["page_id"] == "74.jpg")
    parable_runes = clean_runes(parable_page["runes"])
    pt_decs = runes_to_decimals(parable_runes)
    print(f"Parable length: {len(pt_decs)} runes; plaintext[:80]: {runes_to_latin(parable_runes)[:80]}")
    # Choose a random perm + primer, encrypt with first-diff + MASC
    random.seed(20250103)
    true_perm = list(range(N_RUNES)); random.shuffle(true_perm)
    true_primer = random.randint(0, N_RUNES-1)
    ct = encrypt_first_diff_masc(pt_decs, true_primer, true_perm)
    print(f"Encrypted with random perm; true_primer={DEC_TO_LETTER[true_primer]} true_perm[0]={DEC_TO_LETTER[true_perm[0]]}")
    v3 = hill_climb_known_answer(ct, true_perm, true_primer, max_iter=5000, restarts=10, label="V3")
    print(f"\n>>> V3 KNOWN-ANSWER:")
    print(f"    Recovered score: {v3['score']:.1f}  (true score: {v3['true_score']:.1f})")
    print(f"    Recovered primer: {v3['primer']}  (true: {v3['true_primer']})")
    print(f"    Hamming distance to true plaintext: {v3['hamming_distance_to_true']}/{v3['n_chars']} ({v3['recovery_pct']}%)")
    print(f"    Recovered PT[:80]: {v3['plaintext_latin'][:80]}")
    print(f"    True PT[:80]:      {v3['true_plaintext_latin'][:80]}")

    # Save results
    results = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": round(time.time()-t0, 1),
            "sample_length": len(sample),
            "max_iters": 5000,
            "restarts": 10,
            "n_quadgrams_loaded": len(QUADGRAMS),
            "prior_best_page0_score": -13440.07,
        },
        "variant1_beaufort_firstdiff_masc": v1,
        "variant2_plaintext_feedback_autokey_masc": v2,
        "variant3_known_answer_parable": v3,
    }
    out_path = os.path.join(os.path.dirname(__file__), "extended_cipher_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {out_path}")

if __name__ == "__main__":
    main()
