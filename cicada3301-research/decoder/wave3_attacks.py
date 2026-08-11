#!/usr/bin/env python3
"""
wave3_attacks.py — Wave-3 layered cipher attacks on the 56 unsolved LP2 pages.

Implements 7 attacks:
  Attack 1: Atbash-then-autokey (21 keys x 2 modes = 42 tests)
  Attack 2: Autokey-then-Atbash (reverse layer order) (21 x 2 = 42 tests)
  Attack 3: Caesar-shift-then-autokey (28 shifts x 2 keys x 2 modes = 112 tests, top 10)
  Attack 4: Autokey with F-skip discovery (6 F-rune positions in first 95 runes,
            C(6,0)+C(6,1)+C(6,2)+C(6,3)=42 configs per mode per key, top 10)
  Attack 5: Cipher-direction reversal (4 keys x 2 modes = 8 tests)
  Attack 6: Vigenere (pure, no autokey) with F-skip brute-force (42 configs x 1 key, top 10)
  Attack 7: Per-chapter layered attack (9 chapters x 2 keys = 18 tests)

Imports from gematria_primus.py.
"""
from __future__ import annotations
import json
import itertools
from typing import List, Dict, Optional, Set

from gematria_primus import (
    RUNES, LETTERS, DECIMALS, MOD, N_RUNES,
    RUNE_TO_DEC, DEC_TO_RUNE, F_RUNE,
    is_rune, rune_to_dec, dec_to_rune, dec_to_letter,
    clean_runes, runes_to_decimals, decimals_to_runes, runes_to_latin,
    atbash, caesar, vigenere, autokey_vigenere, english_score,
    KEY_CANDIDATES,
)

DECODER_DIR = "/home/z/my-project/cicada3301-research/decoder"
COMPILED_DIR = "/home/z/my-project/cicada3301-research/compiled"


# ============================================================================
# HELPERS — F-skip-enabled autokey
# ============================================================================

def autokey_vigenere_fskip(
    ciphertext_runes: str,
    primer_runes: str,
    mode: str = "plaintext",
    decrypt: bool = True,
    skip_indices: Optional[Set[int]] = None,
) -> str:
    """
    Autokey Vigenere with F-skip rule.
    - skip_indices: positions (0-indexed over the runes-only stream) where the rune
      is left unchanged and the keystream does NOT advance.
    - For plaintext mode: feedback stream = the decrypted plaintext from non-skip
      positions.
    - For ciphertext mode: feedback stream = the ciphertext from non-skip positions
      (which is just the non-skip ciphertext runes in order).
    """
    if skip_indices is None:
        skip_indices = set()
    primer_decs = runes_to_decimals(primer_runes)
    L = len(primer_decs)
    cipher_decs = runes_to_decimals(ciphertext_runes)

    out_decs: List[int] = []
    feedback_decs: List[int] = []   # feedback stream (non-skip positions only)
    ki = 0  # keystream position counter (only advances on non-skip positions)
    for i, cd in enumerate(cipher_decs):
        if i in skip_indices:
            # Leave unchanged, don't advance key, don't add to feedback
            out_decs.append(cd)
            continue
        # Compute key value at this position
        if ki < L:
            kd = primer_decs[ki]
        else:
            if mode == "plaintext":
                kd = feedback_decs[ki - L]   # = plaintext from (ki-L)-th non-skip position
            elif mode == "ciphertext":
                kd = feedback_decs[ki - L]   # = ciphertext from (ki-L)-th non-skip position
            else:
                raise ValueError(f"unknown mode {mode!r}")
        if decrypt:
            pd = (cd - kd) % MOD
        else:
            pd = (cd + kd) % MOD
        out_decs.append(pd)
        # Update feedback: for plaintext mode, feedback is the decrypted plaintext;
        # for ciphertext mode, feedback is the ciphertext rune.
        if mode == "plaintext":
            feedback_decs.append(pd)
        else:
            feedback_decs.append(cd)
        ki += 1
    return decimals_to_runes(out_decs)


def autokey_vigenere_reversed(
    ciphertext_runes: str,
    primer_runes: str,
    mode: str = "plaintext",
) -> str:
    """
    Cipher-direction reversal: plaintext[i] = (key[i] - cipher[i]) mod 29
    instead of standard (cipher[i] - key[i]) mod 29.
    Tests whether Cicada encrypted with the inverse convention.
    """
    primer_decs = runes_to_decimals(primer_runes)
    L = len(primer_decs)
    cipher_decs = runes_to_decimals(ciphertext_runes)
    out_decs: List[int] = []
    for i, cd in enumerate(cipher_decs):
        if i < L:
            kd = primer_decs[i]
        else:
            if mode == "plaintext":
                kd = out_decs[i - L]
            elif mode == "ciphertext":
                kd = cipher_decs[i - L]
            else:
                raise ValueError(f"unknown mode {mode!r}")
        pd = (kd - cd) % MOD
        out_decs.append(pd)
    return decimals_to_runes(out_decs)


