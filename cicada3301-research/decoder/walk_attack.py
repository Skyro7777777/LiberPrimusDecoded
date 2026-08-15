#!/usr/bin/env python3
"""
walk_attack.py — Random-restart attack on the length-clocked-walk cipher.
=========================================================================
For each random (g, σ) pair:
1. Recover base_0 via the 2-rune likelihood hill-climb (VALIDATED by aldegonde)
2. Decrypt the full corpus
3. Score with quadgrams
4. Report the best

The key insight: base_0 recovery is EXACT when (g, σ) are correct (~1s per pair).
So we can sample many (g, σ) pairs and check each quickly.
"""
import sys, os, json, random, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "solvers", "aldegonde", "experiments"))

from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, N_RUNES, MOD,
    runes_to_decimals, decimals_to_runes, runes_to_latin,
)
from first_diff_masc import quadgram_score, QUADGRAMS

# Import aldegonde's walk cipher
WALK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "solvers", "aldegonde", "experiments")
sys.path.insert(0, WALK_PATH)

try:
    from length_clocked_cipher import compose, inverse, powers, bases
    print("Loaded aldegonde's length_clocked_cipher module", file=sys.stderr)
except ImportError as e:
    print(f"WARNING: could not import aldegonde walk module: {e}", file=sys.stderr)
    # Fallback implementations
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
    def bases(base0, g, sigma, lengths):
        gp = powers(g, 5)
        out = [base0]
        base = base0
        for L in lengths:
            base = compose(base, compose(gp[(L - 1) % 5], sigma))
            out.append(base)
        return out


M = N_RUNES  # 29


def random_order_5_perm():
    """Generate a random order-5 permutation on 29 elements.
    29 = 5*5 + 4, so 5 five-cycles and 4 fixed points.
    """
    elems = list(range(M))
    random.shuffle(elems)
    perm = list(range(M))  # identity
    # 5 five-cycles
    for i in range(5):
        cycle = elems[i*5:(i+1)*5]
        for j in range(5):
            perm[cycle[j]] = cycle[(j+1) % 5]
    # 4 fixed points (elems[25:29] already fixed)
    return perm


def verify_order_5(perm):
    """Verify that perm^5 = identity."""
    p = perm[:]
    for _ in range(4):
        p = compose(p, perm)
    return p == list(range(M))


def random_perm():
    """Generate a random permutation on 29 elements."""
    p = list(range(M))
    random.shuffle(p)
    return p


def decrypt_with_key(ct_decs, word_lengths, base0, g, sigma):
    """Decrypt the full ciphertext using the walk key."""
    gp = powers(g, 5)  # [g^0, g^1, g^2, g^3, g^4]
    gp_inv = [inverse(p) for p in gp]
    
    base = base0[:]
    idx = 0
    pt = []
    
    for w, L in enumerate(word_lengths):
        word_ct = ct_decs[idx:idx+L]
        word_pt = []
        for j, c in enumerate(word_ct):
            # c = base(g^(j%5)(p)) → p = g^(-j%5)(base_inv(c))
            base_inv = inverse(base)
            g_inv_pow = gp_inv[j % 5]
            p = g_inv_pow[base_inv[c]]
            word_pt.append(p)
        pt.extend(word_pt)
        idx += L
        
        # Update base: base = base ∘ g^((L-1) % 5) ∘ sigma
        g_factor = gp[(L - 1) % 5]
        base = compose(base, compose(g_factor, sigma))
    
    return pt


def recover_base_0(ct_decs, word_lengths, g, sigma):
    """
    Recover base_0 via hill-climbing on the 2-rune word likelihood.
    
    For 2-rune words, the decryption is:
    c[0] = base(g^0(p[0])) = base(p[0])
    c[1] = base(g^1(p[1])) = base(g(p[1]))
    
    So: p[0] = base_inv(c[0])
        p[1] = g_inv(base_inv(c[1]))
    
    The most common 2-rune word in Runeglish is THE (ᚦᛖ = TH,E).
    We hill-climb base_0 to maximize the frequency of common 2-rune words.
    """
    # Extract 2-rune words
    gp = powers(g, 5)
    gp_inv = [inverse(p) for p in gp]
    
    two_rune_words = []
    idx = 0
    base = list(range(M))  # start with identity base_0
    for L in word_lengths:
        if L == 2 and idx + 1 < len(ct_decs):
            two_rune_words.append((ct_decs[idx], ct_decs[idx+1]))
        idx += L
        base = compose(base, compose(gp[(L - 1) % 5], sigma))
    
    if not two_rune_words:
        return list(range(M))  # fallback
    
    # The most common Runeglish 2-rune words (from aldegonde's data):
    # THE (ᚦᛖ), OF (ᚩᚠ), TO (ᛏᚩ), IN (ᛁᚾ), IS (ᛁᛋ), IT (ᛁᛏ), AS (ᚪᛋ), AT (ᚪᛏ)
    # Their decimal values: THE=(2,18), OF=(3,0), TO=(16,3), IN=(10,9), IS=(10,15), IT=(10,16), AS=(24,15), AT=(24,16)
    common_pairs = {(2, 18), (3, 0), (16, 3), (10, 9), (10, 15), (10, 16), (24, 15), (24, 16)}
    
    # Hill-climb base_0 to maximize common 2-rune word count
    best_base = list(range(M))
    best_score = -1
    
    for trial in range(500):  # 500 trials
        base_0 = list(range(M))
        random.shuffle(base_0)
        
        # Compute the 2-rune word plaintexts for this base_0
        score = 0
        for c0, c1 in two_rune_words:
            p0 = base_0[c0]  # base_inv = inverse, but base_0 IS the permutation, so base_0[p]=c → p=base_0_inv[c]
            # Actually: c = base(p) → p = base_inv(c). base = base_0 initially.
            # So p0 = base_0_inv(c0)
            base_0_inv = inverse(base_0)
            p0 = base_0_inv[c0]
            p1 = gp_inv[1][base_0_inv[c1]]  # g_inv(base_inv(c1))
            if (p0, p1) in common_pairs:
                score += 1
        
        if score > best_score:
            best_score = score
            best_base = base_0[:]
    
    return best_base


