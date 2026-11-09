# Narrow Opus confirmation (GEO-2, pre-H): interpretation boundary after the dry-run exposure of test images 201-204

You are the real Opus scientific gate for this narrow question (not a re-review of the whole contract). Please state your self-reported model id at the top of your answer.

## What happened (facts, all in the files below)
- During container dry-runs (reduced config, artificially censored arms) the analysis scripts were run on the formal hold-out test images 201-204 and printed analysis values (censor rates, clause booleans, quality H with intervals, wall-clock ratios, Q2/Q1 labels). Images 205-224 were never analysed. FAIL-0029 (memory/FAILURES.md on the device; text reproduced in K2_DRAFT.md) and K1.11 (device: contracts/FROZEN_GEO_CONTRACT_v2.md, last section) record this. No rule, threshold or config was changed afterwards (the only code edit is a min(12, len(TEST_IMGS)) robustness fix with no effect on the 24-image configuration).
- Phase D (tuning, caps, lambda*, arm selection) uses dev images 101-112 / base 9101 only; none of it reads images 201-224. Phase D is running now; no formal H result exists.
- The supervisor (Codex, read-only, via the human) asks: (1) log the exposure as a process failure (done: FAIL-0029); (2) have Opus confirm the interpretation boundary inside the existing review; (3) keep the frozen 24-image metrics and criteria; (4) pre-register a same-calibre result on the 20 unexposed images; (5) disclose the 4-vs-20 difference; (6) the full 24 cannot be called unseen independent evidence; if a conclusion depends on the 4 exposed images it waits for fresh data; (7) do not change metrics/thresholds/config and do not rerun finished phases.

## What to read (container paths)
- /home/claude/geo/K2_DRAFT.md  — the proposed K2 addendum text (to be appended to the frozen contract if you accept it; placeholders @@DATE@@, @@OPUS_K2@@).
- /home/claude/geo/experiments/geo_analyze_unexp.py — the pre-registered 20-image view (imports the unchanged frozen geo_analyze.py; a dry test on dry-run outputs ran without error).
- /home/claude/geo/K1_FINAL.md and /home/claude/geo/experiments/geo_analyze.py for the frozen readings (cmd_h_q2, cmd_q2_quality, cmd_h_timing, cmd_q2_label, cmd_h_q1).

## Questions (answer each ACCEPT / ACCEPT-WITH-CHANGES / REJECT with a minimal concrete fix; no new research programme)
- Q-k1: Is K2.2 an adequate and honest interpretation boundary (24-image primary retained with disclosure; pre-registered 20-image view; the consistency rule in item 4)? Is the wording "must not be called fully unseen independent evidence" sufficient, or must something stronger be said?
- Q-k2: The 20-image image-count floors are scaled to the same 50% (10 of 20; ceil(0.5*n_t) for timing when n_t >= 4; otherwise NOT EVALUABLE). Is that a legitimate "same-calibre" derivation (no new threshold of substance), or must the absolute floors 12 and 6 be kept?
- Q-k3: Does any causal path from the exposed dry-run values to any frozen choice or decision rule exist (caps, lambda*, arm tuning, compression plan, rule edits)? Is any further disclosure needed before the first formal H run?
- Q-k4: Is the consistency rule (labels differ in any per-K Q2 label or Q1 label, or the 20-image view is not evaluable => "depends on exposed images", no ADVANCE) correct and not itself biased towards or against a positive finding? Should it also apply to the 'JOINT-MATTERS' decision only, or to all labels as drafted?
- Q-k5: Anything else that must be done before the first formal H result becomes visible?

## Output
Append your answer to /tmp/claude-0/-home-claude/c30445bf-b91f-5725-a565-964b312260f4/scratchpad/AS/OPUS_REVIEW_GEO_PRED_ADDENDUM_20261106.md under a new heading "## K2 exposure-boundary check (Q-k1..Q-k5)" (append only; do not edit other files), then return a short summary (verdict per question, required text changes, your self-reported model id). Keep it concise.
