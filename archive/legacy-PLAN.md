# Two-track research plan (2026-11-03)

## Objective and decision

Keep P1817 and P1901 active through theory and matched small pilots. Select a main project only after checking reproducibility, novelty against closest work, measurable headroom, runtime, and narrative. No score or originality claim is established by ideation alone.

## Gate 0 — Literature and theory (now)

- [x] P1817: identify Image-GS denoising, Luxar global-K blind-spot calibration, Kim/Fridovich-Keil inverse-problem benchmark; derive fixed-candidate held-out gain identity and selection-bias boundary.
- [x] P1901: define batch encoding-time allocation objective; derive equal marginal gain condition under smooth concave curves and explain why measured curves need discrete optimization.
- [x] CPU-only toy check of P1817's fixed-candidate identity and validation-selection optimism; this is not a denoising result.
- [ ] Search later, earlier, and adjacent work for *local sequential holdout control of Gaussian birth/pruning* and *online compute allocation for implicit image codecs*; record DOI/arXiv, exact claim, overlap, and date in separate ledgers.
- [ ] Ask an independent strong model to attack each novelty statement and evaluator before coding.

## Gate 1 — Official baseline reproduction (separate CPU/setup work; GPU serial)

- [ ] P1817: pin Image-GS commit and environment, run one clean and one noisy image; inspect representation and add-point path; log PSNR, splat count, seconds, VRAM. Recreate same-representation global-K holdout comparator.
- [ ] P1901: pin Cool-Chic 5.0 commit, run sanity check and encode/decode one image; verify decoded dimensions, actual `.cool` bytes, distortion, total seconds, seed and all training stages. A 192×128 debug-preset CPU encode/decode and independent byte/PSNR check passed; official seven-case CPU sanity check exited 0. A formally specified baseline with full stage timing remains open; see `research/P1901_CPU_SANITY_EVIDENCE_20261104.md`.
- [ ] Confirm access to the intended 24–36GB GPU and benchmark one full small run. This local laptop reports an 8GB RTX 3070 Ti and is for setup/CPU checks only.
- [ ] Cloud platform and SSH access are not chosen yet; aim first at an RTX 4090-class 24GB instance. Do not claim a GPU reproduction until a real run exists.

Local-first execution gates and WSL environment status are in [本机全自主复现与预实验计划.md](本机全自主复现与预实验计划.md). The 8GB GPU may be used for small local pilots once official dependencies pass; cloud runs come after those gates.

Agent routing, quota controls, exact G0–G8 gates, and failure branches are in [research/AGENT_AND_PRE_GPU_WORKFLOW_ZH.md](research/AGENT_AND_PRE_GPU_WORKFLOW_ZH.md).

2026-11-04 serial continuation: a bounded local queue now runs P1817 clean/noisy Image-GS fits (10k **maximum** steps, official early stopping retained), P1901 `intra` 5k CPU encode, independent output checks, an OpenCode Go read-only audit, and a Codex CLI Sol read-only decision in that order. Each step starts immediately after the previous verified step; an error stops the chain. Live stage files are under ignored `runs/autochain_20261104_a/`; double-click `watch-progress.cmd` to see them. This batch does not autonomously rewrite its own scientific contract or loop indefinitely when the planned jobs end.

2026-11-04 execution frontier: P1817's separate Python 3.11.10 / PyTorch 2.4.1+cu121 compatibility environment detects the local GPU; the verified CUDA 12.1 Toolkit and both CUDA extensions installed successfully. Clean and noisy 192×192, 50-step Image-GS infrastructure runs completed and rendered/checkpointed. Independent comparison to known clean truth found the noisy-run output 14.7930 dB versus noisy input 20.3394 dB, so no denoising efficacy is established by this deliberately tiny smoke. A longer matched pilot and VRAM measurement are next. P1901's CPU seven-case official sanity passed; a separate non-debug `intra` 2k encode/decode completed with an independently checked 2,788-byte bitstream, 0.907552 bpp, 34.319820 dB and 138.13 s whole-command time. See [P1817 preflight and smoke](research/P1817_ENV_PREFLIGHT_20261104.md), [P1901 preset audit](research/P1901_BUDGET_PRESET_AUDIT_20261104.md) and [P1901 2k result](research/P1901_INTRA_2K_CPU_EVIDENCE_20261104.md).

