#!/usr/bin/env python3
"""
transposition_attack.py — Delimiter-keyed Transposition attack on LP2 unsolved corpus
=====================================================================================
Task ID: p6e (Phase E FINAL hypothesis).

4 Models:
  M1: Delimiter-position grid write, column-major read (control vs row-major)
  M2: Hierarchical grid (page>section>paragraph>row>word) with various readouts
  M3: Rail-fence / columnar transposition keyed by delimiter-count sequence
  M4: Permutation recovery via crib-drag (4 contraction cribs at known positions)

Scores with english_score() from gematria_primus.py.
Random-baseline ceiling ~74, P99=74.36. Break threshold >75.
"""
from __future__ import annotations
import json, sys, os, math, itertools, random
from collections import Counter
from typing import List, Dict, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_LETTER, N_RUNES, MOD,
    is_rune, rune_to_dec, dec_to_rune, runes_to_decimals,
    runes_to_latin, english_score, KEY_CANDIDATES, clean_runes,
)

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "translit_pages_with_delims.json")
OUT_JSON  = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "transposition_results.json")

# === Load corpus ===========================================================

def load_lp2_corpus(test_n: int = 500):
    """Return list of (rune, delim_after) for first N runes of LP2 (pages 17-55)."""
    data = json.load(open(DATA_PATH))
    pairs: List[Tuple[str, str]] = []
    for k in sorted(data.keys(), key=lambda x: int(x.split('.')[0])):
        pno = int(k.split('.')[0])
        if pno < 17 or pno > 55:
            continue
        text = data[k]
        cur_rune = None
        cur_delims = []
        for ch in text:
            if is_rune(ch):
                if cur_rune is not None:
                    pairs.append((cur_rune, "".join(cur_delims)))
                    cur_delims = []
                cur_rune = ch
            else:
                cur_delims.append(ch)
        # trailing rune of page
        if cur_rune is not None:
            pairs.append((cur_rune, "".join(cur_delims) + "\n\n"))  # page break
        if len(pairs) >= test_n + 50:
            break
    return pairs


def pairs_to_runes(pairs: List[Tuple[str,str]]) -> str:
    return "".join(r for r, _ in pairs)


def pairs_to_delims(pairs: List[Tuple[str,str]]) -> str:
    return "".join(d for _, d in pairs)


# === M1: Delimiter-position grid write, various readouts ===================

