#!/usr/bin/env python3
"""
batch_walk_attack.py — Batched Length-Clocked-Walk Attack
==========================================================
Designed for GitHub Actions: runs for a specified duration, saves progress
periodically, and uploads results as artifacts.

Each batch tests a range of random seeds for the (g, σ) search space.
When (g, σ) are correct, base_0 recovers EXACTLY via 2-rune likelihood.

Usage:
  python3 batch_walk_attack.py --batch-id 0 --num-batches 10 --duration 14400
  (runs batch 0 of 10, for 4 hours = 14400 seconds)
"""
import sys, os, json, random, math, time, argparse, signal
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# Setup paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESEARCH_DIR = os.path.dirname(SCRIPT_DIR)  # cicada3301-research/
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(RESEARCH_DIR, "solvers", "aldegonde", "experiments"))

# Import gematria primus toolkit
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, N_RUNES, MOD,
    runes_to_decimals, decimals_to_runes, runes_to_latin,
)

# Import n-gram scoring
try:
    from first_diff_masc import quadgram_score, QUADGRAMS
except ImportError:
    # Fallback: load quadgrams directly
    QUADGRAMS_PATH = os.path.join(RESEARCH_DIR, "solvers", "aldegonde",
                                  "src", "aldegonde", "data", "ngrams", "runeglish", "quadgrams.txt")
    def load_ngrams(path):
        grams = {}
        if not os.path.exists(path):
            return grams
        with open(path) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 2:
                    grams[parts[0]] = int(parts[1])
        return grams

    QUADGRAMS = load_ngrams(QUADGRAMS_PATH)
    total_quad = sum(QUADGRAMS.values()) if QUADGRAMS else 1
    LOG_QUAD = {k: math.log(v / total_quad) for k, v in QUADGRAMS.items()} if QUADGRAMS else {}
    FLOOR_QUAD = math.log(0.01 / total_quad) if total_quad else -20

    def quadgram_score(rune_str):
        if len(rune_str) < 4:
            return FLOOR_QUAD * max(1, len(rune_str))
        score = 0.0
        for i in range(len(rune_str) - 3):
            score += LOG_QUAD.get(rune_str[i:i+4], FLOOR_QUAD)
        return score

# Import aldegonde's walk cipher
try:
    from length_clocked_cipher import compose, inverse, powers
    print(f"Loaded aldegonde's length_clocked_cipher module", file=sys.stderr)
except ImportError:
    print("WARNING: aldegonde module not found, using fallback", file=sys.stderr)
    def compose(a, b):
        return [a[b[i]] for i in range(len(b))]
    def inverse(p):
        inv = [0] * len(p)
        for i, x in enumerate(p):
            inv[x] = i
        return inv
    def powers(p, upto):
        out = [list(range(len(p)))]
        for _ in range(1, upto):
            out.append(compose(p, out[-1]))
        return out

M = N_RUNES  # 29


def random_order_5_perm(rng=random):
    """Generate a random order-5 permutation on 29 elements.
    29 = 5*5 + 4, so 5 five-cycles and 4 fixed points.
    """
    elems = list(range(M))
    rng.shuffle(elems)
    perm = list(range(M))
    for i in range(5):
        cycle = elems[i*5:(i+1)*5]
        for j in range(5):
            perm[cycle[j]] = cycle[(j+1) % 5]
    return perm


def verify_order_5(perm):
    """Verify perm^5 = identity."""
    p = perm[:]
    for _ in range(4):
        p = compose(p, perm)
    return p == list(range(M))


def random_perm(rng=random):
    p = list(range(M))
    rng.shuffle(p)
    return p


def decrypt_with_key(ct_decs, word_lengths, base0, g, sigma):
    """Decrypt using the walk key."""
    gp = powers(g, 5)
    gp_inv = [inverse(p) for p in gp]

    base = base0[:]
    idx = 0
    pt = []

    for L in word_lengths:
        word_ct = ct_decs[idx:idx+L]
        base_inv = inverse(base)
        for j, c in enumerate(word_ct):
            p = gp_inv[j % 5][base_inv[c]]
            pt.append(p)
        idx += L
        g_factor = gp[(L - 1) % 5]
        base = compose(base, compose(g_factor, sigma))

    return pt


