#!/usr/bin/env python3
"""
wave2_attacks.py — Wave-2 attacks on Cicada 3301 Liber Primus unsolved pages
==================================================================================
Task ID: p2c — Wave-2 parable-primer attack subagent

Implements 5 attacks:
  1. Full parable text as autokey primer (4 variants × 2 modes = 8 tests)
  2. Long-text primers from solved LP pages
  3. Numeric primers (1033, 761, 11570, parable-product, P.S. 154-digit, onion cookies, missing primes)
  4. Playfair digraphic cipher (Hypothesis 10)
  5. Kasiski deeper analysis (n-grams 4-8, GCD of repetition distances)

Imports from gematria_primus.py.
"""
from __future__ import annotations
import json, sys, os
from collections import Counter
from math import gcd
from functools import reduce
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, DEC_TO_PRIME,
    PRIMES, LETTERS, N_RUNES, MOD,
    rune_to_dec, dec_to_rune, dec_to_letter,
    clean_runes, runes_to_decimals, decimals_to_runes, decimals_to_latin, runes_to_latin,
    atbash, caesar, vigenere, autokey_vigenere, prime_stream, prime_fib_mesh,
    frequency_analysis, kasiski_examination, english_score, KEY_CANDIDATES,
)

# ============================================================================
# LOAD DATA
# ============================================================================
DECODER_DIR = os.path.dirname(os.path.abspath(__file__))
UNSOLVED = json.load(open(os.path.join(DECODER_DIR, "unsolved_pages.json")))
SOLVED = json.load(open(os.path.join(DECODER_DIR, "solved_pages.json")))

# Concatenate all unsolved pages into one corpus
UNSOLVED_CORPUS = "".join(p["runes"] for p in UNSOLVED)
N_UNSOLVED = len(UNSOLVED_CORPUS)
print(f"[wave2] Loaded {len(UNSOLVED)} unsolved pages, {N_UNSOLVED} total runes")

# Parable (page 74.jpg / LP2 page 57)
PARABLE = "ᛈᚪᚱᚪᛒᛚᛖᛚᛁᚳᛖᚦᛖᛁᚾᛋᛏᚪᚱᛏᚢᚾᚾᛖᛚᛝᛏᚩᚦᛖᛋᚢᚱᚠᚪᚳᛖᚹᛖᛗᚢᛋᛏᛋᚻᛖᛞᚩᚢᚱᚩᚹᚾᚳᛁᚱᚳᚢᛗᚠᛖᚱᛖᚾᚳᛖᛋᚠᛁᚾᛞᚦᛖᛞᛁᚢᛁᚾᛁᛏᛖᚹᛁᚦᛁᚾᚪᚾᛞᛖᛗᛖᚱᚷᛖ"
assert all(c in RUNES for c in PARABLE)
assert len(PARABLE) == 95
print(f"[wave2] Parable: {len(PARABLE)} runes -> '{runes_to_latin(PARABLE)}'")

# ----------------------------------------------------------------------------
# Helper: atbash-transform a rune string
def atbash_runes(runes: str) -> str:
    return "".join(dec_to_rune(MOD - 1 - rune_to_dec(r)) for r in runes)

# ----------------------------------------------------------------------------
# Helper: gematria-prime-values mod 29 -> rune
def prime_values_mod29(runes: str) -> str:
    """Each rune -> its prime value -> mod 29 -> rune index."""
    out = []
    for r in runes:
        p = DEC_TO_PRIME[rune_to_dec(r)]
        out.append(dec_to_rune(p % MOD))
    return "".join(out)

# ----------------------------------------------------------------------------
# Helper: decimal-digit sequence to runes (each digit -> rune at that decimal index)
def decimal_digits_to_runes(digit_str: str) -> str:
    return "".join(dec_to_rune(int(d) % MOD) for d in digit_str if d.isdigit())

# ----------------------------------------------------------------------------
# Helper: hex-string to runes (each hex pair -> decimal mod 29 -> rune)
def hex_to_runes(hex_str: str) -> str:
    cleaned = "".join(c for c in hex_str if c in "0123456789abcdefABCDEF")
    out = []
    for i in range(0, len(cleaned) - 1, 2):
        v = int(cleaned[i:i+2], 16)
        out.append(dec_to_rune(v % MOD))
    return "".join(out)

