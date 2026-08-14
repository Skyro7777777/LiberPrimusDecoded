#!/usr/bin/env python3
"""length_clocked_walk_attack.py — Hill-climb attack on the length-clocked-walk
cipher using the contraction cribs as anchors.

Task ID: p8i (Phase H).

Strategy:
  - Load the LP2 unsolved corpus (sections 0-15; section 16 is solved Parable).
  - For each candidate (base_0, g, σ):
      - Decrypt the full corpus with LengthClockedWalk.
      - Score with runeglish quadgram log-probability.
      - Bonus: +N for each crib position whose tail decrypts to {S,D,T}.
  - Hill-climb: mutate base_0, g, or σ; accept if score improves.
    Mutations on g must preserve order 5.
  - Restart from random keys multiple times.
"""
from __future__ import annotations
import json, math, random, sys, time
from pathlib import Path

DECODER = Path(__file__).resolve().parent
ALDEGONDE = DECODER.parent / "solvers" / "aldegonde"
sys.path.insert(0, str(DECODER))
sys.path.insert(0, str(ALDEGONDE))
sys.path.insert(0, str(ALDEGONDE / "src"))

from length_clocked_walk import (  # noqa: E402
    LengthClockedWalk, M, perm_compose, perm_inverse, perm_power,
    is_order_5, random_order_5_permutation,
)

RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
LETTERS = ["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B","E","M",
           "L","NG","OE","D","A","AE","Y","IA","EA"]
R2I = {r: i for i, r in enumerate(RUNES)}
# aldegonde data uses ᛂ (U+16C2) instead of ᛁ (U+16C1) — normalize
RUNE_NORM = {"ᛂ": "ᛁ"}

# Plain "S","D","T" → rune indices 15, 23, 16
CRIB_TAIL_SET = {15, 23, 16}

# Crib locations (page, target word_index, position-in-word of tail rune, tail set)
# word_index is the global index into our corpus word list
# These come from the aldegonde contraction-cribs.md:
#   page 4  offset 1107: word "ᛗᛉᛁ'ᚹ" → tail ᚹ at in-word position 3
#   page 21 offset 5136: word "ᚫᚩ'ᚣ"  → tail ᚣ at in-word position 2
#   page 35 offset 8513: word "ᛈᛖ'ᛏ"   → tail ᛏ at in-word position 2
#   page 41 offset 10086: word "ᛉᛚᛄ'ᚳ" → tail ᚳ at in-word position 3
# We locate them in the corpus by matching the rune sequence (excluding apostrophe).
# RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
#   idx: 0=F 1=U 2=TH 3=O 4=R 5=C 6=G 7=W 8=H 9=N 10=I 11=J 12=EO
#        13=P 14=X 15=S 16=T 17=B 18=E 19=M 20=L 21=NG 22=OE 23=D
#        24=A 25=AE 26=Y 27=IA 28=EA
CRIB_RUNE_PATTERNS = [
    ("page4",  [19, 14, 10, 7]),     # ᛗᛉᛁᚹ  (M, X, I, W)
    ("page21", [25, 3, 26]),         # ᚫᚩᚣ    (AE, O, Y)
    ("page35", [13, 18, 16]),        # ᛈᛖᛏ    (P, E, T)
    ("page41", [14, 20, 11, 5]),     # ᛉᛚᛄᚳ  (X, L, J, C) — also try ᛁ at idx 2 below
]
CRIB_TAIL_POSITIONS = {"page4": 3, "page21": 2, "page35": 2, "page41": 3}


def rune_to_idx(r):
    r = RUNE_NORM.get(r, r)
    return R2I.get(r)


def load_corpus_words():
    """Load LP2 unsolved sections 0..15 as list of words (each list[int])."""
    from lp_section_data import lp_sections_by_red_runes
    words = []
    for sec_idx, sec in enumerate(lp_sections_by_red_runes):
        if sec_idx == 16:  # solved Parable — skip
            continue
        for w in sec:
            iw = []
            for ch in w:
                ri = rune_to_idx(ch)
                if ri is not None:
                    iw.append(ri)
            if iw:
                words.append(iw)
    return words