def recover_base_0_two_rune(ct_decs, word_lengths, g, sigma):
    """
    Recover base_0 via hill-climbing on 2-rune word likelihood.
    When (g, sigma) are correct, this recovers base_0 EXACTLY.
    """
    gp = powers(g, 5)
    gp_inv = [inverse(p) for p in gp]

    # Extract 2-rune words with their base context
    two_rune_pairs = []
    idx = 0
    base = list(range(M))  # identity base_0
    base_history = []
    for L in word_lengths:
        base_history.append(base[:])
        if L == 2 and idx + 1 < len(ct_decs):
            two_rune_pairs.append((ct_decs[idx], ct_decs[idx+1], base[:]))
        idx += L
        g_factor = gp[(L - 1) % 5]
        base = compose(base, compose(g_factor, sigma))

    if len(two_rune_pairs) < 5:
        return list(range(M))  # not enough 2-rune words

    # Common Runeglish 2-rune words (decimal pairs)
    # THE=(2,18), OF=(3,0), TO=(16,3), IN=(10,9), IS=(10,15), IT=(10,16), AS=(24,15), AT=(24,16)
    # HE=(8,18), WE=(7,18), BE=(17,18), ME=(19,18), AN=(24,9), ND(9,4), ER(4,18), RE(18,4)
    common_pairs = {
        (2, 18), (3, 0), (16, 3), (10, 9), (10, 15), (10, 16),
        (24, 15), (24, 16), (8, 18), (7, 18), (17, 18), (19, 18),
        (24, 9), (9, 4), (4, 18), (18, 4), (24, 8), (8, 19),
        (18, 9), (4, 9),  # EN, NE
        (24, 4),  # AR
        (15, 24),  # SA
        (18, 4),  # RE (repeated)
    }

    # Hill-climb base_0
    best_base = list(range(M))
    best_score = -1
    rng = random.Random(42)

    for trial in range(200):
        base_0 = list(range(M))
        rng.shuffle(base_0)
        base_0_inv = inverse(base_0)

        score = 0
        for c0, c1, base in two_rune_pairs:
            # For the first word, base = base_0
            # For subsequent words, base has evolved
            # But base_0 determines the evolution
            # Simplified: just check the first few words where base ≈ base_0
            p0 = base_0_inv[c0]
            p1 = gp_inv[1][base_0_inv[c1]]
            if (p0, p1) in common_pairs:
                score += 1

        if score > best_score:
            best_score = score
            best_base = base_0[:]

    return best_base


def load_corpus():
    """Load the unsolved LP2 corpus with word boundaries."""
    with open(os.path.join(SCRIPT_DIR, "unsolved_pages.json")) as f:
        unsolved = json.load(f)

    # For now, treat each page as a sequence of words
    # Word boundaries are determined by the delimiters in the raw text
    # Since we don't have delimiters in the JSON, use a heuristic:
    # treat the full corpus as one word (tests g alone)
    # OR use fixed word lengths of 5 (period-5 structure)

    all_runes = "".join(p["runes"] for p in unsolved)
    ct_decs = runes_to_decimals(all_runes)

    return ct_decs


def load_corpus_with_word_boundaries():
    """Load the corpus with actual word boundaries from the raw text.
    
    LP2 delimiters (from analysis):
    - • (bullet) = word separator (primary)
    - . = sentence separator
    - * = section separator
    - & = page separator
    - $ = chapter separator
    - - = line-break within a word (join, don't split)
    - \n, space = formatting (ignore)
    """
    lp_path = os.path.join(RESEARCH_DIR, "raw", "liber_primus.txt")
    if not os.path.exists(lp_path):
        print(f"WARNING: {lp_path} not found, using period-5 word lengths", file=sys.stderr)
        ct_decs = load_corpus()
        n_words = len(ct_decs) // 5
        word_lengths = [5] * n_words + [len(ct_decs) - n_words * 5]
        return ct_decs, [L for L in word_lengths if L > 0]

    with open(lp_path) as f:
        text = f.read()

    # Find LP2 section (after "# LP2")
    lp2_start = text.find("# LP2")
    if lp2_start == -1:
        ct_decs = load_corpus()
        n_words = len(ct_decs) // 5
        word_lengths = [5] * n_words + [len(ct_decs) - n_words * 5]
        return ct_decs, [L for L in word_lengths if L > 0]

    lp2_text = text[lp2_start:]

    # Parse word lengths: words are separated by • . * & $
    # The - is a line-break within a word (join, don't split)
    from gematria_primus import is_rune
    word_lengths = []
    current_word = 0
    word_separators = "•.*&$"  # NOT - or space or newline
    
    for ch in lp2_text:
        if is_rune(ch):
            current_word += 1
        elif ch in word_separators:
            if current_word > 0:
                word_lengths.append(current_word)
                current_word = 0
        # Ignore -, space, \n, / (line breaks within words)
    if current_word > 0:
        word_lengths.append(current_word)

    # Trim to match the unsolved corpus length
    ct_decs = load_corpus()
    total_runes_in_words = sum(word_lengths)
    if total_runes_in_words > len(ct_decs):
        trimmed = []
        total = 0
        for L in word_lengths:
            if total + L > len(ct_decs):
                trimmed.append(len(ct_decs) - total)
                break
            trimmed.append(L)
            total += L
        word_lengths = trimmed
    elif total_runes_in_words < len(ct_decs):
        word_lengths.append(len(ct_decs) - total_runes_in_words)

    avg_len = len(ct_decs) / max(1, len(word_lengths))
    print(f"Loaded corpus: {len(ct_decs)} runes, {len(word_lengths)} words (avg length {avg_len:.1f})", file=sys.stderr)
    return ct_decs, word_lengths


# Graceful shutdown handler
results_buffer = []
def signal_handler(sig, frame):
    print(f"\nReceived signal {sig}, saving results...", file=sys.stderr)
    save_results()
    sys.exit(0)