# ----------------------------------------------------------------------------
# Helper: primes-list to runes (each prime -> mod 29 -> rune)
def primes_to_runes(prime_list) -> str:
    return "".join(dec_to_rune(p % MOD) for p in prime_list)

# ----------------------------------------------------------------------------
# Score a candidate plaintext and produce a snippet
def score_and_snippet(plaintext_runes: str, max_chars: int = 100) -> tuple:
    pt_latin = runes_to_latin(plaintext_runes)
    score = english_score(pt_latin)
    snippet = pt_latin[:max_chars]
    return score, snippet

# ============================================================================
# ATTACK 1: PARABLE-AS-AUTOKEY PRIMER (8 tests)
# ============================================================================
def attack1_parable():
    print("\n" + "=" * 70)
    print("ATTACK 1: Parable as autokey primer (4 variants × 2 modes = 8)")
    print("=" * 70)
    ct = UNSOLVED_CORPUS[:500]  # first 500 runes
    # Build 4 variants of primer
    variants = {
        "forward":          PARABLE,
        "reversed":         PARABLE[::-1],
        "atbash":           atbash_runes(PARABLE),
        "prime_mod29":      prime_values_mod29(PARABLE),
    }
    results = []
    for vname, primer in variants.items():
        # Sanity check: all chars runes
        assert all(c in RUNES for c in primer), f"variant {vname} has non-rune chars"
        for mode in ("plaintext", "ciphertext"):
            pt_runes = autokey_vigenere(ct, primer, mode=mode, decrypt=True)
            score, snippet = score_and_snippet(pt_runes)
            results.append({
                "variant": vname,
                "mode": mode,
                "primer_len": len(primer),
                "primer_latin": runes_to_latin(primer)[:60],
                "score": round(score, 3),
                "snippet": snippet,
            })
            flag = " <<< HIGH" if score > 80 else ""
            print(f"  {vname:14s} {mode:9s}  score={score:7.3f}{flag}  -> {snippet[:60]}")
    return results


# ============================================================================
# ATTACK 2: LONG-TEXT PRIMERS FROM SOLVED PAGES
# ============================================================================
def attack2_longtext():
    print("\n" + "=" * 70)
    print("ATTACK 2: Long-text primers from solved LP pages")
    print("=" * 70)
    ct = UNSOLVED_CORPUS[:500]
    # Build primer candidates from solved-page texts
    primers = {}
    for sp in SOLVED:
        pid = sp["page_id"]
        if pid == "74.jpg":
            primers[f"parable_74"] = sp["runes"]              # = PARABLE
        elif pid == "03.jpg":
            primers["welcome_03"] = sp["runes"]               # Welcome part 1
        elif pid == "04.jpg":
            primers["welcome_04"] = sp["runes"]               # Welcome part 2
        elif pid == "05.jpg":
            primers["wisdom_05"] = sp["runes"]                # Some Wisdom
        elif pid == "06.jpg":
            primers["koan1_06"] = sp["runes"]                 # Koan 1 main
        elif pid == "10.jpg":
            primers["lossofdiv_10"] = sp["runes"]             # Loss of Divinity
        elif pid == "14.jpg":
            primers["koan2_14"] = sp["runes"]                 # Koan 2 main
        elif pid == "13.jpg":
            primers["wisdom2_13"] = sp["runes"]               # Some Wisdom p2
        elif pid == "16.jpg":
            primers["instr_16"] = sp["runes"]                 # An Instruction

    # "Instar Emergence" — the parable IS the ID3 tag of 761.mp3 per dossier §1.
    # Per wiki, identical text — verify by using PARABLE already in primers under "parable_74".
    # We also add a combined welcome page (03+04) for variety
    primers["welcome_03_04"] = primers["welcome_03"] + primers["welcome_04"]

    results = []
    for name, primer in primers.items():
        for mode in ("plaintext", "ciphertext"):
            pt_runes = autokey_vigenere(ct, primer, mode=mode, decrypt=True)
            score, snippet = score_and_snippet(pt_runes)
            results.append({
                "primer_name": name,
                "mode": mode,
                "primer_len": len(primer),
                "score": round(score, 3),
                "snippet": snippet,
            })
            flag = " <<< HIGH" if score > 80 else ""
            print(f"  {name:22s} {mode:9s}  L={len(primer):4d}  score={score:7.3f}{flag}  -> {snippet[:60]}")
    # Sort by score for reporting
    results.sort(key=lambda r: -r["score"])
    return results


