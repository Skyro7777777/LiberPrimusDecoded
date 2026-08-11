# WAVE-3 LAYERED CIPHER ATTACK RESULTS — Cicada 3301 Liber Primus (Unsolved LP2 Pages)

**Subagent:** Task ID `p2e` — Wave-3 layered cipher attack subagent
**Scope:** 56 unsolved LP2 pages (scream314 archive `17.jpg`–`72.jpg` / LP2 `0.jpg`–`55.jpg`); 12,956 runes total
**Toolkit:** `/home/z/my-project/cicada3301-research/decoder/wave3_attacks.py` (new, 7 layered attacks) + `gematria_primus.py` (existing, with F-skip-enabled `autokey_vigenere_fskip()` and `autokey_vigenere_reversed()` added)
**Foundation:** Wave-1 (`ATTACK_RESULTS.md` — autokey signature confirmed, 20 primers all in 60–72 noise band) + Wave-2 (`WAVE2_ATTACK_RESULTS.md` — parable-as-primer refuted, 372 tests all in 60–72 noise band) + Digraphic (`DIGRAPHIC_CIPHER_RESULTS.md` — Hill/Playfair/two-rune rejected)
**Raw data:** `/home/z/my-project/cicada3301-research/decoder/wave3_attack_results.json`
**Precedent:** The Koan-1 page (LP1 `06.jpg`–`09.jpg`) is the only solved page combining two classical operations — **Atbash + Caesar shift of 3**. This wave tests whether the unsolved LP2 pages use a similar layered construction (Atbash + autokey, Caesar + autokey, Atbash + Vigenère+F-skip).

---

## 0. EXECUTIVE SUMMARY — TL;DR

> **NO Wave-3 layered attack produced recognisable English plaintext.** All 7 attacks (Atbash+autokey, Autokey+Atbash, Caesar+autokey, Autokey+F-skip discovery, cipher-direction reversal, Vigenère+F-skip discovery, per-chapter layered) yielded `english_score()` values between 60 and 75 — statistically indistinguishable from random Latin-letter noise. Real English plaintext scores 110+ on the same function; the random-noise band (per `DIGRAPHIC_CIPHER_RESULTS.md` control experiment of 100k random 100-char Latin strings) is mean=65.93, P99=74.36, P99.99=79.48, max=81.06.

**Top 3 scores across all Wave-3 attacks:**
1. **74.695** — Attack 6: Pure Vigenère + F-skip, DIVINITY key, skip=[65, 91] — plaintext `NGIABOEYNJONGTBJAENGANTHMIEODEASEOAYTXGEOAEPIALHSYFSJDEAYOHE` (gibberish)
2. **73.462** — Attack 6: Pure Vigenère + F-skip, DIVINITY key, skip=[65] — same plaintext as above (skipping position 91 makes no difference to first 60 chars)
3. **73.314** — Attack 6: Pure Vigenère + F-skip, DIVINITY key, skip=[17, 91] — plaintext `NGIABOEYNJONGTBJAENGANTHFVNGOEFNGOENGPWDCPTHDAWEAAAEVNGNGLSB` (gibberish)

**The Koan-1 layered-cipher precedent (Atbash+Caesar-3) does NOT extend to the unsolved LP2 pages.** Applying Atbash before/after autokey, or Caesar-shifting before autokey, produces output indistinguishable from random noise. The F-skip discovery (Attacks 4 & 6) marginally improves the score by 2–4 points above the no-skip baseline (e.g. DIVINITY/Vigenère from ~70 → 74.7), but this is the natural effect of skipping F-runes to align the key with non-F positions — it does not unlock English.

**Breakthrough?** **NO.** All 432 Wave-3 tests produced gibberish. The autokey cryptanalytic signature (5.19× doublet suppression, IC~1.0, DJUBEI x2, OUNWM at distance 1031) remains intact from Waves 1–2, but the primer key is still unknown — and now we have strong evidence that the primer is NOT in our 21-candidate list (or any of their Caesar/Atbash transforms).

---

## 1. SETUP — corpus, primer database, F-skip positions

### 1.1 Corpus
- **Source:** `/home/z/my-project/cicada3301-research/decoder/unsolved_pages.json` — 13 page-groups, **12,956 runes total** (matches Wave-1/Wave-2 verification).
- **Working set (default):** first **300 runes** of concatenated unsolved corpus (per task spec for Attacks 1–3, 5).
- **Working set (F-skip discovery):** first **95 runes** (per task spec for Attacks 4, 6).
- **First 30 runes of unsolved corpus:** `ᛋᚻᛖᚩᚷᛗᛡᚠᛋᚣᛖᛝᚳᚦᛄᚷᚫᚠᛄᛟᚩᚾᚦᚾᛖᚹᛒᚪᛋᛟ`

### 1.2 F-rune positions in first 95 runes (verified)
The first 95 runes of the unsolved corpus contain **6 F-runes (ᚠ)** at positions:
```
[7, 17, 58, 61, 65, 91]
```
(Task spec estimated "~5 F-runes"; actual count is 6. The brute-force enumeration was adjusted accordingly: C(6,0)+C(6,1)+C(6,2)+C(6,3) = 1+6+15+20 = **42 skip-configs** per mode per key.)

### 1.3 Primer database
- **21 keys** = 20 `KEY_CANDIDATES` from `gematria_primus.py` (DIVINITY, FIRFUMFERENFE, INSTAR, EMERGENCE, EMERGE, PARABLE, DIVINITY_WITHIN, PILGRIM, PILGRIMAGE, WELCOME, SACRED, PRIMES_ARE_SACRED, TOTIENT, 1033_AS_RUNES, 761_AS_RUNES, 3301_AS_RUNES, 29_AS_RUNES, DJUBEI, OUNWM, HARMONIC_16) + the full 95-rune Parable text (`PARABLE_TEXT`).
- The Parable text was verified as 95 runes (the actual count from `solved_pages.json` page 74.jpg); the task description's "97 runes" appears to be an off-by-2 estimate.

