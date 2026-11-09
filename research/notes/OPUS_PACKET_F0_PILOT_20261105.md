# Opus gate packet: post-pilot review (round 4) of F0 -- written by Sonnet 5.5, 2026-11-05T10:10Z
You are the scientific gate reviewer. Contract v2 (sha256 8c563f02...52feb37ff7f25) was frozen after your round-3 FREEZE-AFTER-CHANGES. The pilot has now been run. Nothing below is a claim of an innovation; 0 validated, 1 candidate mechanism. Report your own model id honestly. No web needed.

## 0. Question being tested
Adaptive 2D Gaussian fitting at fixed final K=48 and fixed Adam budget (600 steps = 4 stages x 150, 24 initial atoms + 3 birth rounds of 8, additive float64 renderer, 64x64, sigma0=0.08): does the candidate search (birth proposals, pool size S; S=8 means births are y-independent) add fitting risk beyond the parameter count? sdf := df_oracle^rand - df_frozen (df_frozen = divergence with birth indices replayed/held fixed). If yes, can it be estimated without clean data and corrected (MC-SURE/DIP-DF transplants are the baselines)?

## 1. What happened (all runs have run_ids under runs/, outputs under outputs/)
1. p1 (torch autograd fitter, 18 workers): aborted by the contract's own 1800 s pilot wall cap (exit 3). 64 main units done at ~43 s/fit; N0 16/32, P-lin partial, V7/det not started. NOT interpreted.
2. Diagnosis: single-process 600-step fit = 4.85 s (torch); parallel throughput saturates at ~3-4 workers (laptop i7-12700H, AC power, best-performance overlay, max processor state 100%; so bandwidth/power-bound, not a settings problem).
3. D-02 (implementation only, same model): numpy analytic-gradient fitter src/gsfast.py + cache-blocked kernel src/gskernel.py. Gradients vs torch autograd rel. err ~1e-15 (K=24/32/48); 5- and 25-step full pipelines agree to 1e-13/3e-12 with identical birth indices; bitwise determinism and bitwise forced replay; 18 host unit tests pass (11 earlier + 7 added: equivalence, leakage negative control); GLM read-only audit of RNG/birth/optimiser parity: 5/5 ok. Single fit 1.86 s. Runner --impl fast.
4. p2 (fast, 6 workers, run 20261105T094618Z-host-py-c85b): completed, 840 fits, 668 s, no abort. Sustained rate 1.3 fits/s (4.42 s/fit with 6 procs; the short benchmark had suggested ~2.4/s).
5. Contract analysis (experiments/f0_analyze.py, run j34): **DECISION: INVALID, reason R7_eps_f_within_1pct.**
   Gates: hash OK; V1 unit tests OK; V2 determinism OK; R1 bitwise replay for all 64 m OK; V6 (|sdf(S=8)|,|sdf(N0)| <= max(3SE,0.03df)) OK only because SEs are huge (S=8 sdf=-97.8 +- 118; N0 sdf=+11.4 +- 12.6); V3 (P-lin on W0 trend) OK; V7 (P-lin exact FD trace = 24 to 1e-6) OK; R7 FAILS.
   R7 numbers (D1, M=32, eps_f = 0.003/0.01/0.03 sigma0): FD mean S=8: 277/479/411 ; S=1024: 561/428/322 (df_oracle^rand 381+-7 and 407+-7). Per-sample FD sd: S=8: 2136/676/385 ; S=1024: 2031/626/252 -- roughly proportional to 1/eps.
   Wall: 4.42 s/fit -> projected Stage 1 (41k fit-equivalents) = 30,177 s (8.4 h) > 4 h cap -> also REDESIGN_WALL by rule 6 even if R7 had passed.

## 2. Post-hoc exploratory diagnostic (NOT pre-registered, n=8 samples per S, D1, same y/omega/probe streams as the pilot; outputs/DIAG_R7_response_p2.json)
Replay-frozen fit g_I(y+eps*s0*b) vs f(y); eps in units of sigma0; median ||g-f||_2 and FD = b^T(g-f)/(eps*s0):
S=1024: eps 1e-9: ||d||=0.170 ; 1e-7: 0.301 ; 1e-5: 0.360 ; 1e-4: 0.423 ; 1e-3: 0.432 ; 3e-3: 0.471 ; 1e-2: 0.556 ; 3e-2: 0.638 ; 0.1: 0.971 ; 0.3: 1.206 ; 1.0: 2.200
   FD mean(sd): 1e-3: -1076(3997) ; 1e-2: 463(514) ; 3e-2: 321(153) ; 0.1: 349(76) ; 0.3: 341(40) ; 1.0: 400(36)
S=8: ||d|| at 1e-9: 0.226 ; 1e-5: 0.455 ; 1e-3: 0.500 ; 1e-2: 0.731 ; 0.1: 1.009 ; 0.3: 1.354 ; 1.0: 2.237 ; FD mean(sd): 1e-2: 821(729) ; 0.1: 459(151) ; 0.3: 383(61) ; 1.0: 404(35)
=> A perturbation of norm ~5e-9 (eps=1e-9 sigma0) already changes the 600-step replayed fit by 0.17-0.23 in L2 (for scale: ||f||_2 ~ 23, noise norm sigma0*sqrt(N) = 5.1): the map y -> f(y; omega, I) is numerically chaotic/non-smooth below eps ~ 0.05 sigma0 although it is bitwise deterministic. The response floor does not shrink with eps, so FD noise ~ rho/eps. FD becomes low-variance only at eps >= 0.1-0.3 sigma0.

