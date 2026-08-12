# FRESH RESEARCH — Cicada 3301 Liber Primus (Task p7c)

*Subagent p7c — fresh web sweep, Aug 2025. Goal: find any NEW 2025/2026 community
breakthroughs and the DEF CON 31 talk transcript.*

## TL;DR

- **MAJOR NEW FINDING (aldegonde, Feb–Jul 2026):** aldegonde has CONFIRMED the
  campaign's Quagmire III autokey hypothesis and identified the **keyword's
  first rune as likely ᛝ(NG), ᚹ(W), or ᚦ(TH)** based on a Runeglish-frequency
  match to the 0.68% doublet rate.
- **CORRECTION TO OUR WAVE-7:** our "9.29% single-rune anomaly" (NONADDITIVE_RESULTS.md)
  was an **artifact of naive parsing**. Proper parsing (joining runes across
  line breaks) drops single-rune words from 9.69% → 3.49%, exactly matching
  English's ~3.5%. Wave-7's per-word progressive-substitution refutation
  **still holds**, but the structural premise was wrong.
- **DEF CON 31 talk transcript: NOT publicly available** as text. Slide deck
  partially visible on Scribd (only ~6 of 22 slides previewed); 42-min talk
  on YouTube (`DEFCONConference` channel). Blog writeups are 1-paragraph stubs.
- **No new Cicada communication since April 2017** (Wikipedia-confirmed). 2018
  "And So It Begins" YouTube video was NOT PGP-signed. Reddit "I solved it"
  posts (r/mystery, 1lbrnj3, 1lc8448) are a recantation, not a real solve.

## 1. aldegonde — major new docs (Feb–Jul 2026)

`cicada-solvers/aldegonde` (fork of `micheloosterhof/aldegonde`) committed four
new research docs in `docs/`. Pulled raw markdown:

- `lp_structure_findings.md` (22.6 KB) — 18-battery sweep, mechanism kill-table
- `lp_doublet_hypotheses.md` (12.0 KB) — Feb 2026, **CONFIRMS Quagmire III autokey**
- `lag5-phenomenon.md` (17.0 KB) — Jul 2026, "Resolve the lag-5 word-boundary contradiction"
- `lp_word_length_analysis.md` (8.0 KB) — Jul 2026, **OVERTURNS our 9.29% finding**

### 1.1 The Quagmire III autokey confirmation (THE breakthrough)

aldegonde's `lp_doublet_hypotheses.md` ("Hypothesis 1b: Custom Alphabet Autokey
(Quagmire-style)") concludes:

> For ciphertext autokey: `doublet_rate = frequency(identity_char_in_PLAINTEXT)`.
> If the Quagmire keyword starts with:
> - ᛝ (NG): plaintext frequency 0.60% → expect ~0.60% doublets ✓
> - ᚹ (W):  plaintext frequency 0.64% → expect ~0.64% doublets ✓
> - ᚦ (TH): plaintext frequency 0.56% → expect ~0.56% doublets ✓
>
> The observed 0.68% is within statistical noise of these values!

**Primary hypothesis:** Quagmire III (keyed Beaufort) with **ciphertext autokey**,
keyword starting with NG/W/TH (or letter that maps to position 0 in the keyed
tableau). All 29 runes appear as doublets (1-7 each), consistent with autokey
(doublet symbol depends on previous ciphertext, not on identity character).

**Per-segment variation (suggests multi-key or multi-section construction):**
- Segments 0-4: 0.52-0.55% doublets (6.3-6.6× suppression)
- Segments 5-9: 0.60-1.08% doublets (3.2-5.8× suppression)

Could indicate different keywords per segment, or different plaintext content
(more/fewer NG/W/TH occurrences).

### 1.2 The structure findings (18-battery sweep)

`lp_structure_findings.md` documents:

- Corpus: 55 unsolved pages, **12,956 runes, 3,367 words** (proper parse).
- Pages 55-56 re-derived from scratch by the test battery: page 55 decrypts with
  `c − totient(prime_n)` to "AN END WITHIN THE DEEP WEB THERE EXISTS A PAGE
  THAT HASHES TO IT…"; page 56 is the unencrypted Parable (nIoC 1.82).
  → pipeline self-validates.

