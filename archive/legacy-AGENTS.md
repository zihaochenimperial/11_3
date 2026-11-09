# Research execution contract

- This repository concerns P1817 and P1901 only. Do not open or modify FATE, MOE_OPD, or other coursework repositories.
- Maintain separate source, environment, data, and output directories for the two tracks. Record exact upstream commits and licenses.
- Label every claim as theoretical derivation, literature observation, infrastructure smoke, development experiment, or independent test result.
- No clean test images, held-out pixel values, or independent test data may enter model proposals, fitting, checkpoint selection, or hyperparameter tuning.
- For P1817, separate fit/proposal pixels from selection pixels; selection pixels are not an independent final audit. Freeze decisions before testing on untouched images.
- For P1901, measure actual encoded file bytes and decoded distortion; account for all wall-clock time including exploration, warm-up, quantization, and final bitstream production.
- Run at most one GPU experiment at a time, even if many literature or code-reading agents work in parallel.
- Keep a fixed evaluator and immutable inputs during each autoresearch sweep. Every run records config, seed, upstream commit, hardware, time, metric, and failure status. Do not optimize on the final test set.
- Main research work: prefer Claude Opus 5.5 when a genuinely available authorized Claude session can execute it; on quota exhaustion or unavailable integration use Codex GPT-6.1 Terra high, escalating hard problems to GPT-6.1 Sol high. Record actual model, availability and fallback; never silently claim Claude ran. Cheap OpenCode roles remain unchanged. The active coordinator owns hypotheses, contracts, promotion and final claims.
- Every scheduled continuation reads research/RESEARCH_OPERATING_MEMORY_ZH.md, PLAN.md, CHECKLIST.md and current evidence/status before dispatch. Preserve the scientific and compute boundaries above.
- Avoid proprietary or paid APIs unless already available to the user. Never put plaintext credentials in this repository, commands, or logs. A Windows-account-protected local credential store is allowed for the user's already-authorized OpenCode Go connection.