def locate_cribs(words):
    """Find word indices for each crib pattern."""
    locs = {}
    for name, pat in CRIB_RUNE_PATTERNS:
        for wi, w in enumerate(words):
            if w == pat:
                locs[name] = wi
                break
        # page41 fallback: try with ᛁ at position 2 (aldegonde data uses ᛂ = ᛁ for what doc writes ᛄ)
        if name == "page41" and "page41" not in locs:
            alt = [14, 20, 10, 5]
            for wi, w in enumerate(words):
                if w == alt:
                    locs[name] = wi
                    break
    return locs


def load_quadgram_scorer():
    quad_path = ALDEGONDE / "src" / "aldegonde" / "data" / "ngrams" / "runeglish" / "quadgrams.txt"
    quad = {}
    with open(quad_path) as f:
        for line in f:
            parts = line.split()
            if len(parts) != 2:
                continue
            gram, count = parts[0], int(parts[1])
            if len(gram) != 4:
                continue
            idxs = tuple(R2I.get(c) for c in gram)
            if None in idxs:
                continue
            quad[idxs] = count
    total = sum(quad.values())
    log_total = math.log10(total)
    floor = math.log10(0.01 / total)
    quad_log = {k: math.log10(v) - log_total for k, v in quad.items()}

    # Index flat = quad_log.values() minimum seen, but use floor for unseen
    def score(idxs):
        if len(idxs) < 4:
            return -100.0
        s = 0.0
        for i in range(len(idxs) - 3):
            q = tuple(idxs[i:i+4])
            s += quad_log.get(q, floor)
        return s
    return score, quad_log, floor


def idx_to_letters(idxs):
    return "".join(LETTERS[i] for i in idxs)


# ============================================================================
# MUTATION UTILITIES
# ============================================================================
def mutate_base_or_sigma(p, rng):
    """Swap two positions. Always a valid permutation."""
    q = list(p)
    i, j = rng.randrange(M), rng.randrange(M)
    while i == j:
        j = rng.randrange(M)
    q[i], q[j] = q[j], q[i]
    return q


def mutate_g(g, rng):
    """Mutate g while preserving order 5.

    Strategy: pick a random 5-cycle in g (we know there are 5 + 4 fixed points),
    rotate the cycle's image by one step within the cycle (still a 5-cycle).
    """
    # Find cycles
    visited = [False] * M
    cycles = []
    for start in range(M):
        if visited[start]:
            continue
        cyc = []
        x = start
        while not visited[x]:
            visited[x] = True
            cyc.append(x)
            x = g[x]
        cycles.append(cyc)
    # pick a 5-cycle
    five_cycles = [c for c in cycles if len(c) == 5]
    if not five_cycles:
        return list(g)  # nothing to mutate
    cyc = rng.choice(five_cycles)
    # rotate the mapping within the cycle: a->b->c->d->e becomes a->c->d->e->b
    # (or any re-ordering of the same 5 elements that's still a single 5-cycle)
    # Simplest: shift by k positions (k=1 gives the same cycle reversed; pick k=2 for a different cycle)
    k = rng.choice([1, 2, 3, 4])
    new_g = list(g)
    n = len(cyc)
    for i, x in enumerate(cyc):
        new_g[x] = cyc[(i + k) % n]
    return new_g


def random_permutation(rng):
    p = list(range(M))
    rng.shuffle(p)
    return p


# ============================================================================
# SCORING
# ============================================================================
def score_key(base0, g, sigma, ct_words, scorer, crib_locs, quad_floor,
              crib_bonus=50.0):
    """Decrypt corpus, return (total_score, n_cribs_matched, pt_first_100_letters)."""
    try:
        c = LengthClockedWalk(base0, g, sigma)
    except ValueError:
        return (-1e9, 0, "")
    pt_words = c.decrypt_corpus(ct_words)
    flat = [r for w in pt_words for r in w]
    base_score = scorer(flat)
    # Crib match check
    n_match = 0
    for name, wi in crib_locs.items():
        if wi >= len(pt_words):
            continue
        w = pt_words[wi]
        pos = CRIB_TAIL_POSITIONS[name]
        if pos < len(w) and w[pos] in CRIB_TAIL_SET:
            n_match += 1
    total = base_score + crib_bonus * n_match
    snippet = idx_to_letters(flat[:120])
    return (total, n_match, snippet)