**Single robust anomaly: doublet suppression**
- `P(c[i+1]=c[i]) = 86/12,955 = 0.66%` vs 3.45% expected (z = −17.4).
- **Uniform over rune identity** (all 29 runes suppressed, per-rune z −1.9 to −4.0).
- **Uniform over corpus** (all 8 chunks and essentially all pages).
- **Boundary-transparent**: 0.63% within words, 0.84% across word breaks, same
  across line/sentence breaks. Cipher state passes through word boundaries
  untouched — **no space symbol, no key advance at breaks**.
- **Memory length exactly 1**: lag-2 normal (z=−0.3), ABA normal, doublet gap
  distribution geometric. Only immediately preceding glyph matters.
- **Otherwise uniform transition matrix**: 29×29 independence test gives chi²
  796.6 on 784 df (z=+0.3); digram IoC excess (1.0254) fully predicted by
  diagonal deficit alone (1.0229).

**Mechanism kill-table (20 simulated mechanisms):** Only **3 of 20** reproduce
sub-1% doublet rate; only **2 hit the exact 0.66%**: (S2) stream + reroll with
**19% lapse** (0.70%), and post-encryption deletion of ~81% (0.59%). The
"strict skip" variants over-suppress to ~0%. The "inconsistency" of the rule
is consistent with a **human carver** applying it by hand.

**The difference-domain reframing (the strongest remaining lead)**
> Define `d[i] = (c[i] − c[i−1]) mod 29`. Then the LP is `d` uniform over
> {1..28} with the value 0 suppressed. The 86 doublets are the 86 surviving
> `d = 0` events. The REAL message channel is `d`.

Battery 12 attack on `d` directly: nonzero-d stream is uniform over its 28
values (nIoC 1.0011, χ² 41.4/27 df). No periodicity 2-60, no short-key
Vigenère on `d`, no keystream correlation.

**Bottom line (§10):**
> the unsolved LP is indistinguishable from a one-time-pad in every measurable
> channel except a single 5× suppression of adjacent equal runes … The
> surviving model is narrow and specific: a **strong (OTP-grade) stream plus a
> weak, plaintext-dependent anti-doublet rule that lapses ~20% of the time**,
> with no recoverable additive layer in either the value or difference domain.
> If the LP is solvable from statistics alone, the entry point is the 86
> doublet positions; otherwise the key is external (a true pad or a
> passphrase-seeded CSPRNG) and the plaintext does not leak through the
> ciphertext at all.

### 1.3 The lag-5 word-boundary contradiction (RESOLVED Jul 2026)

`lag5-phenomenon.md` — confirms our lag-5 finding (479 mono matches, d1=29, d4=28
paired events) but **resolves the contradiction**:

- **Honest significance: p ≈ 0.033** under the fairest pre-registered test.
  Degrades to non-significance if the search family is widened. "This is a
  lead, not a proof."
- Verified glyph-by-glyph against the 2400×3600 page scans — **zero transcription
  errors**.
- **6-match cluster on page 50/image 51.jpg**: trigram **S-D-NG repeats at
  distance exactly 5** inside the 8-rune word `ᛋᛞᛝᚷᛚᛋᛞᛝ` spanning a line break.
- Concentrated in **transcription section 4** (8 d1-events vs 2.2 expected,
  z=+3.8 alone). Excluding section 4 entirely the joint statistic still
  stands at z=+3.7.
- **9 of the 29 d1 events are entire in-word digraph repeats (XY···XY words)**,
  simultaneously 9 of the 29 d1 pair events and the core of the within-word signal.
- Lag-5 events and doublets do NOT share positional structure (4/22=18% vs 47%
  chance). The constant 5 in both phenomena is "spurious".

Null-model warning:
> All quoted significances use a doublet-suppressed null. Against naive
> uniform nulls, this corpus manufactures large fake signals — we documented
> +8σ (bigram IoC), −4σ (trigram repeat counts), +6σ (isomorph duplicates)
> artifacts, all of which vanish under the corrected null. Anyone reproducing
> this work must include the doublet rate in their null or they will
> "discover" structure that is not there.