# ============================================================================
# ATTACK 3: NUMERIC PRIMERS
# ============================================================================
def attack3_numeric():
    print("\n" + "=" * 70)
    print("ATTACK 3: Numeric primers from Cicada numerological constants")
    print("=" * 70)
    ct = UNSOLVED_CORPUS[:500]

    # The 154-digit P.S. number from 2012 (from fresh_wiki_possible_hints.txt)
    ps_number_2012 = (
        "1041279065891998535982789873959431895640"
        "442510695567564373922695237268242385295908173"
        "9834390370374475764863415203423499357108713631"
    )
    print(f"  [info] P.S. 2012 number: {len(ps_number_2012)} digits")

    # Onion cookies
    cookie_167 = "6941f707ff39d259ff71657a79cb6b54c184d2f0455810109c1a960860bde0e6"
    cookie_761 = "7bc1e7805ccfa518920f0d94fc4e8f7dbd83287a03b337b89109cd2287befae5"
    cookie_both = cookie_167 + cookie_761

    # Missing primes list (73 to 1223)
    missing_primes = [
        73, 79, 83, 89, 97, 101, 103, 107, 109, 113,
        127, 131, 137, 139, 149, 151, 157, 163, 167, 173,
        179, 181, 191, 193, 197, 199, 211, 223, 227, 229,
        233, 239, 241, 251, 257, 263, 269, 271, 277, 281,
        283, 293, 307, 311, 313, 317, 331, 337, 347, 349,
        353, 359, 367, 373, 379, 383, 389, 397, 401, 409,
        419, 421, 431, 433, 439, 443, 449, 457, 461, 463,
        467, 479, 487, 491, 499, 503, 509, 521, 523, 541,
        547, 557, 563, 569, 571, 577, 587, 593, 599, 601,
        607, 613, 617, 619, 631, 641, 643, 647, 653, 659,
        661, 673, 677, 683, 691, 701, 709, 719, 727, 733,
        739, 743, 751, 757, 761, 769, 773, 787, 797, 809,
        811, 821, 823, 827, 829, 839, 853, 857, 859, 863,
        877, 881, 883, 887, 907, 911, 919, 929, 937, 941,
        947, 953, 967, 971, 977, 983, 991, 997, 1009, 1013,
        1019, 1021, 1031, 1033, 1039, 1049, 1051, 1061, 1063, 1069,
        1087, 1091, 1093, 1097, 1103, 1109, 1117, 1123, 1129, 1151,
        1153, 1163, 1171, 1181, 1187, 1193, 1201, 1213, 1217, 1223,
    ]

    primers = {
        "1033_decimal":   decimal_digits_to_runes("1033"),
        "761_decimal":    decimal_digits_to_runes("761"),
        "11570_decimal":  decimal_digits_to_runes("11570"),
        "prod_1595277641": decimal_digits_to_runes("1595277641"),
        "ps2012_first100":  decimal_digits_to_runes(ps_number_2012[:100]),
        "ps2012_full154":   decimal_digits_to_runes(ps_number_2012),
        "cookie_167":       hex_to_runes(cookie_167),
        "cookie_761":       hex_to_runes(cookie_761),
        "cookie_both":      hex_to_runes(cookie_both),
        "missing_primes_mod29": primes_to_runes(missing_primes),
    }
    # Sanity check
    for k, v in primers.items():
        assert all(c in RUNES for c in v), f"{k} contains non-rune chars: {v!r}"
        print(f"  [info] {k}: len={len(v)} latin={runes_to_latin(v)[:40]}")

    results = []
    for name, primer in primers.items():
        for mode in ("plaintext", "ciphertext"):
            pt_runes = autokey_vigenere(ct, primer, mode=mode, decrypt=True)
            score, snippet = score_and_snippet(pt_runes)
            results.append({
                "primer_name": name,
                "mode": mode,
                "primer_len": len(primer),
                "score": round(score, 3),
                "snippet": snippet,
            })
            flag = " <<< HIGH" if score > 80 else ""
            print(f"  {name:24s} {mode:9s}  L={len(primer):4d}  score={score:7.3f}{flag}  -> {snippet[:60]}")
    results.sort(key=lambda r: -r["score"])
    return results


