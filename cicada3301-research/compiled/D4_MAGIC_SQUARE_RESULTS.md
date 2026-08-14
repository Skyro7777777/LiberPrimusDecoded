# D4 SYMMETRY ANALYSIS OF PAGE-16 + PAGE-5 MAGIC SQUARES — Task `p8f`

**Date:** 2026-08  •  **Agent:** D4 magic-square symmetry analysis subagent
**Scope:** Exhaustive 8-element D4 group symmetry × multiple interpretations × both magic squares.
**Tests run:** 296 (D4 × cipher modes + D4 × latin readings + 809-center variants + Hill-5 decrypt/encrypt × both squares × all 8 D4 transforms).
**Baselines:** Random palindromic 25-rune (1,000 samples): max=96.22, 99th pctile=88.24. Random primer 25-rune (prior 5,400 samples): max=74.18. Random 5×5 Hill (95 samples): max=72.77. Authentic Cicada plaintext: 80.33–88.36.

---

## 0. EXECUTIVE SUMMARY

**NO D4 interpretation produced English plaintext.** Top score 84.71 (page16, Caesar+19 of (V−809) mod 29 direct read) is within the random-palindrome noise band (99th pctile = 88.24).

### Top 5 of 296 tests (all are page-16 (V−809) variants — directly Echo446's claim)
| Rank | Score | Transform | Mode | Snippet |
|---|---|---|---|---|
| 1 | 84.71 | d4_e (Caesar+19 of minus809) | direct | NGEASITHDOEEAEOLIRMRILEOEAOEDTHISEANG |
| 2 | 82.56 | d4_e (Caesar+9 of minus809)  | direct | JECFNGPEOETHIFDNDFITHEEOPNGFCEJ |
| 3 | 81.38 | d4_e (Caesar+22 of minus809)| direct | ATHEPCYAETHSDPWOEWPDSTHAEYCPETHA |
| 4 | 81.01 | d4_e_minus809_latin        | direct | THNAELEORONOEVLXFXLVOENOREOLAENTH |
| 5 | 74.76 | d4_h_minus809_latin        | direct | EOLAENTHVOENORLXFXLRONOEVTHNAELEO |

Strings do not parse as English.

---

## 1. D4 GROUP × CIPHER MODES (Step 1, 96 tests)

D4 elements tested: `e`, `r90`, `r180`, `r270`, `h` (flipud), `v` (fliplr), `d` (transpose), `a` (anti-diag).

**Method:** For each (square × D4 × reading ∈ {row-major, spiral-in}) × (cipher ∈ {Vigenère no-skip, autokey-PT, autokey-CT}): apply transform → flatten → mod 29 → 25-rune primer → decrypt first 300 LP2 runes → score.

**Top 3:** all in 69.90–71.97 range — below the prior random-primer max of 74.18. **No signal.**

| Rank | Score | Square | Transform | Mode | Snippet |
|---|---|---|---|---|---|
| 1 | 71.97 | page5  | d4_d_rowmod29      | autokey_pt | RMAXFYTHTXJAEWVBELATSFYLHLWOIAFVOESHCTIAFEANXMYXJIABEONGOJBEEAXTVIAIOE |
| 2 | 71.52 | page16 | d4_d_xor_809_mod29 | vigenere   | SYMOEAAOEDCTHJDCRRJSDGIAAENOIAEWGAESSBCSLXEHIRVOEEANGHOETHEOEOLANGSSBT |
| 3 | 69.94 | page16 | d4_h_spiral_in     | vigenere   | GLAEYWEITHGNAESGVDHGDJJPOTHIANGIAFTHNDJOEDNGNGOFJVLMMNGPGMGJLIAEONNGJA |

**Note:** `r180` ≡ `e` for both squares (they ARE 180°-symmetric). `r90` ≡ `r270` reflected; `h` ≡ `v` reflected; `d` ≡ `a` reflected. Only **4 distinct D4 orbits** per square, reducing effective exploration from 8 to 4 unique primers.

---

## 2. PRIME-INDEX INTERPRETATION (Step 2, 32 tests)

### Cell-value primality audit (CRITICAL for Echo446's claim)

**Page-16 — primes found: exactly 1.**
| Position | Value | Prime index |
|---|---|---|
| **[2][2] (center)** | **809** | **140th prime** |

