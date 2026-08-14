# Phase G: Simulated Annealing + Latin Quadgrams + Keyword Alphabets

**Task ID:** p8g
**Target:** page 50.jpg (91 runes, the short page)
**Baseline (swap-only hill-climber, identity=TH):** score = -1057
**Date:** 2025

---

## Executive Summary

**No breakthrough.** All three attacks failed to produce recognisable English or Latin plaintext. The SA solver achieved **-1165.2** (WORSE than the swap-only hill-climber's -1057), confirming the local minimum is extremely deep and resistant to larger neighborhood moves. Latin quadgrams produced different but still-garbage plaintext. Four Cicada-themed keywords produced alphabets with F at the W(7) position, but none decrypted to readable text.

---

## Attack 1: Simulated Annealing

**Implementation:** `decoder/simulated_annealing.py`
- **Move types:** swap, segment-reverse (len 3-7), segment-rotate, single-element move (4 mutators, randomly chosen)
- **Schedule:** T_start=2.0 → T_end=0.01, geometric (T = T_start * (T_end/T_start)^(i/max_iter))
- **Acceptance:** exp(Δ/T) for worse moves
- **Primer:** re-evaluated all 29 primers every 5% of iterations; otherwise kept current
- **Actual run:** 30 restarts × 15,000 iterations (reduced from 50×50,000 to fit 120s timeout)

### Results

| Metric | Value |
|---|---|
| Best SA score | **-1165.2** |
| Best primer | AE |
| perm[0] (identity element) | J (not TH!) |
| Improvement over baseline (identity perm) | +631.7 |
| Comparison to swap-only HC (-1057) | **-108.2 worse** |

**Best plaintext (Latin):**
```
SAELDHEREATSTHEAVLYTHNGWIDDLECOMPHOEIABANOPINENINBOXTARSCFRONEOVSMSEATHVNMYGVREDCIVIARDCNGFEAAPRAEBEEBEO
```

**Analysis:** The SA converged to a different local minimum than the swap-only hill-climber. Notably, the SA's best solution has `perm[0]=J` rather than `TH`, suggesting the swap-only HC's -1057 was specific to the `perm[0]=TH` constraint. The SA did not preserve this constraint during mutation, so it explored a different basin. Fragments like "HEREAT", "THNGWIDDLE", "BOXTAR", "BEEBEO" are coincidental — no English words form.

### Why SA underperformed

1. **Short ciphertext (91 runes):** Only 88 quadgrams to score — high variance, weak signal.
2. **Unconstrained perm[0]:** SA drifted away from the TH identity element that the swap-only HC exploited.
3. **Primer coupling:** The 29-primer search is expensive; reducing its frequency to 5% may have missed better primer/perm combinations.
4. **Deep local minimum:** Even with reversals and rotations, SA could not escape the same basin.

---

## Attack 2: Latin Quadgrams

**Approach:** Built a Latin quadgram model from an embedded corpus (Cicero's *De Bello Gallico*, Seneca's *Epistulae*, Vulgate *Pater Noster*, Thelemic phrases, common Latin maxims). Transliterated Latin → runes via a classical mapping (J→I, U→V, W preserved, K/Q/Z→nearest).

| Metric | Value |
|---|---|
| Latin quadgrams built | 2,487 unique (small corpus) |
| Runeglish quadgrams (reference) | 464,496 unique |
| SA best re-scored under Latin | -1126.9 (vs Runeglish -1165.2) |
| Latin-only HC best (Latin score) | **-1036.0** |
| Latin-only HC best (Runeglish on same PT) | -1642.6 |

**Latin-only best plaintext:**
```
RDJMOVNCWIABVSPJTHBAEOEAMMJVFRHIOLASESTRIATVTATERYWSNIAFNGNRTEOPIAHIACWOPTHTHEAPNVMFAPGNMFAENGCSINDEVVEEO
```

### Verdict: Plaintext is NOT Latin

- The Latin model found a DIFFERENT local minimum (Latin -1036 is "better" under Latin scoring than the SA's Runeglish -1165 under Runeglish scoring).
- BUT the same plaintext scores -1642 under Runeglish — i.e., it looks nothing like English/Runeglish.
- The Latin-optimal plaintext contains non-Latin sequences: "VNCWIABVSP", "JTHBA", "VFRHIOLASE", "PTHTHEAP", "NVMFAPGNMFAENG".
- No Latin words are recognisable.
- **Conclusion:** The plaintext is neither English nor Latin under the first-difference + MASC model. Either the cipher model is wrong, or the scoring corpus is too small (2.5k vs 465k quadgrams).

### Caveat

The Latin corpus is tiny (~3KB of text → 2,487 quadgrams). A proper test would require a 1MB+ Latin corpus (Perseus, Latin Library). The current result is suggestive but not conclusive.

---

## Attack 3: Keyword-Derived Alphabets

**Approach:** For each Cicada-themed keyword, built a keyed alphabet (dedupe + remaining runes in order), then:
1. Found the position of F (decimal 0) in the alphabet — this is the "identity position"
2. Checked if it matches NG(21), W(7), or TH(2)
3. Tested as a direct MASC key with all 29 primers

### Keywords matching identity target (F at position 7 = W)

| Keyword | F-position | Score | Plaintext (first 60 chars) |
|---|---|---|---|
| **VOLVNTAS** | 7 (W) | -1500.5 | TJLPBOWCOLSOFNLTSENIPPLOSTVNGBXIFAFMTNGIMOMIMATHOFWLSRWTMTHN... |
| **VERITAS** | 7 (W) | -1501.9 | TJRPBOWCELSOFNRTSEIIPPROSTVNGBXIFAFMTNGIMOMIMATHEFWLSRWTMTHN... |
| **THELEMITES** | 7 (W) | -1525.2 | TJEPBOWCHLSOFNEMSELIPPEOSTVNGBXIFIFMTNGIMOMIMITHHFWLSRWTMTHN... |
| **LIBERPRIMI** | 7 (W) | -1542.4 | TJBPBOWCILMOFNBRMEEIPPBOSTVNGBXIFPFMTNGIMOMIMPTHIFWLSRWTMTHN... |

### Top 5 by score (regardless of identity match)

| Keyword | perm[0] | F-pos | Score |
|---|---|---|---|
| PARSIFAL | P | 5 (C) | -1482.1 |
| VOLVNTAS | V | 7 (W) | -1500.5 |
| VERITAS | V | 7 (W) | -1501.9 |
| THELEMITES | T | 7 (W) | -1525.2 |
| CIRCUMFERENCE | C | 4 (R) | -1533.3 |

### Verdict: No keyword produced readable plaintext

- 4 keywords (VOLVNTAS, VERITAS, THELEMITES, LIBERPRIMI) produced alphabets where F lands at position 7 (W) — matching one of the identity targets.
- Best score (-1482, PARSIFAL) is much WORSE than SA (-1165) and swap-only HC (-1057).
- No plaintext contains recognisable English or Latin words.
- The recurring "TJ?PBOWC?LSOFN" prefix across W-position keywords suggests the keyed-alphabet structure is forcing a fixed prefix, but it's not meaningful.

---

## Critical Assessment

**Did any attack produce recognisable English or Latin?**
**NO.** All three attacks produced garbage. The best plaintext (SA, -1165):
```
SAELDHEREATSTHEAVLYTHNGWIDDLECOMPHOEIABANOPINENINBOXTARSCFRONEOVSMSEATHVNMYGVRED
```
contains fragments that look English-ish ("HEREAT", "THNG", "BOX") but no actual words.

**Is the plaintext Latin?**
**Inconclusive.** The Latin model found a different local minimum (-1036 Latin vs -1165 Runeglish), but the resulting plaintext is not recognisable Latin. The Latin corpus was too small (2.5k quadgrams) for a definitive test.

**Did any keyword produce identity at NG/W/TH?**
**YES — 4 keywords** (VOLVNTAS, VERITAS, THELEMITES, LIBERPRIMI) produced F at position 7 (W). However, none decrypted to readable text, and their scores (-1500 to -1542) are much worse than the hill-climber's -1057.

---

## Artifacts Produced

| File | Description |
|---|---|
| `decoder/simulated_annealing.py` | SA solver + Latin quadgrams + keyword attack (all 3 attacks) |
| `decoder/simulated_annealing_results.json` | Full numerical results |
| `compiled/SA_LATIN_RESULTS.md` | This report |

---

## Recommended Next Steps

1. **Re-run SA with perm[0]=TH constraint** — the swap-only HC's -1057 was specific to TH identity; SA should be re-run with this constraint enforced throughout mutations.
2. **Larger Latin corpus** — fetch Perseus/Latin Library texts (~1MB) to build a proper Latin quadgram model (50k+ quadgrams) and re-test.
3. **Different cipher model** — the first-difference + MASC model may be wrong. Consider:
   - Pure Vigenère with F-skip (no first-difference)
   - Autokey Vigenère (plaintext mode)
   - Quagmire III with proper keyed plaintext alphabet
4. **Longer ciphertext** — page 50.jpg (91 runes) is too short for reliable quadgram scoring. Re-run on the 1468-rune block (pages 50-56).
5. **Genetic algorithm** — population-based search may escape the deep local minimum better than SA.
6. **Word-level scoring** — use a Runeglish dictionary + word-boundary detection instead of quadgrams, since the plaintext may have unusual spellings (Cicada used "WARNNG", "COAN", "INSTRVCTIAN").

---

## Conclusion

The swap-only hill-climber's -1057 on page 50.jpg appears to be a robust local minimum. Simulated annealing with larger moves did NOT escape it (got -1165, worse). Latin quadgrams did NOT reveal Latin plaintext. Keyword-derived alphabets did NOT produce readable text. **The cipher remains unsolved.** The most likely explanations are: (a) the cipher model is incorrect, (b) the page is too short for statistical attacks, or (c) the plaintext uses a non-standard language/encoding.
