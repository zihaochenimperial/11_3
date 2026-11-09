claude-opus-5-5
# Opus review: AS-S2 analyzer erratum (FAIL-0025) and re-check of verdict C

Reviewer: independent scientific gate. Inputs: OPUS_PACKET_AS_ERRATUM_20261106.md (read in full), my earlier OPUS_REVIEW_AS_DIRECTION_20261106.md, /home/claude/AS_S2_negative_result_20261106.md. I did not re-run, re-hash or open the analyzer, the erratum script or the reports. Every number below is taken from the packet as reported. Status before and after this review: 0 validated contributions.

**Recommendation, up front:** The erratum is sound. STOP-Q1 still holds, and the discrepancy-principle readout makes it hold under a second stopping rule too. Verdict C stands for the JOINT/selection line. I am changing one thing. C is no longer "wait with only a stop menu". There is one bounded next node, R: a read-only re-analysis of the existing S2 trajectories. R separates selection headroom from stopping headroom. It needs a frozen addendum before anything is computed. It is the cheapest step that decides whether any further Gaussian-growth experiment deserves the human's time. The image-space-constraint idea from the external advice was never tested. It stays a human-approval item, and R's outcome informs it.

## Q1. Erratum: faithful? Is STOP-Q1 still correct? What does it kill?

**Answer: yes, it is faithful, and STOP-Q1 is the correct mechanical outcome.**

Why it is faithful:
- The contract defines Gate 1 on KEYS (192 units). Restricting every arm to KEYS is the only reading of the contract. It adds no analyst degree of freedom.
- The frozen functions are imported unmodified. Reproducing the unrestricted run to 1e-9 shows the restriction is the only change.
- The plan was written before computing, and the original report is preserved.

Points the record must state:

1. **Dose-response and D03 handling.** "Every arm restricted to 192" also removes the 24 D03 units from whatever the dose-response readout uses. Either the erratum's dose-response numbers are empty or invalid, or they are inherited from the original run. The record must say which. The correct source for the dose-response readout is the original report, where D03 is supposed to be included. Check that the original dose-response code did not itself mix main and D03 units. The packet does not say.
2. **Aux arms.** Gate 0, H and F already used explicit KEYS, so restricting the aux arms is a no-op for them. The identical values confirm this. Say so explicitly, so nobody reads "identical" as an independent replication.
3. **Single-run rule.** This is a second invocation of the analysis functions. It is legitimate only as an erratum that applies a contract-dictated filter. It is not a re-analysis. Keep the label "erratum, FAIL-0025". Do not let "analyzer run twice" become a precedent for further re-runs.
4. **What "same verdict" supports, and what it does not.** It supports this: the decision is robust to the bug. Flags (i)-(iii) fail in both versions, and (iv) alone cannot rescue Gate 1. It does not support "the bug was immaterial". Flag (iv) flipped from True to False, the family-edge mean changed sign (-0.0097 to +0.0056), and p moved from 0.130 to 0.211. Any document that quotes the old values (meanD -0.034, p 0.130, "(iv) passes", edge family <= 0) is now wrong. Every correction moves against JOINT, so the error flattered the method under test. Record that direction.
5. **The deviation-principle diagnostic.** It is contract-required and carries no decision weight. Keep it that way. Its numbers are now seen post hoc, so they must not be promoted into a gate.

**What STOP-Q1 now kills:**
- On this benchmark, training-loss compensation-aware candidate scoring (JOINT) plus full LM refit is not better than cheap rules (OMP, BLOCK) at gate level.
- This holds at the fixed K_max=36 endpoint and also at one matched, principled stopping rule (discrepancy principle):
  - JOINT vs OMP: -0.022, p 0.21.
  - JOINT vs BLOCK: -0.029, p 0.16.
  - Flags (i)-(iii) fail for both comparisons.
- The second point is new and real. The JOINT failure is not only an over-growth artefact of the fixed endpoint.
- Gate F, "growth has independent value vs fixed K on this benchmark", is unchanged and still killed.

**What it does not kill:**
- Selection criteria that are not training-loss based.
- Any explicitly regularised or image-space-constrained geometry update.
- Gaussian representations on other content, degradations or real data.
- The existence or absence of selection headroom under proper stopping. That is open; see Q4.