def atbash_then_autokey(ciphertext_runes: str, primer_runes: str, mode: str) -> str:
    """Attack 1: atbash(ciphertext) then autokey_vigenere."""
    step1 = atbash(ciphertext_runes)
    step2 = autokey_vigenere(step1, primer_runes, mode=mode, decrypt=True)
    return step2


def autokey_then_atbash(ciphertext_runes: str, primer_runes: str, mode: str) -> str:
    """Attack 2: autokey_vigenere(ciphertext) then atbash."""
    step1 = autokey_vigenere(ciphertext_runes, primer_runes, mode=mode, decrypt=True)
    step2 = atbash(step1)
    return step2


def caesar_then_autokey(ciphertext_runes: str, shift: int, primer_runes: str, mode: str) -> str:
    """Attack 3: caesar(ciphertext, shift) then autokey_vigenere."""
    step1 = caesar(ciphertext_runes, shift, decrypt=True)
    step2 = autokey_vigenere(step1, primer_runes, mode=mode, decrypt=True)
    return step2


# ============================================================================
# LOAD DATA
# ============================================================================

def load_unsolved_corpus() -> str:
    """Load and concatenate all unsolved-page runes."""
    with open(f"{DECODER_DIR}/unsolved_pages.json") as f:
        pages = json.load(f)
    return "".join(p["runes"] for p in pages)


def load_unsolved_pages() -> List[Dict]:
    """Return list of unsolved page-group entries."""
    with open(f"{DECODER_DIR}/unsolved_pages.json") as f:
        return json.load(f)


def load_parable_text() -> str:
    """Load the full 95-rune parable text (page 74.jpg / LP2 page 57)."""
    with open(f"{DECODER_DIR}/solved_pages.json") as f:
        pages = json.load(f)
    for p in pages:
        if p["page_id"] == "74.jpg":
            return p["runes"]
    raise RuntimeError("parable (74.jpg) not found in solved_pages.json")


# ============================================================================
# CHAPTER MAPPING (CicadaSolvers groupings)
# ============================================================================

# Map CicadaSolvers chapter names to indices in unsolved_pages.json list.
# Based on the headers in unsolved_pages.json (LP2 page ranges).
# Indices are 0-based positions in the unsolved_pages.json list.
CHAPTER_MAP = [
    # (chapter_name, [list_indices_into_unsolved_pages_list])
    ("Cross 0-2",        [0]),            # 17.jpg-19.jpg
    ("Spirals 3-7",      [1, 2]),         # 20.jpg + 23.jpg-24.jpg
    ("Branches 8-14",    [3]),            # 25.jpg-31.jpg
    ("Mobius 15-22",     [5]),            # 32.jpg-39.jpg (skip entry 4 = title only)
    ("Mayfly 23-26",     [6]),            # 40.jpg-43.jpg
    ("Wing-Tree 27-32",  [7]),            # 44.jpg-49.jpg
    ("Cuneiform 33-39",  [9]),            # 50.jpg-56.jpg (skip entry 8 = title only)
    ("Spiral-Branch 40-53", [11]),       # 57.jpg (3008 runes)
    ("Hollow 54-55",     [12]),           # 71.jpg (54.jpg)
]


def get_chapter_text(pages: List[Dict], chapter_indices: List[int], n: int = 200) -> str:
    """Get first n runes from a chapter's concatenated text."""
    runes = "".join(pages[i]["runes"] for i in chapter_indices)
    return runes[:n]


# ============================================================================
# ATTACK 1 — Atbash-then-autokey (21 keys x 2 modes = 42 tests)
# ============================================================================

