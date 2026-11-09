# P1817 holdout-birth pilot: independent review of the NO LAUNCH preflight

**Verdict: NO LAUNCH stands.** All seven blockers are real. Two of them (pool matching and exact-hash invariance) can't be fixed by patching code alone: they need a contract amendment.

**About this review:** Claude Opus 5.5 in Claude Code, read-only static audit (infrastructure-smoke level). I ran nothing, edited nothing, and did not read clean truth. Beyond the requested files, I only read the upstream helpers `get_grid`, `set_random_seed`, `clean_dir` and `load_images`, and the atomicAdd calls in `backward.cu`.

## The seven reported blockers

1. **Fold indices: valid.** In `pilot.py:292`, interleaved (y, x) pairs end up used as flat indices at `:411-436` and `:306-316`. That alone decides it, whether or not `.view()` raises. I confirmed `pixel_xy` is row-major with index `y*w+x` and column 0 = x (`image_utils.py:45-50`). The fix is `nonzero(fold.reshape(-1)==k).squeeze(1)`.
2. **Holdout scorer: valid.** `Module.__setattr__` rejects plain tensors assigned to registered parameters (`pilot.py:534-537` vs `model.py:165-169`). The fix is a separate render function that copies `model.py:350-369` and calls gsplat directly, without changing the model's own parameters.
3. **C-boundary: valid.** The full noisy target is saved at `model.py:121-123`. The whole-image arithmetic at `pilot.py:330-331`, `:407-412` and `:560-613` also breaks the contract wording. See issue A below.
4. **Non-finite scores: valid, and worse than reported.** `np.argsort` sorts NaN last, so the `[::-1]` at `pilot.py:456` picks NaN candidates **first**. Use a stable sort on `-scores` after an all-finite check.
5. **Unmatched pool: valid, and the main conceptual problem.** See issue C.
6. **Output protection and GPU exclusivity: valid.** Two more problems:
   - The invariance run's normal arm is named `holdout_seed123` (`:660`, `:832`), the same name as the standalone holdout run, so it's unclear which run belongs to the matched pair.
   - On Windows, `/home/...` is not an absolute path, so the check at `:800` fails. Confirm which machine will run this.
7. **Evidence and evaluator: valid.** `scripts/analyze_p1817_holdout_birth.py` doesn't exist.

## Additional problems

**A. C values sit in trainer memory.** Masking happens *after* whole-image subtraction (`:330`). The safer design:
- At load time, gather separate `gt_A` and `gt_B` tensors.
- Fill the trainer's copy of C with a NaN sentinel.
- Override `_init_target` so it doesn't write images.

If anything then does whole-image arithmetic, it fails loudly: NaN·0 = NaN even in the backward pass of a masked `diff**2`. This turns "no C access" from a promise into something the code enforces. Pass `gt_B` only to the holdout scorer.

**B. The invariance test can't separate leakage from GPU noise.**
- The perturbation (`:310-316`) is weak. Its first delta is 0, and `clamp` cancels it at saturated pixels.
- More seriously, exact checkpoint and render hashes across two full runs will almost certainly differ even without leakage. The topk-norm backward kernel accumulates gradients with float `atomicAdd` (`backward.cu:235`, `:276-282`), and `set_random_seed` (`misc_utils.py:22-29`) can't make that deterministic.

A better test has three layers:
- (i) Exact hashes of every target tensor the trainer holds stay identical under the C perturbation. This is deterministic and needs no GPU.
- (ii) From one saved step-500 checkpoint, the pool, scores and selection are bitwise identical. This uses forward passes only. Forward determinism must be measured, not assumed.
- (iii) Full-run divergence is compared against the divergence of a same-input repeat.

Changing the contract's "identical hashes" rule (`contract:20`) is an amendment and must be registered before any run.

**C. A matched pool needs a fork, not a shared seed.**
- Run steps 1-500 once, then save the parameters, the numpy/torch/CUDA RNG states and the pool.
- Both arms load that same file. Adam is reset at birth in both (`:490`, `model.py:597`), so no optimizer state is needed.
- The pool hash is then equal by construction, and the code still checks it.
- After birth, the gap between arms still includes atomicAdd noise. A single "strictly lower C-MSE" comparison (`contract:10-11`) could be decided by that noise. A control-repeat noise floor from the same fork is needed. This is also an amendment, not tuning.

**D. Scorer limitations (frozen, so record them; don't tune).**
- Only the candidate's own 16×16 tile is scored, but the ~5 px initial footprint crosses tile edges, so candidates near tile borders are under-credited.
- The scorer clamps renders; the training loss does not.
- With topk=10 normalisation, individual scores don't add up when several chosen candidates share a tile.

**E. B noisy MSE is biased after selection.** The analyzer must exclude it from the decision. Commit and hash the analyzer before any outputs exist.

**F. Future-image hazard.** If the pilot ever falls back to upstream `_add_gaussians`, its blur (`model.py:554-558`) mixes folds whenever √(HW) ≥ 400. That isn't triggered at 192 px, but it matters for the later batch.

**Checked and fine:** In the (x+2y) mod 3 map, each A pixel has two B and two C neighbours, so B and C are interchangeable with respect to A. `load_images` loads a single file when given a file path (`image_utils.py:72`).

## Repair order

1. Data boundary and indexing (blockers 1 and 3, issue A).
2. Separate renderer plus scorer guards (blockers 2 and 4).
3. Fork architecture, plus the written amendments for invariance and the noise floor (blocker 5, issues B and C).
4. Run safety (blocker 6):
   - Reserve a new, not-yet-existing directory atomically. Upstream `clean_dir` runs `rmtree` on whatever it's given.
   - Add a GPU lock and an idle check.
   - Give runs unique names.
   - Write a failure manifest when a run aborts.
5. Evidence and the analyzer (blocker 7).

## First safe patch (CPU only)

Limit it to `scripts/p1817_holdout_birth_pilot.py` lines 250-336 and 406-436, plus an `_init_target` override:
- Put fold and index construction, A/B gathering, the C sentinel and the C perturbation into **pure functions that don't import upstream**. `model.py` imports CUDA and perceptual-metric modules (gsplat, fused_ssim, lpips).
- Add CPU unit tests.
- No GPU code paths and no changes to upstream.

## Must be verified before any GPU pilot

- **CPU tests:**
  - A, B and C each have 12,288 indices, are disjoint and cover the image.
  - Pool indices are unique and all in A.
  - The perturbation changes every C value and nothing else, with no cancelled deltas.
  - Hashes of trainer-held tensors don't change under the C perturbation.
- **Single-process GPU smokes, not pilot runs:**
  - The separate renderer bitwise-equals `model.forward`.
  - Two forward passes are bitwise identical.
  - Backward repeat divergence is measured.
- **Paperwork and review:**
  - The amendment is committed.
  - The analyzer is committed and hashed.
  - Someone other than the patch author audits the patch.
  - The GPU is confirmed idle at launch.

**Next action:** the coordinator approves the first-patch scope and drafts the amendment. Nothing here is a result or a novelty claim.
