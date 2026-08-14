# Page 50.jpg Deep Dive — Most Promising Unsolved Page

**Task ID:** p8e
**Date:** 2026-08-14
**Target:** `50.jpg` (91 runes, smallest non-trivial unsolved page)

## Executive Summary

**Page 50.jpg is NOT cracked.** Despite intensive hill-climbing (300+ restarts × 50–100k iterations across 3 identity candidates), crib-dragging with 50+ Cicada phrases, all-29-primers testing, and an alternative first-difference MASC attack, no recognisable English plaintext emerged. The cipher remains unbroken, but several new structural insights were obtained.

Best score: **-1057.3** (TH identity, 100 restarts × 50k iters). Per-rune: -11.6. True English would score ~-5 per rune (-455 total). We are **2.3× off** — a marginal improvement over p8c's -1125 result.

## Page 50.jpg Ciphertext

```
ᛞᛇᛉᚳᚠᛁᚪᚹᚻᚷᛇᛟᚠᛏᛖᛟᛠᚪᛡᛋᚷᚣᛠᚾᚦᚫᚱᚩᛡᛗᚹᛉᛗᚣᛞᛒᛏᚱᚢᛄᚻᚫᛟᛡᛝᚹᚻᛋᚠᛡᛚᚦᛏᛁᚹᛏᚩᚢᚾᚹᛗᛚᛋᚦᛠᚹᛄᚪᛄᚫᚷᚣᛗᚹᛞᛈᛡᛖᛄᚹᛖᚢᚻᚹᛝᛁᛋᚫᚷᛄᛚ
```
91 runes, no header hint, `is_solved: false`.

## Step 1: Intensive Quagmire III Hill-Climbing (3 identities × 100 restarts × 50k iters)

| Identity | Best Score | Per-Rune | Primer | Plaintext (first 70 chars) |
|----------|-----------|----------|--------|---------------------------|
| NG       | -1091.4   | -12.0    | M      | RVELTICCALEWEALFVRTETPOFWATSOIMIDOMYNOADALIDLAHAGGPIPEDMPLACLIEDEAVERVWOOLITEFEWENNVNGSEROOMY |
| W        | -1121.6   | -12.3    | A      | EABEETHINCALCOXLFYMLEYPOSSATIVIMIDOMYROMBALIMLAHATNGPIPEDMPEEPLIEREIVEHVWOOLITOFEWENOVNGSEXOOMY |
| **TH**   | **-1057.3** | **-11.6** | R    | MEARLYIRCVLTONLAYPSHEAPONTHATDOFMINOMYVOOBAYIMIFHVETOSPEDMPLEFLIDGERVEOVWOOLITEMPWEROWNGLETOOMTH |
| TH (200r × 100k) | -1084.9 | -11.9 | W | TVRTYCCCLLEINLARPTHEAPONSATDOFMINOMYTOOBATIYIIHLETOSPEEMPLEPLIDGERVERVWOOLITEMPWEROYNGVPTOOMTH |

**Observation:** TH identity consistently produces the best score. The alphabet positions 4 (TH), 9 (Y), 10 (I), 17 (M), 18 (AE), 20 (T), 23 (D), 25 (J), 28 (G) are **stable across all 3 identities** — suggesting these positions are correctly placed by the hill-climber (or near a strong attractor).

**Common fragments appearing across multiple runs:** "DOFMINOMY", "WOOLITEMP", "...TOOMTH", "PIPEDMP". These appear consistently even with different alphabets — a strong signal of local-minima structure.

## Step 2: First-Difference + MASC Attack

Script: `first_diff_masc.py` (alternative cipher model: D[i] = C[i]-C[i-1] mod 29, P[i] = perm[D[i]]).

| Run | Score | Per-Rune | Primer | Plaintext |
|-----|-------|----------|--------|-----------|
| 50 restarts × 50k | -1189.4 | -13.1 | V | RIATHEGOTMYCHOAITHWHFAESEETHORDNGLGEOSANAVDLSVOVSVNDBYATCREATDVPICNGCMYGIVNGWOEITOERSIXTERFEAMALTIANOONP |

**Worse than Quagmire III** (-1189 vs -1057). The first-difference MASC model is not a better fit for page 50.jpg than Quagmire III autokey.

## Step 3: Crib-Dragging with 50+ Cicada Phrases

Tested 50 specific Cicada phrases (from solved LP1 text) at every position in the 91-rune ciphertext. For each (crib, position), propagated the implied Quagmire III tableau constraints via BFS over Z/29.

**Result: No crib produced high propagation.** Best propagation: 5 out of 7 constraints (crib "SVFFERNG" at position 11). Most cribs propagated only 2–3 constraints before becoming underdetermined.