## 3. Other pilot observations (exploratory reading of the pilot data; the gates above were not designed for them)
- Oracle df (antithetic, secondary estimator, M=32): S=8: 391.9+-5.4 ; S=1024: 416.6+-5.8 (diff ~25 +- 8). Rand-covariance df: 380.9+-7.1 vs 407.2+-6.9 (diff 26 +- 10). N0 (no births): df 201.7+-4.2.
- Full-pipeline MC divergence (re-search at perturbed y, J=2, 64 probes): eps=0.3 sigma0: S=8 391.3+-8.8 ; S=1024 417.3+-10.1 ; eps=1.0 sigma0: S=8 415.4+-5.8 ; S=1024 440.1+-5.3 (by the coupled-bootstrap identity these estimate df at sigma'=sqrt(sigma0^2+eps^2)).
- Frozen FD at eps=1.0 sigma0 (diag, n=8): S=1024: 400 ; S=8: 404. Crude "sdf at sigma' = sqrt(2) sigma0" = full - frozen: S=1024 ~ +40, S=8 ~ +11 (expected 0). Large SEs (>=13); suggestive of a search contribution of order 5-10% of df, but this is post-hoc and under-powered.
- P-lin (forward stepwise, 1024 atoms, 24 selected): FD df_frozen = 24.0 exactly (V7) ; on W0 (pure noise) sdf = 0.06+-0.5 (S=8), 13.4, 40.6, 59.0, 65.6+-0.8 (S=1024): the oracle/frozen pair machinery recovers the Tibshirani search-df on a linear selector. On D1 (signal): sdf(1024)-sdf(8) = 14.3+-8.5 (selection partly stable). 
- Rule 7 (record-only): N0 excess-variance items recorded in outputs/F0-pilot-p2fast/ANALYSIS.md.

## 4. Deviations to rule on
D-01: contract section 5 lists MC probe stream 6 as [img,m,j,eps]; code uses [img,m,j] (same probe across eps for a given m,j). Each eps estimate is still unbiased; only cross-eps pairing differs. Proposed: register as deviation (hash unchanged) or amend in v3.
D-02: fast fitter as above (implementation-only; same model; equivalence evidence above). Proposed: accept; keep torch path as reference.

## 5. My reading (challenge it)
(a) INVALID is the right reading: df_frozen as a local FD divergence is not identified for this 600-step Adam pipeline; this is a property of the pipeline (chaotic optimisation map), not a bug (replay bitwise, P-lin exact, equivalence tests pass, response floor present for both fitters is plausible but I only measured the fast one).
(b) Consequence for the estimand: birth-index selection is not the only discontinuity-like mechanism; basin selection by the optimiser behaves like implicit search and is NOT removed by replaying I. So "frozen" isolates only index selection, and the Stein divergence that matters is a smoothed (scale ~sigma0) object anyway.
(c) The measurable oracle effect (df up ~25 of ~400 between S=8 and S=1024, z~3) is real-looking but cannot yet be attributed to selection vs different atom placement.
(d) Compute: at 1.3 fits/s a 4 h Stage 1 holds only ~18.7k fits (45% of the planned 41k).

## 6. Redesign options (choose, modify, or reject)
A. Smoothed/fission definition: sdf_eps := DIV_full(eps) - DIV_frozen(eps) both at eps in {0.3,1.0} sigma0 (noise level sigma'), with the frozen map's selection taken from an independent fission copy y^- = y - (sigma0^2/eps) b so that selection is independent of the data being fit; same coupled-bootstrap machinery as T3; R7 replaced by an eps-matched consistency/identity check (S=8 must give 0 within SE at each eps; P-lin must still recover the known sdf).
B. Drop the frozen leg: estimand = oracle df contrast df(S)-df(8) plus a placement-matched parametric control (births at random positions but with the same marginal placement law as the S-selected ones); H1 on the contrast; no FD.
C. Make the fit map smoother (fewer steps, SGD/lr schedule, or averaged iterates) so the local divergence exists -- changes contract section 2; justify or reject.
D. Declare the replay-FD estimand non-identifiable, STOP this estimator line, keep only the descriptive result (oracle df rises with S on D1, P-lin positive control) and decide pivot vs headroom.
E. Anything else you consider the minimal sound contract v3.

## 7. Questions
Q1. Verdict on the pilot: confirm INVALID(R7)/REDESIGN_WALL as the correct contract outcome; is any part of it salvageable as evidence, and which post-hoc numbers (section 2-3) may be cited and how (labels)?
Q2. Which option (A-E or a modification) should become contract v3? State the estimand, the validity gates replacing R7, the pilot, and the decision rules; flag any new bias toward continuing.
Q3. Stage 1 sizing under ~1.3 fits/s and 4 h (<= ~18k fits): what to cut or keep; may the number of images/S-levels/M be reduced without destroying H1/H2 (state minimal M, images, S levels)?
Q4. Rule on D-01 and D-02 (accept / amend / re-run).
Q5. Go / Revise / Stop for the mechanism line at this point, and whether any GPU work is justified (current rule: no GPU until contract + headroom evidence + idle check).
Final line: one of  GO-v3(list) | REVISE-v3(list) | STOP(reason) -- plus explicit gates for the next pilot.