def m1_grid_column_readout(pairs: List[Tuple[str,str]]) -> Dict[str, str]:
    """
    Write runes into rows where each row = a sequence of runes separated by
    a delimiter. Then read column-major.
    Also test other readouts.
    """
    # Split into rows by ANY delimiter occurrence
    rows: List[List[str]] = []
    cur: List[str] = []
    for r, d in pairs:
        cur.append(r)
        if d:  # any delimiter terminates the row
            rows.append(cur)
            cur = []
    if cur:
        rows.append(cur)

    # Pad to uniform length
    max_w = max(len(r) for r in rows)
    grid = [r + [None] * (max_w - len(r)) for r in rows]
    H = len(grid); W = max_w

    results = {}

    # Row-major (control)
    row_major = [c for r in grid for c in r if c is not None]
    results["row_major_control"] = "".join(row_major)

    # Column-major (top-down, left-right)
    col_major = []
    for x in range(W):
        for y in range(H):
            if grid[y][x] is not None:
                col_major.append(grid[y][x])
    results["col_major"] = "".join(col_major)

    # Column-major reverse
    col_major_rev = []
    for x in range(W - 1, -1, -1):
        for y in range(H - 1, -1, -1):
            if grid[y][x] is not None:
                col_major_rev.append(grid[y][x])
    results["col_major_rev"] = "".join(col_major_rev)

    # Reverse rows then col-major
    grid_rev = grid[::-1]
    cm_rows_rev = []
    for x in range(W):
        for y in range(H):
            if grid_rev[y][x] is not None:
                cm_rows_rev.append(grid_rev[y][x])
    results["col_major_rows_rev"] = "".join(cm_rows_rev)

    # Spiral inward
    spiral = []
    seen = [[False] * W for _ in range(H)]
    dx = [0, 1, 0, -1]; dy = [1, 0, -1, 0]
    x = y = 0; di = 0
    for _ in range(H * W):
        if grid[y][x] is not None and not seen[y][x]:
            spiral.append(grid[y][x])
            seen[y][x] = True
        nx, ny = x + dx[di], y + dy[di]
        if 0 <= nx < W and 0 <= ny < H and not seen[ny][nx]:
            x, y = nx, ny
        else:
            di = (di + 1) % 4
            x, y = x + dx[di], y + dy[di]
    results["spiral"] = "".join(spiral)

    # Boustrophedon (alternating row direction)
    bous = []
    for i, r in enumerate(grid):
        if i % 2 == 0:
            bous.extend(c for c in r if c is not None)
        else:
            bous.extend(c for c in r[::-1] if c is not None)
    results["boustrophedon"] = "".join(bous)

    # Diagonal down (Z-340 style)
    diag = []
    for s in range(H + W - 1):
        if s % 2 == 0:
            for y in range(min(s, H - 1), max(0, s - W + 1) - 1, -1):
                x = s - y
                if 0 <= x < W and grid[y][x] is not None:
                    diag.append(grid[y][x])
        else:
            for x in range(min(s, W - 1), max(0, s - H + 1) - 1, -1):
                y = s - x
                if 0 <= y < H and grid[y][x] is not None:
                    diag.append(grid[y][x])
    results["diagonal_z340"] = "".join(diag)

    # Reverse entire stream
    all_runes = [c for r in grid for c in r if c is not None]
    results["reverse_all"] = "".join(all_runes[::-1])

    return results, {"H": H, "W": W, "rows": len(rows)}


# === M2: Hierarchical grid ================================================