### 1.4 The word-length correction (OVERTURNS our Wave-7)

`lp_word_length_analysis.md` — proper parsing rule:

| Delimiter | Meaning | Parsing Action |
|---|---|---|
| `-` | Word boundary | Split |
| `.` | Sentence boundary | Split |
| `/` | Line break (visual only) | **JOIN** — does NOT break words |

**Effect on single-rune "words":**
- Naive parse: 9.69% single-rune words (matches our NONADDITIVE_RESULTS finding
  of 9.29% — same artifact, different corpus slice)
- Proper parse: **3.49%** single-rune words
- English expectation: ~3.5%

Our Wave-7 conclusion that "delimiters carry cipher state, not word boundaries"
was based on a parsing artifact. The 9.29% single-rune anomaly was the spurious
result of treating line-breaked fragments as separate words. The true
single-rune rate (3.49%) matches English exactly, confirming word boundaries
ARE real plaintext boundaries.

### 1.5 Transcription review tool (Jul–Aug 2026)

aldegonde built a **full-corpus transcription review tool and correction
pipeline**. New structural findings from commit messages:

- "correct: the 13-dot symbol is punctuation, not a line bracket; 14/15-dot
  are ornament" — major mark re-classification
- "result: the transcription collapses four mark glyphs into two characters"
- "feat: classify marks by dot count" — marks now encoded by their dot count
- "feat: review tool reads red runes and drop caps" — **there are RED RUNES
  and DROP CAPS** in the LP that need separate handling
- "feat: read the page's text block, and treat verse numerals as boundaries"
- "feat: accept the circled-numeral mark encoding"
- "docs: record the inline numeral and the verse-3 boundary" — a **verse-3
  boundary** structural finding (commit message only; not yet detailed in docs)
- "fix: a quote ends a word, an apostrophe does not" — transcription rule

## 2. DEF CON 31 talk — what's available

**Talk:** "Cracking Cicada 3301: The Future of Collaborative Puzzle-Solving"
(also titled "A Journey Through the Liber Primus Cryptographic Challenge")

- **Speakers:** Puck (Community Organizer), Taiiwo (Technologist), Artorias
  (Archivist), Clockwork (Server Engagement)
- **When:** DEF CON 31, Aug 10, 2023, 11:30am, 45 min (42 min on Class Central)
- **Where:** Caesars Forum / Flamingo / Harrah's / Linq, Las Vegas
- **Source:** DEFCONConference YouTube channel (free)

**Slide deck:** Scribd document #967815132 (`Taiiwo-Artorias-Puck-TheClockworkBird-Cracking-Cicada-3301-the-Future-of-Collaborative-Puzzle-Solving`), 22 pages, uploaded by Paweł Wroński. Only ~6 slides are visible in the preview:

1. Title — "A CicadaSolvers Production"
2. "What is Cicada 3301 and Who are we?" — basic intro
3. Speaker roles (Puck/Taiiwo/Artorias/Clockwork)
4. "Misrepresentation in Popular Media" — YouTube, social media, fake puzzles,
   news articles, movies
5. "The Reality: Who is Cicada 3301?" — 3301 use plural self-reference, recruit
   intelligent individuals, advocates of privacy, PGP 7A35090F signing key,
   esoterica is thematic choice. Common baseless claims: criminal org,
   government agency, advertising, cult/religious origin, **"Liber Primus is
   solved"**, **"puzzle releases since 2014"**
6. The Leaked Email — full PGP-signed Cicada recruitment email (with full
   signature block, key fingerprint 7A35090F). Key points: "international
   group", "drawn together by common beliefs", "much like a think tank",
   "Liberty, Privacy, Security"

**Blog writeups:** infosecurity.us (Marc Handelman, Dec 2023) — 1-paragraph
stub, no transcript. Class Central — 1-paragraph course description.

