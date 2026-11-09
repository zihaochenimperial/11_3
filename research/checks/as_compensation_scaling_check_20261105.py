"""AS-phase paper-algebra sanity check (NOT an experiment, NOT evidence for any hypothesis).
Question: at a (near-)stationary fit y ~ A x(theta), how does the gain from a coincident split change when the
existing parameters are allowed to re-fit linearly (compensation, projector P_perp of range(A J)) vs not?
Algebra (Sonnet, unreviewed): gain_unc = r.Aq - 0.5|Aq|^2 ; gain_comp = r.Aq - 0.5|P_perp A q|^2 (r _|_ range(AJ) at stationarity).
For split offsets delta, q = O(delta^2) (zero-mean offsets), so difference = 0.5|P A q|^2 = O(delta^4).
1-D toy, numpy only, fixed seed; prints scaling exponents. Single seed/toy: illustrates the algebra only."""
import numpy as np, json
rng = np.random.default_rng(20261105)
N = 160; xs = np.arange(N, dtype=float)
def gauss(a, m, s): return a*np.exp(-0.5*((xs-m)/s)**2)
def render(th): return sum(gauss(*th[3*i:3*i+3]) for i in range(len(th)//3))
# known blur kernel (A is convolution, zero padding)
k = np.exp(-0.5*(np.arange(-12, 13)/3.0)**2); k /= k.sum()
def A(v): return np.convolve(v, k, mode='same')
Amat = np.stack([A(e) for e in np.eye(N)], axis=1)
th_true = np.array([1.0,60,4.0, 0.7,72,5.0, 0.9,100,3.5, 0.5,120,6.0])
sigma = 0.01
y = A(render(th_true)) + sigma*rng.standard_normal(N)
def jac(th, h=1e-6):
    J = np.zeros((N, len(th)))
    for j in range(len(th)):
        d = np.zeros_like(th); d[j] = h
        J[:, j] = (render(th+d)-render(th-d))/(2*h)
    return J
# Gauss-Newton (LM) fit from perturbed start
th = th_true + 0.05*rng.standard_normal(th_true.shape)
for it in range(200):
    r = y - A(render(th)); J = Amat @ jac(th)
    H = J.T@J + 1e-9*np.eye(len(th))
    step = np.linalg.solve(H, J.T@r)
    th = th + step
    if np.linalg.norm(step) < 1e-12: break
r = y - A(render(th)); J = Amat @ jac(th)
P = J @ np.linalg.pinv(J)             # projector onto range(AJ)
print("stationarity |J^T r|/|r| =", np.linalg.norm(J.T@r)/np.linalg.norm(r))
i = 1  # split Gaussian i along its position axis
res = []
for d in [4.0, 2.0, 1.0, 0.5, 0.25, 0.125]:
    a, m, s = th[3*i:3*i+3]
    # split: two halves amplitude a/2 at m +- d, same width (weights 1/2, zero-mean offsets)
    x_new = render(th) - gauss(a, m, s) + gauss(a/2, m+d, s) + gauss(a/2, m-d, s)
    q = x_new - render(th); Aq = A(q)
    g_unc = r@Aq - 0.5*Aq@Aq
    Pperp_Aq = Aq - P@Aq
    g_comp = r@Aq - 0.5*Pperp_Aq@Pperp_Aq
    res.append(dict(delta=d, norm_q=float(np.linalg.norm(q)), first_order=float(r@Aq), gain_unc=float(g_unc), gain_comp=float(g_comp),
                    diff=float(g_comp-g_unc), s_q=float((Pperp_Aq@Pperp_Aq)/(q@q))))
for a_, b_ in zip(res[:-1], res[1:]):
    a_['exp_first'] = float(np.log(abs(a_['first_order'])/abs(b_['first_order']))/np.log(2)) if b_['first_order'] != 0 else None
    a_['exp_diff'] = float(np.log(abs(a_['diff'])/abs(b_['diff']))/np.log(2))
    a_['exp_normq'] = float(np.log(a_['norm_q']/b_['norm_q'])/np.log(2))
for r_ in res: print({k_: (round(v, 6) if isinstance(v, float) else v) for k_, v in r_.items()})
json.dump(dict(note="paper-algebra sanity check; not evidence", sigma=sigma, N=N, results=res),
          open("research/checks/as_compensation_scaling_check_20261105.json", "w"), indent=1)