def m2_hierarchical_readouts(pairs: List[Tuple[str,str]]) -> Dict[str, str]:
    """
    Build hierarchy: word (split by '-') < row (split by '\n')
                      < clause (split by '.') < paragraph (split by '&')
                      < section (split by '$')
    """
    # Build nested structure
    # Tokenize into words
    words: List[List[str]] = []
    cur_word: List[str] = []
    cur_row: List[List[str]] = []
    cur_clause: List[List[List[str]]] = []
    cur_para: List[List[List[List[str]]]] = []
    sections: List[List[List[List[List[List[str]]]]]] = []

    for r, d in pairs:
        cur_word.append(r)
        # check what delimiters terminate this rune
        if not d:
            continue
        if '-' in d or ' ' in d:
            cur_row.append(cur_word); cur_word = []
            # consume more: chain breaks
        if '\n' in d:
            # row end + word end
            if cur_word:
                cur_row.append(cur_word); cur_word = []
            cur_clause.append(cur_row); cur_row = []
        if '.' in d:
            cur_clause.append(cur_row) if cur_row else None
            cur_row = []
            cur_para.append(cur_clause); cur_clause = []
        if '&' in d:
            cur_para.append(cur_clause) if cur_clause else None
            cur_clause = []
            sections.append(cur_para) if cur_para else None
            # wait - sections might not have been started yet
            if not sections:
                sections.append(cur_para)
            else:
                sections[-1] = cur_para
            cur_para = []
        if '$' in d:
            if cur_para:
                sections.append(cur_para) if cur_para else None
            cur_para = []
    # finalize
    if cur_word:
        cur_row.append(cur_word)
    if cur_row:
        cur_clause.append(cur_row)
    if cur_clause:
        cur_para.append(cur_clause)
    if cur_para:
        sections.append(cur_para)

    results = {}

    # 1. Reverse within each word
    rev_word = []
    for sec in sections:
        for para in sec:
            for clause in para:
                for row in clause:
                    for word in row:
                        rev_word.extend(word[::-1])
    results["reverse_within_word"] = "".join(rev_word)

    # 2. Reverse word order within each row
    rev_row_words = []
    for sec in sections:
        for para in sec:
            for clause in para:
                for row in clause:
                    for word in row[::-1]:
                        rev_row_words.extend(word)
    results["reverse_word_order_row"] = "".join(rev_row_words)

    # 3. Reverse row order within each paragraph
    rev_para_rows = []
    for sec in sections:
        for para in sec:
            for row in clause[::-1] if clause else []:
                for word in row:
                    rev_para_rows.extend(word)
    # Note: 'clause' was the last one above; redo properly
    rev_para_rows = []
    for sec in sections:
        for para in sec:
            for clause in para[::-1]:
                for row in clause:
                    for word in row:
                        rev_para_rows.extend(word)
    results["reverse_row_order_para"] = "".join(rev_para_rows)

    # 4. Reverse paragraph order within section
    rev_sec_paras = []
    for sec in sections:
        for para in sec[::-1]:
            for clause in para:
                for row in clause:
                    for word in row:
                        rev_sec_paras.extend(word)
    results["reverse_para_order_sec"] = "".join(rev_sec_paras)

    # 5. Column-major down each paragraph (treating words as letters? rows as rows)
    # Treat each paragraph as a grid: rows = paragraphs's rows, cols = word-positions
    col_para = []
    for sec in sections:
        for para in sec:
            rows = []
            for clause in para:
                for row in clause:
                    flat = [c for w in row for c in w]
                    rows.append(flat)
            if not rows:
                continue
            max_w = max(len(r) for r in rows)
            grid = [r + [None] * (max_w - len(r)) for r in rows]
            for x in range(max_w):
                for y in range(len(grid)):
                    if grid[y][x] is not None:
                        col_para.append(grid[y][x])
    results["col_major_per_para"] = "".join(col_para)

    # 6. Read words column-major within each paragraph (Z-340 style across rows)
    z340 = []
    for sec in sections:
        for para in sec:
            rows = []
            for clause in para:
                for row in clause:
                    flat = [c for w in row for c in w]
                    rows.append(flat)
            if not rows:
                continue
            max_w = max(len(r) for r in rows)
            grid = [r + [None] * (max_w - len(r)) for r in rows]
            H, W = len(grid), max_w
            for s in range(H + W - 1):
                if s % 2 == 0:
                    for y in range(min(s, H - 1), max(0, s - W + 1) - 1, -1):
                        x = s - y
                        if grid[y][x] is not None:
                            z340.append(grid[y][x])
                else:
                    for x in range(min(s, W - 1), max(0, s - H + 1) - 1, -1):
                        y = s - x
                        if 0 <= y < H and grid[y][x] is not None:
                            z340.append(grid[y][x])
    results["z340_per_para"] = "".join(z340)

    # 7. Reverse entire stream (page-level)
    all_runes = [c for sec in sections
                   for para in sec
                   for clause in para
                   for row in clause
                   for word in row
                   for c in word]
    results["reverse_full"] = "".join(all_runes[::-1])

    return results, {"n_sections": len(sections),
                      "n_paragraphs": sum(len(s) for s in sections),
                      "n_clauses": sum(len(p) for s in sections for p in s)}


# === M3: Rail-fence / columnar keyed by delim counts ======================

def m3_rail_fence(text: str, n_rails: int) -> str:
    """Standard rail fence cipher readout."""
    if n_rails < 2 or n_rails > len(text) // 2 + 1:
        return text
    rails = [[] for _ in range(n_rails)]
    idx, step = 0, 1
    for ch in text:
        rails[idx].append(ch)
        if idx == 0:
            step = 1
        elif idx == n_rails - 1:
            step = -1
        idx += step
    return "".join("".join(r) for r in rails)


def m3_columnar(text: str, key_len: int, order: Optional[List[int]] = None) -> str:
    """Columnar transposition. If order given, use it; else column-major."""
    n = len(text)
    n_rows = math.ceil(n / key_len)
    grid = [list(text[i:i+key_len].ljust(key_len, ' ')) for i in range(0, n, key_len)]
    cols = []
    for x in range(key_len):
        col = [grid[y][x] for y in range(n_rows) if grid[y][x] != ' ']
        cols.append(col)
    if order is None:
        order = list(range(key_len))
    out = []
    for x in order:
        out.extend(cols[x])
    return "".join(out)