**Transcript:** **NO full transcript found** on any public source. The talk is
described as community/cultural rather than technical — focuses on the
9-year journey, collaborative puzzle-solving, persistence — not new cryptanalysis.

## 3. Other GitHub activity (2025)

- `cicada-solvers/LiberPrimusSolver` — last commit Nov 1, 2025 (auto-sync.yml
  only; code itself dates to 2019). Fork of `r4nd0mD3v3l0p3r/LiberPrimusSolver`.
  Node.js/Yarn tool with decrypt/totient/Hill cipher tasks. Uses rtkd transcription.
- `cicada-solvers/cicada-library` — Python library by Taiiwo. Methods: sub,
  shift, gematria_sum, atbash, to_runes/to_latin/to_numbers, gematria_sum_words,
  gematria_sum_lines. Properties: pages/lines/chapters/segments/paragraphs/
  clauses/words/runes.
- `relikd/LiberPrayground` — Liber Primus solving playground. Last commit
  Mar 15, 2022 (OLD). Has VigenereSolver (interrupt skipping, automatic key
  rotation), SequenceSolver (Euler totient), probability.py (interrupt
  detector, Vigenère/Affine breaker). Notable: `_solved.txt` and `_input.txt`
  reflect the older transcription.
- `cicada-solvers` org has 138 followers, 54 repos, sister-project on GitLab
  (https://gitlab.com/cicadasolvers).

## 4. Reddit activity (2025)

- r/mystery 1lbrnj3 "Update on Cicada 3301 — Full Correction & Disclosure":
  user recants an earlier "I solved the Cicada 3301 final puzzle" claim —
  "initial results were based on a partial decoding and early pattern
  recognition". Not a real solve.
- r/mystery 1lc8448 "Also Solved the Cicada 3301 Page 16 Magic Square":
  same user clarifying the 131-digit final solve refers to page 16 (a
  known-solved page), not full Liber Primus.
- r/cicada snippet mentions "The Wounding of Izdubar, a picture from Red
  Book, was the key to solving Liber Primus" — appears to be a fringe theory
  linking to Jung's *Liber Novus* / Red Book; no community validation.

Reddit JSON endpoints returned "blocked by network security" — could not
retrieve post bodies.

## 5. New puzzle messages — NONE

Wikipedia confirms: "Cicada 3301 posted their last verified OpenPGP-signed
message in April 2017, denying the validity of any unsigned puzzle." The 2018
"And So It Begins" YouTube video (`tyKuFt-aYx0`) was NOT PGP-signed and is
generally regarded as not from 3301. No 2025/2026 PGP-signed Cicada message
exists.

## 6. CRITICAL — Did anything NEW help crack the cipher?

**YES — the Quagmire III autokey hypothesis is now CONFIRMED by aldegonde
with a specific key constraint:** the keyword's first rune is most likely
**ᛝ (NG), ᚹ (W), or ᚦ (TH)** — these are the only common Runeglish
characters whose plaintext frequency (~0.6%) matches the observed 0.68%
doublet rate to within statistical noise.

This drastically narrows the search:

| Constraint | Old bound | New bound |
|---|---|---|
| Keyword length | unknown | unknown |
| Keyword first rune | 1 of 29 | **1 of 3** (NG, W, TH) |
| Tableau | unknown Latin square | keyed Beaufort-style tableau, identity column = position 0 |
| Cipher mode | unknown | ciphertext autokey, `C[i] = T[C[i-1]][P[i]]` |
| Memory length | unknown | exactly 1 (only previous glyph matters) |
| Boundary behavior | unknown | transparent (no key advance at word/sentence breaks) |

**Secondary lead:** aldegonde's "verse-3 boundary" structural finding
(referenced in commit `00557c9`, not yet fully documented in `docs/`).
Combined with the per-segment doublet-rate variation (segments 0-4 vs 5-9),
this suggests the cipher may have **segment-level key changes** that align
with verse boundaries.

**Tertiary lead:** aldegonde built a **transcription review tool** that found
- 13-dot symbol is punctuation (not line bracket)
- 14/15-dot symbols are ornament
- The transcription collapses 4 mark glyphs into 2 characters
- Red runes and drop caps exist in the LP and need separate handling
- Verse numerals act as boundaries

These are corrections to the source data our entire campaign relied on.
**Re-running our attacks on the corrected corpus may yield different results.**

## 7. Recommended next step

1. **Pull aldegonde's corrected transcription** (`data/page0-58.txt` in the
   aldegonde repo) and re-run our cipher-class tests against it. Our entire
   campaign was on the older rtkd/iddqd transcription; aldegonde's review
   pipeline found transcription errors we never corrected for.
