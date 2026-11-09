# AS S2 ERRATUM-192 (read-only; FAIL-0025)

reproduction of original report from unrestricted data: ok=True mismatches=[]
original report unchanged: True
units removed (arm: {cond: n}): {'BLOCK': {'D03': 24}, 'JOINT': {'D03': 24}, 'OMP': {'D03': 24}}

decision orig=STOP-Q1 | err192=STOP-Q1 | same=True | gate1 flags same=False | H same=True
GateF orig=0.8162 err192=0.8162

Gate1 vs OMP [orig]: meanD=-0.0342 (ratio 0.9663) p=0.13036 cond={'C1': -0.2335, 'C2': -0.0397, 'C3': 0.0314, 'C4': 0.1358} fam={'edge': -0.0097, 'tex': 0.0083, 'mix': -0.1013} pass(i,ii,iii,iv)=False,False,False,True
Gate1 vs OMP [err192]: meanD=-0.0265 (ratio 0.9739) p=0.21059 cond={'C1': -0.2335, 'C2': -0.0397, 'C3': 0.0314, 'C4': 0.1358} fam={'edge': 0.0056, 'tex': 0.0194, 'mix': -0.1044} pass(i,ii,iii,iv)=False,False,False,False
Gate1 vs BLOCK [orig]: meanD=0.0265 (ratio 1.0269) p=0.75890 cond={'C1': -0.3365, 'C2': -0.1028, 'C3': 0.2178, 'C4': 0.3773} fam={'edge': 0.1109, 'tex': -0.0387, 'mix': 0.0074} pass(i,ii,iii,iv)=False,False,False,False
Gate1 vs BLOCK [err192]: meanD=0.0390 (ratio 1.0397) p=0.82546 cond={'C1': -0.3365, 'C2': -0.1028, 'C3': 0.2178, 'C4': 0.3773} fam={'edge': 0.1335, 'tex': -0.0299, 'mix': 0.0133} pass(i,ii,iii,iv)=False,False,False,False

deviation-principle K diagnostic (contract-required; Gate-1 stats at the deviation K; no decision weight): {"OMP": {"ok": true, "meanD": -0.022421867979555362, "ratio": 0.9778276338574645, "p": 0.2110964059829712, "count": 3541610, "total": 16777216, "sd": 0.13232489308940196, "se": 0.0270107056947809, "cond_means": {"C1": -0.16787088555217342, "C2": -0.06011920642018653, "C3": 0.04789346484619713, "C4": 0.09040915520794135}, "fam_means": {"edge": -0.11371317813936718, "tex": 0.027915566963840614, "mix": 0.018532007236860496}, "pass_i": false, "pass_ii": false, "pass_iii": false, "pass_iv": false, "passed": false}, "BLOCK": {"ok": true, "meanD": -0.02905079085805956, "ratio": 0.9713671266438072, "p": 0.1560571789741516, "count": 2618205, "total": 16777216, "sd": 0.1365974121070694, "se": 0.02788282998724944, "cond_means": {"C1": -0.24286426624970373, "C2": -0.04275355549189611, "C3": 0.04917259609365938, "C4": 0.12024206221570222}, "fam_means": {"edge": -0.06630737546208704, "tex": -0.046604628140117094, "mix": 0.025759631028025434}, "pass_i": false, "pass_ii": false, "pass_iii": false, "pass_iv": true, "passed": false}}
deviation_K_mean_index: {'OMP': 12.875, 'BLOCK': 12.864583333333334, 'JOINT': 13.473958333333334}
overfit(192): {"RAND": {"gm_mse": 0.0045132790755454425, "mean_train_loss": 483.9337537165631, "n": 192}, "OMP": {"gm_mse": 0.007644682938907539, "mean_train_loss": 431.21941403699105, "n": 192}, "BLOCK": {"gm_mse": 0.007160470007748442, "mean_train_loss": 433.01120728167865, "n": 192}, "JOINT": {"gm_mse": 0.0074449618114721, "mean_train_loss": 428.7035227943684, "n": 192}, "JOINT_FREE": {"gm_mse": 0.004916009139486753, "mean_train_loss": 450.0121059989937, "n": 192}}