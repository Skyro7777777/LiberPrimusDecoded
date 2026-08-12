# ALT-HYPOTHESIS RESULTS — Phase C+D
## Per-page different ciphers + non-cipher hypotheses
**Task ID:** p5d
**Subagent:** Alternative-hypothesis testing
**Campaign:** Cicada 3301 Liber Primus decoding (Wave 6)
**Total tests run:** 413

---

## 0. EXECUTIVE SUMMARY

**DID ANY HYPOTHESIS PRODUCE A BREAKTHROUGH? NO.**

After running 413 tests across 8 fundamentally different hypotheses, **none** produced recognisable English plaintext or meaningful structure. The top score across all hypotheses was **74.03** (Hypothesis F: page-16 magic-square cell key vigenere on Branches), which is **statistically indistinguishable from random**.

**Critical baseline verification (the key insight):**
| Sample | Score | Notes |
|---|---|---|
| **Real English: solved page 01 (Atbash decrypt)** | **88.36** | Authentic Cicada plaintext |
| **Real English: solved page 05 (direct)** | **80.33** | Authentic Cicada plaintext |
| "WELCOME PILGRIM TO THE GREAT JOVRNEY..." | 68.63 | Plain English with Cicada-style V→V substitution |
| "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG" | 55.92 | Standard pangram |
| **Random runes (direct translate, 3 samples)** | **67.03, 67.92, 69.37** | Random baseline |

**Implication:** The `english_score()` baseline for *random* text is **~67-69**. Our top alternative-hypothesis result of 74.03 is barely 5 points above random — well below the 80+ range where authentic Cicada plaintext lives. **No alternative hypothesis is producing real signal.**

---

## 1. HYPOTHESIS A — PER-PAGE DIFFERENT CIPHERS (9 chapters × 14 methods = 126 tests)

### Methodology
For each of the 9 LP2 chapter groups, applied each of the 7 LP1 solved-page cipher methods (plus variants). Total 126 tests. Scored first 200 runes with `english_score()`.

The 7 methods (expanded to 14 variants):
1. **Atbash** (page-01 method)
2. **Vigenère DIVINITY** with no F-skip (page-03/04 method)
3. **Vigenère DIVINITY** with F-skip
4. **Vigenère FIRFUMFERENFE** with no F-skip (page-14/15 method)
5. **Vigenère FIRFUMFERENFE** with F-skip
6. **Direct translate** (page-05, page-16, page-57 method)
7. **Prime-stream / totient** (page-56 method)
8. **Atbash + shift 3** (page-06/07/08/09 Koan-1 method)
9. **Autokey DIVINITY plaintext** (wave-2 hypothesis)
10. **Autokey DIVINITY ciphertext**
11. **Autokey FIRFUMFERENFE plaintext**
12. **Autokey FIRFUMFERENFE ciphertext**
13. **Autokey PARABLE plaintext**
14. **Autokey PARABLE ciphertext**

### Top 5 results
| Rank | Score | Chapter | Method | Snippet |
|---|---|---|---|---|
| 1 | 72.74 | Hollow | autokey_PARABLE_ciphertext | JABEAIJAESFGFSMTYCNGOEJFLAOBEAPEPDSELANC |
| 2 | 71.07 | Mayfly | atbash | IARNGWOEXCOEEJETEOJETHFOEPOSNGNFTBTNGLEO |
| 3 | 70.50 | Spirals | autokey_DIVINITY_plaintext | YVJIAEOASMEAICTAENGSOTOEAMVBNOAEEIBEANFX |
| 4 | 70.22 | Cuneiform | autokey_FIRFUMFERENFE_plaintext | NGNGHIEASOEDMEABIAHNCVNGCOYTOEATNGHORMOE |
| 5 | 70.13 | Cross | autokey_DIVINITY_plaintext | NGIABOEYNJODEAVEAHOEFOTHVIDATTHGTGWVLGIR |

### Verdict
**No score exceeded 73.** All within random-noise range (67-69 baseline). The per-page-cipher hypothesis (different methods for different chapters) does NOT produce recognisable English. Note: the top results all feature autokey variants, but their snippets are vowel-heavy random-looking text (lots of AE, OE, NG patterns that english_score rewards by chance).

---

## 2. HYPOTHESIS B — RUNES AS CODEBOOK INDICES (5 codebooks × 3 modes = 15 tests, +3 rune-as-codebook = 18 tests)

