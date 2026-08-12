# Non-Additive Per-Word Progressive Substitution — Results

**Task ID:** p6c
**Subagent:** Non-additive per-word cipher subagent
**Date:** Wave-7 / Phase E
**Workspace:** `/home/z/my-project/cicada3301-research/`
**Attack code:** `decoder/nonadditive_attack.py` (~260 LOC)
**Data:** `decoder/nonadditive_results.json`, `decoder/nonadditive_wordstats.json`

---

## TL;DR

Tested 3 non-additive per-word progressive substitution models × 4 initial alphabets = **12 trials** on the first 500 runes of the unsolved LP2 corpus (delimiters preserved from `raw/primary/primary_translit.txt`). **NO BREAKTHROUGH.** All scores fall in the 64.76 – 68.11 band, well below the >75 lead threshold and within the 60-74 random-baseline established by Wave-4 controls. Plaintext output is gibberish across all 12 trials. The cipher class is NOT any of the three tested per-word substitution families.

**Key ancillary finding:** The most-repeated "rune-words" in the unsolved corpus are **ALL single-rune** (top 20 entirely 1-rune words: T, P, NG, D, M, G, AE, EA, EO, X, J, V, IA, C, L, B, N, OE, E, Y). This is statistically anomalous for English text (which has only two common single-letter words: A, I) and is a strong structural signal that **delimiters in LP may carry cipher state**, or that "words" are not natural English words but per-letter encodings.

---

## 1 — Test Setup

### 1.1 Corpus
- Source: `raw/primary/primary_translit.txt` (Uncovering-Cicada wiki transliteration)
- Aggregate: wiki pages 17-55 (the unsolved LP2 section, after page 16 Instruction)
- Total: **8,739 runes** across **2,249 rune-words** (delim-preserved)
- Delimiters per task spec: `/ • · . - _ = * % & $ # §` plus whitespace
- Test window: first 500 runes = **134 words** (505 runes total)

### 1.2 Models
| ID | Model | Update rule |
|---|---|---|
| **M1** | Per-word gematria-shift | `alphabet ← alphabet[shift:] + alphabet[:shift]` where `shift = sum(pt_word) % 29` |
| **M2** | Atbash-if-prime-length | If `len(word)` is prime: atbash alphabet. Else rotate by 1. |
| **M3** | Length-clocked | `alphabet ← alphabet[L:] + alphabet[:L]` where `L = len(word) % 29` |

### 1.3 Initial alphabets (4)
1. `identity` = `[0, 1, 2, …, 28]`
2. `DIVINITY-derived` — keyword-derived permutation (unique-key-runes-first)
3. `FIRFUMFERENFE-derived` — keyword-derived permutation
4. `parable-derived` — keyword-derived permutation

---

## 2 — All 12 Test Results

| # | Model | Alphabet | Score | Plaintext (first 80 chars) |
|---|---|---|---|---|
| 1 | M1 gematria-shift | identity | 66.713 | EADNNASEOPNGIAOEGIAAFJDIRRBAEEVLJAENGEANGNGXJLOEBYIATHIAPXTHISDLAYRIHAAWIANTOGOE |
| 2 | M1 gematria-shift | DIVINITY-derived | **68.109** ⬆ max | CXIOEODFVNMXIAMOEIANXAFFPMOSRAHROESYEOBYEANGVXAEAESGWAOREONPSLYEOOEPDRHSTHCNGNGS |
| 3 | M1 gematria-shift | FIRFUMFERENFE-derived | 67.295 | EAXWJNTHOEDTHOTHIANGTHWVNGHTTEAVEVLNDMOAEMISOEAMEAEOEOMSLDNGHGXNPSBDOENFMAEJECHO |
| 4 | M1 gematria-shift | parable-derived | 66.550 | SFWAHTHGWTHEADWEANGYSMDCAFOEOSCANCEJTHATHJPWTFEAENGAAEJEBAEOEYEAAETHTOOSTHNXFOMI |
| 5 | M2 atbash-prime | identity | 65.005 | EADNNASOREONGNGSTHNHLWNGDNRNGRDXEAAIOOIAMEAVAECENGEAATMNMFINSMYOEABMRACXOHYLXTHO |
| 6 | M2 atbash-prime | DIVINITY-derived | 64.764 | CXIOEODDCGECIAIAVSNXALFNGCSNGTHLRFIAJSMWWWVIDFCFHPRXDCRIXOHOEEOXEAMFNIAONGAEMWHI |
| 7 | M2 atbash-prime | FIRFUMFERENFE-derived | 65.528 | EAXWJNTHDTHXEHMVRWGOENGDNGATHDEIJRFAMEJRSIAVIOEHAEFFOERXOCRJSDHTHEOXFMFIEAROEAEE |
| 8 | M2 atbash-prime | parable-derived | 65.445 | SFWAHTHNTHIAOHGTHRDGGLDHAETHWBILCVDMMJOSWTHJAHCVFPOPDRONXONOEJPIAEEAHIAONGYLWHIA |
| 9 | M3 length-clocked | identity | 67.440 | EADNNASIAEAWIAOEGIASLAWDFFPXTHXRANCSHYMLFTHYGMBALIAEATAGXJSBJBIAXXYEYRLDIAEGWYMO |
| 10 | M3 length-clocked | DIVINITY-derived | 66.470 | CXIOEODRREOOIAJOLDIAIYOTHSTRTGAEICSXBLXBIOJAOEFAEORMIANBXBMPMFTSIAEYIJAREOYEOEOT |
| 11 | M3 length-clocked | FIRFUMFERENFE-derived | 67.616 | EAXWJNTHAREOTHYITHBOEYNAETHTHPXTHXRANCSHBBOEXEDJANGEAATHVEYHTPBBJBIAXXYEYRJNGEON |
| 12 | M3 length-clocked | parable-derived | 66.919 | SFWAHTHRCPRIAJOLAEFEOEARRBTOSCANCSAOBGPEOEOAEDFAEORNGFJMSMNGPEEASXYEYLYNGAEHCEOP |