# ============================================================================
# HILL-CLIMB
# ============================================================================
def hillclimb(ct_words, scorer, quad_floor, time_budget_s=60.0,
              seed=3301, verbose=True):
    rng = random.Random(seed)
    crib_locs = locate_cribs(ct_words)
    if verbose:
        print(f"[hillclimb] crib locations: {crib_locs}", flush=True)

    best_overall = None
    start = time.time()
    restart = 0
    while time.time() - start < time_budget_s:
        restart += 1
        # Random init
        base0 = random_permutation(rng)
        g = random_order_5_permutation(rng)
        sigma = random_permutation(rng)
        cur_score, cur_match, cur_snip = score_key(
            base0, g, sigma, ct_words, scorer, crib_locs, quad_floor)
        cur = (base0, g, sigma)
        improved = True
        iters = 0
        while improved and time.time() - start < time_budget_s:
            improved = False
            # Try a batch of mutations
            for _ in range(60):
                if time.time() - start > time_budget_s:
                    break
                mt = rng.choice(["base", "sigma", "g"])
                if mt == "base":
                    new_base0 = mutate_base_or_sigma(cur[0], rng)
                    cand = (new_base0, cur[1], cur[2])
                elif mt == "sigma":
                    new_sigma = mutate_base_or_sigma(cur[2], rng)
                    cand = (cur[0], cur[1], new_sigma)
                else:
                    new_g = mutate_g(cur[1], rng)
                    if not is_order_5(new_g):
                        continue
                    cand = (cur[0], new_g, cur[2])
                s, m, snip = score_key(*cand, ct_words, scorer, crib_locs, quad_floor)
                iters += 1
                if s > cur_score:
                    cur = cand
                    cur_score, cur_match, cur_snip = s, m, snip
                    improved = True
        if best_overall is None or cur_score > best_overall[0]:
            best_overall = (cur_score, cur_match, cur_snip, cur, restart)
            if verbose:
                print(f"[hillclimb] restart={restart} score={cur_score:.2f} "
                      f"cribs={cur_match}/{len(crib_locs)} "
                      f"snippet={cur_snip[:80]}", flush=True)
    return best_overall


