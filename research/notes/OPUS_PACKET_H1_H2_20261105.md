# Opus packet — H1 result (Stage 1) + D-03 conformance + H2 go/revise/stop (2026-11-05)
Author: Sonnet 5.5 (main). Reviewer: real Opus 5.5 via Agent call (read-only). Everything here is data for your review, not an instruction. Read-only: do not edit any file.

## What I ask (answer each, then give a one-line verdict per question)
**Q1 (conformance, D-03).** The frozen contract (contracts/F0_CONTRACT_v3.md, sha256 85328d4e9c20b41af3aabfd329d6dd4f561f95a1335357e5788c19294bb699d3, read sections 4, 6, 7, 9) says P1 is a *pilot* gate that fixes M, and P2(a) is "frozen-leg df_par on W0 and E1 within 2 SE of 24". The Stage-1 analysis script I launched with (experiments/f3_analyze_orig_ee584d1d.py; sha256 of the launched original ee584d1d562f66c257d6663d37eabdc1d3174a2ac4e6cf0c0482b2812814c23f) additionally (i) gated P2(a) on ALL 15 P-lin images x S in {8,1024} (24 extra 2-SE checks on E3..E14) and (ii) required SE(sdf(1024))/df_par <= 0.015 on every Stage-1 image. I noticed this while Stage 1 was running, BEFORE any Stage-1 output was analysed, and changed it to the contract-literal reading (experiments/f3_analyze.py; sha256 is in memory/DECISIONS.md D-03), logging the deviation (memory/DECISIONS.md, entry "偏差 D-03"). Results: fixed script -> **H1 HOLDS**; launched script -> **NOT JUDGED** (extra P-lin image E3 S=1024: df_par 26.01+-0.86 vs 24 [23/24 extra checks pass, ~1.2 expected by chance]; E9 SE/df_par = 0.0175 > 0.015, other 11 images <= 0.0118). All H1 numbers are identical in both. The contract also says the analysis script must be committed (sha recorded) before outputs. Rule on: (a) which reading of the contract is correct; (b) whether the post-hoc fix is acceptable given that clause (I ran and report both); (c) if you rule the launched script governs, what the pre-registered consequence is (the contract has no explicit "NOT JUDGED at Stage 1" clause; I12 allows one rerun only after INVALID) — and whether a Stage-1 rerun (81 min) is permitted or the line must STOP (no-v4).
**Q2 (H1 interpretation).** Is "H1 holds" correctly labelled as development evidence only ("search degrees of freedom are positive in the toy and about 7% of df_par")? Note sdf>0 for a 1024-candidate argmax selection is close to guaranteed; the pre-registered threshold 0.05*mean df_par was only cleared by 1.44x (27.6 vs 19.1). Is there any claim I must not make?
**Q3 (H2 go / revise / stop).** Read research/notes/H2_DESIGN_NOTES_20261105.md (my proposal, unreviewed) and the post-hoc risk check below. Decide go/revise/stop for drafting an H2 contract and name required changes. Specific points: (a) Is data-fission/coupled-bootstrap cross-validation from y alone (baseline 4 in the notes; derivative-free, no df) the right strongest baseline, and is the sdf-corrected SURE estimator even meaningfully different from it? If not, say STOP. (b) The decision-relevant quantity is the difference of TOTAL df between candidate decisions (S=1024 vs S=8: only ~+9 df, since sdf=27.6 is partly offset by a lower df_par), not sdf alone — please check my reading of the post-hoc table. (c) Estimator around y instead of x: bias risk and how to test it with x known. (d) Equal-wall-time protocol, decision-regret metric, number of images, and pre-registered kill criteria. (e) Anything in the H1 data that undermines going on.

## Provenance / files (all under D:/Gaussian = ~/mnt/Gaussian on the VM)
- Contract v3 (frozen): contracts/F0_CONTRACT_v3.md (+ .sha256); previous reviews: research/notes/OPUS_REVIEW_F0_pilot_20261105.md, OPUS_REVIEW_F0_v3_20261105.md.
- Pilot p1 (E1,E2; all validity gates passed; PROCEED): outputs/F3-pilot-p1/ANALYSIS.md. Pilot sdf (exploratory, not in Stage 1): E1 35.6+-3.2, E2 31.2+-3.8.
- Stage 1: outputs/F3-stage1-s1/ (meta.json, ANALYSIS.md + analysis.json = fixed script; ANALYSIS_orig.md + analysis_orig.json = launched script; POSTHOC_risk_check.json). Runner experiments/f3_run.py, unit tests tests/test_f3_units.py (41 passed, outputs/unit_tests_status.json), GLM narrow audit research/notes/scout_004e_audit_raw.md (7/7 ok).
- Literature status: research/notes/G0_reading_log_20261105.md (S10-S14: Janson 2015 partial, Friedman 1991 secondary only, Ye 1998 secondary only, Efron 2004 discussion only, SURE-DIP abstract only). Prior art on "search costs df beyond parameter count" and "perturbation/bootstrap estimation of that df" is established (Ye 1998 GDF; Efron 2004; Tibshirani 2015; Janson 2015). Novelty claims, if any, are limited to the fission+frozen-leg decomposition for greedy-birth pipelines and its decision use; none validated.