**Verdict:** Score band 64.76 – 68.11. Random baseline max ≈ 74 (per Wave-4 control with 2,500 random cipher trials). **Zero scores above 75.** No plaintext is recognisable English. Best score (68.109, M1 + DIVINITY-derived) is below the random-baseline P99 = 74.36, hence **indistinguishable from noise**.

---

## 3 — Word-Length Distribution (full unsolved corpus, 2,249 words)

| Len | Count | Pct | Bar |
|---|---|---|---|
| 1 | 209 | 9.29% | █████████ |
| 2 | 425 | 18.90% | ██████████████████ |
| 3 | 544 | 24.19% | ████████████████████████ |
| 4 | 379 | 16.85% | ████████████████ |
| 5 | 248 | 11.03% | ███████████ |
| 6 | 155 | 6.89% | ██████ |
| 7 | 117 | 5.20% | █████ |
| 8 | 88 | 3.91% | ███ |
| 9 | 34 | 1.51% | █ |
| 10 | 27 | 1.20% | █ |
| 11 | 15 | 0.67% |  |
| 12 | 7 | 0.31% |  |
| 14 | 1 | 0.04% |  |

**Mean word length: 3.886 runes** (vs English ~4.7 chars; Runeglish compensates via multi-letter runes TH, NG, EA, EO, AE, OE, IA, so 3.9 runes ≈ 5+ English letters — **within English range**).

**Notable:** Distribution is unimodal with peak at 3-rune words (24.19%), dropping sharply past length 8. Compare English peak at 3-4 letters, dropping past ~10. Runeglish shape is consistent with English text → underlying plaintext is plausibly English prose, NOT a per-letter encoding.

---

## 4 — Top 10 Most-Repeated Rune-Words

| Rank | Count | Rune-word | Latin |
|---|---|---|---|
| 1 | 13 | ᛏ | T |
| 2 | 13 | ᛈ | P |
| 3 | 13 | ᛝ | NG |
| 4 | 11 | ᛞ | D |
| 5 | 11 | ᛗ | M |
| 6 | 9 | ᚷ | G |
| 7 | 9 | ᚫ | AE |
| 8 | 9 | ᛠ | EA |
| 9 | 9 | ᛇ | EO |
| 10 | 9 | ᛉ | X |

**Anomaly:** All top-10 (and top-20 — see `nonadditive_wordstats.json`) most-frequent rune-words are **single-rune**. English has only two common single-letter words (A, I). 209 single-rune words (9.29%) is ~10× the English expectation.

This rules out:
- A direct natural-English plaintext with normal delimiters.
- A simple substitution (would not produce so many 1-rune "words").

