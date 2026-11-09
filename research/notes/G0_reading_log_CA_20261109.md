# G0 reading log — CA node (independent failure attribution), 2026-11-09

Purpose: record what was actually read, at what depth, and what each neighbour does and does not pre-empt, before the CA contract is written. "Read" means read by this orchestrator (Sonnet 5.5) in this run; "relied on" means taken from the Codex/Claude-research notes without re-reading the source. Nothing here is an originality claim.

## Documents read in this run
| Source | Depth | Use |
|---|---|---|
| `runs/codex-monitor/20261109-post-jr-research/CLAUDE_JR_CAUSAL_CONTINUATION_ZH.md` | whole file (the authorisation) | scope of node 1, requirements for the factorial and the diagnostics |
| `.../SOURCE_MATRIX_ZH.md` (Codex) | whole file | neighbour map, errata (Feng–Kao retracted; σ√M is a whole-image norm; "certificate" -> feasible witness only), PCAT/BUQO bounds on novelty claims |
| `.../CLAUDE_RESEARCH_ORIGINAL_ZH.md` (Claude research, ~50 kB) | lines ~1–380 of 466 read; remainder skimmed only | OGCS/GSP-PUQ proposals, source table. Treated as hypotheses, not as verified facts |
| JR terminal artefacts (`verify_REDUCE.txt`, Opus terminal review, FAIL-0035) | whole | what JR did and did not show |

## Neighbour table (what is already done by others; what the CA node may therefore NOT claim)
| Neighbour | Read depth (this run) | What it already does | Consequence for CA |
|---|---|---|---|
| PCAT (Brewer, Foreman-Mackey, Hogg; arXiv 1703.01303) | §III.1–3 read via Codex check + own skim | known PSF; infers catalogue, number of sources and neighbours; "one bright vs two dim sources" is its own motivating ambiguity | the idea "a blurred bright blob can be one or two things, with an observation-consistent alternative" is NOT new; CA only measures when a search method's failure is attributable to noise vs representation |
| BUQO (Repetti/Pereyra/Wiaux style; SIIMS) | full document read earlier in the project (G0 JR) | tests whether a structure exists in the credible set; returns a counter-image when compatible | producing a counter-image / reporting local uncertainty is not new; CA does not claim it |
| TaskUQ (Wen et al.) | abstract and §2–3 summary only | conformal intervals for downstream task quantities; marginal coverage under exchangeability | not used as an assumption; the CA verdicts are paired, finite-sample bootstrap statements on a fixed family, no coverage claim |
| AIR (arXiv 2605.20820) | abstract / method paragraph (via Codex) only | predicts Gaussians from residuals, short optimisation distillation | "learned proposal + short refinement" is a neighbour of any later mechanism; unverified in detail |
| DDNM / DDRM / DPS | method level (Codex check of §2.2/§3.3, DDRM SVD construction, DPS Jensen gap) | range/null decomposition + noise correction; SVD-based pixel posterior; approximate posterior sampling | noise-corrected range/null reasoning is old; the DPS Jensen gap is the likely referent of the handoff's "Jensen" (interpretation, unverified) |
| StarNet / BLISS ("Hansen" in the handoff = BLISS, Hansen et al.; interpretation, unverified) | abstract-level only | amortised posterior for overlapping point sources; blockwise variational factorisation; deterministic deblender after sampled detections | cross-domain transfer / outputting several Gaussian sets is not a differentiator |
| López-Tapia et al. (Moore–Penrose deconvolution + learned null-space) | via Codex (Eq. 2–4) | Wiener pseudo-inverse + learned null-space compensation | "physics part + learned residual" is a neighbour of later INR/learned arms |
| Li & Chi (AtomicDemix / super-resolution of point sources) | via Codex (§1–2) | stable separation under band-limit/spacing assumptions | assumptions differ from CA's additive-pixel-noise 2D blobs; not a general deblurring bound |
| Optical one-vs-two source discrimination (arXiv 1609.03025) | via Codex | hypothesis testing of one vs two sources | direct experimental-idea neighbour for the E-B line-pair diagnostic; photon model differs |
| Raue et al. profile likelihood (Bioinformatics 2009) | via Codex | re-optimise nuisance parameters along the target direction to diagnose practical identifiability | the neighbour-refit (Schur/projection) diagnostic is a standard building block; fixed vs refit are reported separately |
| Explorable Super-Resolution (CVPR 2020) | via Codex | multiple consistent outputs | outputting several consistent images is not an increment |
| Strict bounds for constrained inverse problems (arXiv 2310.02461) | via Codex | frequentist feasibility/coverage control | reminds that likelihood feasibility and coverage are separate; finite candidate sets must disclose missed solutions |
| Feng–Kao arXiv 2602.09415 | not used | retracted (author-noted major error) | excluded as evidence |
| Zach et al. statistical benchmark (2509.12821); astronomical diffusion deconvolution (2411.19158); Zhang defocus blobs (ICCV 2025) | abstract-level via Codex | Gibbs posterior reference and coverage; prior-driven features; Gaussian blobs in defocus deblurring | listed as neighbours; no CA design depends on them |

## Reading limits (honest)
- Only one of the neighbours (BUQO) was read in full by me; the rest are at abstract/method-paragraph level or relied on from Codex. A "not pre-empted" statement about CA can therefore not rest on this table; the CA node is an attribution experiment inside this project, not a novelty claim.
- The Claude-research table contained claims I did not verify (e.g. a 2610.29102 preprint); none is used.
- The handoff's "Hansen/Jensen" is interpreted as BLISS (Hansen et al.) and the DPS Jensen gap; if the human meant something else this entry must be corrected.

## What this means for the design
1. Node 1 is internal: it asks WHY the focal grouped joint repair underperformed its controls in JR, using a fresh, paired, preregistered factorial. No neighbour above answers that, and none is claimed to.
2. The group-ambiguity diagnostics (E-B) are standard hypothesis-testing / profile-likelihood constructions evaluated on this project's own forward model; they are used to measure when finite ambiguity exists at all, not to propose a new detector.
3. Any later "ambiguity-aware recovery" mechanism must be compared on equal budget with the strong baselines (independent-single primitive, grouped-random, INR reference with equal budget) and must reduce real structural errors; otherwise it is a diagnostic, not a method.
