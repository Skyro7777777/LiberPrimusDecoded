#!/usr/bin/env python3
"""
aldegonde_quagmire_test.py — Quick test of aldegonde's Quagmire III + autokey
============================================================================
Tests 8 Cicada keyword candidates as Quagmire III keyed-tableau autokeys
(ciphertext-feedback) on first 500 runes of the unsolved corpus.
"""
import sys, os, json, math, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "solvers", "aldegonde", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from aldegonde import pasc, auto, c3301
from aldegonde.stats import ioc
from gematria_primus import (
    RUNES, RUNE_TO_DEC, DEC_TO_RUNE, DEC_TO_LETTER, N_RUNES, MOD,
    runes_to_decimals, decimals_to_runes, runes_to_latin, clean_runes,
)

# Load quadgrams (same scoring)
ALDE = os.path.join(os.path.dirname(__file__), "..", "solvers", "aldegonde", "src", "aldegonde", "data", "ngrams", "runeglish")
def load_ngrams(path):
    g = {}
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2: g[parts[0]] = int(parts[1])
    return g
QUADGRAMS = load_ngrams(os.path.join(ALDE, "quadgrams.txt"))
total_quad = sum(QUADGRAMS.values()) if QUADGRAMS else 1
LOG_QUAD = {k: math.log(v/total_quad) for k, v in QUADGRAMS.items()}
FLOOR_QUAD = math.log(0.01/total_quad)
def qscore(rune_str):
    if len(rune_str) < 4: return FLOOR_QUAD * max(1, len(rune_str))
    s = 0.0
    for i in range(len(rune_str)-3):
        s += LOG_QUAD.get(rune_str[i:i+4], FLOOR_QUAD)
    return s

# Test keywords (Cicada-significant)
KEYWORDS = [
    "DIVINITY", "FIRFUMFERENFE", "PRIMUS", "INSTAR", "EMERGENCE",
    "PILGRIMAGE", "SACRED", "PRIMES", "FORGIVENESS", "INTENTIONAL",
    "PARABLE", "WISDOM",
]

# Load unsolved corpus
with open(os.path.join(os.path.dirname(__file__), "unsolved_pages.json")) as f:
    uns = json.load(f)
corpus = clean_runes("".join(p["runes"] for p in uns))[:500]
ct_sym = [c3301.CICADA_ALPHABET[r] if False else r for r in corpus]  # just use rune strings

# Actually use runes as the symbols; aldegonde's tr works on any hashable.
# Build Quagmire III tr from a keyword (as a keyed alphabet).
LETTER_TO_DEC = {l: i for i, l in enumerate(DEC_TO_LETTER.values()) if l is not None}
def keyword_to_keyed_alpha(keyword):
    """Dedup keyword + remaining runes in canonical order.
    Keyword may be Latin letters (e.g. "DIVINITY") or runes."""
    seen = set(); alpha = []
    for ch in keyword:
        # Convert Latin letter -> rune
        if ch in RUNES:
            r = ch
        elif ch.upper() in LETTER_TO_DEC:
            r = DEC_TO_RUNE[LETTER_TO_DEC[ch.upper()]]
        else:
            continue
        if r not in seen:
            seen.add(r); alpha.append(r)
    for r in RUNES:
        if r not in seen:
            alpha.append(r)
    return alpha

# Load solved plaintexts as keyword sources too
print("="*70)
print("ALDEGONDE QUAGMIRE III + CIPHERTEXT AUTOKEY")
print("="*70)
print(f"Sample: {len(corpus)} runes")
results = []
for kw in KEYWORDS:
    keyed_alpha = keyword_to_keyed_alpha(kw)
    tr = pasc.quagmire3_tr(keyed_alpha)
    best_score = -1e18; best_primer = None; best_pt = None
    for primer in keyed_alpha:  # try every rune as primer
        try:
            pt = list(auto.ciphertext_autokey_decrypt(corpus, [primer], tr))
            pt_str = "".join(pt)
            s = qscore(pt_str)
            if s > best_score:
                best_score = s; best_primer = primer; best_pt = pt_str
        except Exception as e:
            pass
    pt_lat = runes_to_latin(best_pt) if best_pt else ""
    print(f"  kw={kw:18s} primer={best_primer} score={best_score:8.1f}  {pt_lat[:80]}")
    results.append({
        "keyword": kw, "primer": best_primer, "score": best_score,
        "plaintext_latin": pt_lat,
    })

# Also test beaufort_tr, quagmire4_tr, variantbeaufort_tr
print("\n--- Testing other tableau types with best keyword DIVINITY ---")
kw = "DIVINITY"
keyed_alpha = keyword_to_keyed_alpha(kw)
for tr_name, tr_fn in [
    ("vigenere_tr", pasc.vigenere_tr),
    ("beaufort_tr", pasc.beaufort_tr),
    ("variantbeaufort_tr", pasc.variantbeaufort_tr),
    ("quagmire1_tr", pasc.quagmire1_tr),
    ("quagmire2_tr", pasc.quagmire2_tr),
    ("quagmire3_tr", pasc.quagmire3_tr),
    ("quagmire4_tr", pasc.quagmire4_tr),
]:
    try:
        tr = tr_fn(keyed_alpha)
        best_score = -1e18; best_primer = None; best_pt = None
        for primer in keyed_alpha:
            try:
                pt = list(auto.ciphertext_autokey_decrypt(corpus, [primer], tr))
                pt_str = "".join(pt)
                s = qscore(pt_str)
                if s > best_score:
                    best_score = s; best_primer = primer; best_pt = pt_str
            except Exception:
                pass
        pt_lat = runes_to_latin(best_pt) if best_pt else ""
        print(f"  {tr_name:24s} primer={best_primer} score={best_score:8.1f}  {pt_lat[:80]}")
        results.append({
            "keyword": kw, "tableau": tr_name, "primer": best_primer,
            "score": best_score, "plaintext_latin": pt_lat,
        })
    except Exception as e:
        print(f"  {tr_name}: ERROR {e}")

# Also try plaintext_autokey_decrypt with each keyword
print("\n--- Plaintext autokey (P-feedback) with various keywords ---")
for kw in ["DIVINITY", "FIRFUMFERENFE", "PRIMUS", "INSTAR"]:
    keyed_alpha = keyword_to_keyed_alpha(kw)
    tr = pasc.quagmire3_tr(keyed_alpha)
    best_score = -1e18; best_primer = None; best_pt = None
    for primer in keyed_alpha:
        try:
            pt = list(auto.plaintext_autokey_decrypt(corpus, [primer], tr))
            pt_str = "".join(pt)
            s = qscore(pt_str)
            if s > best_score:
                best_score = s; best_primer = primer; best_pt = pt_str
        except Exception:
            pass
    pt_lat = runes_to_latin(best_pt) if best_pt else ""
    print(f"  kw={kw:18s} primer={best_primer} score={best_score:8.1f}  {pt_lat[:80]}")
    results.append({
        "keyword": kw, "mode": "plaintext_autokey", "primer": best_primer,
        "score": best_score, "plaintext_latin": pt_lat,
    })

# Save
with open(os.path.join(os.path.dirname(__file__), "aldegonde_quagmire_results.json"), "w") as f:
    json.dump({"sample_length": len(corpus), "results": results}, f, indent=2, ensure_ascii=False)
print("\nSaved aldegonde_quagmire_results.json")
