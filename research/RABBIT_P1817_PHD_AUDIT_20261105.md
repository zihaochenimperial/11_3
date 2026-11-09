# ResearchRabbit browser observation — P1817 PhD novelty audit

Date2026-11-05. Literature observations only; no novel-method efficacy claim or experiment authorization.

Authenticated ResearchRabbit session used via browser UI. New search: https://app.researchrabbit.ai/search/94483736-2386-4764-a67a-ee76dcd234f1/

Query `Gaussian splatting inverse problems`: first visible hit Feng2026, *Stability and Concentration in Nonlinear Inverse Problems with Block-Structured Parameters: Lipschitz Geometry, Identifiability, and an Application to Gaussian Splatting*. Selected as seed. Primary source independently located: https://arxiv.org/abs/2602.09415 and https://arxiv.org/html/2602.09415v1 . Its abstract claims operator-level stability, concentration and resolution-complexity tradeoff. Claims in a preprint are not independently validated theorems.

Query `Image-GS`: selected Zhang2024 *Image-GS: Content-Adaptive Image Representation via2D Gaussians*, https://arxiv.org/abs/2407.01866 . Clicked Grow: UI confirmed2 seeds,10 results,503 available recommendations (Analyze513 includes network pool; not513 papers read). Visible recommendations: GaussianImage2024, WIRE2023, SIREN2020, InstantNGP2022, original3DGS2023, gsplat2024,2DGS surface reconstruction2024,4DGS2023,LPIPS2018. Some duplicate SIREN records. This expansion is predominantly background, not evidence of an empty novelty gap. Surface2DGS must not be confused with2D image Gaussian representation.

Coordinator primary-source supplementary search located: FisherRF official https://github.com/JiangWenPL/FisherRF ; PUP3D-GS https://arxiv.org/abs/2406.10219 (second-order sensitivity pruning); Rendering-Aware Bayesian3DGS https://arxiv.org/abs/2607.05522 (geometry posterior, calibrated uncertainty, complexity signal); these directly challenge generic Fisher+uncertainty+adaptive complexity claims.

Additional UI searches completed: `FisherRF` returned both Jiang2024 conference and Jiang2023 preprint versions; selected the2024 record. `Rendering-Aware Bayesian3D Gaussian Splatting` returned Jia2026, PUP Hanson2024,3DGS as MCMC Kheradmand2024,VBGS-SLAM2026, and other confidence work. Selected Jia and PUP. Clicked Grow again: UI confirmed5 seeds and20 recommendation results,25 nodes total,773 available recommendations,Analyze793. These are displayed counts, not papers read or independent citations.

New visible recommendations include *Reducing the Memory Footprint of3D Gaussian Splatting* (Papantonakis2024; abstract explicitly describes per-Gaussian adaptive SH coefficients), Mini-Splatting, Compact3DGS,LightGaussian,RadSplat. This directly weakens a generic claim of per-Gaussian adaptive degrees of freedom. Task-specific geometric direction control under a degradation operator remains to be compared method by method. Rabbit metadata contains errors (e.g. RadSplat venue label), so bibliographic facts require primary verification.

Final network URL: https://app.researchrabbit.ai/search/94483736-2386-4764-a67a-ee76dcd234f1/a62048d2-fa2a-492b-ab4c-4c9cfad310aa/grow . Search is bounded and cannot certify global originality. Browser-observed abstracts and recommendations are discovery evidence, not independent method validation.
