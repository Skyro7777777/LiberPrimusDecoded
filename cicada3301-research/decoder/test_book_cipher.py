#!/usr/bin/env python3
"""
test_book_cipher.py
===================
Test the book-cipher hypothesis (dossier §9 hypothesis 2).

For each (codebook, unsolved-page) pair, apply the `book_cipher()` function
from gematria_primus.py to the first 100 runes of the page.  Score the
result with `english_score()` and report the top 5 (codebook, page, score,
plaintext snippet) triples.

Also tests an "expanded" book-cipher variant that indexes both word and
letter by *pairs of runes* taken as base-29 indices, so a longer prefix of
the codebook is reachable.  Both variants are reported.

Outputs:
  - prints a ranked table to stdout
  - writes /home/z/my-project/cicada3301-research/compiled/BOOK_CIPHER_RESULTS.md
"""
from __future__ import annotations
import json, os, sys, itertools
from typing import List, Tuple

# Make the decoder package importable
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gematria_primus as gp  # noqa: E402

RAW_DIR = "/home/z/my-project/cicada3301-research/raw"
COMP_DIR = "/home/z/my-project/cicada3301-research/compiled"

CODEBOOK_FILES = {
    "Liber AL vel Legis":     "codebook_liber_al.txt",
    "Self-Reliance":          "codebook_self_reliance.txt",
    "Agrippa":                "codebook_agrippa.txt",
    "Mabinogion":             "codebook_mabinogion.txt",
    "Instar Emergence":       "codebook_instar_emergence.txt",
}

UNSOLVED_PAGES_PATH = os.path.join(HERE, "unsolved_pages.json")


