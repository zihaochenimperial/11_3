# Post-hoc exploratory note (NOT preregistered; Stage 1 data, x known to the evaluator) — 2026-11-05T12:35:35Z
Written after Stage 1 results and after the Opus H1/H2 gate. Candidate lead only; 0 validated; no claim.
Quantity: oracle risk E||fit - x||^2 (sum over 4096 px; mean over 32 draws x both fission legs = 64 values/image), S=1024. F = births selected on the fit's own copy; G = same copy's fit with births taken from the independent copy (frozen leg). Both at noise sigma'=sqrt2*sigma0.
| image | type | risk F(S=1024) | risk G | G-F (+-SE) | risk F(S=8) |
|---|---|---|---|---|---|
| E3 | D3 | 18.578 | 18.682 | +0.104 +- 0.156 | 20.793 |
| E4 | D1 | 4.160 | 3.688 | -0.472 +- 0.053 | 3.953 |
| E5 | D2 | 6.752 | 6.619 | -0.134 +- 0.068 | 6.983 |
| E6 | D3 | 31.552 | 32.794 | +1.242 +- 0.463 | 37.942 |
| E7 | D1 | 4.636 | 4.177 | -0.459 +- 0.053 | 4.443 |
| E8 | D2 | 6.784 | 6.578 | -0.206 +- 0.067 | 7.139 |
| E9 | D3 | 39.312 | 40.311 | +0.998 +- 0.448 | 44.542 |
| E10 | D1 | 4.430 | 3.963 | -0.467 +- 0.057 | 4.131 |
| E11 | D2 | 6.764 | 6.636 | -0.128 +- 0.071 | 7.149 |
| E12 | D3 | 11.276 | 11.262 | -0.015 +- 0.193 | 13.249 |
| E13 | D1 | 5.722 | 5.326 | -0.396 +- 0.057 | 5.406 |
| E14 | D2 | 7.033 | 6.897 | -0.136 +- 0.057 | 7.293 |
Reading (cautious): G<F on 9/12 images; D1 and D2 images (8/8) show G better by 0.13-0.47 (about 2-10% of risk; on D1 G(S=1024) also beats F(S=8)); D3 images (high-risk) show G worse or tied (E6 +1.24, E9 +1.00). Mean difference over images is ~0 because the D3 images dominate the scale. Confounds: G keeps the value initialisation of its own copy; both legs run at sigma'=sqrt2*sigma0 (a real single-image cross-fit would fit a noisier copy than the full data, losing information); type is confounded with image difficulty (n=4 per type). Likely prior art to check before any claim: sample-splitting / cross-fitting for selection, winner's-curse corrections, data fission (Leiner et al.), coupled bootstrap (Oliveira/Lei/Tibshirani — named by Opus, not verified). This would be a METHOD lead (cross-fitted birth selection), not the estimator line; needs a new G0 nearest-work pass, a new contract and an Opus gate; a mainline change is the human's call.