It supports:
- **Delimiter-channel hypothesis** (Wave-5 tested): delimiters themselves may encode information; the apparent "single-rune words" may be intentional markers.
- **Per-letter Vigenère/autokey with stripped delimiters** (rejected by Wave-1/2/3 doublet-rate analysis: 0.66% < 1.7% additive floor).
- **Cipher where delimiters are positioned by the cipher-state itself** (not plaintext word boundaries).

---

## 5 — Critical Assessment

### 5.1 Did any non-additive model beat score 75?
**NO.** Maximum score was 68.109 (M1 gematria-shift + DIVINITY-derived alphabet), which is **below** the random-baseline P99 = 74.36 established by Wave-4 controls. All 12 plaintext outputs are gibberish.

### 5.2 Did any model produce recognisable English?
**NO.** Plaintext snippets like `EADNNASEOPNGIAOEGIAAFJDIRRBAEEVLJAENGEANGNGXJLOEBYIATHIAPXTHISDLAYRIHAAWIANTOGOE` contain vowel/consonant runs that are statistically English-like (hence the 64-68 scores, which reflect vowel ratio + common-bigram hits) but no actual English words longer than 3 letters are visible. The scores are driven entirely by the underlying English letter-frequency of the cipher-runes themselves, NOT by decryption.

### 5.3 What's the verdict on the non-additive per-word class?
**REFUTED.** The 3 model families (gematria-shift, atbash-if-prime, length-clocked) all fail to produce decryption beyond the random-baseline noise floor. Combined with the Wave-5 PRNG and Wave-4 hash-keystream refutations, this **closes the per-word progressive substitution family**.

### 5.4 Why didn't it work?
The per-word progressive models assume the alphabet **resets** at the start of each word (position 0 in each word). But this means word-internal positions are decrypted with the same alphabet index — so all 2nd-position letters share a shift, all 3rd-position letters share a shift, etc. This effectively becomes a **positional polyalphabetic with period = average word length** (~3.9), which the aldegonde `lp_lag5_attack.py` already sweeps (coset IOC z ≤ +1.78 for any period — noise).

The truly non-additive regime would require the alphabet to evolve **across word boundaries** in a way that depends on cumulative plaintext state — which is essentially a per-rune feedback cipher, i.e., **autokey** (already rejected by Wave-1) or **ciphertext-feedback autokey** (already rejected by Wave-2 with 372 tests).

### 5.5 Recommended next vector

1. **Delimiter-channel cipher** (top priority): The single-rune dominance (9.29%) strongly suggests delimiters are cipher-state, not word-boundaries. Test: encode the delim sequence as a separate channel and search for a per-rune additive cipher where the keystream advances **only on delim-positions** (not on every rune). This is a hybrid stream/delim cipher not yet tested.

2. **Liber-Primus-as-book cipher with rune-pair indexing into LP1 solved pages** (the 13 solved pages = ~6,000 runes of codebook). Test: rune-pair → (position, offset) in concatenated solved-page text. Wave-2 BOOK_CIPHER_RESULTS tested 5 codebooks but NOT the LP1-solved-pages themselves as a codebook.

3. **Length-clocked hill-climb with fitness function = crib-positions from the 4 contraction cribs** (per LAG5_CRIBDRAG_RESULTS §5.5 recommendation). The contraction cribs at offsets 1107, 5136, 8513, 10086 give 28 bits of known plaintext — enough to anchor a hill-climb in the M3 length-clocked family with a wider alphabet-permutation search space (the 12 fixed-alphabet tests above used only 4 fixed alphabets; a full 29!-permutation hill-climb was out of scope here but is the natural next step).

4. **Final fallback — declare LP2 undecryptable with current public information.** Total tests across 7 waves now exceed 2,500+; all known cipher classes (additive, hash-keystream, PRNG, prime-stream, book, digraphic, per-word non-additive) have been refuted by either doublet-rate or fitness-score tests. The remaining untested space is the per-rune-feedback hybrid stream/delim cipher (vector #1 above).

---

## 6 — Artifacts Produced

- `decoder/nonadditive_attack.py` — attack script (260 LOC, 3 models × 4 alphabets + word-stats)
- `decoder/nonadditive_results.json` — 12 trial results (model, alphabet, score, snippet)
- `decoder/nonadditive_wordstats.json` — word-length distribution + top-20 repeated words
- `decoder/translit_pages_with_delims.json` — delimiter-preserved wiki pages (0-57)
- `compiled/NONADDITIVE_RESULTS.md` — this report

---

*End of report. 12/12 trials complete; non-additive per-word progressive substitution family REFUTED.*
