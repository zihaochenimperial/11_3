import os, sys, json, importlib.util
sys.path.insert(0,'src'); sys.path.insert(0,'experiments')
import numpy as np
import as_core as C, as_gen as G
spec=importlib.util.spec_from_file_location('as_run_var','experiments/as_run_var.py'); R=importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
out='outputs/vartest/AS'
# infeasible unit -> marker, no exception
p,w,s=R.do_unit(dict(arm='OMP_s',img=16,cond='C1',ns=9001) and (dict(arm='OMP_s',img=16,cond='C1',ns=9001),out,'t1'))
d=json.load(open(p)); print('infeasible:',s,d['status'],d['empty_step'],d['unit']['arm'],'traj' in d)
assert d['status']=='infeasible_restricted_set' and d['empty_step']==0 and 'traj' not in d
# step-2 case
p,w,s=R.do_unit((dict(arm='OMP_s',img=16,cond='C3',ns=9002),out,'t1')); d=json.load(open(p)); print('step2 case:',d['status'],d['empty_step'])
assert d['empty_step']==2
# skip-if-exists
print(R.do_unit((dict(arm='OMP_s',img=16,cond='C3',ns=9002),out,'t1'))[2])
# feasible unit bit-identical to direct as_core call, for _s and _b and JOINT_s
for arm,rule in (('OMP_s','OMP'),('OMP_b','OMP'),('JOINT_s','JOINT'),('JOINT_b','JOINT')):
    u=dict(arm=arm,img=14,cond='C2',ns=9001); p,w,s=R.do_unit((u,out,'t1')); d=json.load(open(p))
    sb,sn=R.COND['C2']; op=C.Op(sb); y=G.noisy_obs(op,G.clean_image(14),sn,9001,14)
    ref=C.run_path(y,op,sn,rule,only=arm.split('_')[1],seed=14); ref['only']=arm.split('_')[1]
    same=np.array_equal(np.array(d['traj'][-1]),np.array(ref['traj'][-1])) and all(np.array_equal(np.array(a),np.array(b)) for a,b in zip(d['traj'],ref['traj']))
    print(arm,'bitwise equal to direct run_path:',same,'wall',round(w,1)); assert same
# mask_for restored
assert C.mask_for.__name__=='mask_for'; print('mask_for restored OK')
# error path: bad arm -> ERROR tuple, no crash
print(R.do_unit_safe((dict(arm='NOPE',img=1,cond='C1',ns=9001),out,'t1'))[2][:60])
