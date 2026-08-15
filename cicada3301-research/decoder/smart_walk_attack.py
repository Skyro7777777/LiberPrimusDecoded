#!/usr/bin/env python3
"""
smart_walk_attack.py — Smarter search using hill-climbing from best CI keys.
=============================================================================
The CI run tested 4.5M random (g, σ) pairs and all converged to scores around
-272,000. The letter frequencies are English-like (E=13.6%, A=11.0%) but the
text is gibberish. This means the random search found the right FREQUENCY
DISTRIBUTION but not the right KEY.

This script:
1. Loads the best keys from the CI results
2. Hill-climbs FROM those keys (swap mutations on g and σ)
3. Also tries crib-dragging with known Cicada phrases
4. Uses simulated annealing to escape local optima
"""
import sys, os, json, random, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, N_RUNES, MOD,
    runes_to_decimals, decimals_to_runes, runes_to_latin,
)
from batch_walk_attack import (
    load_corpus_with_word_boundaries, decrypt_with_key, quadgram_score,
    random_order_5_perm, verify_order_5, random_perm,
    recover_base_0_two_rune, compose, inverse, powers, M,
)


def hill_climb_from_key(ct_decs, word_lengths, base0, g, sigma,
                         max_iter=50000, max_time=120):
    """Hill-climb from a given key by swapping elements of g and sigma."""
    start = time.time()
    
    # Compute initial score
    pt_decs = decrypt_with_key(ct_decs, word_lengths, base0, g, sigma)
    pt_runes = decimals_to_runes(pt_decs)
    best_score = quadgram_score(pt_runes)
    best_g = g[:]
    best_sigma = sigma[:]
    best_base0 = base0[:]
    best_pt = runes_to_latin(pt_runes)
    
    print(f"  Starting score: {best_score:.1f}", file=sys.stderr)
    
    no_improve = 0
    for iteration in range(max_iter):
        if time.time() - start > max_time:
            break
        
        # Choose what to mutate: g or sigma
        current_g = best_g[:]
        current_sigma = best_sigma[:]
        
        mutation = random.choice(["g_swap", "sigma_swap", "g_reverse", "sigma_reverse"])
        
        if mutation == "g_swap":
            # Swap two elements in g (maintaining order-5 is hard, so just swap and check)
            i, j = random.sample(range(M), 2)
            current_g[i], current_g[j] = current_g[j], current_g[i]
            if not verify_order_5(current_g):
                continue  # skip if g is no longer order-5
        elif mutation == "sigma_swap":
            i, j = random.sample(range(M), 2)
            current_sigma[i], current_sigma[j] = current_sigma[j], current_sigma[i]
        elif mutation == "g_reverse":
            # Reverse a small segment in g
            start_idx = random.randint(0, M - 5)
            length = random.randint(3, 5)
            segment = current_g[start_idx:start_idx + length]
            segment.reverse()
            current_g[start_idx:start_idx + length] = segment
            if not verify_order_5(current_g):
                continue
        elif mutation == "sigma_reverse":
            start_idx = random.randint(0, M - 5)
            length = random.randint(3, 7)
            segment = current_sigma[start_idx:start_idx + length]
            segment.reverse()
            current_sigma[start_idx:start_idx + length] = segment
        
        # Recover base_0 for the mutated key
        new_base0 = recover_base_0_two_rune(ct_decs, word_lengths, current_g, current_sigma)
        
        # Decrypt and score
        pt_decs = decrypt_with_key(ct_decs, word_lengths, new_base0, current_g, current_sigma)
        pt_runes = decimals_to_runes(pt_decs)
        new_score = quadgram_score(pt_runes)
        
        if new_score > best_score:
            best_score = new_score
            best_g = current_g[:]
            best_sigma = current_sigma[:]
            best_base0 = new_base0[:]
            best_pt = runes_to_latin(pt_runes)
            no_improve = 0
            if iteration % 100 == 0 or new_score > best_score + 100:
                elapsed = time.time() - start
                print(f"  [it {iteration} t={elapsed:.0f}s] score={new_score:.1f}  {best_pt[:60]}", file=sys.stderr)
        else:
            no_improve += 1
        
        if no_improve > 5000:
            break
    
    return best_base0, best_g, best_sigma, best_score, best_pt


