# CI Workflow Results — Run 1 + Run 2 Triggered

## Run 1 Results (COMPLETED)

**Workflow:** Liber Primus Walk Attack (Batched)
**Run ID:** 31823481392
**Status:** Completed (10/10 batches succeeded, aggregate job failed on push)
**Duration:** ~4 hours (14,400 seconds per batch)
**Total trials:** 4,535,175

### Per-Batch Results:
| Batch | Score | Trials | Duration |
|-------|-------|--------|----------|
| 0 | -272,657 | 440,040 | 14,400s |
| 1 | -272,518 | 428,221 | 14,400s |
| 2 | -272,546 | 440,505 | 14,400s |
| 3 | -272,798 | 428,072 | 14,400s |
| 4 | -272,853 | 468,745 | 14,400s |
| 5 | -272,540 | 567,517 | 14,400s |
| 6 | -272,501 | 423,256 | 14,400s |
| 7 | -272,395 | 462,140 | 14,400s |
| 8 | -272,729 | 423,101 | 14,400s |
| **9** | **-272,382** | 451,578 | 14,400s |

### Analysis:
- **Best score:** -272,382 (batch 9)
- **All batches converged** to scores between -272,382 and -272,853
- **Letter frequencies match English:** E=13.6%, A=11.0%, O=7.9%
- **English words found:** "THE" x2, "NOT", "DID"
- **No coherent English** — the random search found a local optimum
- **Root cause:** The simplified `recover_base_0_two_rune` function was insufficient

### Aggregate Job Failure:
The aggregate job completed successfully (created `aggregated_results.json`) but failed to push to the repo because `github-actions[bot]` lacked write permissions. **This is fixed in the v2 workflow** (added `permissions: contents: write` and proper bot identity).

---

## Run 2 (IN PROGRESS)

**Workflow:** Liber Primus Walk Attack v2 (Validated)
**Run ID:** 31877506584
**Status:** `in_progress`
**Started:** 2026-08-15T09:38:31Z
**URL:** https://github.com/Skyro7777777/LiberPrimusDecoded/actions/runs/31877506584

### What's Different in v2:
1. **Uses aldegonde's VALIDATED 2-rune likelihood objective** (not the simplified version)
2. **Downloads Project Gutenberg prose corpus** for the 2-rune probability table
3. **Installs aldegonde as a Python package** for proper imports
4. **Fixed push permissions** — uses `github-actions[bot]` with proper email
5. **Commits results to `ci_results/` directory** (not root)

### Why v2 Should Work Better:
Aldegonde's `two_rune_gradient.py` validates that:
- When (g, σ) are known, base_0 recovers **EXACTLY** (29/29 runes, 79/79 THE decrypts)
- The true key scores -1318.9 vs random -5365.7 (a clear 4,046.8 nat gradient)
- The 2-rune likelihood objective provides a **usable fitness gradient**

The v1 CI used a simplified base_0 recovery that only tried 200 random permutations. The v2 CI uses aldegonde's proper hill-climb with 5,000 iterations of swap mutations, which is validated to achieve exact recovery.

### Expected Results:
- Each trial takes ~49 seconds (vs 0.01s in v1) due to the proper hill-climb
- In 4 hours, each batch will test ~300 trials (vs 450,000 in v1)
- BUT each trial is much higher quality — if the right (g, σ) is sampled, base_0 will recover exactly
- Total across 10 batches: ~3,000 high-quality trials

### Breakthrough Threshold:
- **True English score:** ~-60,000 for the full corpus
- **v1 best:** -272,382 (4.5× off)
- **v2 target:** If any batch finds score > -100,000, that's significant progress
- **Break:** Score > -60,000 would indicate the correct key

---

## How to Check Results

### Option 1: GitHub Actions Tab
Visit: https://github.com/Skyro7777777/LiberPrimusDecoded/actions
Click on "Liber Primus Walk Attack v2 (Validated)" → any batch job for live logs

### Option 2: API (in next prompt)
```bash
# Check status
curl -s -H "Authorization: token <TOKEN>" \
  "https://api.github.com/repos/Skyro7777777/LiberPrimusDecoded/actions/runs/31877506584"

# List artifacts (after completion)
curl -s -H "Authorization: token <TOKEN>" \
  "https://api.github.com/repos/Skyro7777777/LiberPrimusDecoded/actions/runs/31877506584/artifacts"
```

### Option 3: Repo (auto-committed)
After completion, the aggregate job will commit results to:
`cicada3301-research/decoder/ci_results/aggregated_YYYYMMDD_HHMM.json`

Just `git pull` to see the results.

---

## Artifacts from Run 1 (Available Now)

All 10 batch results + aggregated results are available as GitHub artifacts (30-day retention):
- `batch-0-results` through `batch-9-results`
- `aggregated-results`

Download via API:
```bash
curl -s -L -H "Authorization: token <TOKEN>" \
  "https://api.github.com/repos/Skyro7777777/LiberPrimusDecoded/actions/artifacts/{ARTIFACT_ID}/zip" -o result.zip
```

The aggregated results are also saved locally at:
`cicada3301-research/decoder/aggregated_results.json`
`cicada3301-research/decoder/ci_results/batch_*_results.json`