def m3_rail_fence_decrypt(text: str, n_rails: int) -> str:
    """Invert rail fence: given the cipher text (the rail-strips concatenated),
    recover plaintext."""
    n = len(text)
    if n_rails < 2 or n_rails > n // 2 + 1:
        return text
    # Compute rail assignment pattern
    pattern = []
    idx, step = 0, 1
    for _ in range(n):
        pattern.append(idx)
        if idx == 0:
            step = 1
        elif idx == n_rails - 1:
            step = -1
        idx += step
    # Each rail gets ceil(count) chars
    rail_lens = [pattern.count(r) for r in range(n_rails)]
    rails = []
    pos = 0
    for l in rail_lens:
        rails.append(list(text[pos:pos+l]))
        pos += l
    # Re-read zig-zag
    out = []
    rail_iters = [iter(r) for r in rails]
    for r in pattern:
        out.append(next(rail_iters[r]))
    return "".join(out)


def m3_models(pairs: List[Tuple[str,str]]) -> Dict[str, str]:
    runes = pairs_to_runes(pairs)

    # Build delimiter-count sequence between runes
    counts = [len(d) for _, d in pairs]  # number of delimiter chars after each rune
    cnt_seq = [c for c in counts if c > 0]

    results = {}

    # Rail fence: depths 2..9
    for n in range(2, 10):
        # forward direction (read rails as ciphertext, recover plaintext)
        results[f"railfence_decrypt_n{n}"] = m3_rail_fence_decrypt(runes, n)
        # backward direction (treat cipher as plaintext read zigzag, output is rails)
        results[f"railfence_encrypt_n{n}"] = m3_rail_fence(runes, n)

    # Columnar: key lengths 3..12, both direct and reversed col order
    for klen in range(3, 13):
        results[f"columnar_k{klen}_fwd"] = m3_columnar(runes, klen)
        results[f"columnar_k{klen}_rev"] = m3_columnar(runes, klen, list(range(klen))[::-1])

    # Rail-fence with depth = unique values in cnt_seq
    if cnt_seq:
        unique_vals = sorted(set(cnt_seq))
        for v in unique_vals[:5]:  # limit
            if 2 <= v <= 9:
                results[f"railfence_depth_cnt{v}"] = m3_rail_fence_decrypt(runes, v)

    return results


# === M4: Crib-drag permutation recovery ===================================

# 4 contraction cribs: page 4 (ᛗᛉᛁ'ᚹ → MXI'S tail rune must be S/D/T)
#   page 21 (ᚫᚩ'ᚣ), page 35 (ᛈᛖ'ᛏ), page 41 (ᛉᛚᛄ'ᚳ)
# Each gives a positional constraint: cipher position i has known plaintext letter.
# But for PERMUTATION recovery, we need known plaintext at known cipher-positions.

# Per LAG5_CRIBDRAG_RESULTS, the 4 cribs are at:
#   page 4 idx 164 (cipher W, global 1110)
#   page 21 idx 36 (cipher Y, global 5138)
#   page 35 idx 80 (cipher T, global 8515)
#   page 41 idx 218 (cipher C, global 10089)
# Plaintext tail runes: S, D, T (test all combinations)

CRIBS = [
    {"page": 4,  "cipher_pos_global": 1110, "cipher_rune": "ᚹ", "pt_options": ["S","D","T"]},
    {"page": 21, "cipher_pos_global": 5138, "cipher_rune": "ᚣ", "pt_options": ["S","D","T"]},
    {"page": 35, "cipher_pos_global": 8515, "cipher_rune": "ᛏ", "pt_options": ["S","D","T"]},
    {"page": 41, "cipher_pos_global": 10089,"cipher_rune": "ᚳ", "pt_options": ["S","D","T"]},
]


