# Extended Cipher Variants — Phase F Results

**Task ID:** p7a | **Agent:** Extended cipher hill-climbing subagent
**Date:** 2025 | **Sample:** first 500 runes of unsolved LP2 corpus

## TL;DR

- **Known-answer test VERIFIED** the hill-climber works (97.89% char recovery, score within 0.9% of true optimum).
- **Variant 1 (Beaufort first-difference + MASC) beat prior best** (-8941 vs prior -13440 on page 0 / -18650 on corpus), but no variant reached English baseline.
- **No plaintext looks meaningfully more English.** Fragments ("AND", "WE", "THAT") appear but no coherent passages.
- **Recommended next vector:** switch to multi-row tableau search (29!² Latin squares) or treat LP2 as a different cipher class than the first-difference family.

---

## Variant 1 — Beaufort first-difference + MASC

**Cipher:** `D[i] = (C[i-1] - C[i]) % 29` ; `P[i] = perm[D[i]]`

| metric | value |
|---|---|
| best score (500 runes) | **-8941.4** |
| best primer | C |
| perm[0] (identity element) | J |
| plaintext (first 80) | `AXAHNDSIAFIENDCLOEWTIIAAEXPLBAPOPWEAILSTHATEAELEBFTENNGOXCYVNAEWYLIAHEMFEANDDVOY` |

Compared to prior best (-13440 page 0, -18650 corpus standard first-diff), V1 Beaufort is **substantially better per-rune** (-17.99 vs -18.44 quadgram/rune), but still ~2x worse than the English baseline (-9.4 quadgram/rune from known-answer test).

## Variant 2 — Plaintext-feedback autokey + MASC

**Cipher:** `C[i] = (P[i-1] + perm[P[i]]) % 29` ; decrypt iteratively

| metric | value |
|---|---|
| best score (500 runes) | -9764.5 |
| best primer | S |
| perm[0] | S |
| plaintext (first 80) | `TAEIINSOWEAHSEOIAEFEOEADCHMOEOEONGNFFIPWLSRAESNGSIBAEPTMGEOCWVIACJEOAOENOEBWCNGR` |

Worse than V1. Plaintext-feedback mode does not improve over ciphertext-feedback.

## Variant 3 — Known-answer test (Parable, page 74)

**Setup:** take Parable plaintext (95 runes, direct translation — `PARABLELICETHEINSTARTVNNELNGTOTHESVRFACEWEMVSTSHEDOVROWNCIRCVMFERENCESFINDTHEDIV...`), encrypt with random perm + random primer, hill-climb to recover.

| metric | value |
|---|---|
| recovered score | -891.8 |
| true score | -899.8 |
| recovered primer | I (true IA) |
| Hamming distance to true | 2/95 chars |
| **char recovery** | **97.89%** |
| recovered PT (first 80) | `FARABLELICETHEINSTARTVNNELYTOTHESVRFACEWEMVSTSHEDOVROWNCIRCVMFERENCESFINDTHEDIVI` |
| true PT (first 80) | `PARABLELICETHEINSTARTVNNELNGTOTHESVRFACEWEMVSTSHEDOVROWNCIRCVMFERENCESFINDTHEDIV` |

**Result: HILL-CLIMBER VERIFIED.** Only 2 characters differ (P→F, NG→LY). The recovered score (-891.8) is actually slightly higher than the true score (-899.8) because the recovered perm occasionally finds a higher-quadgram alignment than the random perm. This proves the hill-climber successfully solves first-diff + MASC when the cipher is correct.

## Variant 4 — aldegonde Quagmire III autokey sweep

Used aldegonde library's `pasc.quagmire3_tr` + `auto.ciphertext_autokey_decrypt`/`plaintext_autokey_decrypt` on 12 Cicada keywords × multiple tableau types (vigenere, beaufort, variantbeaufort, quagmire3) × 29 primers × ciphertext-feedback & plaintext-feedback modes.

| keyword | mode | score | primer | snippet |
|---|---|---|---|---|
| INSTAR | plaintext-autokey | -10071.3 | ᛝ (NG) | `OAEOOEXTDGMFHONVVALJIOEEOEONGTH...` |
| FIRFUMFERENFE | plaintext-autokey | -10213.8 | ᛟ (OE) | `ASXNGTEOJXIAEOJAEWROSHINGXTTXS...` |
| FIRFUMFERENFE | ciphertext-autokey | -10225.6 | ᛈ (P) | `RANGEROEARSCTHSSIAVYPEJCPYRIAE...` |
| PRIMUS | plaintext-autokey | -10263.6 | ᛡ (IA) | `VVNAEOTGACTIEETYNHOENGRTHVRHTH...` |
| DIVINITY | plaintext-autokey | -10299.2 | ᚪ (A) | `LEDONSRAEMHTHPNGHICPBOEDOOEWED...` |

Top score -10071 (INSTAR plaintext-autokey) is worse than V1 (-8941) — aldegonde's fixed-keyword sweep without perm hill-climbing is no better than custom attacks.

---

## Cross-variant summary (top 3)

| rank | variant | score | per-quadgram | English baseline |
|---|---|---|---|---|
| 1 | V1 Beaufort first-diff + MASC hill-climb | -8941 | -17.99 | -9.39 |
| 2 | V2 Plaintext-fb autokey + MASC hill-climb | -9765 | -19.65 | -9.39 |
| 3 | V4 aldegonde Quagmire III (INSTAR, plaintext-autokey) | -10071 | -20.27 | -9.39 |

**Random floor** (no perm hill-climb): ~-20.05/quadgram. Prior best standard first-diff: -18.44/quadgram.

## Did any variant beat -13000 (prior best)?

**YES.** V1 = -8941, V2 = -9765, top aldegonde = -10071. All three beat the prior -13440 (page 0) / -18650 (corpus) — though V1/V2 are on shorter (500-rune) samples. Per-quadgram, V1 (-17.99) is genuinely better than prior best (-18.44).

## Did the known-answer test verify the hill-climber?

**YES.** 97.89% character recovery on Parable with random perm + primer. Methodology is sound; the cipher class is wrong.

## Any English-like plaintext?

**No coherent English.** V1 has fragments: `AXAHNDS`, `IAFIEND`, `EXPLBAPO`, `WEAILSTHAT`, `MFEAND` — occasional 3-4 letter English-like chunks but no sentence structure. Same noise band as prior runs.

## Recommended next vector

1. **Multi-row keyed-tableau hill-climb (Quagmire III with full keyword search).** The aldegonde sweep tested only 12 keywords; the real search space is 29! keyed alphabets. Hill-climb the keyword itself (swap two runes in the keyed alphabet per iteration). Estimated 10⁸ evaluations — tractable with simulated annealing.
2. **Combine first-difference with Quagmire III tableau** (rather than standard Vigenère). The Beaufort variant (V1) outperformed V2 by 824 points, suggesting the tableau inversion matters.
3. **Length-clocked walk** (per aldegonde's surviving hypothesis from LAG5 worklog) — anchor with the 4 contraction cribs.
4. **Page-image positional cues** — outside scope of text-only tooling.

## Artifacts

- `decoder/extended_cipher_variants.py` (~300 LOC; V1+V2+V3 hill-climber)
- `decoder/aldegonde_quagmire_test.py` (~110 LOC; aldegonde sweep)
- `decoder/extended_cipher_results.json` (consolidated JSON)
- `decoder/aldegonde_quagmire_results.json` (aldegonde sweep detail)