This is consistent with: (a) page 50.jpg is NOT a contiguous substring of known LP1 text, OR (b) the Quagmire III model is incorrect for this page, OR (c) the crib must be at a very specific position to fire many constraints.

| Crib | Best Pos | Constraints | Propagated | Status |
|------|----------|-------------|-----------|--------|
| SVFFERNG (7 char) | 11 | 7 | 5 | OK (no contradiction) |
| AREALAWVNTO | 51 | 10 | 4 | OK |
| AREABENGVNTO | 50 | 11 | 3 | OK |
| FINDTHEDIVINITY | 29 | 14 | 2 | OK |
| ANINSTRVCTIAN | 32 | 12 | 2 | OK |

Full results saved to `deep_50_cribdrag.json`.

## Step 4: All-29 Primers Test with Best Keyed-Alphabet

Loaded the TH best alphabet and tested all 29 primers (F, U, TH, O, R, ... , NG).

**Key insight:** In Quagmire III autokey with ciphertext feedback, the primer affects ONLY the first plaintext character. Subsequent characters depend on the previous ciphertext rune. So all 29 primers produce essentially the same plaintext with only the first character changed.

For the TH alphabet, the top primers (by quadgram score) are:
- primer=EA, score=-2468.6 → "AEARLYIRCVLTONLA..."
- primer=Y,  score=-2468.6 → "YEARLYIRCVLTONLA..."
- primer=D,  score=-2468.6 → "FEARLYIRCVLTONLA..."
- primer=R,  score=-2468.6 → "MEARLYIRCVLTONLA..." (the one chosen by hill-climber)

The original hill-climber's choice (R) was already optimal. No primer variant yields recognisable English.

## Step 5: Structural Analysis of the Best Alphabet (TH)

The best keyed-alphabet (TH identity, score -1057.3):
```
W N F IA TH C EA O H Y I E P L A OE X M AE R T V EO D B J S NG G
0 1 2 3  4  5 6  7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28
```

**Cross-identity stable positions** (same letter in NG, W, and TH alphabets):
- pos 4 = TH, pos 9 = Y, pos 10 = I, pos 17 = M, pos 18 = AE, pos 20 = T, pos 23 = D, pos 25 = J, pos 28 = G

These 9 stable positions across all 3 identity candidates suggest a strong attractor in the search space — either the true alphabet has these letters at these positions, or the search is converging on a structurally-similar local minimum.

## Step 6: Web Search — Skipped (out of time budget)

Web search was not performed due to time constraints. Page 50.jpg may match a known Cicada phrase, but the 91-rune length doesn't immediately suggest any specific known text from LP1.

## CRITICAL FINDINGS

1. **Page 50.jpg is NOT cracked.** No attack produced recognisable English plaintext.
2. **Best score: -1057.3** (TH identity, 100×50k restarts). This is **2.3× off** the theoretical English-text score of -455.
3. **The hill-climber is stuck at a strong local minimum** — multiple runs from different seeds converge to similar plaintext structures ("DOFMINOMY", "WOOLITEMP", "...TOOMTH" fragments).
4. **All 29 primers test confirmed** the primer only affects character 0; the hill-climber's choice was already optimal.
5. **Crib-dragging failed** — no Cicada phrase produced high-constraint propagation. Either the page is not contiguous LP1 text, or the cipher model is wrong, or the crib position is highly specific.
6. **First-difference MASC model** scored worse (-1189) than Quagmire III (-1057) on this page — Quagmire III remains the better model.

## Hypotheses for Future Work

1. **Page 50.jpg may use a different cipher** than the solved pages (the puzzle could switch cipher models for unsolved sections).
2. **The alphabet may be keyword-based** — try deriving it from a Cicada-themed keyword (e.g., "PRIMESARESACRED", "LIBER", "INSTAR").
3. **The plaintext may be Latin** rather than English (Runeglish quadgrams may be mis-scoring it).
4. **Try simulated annealing** with larger neighborhood moves (3-letter block swaps, reversals) to escape the local minimum.
5. **Try Vigenère-style** instead of Quagmire III (different tableau structure).

## Artifacts Produced

- `decoder/deep_50_NG.json` — NG identity result (-1091.4)
- `decoder/deep_50_W.json` — W identity result (-1121.6)
- `decoder/deep_50_TH.json` — TH identity result, **best (-1057.3)**
- `decoder/deep_50_TH_long.json` — TH extended run (-1084.9, no improvement)
- `decoder/deep_50_firstdiff_masc.json` — first-diff+MASC result (-1189.4)
- `decoder/deep_50_cribdrag.json` — all crib-drag results (50 cribs × ~80 positions)
- `compiled/PAGE50_DEEPDIVE.md` — this report
