#!/usr/bin/env python3
"""
aldegonde_walk_attack.py — Uses aldegonde's VALIDATED 2-rune likelihood objective.
=============================================================================
The prior batch_walk_attack.py used a simplified base_0 recovery that didn't work.
This script uses aldegonde's ACTUAL validated score function, which achieves
EXACT key recovery (29/29 runes) when (g, σ) are known.

The attack:
1. For each random (g, σ) pair:
   a. Use aldegonde's 2-rune likelihood to recover base_0 (hill-climb)
   b. Decrypt the full corpus
   c. Score with quadgrams
2. Report the best
"""
import sys, os, json, random, math, time
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESEARCH_DIR = os.path.dirname(SCRIPT_DIR)
ALDEGONDE_DIR = os.path.join(RESEARCH_DIR, "solvers", "aldegonde")
ALDEGONDE_EXP = os.path.join(ALDEGONDE_DIR, "experiments")

sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, ALDEGONDE_EXP)
sys.path.insert(0, os.path.join(ALDEGONDE_DIR, "src"))

# Import aldegonde modules
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, N_RUNES, MOD,
    runes_to_decimals, decimals_to_runes, runes_to_latin,
)

# Import aldegonde's validated functions
try:
    from aldegonde import c3301
    from d5_partial_leak import to_runeglish
    from doublet_position_profile import IDX_ENG
    from ea_direction_test import PROSE_CACHE, prose_words
    from lp_corpus import load_clean
    print("Loaded aldegonde modules successfully", file=sys.stderr)
    ALDEGONDE_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: aldegonde modules not available: {e}", file=sys.stderr)
    ALDEGONDE_AVAILABLE = False
    sys.exit(1)

M = 29

# Aldegonde's compose/inverse/bases/encrypt/score functions
def compose(a, b):
    return [a[b[x]] for x in range(M)]

def inverse(p):
    q = [0] * M
    for i, v in enumerate(p):
        q[v] = i
    return q

def rand_order5(rng):
    pts = list(range(M))
    rng.shuffle(pts)
    g = list(range(M))
    for c in range(5):
        cy = pts[c * 5 : (c + 1) * 5]
        for i in range(5):
            g[cy[i]] = cy[(i + 1) % 5]
    return g

def bases(base0, g, sigma, lens):
    gp = [list(range(M))]
    for _ in range(4):
        gp.append(compose(g, gp[-1]))
    out, base = [], base0[:]
    for L in lens:
        out.append(base)
        base = compose(base, compose(gp[(L - 1) % 5], sigma))
    return out

def decrypt_word(word_ct, base, g):
    """Decrypt a single word given the base and g."""
    gp = [list(range(M))]
    for _ in range(4):
        gp.append(compose(g, gp[-1]))
    ginv = inverse(g)
    binv = inverse(base)
    return [ginv[binv[c]] for c in word_ct]

def score_2rune(cipher2, idx2, base0, g, sigma, lens, table, floor):
    """Aldegonde's validated 2-rune likelihood score."""
    bs = bases(base0, g, sigma, lens)
    ginv = inverse(g)
    total = 0.0
    for k, i in enumerate(idx2):
        binv = inverse(bs[i])
        c0, c1 = cipher2[k]
        p0 = binv[c0]
        p1 = ginv[binv[c1]]
        total += table.get((p0, p1), floor)
    return total

# Load quadgrams for final scoring
def load_quadgrams():
    path = os.path.join(ALDEGONDE_DIR, "src", "aldegonde", "data", "ngrams", "runeglish", "quadgrams.txt")
    grams = {}
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                grams[parts[0]] = int(parts[1])
    return grams

QUADGRAMS = load_quadgrams()
total_quad = sum(QUADGRAMS.values())
LOG_QUAD = {k: math.log(v / total_quad) for k, v in QUADGRAMS.items()}
FLOOR_QUAD = math.log(0.01 / total_quad)

def quadgram_score(rune_str):
    if len(rune_str) < 4:
        return FLOOR_QUAD * max(1, len(rune_str))
    score = 0.0
    for i in range(len(rune_str) - 3):
        score += LOG_QUAD.get(rune_str[i:i+4], FLOOR_QUAD)
    return score