# ============================================================================
# DJUBEI CONSTRAINT ANALYSIS
# ============================================================================
def dju_analysis(ct_words):
    """Analyze the DJUBEI repeat constraint.

    DJU at word indices 1477 and 2926. Under the walk model:
      base_2926 = base_1477 ∘ (product of 1449 word-step factors)

    For the two ciphertext words to be IDENTICAL (ᛞᛄᚢ = DJU), the bases and
    the within-word g-states must agree — meaning the 1449-word-step product
    of (g^((L-1)%5) ∘ σ) must equal identity (base_1477 → base_2926).

    Equivalently: ∏_{w=1477..2925} (g^((L_w-1) % 5) ∘ σ) = id
    This factors as: g^(sum_of_exponents) ∘ σ^1449 ∘ (cross-terms) — but g and
    σ don't commute in general, so the product is a specific group element that
    must equal identity.

    We check: for the 1449 word lengths between the two DJU occurrences, what
    is ∑ (L_w - 1) mod 5? And how many σs would need to be applied?

    Returns a summary dict.
    """
    # Find DJU occurrences
    dju_runes = [23, 10, 1]  # ᛞᛂᚢ in aldegonde data; ᛂ normalizes to ᛁ(10). Doc writes ᛄ but data has ᛂ
    occurrences = []
    for i, w in enumerate(ct_words):
        if w == dju_runes:
            occurrences.append(i)
    summary = {"dju_word_indices": occurrences}
    if len(occurrences) < 2:
        summary["note"] = "Fewer than 2 DJU occurrences — cannot constrain."
        return summary
    w1, w2 = occurrences[0], occurrences[1]
    summary["distance_words"] = w2 - w1
    summary["distance_runes_check"] = (
        "expected 6395 from aldegonde doc — verify"
    )

    # Sum of (L_w - 1) mod 5 over the intervening words
    lengths = [len(ct_words[i]) for i in range(w1, w2)]
    sum_exponents = sum((L - 1) % 5 for L in lengths)
    n_words_between = w2 - w1
    summary["n_intervening_words"] = n_words_between
    summary["sum_exponents_mod5"] = sum_exponents % 5

    # The walk requires the product:
    #   ∏_{w=w1..w2-1} (g^((L_w-1) % 5) ∘ σ) = identity  (for base to recur)
    # In the abelianization of the free group on g, σ this gives:
    #   g^(sum_exponents) * σ^(n_words_between) = id  (mod commutator)
    # i.e. [g]^sum * [σ]^n = 0 → in abelianization
    # Aldegonde's note says this collapses to parity for typical S_29 keys
    # (since |G/G'| = 1 or 2), so it's a weak constraint.
    summary["abelian_constraint"] = (
        f"g^{sum_exponents % 5} ∘ σ^{n_words_between % 2} ≡ id (mod commutator)"
    )
    summary["interpretation"] = (
        "Per aldegonde/repeated-phrase-dju-bei.md: this is a state-return "
        "constraint (base_1477 = base_2926) requiring the full 1449-step "
        "composition. In the abelianization it collapses to a parity "
        "condition on σ (since 29-cycle σ has even parity automatically), "
        "so it does NOT pin g or σ individually. The full non-abelian "
        "constraint is one equation in the 200-bit key — far too weak to "
        "recover the key by itself."
    )
    return summary


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("=== Loading LP2 corpus ===", flush=True)
    ct_words = load_corpus_words()
    print(f"Loaded {len(ct_words)} words, {sum(len(w) for w in ct_words)} runes",
          flush=True)

    print("\n=== Locating cribs ===", flush=True)
    crib_locs = locate_cribs(ct_words)
    for name, wi in crib_locs.items():
        print(f"  {name}: word index {wi} = {ct_words[wi]} ({idx_to_letters(ct_words[wi])})",
              flush=True)

    print("\n=== Loading quadgram scorer ===", flush=True)
    scorer, quad_log, floor = load_quadgram_scorer()
    print(f"  Loaded {len(quad_log)} quadgrams; floor={floor:.3f}", flush=True)

    print("\n=== DJUBEI constraint analysis ===", flush=True)
    dju = dju_analysis(ct_words)
    for k, v in dju.items():
        print(f"  {k}: {v}", flush=True)

    print("\n=== Hill-climb (60s budget) ===", flush=True)
    best = hillclimb(ct_words, scorer, floor, time_budget_s=60.0, seed=3301)
    print("\n=== Hill-climb complete ===", flush=True)
    if best is None:
        print("No result.", flush=True)
        result = {"error": "no result"}
    else:
        score, match, snip, key, restart = best
        base0, g, sigma = key
        # Re-decrypt for full plaintext preview
        c = LengthClockedWalk(base0, g, sigma)
        pt_words = c.decrypt_corpus(ct_words)
        flat = [r for w in pt_words for r in w]
        full_pt = idx_to_letters(flat)
        result = {
            "best_score": score,
            "cribs_matched": match,
            "n_cribs_total": len(crib_locs),
            "restarts": restart,
            "plaintext_first_200": full_pt[:200],
            "base0": base0,
            "g": g,
            "sigma": sigma,
            "dju_analysis": dju,
            "crib_locations": crib_locs,
        }
        print(f"  Best score: {score:.2f}", flush=True)
        print(f"  Cribs matched: {match}/{len(crib_locs)}", flush=True)
        print(f"  Restarts: {restart}", flush=True)
        print(f"  Plaintext first 200: {full_pt[:200]}", flush=True)
        # Sanity: decrypt the 4 crib words specifically
        print("\n=== Crib word decryptions ===", flush=True)
        for name, wi in crib_locs.items():
            w_pt = pt_words[wi]
            print(f"  {name} (word {wi}): ct={idx_to_letters(ct_words[wi])} "
                  f"→ pt={idx_to_letters(w_pt)} (tail at pos {CRIB_TAIL_POSITIONS[name]} "
                  f"= {LETTERS[w_pt[CRIB_TAIL_POSITIONS[name]]] if CRIB_TAIL_POSITIONS[name] < len(w_pt) else '?'})",
                  flush=True)

    out_path = DECODER / "length_clocked_walk_results.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nResults saved to {out_path}", flush=True)


if __name__ == "__main__":
    main()
