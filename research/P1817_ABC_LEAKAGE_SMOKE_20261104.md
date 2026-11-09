# P1817 A/B/C data-flow smoke

Date: 2026-11-04. `scripts/p1817_leakage_smoke.py` ran on CPU in the P1817 environment, seed 123, 18 scalar synthetic pixels, three rotating target folds. Output `/home/research/msc_inverse_research/runs/p1817_leakage_smoke_20261104.json`, SHA-256 `95eaf9c25ff2e39c7396289a0239e7afd4b59ace834bfcceb6ae8d8dd025a14c`; status `passed`, all three rotations.

The script tests the intended **interface** using simple fixed candidates: A values can affect fitted candidate predictions; B values can affect selection but cannot change candidates; target C values cannot change candidates, selection or target predictions. A deliberately leaky candidate that reads C fails the invariance check. Clean truth never enters fitting or selection functions. This is a meaningful data-flow check before implementation, but it is **not** an Image-GS implementation, a Gaussian birth result, proof of target exclusion in the future code, or independent test evidence.

Next: wire the same invariance checks to the actual Gaussian proposal/acceptance code and freeze fixed-K, global-K and local-birth budgets before any matched GPU comparison.