# ============================================================================
# ATTACK 4: PLAYFAIR DIGRAPHIC CIPHER (HYPOTHESIS 10)
# ============================================================================
def build_playfair_matrix(primer_runes: str, filler: str = "ᛠ"):
    """
    Build a 6×5 (rows=6, cols=5) Playfair matrix seeded by a primer.
    Total cells = 30 (29 runes + 1 filler). Filler doubles for last rune.
    """
    matrix = []
    used = set()
    # Place primer runes first
    for r in primer_runes:
        if r not in used:
            matrix.append(r)
            used.add(r)
    # Then place remaining runes in standard order
    for r in RUNES:
        if r not in used:
            matrix.append(r)
            used.add(r)
    # Append filler if needed (only if matrix length is 29)
    if len(matrix) == 29:
        matrix.append(filler)
    assert len(matrix) == 30, f"matrix len {len(matrix)} != 30"
    # Reshape 6×5
    rows = 6
    cols = 5
    grid = [matrix[r*cols:(r+1)*cols] for r in range(rows)]
    return grid, rows, cols

def find_pos(grid, rows, cols, r):
    for ri in range(rows):
        for ci in range(cols):
            if grid[ri][ci] == r:
                return ri, ci
    raise ValueError(f"rune {r} not in grid")

def playfair_decrypt(ciphertext_runes: str, primer_runes: str) -> str:
    """Playfair decryption on rune pairs (drop non-rune chars first)."""
    grid, rows, cols = build_playfair_matrix(primer_runes)
    # Take pairs
    ct = [c for c in ciphertext_runes if c in RUNES]
    if len(ct) % 2 == 1:
        ct = ct[:-1]  # drop trailing odd rune
    out = []
    for i in range(0, len(ct), 2):
        a, b = ct[i], ct[i+1]
        ra, ca = find_pos(grid, rows, cols, a)
        rb, cb = find_pos(grid, rows, cols, b)
        if ra == rb:
            # same row: shift LEFT (decrypt of right-shift encrypt)
            out.append(grid[ra][(ca - 1) % cols])
            out.append(grid[rb][(cb - 1) % cols])
        elif ca == cb:
            # same col: shift UP
            out.append(grid[(ra - 1) % rows][ca])
            out.append(grid[(rb - 1) % rows][cb])
        else:
            # rectangle swap
            out.append(grid[ra][cb])
            out.append(grid[rb][ca])
    return "".join(out)

def attack4_playfair():
    print("\n" + "=" * 70)
    print("ATTACK 4: Playfair digraphic cipher (Hypothesis 10)")
    print("=" * 70)
    ct = UNSOLVED_CORPUS[:200]  # first 200 runes (100 pairs)
    primers = {
        "DIVINITY":       "ᛞᛁᚢᛁᚾᛁᛏᚣ",
        "FIRFUMFERENFE":  "ᚠᛁᚱᚠᚢᛗᚠᛖᚱᛖᚾᚠᛖ",
        "PARABLE":        PARABLE,
        "1033_AS_RUNES":  KEY_CANDIDATES["1033_AS_RUNES"],
        "INSTAR":         "ᛁᚾᛋᛏᚪᚱ",
        "EMERGENCE":      "ᛖᛗᛖᚱᚷᛖᚾᚳᛖ",
        "WELCOME":        "ᚹᛖᛚᚳᚩᛗᛖ",
        "TOTIENT":        "ᛏᚩᛏᛁᛖᚾᛏ",
        "DJUBEI":         "ᛞᛄᚢᛒᛖᛁ",
    }
    results = []
    for name, primer in primers.items():
        try:
            pt_runes = playfair_decrypt(ct, primer)
            score, snippet = score_and_snippet(pt_runes)
            results.append({
                "primer_name": name,
                "primer_len": len(primer),
                "score": round(score, 3),
                "snippet": snippet,
            })
            flag = " <<< HIGH" if score > 80 else ""
            print(f"  {name:18s}  L={len(primer):3d}  score={score:7.3f}{flag}  -> {snippet[:60]}")
        except Exception as e:
            print(f"  {name:18s}  ERROR: {e}")
    results.sort(key=lambda r: -r["score"])
    return results


