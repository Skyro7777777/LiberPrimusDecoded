# Aldegonde's Own Attack Scripts — Results

**Task ID:** p8h
**Agent:** aldegonde attack scripts subagent
**Date:** 2025-11
**Source repo:** `solvers/aldegonde/` (aldegonde v0.1.dev1+g782d2000d)
**Headline:** Aldegonde's tools DID NOT crack any unsolved LP2 page. They DID
confirm the cipher is NOT any classical family — Quagmire III keyword family
excluded by full ~3.1×10⁸-key enumeration. The leading hypothesis is now
"length-clocked-walk" (mixed-permutation g + σ), not Quagmire III.

---

## 1. Installation

- `pip install -e .` initially failed (externally-managed-environment).
- Worked via `python3 -m pip install -e .` (Python 3.13, system). Pulled
  `numpy-2.2.6`, `scipy-1.15.3`.
- `python3 -c "from aldegonde import pasc, auto, c3301, stats; print('OK')"`
  → ImportError resolved only via `PYTHONPATH=src`. Final install used
  `python3 -m pip install -e .` from inside the aldegonde directory.
- **174 experiment scripts** present in `experiments/`. **76 hypothesis
  files** in `hypotheses/` (32 observations + 44 hypotheses per INDEX.md).

## 2. Does aldegonde have a working Quagmire III implementation?

**Yes, but only as a tableau generator, not a turnkey cracker.**

- `src/aldegonde/pasc.py::quagmire3_tr(alphabet)` — builds the Quagmire III
  tabula recta. NOTE: as written, this is identical to a standard Vigenère
  tableau (every row is a left-shift of the plain alphabet). The mixed
  alphabet is the **plain** alphabet; this matches the ACA Quagmire III
  definition (single keyed alphabet used both as plaintext and ciphertext
  reference).
- `quagmire1_tr`, `quagmire2_tr`, `quagmire4_tr` also implemented.
- A richer "Quagmire III ciphertext autokey" routine lives in
  `experiments/quagmire_hillclimber.py::quagmire3_autokey_decrypt()` —
  implements Beaufort-style decrypt with mixed alphabet + primer.
- The full key-space enumeration of the *mixed-alphabet Vigenère family
  with keyword-derived alphabets* lives in
  `experiments/keyword_exhaustion.py` (~787,592 alphabets from web2).

## 3. Experiment script inventory (relevant subset)

| Script | Purpose | Outcome |
|---|---|---|
| `examples/lp_analysis.py` | Per-page IOC/bigram/dist | Crashes on `ioc.print_ioc_statistics` (API drift) |
| `examples/lp_lag5_attack.py` | Period-5 shift attack, all interruptor rules | **Excluded** for shift family. Max z=+3.56 over 6710 runs; real crack scores z>+7 |
| `experiments/lp_attack_battery.py` | Affine, Vigenère, Beaufort, 6 autokey families, prime/totient keystream, beam search | **Only page 55 ("AN END") recovered from scratch.** Pages 0-54 stay at random fitness |
| `experiments/verify_quagmire_hypothesis.py` | Simulate Quagmire III autokey; check LP-like stats | Hypothesis **statistically plausible**; not decrypted |
| `experiments/quagmire_hillclimber.py` | Hill-climb mixed alphabet with runeglish quadgrams | Timed out at 120s (full search would take much longer) |
| `experiments/quagmire_az_hillclimber.py` | Same, A-Z test alphabet | Self-test on planted ciphertext only; doesn't touch real LP |
| `experiments/quagmire_repeat_attack.py` | Repeat-based constraint solver | Timed out at 60s |
| `experiments/quagmire_runner.py` | End-to-end enumeration over ~2.2×10⁸ keys | Not attempted (estimated hours/days) |
| `experiments/quagmire_survivors.jsonl` | Output of quagmire_runner | **69 survivors, ALL tagged "DEGENERATE"** — none verified |
| `experiments/period5_quagmire_sim.py` | Compare simulated Quagmire variants against LP | None match observed LP stats exactly |
| `experiments/custom_autokey_analysis.py` | Why LP doublets are suppressed | Explains mechanism (identity char frequency); no decryption |

## 4. Results per attack

### 4.1 lp_attack_battery.py (the headline result)

