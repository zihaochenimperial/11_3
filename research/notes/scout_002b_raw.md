# GLM code-mapper raw output (task 002b), job j10 — UNVERIFIED worker output (not yet checked by Sonnet)

# Scout 002b 鈥?F0 design evidence (read-only; paths actually opened)

**Opened:** `AGENTS.md` (L3鈥?3); `research/P1817_PHD_NOVELTY_FEASIBILITY_20261105_ZH.md` (L9,30,40鈥?3,47鈥?1); `research/P1817_CODE_MAP_20261104.md` (L5鈥?, only one CODE_MAP exists); `archive/theory/P1817.md` (L3鈥?1); all 5 `archive/legacy-reviews/*.md`; source under `archive/`: `archive/scripts/p1817_holdout_birth_pilot.py` (key sections), directory listings of `archive/{codex-originals,pre-restructure-20261105,scripts,tests}`.

## 1. Renderer details that matter for a CPU rewrite (seen)
- Params: `xy` in **normalized [0,1] coords**, `scale` entered as **inverse scale** (`scale = 1/s`; applied at `pilot.py:745-746`; flag `disable_inverse_scale`), rotation (1 param), per-Gaussian feature/color; gamma=1.0 pinned (`pilot.py:329,442`); render clamped to [0,1] before gamma/scoring (`770-772`, `821-823`).
- Pipeline: `project_gaussians_2d_scale_rot(xy, inv_scale, rot, h, w, tile_bounds)` 鈫?`(xy_px, radii, conics, num_tiles_hit)`, then `rasterize_gaussians_sum(..., block_h, block_w, topk_norm_enabled)` (`747-755`) producing H脳W脳C, `view(-1,h,w,C).permute` 鈫?CHW (`756-758`).
- Tiles 16脳16 (`445`), tile_bounds = ceil-div tiles (`470-472`); topk=10 with normalization **on** (`338-339`). Tiles matter mostly because scoring is per-tile (`760-830`); a CPU renderer can be tile-free but must keep top-K normalization.
- Init: random positions, `init_scale=5.0` (i.e. footprint 鈮? px), `init_random_ratio=1.0`, non-target-derived colors (`343-344,100`) 鈥?reuse, so F0 avoid saliency/gradient init.
- Birth/candidate pool: residual-weighted sampling **without replacement** over A-fold pixels, prob = mean A squared residual normalized twice (`635-647`); candidates get init scale `1/init_scale`, rot=0, **feat = local A residual color** (`654-664`); birth concatenates chosen candidates and **re-creates Adam from scratch** with per-group LRs pos 5e-4 / scale 2e-3 / rot 2e-3 / feat 5e-3 (`101-104`, `708-724`, mirroring upstream `model.py:597-600` per comment). `vis_feat` non-trainable (`712`).
- **Not seen:** upstream `model.py` body (only second-hand refs: code-map L7 model.py:431-432 progressive add, 547-602 birth; preflight L11 model.py:165-169 param registration, L14 121-123 target logging). The exact top-K sum-tie-breaking鏁板 and kernel math are **inferred**, not read.

## 2. Discontinuities / FD implications (partly inferred)
- Top-K membership per pixel: a Gaussian entering/leaving the top-10 set jumps pixel output by ~ its removed weight 鈫?error scale 鈮?weight magnitude; **inferred** exact sort/tie behavior (kernel not read). Ties at the K-th boundary are the only O(1) jumps; within-set reordering is harmless under normalization (**inferred**).
- Birth candidate selection: residual-weighted `np.random.choice` + `np.argsort(-scores, stable)` (`645-647,694`) 鈥?discrete; note NaN sorts first with `[::-1]`-style argsort (preflight blocker 4).
- Pruning: **no pruning code found** in the pilot; unknown in upstream.
- FD h must be 鈮?smallest effective scale (鈮?/5 in inverse-scale param) so memberships don't flip; but too small h 鈫?cancellation. Randomized/repeated draws per probe recommended (feasibility L30; review v2 L49 Tibshirani randomized search).

## 3. Data boundary (seen)
- A fit/proposal, B choose, C audit; noise independent at target pixels; fixed candidate counts (theory L7-9). C-values replaced by NaN sentinel in trainer (preflight issue A), C never enters A-loss/proposals (integrated-review L36). Clean image only in the independent reference evaluator; distinguish noise seeds from optimizer seeds and refit them independently (feasibility L40); blur after noise breaks holdout independence (review v2 L31). Validate noisy provenance before opening clean truth (integrated-review item 5).

## 4. Cheapest MC-SURE comparator (inferred, not measured)
Fix post-fit network (DIP-SURE style): 1 full pipeline fit per noise draw; then 2鈥? forward-only probes `f(鈭毼?y + 蔚)` (Ramani; ~4鈥? forward renders/draw). Re-pipeline-per-probe variants cost O(J脳) refits 鈥?likely infeasible on CPU. All probe costs count toward budget (feasibility L41).

## 5. Blockers
Upstream `model.py`/CUDA weight math absent from archive 鈫?CPU-equivalence smoke (per preflight "verify before GPU") is pending; exact top-K semantics unverified; pruning unknown; any cost numbers unmeasured.