def m4_crib_drag_permutation(all_pairs: List[Tuple[str,str]], test_n: int = 500) -> Dict[str, str]:
    """
    Crib-drag approach: assume ciphertext is permutation of plaintext.
    If crib says pt_letter X appears at cipher position p (assuming crib-tail = X),
    then plaintext position p' = position of cipher rune in original plaintext.
    We can drag the crib across the plaintext-positions in the cipher.

    For each combination of crib assignments:
      - Test if rune at each cipher-pos in test window maps to a candidate crib letter.
      - For each window of 5-7 runes, check if it could spell S A C R E D or similar.
    """
    # Use first test_n runes for the main test
    runes_test = pairs_to_runes(all_pairs[:test_n])
    full_runes = pairs_to_runes(all_pairs)

    results = {}

    # Approach 1: Test if the cipher text itself (no permutation) contains known Cicada
    # cribs at the expected positions when no transposition is applied (sanity control)
    cribs_test = ["WELCOME", "A WARNING", "SOME WISDOM", "A COAN", "PARABLE",
                   "AN END", "AN INSTRVCTIAN", "THE PRIMES ARE SACRED",
                   "DO NOT EDIT", "FIND THE DIVINITY WITHIN", "DIVINITY", "INSTAR",
                   "SACRED", "EMERGENCE", "PILGRIM"]
    latin_test = runes_to_latin(runes_test)
    for crib in cribs_test:
        c = crib.replace(" ", "").upper()
        if c in latin_test.upper():
            results[f"crib_{crib}_direct_match"] = latin_test

    # Approach 2: Columnar transposition + crib search
    # For each column width, decrypt with crib at possible positions
    best_col = None
    best_score = -1e9
    best_text = ""
    best_cfg = ""
    for klen in range(3, 13):
        for order_offset in range(klen):
            order = [(i + order_offset) % klen for i in range(klen)]
            text = m3_columnar(runes_test, klen, order)
            s = english_score(runes_to_latin(text))
            if s > best_score:
                best_score = s
                best_text = text
                best_cfg = f"col_k{klen}_off{order_offset}"
                best_col = (klen, order)
    results[f"best_columnar_{best_cfg}"] = runes_to_latin(best_text)

    # Approach 3: Use the 4 cribs as known plaintext to recover a key-length / shift
    # Build constraint: if cipher_rune[i] = pt[k] for some k, then in a periodic cipher
    # with period P, cipher_rune[i] - pt[k] = key[i mod P]
    # For permutation cipher, this doesn't apply. We test periodic additive.

    # Approach 4: Permutation grid - if runes are written into grid and read out
    # in a different order, the crib-tail positions tell us row/col readout
    # Let's test ALL 4 crib assignments × transposition shapes
    pt_combos = list(itertools.product(["S","D","T"], repeat=4))
    # For each combo, derive key constraint for vigenere of period P
    for combo in pt_combos[:6]:  # limit to 6 of 81 combos
        # Assume permutation = additive with period P; check consistency
        # If crib-i maps to pt[k], then key[i mod P] = cipher_dec[i] - pt_dec[k]
        for P in [4, 5, 7, 13, 29]:
            if P > test_n // 2:
                continue
            key = [None] * P
            valid = True
            for crib, pt_l in zip(CRIBS, combo):
                pos = crib["cipher_pos_global"]
                if pos >= test_n:
                    continue
                cd = rune_to_dec(all_pairs[pos][0])
                pt_dec = None
                for i, letter in enumerate(DEC_TO_LETTER):
                    if letter == pt_l:
                        pt_dec = i
                        break
                if pt_dec is None:
                    valid = False; break
                slot = pos % P
                expected = (cd - pt_dec) % MOD
                if key[slot] is not None and key[slot] != expected:
                    valid = False; break
                key[slot] = expected
            if not valid:
                continue
            # Try to decrypt with partial key (fill unknown slots with 0)
            full_key_decs = [k if k is not None else 0 for k in key]
            pt_decs = []
            for i, (r, _) in enumerate(all_pairs[:test_n]):
                cd = rune_to_dec(r)
                kd = full_key_decs[i % P]
                pt_decs.append((cd - kd) % MOD)
            pt_text = "".join(DEC_TO_LETTER[d] for d in pt_decs)
            cfg = f"crib_{combo}_P{P}_key{full_key_decs}"
            results[cfg] = pt_text

    return results