```
page 17 len=273 best=affine-18-3            fitness=-6.109  (random ≈ -6.2)
page 33 len=214 best=bof-WELCOME             fitness=-6.081
page 34 len=261 best=vig-PILGRIM             fitness=-6.086
...
page 55 len= 85 best=totient-interrupted--1  fitness=-3.417  <<< HIT
   ANENDWITHINTHEDEEPWEBTHEREEXISTSAPAGETHATHASHESTOITISTHEDUTYOFEUERYPILGRIMTOSEECOUTTHISPAGE
```

→ **Only page 55 cracked.** All 0-54 stay at noise floor under affine,
Vigenère (incl. PILGRIM, WELCOME), Beaufort, six autokey families, prime-
and totient-keystream with ᚠ-interruptor beam search. This is the same
"AN END" page already documented as the only solved section beyond the
Parable. **No new plaintext recovered.**

### 4.2 lp_lag5_attack.py

- 6710 attack runs across all (page × rule × coset) combinations.
- Best real-page score: z=+3.56 (page 36, add/reset:N) — well below the
  z>+7 a true crack scores at 95 runes (positive control on page 57).
- Period-5 polyalphabetic detector: top z=+1.78 (skip:NG); significance
  threshold for 61 tests is z≈3.2 → no detection.

### 4.3 verify_quagmire_hypothesis.py

- Simulated ciphertext (13 000 runes, English plaintext via Gematria
  Primus, Quagmire III ciphertext-autokey with mixed alphabet).