All other 24 cells composite: 434=2·7·31, 1311=3·19·23, 312=2⁴·3·13, 278=2·139, 966=2·3·7·23, 204=2²·3·17, 812=2²·7·29, 934=2·467, 280=2³·5·7, 1071=3²·7·17, 626=2·313, 620=2²·5·31.

✅ **Echo446 VERIFIED (structural):** page-16 has exactly one prime, and it IS at the center.

**Page-5 — primes found: 3 (none at center).** Cells 131 (32nd, [0][3]/[4][1]), 151 (36th, [0][4]/[4][0]), 199 (46th, [1][1]/[3][3]). Page-5 center = **91 = 7 × 13 (composite)**. The "single prime at center" property is UNIQUE to page-16.

### Prime-index primer tests
- Variant A (prime cells only): page-16 yields 1-rune primer [809→140→140%29=24 → ᚪ "A"]; page-5 yields 6-rune primer. Neither decrypts LP2 (top score 67.43).
- Variant B (prime_index(V) mod 29 if prime, else V mod 29): tested as Vigenère/autokey on LP2 — top score 68.99, pure noise.

---

## 3. GEMATRIA-PRIMUS LETTER READINGS (Step 3, 48 tests)

**Method:** For each (square × D4 × reading ∈ {row-major, spiral-in, spiral-out}): apply D4 → flatten → V mod 29 → rune → Latin → score as standalone message.

**Top 3 (non-(V−809) readings):** all ≤ 68.84 — pure noise.

| Rank | Score | Square | Reading | String |
|---|---|---|---|---|
| 1 | 68.84 | page5  | spiral_in/out_latin | JOEOESGEDEJOEOESGEDEAEXVPAEXVPR (palindromic) |
| 2 | 67.61 | page16 | d4_e/r180_latin_reading | EAGOEBNVFGMIABJYJBIAMGFVNBOEGEA (palindromic) |
| 3 | 67.30 | page16 | d4_r90/r270_latin_reading | EAVNBMIGFEOABJYJBAOEFGBMNBVAE |

**No Gematria reading produces English words or Cicada-relevant phrases.**

---

## 4. 809-CENTER ANALYSIS (Step 4, 96 tests) — Echo446's specific claim

### Critical finding — (V − 809) mod 29 produces a PALINDROMIC 25-rune sequence
Because the square has 180° symmetry, `(V[i][j] − 809) mod 29 = (V[4−i][4−j] − 809) mod 29`. The 25-rune sequence is palindromic:

```
Decimal: [2, 9, 25, 20, 12, 4, 3, 9, 22, 1, 20, 14, 0, 14, 20, 1, 22, 9, 3, 4, 12, 20, 25, 9, 2]
Runes:   ᚦᚾᚫᛚᛇᚱᚩᚾᛟᚢᛚᛉᚠᛉᛚᚢᛟᚾᚩᚱᛇᛚᚫᚾᚦ
Latin:   TH N AE L EO R O N OE V L X F X L V OE N O R EO L AE N TH
Concat:  THNAELEORONOEVLXFXLVOENOREOLAENTH
```
Center rune = ᚠ (decimal 0 = "F"), from `(809−809) mod 29 = 0`.

### Direct-read scores — all 8 D4 transforms
| D4 | Score | Latin |
|---|---|---|
| `e`, `r180` | **81.01** | THNAELEORONOEVLXFXLVOENOREOLAENTH |
| `h`, `v`    | 74.76 | EOLAENTHVOENORLXFXLRONOEVTHNAELEO |
| `r90`,`r270`| 68.51 | EOVLRTHLOEXONAENFNAENOXOELTHRLVEO |
| `d`, `a`    | 68.51 | THRLVEONOXOELAENFNAELOEXONEOVLRTH |

### Caesar shift sweep (29 shifts of (V−809) mod 29 sequence)
| Shift | Score | Latin |
|---|---|---|
| +0  | 81.01 | THNAELEORONOEVLXFXLVOENOREOLAENTH |
| +9  | 82.56 | JECFNGPEOETHIFDNDFITHEEOPNGFCEJ |
| +19 | **84.71** | NGEASITHDOEEAEOLIRMRILEOEAOEDTHISEANG |
| +22 | 81.38 | ATHEPCYAETHSDPWOEWPDSTHAEYCPETHA |