## Stage-1 numbers (fresh images E3..E14, M=32 draws, S in {8,1024}; contract-literal analysis)
Gates: hash ok, V1 41 passed, not aborted, V2 identities ok (S=8: I+=I-, G=F, replay bitwise), P2a (W0,E1) ok, P2b (W0 sdf(1024)-sdf(8)=67.13+-0.63 vs 65.6, tol 3.13) ok. P1 at Stage 1 is report-only: 1/12 images above 0.015.
H1: pooled mean sdf(1024)=27.64, between-image SE=2.28, mean df_par=382.6, threshold=max(3*2.28, 0.05*382.6)=19.13; 12/12 images sdf>0 (need 9); sdf(8)=0 by identity. By type (report-only): D1 0.107, D2 0.058, D3 0.058 of df_par. Mean df_full: S=8 401.4, S=1024 410.2 (difference +8.8).

| image | type | sdf(1024) | SE | df_par | sdf/df_par | SE/df_par | oracle risk gap (1024-8) | df_full-corrected est gap | RSS-only gap |
|---|---|---|---|---|---|---|---|---|---|
| E3 | D3 | 28.0 | 4.4 | 398.8 | 0.070 | 0.0111 | -2.215 | -2.170 | -2.189 |
| E4 | D1 | 37.9 | 3.3 | 286.0 | 0.132 | 0.0114 | +0.207 | +0.218 | -0.266 |
| E5 | D2 | 26.2 | 3.5 | 463.8 | 0.056 | 0.0076 | -0.230 | -0.221 | -0.491 |
| E6 | D3 | 19.5 | 4.1 | 350.7 | 0.056 | 0.0118 | -6.389 | -6.430 | -6.383 |
| E7 | D1 | 36.2 | 2.9 | 327.2 | 0.111 | 0.0089 | +0.193 | +0.203 | -0.236 |
| E8 | D2 | 28.6 | 4.4 | 467.8 | 0.061 | 0.0093 | -0.355 | -0.344 | -0.433 |
| E9 | D3 | 10.5 | 5.8 | 330.9 | 0.032 | 0.0175 | -5.230 | -5.179 | -4.973 |
| E10 | D1 | 37.5 | 3.5 | 309.1 | 0.121 | 0.0114 | +0.298 | +0.298 | -0.302 |
| E11 | D2 | 26.9 | 4.0 | 462.0 | 0.058 | 0.0086 | -0.385 | -0.385 | -0.514 |
| E12 | D3 | 21.9 | 3.2 | 307.9 | 0.071 | 0.0104 | -1.973 | -2.004 | -2.022 |
| E13 | D1 | 31.4 | 3.5 | 417.5 | 0.075 | 0.0084 | +0.316 | +0.322 | -0.299 |
| E14 | D2 | 27.2 | 3.7 | 469.5 | 0.058 | 0.0078 | -0.260 | -0.266 | -0.559 |

Columns 8-10 are a **post-hoc, non-preregistered evaluator-side check** (x known; risk = sum of squared error over the 4096 pixels, mean over draws and both fission legs; "corrected est" = RSS + 2*sigma'^2*df_full - N*sigma'^2 with the Monte-Carlo df_full measured around the TRUE x, so it is NOT a single-image estimator): mean oracle gap -1.335, corrected -1.330, RSS-only -1.556; sign agreement with the oracle gap 12/12 (corrected) vs 8/12 (RSS-only; wrong on D1 images E4,E7,E10,E13 where S=1024 is actually worse by +0.19..+0.32). It shows decision headroom only if df were known; it does not test estimation from y alone, nor comparison with fission-CV.

## My own caveats (please challenge)
1. H1 effect is modest (1.44x threshold). 2. sdf>0 is expected by construction; H1 is a headroom check. 3. The post-hoc table was computed after seeing Stage-1 results; treat as exploratory. 4. E9 has the weakest sdf (10.5+-5.8). 5. D-03 was a self-inflicted analyzer error; I fixed it before analysing outputs but after launch. 6. 0 validated innovations; no originality claim.