Later on 2026-11-04: the bounded serial queue completed P1817 clean/noisy 192×192 Image-GS fits with 512 Gaussians and 10k maximum steps (both stopped at actual step 5000): clean render 48.147683 dB; noisy input 20.339398 dB versus noisy-fit render 29.135178 dB against clean truth. This is one synthetic development image, not a mechanism comparison. P1901's independent full 5k CPU encode completed at 2,732 bytes, 0.889322917 bpp, 34.512606 dB and 4:52.67 total wall time. See [P1817 fit evidence](research/P1817_LOCAL_FIT_20261104.md) and [P1901 5k evidence](research/P1901_INTRA_5K_CPU_EVIDENCE_20261104.md).

The first queue's OpenCode and Codex CLI audits completed. Their reconciled findings and next gates are in [serial audit](research/AUTOCHAIN_AUDIT_20261104.md). A separate CPU-only three-fold A/B/C data-flow smoke passed, but has not yet touched Image-GS; see [leakage smoke](research/P1817_ABC_LEAKAGE_SMOKE_20261104.md). A second bounded OpenCode→Codex literature collision chain started immediately after the first batch, with live status under `runs/literature_chain_20261104/`.

The literature collision chain finished with a caveat: both OpenCode scouts returned nonzero after cancelled web searches despite producing reports; Codex CLI completed the primary-source audit. The reconciled, narrower originality claims and unresolved sources are in [literature collision audit](research/LITERATURE_COLLISION_AUDIT_20261104.md). The launcher exit-code propagation was fixed so future chains stop on such a failure rather than silently advancing.

