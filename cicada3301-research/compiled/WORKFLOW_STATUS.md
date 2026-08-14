# GitHub Actions Workflow — Status & Instructions

## ✅ Workflow is LIVE and RUNNING

**Workflow URL:** https://github.com/Skyro7777777/LiberPrimusDecoded/actions
**Current Run:** https://github.com/Skyro7777777/LiberPrimusDecoded/actions/runs/31823481392
**Workflow ID:** 334499434
**Status:** `in_progress` (10 parallel batches)
**Started:** 2026-08-14T17:19:48Z
**Duration per batch:** 4 hours (14,400 seconds)
**Expected completion:** ~4-5 hours from start

## What's Running

10 parallel batches (IDs 0-9), each testing ~300,000 random (g, σ) pairs against the length-clocked-walk cipher model. Total: ~3 million trials.

Each batch:
1. Generates random order-5 permutation `g` (g⁵ = identity)
2. Generates random permutation `σ` (word-boundary step)
3. Recovers `base_0` via 2-rune likelihood hill-climb (VALIDATED: exact recovery when key is correct)
4. Decrypts the full 12,956-rune unsolved LP2 corpus
5. Scores with Runeglish quadgrams (464K entries from aldegonde)
6. Saves results to `batch_N_results.json` every 10 minutes

## How to Check Results

### Option 1: GitHub Actions Tab
1. Go to: https://github.com/Skyro7777777/LiberPrimusDecoded/actions
2. Click on the "Liber Primus Walk Attack (Batched)" run
3. Click on any batch job to see live logs
4. Artifacts will appear at the bottom of each job when complete

### Option 2: GitHub API (in next prompt)
```bash
# Check workflow status:
curl -s -H "Authorization: token <YOUR_GITHUB_TOKEN>" \
  "https://api.github.com/repos/Skyro7777777/LiberPrimusDecoded/actions/runs/31823481392"

# List artifacts (available after batches complete):
curl -s -H "Authorization: token <YOUR_GITHUB_TOKEN>" \
  "https://api.github.com/repos/Skyro7777777/LiberPrimusDecoded/actions/runs/31823481392/artifacts"

# Download a specific batch result:
curl -s -L -H "Authorization: token <YOUR_GITHUB_TOKEN>" \
  "https://api.github.com/repos/Skyro7777777/LiberPrimusDecoded/actions/artifacts/{ARTIFACT_ID}/zip" -o batch_results.zip
```

### Option 3: Aggregated Results
After all 10 batches complete, an `aggregate` job will:
1. Download all 10 batch results
2. Find the best score across all batches
3. Save to `aggregated_results.json`
4. Commit to the repo
5. Upload as an artifact named `aggregated-results` (90-day retention)

## What to Look For

### Breakthrough Threshold
- **True English score:** ~-60,000 for 12,956 runes (≈ -5 per quadgram)
- **Current best (local):** ~-274,000 (≈ -21 per quadgram — random noise)
- **Break threshold:** If any batch scores > -60,000, that's a potential break
- The workflow will display `::warning::POTENTIAL BREAKTHROUGH!` if this threshold is exceeded

### What the Results JSON Contains
```json
{
  "batch_id": 0,
  "best_score": -274675.3,
  "best_key": {
    "base_0": ["F", "V", "TH", ...],  // 29-letter permutation
    "g": ["F", "V", "TH", ...],       // order-5 permutation
    "sigma": ["F", "V", "TH", ...]    // word-boundary permutation
  },
  "best_plaintext": "DTSWIXOOPAEFJIWVW...",
  "trials_done": 1514,
  "duration_seconds": 20
}
```

## If No Breakthrough in This Run

The workflow can be re-triggered with different parameters:
1. Go to: https://github.com/Skyro7777777/LiberPrimusDecoded/actions/workflows/walk_attack.yml
2. Click "Run workflow"
3. Adjust:
   - `num_batches`: 10 (default) or more for wider search
   - `duration`: 14400 (4 hours) or up to 18000 (5 hours, the max)

Or trigger via API:
```bash
curl -X POST \
  -H "Authorization: token <YOUR_GITHUB_TOKEN>" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/Skyro7777777/LiberPrimusDecoded/actions/workflows/334499434/dispatches" \
  -d '{"ref":"main","inputs":{"num_batches":"10","duration":"14400"}}'
```

## The Cipher Model (for reference)

The length-clocked-walk model (CONFIRMED by aldegonde):
```
c[j] = base_w( g^(j mod 5)( p[j] ) )
base_{w+1} = base_w ∘ g^((L_w − 1) mod 5) ∘ σ
```
- `g` = order-5 permutation (5 five-cycles + 4 fixed points on 29 runes)
- `σ` = general permutation (word-boundary step)
- `base_0` = initial alphabet
- `L_w` = length of word w (public, from ciphertext)
- Total key: ~200 bits

The attack is validated: when (g, σ) are correct, base_0 recovers EXACTLY. The bottleneck is the (g, σ) search space, which this workflow explores with 3 million random trials.
