# GLM task 004c — NARROW read-only audit (attempt 3). Do NOT edit files. Files are frozen during this audit.
Read ONLY: contracts/F0_CONTRACT.md (sections 2,3,4,5), experiments/f0_run.py, src/gsfit.py, src/omega.py. Read each once. Think briefly. Your FINAL message must be plain text, at most 25 lines, in this exact form (no tool calls after you start the final message):
LEAKAGE: <ok|problem + file:line>
SEEDS-S-INDEPENDENT: <ok|problem + file:line>  (noise stream 1 [img,m], omega stream 2 [img,m], probes 3/6/9/11 must not depend on S; fix omega stream 8 must not depend on m or S)
REPLAY: <ok|problem + file:line>  (forced_idx path identical to selection path except the chosen indices; runner asserts np.array_equal for every m and aborts)
FD-FORMULA: <ok|problem + file:line>  (FD_m = b.(g(y+eps_f b)-f(y))/eps_f with eps_f=rel*sigma0 absolute; base term is f(y); same omega)
ANTITHETIC/MC/SIGMA-RESIM: <ok|problem + file:line>
CONTRACT-COUNTS: <ok|problem>  (S grid, M, Mmc=64 J=2 5 eps, T3 cells eps in {0.3,1.0} S in {8,256} 256 samples, fix 4x128, conv D1 S{8,1024}, pilot sizes)
OTHER: <anything that could bias sdf(S) with S, or "none found">
Start the final message directly with "LEAKAGE:".