def recover_base_0_validated(ct_words, g, sigma, table, floor, rng):
    """
    Recover base_0 using aldegonde's VALIDATED 2-rune likelihood hill-climb.
    
    ct_words: list of lists of rune decimals (the ciphertext words)
    g: order-5 permutation
    sigma: word-boundary permutation
    table: 2-rune log-probability table from Runeglish prose
    floor: log-floor for unseen 2-rune pairs
    """
    lens = [len(w) for w in ct_words]
    idx2 = [i for i, w in enumerate(ct_words) if len(w) == 2]
    cipher2 = [(ct_words[i][0], ct_words[i][1]) for i in idx2]
    
    # Hill-climb base_0
    best_score = -1e18
    best_base0 = list(range(M))
    
    for trial in range(200):
        base0 = list(range(M))
        rng.shuffle(base0)
        s = score_2rune(cipher2, idx2, base0, g, sigma, lens, table, floor)
        if s > best_score:
            best_score = s
            best_base0 = base0[:]
    
    # Local hill-climb: swap pairs in base_0
    current_score = best_score
    current_base0 = best_base0[:]
    
    for iteration in range(5000):
        # Try swapping two elements
        i, j = random.sample(range(M), 2)
        current_base0[i], current_base0[j] = current_base0[j], current_base0[i]
        s = score_2rune(cipher2, idx2, current_base0, g, sigma, lens, table, floor)
        if s > current_score:
            current_score = s
            if s > best_score:
                best_score = s
                best_base0 = current_base0[:]
        else:
            current_base0[i], current_base0[j] = current_base0[j], current_base0[i]
    
    return best_base0, best_score


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Aldegonde validated walk attack")
    parser.add_argument("--batch-id", type=int, default=0, help="Batch ID")
    parser.add_argument("--duration", type=int, default=240, help="Duration in seconds")
    parser.add_argument("--save-interval", type=int, default=60, help="Save every N seconds")
    args = parser.parse_args()
    
    print("=" * 60, file=sys.stderr)
    print(f"ALDEGONDE VALIDATED WALK ATTACK (Batch {args.batch_id})", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    # Load the LP corpus using aldegonde's own loader
    stream, wid = load_clean()
    print(f"Loaded LP corpus: {len(stream)} runes, {max(wid)+1} words", file=sys.stderr)
    
    # Build the word list
    words_by_id = {}
    for i, w in enumerate(wid):
        words_by_id.setdefault(w, []).append(stream[i])
    ct_words = [words_by_id[k] for k in sorted(words_by_id)]
    lens = [len(w) for w in ct_words]
    print(f"Words: {len(ct_words)}, avg length: {sum(lens)/len(lens):.1f}", file=sys.stderr)
    
    # Build the 2-rune log-probability table from Runeglish prose
    prose_path = PROSE_CACHE
    if not prose_path.exists():
        print(f"Prose corpus not found at {prose_path}, downloading...", file=sys.stderr)
        import urllib.request
        urllib.request.urlretrieve("https://www.gutenberg.org/files/1342/1342-0.txt", prose_path)
    
    two_counts = {}
    total_2rune = 0
    for w in prose_words(prose_path):
        r = [IDX_ENG[t] for t in to_runeglish(w)]
        if len(r) == 2:
            key = (r[0], r[1])
            two_counts[key] = two_counts.get(key, 0) + 1
            total_2rune += 1
    
    table = {k: math.log(v / total_2rune) for k, v in two_counts.items()}
    floor = math.log(0.2 / total_2rune)
    print(f"2-rune table: {len(table)} types, {total_2rune} tokens", file=sys.stderr)
    
    # Run the attack
    rng = random.Random(args.batch_id * 1000000 + 42)
    best_overall_score = -1e18
    best_overall_key = None
    best_overall_pt = ""
    
    start = time.time()
    max_duration = args.duration
    last_save = start
    
    trial = 0
    while time.time() - start < max_duration:
        # Generate random (g, sigma)
        g = rand_order5(rng)
        sigma = list(range(M))
        rng.shuffle(sigma)
        
        # Recover base_0 using VALIDATED 2-rune likelihood
        base0, two_rune_score = recover_base_0_validated(ct_words, g, sigma, table, floor, rng)
        
        # Decrypt the full corpus
        bs = bases(base0, g, sigma, lens)
        pt_decs = []
        for k, word_ct in enumerate(ct_words):
            pt_word = decrypt_word(word_ct, bs[k], g)
            pt_decs.extend(pt_word)
        
        pt_runes = decimals_to_runes(pt_decs)
        quad_score = quadgram_score(pt_runes)
        
        if quad_score > best_overall_score:
            best_overall_score = quad_score
            best_overall_key = (base0[:], g[:], sigma[:])
            best_overall_pt = runes_to_latin(pt_runes)
            elapsed = time.time() - start
            print(f"[trial {trial} t={elapsed:.0f}s] 2rune={two_rune_score:.1f} quad={quad_score:.1f}  {best_overall_pt[:70]}", file=sys.stderr)
        
        trial += 1
        if trial % 10 == 0:
            elapsed = time.time() - start
            print(f"trial {trial} (t={elapsed:.0f}s) best_quad={best_overall_score:.1f}", file=sys.stderr)
        
        # Save periodically
        now = time.time()
        if now - last_save > args.save_interval and best_overall_key is not None:
            result = {
                "batch_id": args.batch_id,
                "best_quad_score": best_overall_score,
                "best_key": {
                    "base_0": [DEC_TO_LETTER[a] for a in best_overall_key[0]],
                    "g": [DEC_TO_LETTER[a] for a in best_overall_key[1]],
                    "sigma": [DEC_TO_LETTER[a] for a in best_overall_key[2]],
                },
                "best_plaintext": best_overall_pt[:2000],
                "trials": trial,
                "duration": time.time() - start,
            }
            save_path = os.path.join(SCRIPT_DIR, "aldegonde_attack_results.json")
            with open(save_path, "w") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            last_save = now
    
    # Save results
    result = {
        "best_quad_score": best_overall_score,
        "best_key": {
            "base_0": [DEC_TO_LETTER[a] for a in best_overall_key[0]] if best_overall_key else None,
            "g": [DEC_TO_LETTER[a] for a in best_overall_key[1]] if best_overall_key else None,
            "sigma": [DEC_TO_LETTER[a] for a in best_overall_key[2]] if best_overall_key else None,
        },
        "best_plaintext": best_overall_pt[:2000],
        "trials": trial,
        "duration": time.time() - start,
    }
    
    save_path = os.path.join(SCRIPT_DIR, "aldegonde_attack_results.json")
    with open(save_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== FINAL RESULT ===", file=sys.stderr)
    print(f"Trials: {trial}", file=sys.stderr)
    print(f"Best quad score: {best_overall_score:.1f}", file=sys.stderr)
    print(f"Best plaintext: {best_overall_pt[:300]}", file=sys.stderr)
    print(f"Saved to {save_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
