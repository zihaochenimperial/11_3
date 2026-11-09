# GEO-0 node R (read-only, post-hoc diagnostic; addendum I)

reproduction: max rel diff endpoint vs analyzer M = 0.00e+00; traj lengths [31]
H_end (trajectory endpoint, vs BLOCK): {'ORACLE_xs': 0.4518, 'OMP': -0.0676, 'JOINT': -0.0397, 'RAND': 0.3697, 'JOINT_FREE': 0.3135}
H_orig (report): {'ORACLE_xs': 0.4518, 'OMP': -0.0676, 'JOINT': -0.0397, 'RAND': 0.3697, 'JOINT_FREE': 0.3135}

stop index per arm (mean j, median j, mean K, fallback-to-j30 rate, mean j*): {'ORACLE_xs': (12.58, 12.0, 18.58, 0.0, 14.04), 'BLOCK': (12.86, 13.0, 18.86, 0.005, 12.62), 'OMP': (12.88, 12.5, 18.88, 0.016, 12.46), 'JOINT': (13.47, 13.0, 19.47, 0.005, 13.38), 'RAND': (18.59, 18.0, 24.59, 0.13, 16.81), 'JOINT_FREE': (15.06, 14.0, 21.06, 0.036, 14.81)}
endpoint repro ok vs orig 1e-6: {'ORACLE_xs': True, 'OMP': True, 'JOINT': True, 'RAND': True, 'JOINT_FREE': True}; vs rounded S2 1e-3: {'ORACLE_xs': True, 'OMP': True, 'JOINT': True, 'RAND': True, 'JOINT_FREE': True}; missing/short: {'ORACLE_xs': 0, 'BLOCK': 0, 'OMP': 0, 'JOINT': 0, 'RAND': 0, 'JOINT_FREE': 0} / {'ORACLE_xs': 0, 'BLOCK': 0, 'OMP': 0, 'JOINT': 0, 'RAND': 0, 'JOINT_FREE': 0}
gm MSE end/stop/best: {'end': {'ORACLE_xs': 0.00393, 'BLOCK': 0.00716, 'OMP': 0.00764, 'JOINT': 0.00744, 'RAND': 0.00451, 'JOINT_FREE': 0.00492}, 'stop': {'ORACLE_xs': 0.00188, 'BLOCK': 0.00268, 'OMP': 0.00266, 'JOINT': 0.0026, 'RAND': 0.00282, 'JOINT_FREE': 0.00248}, 'best': {'ORACLE_xs': 0.00155, 'BLOCK': 0.00226, 'OMP': 0.00225, 'JOINT': 0.00214, 'RAND': 0.00231, 'JOINT_FREE': 0.0021}}

## a_stop (H vs BLOCK; positive = lower MSE; [95% t-interval over 24 images]; sign-flip p)
- ORACLE_xs: H=0.2980 [0.2282, 0.3615] p=0.0000
- OMP: H=0.0066 [-0.0268, 0.0389] p=0.3420
- JOINT: H=0.0286 [-0.0290, 0.0831] p=0.1561
- RAND: H=-0.0546 [-0.1136, 0.0013] p=0.9720
- JOINT_FREE: H=0.0726 [0.0018, 0.1385] p=0.0228
## b_clean_best_step (H vs BLOCK; positive = lower MSE; [95% t-interval over 24 images]; sign-flip p)
- ORACLE_xs: H=0.3154 [0.2579, 0.3685] p=0.0000
- OMP: H=0.0043 [-0.0317, 0.0390] p=0.4026
- JOINT: H=0.0515 [0.0018, 0.0988] p=0.0214
- RAND: H=-0.0240 [-0.0790, 0.0282] p=0.8209
- JOINT_FREE: H=0.0684 [0.0085, 0.1247] p=0.0141
## endpoint_context (H vs BLOCK; positive = lower MSE; [95% t-interval over 24 images]; sign-flip p)
- ORACLE_xs: H=0.4518 [0.3986, 0.5002] p=0.0000
- OMP: H=-0.0676 [-0.1443, 0.0039] p=0.9681
- JOINT: H=-0.0397 [-0.1317, 0.0448] p=0.8255
- RAND: H=0.3697 [0.3143, 0.4206] p=0.0000
- JOINT_FREE: H=0.3135 [0.2515, 0.3703] p=0.0000
## stop index by condition (mean j / fallback rate j30 / mean j*)
- C1: {'ORACLE_xs': (19.2, 0.0, 23.4), 'BLOCK': (21.2, 0.02, 22.6), 'OMP': (21.1, 0.06, 23.4), 'JOINT': (21.5, 0.02, 25.7), 'RAND': (27.2, 0.42, 27.1), 'JOINT_FREE': (23.9, 0.12, 24.9)}
- C2: {'ORACLE_xs': (12.6, 0.0, 13.5), 'BLOCK': (12.8, 0.0, 12.9), 'OMP': (13.0, 0.0, 12.5), 'JOINT': (13.5, 0.0, 14.0), 'RAND': (18.7, 0.06, 17.9), 'JOINT_FREE': (14.1, 0.0, 14.8)}
- C3: {'ORACLE_xs': (11.7, 0.0, 12.6), 'BLOCK': (11.6, 0.0, 10.6), 'OMP': (11.5, 0.0, 9.7), 'JOINT': (12.2, 0.0, 9.7), 'RAND': (18.0, 0.04, 15.1), 'JOINT_FREE': (14.7, 0.0, 13.9)}
- C4: {'ORACLE_xs': (6.9, 0.0, 6.7), 'BLOCK': (5.9, 0.0, 4.4), 'OMP': (5.9, 0.0, 4.3), 'JOINT': (6.7, 0.0, 4.1), 'RAND': (10.4, 0.0, 7.1), 'JOINT_FREE': (7.5, 0.02, 5.6)}
## d_stop_by_condition (ORACLE_xs / RAND / JOINT_FREE / OMP / JOINT vs BLOCK)
- C1: {'ORACLE_xs': (0.4038, 0.2822, 0.5048), 'OMP': (0.0723, -0.0239, 0.1594), 'JOINT': (0.2156, 0.0753, 0.3347), 'RAND': (-0.0412, -0.2305, 0.119), 'JOINT_FREE': (0.0791, -0.0682, 0.2061)}
- C2: {'ORACLE_xs': (0.2697, 0.1988, 0.3344), 'OMP': (-0.0175, -0.0714, 0.0337), 'JOINT': (0.0419, -0.0334, 0.1116), 'RAND': (-0.0834, -0.2214, 0.039), 'JOINT_FREE': (0.0486, -0.0287, 0.1201)}
- C3: {'ORACLE_xs': (0.3323, 0.2276, 0.4229), 'OMP': (-0.0013, -0.0868, 0.0775), 'JOINT': (-0.0504, -0.1982, 0.0792), 'RAND': (0.0238, -0.0956, 0.1301), 'JOINT_FREE': (0.1334, -0.0181, 0.2623)}
- C4: {'ORACLE_xs': (0.1646, 0.0477, 0.2671), 'OMP': (-0.0303, -0.0545, -0.0066), 'JOINT': (-0.1278, -0.2351, -0.0297), 'RAND': (-0.1233, -0.2405, -0.0172), 'JOINT_FREE': (0.026, -0.0549, 0.1006)}