## Q2. Are the corrected statements right? Anything else to correct?

**Answer: both corrections read right. Tighten the REG wording, and fix four other items.**

- **REG wording.** "No systematically tuned, task-matched regulariser or stopping rule" is accurate. Add the scale. With loss 0.5||r||^2 ≈ 430, a 1e-6 Σa² term is at most a few tenths unless amplitudes are in the hundreds. It works as a numerical-stability ridge, not as a regulariser. So "effectively unregularised in amplitude" is still true in substance. My earlier "unregularised least squares" was literally wrong and substantively right.
  - The box clamps on position and scale are a real implicit regulariser. A lower scale bound limits how much high-frequency detail, and so how much noise, one Gaussian can fit. My earlier review ignored them.
  - Record the clamp values next to the REG statement.
- **Scope wording.** This one is right and important. S2 kills one implementation: JOINT training-loss scoring plus LM refit. It did not test the image-norm bound or spectral-filtered geometry update.
  - Also state the novelty status: such an update is regularising Gauss-Newton / LM-as-regularisation (Hanke-type regularising LM, iteratively regularised Gauss-Newton, Bakushinsky), applied to Gaussian parameters.
  - So "untested" must not be read as "novel". This is from memory at L2; it needs a G0.
- **Other corrections needed:**
  1. **S2 note §2 table.** Replace the Gate-1 rows with the 192-set values. Change "(iv) 族 2/3 <=0 过" to "(iv) fail" and mark the change as FAIL-0025. Same for the family means. Any decision memo that quotes them (e.g. AS_direction_decision_memo_20261106) also needs the update. I could not read that memo; check it.
  2. **S2 note §4 "没有杀死".** Add "a principled stopping rule (discrepancy principle) does not rescue JOINT (diagnostic, no decision weight)". Add "image-space constraint untested".
  3. **Step count.** The packet says "stopping index ~13 of 30 steps" while K_max=36. Write explicitly whether the index counts births, Gaussians, or steps after some number of initial Gaussians. Also give the discrepancy factor τ and the noise σ used, known or estimated. "Stops at 13" means nothing without them.
  4. **My earlier review, Q3 and Q5.** "No stopping" should read "fixed-endpoint stopping only". "Unregularised" should read "numerical ridge 1e-6 plus box clamps, no tuned regulariser". Neither change alters those arguments; see Q3.

## Q3. Does C still stand?

**Answer: C stands for the JOINT/selection line. The two corrections do not rescue A or B. I replace "wait" with one bounded, read-only next node, R.**

What does not change:
- The REG correction does not change the Q3/Q5 premise. A 1e-6 ridge does not control noise amplification under strong blur.
- The collision findings for A and B are unchanged:
  - search-df / SURE-GCV risk correction: F0/H2, 2308.13630;
  - held-out or fission stopping: CF0 report-only, OMP-CV;
  - randomised greedy as regularisation: 2506.15643.
- None of these may be revived under a new name. Specifically, R and anything after it must not use fission/held-out CV stopping or a search-df penalty as the tested variable.

What changes:
1. The discrepancy readout extends the JOINT kill to matched stopping. That strengthens C for JOINT.
2. The scope correction means the "capacity/geometry control" mechanism has not been tested by S2. It has only had one implementation killed. That removes my implicit support for ending the whole Gaussian-capacity mainline on S2 alone. The human still decides that.
3. The open question that matters most is Q4: did S2's Gate-0 headroom survive proper stopping? It can be answered without new fits.

**The one next node: R (read-only selection-vs-stopping decomposition on existing S2 trajectories)**

- **Hypothesis.** At matched principled stopping, ORACLE_xs still beats the cheap rule (BLOCK) by at least 10% geometric-mean MSE on the 192 set. Matched stopping means the discrepancy-principle index, each arm at its own index, with the frozen τ. That would be selection headroom. If the margin collapses, the 45% at K=36 was stopping headroom, i.e. over-growth.
- **Readouts, fixed in advance.**
  - (a) H_Oxs at each arm's discrepancy stop.
  - (b) H_Oxs under oracle stopping, i.e. each arm at its own best-step clean MSE. This is a pure upper bound that isolates selection from stopping.
  - (c) RAND, JOINT_FREE and FIXED vs BLOCK at the discrepancy stop.
  - (d) Per-condition (C1-C4) versions of (a).
  - Report all four. No other cuts.