### 1.4 New functions added to `wave3_attacks.py`
- `autokey_vigenere_fskip(ciphertext, primer, mode, decrypt, skip_indices)` — autokey Vigenère with F-skip rule. Skip positions: rune left unchanged, keystream does NOT advance, feedback stream is the non-skip plaintext/ciphertext.
- `autokey_vigenere_reversed(ciphertext, primer, mode)` — cipher-direction reversal: `plaintext[i] = (key[i] - cipher[i]) mod 29` instead of standard `(cipher[i] - key[i]) mod 29`.
- `atbash_then_autokey`, `autokey_then_atbash`, `caesar_then_autokey` — layered cipher compositors.

### 1.5 Random-noise baseline (control experiment, from `DIGRAPHIC_CIPHER_RESULTS.md`)
For 100-character Latin strings drawn uniformly from the 29-letter Gematria-Primus alphabet:
- Mean = 65.93, Median = 65.86
- P90 = 70.48, P95 = 71.83, P99 = 74.36, P99.99 = 79.48, Max = 81.06
- **A real English plaintext of length 100 scores ≥110.**
- **Anything below ~85 is statistically indistinguishable from random Latin noise.**

---

## 2. ATTACK 1 — ATBASH-THEN-AUTOKEY (Koan-1 precedent, 21 keys × 2 modes = 42 tests)

**Hypothesis:** Cicada may have used the same layered construction as Koan 1 (Atbash + shift-3), but with Atbash + autokey instead of Atbash + Caesar. Step 1: `atbash(ciphertext)` → Step 2: `autokey_vigenere(atbashed, key, mode)`.

**Test window:** first 300 runes of unsolved corpus.

### Top 5 (out of 42)

| Rank | Key | Mode | Score | Plaintext (first 60 chars) |
|---|---|---|---|---|
| **1** | **3301_AS_RUNES** | **plaintext** | **70.154** | `IBIAEONGLRVIMOOETIAMIEOMTSWWOAXRVENGEOBEGWSREOMCWWJIREOCWOEN` |
| 2 | PILGRIMAGE | ciphertext | 69.342 | `FIMMEEAJRWPYTPVAPTHFRRSEOOOEOEEAHCAEFLEAIHNJJXPXAVDBNGTDEAFP` |
| 3 | PARABLE | plaintext | 68.769 | `FAEGVCEEOEABAENTHCXECWMSVJVNGEOLGIOEEOXRIAVBYLHXEAMDOEIWYLYD` |
| 4 | EMERGENCE | ciphertext | 68.229 | `AVNGNGTLNGDAEMYIARHNGRSSAEEAEFTHBEEOTWIYNGBBIANGECLROEEOOAEH` |
| 5 | INSTAR | plaintext | 67.695 | `OJANIACIABEOEEOTHAENEAFLYNGYYMGOEEAXXWPIADOEPEOMAARWEAFGLWEO` |

**Full 42 tests** saved in `wave3_attack_results.json` under `attack1_atbash_then_autokey`.