def load_codebook(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as fp:
        return [line.strip() for line in fp if line.strip()]


def load_unsolved_pages() -> List[dict]:
    with open(UNSOLVED_PAGES_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)


# ---- The dossier / gematria_primus.book_cipher convention ---------------
# Pair-up rule: rune[i] -> word_idx, rune[i+1] -> letter_idx.  Decimals 0-28.
# Word_idx is 0..28 (so only the first 29 words of a codebook are usable).
# Letter_idx is 0..28 (so only the first 29 letters of each word are usable).

def book_cipher_pairs(runes: str, codebook_words: List[str]) -> str:
    """Wraps gp.book_cipher() for clarity.  Returns letters / '?'.  Pairs runes."""
    return gp.book_cipher(runes, codebook_words, decrypt=True)


# ---- An alternative convention: "word-triple" ---------------------------
# Take THREE runes per output: rune[i] -> word_idx_high, rune[i+1] -> word_idx_low,
# rune[i+2] -> letter_idx.  Word index = (r0*29 + r1) reaches 0..840, so far
# more of the codebook is reachable.  This is closer to historical book ciphers
# (Beale / Poe's Gold-Bug use 3-digit groupings).
def book_cipher_triples(runes: str, codebook_words: List[str]) -> str:
    decs = gp.runes_to_decimals(runes)
    out = []
    i = 0
    while i + 2 < len(decs):
        word_idx = decs[i] * gp.MOD + decs[i + 1]
        letter_idx = decs[i + 2]
        if word_idx < len(codebook_words):
            w = codebook_words[word_idx]
            if letter_idx < len(w):
                out.append(w[letter_idx])
            else:
                out.append("?")
        else:
            out.append("?")
        i += 3
    return "".join(out)


# ---- Another convention: "single rune indexes letter of running word" ---
# Pure running-key: rune decimal[i] -> letter index within word[i % N_words].
# Equivalent to letter-picking through the codebook in order.  Produces
# something like the Vigenère output where each rune picks a single letter.
def book_cipher_running(runes: str, codebook_words: List[str]) -> str:
    decs = gp.runes_to_decimals(runes)
    out = []
    for i, d in enumerate(decs):
        w = codebook_words[i % len(codebook_words)] if codebook_words else ""
        if d < len(w):
            out.append(w[d])
        else:
            out.append("?")
    return "".join(out)


def english_score(text: str) -> float:
    return gp.english_score(text)


def slice_first_100_runes(runes: str) -> str:
    return "".join(c for c in runes if gp.is_rune(c))[:100]


def main():
    print("=" * 78)
    print("BOOK CIPHER TEST — dossier §9 hypothesis 2")
    print("=" * 78)

    # ---- Load codebooks ----
    codebooks = {}
    print("\nLoading codebooks:")
    for name, fname in CODEBOOK_FILES.items():
        path = os.path.join(RAW_DIR, fname)
        words = load_codebook(path)
        codebooks[name] = words
        print(f"  {name:24s}  {len(words):>7d} words  (first 5: {words[:5]})")

    # ---- Load unsolved pages ----
    unsolved = load_unsolved_pages()
    print(f"\nLoaded {len(unsolved)} unsolved page entries.")

    # ---- Restrict to pages with at least 100 runes ----
    pages = []
    for p in unsolved:
        r = "".join(c for c in p.get("runes", "") if gp.is_rune(c))
        if len(r) >= 50:  # we will take first 100 if available; else first 50
            pages.append({
                "page_id": p["page_id"],
                "header": p.get("header", "")[:80],
                "runes_first100": r[:100],
                "n_runes": len(r),
            })
    print(f"Pages with >=50 runes: {len(pages)}")
    print()

    # ---- Run all (codebook, page, variant) combinations ----
    variants = [
        ("pairs",    book_cipher_pairs),
        ("triples",  book_cipher_triples),
        ("running",  book_cipher_running),
    ]

    results = []
    for cb_name, cb_words in codebooks.items():
        for page in pages:
            r = page["runes_first100"]
            for vname, vfn in variants:
                try:
                    out = vfn(r, cb_words)
                except Exception as e:
                    out = f"<ERR {e}>"
                score = english_score(out)
                results.append({
                    "codebook": cb_name,
                    "page": page["page_id"],
                    "variant": vname,
                    "score": score,
                    "snippet": out[:80],
                    "n_chars": len(out),
                })

    # ---- Rank ----
    results.sort(key=lambda x: x["score"], reverse=True)

    print("TOP 20 (codebook, page, variant, score, snippet):")
    print("-" * 100)
    for r in results[:20]:
        print(f"  {r['score']:>8.2f}  {r['codebook']:18s}  {r['page']:8s}  {r['variant']:8s}  {r['snippet']!r}")
    print()

    # ---- Top 5 per variant ----
    print("\nTOP 5 PER VARIANT:")
    for vname, _ in variants:
        print(f"\n  === Variant: {vname} ===")
        sub = [r for r in results if r["variant"] == vname][:5]
        for r in sub:
            print(f"    {r['score']:>8.2f}  {r['codebook']:18s}  {r['page']:8s}  {r['snippet']!r}")

    # ---- Top 5 per codebook (pairs variant only — the dossier's convention) ----
    print("\nTOP 5 PER CODEBOOK (pairs variant):")
    for cb_name, _ in CODEBOOK_FILES.items():
        print(f"\n  === Codebook: {cb_name} ===")
        sub = [r for r in results if r["codebook"] == cb_name and r["variant"] == "pairs"][:5]
        for r in sub:
            print(f"    {r['score']:>8.2f}  {r['page']:8s}  {r['snippet']!r}")

    # ---- Save the ranked results to compiled/BOOK_CIPHER_RESULTS.md ----
    os.makedirs(COMP_DIR, exist_ok=True)
    out_path = os.path.join(COMP_DIR, "BOOK_CIPHER_RESULTS.md")
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write("# BOOK CIPHER TEST RESULTS\n")
        fp.write("### Cicada 3301 Liber Primus — dossier §9 hypothesis 2\n")
        fp.write("**Subagent:** Task ID `p2b` — Book-cipher-and-literary-codebook subagent\n\n")
        fp.write("Tested all (codebook × unsolved-page × variant) combinations on the first 100 runes of each page.\n\n")
        fp.write("## Codebooks loaded\n\n")
        fp.write("| Codebook | Word count | Source |\n")
        fp.write("|---|---:|---|\n")
        for name, fname in CODEBOOK_FILES.items():
            fp.write(f"| {name} | {len(codebooks[name])} | `raw/{fname}` |\n")
        fp.write("\n## Variants tested\n\n")
        fp.write("| Variant | Convention |\n")
        fp.write("|---|---|\n")
        fp.write("| `pairs`   | rune[i] -> word_idx (0..28), rune[i+1] -> letter_idx (0..28). **This is the `gematria_primus.book_cipher()` convention.** |\n")
        fp.write("| `triples` | rune[i] -> word_idx_high, rune[i+1] -> word_idx_low (word_idx = r0*29 + r1, 0..840), rune[i+2] -> letter_idx (0..28).  Historical Beale/Poe convention. |\n")
        fp.write("| `running` | rune[i] -> letter_idx (0..28) of `codebook_words[i]` — i.e. letter-picking through the codebook in order, one letter per rune. |\n\n")
        fp.write("## Top 20 overall\n\n")
        fp.write("| Score | Codebook | Page | Variant | Snippet (first 80 chars) |\n")
        fp.write("|---:|---|---|---|---|\n")
        for r in results[:20]:
            snip = r["snippet"].replace("|", "\\|")
            fp.write(f"| {r['score']:.2f} | {r['codebook']} | {r['page']} | {r['variant']} | `{snip}` |\n")
        fp.write("\n## Top 5 per codebook (pairs variant)\n\n")
        for cb_name, _ in CODEBOOK_FILES.items():
            fp.write(f"### {cb_name}\n\n")
            fp.write("| Score | Page | Snippet |\n")
            fp.write("|---:|---|---|\n")
            sub = [r for r in results if r["codebook"] == cb_name and r["variant"] == "pairs"][:5]
            for r in sub:
                snip = r["snippet"].replace("|", "\\|")
                fp.write(f"| {r['score']:.2f} | {r['page']} | `{snip}` |\n")
            fp.write("\n")
        fp.write("## Assessment\n\n")
        # Quick automated assessment
        best_score = results[0]["score"] if results else -1e9
        best_snippet = results[0]["snippet"] if results else ""
        # Check for any English-looking snippet in top 20
        english_indicators = ["THE", "AND", "FOR", "WITH", "THAT", "THIS", "ARE", "WAS", "WERE", "NOT", "BUT", "WELCOME", "PRIMES", "SACRED"]
        english_hit_count = 0
        for r in results[:20]:
            for w in english_indicators:
                if w in r["snippet"].upper():
                    english_hit_count += 1
                    break
        fp.write(f"- Best english_score across all combinations: **{best_score:.2f}**\n")
        fp.write(f"- Best snippet: `{best_snippet}`\n")
        fp.write(f"- Of the top 20 results, **{english_hit_count}** contain at least one common English indicator word "
                 f"(THE/AND/FOR/WITH/THAT/THIS/ARE/WAS/WERE/NOT/BUT/WELCOME/PRIMES/SACRED).\n")
        if english_hit_count == 0:
            fp.write("- **CONCLUSION:** No book cipher combination produced recognisable English. "
                    "The dossier's hypothesis 2 (book cipher with these specific codebooks) is **NOT SUPPORTED** by the pairs/triples/running conventions tested. "
                    "Likely reasons:\n"
                    "  1. The `pairs` convention only accesses the first 29 words × first 29 letters of each codebook (since rune decimals are 0..28), so information content is severely limited.\n"
                    "  2. The 56 unsolved LP2 pages are widely believed (CicadaSolvers, fresh findings §2.1) to use an **autokey/autoclave** cipher, NOT a classical book cipher.\n"
                    "  3. The book-cipher hypothesis may still be valid IF the indexing convention is different (e.g. larger block sizes, or different rune-value mapping), "
                    "but that is outside the scope of the dossier's `book_cipher()` definition.\n")
        else:
            fp.write("- **CONCLUSION:** Some book-cipher combinations produced recognisable English indicator words — worth manual review.\n")
    print(f"\nResults written to: {out_path}")


if __name__ == "__main__":
    main()