Caesar +19 produces "NGEASITHDOEEAEOLIRMRILEOEAOEDTHISEANG" — score 84.71, highest of any test. The string is **palindromic at the rune level** (since the underlying sequence is). It contains recognizable fragments ("THIS", "EA", "OE", "NG") but **does not parse as English**.

### Statistical significance — random palindromic baseline
1,000 random palindromic 25-rune sequences scored: min=46.00, mean=65.65, 99th pctile=88.24, **max=96.22**.

**Our top (V−809) score of 84.71 is BELOW the random-palindrome 99th pctile (88.24).** The high score is a structural artifact of palindromes (which double common-bigram hits at endpoints). NOT statistically significant.

### Cipher-based tests using (V−809) mod 29 as primer on LP2 (all pure noise)
| Mode | Score | Snippet (first 60 chars) |
|---|---|---|
| Vigenère (no-skip) | 63.56 | PEAOEEODSALOEAEIAWCBLCOLHELEGFTCHEAAIHWEOHHCNGIBBTTEIPYNGSOEO |
| autokey-PT | 65.51 | PEAOEEODSALOEAEIAWCBLCOLHELEGFTDETHOEAYSVHPIAEACXBEOGWCEAEDC |
| autokey-CT | 67.27 | PEAOEEODSALOEAEIAWCBLCOLHELEGFTNGNGEOTOEEONGSEOWXCFYJPIATHAG |

All within pure-noise band (random-primer mean ≈ 66.2). **(V−809) mod 29 does NOT function as a working cipher primer.**

### Verdict — Step 4
- ✅ Echo446's structural observation VERIFIED: 180° symmetry around sole prime 809 at center.
- ✅ New finding: `(V−809) mod 29` produces a palindromic 25-rune sequence (architectural curiosity).
- ❌ Palindromic sequence does NOT produce English (score 84.71 is within random-palindrome noise).
- ❌ As cipher primer on LP2, scores are pure noise (63.56–67.27).
- **Echo446's "literally contains its own solution" claim is NOT VERIFIED.**

---

## 5. HILL-5 CIPHER (Step 5, 32 tests)

### Determinant invariance under D4
| Square | det mod 29 (all 8 D4 transforms) | Invertible? |
|---|---|---|
| Page-16 | 10 (10⁻¹ = 3 mod 29) | ✅ YES — all 8 D4 transforms invertible |
| Page-5  | 3 (3⁻¹ = 10 mod 29) | ✅ YES — all 8 D4 transforms invertible |