Next serial CPU job started immediately after the literature audit: freeze [P1901's second development image](research/P1901_SECOND_IMAGE_INPUT_20261104.md), then complete its 2k and 5k independent full encodes with byte/PSNR/time checks. Live status is under `runs/p1901_second_image_20261104/` and appears in `watch-progress.cmd`. No allocation claim is made until these outputs and total-time objective are audited.

The second-image 2k/5k runs and independent verification completed. A provenance audit showed the nominal 500-second cap was durably recorded after the second image's 2k result existed, and the compared assignments consume unequal time. The best measured menu entry is still kodim15=5k/kodim01=2k, but its 1.1219% difference versus all-2k is a retrospective unequal-time description; only 0.2240% separates the mixed assignments, also at unequal time and without replication. **Online allocator remains no-go.** See [corrected two-image diagnostic](research/P1901_TWO_IMAGE_HEADROOM_20261104.md).

Before any allocator implementation, the [seeded replication contract](research/P1901_REPLICATION_CONTRACT_20261104.md) freezes two images, 2k/5k independent schedules, seeds 123/456, eight CPU threads, deterministic settings, complete bitstreams and independent decoding. Its only question is whether the 0.2240% retrospective mixed-schedule separation exceeds controlled seed variation; passing would justify a larger prospective development curve, not an allocator claim.

The frozen implementation was committed as `4bb5f75` after three read-only preflight audits (two `NO LAUNCH` rounds whose blockers were repaired, then `LAUNCH`). The eight-cell CPU batch started serially at 2026-11-04 21:11 UTC. Live status and partial evidence are under ignored `runs/p1901_seed_replication_20261104/`; `watch-progress.cmd` now displays the active cell. No allocator code is authorized by this launch.

A bounded post-batch chain waits for all eight verified cells, then applies only the frozen analyzer, requests one OpenCode Go read-only result audit, and requests one Codex CLI strong-model promotion decision. It does not retry failures or launch another experiment, so completion flows immediately into audit without opening an autonomous tuning loop.

The eight-cell batch completed at 21:34 UTC; see [fixed-seed replication evidence](research/P1901_SEEDED_REPLICATION_EVIDENCE_20261104.md). The frozen analyzer returned **no-go**: the mean mixed-assignment effect magnitude was `3.6031e-06`, below the two-seed range `7.1801e-06` (`E/R = 0.502`). The post-batch OpenCode audit failed on Windows/WSL shell orchestration after reading aggregate evidence, so this is recorded as an agent-audit failure rather than an experiment failure. Codex strong-model fallback independently recomputed every objective and contrast and upheld the no-go. P1901 allocator implementation and retrospective tuning are stopped; local compute returns to P1817's matched holdout-birth mechanism pilot.

## Gate 2 — Small mechanism pilots

- [ ] P1817: synthetic flat/edge/repeated-texture images, then ~8 development images at sigma 25/255. Compare residual birth, fixed K, holdout-selected global K, and local holdout birth under matched K and matched time. Use A fit/propose, B select, C audit; final pixelwise blind-spot output requires a separate three-fold rotation.
- [ ] P1901: 4–6 development images at one lambda; completed 5k/10k/20k-iteration encodes, at least two seeds if runtime allows. Compare equal time, equal iterations, pixel-count heuristic, and offline discrete oracle. If staged schedules make these incomparable as checkpoints, record independent restart curves explicitly.

## Gate 3 — Independent confirmation and mainline selection

- [ ] Freeze methods and metrics. P1817: untouched images and noise sigma 15/25/50; include BM3D, TV-grid, pre-denoise-fit and failure cases. P1901: untouched images and multiple lambdas; count online decision overhead in total time and use actual bitstreams.
- [ ] Choose P1817 if local selection gives repeatable gains beyond global-K selection or a compelling mechanism analysis. Choose P1901 if attainable oracle gap clearly exceeds seed noise and an online policy closes it on unseen images. Otherwise keep the strongest negative/mechanism result and revise ideas.

## Autoresearch rule

One runner, one GPU, one candidate change per run. Let small agents propose patches on separate branches; strong-model reviewer admits one patch after validating the invariant evaluator. Append results to a ledger; promote only after same-budget improvement repeats across development seeds. The independent test is run once after the rule is frozen.

2026-11-04 P1817 frontier: [the matched local holdout-birth pilot contract](research/P1817_HOLDOUT_BIRTH_PILOT_CONTRACT_20261104.md) freezes one 1000-step, 320-Gaussian auxiliary mechanism test before implementation. It uses random/color-free initialization, A-only L2/proposals, local B selection, untouched C audit and a mandatory C-perturbation invariance smoke. Upstream stays read-only; no full development batch or tuning is authorized until this minimum gate passes.

2026-11-05: Claude Opus 5.5 and OpenCode read-only review plus simulated-unavailability Codex Terra high fallback were exercised; see [routing validation](research/AGENT_ROUTING_E2E_20261105_ZH.md). The recovered Claude preflight independently upheld P1817 NO LAUNCH and identified the need to amend the matching and determinism protocol before experiments. OpenCode incorrectly described an uncommitted amendment as completed; all model outputs require coordinator review. No GPU work was run.

The prospective [P1817 amendment](research/P1817_PILOT_AMENDMENT_20261105.md) specifies a shared step-500 prefix and candidate pool, layered C-invariance checks, and a two-control observed noise floor. It preserves the original scientific objective and is frozen before pilot execution; implementation, fixed evaluator, tests and independent audit remain outstanding.

P1817 repair is underway: a CPU-only fold boundary module, subclass boundary integration and 37 CPU tests are recorded in [repair log](research/P1817_REPAIR_LOG_20261105.md). The current draft has an explicit NO LAUNCH guard; shared-prefix implementation, fixed evaluator and independent integrated audit remain required.

Later 2026-11-05: Claude Opus 5.5 produced guarded shared-prefix/three-arm and fixed-evaluator drafts; the complete CPU suite passed 61 tests. The implementation explicitly still lacks an automatic GPU idle check, and its invariance result needs independent validation. A Sol high integrated review is in progress. These are infrastructure results, not a completed development experiment; NO LAUNCH remains.

Human-requested PhD novelty assessment2026-11-05: two actual Claude Opus5.5 audits plus ResearchRabbit5-seed/20-recommendation expansion and coordinator primary checks are recorded in [PhD novelty and feasibility audit](research/P1817_PHD_NOVELTY_FEASIBILITY_20261105_ZH.md). Broad Fisher/adaptive-complexity/uncertainty ideas overlap prior work; retain search-risk-aware primitive growth as a candidate for cheap falsification, with geometry theory and reliability as conditional extensions. No new method was promoted and no new experiment ran; existing pilot contract/NO LAUNCH remains. First Claude web audit was permission-blocked; second read-only call succeeded with web access and an auxiliary Haiku model recorded for web summaries.