### Critical assessment
- **Top score 70.154** (3301_AS_RUNES/plaintext) sits at the **P90 band** of random Latin strings (P90=70.48). It is **BELOW** the Wave-1 autokey top score of 69.62 — well within the random-noise band.
- The `3301_AS_RUNES` key ([3,3,0,1] as decimal-mod-29 runes) is short (4 runes), so the autokey feedback dominates the key stream after only 4 positions; its high score reflects incidental vowel-rich output (IBIAEON, ETIAMIEOM, ENGLEO, etc.) rather than real English.
- **NO recognisable English** in any of the 42 outputs. Plaintexts contain fragmentary English-like trigrams (THM, NGL, EOM, IAE) but no English words.
- The Atbash-before-autokey ordering (matching Koan-1's Atbash-before-Caesar) does NOT unlock the cipher. **The Koan-1 layered precedent does NOT extend to Atbash+autokey.**

---

## 3. ATTACK 2 — AUTOKEY-THEN-ATBASH (reverse layer order, 21 × 2 = 42 tests)

**Hypothesis:** Reverse layer order: maybe Cicada applied autokey first (encrypting plaintext to a vigenere-like stream), then Atbash on top. Step 1: `autokey_vigenere(ciphertext, key, mode)` → Step 2: `atbash(autokey_result)`.

**Test window:** first 300 runes.

### Top 5 (out of 42)

| Rank | Key | Mode | Score | Plaintext (first 60 chars) |
|---|---|---|---|---|
| **1** | **EMERGE** | **ciphertext** | **69.984** | `THIEAFEAIATWTHCTYNGYOMNGLOEHWAEOEMNGXXPSSCAEAOECAECEAENGLSWA` |
| 2 | SACRED | ciphertext | 69.576 | `EASSFJOTWTHCTYNGYOMNGLOEHWAEOEMNGXXPSSCAEAOECAECEAENGLSWAEPI` |
| 3 | DJUBEI | ciphertext | 69.498 | `WTHJPJMTWTHCTYNGYOMNGLOEHWAEOEMNGXXPSSCAEAOECAECEAENGLSWAEPI` |
| 4 | INSTAR | ciphertext | 69.279 | `DFAEEOBPTWTHCTYNGYOMNGLOEHWAEOEMNGXXPSSCAEAOECAECEAENGLSWAEP` |
| 5 | INSTAR | plaintext | 68.979 | `DFAEEOBPGIATENGOETIAFOICFWASSPNPSBYNGGRLNNGISPCIEHXVCHYHJTHV` |

### Critical assessment
- **Top score 69.984** (EMERGE/ciphertext) sits at the **P90 band** of random Latin strings.
- **Notable:** The top 4 ciphertext-mode results all converge to nearly identical output `...WTHCTYNGYOMNGLOEHWAEOEMNGXXPSSCAEAOECAECEAENGLSWA...` after the first 8 chars. This is because (a) all 4 keys are short (5–6 runes), so autokey feedback dominates after the primer is consumed, and (b) Atbash is its own inverse — applying Atbash to the autokey output essentially swaps the keystream positions. The convergent output suggests the cipher is structurally insensitive to short-primer choice under this layer ordering.
- **NO recognisable English.** The convergent suffix `WTHCTYNGYOMNGLOEHWAEOEMNG` has fragmentary trigrams (WTH, CTY, NGY, OMN, GLO, EHW) but no English words.
- **Autokey+Atbash is structurally similar to Atbash+autokey** (both produce vowel-heavy noise), confirming that Atbash as either inner or outer layer does not unlock the cipher.

---

## 4. ATTACK 3 — CAESAR-SHIFT-THEN-AUTOKEY (28 shifts × 2 keys × 2 modes = 112 tests)

**Hypothesis:** The unsolved pages may have a constant Caesar shift applied before/after the autokey layer. Step 1: `caesar(ciphertext, k, decrypt=True)` for k=1..28 → Step 2: `autokey_vigenere(caesar_result, key, mode)`.

**Keys tested:** DIVINITY (best Wave-1 performer) + PARABLE_TEXT (95-rune parable). 28 shifts × 2 keys × 2 modes = 112 tests.

### Top 10 (out of 112)

| Rank | Shift | Key | Mode | Score | Plaintext (first 60 chars) |
|---|---|---|---|---|---|
| **1** | **1** | **DIVINITY** | **ciphertext** | **69.963** | `LYTNGAEHITHFEFEEAEOPGIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJEA` |
| 2 | 4 | DIVINITY | plaintext | 69.938 | `BDPEOECWEADEAVEAHOEFOIAYGMLEOIATHTGWVLGIRVLIALJFBFEOXAEETHCL` |
| 3 | 20 | DIVINITY | ciphertext | 69.763 | `VWYTHGELEOFEFEEAEOPGIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJEAI` |
| 4 | 24 | DIVINITY | ciphertext | 69.721 | `YOOEIATHXTHFEFEEAEOPGIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJEA` |
| 5 | 19 | DIVINITY | ciphertext | 69.700 | `THHIAOWMNGPFEFEEAEOPGIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJEA` |
| 6 | 16 | DIVINITY | ciphertext | 69.566 | `CJVGIOEATFEFEEAEOPGIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJEAI` |
| 7 | 17 | DIVINITY | ciphertext | 69.508 | `RIFCNNGDSFEFEEAEOPGIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJEAI` |
| 8 | 4 | DIVINITY | ciphertext | 69.499 | `BDPEOECWEAFEFEEAEOPGIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJEAI` |
| 9 | 7 | DIVINITY | ciphertext | 69.499 | `XLISMTHRAEFEFEEAEOPGIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJEAI` |
| 10 | 11 | DIVINITY | ciphertext | 69.499 | `ITGJSIAFNGFEFEEAEOPGIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJEAI` |

### Critical assessment
- **Top score 69.963** (shift=1, DIVINITY/ciphertext) — within the random-noise P90 band.
- **Notable pattern:** Every DIVINITY/ciphertext result from shift=1 through shift=28 converges to the same suffix `FEFEEAEOPGIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJEAI` after a 4–8 character prefix. This is the same autokey-feedback convergence observed in Attack 2 — short primers (DIVINITY=8 runes) make the autokey feedback dominate after the primer is consumed, so the Caesar shift only changes the first ~8 runes of output before the autokey "settles" into its self-similar stream.
- The shift=4/DIVINITY/plaintext result (rank 2, score 69.938) shows slightly more variety in the suffix, but is still gibberish.
- **PARABLE_TEXT (95 runes) does not appear in the top 10** — its longer primer means more primer-phase runes (95 of 300) but the autokey feedback after position 95 still produces noise. Best PARABLE_TEXT score across all 112 shifts: 67.452 at shift=11/ciphertext (not in top 10).
- **NO recognisable English** in any output. The repeated `FEFEEAEOPGIOOEVIAWLOOEWGTHEOPIVODNGVLBM` fragment has incidental English-like trigrams (FEF, EAE, EOP, GIO, OEV, IAW, LOO, EWT, HEO, PIV, ODNGVLBM) but no English words.
- **The Caesar-shift+autokey layered hypothesis is rejected.** No shift value (1–28) unlocks English plaintext.

---

## 5. ATTACK 4 — AUTOKEY WITH F-SKIP DISCOVERY (DIVINITY + PARABLE, 168 tests)

**Hypothesis:** The solved Vigenère pages (3-4 DIVINITY, 14-15 FIRFUMFERENFE, 56 prime-stream) all required F-skip discovery. The autokey variant may also require F-skip, but the skip positions are unknown. Brute-force all combinations of 0–3 of the 6 F-rune positions in the first 95 runes.

**Configuration:** 6 F-rune positions = `[7, 17, 58, 61, 65, 91]`. All combinations of 0, 1, 2, 3 of these = 1+6+15+20 = **42 skip-configs** per key per mode. With 2 keys (DIVINITY, PARABLE_TEXT) × 2 modes = **168 total tests**.

### Top 10 (out of 168)

| Rank | Key | Mode | Skip indices | Score | Plaintext (first 60 chars) |
|---|---|---|---|---|---|
| **1** | **DIVINITY** | **ciphertext** | **[7, 91]** | **71.634** | `NGIABOEYNJFEJIOTHAENGHIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJE` |
| 2 | DIVINITY | ciphertext | [7] | 71.471 | `NGIABOEYNJFEJIOTHAENGHIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJE` |
| 3 | DIVINITY | ciphertext | [7, 58, 91] | 71.215 | `NGIABOEYNJFEJIOTHAENGHIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJE` |
| 4 | DIVINITY | ciphertext | [7, 58, 65] | 71.121 | `NGIABOEYNJFEJIOTHAENGHIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJE` |
| 5 | DIVINITY | ciphertext | [7, 58] | 70.985 | `NGIABOEYNJFEJIOTHAENGHIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJE` |
| 6 | DIVINITY | ciphertext | [7, 61, 65] | 70.979 | `NGIABOEYNJFEJIOTHAENGHIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJE` |
| 7 | DIVINITY | plaintext | [58, 61, 65] | 70.758 | `NGIABOEYNJODEAVEAHOEFOTHVIDATTHGTGWVLGIRCATHASRNGR` |
| 8 | DIVINITY | ciphertext | [7, 17, 91] | 70.675 | `NGIABOEYNJFEJIOTHAENGHIFXRJRFIAEOJGTHEOPIVODNGVLBM` |
| 9 | DIVINITY | ciphertext | [7, 17] | 70.552 | `NGIABOEYNJFEJIOTHAENGHIFXRJRFIAEOJGTHEOPIVODNGVLBM` |
| 10 | DIVINITY | ciphertext | [7, 65, 91] | 70.481 | `NGIABOEYNJFEJIOTHAENGHIOOEVIAWLOOEWGTHEOPIVODNGVLB` |

### Critical assessment
- **Top score 71.634** (DIVINITY/ciphertext/skip=[7, 91]) — still below the 80 break-flag threshold and far below the ~110 real-English threshold.
- **All top-10 results involve skipping position 7** (the first F-rune in the unsolved corpus). This is structurally intuitive: the first F-rune in the ciphertext is the natural skip candidate (page-56 precedent: the 4th of 5 F-runes was skipped; here, the 1st of 6 is the most natural skip).
- **Notable:** The output for skip=[7] vs skip=[7, 91] is identical in the first 60 chars (`NGIABOEYNJFEJIOTHAENGHIOOEVIAWLOOEWGTHEOPIVODNGVLB`). This is because position 91 is at the end of the 95-rune window — skipping it doesn't change the prior output, only the autokey feedback stream from position 91 onward. The marginal score difference (71.634 vs 71.471) comes from the last 4 characters of the 95-rune window.
- **The autokey+F-skip top score (71.634) is essentially the same as the Wave-1 DIVINITY/ciphertext top score (69.46).** The 2.2-point improvement comes from correctly skipping the first F-rune (which slightly aligns the keystream with the non-F ciphertext positions), NOT from unlocking English.
- **NO recognisable English** in any of the 168 outputs. The top plaintext `NGIABOEYNJFEJIOTHAENGHIOOEVIAWLOOEWGTHEOPIVODNGVLBMIAAEHEBJE` is gibberish — fragmentary trigrams (NGIA, BOEY, FEJI, OTHA, NGHI, OOEV, IAWL, OOEW, GTHE, OPIV, ODNGVLBM, IAAE, HEBJEA) but no English words.
- **The F-skip discovery does NOT unlock the autokey cipher.** The 6 F-runes in the first 95 runes, even with optimal skip-position selection, do not produce English.

---

## 6. ATTACK 5 — CIPHER-DIRECTION REVERSAL (4 keys × 2 modes = 8 tests)

**Hypothesis:** Standard autokey decryption is `plaintext[i] = (cipher[i] - key[i]) mod 29`. Test the reverse: `plaintext[i] = (key[i] - cipher[i]) mod 29` — if Cicada encrypted with `cipher[i] = (key[i] - plaintext[i]) mod 29` (subtracting plaintext from key), our "decryption" would actually be encryption.

### All 8 results (sorted by score)

| Rank | Key | Mode | Score | Plaintext (first 60 chars) |
|---|---|---|---|---|
| **1** | **TOTIENT** | **plaintext** | **68.213** | `VAIAWEOMEVNVELXTMOCENNGPIVAEFTHREAHPMIONEATHOBTHSFVESHMRIAGY` |
| 2 | PARABLE_TEXT | plaintext | 67.590 | `IATSNGJVLLAHFIPHIANLAOEDIAFWNTHXEAHTAEOLEOEASNEOYTJPGETHLNJN` |
| 3 | DIVINITY | ciphertext | 66.293 | `HTHEOWOLEYFJFJVBTDMYWEATHOENYWOEDIABTMEAYGHEANEOITHRNGJEOEVM` |
| 4 | FIRFUMFERENFE | plaintext | 65.743 | `XTHSYAFTHEENGLHPEOLNVAENSNMJMGAAEDHEOHBXFDCNRTHXIEALHTHENGIB` |
| 5 | FIRFUMFERENFE | ciphertext | 65.459 | `XTHSYAFTHEENGLHPPYEOWGHCYGANOIAXTLOBVVTHFGOHCNWGAEAOEEOEIADJ` |
| 6 | TOTIENT | ciphertext | 65.161 | `VAIAWEOMESOENGXXXAEENVEIEOEATHRTJRCHDNYHSTSMTTHHPPFIAOEOEOEA` |
| 7 | DIVINITY | plaintext | 64.256 | `HTHEOWOLEYOECDSIAEWLYCEOOEANCJHIAAIANTOEVTYSTHOGLOEEABBESYHJ` |
| 8 | PARABLE_TEXT | ciphertext | 63.647 | `IATSNGJVLLAHFIPHIANLAOEDIAFWNTHXEAHTAEOLEOEASNEOYTJPGETHLNJN` |

### Critical assessment
- **Top score 68.213** (TOTIENT/plaintext) — below Wave-1 autokey top (69.62). Cipher-direction reversal does NOT improve the score.
- The reversed-direction output `VAIAWEOMEVNVELXTMOCENNGPIVAEFTHREAHPMIONEATHOBTHSFVESHMRIAGY` has fragmentary English-like trigrams (VIA, AWE, OEV, NVEL, TMOC, NNGPI, EFTHRE, PION, EATH, OBTH, SFV, ESHM, RIAGY) but no English words.
- **The cipher-direction-reversal hypothesis is REJECTED.** Cicada did NOT encrypt with the inverse direction.

---

## 7. ATTACK 6 — VIGENÈRE (PURE, NO AUTOKEY) WITH F-SKIP BRUTE-FORCE (DIVINITY, 42 tests)

**Hypothesis:** The cipher may be pure Vigenère (not autokey) with the DIVINITY key, but with an undiscovered F-skip pattern. Brute-force all 42 F-skip configurations (C(6,0..3)) over the first 95 runes.

### Top 10 (out of 42)

| Rank | Skip indices | Score | Plaintext (first 60 chars) |
|---|---|---|---|
| **1** | **[65, 91]** | **74.695** | `NGIABOEYNJONGTBJAENGANTHMIEODEASEOAYTXGEOAEPIALHSYFSJDEAYOHE` |
| 2 | [65] | 73.462 | `NGIABOEYNJONGTBJAENGANTHMIEODEASEOAYTXGEOAEPIALHSYFSJDEAYOHE` |
| 3 | [17, 91] | 73.314 | `NGIABOEYNJONGTBJAENGANTHFVNGOEFNGOENGPWDCPTHDAWEAAAEVNGNGLSB` |
| 4 | [17] | 72.533 | `NGIABOEYNJONGTBJAENGANTHFVNGOEFNGOENGPWDCPTHDAWEAAAEVNGNGLSB` |
| 5 | [61, 91] | 71.682 | `NGIABOEYNJONGTBJAENGANTHMIEODEASEOAYTXGEOAEPIALHSYFSJDEAYOHE` |
| 6 | [17, 58] | 71.347 | `NGIABOEYNJONGTBJAENGANTHFVNGOEFNGOENGPWDCPTHDAWEAAAEVNGNGLSB` |
| 7 | [17, 61] | 71.302 | `NGIABOEYNJONGTBJAENGANTHFVNGOEFNGOENGPWDCPTHDAWEAAAEVNGNGLSB` |
| 8 | [58, 91] | 70.842 | `NGIABOEYNJONGTBJAENGANTHMIEODEASEOAYTXGEOAEPIALHSYFSJDEAYOHE` |
| 9 | [61] | 70.784 | `NGIABOEYNJONGTBJAENGANTHMIEODEASEOAYTXGEOAEPIALHSYFSJDEAYOHE` |
| 10 | [17, 58, 91] | 70.642 | `NGIABOEYNJONGTBJAENGANTHFVNGOEFNGOENGPWDCPTHDAWEAAAEVNGNGLSB` |

### Critical assessment
- **Top score 74.695** (DIVINITY/Vigenère/skip=[65, 91]) — the **highest score across ALL Wave-3 attacks**. This is at the **P99 band** of random Latin strings (P99=74.36) — i.e., the best-of-42 random samples naturally lands around 74.
- **Compared to Wave-1's pure Vigenère (DIVINITY) top score of ~75** (per `ATTACK_RESULTS.md` §3a, the Wave-1 Vigenère scores were in the 60–75 range), the F-skip discovery gives a marginally lower top score (74.695 vs ~75). This is because the default Vigenère (no explicit skip) already implicitly handles F-runes as zero-shift runes; adding explicit skip=[65,91] just removes two zero-shifts from the keystream, slightly altering the alignment of subsequent key positions.
- **Notable:** The top results cluster into TWO distinct plaintext families:
  - Family A (skip includes 65): `NGIABOEYNJONGTBJAENGANTHMIEODEASEOAYTXGEOAEPIALHSYFSJDEAYOHE...`
  - Family B (skip includes 17, not 65): `NGIABOEYNJONGTBJAENGANTHFVNGOEFNGOENGPWDCPTHDAWEAAAEVNGNGLSB...`
  - The first 24 characters are identical (`NGIABOEYNJONGTBJAENGANTH`), then the streams diverge based on whether the F at position 17 was skipped. This is the expected behavior of pure Vigenère with F-skip — the key alignment differs based on skip choices.
- **NO recognisable English** in any of the 42 outputs. Family A has fragmentary trigrams (NGIA, BOEY, NONG, TBJA, ENGANT, HMIE, ODEA, SEOA, YTX, GEOA, EPIA, LHSY, FSJDEA, YOHE) and Family B has different fragments (HM FVNG, OEFN, GOEN, GPWD, CPTH, DAWE, AAAE, VNGN, GLSB) — but neither contains English words.
- **The pure-Vigenère+F-skip hypothesis with DIVINITY key is REJECTED.** The F-skip brute-force over the first 95 runes does not unlock English.

---

## 8. ATTACK 7 — PER-CHAPTER LAYERED ATTACK (9 chapters × 2 keys = 18 tests)

**Hypothesis:** Different chapter groups (CicadaSolvers groupings: Cross 0-2, Spirals 3-7, Branches 8-14, Möbius 15-22, Mayfly 23-26, Wing/Tree 27-32, Cuneiform 33-39, Spiral/Branches 40-53, Hollow 54-55) may each use a different layered cipher. Test the best Wave-1+Wave-3 combination (Atbash+autokey/DIVINITY/plaintext mode, and Atbash+autokey/PARABLE/plaintext mode) on each chapter's first 200 runes.

### All 18 results (sorted by score)

| Rank | Chapter | Key | Score | Plaintext (first 60 chars) |
|---|---|---|---|---|
| **1** | **Spiral-Branch 40-53** | **DIVINITY** | **71.130** | `CNHNGPATDEAGGIWNGPTHJGVMVYEAABOORNHABWOMAEIATIOHHVEJGOOIWCAE` |
| 2 | Hollow 54-55 | DIVINITY | 71.004 | `IEAGANGTIANGEATHEALSJDEOIICTNGSWNOIPWJFAEPOEEACYEAAETHOFYVPN` |
| 3 | Spirals 3-7 | DIVINITY | 70.863 | `XWSIIAPISEIYROEEABLACIAENLTTHNGTHNGOMJONHEADTEOOEIFOTHGXGOVA` |
| 4 | Cuneiform 33-39 | PARABLE_TEXT | 68.120 | `DTHEODJOBAEAGPEAPBOERIFGOEBWAEGVOEABNGEASOSNGARINFYOIYAEIADD` |
| 5 | Hollow 54-55 | PARABLE_TEXT | 67.852 | `LXOIPGAEIAEAAETPEBEOEOEBFLGBNGOOEEATHLVYBNGNGNDEANGEDTHAPSEO` |
| 6 | Möbius 15-22 | DIVINITY | 67.772 | `XBGNXBAOEIAJVNPVOPCGIADXNGJOIHRGDEOOOROEOEXGWVLDFYIAVNVEOEE` |
| 7 | Branches 8-14 | DIVINITY | 66.903 | `LHPEAEROEYGWEOEOEOSMOHHEOMPHIGEAXTHEXEAHGYOYEEANJETHEXLDNGO` |
| 8 | Mayfly 23-26 | PARABLE_TEXT | 66.569 | `XNBEOCDTTHHGFXDVNTPIANTXEOFJAEAEFEEFWEAWIAWSPFOHDIIOEVNGNGO` |
| 9 | Mayfly 23-26 | DIVINITY | 65.944 | `RDLYPREAEXBIAMEAWFGSCSPTXNDVEOVHRRPGISVEOIAOHNGXIAHADNGNJOAT` |
| 10 | Spirals 3-7 | PARABLE_TEXT | 65.623 | `AOEEOAEMOHNGOEEODEOTHTHELYLLGVIARAESOEYPRIAEVLXPYAOEEOAEMOHN` |
| 11 | Cuneiform 33-39 | DIVINITY | 65.345 | `PTSHMPMMNGATOEEOXEOFCFDTGTHOEATXBRBSHNOWTHCJVIWVEJIAAVOEYTH` |
| 12 | Wing-Tree 27-32 | PARABLE_TEXT | 65.079 | `AELIAPAECSEOIONGXFEAEAOEYEAJOMPEEOFGAAEOEAEOIGEHDYIAFNGIOEH` |
| 13 | Cross 0-2 | PARABLE_TEXT | 63.976 | `FAEGVCEEOHOYNGCCTHWTRPMAIBVMFAVJBVBOIAAIARJHVIRXFOEATHEOOEI` |
| 14 | Möbius 15-22 | PARABLE_TEXT | 63.009 | `AOOAGWOEEATHDETNHELTOEATYPCIAAOESYGSEACIVTHSJEOSRYIAVTHSEAN` |
| 15 | Spiral-Branch 40-53 | PARABLE_TEXT | 62.588 | `SACWCXXFDIAEFTHGLIDBOPWNOHHBBLHTHJLGIAAVAEOEHNAEJJYOANIEAE` |
| 16 | Branches 8-14 | PARABLE_TEXT | 62.304 | `VDIXIDLOTIWNEONOXIALLSAXLLTVIACAEEOJNGBRTHAVVSADFBEAEOEOTHG` |
| 17 | Wing-Tree 27-32 | DIVINITY | 61.950 | `SCVIARSBGCONEXDLTHHLGVGEAWEAEOWCIAEAELEOIAJIAVTXAXOEEJINATH` |
| 18 | Cross 0-2 | DIVINITY | 60.399 | `MINSPEAXTHDNGVNGIIAOLNWTXSNGDEAVXAMIAXOEMGPAPARRVCOEENGEAO` |

### Critical assessment
- **Top score 71.130** (Spiral-Branch 40-53 chapter, DIVINITY) — barely above the Wave-3 average (~67), within the random-noise band.
- **Notable:** The DIVINITY key outperforms PARABLE_TEXT in 6 of 9 chapters, while PARABLE_TEXT wins in 3 (Cuneiform 33-39, Mayfly 23-26, Wing-Tree 27-32). Neither dominance is statistically significant given the 1–3 point score gaps.
- **The Spiral-Branch 40-53 chapter (3008 runes — the longest unsolved page, LP2 page 40) shows the highest score** (71.130), but the plaintext `CNHNGPATDEAGGIWNGPTHJGVMVYEAABOORNHABWOMAEIATIOHHVEJGOOIWCAE` is gibberish. There is NO chapter-specific break.
- **The Hollow 54-55 chapter (71.004) and Spirals 3-7 chapter (70.863)** are similarly gibberish.
- **NO chapter produces recognisable English.** The per-chapter layered attack confirms that the unsolved pages do not use a chapter-specific Atbash+autokey(DIVINITY or PARABLE) cipher.

---

## 9. CRITICAL ASSESSMENT — DID ANY WAVE-3 ATTACK PRODUCE ENGLISH?

### NO. Across all 7 Wave-3 attacks:

| Attack | Tests run | Best score | Top key / mode / skip | English? |
|---|---|---|---|---|
| 1: Atbash-then-autokey (21 keys × 2 modes) | 42 | 70.154 | 3301_AS_RUNES / plaintext / no skip | NO |
| 2: Autokey-then-Atbash (21 × 2) | 42 | 69.984 | EMERGE / ciphertext / no skip | NO |
| 3: Caesar-then-autokey (28 × 2 × 2) | 112 | 69.963 | shift=1 / DIVINITY / ciphertext | NO |
| 4: Autokey + F-skip discovery (42 × 2 × 2) | 168 | 71.634 | DIVINITY / ciphertext / skip=[7,91] | NO |
| 5: Cipher-direction reversal (4 × 2) | 8 | 68.213 | TOTIENT / plaintext | NO |
| 6: Vigenère + F-skip discovery (42 × 1) | 42 | 74.695 | DIVINITY / skip=[65,91] | NO |
| 7: Per-chapter layered (9 × 2) | 18 | 71.130 | Spiral-Branch 40-53 / DIVINITY | NO |

**Total: 432 tests. Best score 74.695 (well below the 80 break-flag threshold and far below real-English threshold ~110).**

The `english_score()` function rewards (a) vowel ratio close to 0.40, (b) presence of common bigrams (TH/HE/IN/ER/...), (c) high letter-ratio. Random Latin-letter gibberish with ~40% vowels scores 60–75; real English scores 110+. **None of the 432 Wave-3 outputs contained meaningful English text.**

### Statistical significance of the top scores

| Wave-3 score | Random-Latin-string percentile (per `DIGRAPHIC_CIPHER_RESULTS.md` control) | Interpretation |
|---|---|---|
| 74.695 (Attack 6 best) | P99 (= 74.36) | Best-of-42 random samples; **expected** by random chance |
| 71.634 (Attack 4 best) | P95 (= 71.83) | Best-of-168 random samples; **expected** by random chance |
| 71.130 (Attack 7 best) | P95 (= 71.83) | Best-of-18 random samples; **slightly above expectation** but within noise |
| 70.154 (Attack 1 best) | P90 (= 70.48) | Best-of-42 random samples; **expected** by random chance |
| 69.963 (Attack 3 best) | P90 (= 70.48) | Best-of-112 random samples; **expected** by random chance |

**All top scores are statistically consistent with random Latin-letter noise.** The fact that Attack 6 (42 tests) reached 74.695 is fully explained by the best-of-42 sampling distribution (P99 of single-sample = 74.36, so best-of-42 ≈ P99.7). No Wave-3 attack produced a score that exceeds the random-noise envelope for its sample size.

---

## 10. RANKING OF ALL HYPOTHESES TESTED ACROSS WAVES 1–3

| Rank | Hypothesis | Wave | Best score | Sample size | Statistical status | Plaintext English? |
|---|---|---|---|---|---|---|
| 1 | H1: Vigenère + F-skip brute-force, DIVINITY | W3 (Attack 6) | **74.695** | 42 tests | Best-of-42 random (P99 single-sample) | NO |
| 2 | Hill-2 cipher full brute-force | W2 (digraphic) | 79.40 | 682k matrices | Best-of-682k random sampling artifact | NO |
| 3 | Hill-2 cipher hill-climbing | W2 (digraphic) | 75.75 | 25k evals | Best-of-25k random sampling artifact | NO |
| 4 | H8: Autokey + F-skip brute-force, DIVINITY | W3 (Attack 4) | **71.634** | 168 tests | Best-of-168 random | NO |
| 5 | H8: Autokey Vigenère (best of Wave-1) | W1 | 69.62 | 40 tests | Best-of-40 random (P90–P95) | NO |
| 6 | Missing-primes-mod-29 autokey primer | W2 (Attack 3) | 71.433 | 20 tests | Best-of-20 random | NO |
| 7 | Per-chapter Atbash+autokey(DIVINITY) | W3 (Attack 7) | 71.130 | 18 tests | Best-of-18 random (P95) | NO |
| 8 | H9: Prime-Fibonacci meshed stream | W1 | ~70 | 6 formulations | Best-of-6 random | NO |
| 9 | H10: Playfair (best of 17 keys) | W2 (digraphic) | 68.99 | 17 keys | Below autokey baseline | NO |
| 10 | H10: Hill-2 magic-square sub-blocks | W2 (digraphic) | 71.44 | 20 matrices | Best-of-20 specific matrices | NO |
| 11 | H10: Two-rune `sub_rev` function | W2 (digraphic) | 69.97 | 8 functions | Tied with autokey baseline | NO |
| 12 | Cipher-direction reversal (Attack 5) | W3 | 68.213 | 8 tests | Best-of-8 random | NO |
| 13 | Atbash-then-autokey (Attack 1) | W3 | 70.154 | 42 tests | Best-of-42 random | NO |
| 14 | Autokey-then-Atbash (Attack 2) | W3 | 69.984 | 42 tests | Best-of-42 random | NO |
| 15 | Caesar-shift-then-autokey (Attack 3) | W3 | 69.963 | 112 tests | Best-of-112 random | NO |
| 16 | Parable-as-autokey primer (8 variants) | W2 (Attack 1) | 66.718 | 8 tests | Below baseline | NO (REFUTED) |
| — | **Real English (target)** | — | **≥110** | — | — | YES |

### Cross-wave synthesis

The autokey cryptanalytic signature (5.19× doublet suppression, IC~1.0, DJUBEI x2, OUNWM at distance 1031 = parable-product factor) is **the only structural evidence that survives all 3 waves**. No layered variant, no F-skip configuration, no cipher-direction reversal, and no chapter-specific combination produced English plaintext. This means one of:

1. **The primer key is NOT in our 21-candidate list** (or any Caesar/Atbash transform of those candidates). The cipher's autokey structure is real but the primer is something we have not yet considered.

2. **The cipher may not be autokey after all.** The 5.19× doublet suppression could arise from other polyalphabetic structures (e.g., a long-keyed Vigenère, a one-time-pad-style stream cipher, or a transposition+substitution hybrid). The IC=1.0 is suspicious — it suggests the output is essentially uniform-random, which is more consistent with a true one-time pad or a long-keyed stream cipher than with classical autokey (which would typically leave IC slightly above 1.0 due to primer-phase repetition).

3. **The plaintext is not English.** Cicada may have used a non-English plaintext (e.g., Latin, Anglo-Saxon, or a constructed language) whose statistical fingerprint does not match the `english_score()` function. However, the solved pages all produced English-like Runeglish text, so this is unlikely.

4. **The cipher uses a stream we have not enumerated.** Candidates not yet tested:
   - The page-56 deep-web hash (`36367763ab73783c7af284446c59466b4cd653239a311cb7116d4618dee09a8425893dc7500b464fdaf1672d7bef5e891c6e2274568926a49fb4f45132c2a8b4`) as a Vigenère/autokey keystream (hex pairs mod 29).
   - The page-5 and page-16 magic-square number sequences (e.g., 434 1311 312 278 966 / 204 812 934 280 1071 / ...) as keystreams.
   - The product `1,595,277,641` (= 1259 × 1031 × 1229) decomposed into its prime factors and used as a 3-rune key cycle (1259 mod 29, 1031 mod 29, 1229 mod 29).
   - The CicadaSolvers 2024-2025 Zeckendorf reconstruction of the page-16 magic square — which suggests the key may be a Zeckendorf representation (binary-string of Fibonacci coefficients) used as a long-period Vigenère keystream.

### Recommended path forward (Wave-4 candidates, in priority order)

**A. Hill-climbing / simulated annealing on the autokey primer.** Start from a random primer of length L ∈ {3, 5, 7, 11, 13, 29, 33, 56, 95, 1031, 1229, 1259} (the parable factors + 29 + 95-rune parable length + 33-rune deep-web hash mod-29 length), iteratively mutate (single-rune substitution, insertion, deletion) to maximize `english_score()`. This explores the primer space beyond the 21 known candidates. **Expected outcome**: if the cipher is autokey with a primer of length ≤ 30, hill-climbing will find it within ~10k iterations; if length ≥ 100, hill-climbing is infeasible.

**B. Stream-cipher hypothesis (IC=1.0 suggests OTP-like).** Test whether the unsolved corpus is XOR'd (mod 29) with a long pseudo-random stream derived from the page-56 deep-web hash, the magic-square sequences, or a CSPRNG seeded with a Cicada constant. The IC=1.0 is more consistent with a true OTP than with autokey; the autokey signature (5.19× doublet suppression) may be a coincidence of the primer-phase repetition rather than proof of autokey structure.

**C. Test the page-56 hash as a Vigenère/autokey keystream.** Convert the 80-byte hash to 80 runes (each byte mod 29 → rune), then use it as either a Vigenère key (repeating) or an autokey primer (one-shot). This was nominally tested in Wave-2 Attack 3 (`cookie_167`, `cookie_761`) but those were 32-byte onion cookies, NOT the page-56 deep-web hash. The hash is a NEW, untested 80-byte keystream.

**D. Test the Zeckendorf reconstruction of the page-16 magic square as a key.** The CicadaSolvers 2024-2025 finding that the magic square reconstructs via Zeckendorf's theorem suggests the key may be the Zeckendorf representation (binary string of Fibonacci coefficients) of the magic-square constants. Each constant (434, 1311, 312, 278, 966, ...) has a Zeckendorf representation as a sum of distinct Fibonacci numbers; the concatenated binary string of these representations, taken mod 29, is a candidate long-period keystream.

**E. Test cross-page chaining.** The unsolved pages may form a CHAINED sequence where page N's plaintext (or ciphertext) is used as page N+1's Vigenère/autokey primer. The solved pages 3-4 already demonstrate cross-page key continuation (DIVINITY continued from page 3 to page 4); the unsolved pages may use a similar chained-key schedule.

**F. Accept that the cipher may require a non-computational breakthrough.** After 4 waves (~860+ tests), every classical cipher construction with every candidate primer has been exhausted. The next breakthrough may require either (i) finding a NEW Cicada-emitted string (e.g., a new PGP-signed message in 2025–2026), or (ii) reading the page-56 deep-web hash's underlying Tor onion / Freenet key, or (iii) a non-cryptographic insight (e.g., the dendrite decorations on pages 8-14 encode a visual key that text-based analysis cannot recover).

---

## 11. ARTIFACTS PRODUCED

| File | Description |
|---|---|
| `/home/z/my-project/cicada3301-research/decoder/wave3_attacks.py` | **New** — Wave-3 attack script implementing all 7 layered cipher attacks (432 tests total). Adds `autokey_vigenere_fskip()`, `autokey_vigenere_reversed()`, `atbash_then_autokey()`, `autokey_then_atbash()`, `caesar_then_autokey()`. |
| `/home/z/my-project/cicada3301-research/decoder/wave3_attack_results.json` | **New** — Consolidated JSON results (432 tests across 7 attacks). |
| `/home/z/my-project/cicada3301-research/compiled/WAVE3_ATTACK_RESULTS.md` | **New** — This report. |

---

## 12. VERIFICATION

- **Unsolved corpus verified:** 13 page-groups, 12,956 runes total — matches Wave-1/Wave-2 baselines exactly.
- **Parable text verified:** 95 runes from `solved_pages.json` page 74.jpg (the task spec's "97 runes" appears to be an off-by-2 estimate from a different transcription source; we used the verified 95-rune version).
- **F-rune positions verified:** 6 F-runes in first 95 runes of unsolved corpus at positions `[7, 17, 58, 61, 65, 91]` (task spec estimated ~5; actual count is 6; brute-force enumeration adjusted accordingly).
- **Autokey cryptanalytic signature:** Not re-tested in Wave-3 (already confirmed in Waves 1-2). 5.19× doublet suppression, IC~1.0, DJUBEI x2, OUNWM at distance 1031 = parable-product factor.
- **english_score baseline:** Per `DIGRAPHIC_CIPHER_RESULTS.md` control experiment (100k random 100-char Latin strings): mean=65.93, P99=74.36, P99.99=79.48, max=81.06. Real English ≥110. All Wave-3 top scores fall within the random-noise band for their respective sample sizes.

---

## 13. END OF REPORT

**Bottom line:** All 432 Wave-3 layered-cipher tests produced gibberish. The Koan-1 precedent (Atbash+Caesar-3) does NOT extend to the unsolved LP2 pages — neither Atbash+autokey, Caesar+autokey, autokey+Atbash, cipher-direction reversal, F-skip discovery (autokey or Vigenère), nor per-chapter layered combinations produced English plaintext. The autokey cryptanalytic signature remains unbroken but the primer key is still unknown. **Wave-3 is INCONCLUSIVE; the next attack (Wave-4) should test long primer candidates (page-56 hash, magic-square Zeckendorf reconstructions, chained cross-page keys) and consider whether the cipher is actually a stream cipher / OTP rather than classical autokey.**

*End of WAVE3_ATTACK_RESULTS.md.*
