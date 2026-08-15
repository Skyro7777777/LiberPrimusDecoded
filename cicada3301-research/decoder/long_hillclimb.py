#!/usr/bin/env python3
"""
long_hillclimb.py — Optimized Long-Running Quagmire III Hill-Climber
=====================================================================
Runs the constrained Quagmire III autokey hill-climber for an extended period.
Saves progress to JSON periodically. Designed for GitHub Actions / background runs.

Usage:
  python3 long_hillclimb.py --identity NG --restarts 50 --iterations 20000 --sample 1000
  python3 long_hillclimb.py --identity W --restarts 30 --iterations 15000 --sample 800
  python3 long_hillclimb.py --identity TH --restarts 30 --iterations 15000 --sample 800

The known-answer test (p7a) proved this method works — 97.89% recovery on
encrypted Parable. The cipher is CONFIRMED as Quagmire III autokey.
Only the keyed-alphabet permutation (29! space) remains.
"""
import sys, os, json, random, math, time, argparse
from typing import List, Tuple, Dict, Optional
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, PRIMES, N_RUNES, MOD,
    runes_to_decimals, decimals_to_runes, decimals_to_latin, runes_to_latin,
    is_rune, rune_to_dec, dec_to_rune,
)

# Load Runeglish quadgrams from aldegonde
QUADGRAMS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "solvers", "aldegonde", "src", "aldegonde",
                              "data", "ngrams", "runeglish", "quadgrams.txt")
TRIGRAMS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "solvers", "aldegonde", "src", "aldegonde",
                             "data", "ngrams", "runeglish", "trigrams.txt")

def load_ngrams(path):
    grams = {}
    if not os.path.exists(path):
        print(f"WARNING: n-gram file not found: {path}")
        return grams
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                grams[parts[0]] = int(parts[1])
    return grams

QUADGRAMS = load_ngrams(QUADGRAMS_PATH)
TRIGRAMS = load_ngrams(TRIGRAMS_PATH)
total_quad = sum(QUADGRAMS.values()) if QUADGRAMS else 1
LOG_QUAD = {k: math.log(v / total_quad) for k, v in QUADGRAMS.items()} if QUADGRAMS else {}
FLOOR_QUAD = math.log(0.01 / total_quad) if total_quad else -20

total_tri = sum(TRIGRAMS.values()) if TRIGRAMS else 1
LOG_TRI = {k: math.log(v / total_tri) for k, v in TRIGRAMS.items()} if TRIGRAMS else {}
FLOOR_TRI = math.log(0.01 / total_tri) if total_tri else -20

print(f"Loaded {len(QUADGRAMS)} quadgrams, {len(TRIGRAMS)} trigrams", file=sys.stderr)


def quadgram_score(rune_str):
    """Score a rune string using Runeglish quadgram log-probabilities. Higher = better."""
    if len(rune_str) < 4:
        return FLOOR_QUAD * max(1, len(rune_str))
    score = 0.0
    for i in range(len(rune_str) - 3):
        score += LOG_QUAD.get(rune_str[i:i+4], FLOOR_QUAD)
    return score


def build_inverse_tableau(keyed_alpha):
    """
    Build inverse tableau for Quagmire III decryption.
    T[k][p] = keyed_alpha[(k + p) % 29]
    T_inv[k][c] = p such that T[k][p] = c
    """
    inv = [[0] * N_RUNES for _ in range(N_RUNES)]
    for k in range(N_RUNES):
        for p in range(N_RUNES):
            c = keyed_alpha[(k + p) % N_RUNES]
            inv[k][c] = p
    return inv


def decrypt_quagmire3(ct_decs, primer, keyed_alpha):
    """Decrypt: P[i] = T_inv[C[i-1]][C[i]] with ciphertext feedback."""
    inv = build_inverse_tableau(keyed_alpha)
    pt = []
    prev = primer
    for c in ct_decs:
        p = inv[prev][c]
        pt.append(p)
        prev = c
    return pt