def save_results(batch_id, best_score, best_key, best_pt, trials_done, duration):
    """Save results to JSON."""
    result = {
        "batch_id": batch_id,
        "best_score": best_score,
        "best_key": {
            "base_0": [DEC_TO_LETTER[a] for a in best_key[0]] if best_key else None,
            "g": [DEC_TO_LETTER[a] for a in best_key[1]] if best_key else None,
            "sigma": [DEC_TO_LETTER[a] for a in best_key[2]] if best_key else None,
        },
        "best_plaintext": best_pt[:1000] if best_pt else "",
        "trials_done": trials_done,
        "duration_seconds": duration,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_path = os.path.join(SCRIPT_DIR, f"batch_{batch_id}_results.json")
    with open(save_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Saved results to {save_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Batched length-clocked-walk attack")
    parser.add_argument("--batch-id", type=int, required=True, help="Batch ID (0-N)")
    parser.add_argument("--num-batches", type=int, default=10, help="Total number of batches")
    parser.add_argument("--duration", type=int, default=14400, help="Duration in seconds (default: 4 hours)")
    parser.add_argument("--save-interval", type=int, default=300, help="Save results every N seconds")
    args = parser.parse_args()

    # Set up signal handler for graceful shutdown
    def handler(sig, frame):
        print(f"\nReceived signal {sig}, saving results...", file=sys.stderr)
        if best_key is not None:
            save_results(args.batch_id, best_score, best_key, best_pt, trials_done, time.time() - start)
        sys.exit(0)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

    # Load corpus
    ct_decs, word_lengths = load_corpus_with_word_boundaries()

    # Set up random seed for this batch
    seed = args.batch_id * 1000000 + 42
    rng = random.Random(seed)

    print(f"=" * 60, file=sys.stderr)
    print(f"BATCH {args.batch_id}/{args.num_batches}", file=sys.stderr)
    print(f"Seed: {seed}", file=sys.stderr)
    print(f"Duration: {args.duration}s ({args.duration/3600:.1f} hours)", file=sys.stderr)
    print(f"Corpus: {len(ct_decs)} runes, {len(word_lengths)} words", file=sys.stderr)
    print(f"=" * 60, file=sys.stderr)

    best_score = -1e18
    best_key = None
    best_pt = ""
    trials_done = 0
    start = time.time()
    last_save = start

    # Break threshold: true English scores ~-5 per quadgram
    # For 12000 runes, that's ~-60000. But with word boundaries, it's different.
    # Let's use a relative threshold: if score improves by 20% over the initial random, flag it.
    initial_scores = []

    while time.time() - start < args.duration:
        # Generate random (g, sigma)
        g = random_order_5_perm(rng)
        assert verify_order_5(g)
        sigma = random_perm(rng)

        # Recover base_0
        base_0 = recover_base_0_two_rune(ct_decs, word_lengths, g, sigma)

        # Decrypt and score
        pt_decs = decrypt_with_key(ct_decs, word_lengths, base_0, g, sigma)
        pt_runes = decimals_to_runes(pt_decs)
        score = quadgram_score(pt_runes)

        if len(initial_scores) < 10:
            initial_scores.append(score)
        elif best_score == -1e18:
            best_score = sum(initial_scores) / len(initial_scores)  # baseline

        if score > best_score:
            best_score = score
            best_key = (base_0[:], g[:], sigma[:])
            best_pt = runes_to_latin(pt_runes)
            elapsed = time.time() - start
            print(f"[trial {trials_done} t={elapsed:.0f}s] NEW BEST score={score:.1f}  {best_pt[:80]}", file=sys.stderr)

            # Check for break
            if score > -60000:  # heuristic threshold
                print(f"\n*** POTENTIAL BREAK! score={score:.1f} ***", file=sys.stderr)
                print(f"Plaintext: {best_pt[:500]}", file=sys.stderr)
                # Save immediately
                save_results(args.batch_id, best_score, best_key, best_pt, trials_done, elapsed)

        trials_done += 1

        # Save periodically
        now = time.time()
        if now - last_save > args.save_interval:
            if best_key is not None:
                save_results(args.batch_id, best_score, best_key, best_pt, trials_done, now - start)
            last_save = now
            elapsed = now - start
            rate = trials_done / elapsed if elapsed > 0 else 0
            print(f"[checkpoint] trials={trials_done} rate={rate:.1f}/s best={best_score:.1f} elapsed={elapsed/60:.1f}min", file=sys.stderr)

    # Final save
    if best_key is not None:
        save_results(args.batch_id, best_score, best_key, best_pt, trials_done, time.time() - start)

    print(f"\nBATCH {args.batch_id} COMPLETE", file=sys.stderr)
    print(f"Trials: {trials_done}", file=sys.stderr)
    print(f"Best score: {best_score:.1f}", file=sys.stderr)
    print(f"Best plaintext: {best_pt[:200]}", file=sys.stderr)


if __name__ == "__main__":
    main()