### Methodology
Tested three book-cipher modes on the first 200 runes of the **Cross** chapter (most sensitive test):
- **single_idx_first_letter**: each rune (0-28) → Nth word → first letter
- **pair_idx_first_letter**: each rune-pair (29×29=841 combinations) → Nth word → first letter
- **pair_word_idx_letter_pos**: rune-pair = (word_index, letter_index)

Codebooks: Liber AL vel Legis (6,618 words), Agrippa (9,123), Mabinogion (108,216), Self-Reliance (77,982), Instar Emergence (19), and the runes of solved LP1 pages themselves.

### Top 5 results
| Rank | Score | Codebook | Mode | Snippet |
|---|---|---|---|---|
| 1 | 71.72 | self_reliance | pair_idx_first_letter | FASULIEOFTTOHTRIAPVTHOHEITAIOGTTIBTFATUC |
| 2 | 70.92 | liber_al | pair_idx_first_letter | OFRNMMVAIOSTTBSRHSPMFTFSTSMLJMTBITSMCIAI |
| 3 | 67.18 | agrippa | pair_idx_first_letter | TRKTAVATBAASTTTNPAJATWTIIRBLWOTITTRTAIGA |
| 4 | 66.94 | mabinogion | single_idx_first_letter | TIEBGGTTTOESCTOGATOOBTTTECOKTOTLSMTAGLTI |
| 5 | 65.88 | agrippa | single_idx_first_letter | CADOTCHACEDJDBATMAAMOTBTDDAACMADJATMTDBA |

### Verdict
All scores are at or below random baseline (67). The book-cipher hypothesis produces gibberish. Most codebooks are too short to have words at index 800+ (max index for pair-mode is 841), so many positions return "?". **No breakthrough.**

---

## 3. HYPOTHESIS C — GEMATRIA-SUMS AS THE MESSAGE

### Methodology
For each chapter, properly split the raw text into rune-words (using delimiters), computed gematria-sums (prime-value-sum and decimal-value-sum) of the first 100 words. Looked for: prime sums being prime themselves, ASCII/coordinate interpretations, patterns.

