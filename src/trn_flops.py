"""TRN work proxy additions (contract TRN v1 section 5). Same convention as the frozen geo_flops.py (floating-point-operation ESTIMATES; vector ops O(p) ignored unless they are
O(p k) or O(p n k); a stored-matrix product is 2 nnz). geo_flops is imported read-only; this file only ADDS formulas for the TRN arms. sha256 is recorded in contracts/TRN_FREEZE_RECORD.txt
BEFORE any formal accounting."""
import geo_flops as FL

F_A, F_matvec, F_jbuild, F_render, F_gram, F_eigh, F_gemm = FL.F_A, FL.F_matvec, FL.F_jbuild, FL.F_render, FL.F_gram, FL.F_eigh, FL.F_gemm


def F_H_matvec(N, nnz):          # one H v = J^T (A^T A/sn^2 + c I) J v : J, A, A^T, J^T
    return 2.0 * F_matvec(nnz) + 2.0 * F_A(N)


def F_cg_iter_vec(p):            # axpy/dot overhead per CG iteration (8p)
    return 8.0 * p


def F_defl_iter(p, k):           # per-iteration deflation projection  (I - W E^-1 (HW)^T): two p x k products + k x k solve
    return 4.0 * p * k + 2.0 * k * k


def F_defl_setup(p, k, N, nnz):  # RR / E = W^T H W: k H-matvecs, Gram p k^2, small pinv ~ eigh(k)
    return k * F_H_matvec(N, nnz) + 2.0 * p * k * k + F_eigh(k)


def F_qr(p, k):                  # thin QR of p x k (Householder)
    return 4.0 * p * k * k


def F_ritz_extract(p, n, k):     # Lanczos-vector combination Q Y_sel (p x n times n x k) + small tridiagonal eigendecomposition
    return 2.0 * p * n * k + F_eigh(n)


def F_block_jacobi_build(p, K, N, m):   # strict accounting: p A-applications (AJ columns) + per-Gaussian 6x6 Gram (2 m 36) + inverse (9*216) ... (cached accounting: minus p*F_A)
    return p * F_A(N) + K * (2.0 * m * 36 + 9.0 * 216)


def F_block_apply(K):            # apply K 6x6 block inverses to a p-vector
    return K * 2.0 * 36


def F_transport_ls_iter(p, k, N, nnz):  # one block-PCG iteration on  min_Z ||M_t Z - Y||_F  (normal equations, k right-hand sides): k H-matvecs + O(p k) block ops + k x k solves
    return k * F_H_matvec(N, nnz) + 10.0 * p * k + 2.0 * k ** 3


def F_transport_rhs(p, k, N, nnz):      # Y = M_{t-1} U and M_t^T Y: two M-type products per column (J, A, sqrt(c) J) with the stored M_{t-1}-image of U (k columns) + ...
    return k * (2.0 * (2.0 * F_matvec(nnz) + F_A(N)))


def F_krylov_extend(p, r, N, nnz):      # D5: r extra directions from a short Krylov expansion of the current residual (r H-matvecs + orthogonalisation against k_t columns)
    return r * F_H_matvec(N, nnz) + 4.0 * p * r * r
