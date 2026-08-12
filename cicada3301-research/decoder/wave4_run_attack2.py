#!/usr/bin/env python3
"""Run attack 2 (hill-climbing) only — the slow one."""
import sys, os, json, time
sys.path.insert(0, '/home/z/my-project/cicada3301-research/decoder')
import wave4_attacks as w

t0 = time.time()
print("="*70)
print("WAVE-4 ATTACK 2: HILL-CLIMBING AUTOKEY PRIMER DISCOVERY")
print("="*70)
print(f"Unsolved corpus: {len(w.UNSOLVED_FULL)} runes total; using first 500 for hill-climb")

results = w.run_attack2()
print(f"\nTotal elapsed: {time.time()-t0:.1f}s")

def to_jsonable(obj):
    if isinstance(obj, dict): return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list): return [to_jsonable(x) for x in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None: return obj
    return str(obj)

with open('/home/z/my-project/cicada3301-research/decoder/wave4_attack2_results.json', 'w') as f:
    json.dump(to_jsonable(results), f, indent=2, ensure_ascii=False)
print(f"Saved to wave4_attack2_results.json")