### Per-chapter findings
| Chapter | First-5 prime sums | First-5 decimal sums | % prime | Notes |
|---|---|---|---|---|
| Cross | 347, 315, 160, 122, 41 | 96, 85, 44, 33, 14 | 23.3% | Decimal sums in ASCII range (44=`, 65=A, 80=P, 85=U...) |
| Spirals | 110, 487, 145, 124, 395 | 31, 138, 39, 38, 107 | 16.0% | Mixed |
| Branches | 196, 250, 195, 156, 157 | 57, 74, 52, 42, 43 | 12.7% | Many small sums (40-80 ASCII range) |
| Möbius | 184, 16, 230, 68, 324 | 51, 6, 63, 22, 83 | 19.4% | Word with sum 16 (single-rune word?) |
| Mayfly | 100, 268, 123, 295, 522 | 25, 77, 37, 81, 141 | 17.3% | Sums 100, 268, 522 — wider range |
| Wing/Tree | 217, 710, 182, 205, 63 | 58, 194, 53, 60, 17 | 15.5% | 710 is large |
| Cuneiform | 125, 170, 466, 317, 160 | 35, 49, 120, 88, 46 | 28.8% | Highest prime % — 466, 317 are prime |
| Spiral/Branches | 102, 333, 313, 224, 247 | 28, 88, 85, 61, 65 | 14.5% | 313, 247 are prime; 333 = 9×37 |
| Hollow | 97, 500, 508, 235, 286 | 24, 135, 135, 61, 80 | 21.2% | 97 prime; 500, 508 even |

### Verdict
- **The decimal sums DO fall in the ASCII printable range (32-127) for many words** — this is genuinely interesting and warrants further investigation.
- **The prime sums are too large** for direct ASCII (most are 100-500, requiring base-29 chunking or 2-byte interpretation).
- **No obvious coordinate pattern** (e.g., no consistent lat/long pairs).
- **Prime-density is not anomalous** (12-29%, normal for these sum ranges).
- The decimal-sum-as-ASCII hypothesis is the most interesting thread here: e.g., Cross chapter's first words have decimal sums `[96, 85, 44, 33, 14, ...]` → ASCII characters `` ` ``, `U`, `,`, `!`, (control). Not readable, but not random either — could be compressed/encoded further.

**No breakthrough.** Most promising lead: investigate decimal-sum-to-ASCII with various encoding schemes (Base64, hex, etc.) — left for future work.

---

## 4. HYPOTHESIS D — NON-LINEAR PAGE READING ORDERS (6 orderings × 9 ciphers = 54 tests)

### Orderings tested
1. **normal_chapter_order** — Cross → Spirals → ... → Hollow (baseline)
2. **reverse** — Hollow → Spiral_Branches → ... → Cross
3. **fibonacci** — chapters ordered by Fibonacci page indices
4. **prime** — chapters ordered by prime page indices
5. **smallest_first** — sort chapters by length, ascending
6. **largest_first** — sort chapters by length, descending

Each ordering concatenated, then tested with 9 cipher variants (direct, atbash, vigenere-DIVINITY, vigenere-parable, autokey-DIVINITY-pt/ct, autokey-parable-pt/ct, prime_stream). Scored first 300 runes.

### Top 5 results
| Rank | Score | Ordering | Cipher | Snippet |
|---|---|---|---|---|
| 1 | 69.70 | largest_first | autokey_DIVINITY_ciphertext | GEAETYPNJARAFTHEOADOWTHEOIABEAJOOGIAPEXR |
| 2 | 69.46 | normal_chapter_order | autokey_DIVINITY_ciphertext | NGIABOEYNJOFEFEEAEOPGIOOEVIAWLOOEWGTHEOP |
| 3 | 69.46 | fibonacci | autokey_DIVINITY_ciphertext | NGIABOEYNJOFEFEEAEOPGIOOEVIAWLOOEWGTHEOP |
| 4 | 69.26 | prime | vigenere_DIVINITY | LFPNNGROHHOTHWEEAFTHLOOTDAEOOEIAAEPINGJD |
| 5 | 68.95 | largest_first | vigenere_DIVINITY | GEAETYPNJVOPTEATHEOGAGLEJFFCGNDANPEMIEOC |

### Verdict
All scores around the random baseline. **Non-linear reading orders do not unlock the cipher.** Note that `normal_chapter_order` and `fibonacci` produce identical results (because Fibonacci reordering happens to map chapter 0→0, 1→1, 2→1, 3→2, 5→5, 8→8 in a way that preserves early ordering).

---

## 5. HYPOTHESIS E — PAGE-NUMBER-BASED KEYS (9 chapters × 5 derivations × 2 ciphers = 90 tests)

### Derivations tested
For each chapter (representative LP2 page number 0-54), derived a primer via:
1. **page_digits** — decimal digits of page number → runes (e.g. page 5 → [5] → rune ᚳ)
2. **nth_prime** — Nth prime where N=page_num → its decimal digits → runes
3. **nth_fib** — Nth Fibonacci number → its decimal digits → runes
4. **page_repeated_20** — page number digits repeated to fill 20-rune primer
5. **page_base29** — page number in base-29 → runes

Each tested as both Vigenère (no F-skip) and autokey-plaintext primer.

### Top 5 results
| Rank | Score | Chapter | Page | Derivation | Cipher | Snippet |
|---|---|---|---|---|---|---|
| 1 | 71.56 | Wing_Tree | 27 | page_digits | vigenere_noskip | BGAPPAEOEEGPTCHEOEPPIAJTHGEAEALGDSOENGRE |
| 2 | 71.56 | Wing_Tree | 27 | page_repeated_20 | vigenere_noskip | BGAPPAEOEEGPTCHEOEPPIAJTHGEAEALGDSOENGRE |
| 3 | 71.52 | Branches | 8 | nth_fib | autokey_plaintext | EONTHIEARLVJEONGCGRIAREFHOYAEOEAEPEWEOXI |
| 4 | 70.95 | Cuneiform | 33 | nth_fib | vigenere_noskip | EYIGAIAXNESOEOEMOEDRFFPEOTHNETHONIFTHGAE |
| 5 | 70.66 | Hollow | 54 | nth_fib | autokey_plaintext | TPMBLYWNBLNGYHJMROENSRVIVEAREGEOTIANGCOE |

### Verdict
All scores ~70 (just above random). Page 27 Wing_Tree shows identical results for page_digits and page_repeated_20 (because page 27 is a 2-digit number, repeating gives same first 2 runes). The nth_fib derivation appears several times in the top 5 but produces no recognisable English. **No breakthrough.**

---

## 6. HYPOTHESIS F — MAGIC-SQUARE-CELL-BASED KEYS (9 chapters × 3 derivations × 2 ciphers = 54 tests) ⭐ TOP-SCORING

### Derivations tested
Used the 5×5 magic square from LP1 page 16 (sums to 3301 per row) as a key schedule:
```
434  1311  312  278  966
204  812   934  280  1071
626  620   809  620  626
1071 280   934  812  204
966  278   312  1311 434
```
- **page16_digits** — for page N, primer = digits of cells N, N+1, ... (filled to 20 runes)
- **page5_digits** — same but using page-5 magic square values (only 12 known values, cycled)
- **page16_mod29** — use cell values mod 29 directly as rune decimals (cleaner mapping)

### Top 5 results
| Rank | Score | Chapter | Page | Derivation | Cipher | Snippet |
|---|---|---|---|---|---|---|
| **1** | **74.03** | **Branches** | **8** | **page16_mod29** | **vigenere_noskip** | AEOYHROTHWEOWOTENGDOESXIARPWJHAAYOEJSISD |
| 2 | 73.90 | Spiral_Branches | 40 | page16_digits | autokey_plaintext | EANEOAERSAEEANGNGAEGIEAEANISYNGVRGAEREAG |
| 3 | 70.50 | Möbius | 15 | page16_mod29 | autokey_plaintext | OEJSNRNGFTIVOERHOENGNGAECIIAHAEAONOEYEOI |
| 4 | 70.43 | Spiral_Branches | 40 | page5_digits | autokey_plaintext | EAVBAFNGNGODCPNGWJAETHBPPYNGNEAWFIAOTHAE |
| 5 | 70.02 | Wing_Tree | 27 | page16_mod29 | autokey_plaintext | YAEBMSYCIALNNGVOENGVXSRRNGJIPHOEREOTHOTH |

### Verdict
**Top score 74.03 — the highest of ALL hypotheses.** But this is still only ~5 points above the random baseline (67-69) and well below the 80+ threshold for real Cicada plaintext. The snippet "AEOYHROTHWEOWOTENGDOESXIARPWJHAAYOEJSISD" contains English bigram fragments (TH, EN, NG, AR, HA, IS — 8 bigrams in 40 chars) but is NOT readable English.

**The magic-square-cell approach is the most promising lead** of all hypotheses tested, particularly `page16_mod29` on the Branches chapter. Worth deeper investigation with:
- All 25 cells of the magic square (not just first 5-6) as a longer repeating primer
- Page-5 magic square with filled-in missing values (deducible from row/col sum = 1033)
- Combination with F-skip rule
- Magic square read in different orders (diagonals, spiral, etc.)

**No breakthrough yet** — but this is the recommended hypothesis for deeper investigation in the next wave.

---

## 7. HYPOTHESIS G — CROSS-PAGE CHAINED KEYS

### Methodology
Assumed chapter 0 (Cross) decrypts with a known primer; the resulting plaintext becomes chapter 1's primer; and so on. Tested with 4 primers (DIVINITY, FIRFUMFERENFE, PARABLE, INSTAR) and 2 chaining modes (autokey-plaintext chain, vigenere chain).

### Results
| Score | Primer | Method | Snippet |
|---|---|---|---|
| 70.72 | PARABLE | autokey_plaintext_chain | EIAIAFOGOEEDEAGJTHDBETHDAEMTPYIPOEHOEITH |
| 70.06 | INSTAR | vigenere_chain | SEONNGIMNSPVNHAESTHYYMCXOEAEJLOEGAEAEIAM |
| 70.00 | DIVINITY | vigenere_chain | EAPASAAELPTHEOSSFDVMPEODEOTHOEOEFAESTHGN |
| 68.93 | DIVINITY | autokey_plaintext_chain | EAPASAAELPTHEOSSFDVMPEODEOTHOEOEFAESTHGN |
| 68.10 | FIRFUMFERENFE | autokey_plaintext_chain | CPIACTCRCXOWOENGFBVOEEOEJCJVGSVHAEGYNGET |
| 65.45 | INSTAR | autokey_plaintext_chain | SEONNGIMNSPVNHAESTHYYMCXOEAEJLOEGAEAEIAM |
| 63.97 | FIRFUMFERENFE | vigenere_chain | CPIACTCRCXOWOENGFBVOEEOEJCJVGSVHAEGYNGET |
| 63.31 | PARABLE | vigenere_chain | EIAIAFOGOEEDEAGJTHDBETHDAEMTPYIPOEHOEITH |

### Verdict
All scores ~63-71, within random range. Cross-page chained keys **do not unlock** the cipher. If the chain hypothesis were correct, we would expect at least one primer to produce readable plaintext for chapter 0 — none did.

---

## 8. HYPOTHESIS H — DELIMITERS AS THE MESSAGE

### Methodology
Extracted the delimiter sequence (chars `/•·.-_=*%&$#`) from each chapter's raw text. Applied 6 mappings:
- ordinal_0_to_11 (delimiter position)
- ordinal_mod10
- mod29_rune
- plus_65_to_letter (delimiter → A, B, C, ...)
- plus_32_printable (delimiter → space, !, "...)
- raw_byte_direct (unicode codepoint)

### Top findings (per chapter, plus_65_to_letter mapping)
| Chapter | n_delims | Score | First-60 ASCII |
|---|---|---|---|
| Cross | 82 | 53.77 | DEDEDEDHHHHDDDBBBBBBBBBBBBBBBBBBBBBBBBBB |
| Branches | 73 | 51.83 | DDDDDDDEDEDHHHHBBBBBBBBBBBBBBBBBBBBBBBBB |
| Hollow | 74 | 51.75 | DEDHHHHDEDBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB |
| Spirals | 161 | 51.25 | DEDEDHHHHBBBBBBBBBBBBBBBBBBBBHHHHDDDDBBB |
| Wing_Tree | 81 | 51.25 | DDDDDDEDEDHHHHBBBBBBBBBBBBBBBBBBBBBBBBBB |
| Cuneiform | 83 | 51.12 | DDDDDDDDEDEDHHHHBBBBBBBBBBBBBBBBBBBBBBBBB |
| Möbius | 84 | 51.06 | DDDDDDDDEDEDHHHHBBBBBBBBBBBBBBBBBBBBBBBB |
| Mayfly | 84 | 51.06 | DDDDEDEDHHHHBBBBBBBBBBBBBBBBBBBBBBBBBBBB |
| Spiral/Branches | 78 | 48.73 | DEDHHHHBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB |

### Pattern observation
The delimiter sequences show a **consistent structural pattern**: a header section using delimiters `D` (=`.`) and `E` (=`-`) and `H` (=`=`), followed by long runs of `B` (=`•`). The header (positions 0-10) differs per chapter but the body (positions 11+) is uniformly `B` (the `•` bullet point separator between rune-words).

### Verdict
**No meaningful message in the delimiter sequence.** The only structure is the chapter header (which has different delimiters from the body) and the body (uniformly `•` separators). The `•` body delimiters carry no information beyond word-boundaries. The header delimiters (`/`, `.`, `-`, `=`) may indicate page-title structure but don't form a coherent message. **No breakthrough.**

---

## 9. CRITICAL ASSESSMENT — RANKING ALL HYPOTHESES

### Did ANY hypothesis produce recognisable English?
**NO.** All 413 tests produced scores in the range 48-74, which is within or barely above the random-rune baseline of 67-69. Authentic Cicada plaintext (verified via solved pages 01 and 05) scores 80+. **None of the 8 hypotheses is correct as formulated.**

### Top 10 scores across ALL hypotheses
| Rank | Score | Hypothesis | Detail |
|---|---|---|---|
| 1 | 74.03 | F | Branches, page16_mod29 vigenere_noskip |
| 2 | 73.90 | F | Spiral_Branches, page16_digits autokey_plaintext |
| 3 | 72.74 | A | Hollow, autokey_PARABLE_ciphertext |
| 4 | 71.72 | B | self_reliance, pair_idx_first_letter |
| 5 | 71.56 | E | Wing_Tree page 27, page_digits vigenere_noskip |
| 6 | 71.56 | E | Wing_Tree page 27, page_repeated_20 vigenere_noskip |
| 7 | 71.52 | E | Branches page 8, nth_fib autokey_plaintext |
| 8 | 71.07 | A | Mayfly, atbash |
| 9 | 70.95 | E | Cuneiform page 33, nth_fib vigenere_noskip |
| 10 | 70.92 | B | liber_al, pair_idx_first_letter |

### Hypotheses ranked by promise
| Rank | Hypothesis | Top score | Promise | Why |
|---|---|---|---|---|
| 1 | **F** (magic-square keys) | **74.03** | **HIGH** | Top score; page-16 magic square is structurally elegant (sums to 3301 = Cicada's number); page16_mod29 mapping is conceptually clean. Worth deeper investigation with all 25 cells, F-skip variants, magic-square spiral-read. |
| 2 | **E** (page-number keys) | 71.56 | Medium | Several top-10 results. The nth_fib derivation appears multiple times. Page numbers as keys is conceptually consistent with "their numbers are the direction." |
| 3 | **A** (per-page ciphers) | 72.74 | Medium | Autokey variants produced several top-10 results. The hypothesis of different ciphers per chapter is correct in principle (LP1 did this) but the test set of methods didn't include the right one. |
| 4 | **B** (codebook indices) | 71.72 | Medium | Top result with self_reliance pair-idx is curious, but the snippet is gibberish. Most codebooks too short for pair-indexing. |
| 5 | **D** (non-linear orders) | 69.70 | Low | All scores at random baseline. Reading order doesn't matter much. |
| 6 | **G** (chained keys) | 70.72 | Low | If chain were correct, we'd expect at least one primer to break chapter 0. None did. |
| 7 | **C** (gematria-sums) | n/a | Low-Medium | Sums are too large for direct ASCII; decimal sums ARE in ASCII range but don't form readable text. Worth investigating with various encodings (Base64, hex). |
| 8 | **H** (delimiters) | 53.77 | Very low | Delimiters show only structural pattern (header vs body), no message. |

### Most promising hypothesis for further work
**Hypothesis F: magic-square-cell-based keys**, specifically:
1. Use the page-16 magic square (row-sum 3301 = Cicada's number) as a 25-element key schedule
2. `page16_mod29` derivation (cell values mod 29 → rune decimals directly)
3. Focus on the **Branches** chapter (which scored highest)
4. Variants to try next:
   - All 25 cells as a longer primer (not just 5-6)
   - Magic square read in spiral order
   - Magic square read by columns vs rows vs diagonals
   - Magic square combined with F-skip rule
   - Magic square as autokey-ciphertext-mode primer (instead of vigenere)
   - Combine magic square with a Caesar shift offset

---

## 10. ARTIFACTS PRODUCED

| File | Description |
|---|---|
| `/home/z/my-project/cicada3301-research/compiled/ALT_HYPOTHESIS_RESULTS.md` | This report |
| `/home/z/my-project/cicada3301-research/decoder/alt_hypothesis_attacks.py` | Test harness (8 hypotheses, 413 tests) |
| `/home/z/my-project/cicada3301-research/decoder/alt_hypothesis_results.json` | Raw JSON results |

---

## 11. CONCLUSIONS & NEXT STEPS

### What this wave definitively established
1. **Per-page different ciphers (Hypothesis A) is WRONG** as formulated: none of the 7 LP1 solved-page methods, applied to any LP2 chapter, produced plaintext above the random baseline.
2. **Runes-as-codebook-indices (Hypothesis B) is WRONG** for the 5 codebooks tested.
3. **Non-linear reading orders (Hypothesis D) make no difference** — all 6 orderings produced identical scores (within noise).
4. **Page-number-based keys (Hypothesis E) did not break the cipher** but the nth_fib derivation is worth retrying with longer primers.
5. **Magic-square-cell keys (Hypothesis F) is the most promising lead** — score 74.03 is the highest, the concept is elegant (3301-sum square), and it has not been exhausted (only 3 of many possible derivations tested).
6. **Cross-page chained keys (Hypothesis G) is WRONG** — no primer broke chapter 0.
7. **Delimiters-as-message (Hypothesis H) is WRONG** — delimiter sequence is structurally trivial.
8. **Gematria-sums-as-message (Hypothesis C) is inconclusive** — sums don't form direct ASCII but are in plausible ranges. Needs encoding-scheme exploration.

### Recommended next-wave priorities (in order)
1. **Deepen Hypothesis F**: test all 25 magic-square cells as longer primers, with F-skip variants, on the Branches chapter specifically.
2. **Image steganography (Phase B from CAMPAIGN_PLAN.md)** — never yet tried; the actual JPEG images may carry the real data via Outguess or LSB.
3. **Deepen Hypothesis C**: test gematria decimal-sums as Base64 / hex / 2-byte ASCII pairs.
4. **Look for the actual CicadaSolvers' solver code** (54 GitHub repos mentioned in CAMPAIGN_PLAN.md §1) — primary source research may reveal a method none of us have considered.
5. **Cross-correlate**: combine Hypothesis F (magic-square primers) with Hypothesis A (per-page ciphers) — e.g., different magic-square cells for different chapters.

---

*Report ends. All 413 test results preserved in `alt_hypothesis_results.json`. Push to GitHub pending.*