def attack(ct_decs, word_lengths, n_trials=100, timeout=240):
    """Random-restart attack: try many (g, σ) pairs, recover base_0 for each."""
    start = time.time()
    best_score = -1e18
    best_key = None
    best_pt = ""
    
    for trial in range(n_trials):
        if time.time() - start > timeout:
            break
        
        # Generate random g (order 5) and σ
        g = random_order_5_perm()
        assert verify_order_5(g)
        sigma = random_perm()
        
        # Recover base_0 via 2-rune hill-climb
        base_0 = recover_base_0(ct_decs, word_lengths, g, sigma)
        
        # Decrypt and score
        pt_decs = decrypt_with_key(ct_decs, word_lengths, base_0, g, sigma)
        pt_runes = decimals_to_runes(pt_decs)
        score = quadgram_score(pt_runes)
        
        if score > best_score:
            best_score = score
            best_key = (base_0[:], g[:], sigma[:])
            best_pt = runes_to_latin(pt_runes)
            elapsed = time.time() - start
            print(f"[trial {trial} t={elapsed:.0f}s] score={score:.1f}  {best_pt[:80]}", file=sys.stderr)
        
        if trial % 10 == 0:
            elapsed = time.time() - start
            print(f"trial {trial}/{n_trials} (t={elapsed:.0f}s) best={best_score:.1f}", file=sys.stderr)
    
    return best_key, best_score, best_pt


def main():
    # Load the unsolved LP2 corpus with word boundaries
    # The word boundaries are the delimiters in the raw text
    # We need to parse the raw liber_primus.txt to get word lengths
    
    # For now, use a simplified approach: treat the full corpus as one "word"
    # (this tests the g model without σ)
    # Then try with word boundaries from the raw text
    
    print("=" * 60, file=sys.stderr)
    print("LENGTH-CLOCKED-WALK ATTACK", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    # Load unsolved pages
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "unsolved_pages.json")) as f:
        unsolved = json.load(f)
    
    # Get the raw text with delimiters for word boundary extraction
    # Use the first unsolved section (page 0, 729 runes)
    first_page = unsolved[0]
    ct_runes = first_page["runes"]
    ct_decs = runes_to_decimals(ct_runes)
    
    # For word boundaries: the raw text has delimiters between words
    # For now, try two approaches:
    # 1. Single word (no σ, tests g alone)
    # 2. Words of length 5 (uniform, tests the period-5 structure)
    
    print(f"\nAttack 1: Single word (no σ, tests g alone)", file=sys.stderr)
    word_lengths_1 = [len(ct_decs)]  # one big word
    key1, score1, pt1 = attack(ct_decs, word_lengths_1, n_trials=50, timeout=80)
    print(f"\nBest single-word: score={score1:.1f}", file=sys.stderr)
    print(f"Plaintext: {pt1[:200]}", file=sys.stderr)
    
    print(f"\nAttack 2: Words of length 5 (uniform period-5)", file=sys.stderr)
    n_words = len(ct_decs) // 5
    word_lengths_2 = [5] * n_words + [len(ct_decs) - n_words * 5]
    word_lengths_2 = [L for L in word_lengths_2 if L > 0]
    key2, score2, pt2 = attack(ct_decs, word_lengths_2, n_trials=50, timeout=80)
    print(f"\nBest period-5: score={score2:.1f}", file=sys.stderr)
    print(f"Plaintext: {pt2[:200]}", file=sys.stderr)
    
    print(f"\nAttack 3: Random word lengths (simulating real word boundaries)", file=sys.stderr)
    # Generate random word lengths averaging 4 (typical English word length)
    word_lengths_3 = []
    idx = 0
    while idx < len(ct_decs):
        L = random.randint(1, 8)
        if idx + L > len(ct_decs):
            L = len(ct_decs) - idx
        word_lengths_3.append(L)
        idx += L
    key3, score3, pt3 = attack(ct_decs, word_lengths_3, n_trials=50, timeout=80)
    print(f"\nBest random-words: score={score3:.1f}", file=sys.stderr)
    print(f"Plaintext: {pt3[:200]}", file=sys.stderr)
    
    # Save results
    results = {
        "single_word": {"score": score1, "plaintext": pt1[:500]},
        "period_5": {"score": score2, "plaintext": pt2[:500]},
        "random_words": {"score": score3, "plaintext": pt3[:500]},
    }
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "walk_attack_results.json"), "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved walk_attack_results.json", file=sys.stderr)


if __name__ == "__main__":
    main()