# === Main runner ===========================================================

def score_all(results: Dict[str, str]) -> List[Dict]:
    scored = []
    for cfg, text in results.items():
        # text may contain delimiters from clean_runes; normalize
        latin = runes_to_latin(clean_runes(text)) if any(is_rune(c) for c in text) else text.upper()
        s = english_score(latin)
        scored.append({
            "config": cfg,
            "score": round(s, 3),
            "snippet": latin[:80],
        })
    scored.sort(key=lambda r: -r["score"])
    return scored


def main():
    print("=== Transposition attack on LP2 ===")
    pairs = load_lp2_corpus(test_n=500)
    print(f"Loaded {len(pairs)} rune-delimiter pairs (LP2 pages 17-55)")
    n_runes = sum(1 for r, _ in pairs if is_rune(r))
    print(f"Total runes: {n_runes}")

    all_results = {}

    # === Model 1 ===
    print("\n--- Model 1: Delimiter-position grid write, multiple readouts ---")
    m1_results, m1_info = m1_grid_column_readout(pairs[:500])
    print(f"  Grid: {m1_info['H']} rows x {m1_info['W']} cols")
    m1_scored = score_all(m1_results)
    for r in m1_scored[:5]:
        print(f"  {r['config']:35s} score={r['score']:7.3f}  {r['snippet'][:60]}")
    all_results["M1"] = {"info": m1_info, "results": m1_scored}

    # === Model 2 ===
    print("\n--- Model 2: Hierarchical grid (page>sec>para>row>word) readouts ---")
    m2_results, m2_info = m2_hierarchical_readouts(pairs[:500])
    print(f"  Hierarchy: {m2_info}")
    m2_scored = score_all(m2_results)
    for r in m2_scored[:5]:
        print(f"  {r['config']:35s} score={r['score']:7.3f}  {r['snippet'][:60]}")
    all_results["M2"] = {"info": m2_info, "results": m2_scored}

    # === Model 3 ===
    print("\n--- Model 3: Rail-fence / columnar keyed by delimiter counts ---")
    m3_results = m3_models(pairs[:500])
    m3_scored = score_all(m3_results)
    for r in m3_scored[:5]:
        print(f"  {r['config']:35s} score={r['score']:7.3f}  {r['snippet'][:60]}")
    all_results["M3"] = {"info": {"n_configs": len(m3_results)}, "results": m3_scored}

    # === Model 4 ===
    print("\n--- Model 4: Crib-drag permutation recovery (4 contraction cribs) ---")
    m4_results = m4_crib_drag_permutation(pairs, test_n=500)
    m4_scored = score_all(m4_results)
    for r in m4_scored[:5]:
        print(f"  {r['config']:50s} score={r['score']:7.3f}  {r['snippet'][:60]}")
    all_results["M4"] = {"info": {"n_configs": len(m4_results)}, "results": m4_scored}

    # === Save JSON ===
    json.dump(all_results, open(OUT_JSON, "w"), indent=2)
    print(f"\nResults saved to {OUT_JSON}")

    # === Aggregate top scores ===
    print("\n=== TOP 10 ACROSS ALL MODELS ===")
    combined = []
    for model, data in all_results.items():
        for r in data["results"]:
            combined.append({"model": model, **r})
    combined.sort(key=lambda r: -r["score"])
    for r in combined[:10]:
        print(f"  [{r['model']}] {r['config']:45s} score={r['score']:7.3f}  {r['snippet'][:60]}")

    # === Summary ===
    print("\n=== SUMMARY ===")
    n_total = sum(len(d["results"]) for d in all_results.values())
    print(f"Total configs tested: {n_total}")
    print(f"Top score overall: {combined[0]['score']} ({combined[0]['model']}/{combined[0]['config']})")
    print(f"Break threshold: >75. Random baseline ceiling: ~74 (P99=74.36)")
    breakthrough = combined[0]['score'] > 75
    print(f"BREAKTHROUGH: {breakthrough}")


if __name__ == "__main__":
    main()
