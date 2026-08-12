#!/usr/bin/env python3
"""Run attacks 1, 3, 4 only (the fast ones)."""
import sys, os, json, time
sys.path.insert(0, '/home/z/my-project/cicada3301-research/decoder')
import wave4_attacks as w

t0 = time.time()
print("="*70)
print("WAVE-4 ATTACKS 1, 3, 4 (fast attacks)")
print("="*70)
print(f"Unsolved corpus: {len(w.UNSOLVED_FULL)} runes total")
print(f"Sample windows: 300 + 1000 runes")

results = {}
results["attack1"] = w.run_attack1()
print(f"  Attack 1 done at {time.time()-t0:.1f}s")
results["attack3"] = w.run_attack3()
print(f"  Attack 3 done at {time.time()-t0:.1f}s")
results["attack4"] = w.run_attack4()
print(f"  Attack 4 done at {time.time()-t0:.1f}s")

# Save partial JSON
def to_jsonable(obj):
    if isinstance(obj, dict): return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list): return [to_jsonable(x) for x in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None: return obj
    return str(obj)

with open('/home/z/my-project/cicada3301-research/decoder/wave4_attacks_134.json', 'w') as f:
    json.dump(to_jsonable(results), f, indent=2, ensure_ascii=False)
print(f"\nSaved to wave4_attacks_134.json  (elapsed: {time.time()-t0:.1f}s)")