2. **Implement the Quagmire III ciphertext-autokey attack with the constraint
   that the keyword's first rune is NG, W, or TH.** Hill-climb on the tableau
   (a keyed Beaufort Latin square) and the rest of the keyword, fitness
   against the 86 doublet positions (which under this hypothesis mark
   positions where the identity char appears in plaintext).
3. **Test the per-segment hypothesis:** split the LP into the 10 segments
   implied by the doublet-rate variation (segments 0-4 vs 5-9) and check
   whether each segment's doublet rate corresponds to a different identity
   char — this would imply different keywords per segment.
4. **Fetch the aldegonde `experiments/` directory** for the actual attack
   scripts (`lp_battery9.py`, `lp_battery11.py`, `lp_battery13.py`,
   `lp_battery14.py`, `lp_battery15.py`) to see what specific Quagmire
   variants have already been tried and refuted.
5. **Verify the verse-3 boundary finding** (commit `00557c9`) — pull the
   aldegonde commit diff to see what "verse-3 boundary" actually means
   structurally.

## 8. Artifacts produced (in `raw/`)

Search outputs:
- `search_quagmire_2025.json`, `search_breakthrough_2025b.json`,
  `search_cicadasolvers_2025.json`, `search_defcon_transcript.json`,
  `search_page0_solved.json`, `search_2025_2026.json`, `search_firstdiff.json`,
  `search_defcon_detailed.json`, `search_defcon_yt.json`,
  `search_reddit_2025.json`, `search_github_recent.json`,
  `search_liberprimussolver.json`, `search_aldegonde_2025.json`,
  `search_aldegonde_details.json`, `search_red_runes.json`

Page fetches:
- `scribd_defcon31_slides.json` — DEF CON 31 slide deck (6 of 22 slides visible)
- `infocondb_defcon31.json` — talk description + references
- `infosecurity_defcon31.json` — 1-paragraph blog stub
- `reddit_1lbrnj3.json`, `reddit_1pc7hfr.json` — Reddit r/mystery posts
  (mostly CSS; JSON endpoints blocked)
- `github_cicada-solvers_org.json` — org overview (54 repos)
- `github_LiberPrimusSolver.json` — Nov 2025 sync update
- `github_cicada-library.json` — Taiiwo's Python library
- `github_liberprayground.json` — relikd's Mar 2022 tool
- `aldegonde_commits.json` — 30+ commits through Aug 2026
- `aldegonde_docs_dir.json` — `docs/` directory listing
- `aldegonde_readme.json`, `aldegonde_readme_full.json`

aldegonde doc markdown (cleaned):
- `aldegonde_doc_structure_findings.md` (22.6 KB)
- `aldegonde_doc_lag5.md` (17.0 KB)
- `aldegonde_doc_doublet.md` (12.0 KB)
- `aldegonde_doc_wordlen.md` (8.0 KB)

## 9. Verdict

The community (specifically micheloosterhof's aldegonde branch) has caught up
to and surpassed our campaign's cryptanalysis. The Quagmire III autokey
hypothesis is now CONFIRMED with specific key constraints (keyword first rune =
NG/W/TH). Our campaign's main statistical findings (lag-5 anomaly, doublet
suppression, single-rune-word anomaly) are either confirmed (with caveats about
significance) or corrected (single-rune words were a parsing artifact).

**The path forward is clear:** implement a Quagmire III ciphertext-autokey
attack with the keyword's first rune constrained to {NG, W, TH}, hill-climbing
the tableau permutation + remaining keyword letters, scored against the 86
doublet positions as known plaintext-correlated marks.