def attack1_atbash_then_autokey(corpus: str, parable: str) -> List[Dict]:
    print("\n" + "=" * 70)
    print("ATTACK 1 — Atbash-then-autokey (21 keys x 2 modes = 42 tests)")
    print("=" * 70)
    # 21 keys = 20 KEY_CANDIDATES + parable
    keys = list(KEY_CANDIDATES.items()) + [("PARABLE_TEXT", parable)]
    test_window = corpus[:300]
    results = []
    for key_name, key_runes in keys:
        for mode in ["plaintext", "ciphertext"]:
            try:
                pt_runes = atbash_then_autokey(test_window, key_runes, mode)
                pt_latin = runes_to_latin(pt_runes)
                score = english_score(pt_latin)
                results.append({
                    "key": key_name,
                    "mode": mode,
                    "score": round(score, 4),
                    "plaintext": pt_latin[:120],
                })
            except Exception as e:
                results.append({"key": key_name, "mode": mode, "score": -1, "error": str(e)})
    results.sort(key=lambda r: -r["score"])
    print(f"Top 5 (out of {len(results)}):")
    for r in results[:5]:
        print(f"  {r['score']:7.3f}  {r['key']:24s}  {r['mode']:10s}  {r['plaintext'][:60]}")
    return results


# ============================================================================
# ATTACK 2 — Autokey-then-Atbash (reverse layer order) (21 x 2 = 42 tests)
# ============================================================================

def attack2_autokey_then_atbash(corpus: str, parable: str) -> List[Dict]:
    print("\n" + "=" * 70)
    print("ATTACK 2 — Autokey-then-Atbash (21 keys x 2 modes = 42 tests)")
    print("=" * 70)
    keys = list(KEY_CANDIDATES.items()) + [("PARABLE_TEXT", parable)]
    test_window = corpus[:300]
    results = []
    for key_name, key_runes in keys:
        for mode in ["plaintext", "ciphertext"]:
            try:
                pt_runes = autokey_then_atbash(test_window, key_runes, mode)
                pt_latin = runes_to_latin(pt_runes)
                score = english_score(pt_latin)
                results.append({
                    "key": key_name,
                    "mode": mode,
                    "score": round(score, 4),
                    "plaintext": pt_latin[:120],
                })
            except Exception as e:
                results.append({"key": key_name, "mode": mode, "score": -1, "error": str(e)})
    results.sort(key=lambda r: -r["score"])
    print(f"Top 5 (out of {len(results)}):")
    for r in results[:5]:
        print(f"  {r['score']:7.3f}  {r['key']:24s}  {r['mode']:10s}  {r['plaintext'][:60]}")
    return results


# ============================================================================
# ATTACK 3 — Caesar-shift-then-autokey (28 x 2 x 2 = 112 tests)
# ============================================================================

def attack3_caesar_then_autokey(corpus: str, parable: str) -> List[Dict]:
    print("\n" + "=" * 70)
    print("ATTACK 3 — Caesar-shift-then-autokey (28 shifts x 2 keys x 2 modes = 112 tests)")
    print("=" * 70)
    keys = [("DIVINITY", KEY_CANDIDATES["DIVINITY"]), ("PARABLE_TEXT", parable)]
    test_window = corpus[:300]
    results = []
    for shift in range(1, 29):
        for key_name, key_runes in keys:
            for mode in ["plaintext", "ciphertext"]:
                try:
                    pt_runes = caesar_then_autokey(test_window, shift, key_runes, mode)
                    pt_latin = runes_to_latin(pt_runes)
                    score = english_score(pt_latin)
                    results.append({
                        "shift": shift,
                        "key": key_name,
                        "mode": mode,
                        "score": round(score, 4),
                        "plaintext": pt_latin[:120],
                    })
                except Exception as e:
                    results.append({"shift": shift, "key": key_name, "mode": mode,
                                    "score": -1, "error": str(e)})
    results.sort(key=lambda r: -r["score"])
    print(f"Top 10 (out of {len(results)}):")
    for r in results[:10]:
        print(f"  {r['score']:7.3f}  shift={r['shift']:2d}  {r['key']:14s}  {r['mode']:10s}  {r['plaintext'][:50]}")
    return results


# ============================================================================
# ATTACK 4 — Autokey with F-skip discovery
# ============================================================================