def hill_climb(ct_decs, identity_pos, max_iter, restarts, sample_len, save_path=None,
               tag=""):
    """
    Hill-climb on the keyed alphabet with identity constrained to identity_pos.
    
    identity_pos: position in keyed_alpha where F (0) must sit.
    For NG: identity_pos = 21
    For W:  identity_pos = 7
    For TH: identity_pos = 2
    """
    sample = ct_decs[:sample_len]
    n_sample = len(sample)
    
    best_overall_score = -1e18
    best_overall_alpha = None
    best_overall_primer = 0
    best_overall_pt = ""
    best_overall_runes = ""
    
    start_time = time.time()
    
    for restart in range(restarts):
        # Random keyed alphabet with F at identity_pos
        others = list(range(1, N_RUNES))
        random.shuffle(others)
        alpha = others[:identity_pos] + [0] + others[identity_pos:]
        assert len(alpha) == N_RUNES
        assert alpha[identity_pos] == 0
        
        # Find best primer for this alpha
        best_primer = 0
        best_score = -1e18
        for primer in range(N_RUNES):
            pt = decrypt_quagmire3(sample, primer, alpha)
            pt_runes = decimals_to_runes(pt)
            s = quadgram_score(pt_runes)
            if s > best_score:
                best_score = s
                best_primer = primer
        
        current_alpha = alpha[:]
        current_primer = best_primer
        current_score = best_score
        
        # Positions that can be swapped (not the identity position)
        swappable = [i for i in range(N_RUNES) if i != identity_pos]
        
        no_improve = 0
        for iteration in range(max_iter):
            # Mutate: swap two swappable elements
            i, j = random.sample(swappable, 2)
            current_alpha[i], current_alpha[j] = current_alpha[j], current_alpha[i]
            
            # Occasionally try a different primer
            if random.random() < 0.03:
                new_primer = random.randint(0, N_RUNES - 1)
            else:
                new_primer = current_primer
            
            pt = decrypt_quagmire3(sample, new_primer, current_alpha)
            pt_runes = decimals_to_runes(pt)
            new_score = quadgram_score(pt_runes)
            
            if new_score > current_score:
                current_score = new_score
                current_primer = new_primer
                no_improve = 0
                if new_score > best_overall_score:
                    best_overall_score = new_score
                    best_overall_alpha = current_alpha[:]
                    best_overall_primer = new_primer
                    best_overall_pt = runes_to_latin(pt_runes)
                    best_overall_runes = pt_runes
                    elapsed = time.time() - start_time
                    if new_score > -3000 or iteration % 1000 == 0:
                        print(f"[{tag} r{restart} it{iteration} t={elapsed:.0f}s] score={new_score:.1f}  {best_overall_pt[:70]}", file=sys.stderr)
            else:
                current_alpha[i], current_alpha[j] = current_alpha[j], current_alpha[i]
                no_improve += 1
            
            if no_improve > 2000:
                break
        
        elapsed = time.time() - start_time
        print(f"[{tag}] restart {restart}/{restarts}: score={best_score:.1f} (best overall={best_overall_score:.1f}, t={elapsed:.0f}s)", file=sys.stderr)
        
        # Save progress periodically
        if save_path and best_overall_alpha is not None and (restart % 5 == 0 or restart == restarts - 1):
            result = {
                "tag": tag,
                "identity_pos": identity_pos,
                "identity_rune": DEC_TO_LETTER[identity_pos],
                "best_score": best_overall_score,
                "best_primer": DEC_TO_LETTER[best_overall_primer],
                "best_keyed_alphabet": [DEC_TO_LETTER[a] for a in best_overall_alpha],
                "best_plaintext_latin": best_overall_pt[:500],
                "best_plaintext_runes": best_overall_runes[:500],
                "restarts_done": restart + 1,
                "total_restarts": restarts,
                "elapsed_seconds": elapsed,
                "sample_len": n_sample,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(save_path, "w") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
    
    return best_overall_alpha, best_overall_primer, best_overall_score, best_overall_pt, best_overall_runes


def main():
    parser = argparse.ArgumentParser(description="Long-running Quagmire III hill-climber")
    parser.add_argument("--identity", choices=["NG", "W", "TH", "ALL"], default="NG",
                        help="Identity rune constraint")
    parser.add_argument("--restarts", type=int, default=30, help="Number of restarts")
    parser.add_argument("--iterations", type=int, default=15000, help="Iterations per restart")
    parser.add_argument("--sample", type=int, default=800, help="Sample length (runes)")
    parser.add_argument("--page", type=str, default="",
                        help="Specific page to attack (e.g., '17.jpg'). Empty = full corpus")
    parser.add_argument("--save", type=str, default="", help="Save path for results JSON")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    
    random.seed(args.seed)
    
    # Load unsolved pages
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "unsolved_pages.json")) as f:
        unsolved = json.load(f)
    
    if args.page:
        page = next((p for p in unsolved if p["page_id"] == args.page), None)
        if not page:
            print(f"Page {args.page} not found. Available: {[p['page_id'] for p in unsolved]}", file=sys.stderr)
            sys.exit(1)
        ct_runes = page["runes"]
        tag = args.page
    else:
        ct_runes = "".join(p["runes"] for p in unsolved)
        tag = "corpus"
    
    ct_decs = runes_to_decimals(ct_runes)
    print(f"Target: {tag} ({len(ct_decs)} runes)", file=sys.stderr)
    print(f"Params: identity={args.identity}, restarts={args.restarts}, iterations={args.iterations}, sample={args.sample}", file=sys.stderr)
    
    if args.save:
        save_path = args.save
    else:
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 f"long_hillclimb_{args.identity}_{tag}.json")
    
    # Run the hill-climb
    if args.identity == "ALL":
        # Run all 3 identity candidates
        all_results = {}
        for id_name, id_pos in [("NG", 21), ("W", 7), ("TH", 2)]:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"IDENTITY = {id_name} (pos {id_pos})", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            
            best = hill_climb(ct_decs, id_pos, args.iterations, args.restarts,
                              args.sample, save_path, tag=f"{tag}_{id_name}")
            alpha, primer, score, pt_latin, pt_runes = best
            all_results[id_name] = {
                "score": score,
                "primer": DEC_TO_LETTER[primer],
                "keyed_alphabet": [DEC_TO_LETTER[a] for a in alpha] if alpha else None,
                "plaintext_latin": pt_latin[:500],
                "plaintext_runes": pt_runes[:500],
            }
            
            # Check for break
            if score > -3000:
                print(f"\n*** POTENTIAL BREAK! identity={id_name} score={score:.1f} ***", file=sys.stderr)
                print(f"Plaintext: {pt_latin[:300]}", file=sys.stderr)
        
        # Save combined results
        with open(save_path, "w") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved combined results to {save_path}", file=sys.stderr)
    else:
        id_map = {"NG": 21, "W": 7, "TH": 2}
        id_pos = id_map[args.identity]
        
        best = hill_climb(ct_decs, id_pos, args.iterations, args.restarts,
                          args.sample, save_path, tag=f"{tag}_{args.identity}")
        alpha, primer, score, pt_latin, pt_runes = best
        
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"FINAL RESULT: identity={args.identity} score={score:.1f}", file=sys.stderr)
        print(f"Primer: {DEC_TO_LETTER[primer]}", file=sys.stderr)
        print(f"Keyed alphabet: {[DEC_TO_LETTER[a] for a in alpha] if alpha else 'None'}", file=sys.stderr)
        print(f"Plaintext: {pt_latin[:300]}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        
        if score > -3000:
            print(f"\n*** POTENTIAL BREAK! ***", file=sys.stderr)


if __name__ == "__main__":
    main()