# ============================================================================
# ATTACK 5: KASISKI DEEPER ANALYSIS (n=4..8)
# ============================================================================
def attack5_kasiski():
    print("\n" + "=" * 70)
    print("ATTACK 5: Kasiski deeper analysis (n=4..8 on full corpus)")
    print("=" * 70)
    decs = runes_to_decimals(UNSOLVED_CORPUS)
    n = len(decs)
    # Find ALL repeated n-grams for n=4..8
    all_repeats = []
    for ng in range(4, 9):
        gram_positions = {}
        for i in range(n - ng + 1):
            g = tuple(decs[i:i+ng])
            gram_positions.setdefault(g, []).append(i)
        for g, positions in gram_positions.items():
            if len(positions) >= 2:
                dists = [positions[j+1] - positions[j] for j in range(len(positions) - 1)]
                # Compute GCD of all distances
                g_gcd = reduce(gcd, dists)
                all_repeats.append({
                    "n_gram": ng,
                    "gram_runes": "".join(dec_to_rune(x) for x in g),
                    "gram_latin": decimals_to_latin(g),
                    "positions": positions,
                    "distances": dists,
                    "gcd": g_gcd,
                    "n_repeats": len(positions),
                })
        print(f"  n={ng}: {len([r for r in all_repeats if r['n_gram']==ng])} repeated n-grams")

    # Tally GCD values across all repeats
    gcd_tally = Counter()
    for r in all_repeats:
        gcd_tally[r["gcd"]] += 1
    top_gcds = gcd_tally.most_common(15)
    print(f"\n  Top 15 GCD values across all repeated n-grams:")
    for g, c in top_gcds:
        print(f"    GCD={g:6d}  count={c:4d}  factors={_factorize_str(g)}")

    # Test top 5 GCDs as candidate key lengths: Vigenère AND autokey with
    # each of 20 KEY_CANDIDATES + PARABLE truncated/padded to GCD length.
    top5_lengths = [g for g, _ in top_gcds if g > 0][:5]
    print(f"\n  Top 5 candidate key lengths: {top5_lengths}")

    ct_short = UNSOLVED_CORPUS[:500]
    test_keys = {}
    for name, krunes in KEY_CANDIDATES.items():
        test_keys[name] = krunes
    test_keys["PARABLE"] = PARABLE

    # Truncate/pad primer to key length
    def fit_key(krunes, klen):
        if len(krunes) >= klen:
            return krunes[:klen]
        # pad with cyclic repeat
        out = krunes
        while len(out) < klen:
            out += krunes
        return out[:klen]

    keylen_results = []
    for klen in top5_lengths:
        for kname, krunes in test_keys.items():
            fitted = fit_key(krunes, klen)
            # Vigenère (no skip)
            try:
                pt_v = vigenere(ct_short, fitted, skip_indices=set(), decrypt=True)
                score_v, snip_v = score_and_snippet(pt_v)
            except Exception as e:
                score_v, snip_v = -1, f"ERR: {e}"
            # Autokey plaintext mode
            try:
                pt_a = autokey_vigenere(ct_short, fitted, mode="plaintext", decrypt=True)
                score_a, snip_a = score_and_snippet(pt_a)
            except Exception as e:
                score_a, snip_a = -1, f"ERR: {e}"
            # Autokey ciphertext mode
            try:
                pt_c = autokey_vigenere(ct_short, fitted, mode="ciphertext", decrypt=True)
                score_c, snip_c = score_and_snippet(pt_c)
            except Exception as e:
                score_c, snip_c = -1, f"ERR: {e}"
            keylen_results.append({
                "key_len": klen,
                "primer": kname,
                "vigenere_score": round(score_v, 3),
                "autokey_pt_score": round(score_a, 3),
                "autokey_ct_score": round(score_c, 3),
                "best_score": round(max(score_v, score_a, score_c), 3),
                "best_mode": max([("vigenere", score_v), ("autokey_pt", score_a), ("autokey_ct", score_c)], key=lambda x: x[1])[0],
                "snippet": max([snip_v, snip_a, snip_c], key=lambda s: len(s) if s else 0)[:60],
            })

    keylen_results.sort(key=lambda r: -r["best_score"])
    print(f"\n  Top 10 key-length × primer combinations by best score:")
    for r in keylen_results[:10]:
        flag = " <<< HIGH" if r["best_score"] > 80 else ""
        print(f"    klen={r['key_len']:4d} primer={r['primer']:18s} {r['best_mode']:12s} score={r['best_score']:7.3f}{flag}  -> {r['snippet']}")

    return {
        "n_gram_repeats_count": {
            4: sum(1 for r in all_repeats if r["n_gram"]==4),
            5: sum(1 for r in all_repeats if r["n_gram"]==5),
            6: sum(1 for r in all_repeats if r["n_gram"]==6),
            7: sum(1 for r in all_repeats if r["n_gram"]==7),
            8: sum(1 for r in all_repeats if r["n_gram"]==8),
        },
        "top_gcd_values": top_gcds,
        "top5_key_lengths": top5_lengths,
        "top10_combos": keylen_results[:10],
    }