def attack4_autokey_fskip(corpus: str, parable: str) -> List[Dict]:
    print("\n" + "=" * 70)
    print("ATTACK 4 — Autokey with F-skip discovery (DIVINITY + PARABLE)")
    print("=" * 70)
    test_window = corpus[:95]
    # Identify F-rune positions
    f_positions = [i for i, r in enumerate(test_window) if r == F_RUNE]
    print(f"F-rune positions in first 95 runes: {f_positions} ({len(f_positions)} positions)")
    n_f = len(f_positions)
    # Enumerate combinations of 0, 1, 2, 3 of the F positions
    skip_configs: List[frozenset] = []
    for k in range(4):  # 0, 1, 2, 3
        for combo in itertools.combinations(f_positions, k):
            skip_configs.append(frozenset(combo))
    print(f"Total skip-configs: {len(skip_configs)} (1 + {n_f} + C({n_f},2) + C({n_f},3) = "
          f"1 + {n_f} + {len(list(itertools.combinations(f_positions, 2)))} + "
          f"{len(list(itertools.combinations(f_positions, 3)))})")
    keys = [("DIVINITY", KEY_CANDIDATES["DIVINITY"]), ("PARABLE_TEXT", parable)]
    results = []
    for key_name, key_runes in keys:
        for mode in ["plaintext", "ciphertext"]:
            for skip_set in skip_configs:
                try:
                    pt_runes = autokey_vigenere_fskip(
                        test_window, key_runes, mode=mode, decrypt=True,
                        skip_indices=set(skip_set)
                    )
                    pt_latin = runes_to_latin(pt_runes)
                    score = english_score(pt_latin)
                    results.append({
                        "key": key_name,
                        "mode": mode,
                        "skip_indices": sorted(skip_set),
                        "score": round(score, 4),
                        "plaintext": pt_latin[:95],
                    })
                except Exception as e:
                    results.append({"key": key_name, "mode": mode,
                                    "skip_indices": sorted(skip_set),
                                    "score": -1, "error": str(e)})
    results.sort(key=lambda r: -r["score"])
    print(f"Top 10 (out of {len(results)}):")
    for r in results[:10]:
        print(f"  {r['score']:7.3f}  {r['key']:14s}  {r['mode']:10s}  skip={r['skip_indices']}  "
              f"{r['plaintext'][:50]}")
    return results


# ============================================================================
# ATTACK 5 — Cipher-direction reversal (4 keys x 2 modes = 8 tests)
# ============================================================================

def attack5_cipher_reversal(corpus: str, parable: str) -> List[Dict]:
    print("\n" + "=" * 70)
    print("ATTACK 5 — Cipher-direction reversal (4 keys x 2 modes = 8 tests)")
    print("=" * 70)
    keys = [
        ("DIVINITY",       KEY_CANDIDATES["DIVINITY"]),
        ("FIRFUMFERENFE",  KEY_CANDIDATES["FIRFUMFERENFE"]),
        ("PARABLE_TEXT",   parable),
        ("TOTIENT",        KEY_CANDIDATES["TOTIENT"]),
    ]
    test_window = corpus[:300]
    results = []
    for key_name, key_runes in keys:
        for mode in ["plaintext", "ciphertext"]:
            try:
                pt_runes = autokey_vigenere_reversed(test_window, key_runes, mode=mode)
                pt_latin = runes_to_latin(pt_runes)
                score = english_score(pt_latin)
                results.append({
                    "key": key_name,
                    "mode": mode,
                    "score": round(score, 4),
                    "plaintext": pt_latin[:120],
                })
            except Exception as e:
                results.append({"key": key_name, "mode": mode, "score": -1, "error": str(e)})
    results.sort(key=lambda r: -r["score"])
    print("All 8 results:")
    for r in results:
        print(f"  {r['score']:7.3f}  {r['key']:14s}  {r['mode']:10s}  {r['plaintext'][:60]}")
    return results


# ============================================================================
# ATTACK 6 — Vigenère (pure, no autokey) with F-skip brute-force
# ============================================================================

def attack6_vigenere_fskip(corpus: str) -> List[Dict]:
    print("\n" + "=" * 70)
    print("ATTACK 6 — Pure Vigenere with F-skip brute-force (DIVINITY, 42 configs)")
    print("=" * 70)
    test_window = corpus[:95]
    f_positions = [i for i, r in enumerate(test_window) if r == F_RUNE]
    print(f"F-rune positions in first 95 runes: {f_positions} ({len(f_positions)} positions)")
    skip_configs: List[frozenset] = []
    for k in range(4):
        for combo in itertools.combinations(f_positions, k):
            skip_configs.append(frozenset(combo))
    print(f"Total skip-configs: {len(skip_configs)}")
    key_runes = KEY_CANDIDATES["DIVINITY"]
    results = []
    for skip_set in skip_configs:
        try:
            # Pure Vigenere with F-skip rule
            pt_runes = vigenere(test_window, key_runes, skip_indices=set(skip_set),
                                decrypt=True, f_skip_rule=True)
            pt_latin = runes_to_latin(pt_runes)
            score = english_score(pt_latin)
            results.append({
                "key": "DIVINITY",
                "skip_indices": sorted(skip_set),
                "score": round(score, 4),
                "plaintext": pt_latin[:95],
            })
        except Exception as e:
            results.append({"key": "DIVINITY", "skip_indices": sorted(skip_set),
                            "score": -1, "error": str(e)})
    results.sort(key=lambda r: -r["score"])
    print(f"Top 10 (out of {len(results)}):")
    for r in results[:10]:
        print(f"  {r['score']:7.3f}  skip={r['skip_indices']}  {r['plaintext'][:60]}")
    return results


