**NO LAUNCH.**

Classification: **infrastructure smoke — static, read-only audit**. I read all four requested files and relevant renderer/helpers. No files were edited; no pilot or GPU code was run. Upstream HEAD matches `03088368d42684fb54225c981cfd94b58cc0393a`, its working tree is clean, and its license is MIT.

Blocking defects:

1. **Fold indices are coordinate pairs, not flattened pixel indices.**  
   [Pilot line 292](/C:/Users/USER/Desktop/P1817_P1901_research/scripts/p1817_holdout_birth_pilot.py:292) applies `.view(-1)` to `nonzero()` on a 2D mask. This normally fails on its noncontiguous output. Even if made contiguous, it produces interleaved `y,x` coordinates, all between 0 and 191. Lines **411–436** then treat these as flattened image indices: proposals and features come from the first row, including B/C targets, and sampled entries can refer to duplicate pixels. Lines **306–316** likewise perturb first-row A/B/C pixels instead of C alone. This breaks proposal isolation, pool uniqueness, and the invariance intervention. Correct indices must identify nonzero entries of the **flattened mask**.

2. **Holdout scoring cannot assign its augmented parameters.**  
   [Pilot line 534](/C:/Users/USER/Desktop/P1817_P1901_research/scripts/p1817_holdout_birth_pilot.py:534), and lines **535–537**, assign ordinary concatenated tensors to attributes registered as `nn.Parameter` at [upstream lines 165–169](/C:/Users/USER/Desktop/P1817_P1901_research/upstream/image-gs/model.py:165). PyTorch rejects this assignment; `no_grad()` does not change parameter-registration rules. After fixing initialization, holdout would fail at the first candidate score, after 500 optimization steps.

3. **Inherited target logging violates the C-access boundary.**  
   [Upstream lines 121–123](/C:/Users/USER/Desktop/P1817_P1901_research/upstream/image-gs/model.py:121) save the entire noisy target during initialization. The subclass overrides loading, but leaves this caller intact. This exports C values before optimization, contrary to [contract line 20](/C:/Users/USER/Desktop/P1817_P1901_research/research/P1817_HOLDOUT_BIRTH_PILOT_CONTRACT_20261104.md:20). Additionally, pilot lines **330–331, 407–412, and 560–613** perform whole-target arithmetic before masking. With correct masks and finite values, that arithmetic does not itself demonstrate parameter leakage, but it does not meet the literal external-audit-only C-read requirement.

4. **Non-finite scores can be selected and reported as completed.**  
   [Pilot lines 453–456](/C:/Users/USER/Desktop/P1817_P1901_research/scripts/p1817_holdout_birth_pilot.py:453) sort scores without checking finiteness; lines **613–615** return them unchecked. A NaN can therefore enter the selected set. There are also no explicit finite-loss, gradient, parameter, or final-render guards. This fails the mandatory non-finite-score stop in contract line **26**.

5. **The matched control/holdout pool is recorded but never enforced.**  
   [Pilot lines 823–845](/C:/Users/USER/Desktop/P1817_P1901_research/scripts/p1817_holdout_birth_pilot.py:823) launch independent trajectories. The only pool comparison, lines **847–850**, compares normal versus perturbed **holdout**, not control versus holdout. Matching seeds cannot guarantee identical trajectories: the selected CUDA backward path uses floating-point `atomicAdd` reductions at [kernel lines 235 and 276–282](/C:/Users/USER/Desktop/P1817_P1901_research/upstream/image-gs/gsplat/gsplat/cuda/csrc/backward.cu:235). This also makes exact invariance hashes vulnerable to execution nondeterminism. No shared frozen prefix/pool or mandatory pair-validation gate currently establishes the contract’s matching requirement.

6. **Output protection is vulnerable to concurrent deletion, and GPU exclusivity is absent.**  
   [Pilot lines 621–627](/C:/Users/USER/Desktop/P1817_P1901_research/scripts/p1817_holdout_birth_pilot.py:621) check directories without reserving them. Initialization subsequently invokes [upstream `clean_dir`, line 77](/C:/Users/USER/Desktop/P1817_P1901_research/upstream/image-gs/model.py:77), which recursively deletes an existing directory. Two launches can pass the check and then delete each other’s outputs. There is no GPU process check or lock before lines **675–680**. Also, an existing empty status directory passes preflight but fails at line **702**, after optimization. These violate the overwrite and simultaneous-GPU stop requirements.

7. **Required evidence and the fixed evaluator are incomplete.**  
   [Pilot manifest lines 716–748](/C:/Users/USER/Desktop/P1817_P1901_research/scripts/p1817_holdout_birth_pilot.py:716) omit implementation/tool hashes and metrics. Failures before manifest creation leave no structured failure record. Final Gaussian count and steps are recorded as constants at lines **731–734**, rather than verified observations. The required `scripts/analyze_p1817_holdout_birth.py` is absent; consequently, there is no implemented fixed evaluator or exact noisy-C/clean-C decision gate required by contract lines **24–33**. The upstream YAML does capture configuration, but that only partially covers provenance.

The invariance comparison itself checks the four intended quantities—pool, selected indices, parameter state, and raw render—at lines **847–860**. Its present intervention is invalid because of defect 1, so those comparisons cannot establish C isolation.

The intended finite-data paths otherwise look appropriate: random initialization disables target-derived colors and saliency; masked A loss gives zero B/C output gradients; evaluation logs A metrics; extra perceptual metrics are disabled; and LR scheduling is disabled for a fixed 1,000 steps. Candidate scoring uses the actual augmented renderer, including inverse scales and top-k normalization, and evaluates B pixels in the containing 16×16 tile. It ranks candidates individually and retains 64 even for negative scores, as contracted. These safeguards remain unvalidated because the execution blockers prevent a valid run.

**Keep GPU execution blocked until the fold indexing, scorer, C boundary, and fail-closed run/evidence gates are corrected and reviewed.**