def _factorize_str(n: int) -> str:
    if n <= 0:
        return "n/a"
    f = {}
    d = 2
    orig = n
    while d * d <= n:
        while n % d == 0:
            f[d] = f.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        f[n] = f.get(n, 0) + 1
    return "×".join(f"{p}^{e}" if e > 1 else str(p) for p, e in sorted(f.items())) if f else str(orig)


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("WAVE-2 ATTACKS — Cicada 3301 Liber Primus unsolved pages")
    print("=" * 70)
    a1 = attack1_parable()
    a2 = attack2_longtext()
    a3 = attack3_numeric()
    a4 = attack4_playfair()
    a5 = attack5_kasiski()

    # Save consolidated results
    out = {
        "attack1_parable": a1,
        "attack2_longtext": a2,
        "attack3_numeric": a3,
        "attack4_playfair": a4,
        "attack5_kasiski": a5,
    }
    out_path = os.path.join(DECODER_DIR, "wave2_attack_results.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n[wave2] Saved consolidated results to {out_path}")

    # Print final summary
    print("\n" + "=" * 70)
    print("SUMMARY — Top scores across all attacks")
    print("=" * 70)
    all_results = []
    for r in a1:
        all_results.append(("A1-parable", f"{r['variant']}/{r['mode']}", r["score"], r["snippet"]))
    for r in a2[:10]:
        all_results.append(("A2-longtext", f"{r['primer_name']}/{r['mode']}", r["score"], r["snippet"]))
    for r in a3[:10]:
        all_results.append(("A3-numeric", f"{r['primer_name']}/{r['mode']}", r["score"], r["snippet"]))
    for r in a4[:5]:
        all_results.append(("A4-playfair", f"{r['primer_name']}", r["score"], r["snippet"]))
    for r in a5["top10_combos"][:5]:
        all_results.append(("A5-kasiski", f"klen={r['key_len']}/{r['primer']}/{r['best_mode']}", r["best_score"], r["snippet"]))

    all_results.sort(key=lambda x: -x[2])
    print("\nTop 10 across all attacks:")
    for atk, desc, score, snip in all_results[:10]:
        flag = " <<< HIGH" if score > 80 else ""
        print(f"  {atk:14s} {desc:50s} score={score:7.3f}{flag}")
        print(f"                -> {snip[:80]}")