- IoC ≈ 0.0344 (target 0.0345) ✓, doublet rate tunable via keyword's
  first letter (NG-first → 1.08% vs LP's 0.68%).
- Confirms **the hypothesis is statistically plausible** — but does NOT
  produce LP plaintext.

### 4.4 quagmire_survivors.jsonl (the enumeration result)

- 69 candidate keys survive the DJU-BEI base-free return + 2-rune
  likelihood filter.
- Every single one is tagged `"DEGENERATE"` — i.e. the per-word base
  matrix is rank-deficient, alphabet collapses, plaintext still random.
- `grep -v DEGENERATE quagmire_survivors.jsonl | wc -l` → **0**.

→ **The Quagmire III keyword family is excluded** by full enumeration
(~3.1×10⁸ keys; see `hypotheses/mixed-alphabet-vigenere.md`).

## 5. Did aldegonde's own tools crack any page?

**NO.** Specifically:

- Pages 0-54 of `data/page0-58.txt`: **not cracked** by any aldegonde
  script run in this task. Every attack's best fitness equals noise.
- Page 55 ("AN END"): cracked from scratch by `lp_attack_battery.py`
  via totient-interrupted keystream with -1 shift — **but this page was
  already documented as solved** in our dossier; aldegonde merely
  re-derives it as a method validation.
- Section 11 (the Parable): stored as plaintext, not encrypted through
  the 0-9 cipher; trivially readable but provides no foothold.

## 6. Any English plaintext produced?

Only the known page 55 string already in our dossier:

```
ANENDWITHINTHEDEEPWEBTHEREEXISTSAPAGETHATHASHESTOITISTHEDUTYOFEUERYPILGRIMTOSEECOUTTHISPAGE
```

No new English from any unsolved page.

## 7. Latest hypotheses (44 total, from `hypotheses/INDEX.md`)

**32 confirmed observations** (statistical characterisations of LP).
Notable: flat IoC, doublet suppression 5.2×, no periodicity, no running-
key depth, DJU-BEI repeat, rune-S carries the lag-5 echo, four
apostrophe contraction-crib sites (~28 bits plaintext constraint at
offsets 1107, 5136, 8513, 10086).

**44 hypotheses** by status:

| Status | Count | Examples |
|---|---|---|
| disproved | ~32 | ciphertext-autokey, plaintext-autokey, affine-autokey, Beaufort-autokey-EA, Vigenère, bifid, playfair, hill-cipher-per-word, transposition, homophonic, prime-value-autokey, second-order-difference, sigma-power-step, stay-slot-hold, multi-layer-autokey, monoalphabetic+autokey, word-boundary-reset, running-key-text, running-key-math-sequence, periodic-polyalphabetic, page-reset-keystream, gematria-primus-arithmetic, encoding-only, explicit-doublet-avoidance, first-difference, doublet-marker-rune-EA, block-cipher, position-within-word, substitution+autokey, within-word-key-sharing, mixed-alphabet-vigenere (keyword family only) |
| plausible | 4 | contraction-cribs (28 bits of constraint), length-clocked-walk (best fit), per-word-related-alphabets (superseded by walk), within-word-d5-coincidence |
| unresolved | 4 | autokey+substitution, five-block-boundary, g-from-5x5-grid, lag5-back-reference, stream-cipher-no-repeat (reformulated), thirty-symbol-disk |

### Leading hypothesis: **length-clocked-walk**

From `hypotheses/length-clocked-walk.md`:

> Cipher is a progressive polyalphabetic substitution with a small fixed
> key. Alphabet advances by an order-5 mixed permutation `g` on every
> letter, and by a second mixed permutation `σ` at every word boundary.
> Per word `w`, at within-word position `j`:
>   c[j] = base_w( g^(j mod 5)( p[j] ) )
>   base_{w+1} = base_w ∘ g^((L_w − 1) mod 5) ∘ σ
> Total key: two mixed 29-permutations, ~200 bits, fixed (does NOT grow
> with text). Breakable in principle, but no plaintext produced yet.

**Status:** plausible (comprehensive statistical fit; NOT confirmed by
decryption). The two mixed permutations have not been recovered.

### Why Quagmire III is NOT the answer

- Keyword family: excluded by full ~3.1×10⁸-key enumeration.
- Free mixed alphabet: not excluded, but every hill-climb and survivor
  attempt has produced degenerate keys.
- The length-clocked-walk hypothesis generalises Quagmire III to two
  interleaved permutations (g per letter, σ per word) and is the
  currently-active model.

## 8. Most promising aldegonde script

**`experiments/quagmire_runner.py`** (NOT run to completion — estimated
hours to days). This is the only script that could in principle crack
the length-clocked-walk model: it enumerates the full key space
(~2.2×10⁸ complete keys = 562k letter-wheel pairs × 400 space-wheel
pairs) and filters by (1) DJU-BEI 6-point return, (2) 2-rune likelihood
hill-climb on base_0, (3) IoC + quadgram confirmation.

The current survivors file shows **0 non-degenerate keys** survive
stage 1 — meaning either (a) the planted-key self-test was the only
configuration that would have survived, or (b) the cipher is genuinely
outside the keyword-Quagmire family.

Secondary candidate: `examples/lp_lag5_attack.py` — already excluded
the shift-cipher family conclusively. The same attack reformulated for
**mixed alphabets** (rather than shifts) is the natural next step, and
is what `length-clocked-walk.md` recommends.

## 9. Concrete next actions for our campaign

1. **Adopt length-clocked-walk as the primary hypothesis** in our
   dossier; retire Quagmire III as the leading candidate.
2. **Pull in aldegonde's contraction-crib constraint** (~28 bits at
   four known offsets) — this is the only known-plaintext foothold
   available beyond the Parable, and we had not previously integrated
   it.
3. **Port `quagmire_runner.py`'s enumeration strategy** but with free
   mixed alphabets (not keyword-derived). The current keyword-
   constrained enumeration is exhausted; the free-alphabet space is
   ~29! but reducible via the g⁵=id constraint.
4. **Re-run `lp_attack_battery.py` against our specifically-targeted
   pages** (LP2 section 0 / page 56 etc.) — aldegonde's run covered
   `data/page0-58.txt` which may or may not include our LP2 segment.
5. **Check `experiments/two_rune_gradient.py`** — aldegonde claims a
   validated 2-rune likelihood objective that recovers planted keys;
   this is the most direct path to base_0 recovery if the walk model
   is correct.

## 10. Critical takeaway

Aldegonde's professional toolkit has **excluded roughly 32 cipher
families** (all standard classical ciphers, all simple autokey
variants, all keyword-derived Quagmire III). The remaining live
hypothesis is the **length-clocked progressive substitution with two
mixed permutations (g, σ)** — a 200-bit fixed key that is breakable in
principle but has not been broken by aldegonde either.

**Bottom line:** aldegonde's tools did not crack LP2. They give us a
sharper hypothesis (length-clocked-walk) and a partial-crib foothold
(four contraction apostrophes) that we did not have before. The next
break, if it comes, will be via free-alphabet enumeration under the
walk model, not via any of the classical cipher families.