Both squares are mathematically valid Hill-5 keys under all 8 D4 transforms. (Determinant is group-theoretically invariant under D4 action; the 8 transforms collapse to identical determinant, so D4 sampling doesn't expand the Hill-5 key space.)

### Top 3 Hill-5 results
| Rank | Score | Square | Transform | Direction | Snippet |
|---|---|---|---|---|---|
| 1 | 72.55 | page5  | d4_h/v_hill5_encrypt  | hill5 | PBTHNGGRDSNGATHAEFBAEAENGINXPTHFTHAECOMOETHOEJXAPEOWRTNEAMTIFVIAEAGAEV |
| 2 | 70.20 | page5  | d4_e/r180_hill5_encrypt | hill5 | GNGTHBPANGSDRAEBFAETHXNINGAEAETHFTHPTHOEMOCPAXJOENTRWEOFITMEAAEGEAIAVA |
| 3 | 69.03 | page16 | d4_e/r180_hill5_decrypt | hill5 | NBJTHNNGSORSFJEADTHIINOMJRTNRPCIJTHEAVBMDEOJNGBIEOLEOELPOECOSMSFAETHOE |

**Hill-5 fails.** Top score (72.55) is below the prior random-5×5-Hill baseline max of 72.77. All 32 results within pure-noise band.

---

## 6. PAGE-5 SQUARE — PARALLEL ANALYSIS (Step 6)

Page-5 recap: magic constant **1033** (prime, 174th); center cell **91 = 7×13 (composite)**; 3 primes present (131, 151, 199) — none at center; 180° symmetry verified.

### (V − 91) mod 29 — page-5 center-subtraction analogue
```
Decimal: [7, 18, 18, 11, 2, 14, 21, 10, 26, 14, 19, 9, 0, 9, 19, 14, 26, 10, 21, 14, 2, 11, 18, 18, 7]
Runes:   ᚹᛖᛖᛄᚦᛉᛝᛁᚣᛉᛗᚾᚠᚾᛗᛉᚣᛁᛝᛉᚦᛄᛖᛖᚹ
Latin:   WEEJTHXNGIYXMNFNMXYINGXTHJEEW
Score:   65.93 (best Caesar +20 → 74.76, within noise)
```

**Page-5 top score across all steps: 72.55 (Hill-5 encrypt, d4_h/v).** All other tests < 72. The "single prime at center" structural property does NOT apply to page-5.

---

## 7. CRITICAL ASSESSMENT — DID u/Echo446's CLAIM VERIFY?

### Claim-by-claim verdict
| Claim | Verified? | Evidence |
|---|---|---|
| Page-16 has 180° rotational symmetry | ✅ YES | `a[i][j] == a[4−i][4−j]` for all 25 cells |
| "Perfect symmetry around single prime (809)" | ✅ YES (structural) | 809 is the ONLY prime in the 25-cell square; at center [2][2]; 809 = 140th prime |
| Square "literally contains its own solution" | ❌ NO (functional) | 296 D4 tests failed to extract English; top score 84.71 within random palindromic noise |
| "Center row [809, 620, 626] converts to ASCII" | ❌ NO | Actual center row is [626, 620, 809, 620, 626]; values ≥204, outside ASCII 32–126 |
| `(V − 809) mod 29` produces a palindromic rune sequence | ✅ YES (new finding) | 25-rune palindrome centered on ᚠ (decimal 0) |
| Palindrome reads as English under any transformation | ❌ NO | Direct read 81.01; best Caesar (+19) 84.71; no parseable English words |

### Statistical significance summary
| Test | Score | Random baseline max | 99th pctile | Verdict |
|---|---|---|---|---|
| `(V−809) mod 29` direct read | 81.01 | 96.22 (random palindrome) | 88.24 | WITHIN NOISE |
| Best Caesar shift (+19) | 84.71 | 96.22 | 88.24 | WITHIN NOISE |
| `(V−809) mod 29` as Vigenère primer | 63.56 | 74.18 (random primer) | 73.56 | PURE NOISE |
| Hill-5 decrypt (any D4 transform) | 69.03 | 72.77 (random 5×5 Hill) | — | PURE NOISE |
| Authentic Cicada plaintext (page 01) | 88.36 | — | — | reference |

### Final verdict
**PARTIALLY VERIFIED (structural) / NOT VERIFIED (functional).** u/Echo446's structural observation about 180° rotational symmetry around the sole prime 809 is correct and notable. The new finding — that `(V−809) mod 29` produces a palindromic 25-rune sequence — is mathematically interesting but cryptographically inert. Exhaustive cryptanalysis (296 D4 tests + 1,029 prior deepdive tests = 1,325 total) found **no English plaintext, no meaningful message, and no cipher primer that decrypts LP2**. The high scores (81.01–84.71) on direct-read variants are statistical artifacts of palindromic structure (palindromes double common-bigram hits at endpoints). Echo446 likely over-interpreted a real structural observation as a functional solution — consistent with the broader recantation in post `1lbrnj3`.

### Most promising interpretation / recommendation
**None are promising as cipher solutions.** Two structural observations have independent mathematical interest (as design features, not ciphers):

1. **(V − 809) mod 29 palindrome**: Architecturally elegant (palindromic 25-rune sequence with ᚠ at center) but cryptographically inert.
2. **Determinant invariance under D4**: All 8 D4 transforms produce identical determinants mod 29 (det=10 for page-16, det=3 for page-5). Group-theoretic property; D4 sampling doesn't expand the Hill-5 key space.

**Recommendation for parent agent:**
- **DROP** the magic-square-as-cipher-key hypothesis. 1,325 total tests across all reasonable interpretations have produced zero signal above noise.
- **RETAIN** the structural observation that page-16 has 180° symmetry around its sole prime (809 = 140th prime). Deliberate design feature; aesthetic/philosophical significance to Cicada, NOT a cipher key.
- u/Echo446's claim: **correct structural observation, incorrect functional inference.** The recantation in `1lbrnj3` was appropriate.

---

## 8. ARTIFACTS PRODUCED
- `decoder/d4_runs/d4_symmetry_analysis.py` — Full analysis script (296 tests).
- `decoder/d4_runs/d4_results.json` — Complete 296-result JSON.
- `compiled/D4_MAGIC_SQUARE_RESULTS.md` — This document.

---

*End of report — Task p8f, 2026-08.*
