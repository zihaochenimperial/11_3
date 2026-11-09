import sys, os, shutil, time, json
sys.path.insert(0,'/home/claude/geo/experiments'); sys.path.insert(0,'/home/claude/geo/src')
import geo_run as R, geo_analyze as A, geo_gen as GG, geo_core as GC
OUTD='/tmp/dry/outputs'
R.OUT = A.OUT = OUTD
R.TUNE_IMGS=[101,102]; GG.DEV_IMGS[:] = [101,102]; GG.TEST_IMGS[:] = [201,202,203,204]; R.KS=(16,); A.R.KS=(16,)
R.CONDS=('C1','C4'); R.TUNE_CONDS=('C1','C4')
A.V_CELLS=4; A.V_CELLS_K=4; A.MIN_IMG_A=2; A.MIN_IMG_T=2
GC.SAFETY.update(GEO=1500, LMD=1500, BJ=1500, BLK=1500, LSMR=500, PCG8P=500, PCG8D=500)
def job(name, **kv):
    argv=['job='+name]+['%s=%s'%(k,v) for k,v in kv.items()]
    r=R.Runner(argv); r.run()
def step(msg): print('=== '+msg, flush=True)
t=time.time()
job('tune_geo'); job('fref', cells='tune'); A.cmd_select_geo()
job('calib_caps'); A.cmd_caps()
job('tune_arms'); A.cmd_select_arms()
job('fref', cells='dev'); job('vpass'); A.cmd_vpass()
job('lamgrid'); A.cmd_select_lam()
job('fref', cells='dev', lam='star'); job('vpass_lam'); A.cmd_vpass_lam()
sys.argv=['x','plan','deadline_utc=2026-11-09T18:15Z','now_utc=2026-11-08T01:00Z','cap_h=0.001']; A.cmd_plan()
step('H')
job('fref', cells='h201', lam='star'); job('h_q2'); job('h_q1'); job('ypair'); job('timing', reps=2)
A.cmd_h_q2(); A.cmd_q2_quality(); A.cmd_h_timing(); A.cmd_q2_label(); A.cmd_h_q1()
print('DRY DONE', time.time()-t)
