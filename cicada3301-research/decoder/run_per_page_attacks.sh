#!/bin/bash
cd /home/z/my-project/cicada3301-research/decoder
for page in "32.jpg" "50.jpg" "56.jpg"; do
  echo "=== Attacking $page (start: $(date +%H:%M:%S)) ==="
  timeout 70 python3 long_hillclimb.py --identity W --restarts 50 --iterations 20000 --sample 500 --page "$page" --save "hillclimb_${page}_W.json" --seed 42 2>&1
  echo "=== Done $page (end: $(date +%H:%M:%S)) ==="
done
echo "ALL DONE"