# ============================================================================
# ATTACK 7 — Per-chapter layered attack (9 chapters x 2 keys = 18 tests)
# ============================================================================

def attack7_per_chapter(pages: List[Dict], parable: str) -> List[Dict]:
    print("\n" + "=" * 70)
    print("ATTACK 7 — Per-chapter layered: Atbash+autokey(DIVINITY or PARABLE, plaintext mode)")
    print("=" * 70)
    keys = [
        ("DIVINITY", KEY_CANDIDATES["DIVINITY"]),
        ("PARABLE_TEXT", parable),
    ]
    results = []
    for chapter_name, chapter_indices in CHAPTER_MAP:
        try:
            chapter_text = get_chapter_text(pages, chapter_indices, n=200)
        except IndexError as e:
            print(f"  [SKIP] {chapter_name}: index out of range ({e})")
            continue
        for key_name, key_runes in keys:
            try:
                # Atbash + autokey(plaintext mode) — best wave-1+wave-3 combination
                pt_runes = atbash_then_autokey(chapter_text, key_runes, "plaintext")
                pt_latin = runes_to_latin(pt_runes)
                score = english_score(pt_latin)
                results.append({
                    "chapter": chapter_name,
                    "key": key_name,
                    "score": round(score, 4),
                    "plaintext": pt_latin[:120],
                    "n_runes_tested": len(chapter_text),
                })
            except Exception as e:
                results.append({"chapter": chapter_name, "key": key_name,
                                "score": -1, "error": str(e)})
    results.sort(key=lambda r: -r["score"])
    print(f"All {len(results)} results (sorted):")
    for r in results:
        print(f"  {r['score']:7.3f}  {r['chapter']:22s}  {r['key']:14s}  {r.get('plaintext','')[:50]}")
    return results


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("WAVE-3 LAYERED CIPHER ATTACKS — Cicada 3301 Liber Primus")
    print("=" * 70)
    corpus = load_unsolved_corpus()
    parable = load_parable_text()
    pages = load_unsolved_pages()
    print(f"Unsolved corpus: {len(corpus)} runes (across {len(pages)} page-groups)")
    print(f"Parable text: {len(parable)} runes (page 74.jpg / LP2 page 57)")
    print(f"First 30 runes of unsolved corpus: {corpus[:30]}")

    all_results = {}

    # Attack 1
    all_results["attack1_atbash_then_autokey"] = attack1_atbash_then_autokey(corpus, parable)

    # Attack 2
    all_results["attack2_autokey_then_atbash"] = attack2_autokey_then_atbash(corpus, parable)

    # Attack 3
    all_results["attack3_caesar_then_autokey"] = attack3_caesar_then_autokey(corpus, parable)

    # Attack 4
    all_results["attack4_autokey_fskip"] = attack4_autokey_fskip(corpus, parable)

    # Attack 5
    all_results["attack5_cipher_reversal"] = attack5_cipher_reversal(corpus, parable)

    # Attack 6
    all_results["attack6_vigenere_fskip"] = attack6_vigenere_fskip(corpus)

    # Attack 7
    all_results["attack7_per_chapter"] = attack7_per_chapter(pages, parable)

    # Save consolidated JSON
    out_path = f"{DECODER_DIR}/wave3_attack_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n[Saved] {out_path}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY — Top score per attack:")
    print("=" * 70)
    for name, results in all_results.items():
        if results:
            top = max(results, key=lambda r: r.get("score", -1))
            print(f"  {name:38s}  top_score={top.get('score', -1):.3f}")

    # Overall top 3
    all_flat = []
    for name, results in all_results.items():
        for r in results:
            r2 = dict(r)
            r2["attack"] = name
            all_flat.append(r2)
    all_flat.sort(key=lambda r: -r.get("score", -1))
    print("\nOverall top 3 (across ALL wave-3 attacks):")
    for r in all_flat[:3]:
        print(f"  {r.get('score', -1):7.3f}  [{r['attack']}]  {r.get('key','')}  {r.get('mode','')}  "
              f"{r.get('plaintext','')[:60]}")

    return all_results


if __name__ == "__main__":
    main()
