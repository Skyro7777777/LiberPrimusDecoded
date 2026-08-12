# LIBER PRIMUS DECODING CAMPAIGN — LIVING PLAN
## A long-term, multi-vector, assumption-questioning decryption effort

**Repo:** https://github.com/Skyro7777777/LiberPrimusDecoded
**Started:** This session
**Status:** Wave 5 complete (~1,328 tests); pivoting to fundamentally different approaches

---

## 0. THE USER'S CRITICAL CORRECTION

The user correctly identified that my initial approach was flawed:
1. **I treated this as a single-shot solve** — but Cicada 3301 has been unsolved for 11+ years despite an 11,168-member solver community.
2. **I assumed my decryption method was right** — but if the method is wrong, no amount of testing variations will work.
3. **The previous 2 Cicada puzzles WERE solved 14 years ago by people** — so it IS possible. Don't give up.
4. **I should research how the 19 solved pages were ACTUALLY decrypted** (primary sources, actual solver code), not just summaries.
5. **I should explore more methods, tools, skills** — including ones I haven't considered.

---

## 1. ASSUMPTIONS TO QUESTION (explicitly)

| # | Assumption I made | Why it might be wrong | Alternative to test |
|---|-------------------|-----------------------|---------------------|
| 1 | The 56 unsolved pages use ONE uniform cipher | LP1 used a DIFFERENT cipher per page-group (Atbash / DIVINITY / FIRFUMFERENFE / direct / prime-stream / Atbash+shift3) | Each LP2 chapter may use a different method — test solved-page methods per chapter |
| 2 | The runes are ciphertext | Cicada's theme is "words are the map, meaning is the road, numbers are the direction" | Maybe runes are CODEBOOK indices, or the gematria-sums ARE the message |
| 3 | The key is a Cicada-emitted string | None of 20+ strings worked | Maybe key is structural: page number, position in book, magic-square cell coordinates |
| 4 | Classical cryptanalysis is the right approach | All ~1,328 classical tests failed | Image steganography (LSB in actual JPEGs) — never tried |
| 5 | I have all the data | I only worked from transcriptions | Never fetched actual JPEGs, never cloned CicadaSolvers' 54 GitHub repos with real solver code |
| 6 | The F-skip rule applies uniformly | Solved pages had different skip patterns | Each page may have its own derivable skip pattern |
| 7 | Pages should be read in order 0→57 | The 2016 message said "follow direction" | Maybe non-linear reading order (the book is a "map") |
| 8 | The plaintext is English/Runeglish | Cicada uses gematria-sums as numbers | Maybe plaintext is coordinates, URLs, or binary data |
| 9 | The cipher operates on individual runes | lp-decrypter repo says "functions of two runes" | Digraphic — but my Playfair/Hill tests failed; maybe a different digraphic |
| 10 | The gematria-sums are decorative | "Their numbers are the direction" | The sums may BE the message (numbers as compass bearings / lat-long) |

---

## 2. CAMPAIGN PHASES

### Phase A — Foundation reset (CURRENT)
- [x] Push existing work to GitHub repo (persistence)
- [ ] Clone ALL CicadaSolvers GitHub repos (54 repos) and study actual solver code
- [ ] Fetch actual Liber Primus page IMAGES (not transcriptions)
- [ ] Deep primary-source research: how were the 19 pages ACTUALLY decrypted?
- [ ] Fetch & transcribe DEF CON 31 talk (42 min, CicadaSolvers leaders)

### Phase B — Image steganography (NEW VECTOR)
- [ ] LSB extraction on the 56 unsolved page JPEGs (multiple bit-plane/channel combos)
- [ ] Outguess with different parameters / passwords
- [ ] Visual analysis of marginalia (Cross/Spirals/Branches/Möbius/Mayfly/Wing-Tree/Cuneiform)
- [ ] Color-channel separation (R/G/B, HSV, YCbCr)
- [ ] JPEG coefficient analysis (DCT domain steganography)
- [ ] EXIF/metadata extraction
- [ ] File carving (look for embedded files in the JPEGs)

### Phase C — Per-page different ciphers
- [ ] For each LP2 chapter, test ALL 5 solved-page methods (Atbash, DIVINITY, FIRFUMFERENFE, direct, prime-stream, Atbash+shift3)
- [ ] Look for chapter-specific clues in marginalia
- [ ] Test page-number-based keys (page N uses primer = decimal digits of N)
- [ ] Test position-based keys (primer = magic-square cell at position N)

### Phase D — Non-cipher hypotheses
- [ ] Runes as codebook indices (each rune = a word in Liber AL / Agrippa / etc.)
- [ ] Gematria-sums as the actual message (sums = numbers = directions)
- [ ] Non-linear page reading order (per "follow direction" instruction)
- [ ] The 5×5 magic squares AS the key schedules (cell values as keystream)
- [ ] Cross-page chained keys (page N's plaintext → page N+1's key)

### Phase E — Automated long-running workflows
- [ ] Genetic algorithms for primer discovery
- [ ] Hill-climbing with longer runtimes (hours, not seconds)
- [ ] Exhaustive brute-force of smaller subspaces
- [ ] GitHub Actions CI for persistent runs
- [ ] Distributed solving via multiple parallel agents

### Phase F — Community engagement
- [ ] Fetch CicadaSolvers Discord archives (if public)
- [ ] Read all r/cicada historical posts
- [ ] Study the DEF CON 31 talk in detail
- [ ] Check for any leaked/solved material in the complete archive (krisyotam/cicada3301, 5,157 files)

---

## 3. VERSIONED MILESTONES

Each phase produces a versioned report pushed to GitHub:
- v0.1 — Foundation (data collection) ✅
- v0.2 — Fresh 2024-2025 findings ✅
- v0.3 — Decoder toolkit + verification ✅
- v0.4 — 5-wave classical attack campaign ✅
- v0.5 — Phase A: Foundation reset (deep primary-source research) ← CURRENT
- v0.6 — Phase B: Image steganography
- v0.7 — Phase C: Per-page different ciphers
- v0.8 — Phase D: Non-cipher hypotheses
- v0.9 — Phase E: Automated workflows
- v1.0 — DECRYPTED (goal)

---

## 4. WHAT "SUCCESS" LOOKS LIKE

Given the user's reminder that the previous 2 puzzles were solved:
- **Success = producing recognisable plaintext** for at least one unsolved LP2 page.
- **Partial success = identifying the correct cipher TYPE** (even if the key is unknown).
- **Methodological success = ruling out a hypothesis conclusively** (which waves 1-5 did for classical ciphers).

The campaign will continue across multiple prompts. Each prompt advances one or more phases. Failures are expected and informative — each ruled-out method narrows the search space.

---

*This is a LIVING document. Update after each phase. Push all changes to GitHub for persistence.*