- **Kill criterion.** If (a) < 0.10, or the paired sign-flip interval over the 24 images includes 0: the "which edit to pick" axis is closed on this benchmark. S2's Gate-0 PASS is then re-labelled "stopping headroom, not selection headroom" in the record. In addition, if (b) < 0.10, the axis is closed even for a perfect stopping rule.
- **Survival does not validate anything.** If (a) >= 0.10, the result is still post hoc on dev data. It only justifies asking the human for the fresh-data headroom check from my earlier Q2, under a new G0, contract and freeze. Fresh dev and confirmation images, E41-58 sealed.
- **Data and stopping safeguards.**
  - Use only already-written S2 trajectories and the frozen τ/σ from the contract's deviation diagnostic. No new fits and no new images.
  - Before computing, run a structure-only check that per-step clean MSE, or per-step parameters, exist for ORACLE_xs, BLOCK, RAND, JOINT_FREE and FIXED. If they do not, R becomes "needs re-fit", and that is a new experiment that needs the human.
  - Write addendum I (plan, thresholds, closure-only decision weight) before computing. Then a light Opus check of the addendum, then one run.
- **What needs the human.** R itself does not, provided the addendum is frozen first and it stays read-only. Any action on R's outcome does: the fresh-data check, an image-space-constraint arm (regularising-LM-type update plus a TV baseline), or closing the overall mainline.
- **Honest expected value.**
  - R costs minutes of CPU. It mostly buys closure.
  - My prior is about 60% that (a) falls below 0.10. With about 250 parameters against 1024 pixels and arms stopping near 13 of 30, much of the K=36 margin should be over-growth.
  - Contribution probability from R is ~0. It is a benchmark diagnostic.
  - It is still the right next node. The two alternatives (fresh-data headroom, image-space constraint) are both worth less if R shows the headroom was stopping all along. R's outcome also tells the human which of the two to fund. Collapse points to regularisation, i.e. the image-space arm against TV. Survival points to the selection headroom check.

## Q4. Is the discrepancy result informative about the Q5 over-growth risk?

**Answer: partly. It confirms the precondition of the risk but does not test the risk itself.**

What it shows:
- With a principled stopping rule, all three data-fit arms stop at about 13 of 30 steps. So the K_max endpoint is far past the point where the residual reaches the noise level. Over-growth at the S2 endpoint is now likely, not hypothetical, conditional on τ and σ being sensible (see Q2, correction 3).
- JOINT still does not win at that stop, so JOINT's failure is not explained by over-growth.

What it leaves open:
- The Q5 risk is about ORACLE_xs's 45% Gate-0 margin, and the RAND/JOINT_FREE > BLOCK ordering, being over-growth artefacts.
- The diagnostic reports neither of these at the stop. That risk is still fully open.

The cheap read-only computation that closes it is node R (Q3): readouts (a)-(c), and (b) in particular separates selection from stopping cleanly.
- **Does it need a new plan or addendum? Yes.**
  - It is a new analysis on dev data whose endpoint results are already known.
  - ORACLE_xs, RAND, JOINT_FREE and FIXED were not in the contract's deviation diagnostic, so it probably needs a small new script, not the frozen functions.
  - The oracle-stopping readout (b) is not in any contract.
- Write addendum I with the readouts and kill thresholds above before computing. Run it once. Report every number. Label it "post-hoc diagnostic, closure-only weight".

## Caveats (one place)
- I did not verify any hash, file or number. Everything rests on the packet.
- The literature statements are at L2-L3. That includes the regularising-LM/IRGN neighbours, which I named from memory and did not check.
- n = 24 images in the sign-flip tests, so p-values near 0.2 carry little information either way.
- The roughly 60% prior in Q3 is my judgement, not an estimate from data.
- R uses dev data that has already been read. It can close things; it cannot open them.
