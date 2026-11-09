# AS contract v2.1 -- S2 analysis report (mechanical)

Decision: **STOP-Q1**

Gate 0 passed, Gate 1 failed: JOINT compensation shows no (gate-level) advantage over cheap rules. GateF-FAIL(FIXED-K <= 1.02 x JOINT): STOP growth line; Gate1-FAIL

cheap rule (fixed once): BLOCK; H (vs cheap, 192 units): {'JOINT': -0.0397, 'OMP': -0.0676, 'BLOCK': 0.0, 'FIXED': 0.1514, 'ORACLE_xs': 0.4518, 'RAND': 0.3697, 'JOINT_FREE': 0.3135}
H_Oxs=0.4518  H_Oys(96)=-0.6444  gate0=PASS

Gate1 vs OMP: meanD=-0.0342 (ratio 0.9663) p=0.13036 (count 2187031/16777216) cond={'C1': -0.2335, 'C2': -0.0397, 'C3': 0.0314, 'C4': 0.1358} fam={'edge': -0.0097, 'tex': 0.0083, 'mix': -0.1013} pass(i,ii,iii,iv)=False,False,False,True  SD(D)=0.1448 SE=0.0296
Gate1 vs BLOCK: meanD=0.0265 (ratio 1.0269) p=0.75890 (count 12732192/16777216) cond={'C1': -0.3365, 'C2': -0.1028, 'C3': 0.2178, 'C4': 0.3773} fam={'edge': 0.1109, 'tex': -0.0387, 'mix': 0.0074} pass(i,ii,iii,iv)=False,False,False,False  SD(D)=0.1830 SE=0.0374

GateF: FIXED/JOINT geometric-mean MSE ratio = 0.8162 (fail if <= 1.02): True
typemix: {}
infeasible restricted-set units (excluded from paired variant comparisons): {'JOINT_s': 6, 'OMP_s': 7}
V10 stability rate: 0.9683641975308642

JOINT_vs_JOINT_FREE: {'meanD': 0.4150404858705466, 'ratio': 1.5144320525509392}
JOINT_vs_ORACLE_y_full: {'n': 6, 'geo_ratio_JOINT_over_oracle': 0.7202392877390031}

Diagnostics (no decision weight):
```
{
 "overfit": {
  "RAND": {
   "gm_mse": 0.0045132790755454425,
   "mean_train_loss": 483.9337537165631,
   "n": 192
  },
  "OMP": {
   "gm_mse": 0.00542602348118032,
   "mean_train_loss": 434.17268079710163,
   "n": 216
  },
  "BLOCK": {
   "gm_mse": 0.005106104986139497,
   "mean_train_loss": 437.1240752743501,
   "n": 216
  },
  "JOINT": {
   "gm_mse": 0.005243337375645888,
   "mean_train_loss": 431.357372205238,
   "n": 216
  },
  "JOINT_FREE": {
   "gm_mse": 0.004916009139486753,
   "mean_train_loss": 450.0121059989937,
   "n": 192
  }
 },
 "dose_response": {
  "0.3": 0.07040236786542142,
  "1.0": 0.07246302949109662,
  "2.0": -0.3355671706605996,
  "monotone_H03<=H10<=H20": false
 },
 "K_c": {
  "C1": {
   "tik_gcv_gm_mse": 0.0028706772528335187,
   "tik_oracle_lambda_gm_mse": 0.0008981056244867006,
   "best_gauss_gm_mse": 0.0005595317818372767,
   "tik_gcv_better_dB": -7.101596081510986,
   "tik_oracle_lambda_better_dB": -2.0550265638844523
  },
  "C2": {
   "tik_gcv_gm_mse": 0.007738244370103669,
   "tik_oracle_lambda_gm_mse": 0.002851731274202027,
   "best_gauss_gm_mse": 0.0023183683330017567,
   "tik_gcv_better_dB": -5.234600043530922,
   "tik_oracle_lambda_better_dB": -0.8992616238510317
  },
  "C3": {
   "tik_gcv_gm_mse": 0.0031231443492602522,
   "tik_oracle_lambda_gm_mse": 0.0023871564790794984,
   "best_gauss_gm_mse": 0.006814924349827807,
   "tik_gcv_better_dB": 3.3886898179981957,
   "tik_oracle_lambda_better_dB": 4.5558015112114685
  },
  "C4": {
   "tik_gcv_gm_mse": 0.006357465590466017,
   "tik_oracle_lambda_gm_mse": 0.0041147243514431985,
   "best_gauss_gm_mse": 0.02663051217470527,
   "tik_gcv_better_dB": 6.220955008908044,
   "tik_oracle_lambda_better_dB": 8.110387723424441
  },
  "flag_gaussian_capacity_no_task_value": false,
  "flag_with_oracle_lambda_context_only": false
 },
 "step": {
  "top1_agree_with_JOINT": {
   "OMP": 0.08703703703703704,
   "BLOCK": 0.07716049382716049,
   "JOINT_FREE": 0.2933641975308642
  },
  "mean_spearman": {
   "OMP~JOINT": 0.5615074274308581,
   "BLOCK~JOINT": 0.5694106590862772,
   "JOINT_FREE~JOINT": 0.32306497460655126
  },
  "stationarity_ratio_mean": 0.017376202125086556,
  "JOINT_split_share": 0.059722222222222225,
  "exclusions_and_caps": {
   "clamped": 40822,
   "below_floor": 32721,
   "capped": 0
  },
  "time_seconds_total": {
   "score": 543.3837332725525,
   "refit": 3274.8311553001404
  },
  "pred_vs_real_chosen_spearman": 0.8855984297832075,
  "top5_pred_vs_real_spearman_mean": 0.08447916666666666,
  "top5_n": 2880
 },
 "V16": {
  "units_checked": 216,
  "units_with_hash_mismatch": 0,
  "ok": true
 },
 "INIT_N": {}
}
```