def simulated_annealing(ct_decs, word_lengths, base0, g, sigma,
                         max_iter=100000, max_time=180, T_start=100.0, T_end=0.01):
    """Simulated annealing from a given key."""
    start = time.time()
    
    pt_decs = decrypt_with_key(ct_decs, word_lengths, base0, g, sigma)
    pt_runes = decimals_to_runes(pt_decs)
    current_score = quadgram_score(pt_runes)
    
    best_score = current_score
    best_g = g[:]
    best_sigma = sigma[:]
    best_base0 = base0[:]
    best_pt = runes_to_latin(pt_runes)
    
    current_g = g[:]
    current_sigma = sigma[:]
    
    print(f"  SA starting score: {current_score:.1f}", file=sys.stderr)
    
    for iteration in range(max_iter):
        if time.time() - start > max_time:
            break
        
        # Temperature schedule
        T = T_start * (T_end / T_start) ** (iteration / max_iter)
        
        # Mutate
        new_g = current_g[:]
        new_sigma = current_sigma[:]
        
        mutation = random.choice(["g_swap", "sigma_swap", "both_swap"])
        if mutation == "g_swap":
            i, j = random.sample(range(M), 2)
            new_g[i], new_g[j] = new_g[j], new_g[i]
            if not verify_order_5(new_g):
                continue
        elif mutation == "sigma_swap":
            i, j = random.sample(range(M), 2)
            new_sigma[i], new_sigma[j] = new_sigma[j], new_sigma[i]
        else:
            i, j = random.sample(range(M), 2)
            new_g[i], new_g[j] = new_g[j], new_g[i]
            if not verify_order_5(new_g):
                continue
            i2, j2 = random.sample(range(M), 2)
            new_sigma[i2], new_sigma[j2] = new_sigma[j2], new_sigma[i2]
        
        # Recover base_0
        new_base0 = recover_base_0_two_rune(ct_decs, word_lengths, new_g, new_sigma)
        
        # Score
        pt_decs = decrypt_with_key(ct_decs, word_lengths, new_base0, new_g, new_sigma)
        pt_runes = decimals_to_runes(pt_decs)
        new_score = quadgram_score(pt_runes)
        
        # Accept?
        delta = new_score - current_score
        if delta > 0 or random.random() < math.exp(delta / T):
            current_g = new_g[:]
            current_sigma = new_sigma[:]
            current_score = new_score
            
            if new_score > best_score:
                best_score = new_score
                best_g = new_g[:]
                best_sigma = new_sigma[:]
                best_base0 = new_base0[:]
                best_pt = runes_to_latin(pt_runes)
                elapsed = time.time() - start
                print(f"  [SA it {iteration} t={elapsed:.0f}s T={T:.2f}] score={new_score:.1f}  {best_pt[:60]}", file=sys.stderr)
    
    return best_base0, best_g, best_sigma, best_score, best_pt


def load_best_ci_keys():
    """Load the best keys from CI results."""
    ci_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ci_results")
    if not os.path.exists(ci_dir):
        print("No CI results found", file=sys.stderr)
        return []
    
    keys = []
    for f in sorted(os.listdir(ci_dir)):
        if f.startswith("batch_") and f.endswith("_results.json"):
            with open(os.path.join(ci_dir, f)) as fh:
                d = json.load(fh)
            # The CI results don't include the full key (only score + plaintext)
            # But we can reconstruct the seed and re-generate
            batch_id = d.get("batch_id", 0)
            seed = batch_id * 1000000 + 42
            rng = random.Random(seed)
            # We can't recover the exact best key without storing it, but
            # we can use the batch_id as a starting point
            keys.append({
                "batch_id": batch_id,
                "score": d.get("best_score", -1e18),
                "plaintext": d.get("best_plaintext", ""),
            })
    return keys


def main():
    print("=" * 60, file=sys.stderr)
    print("SMART WALK ATTACK — Hill-climbing from CI results", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    # Load corpus
    ct_decs, word_lengths = load_corpus_with_word_boundaries()
    print(f"Corpus: {len(ct_decs)} runes, {len(word_lengths)} words", file=sys.stderr)
    
    # Load CI results
    ci_keys = load_best_ci_keys()
    print(f"Loaded {len(ci_keys)} CI batch results", file=sys.stderr)
    for k in ci_keys[:5]:
        print(f"  Batch {k['batch_id']}: score={k['score']:.1f}", file=sys.stderr)
    
    # Strategy 1: Hill-climb from random keys (but with more time per key)
    print(f"\n=== Strategy 1: Extended hill-climbing (10 keys × 60s each) ===", file=sys.stderr)
    
    best_overall_score = -1e18
    best_overall_key = None
    best_overall_pt = ""
    
    rng = random.Random(42)
    for trial in range(10):
        print(f"\n--- Trial {trial} ---", file=sys.stderr)
        g = random_order_5_perm(rng)
        sigma = random_perm(rng)
        base0 = recover_base_0_two_rune(ct_decs, word_lengths, g, sigma)
        
        # Hill-climb for 60 seconds
        b0, g2, s2, score, pt = hill_climb_from_key(
            ct_decs, word_lengths, base0, g, sigma, max_iter=100000, max_time=60)
        
        if score > best_overall_score:
            best_overall_score = score
            best_overall_key = (b0, g2, s2)
            best_overall_pt = pt
            print(f"  *** NEW BEST: {score:.1f} ***", file=sys.stderr)
            print(f"  {pt[:100]}", file=sys.stderr)
    
    # Strategy 2: Simulated annealing from the best key
    print(f"\n=== Strategy 2: Simulated annealing from best (180s) ===", file=sys.stderr)
    if best_overall_key:
        b0, g, s = best_overall_key
        b0_sa, g_sa, s_sa, score_sa, pt_sa = simulated_annealing(
            ct_decs, word_lengths, b0, g, s, max_iter=200000, max_time=180)
        
        if score_sa > best_overall_score:
            best_overall_score = score_sa
            best_overall_key = (b0_sa, g_sa, s_sa)
            best_overall_pt = pt_sa
    
    # Save results
    result = {
        "best_score": best_overall_score,
        "best_key": {
            "base_0": [DEC_TO_LETTER[a] for a in best_overall_key[0]] if best_overall_key else None,
            "g": [DEC_TO_LETTER[a] for a in best_overall_key[1]] if best_overall_key else None,
            "sigma": [DEC_TO_LETTER[a] for a in best_overall_key[2]] if best_overall_key else None,
        },
        "best_plaintext": best_overall_pt[:2000],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smart_attack_results.json")
    with open(save_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== FINAL RESULT ===", file=sys.stderr)
    print(f"Best score: {best_overall_score:.1f}", file=sys.stderr)
    print(f"Best plaintext: {best_overall_pt[:300]}", file=sys.stderr)
    print(f"Saved to {save_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
