"""GEO deterministic work proxy W: frozen flop-formula table (pre-D addendum, item A1.1 of the GEO contract v2; the sha256 of this file is recorded in the
append-only freeze record BEFORE any phase-D calibration).
Every function returns a floating-point-operation ESTIMATE. Vector operations and O(p^2) work are ignored; matrix-vector products with a stored matrix are charged 2*nnz.
Notation: N image side, m = N*N pixels, p = 6K parameters, K Gaussians, rho retained rank, nnz = stored nonzeros of the (dense: p*m) image Jacobian J.
Implemented operator A: separable dense B (N x N), A X = B X B^T  ->  F_A = 4 N^3 (two N x N x N matmuls)."""


def F_A(N):                  # one A or A^T application to ONE image
    return 4.0 * N ** 3


def F_render(K, N):          # (re-)render K Gaussians on an N x N grid (exp + a few multiplies per pixel and Gaussian)
    return 10.0 * K * N * N


def F_jbuild(nnz):           # value + 6 derivative maps: full J or per block (30 flops per stored entry)
    return 30.0 * nnz


def F_matvec(nnz):           # J v, J^T v, (AJ) v, ...: 2 flops per stored entry
    return 2.0 * nnz


def F_svd(m, p):             # thin SVD of an m x p matrix
    return 4.0 * m * p * p + 8.0 * p ** 3


def F_gram(m, q):            # B^T B for an m x q matrix
    return 2.0 * m * q * q


def F_eigh(q):               # symmetric eigendecomposition of a q x q matrix
    return 9.0 * q ** 3


def F_chol(q):               # Cholesky factorisation + solve of a dense q x q SPD system (dense LM arms)
    return q ** 3 / 3.0


def F_gemm(m, p, q):         # (m x p) @ (p x q)
    return 2.0 * m * p * q


def F_block_solve(K, m):     # batched per-Gaussian block step: K thin SVDs of m x 6 + gemm AJ_k V_k + Gram + eigh of K 6x6 blocks
    return K * (4.0 * m * 36 + 8.0 * 216 + 2.0 * m * 36 + 2.0 * m * 36 + 9.0 * 216)
