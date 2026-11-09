import sys, json
sys.path.insert(0,'/home/claude/geo/experiments'); sys.path.insert(0,'/home/claude/geo/src')
import geo_run as R, geo_analyze as A, geo_gen as GG
import geo_analyze_unexp as U
R.OUT = A.OUT = '/tmp/dry/outputs'; R.KS=(16,); R.CONDS=('C1','C4'); R.TUNE_CONDS=('C1','C4'); GG.TEST_IMGS[:] = [201,202,203,204]
import io, contextlib
for ex in ((), (201,202)):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): cons = U.run(exposed=ex, real_out='/tmp/dry/outputs')
    print('exposed', ex, '| meta', cons['meta'], '| per_K', {k:(v['primary_category'],v['view20_category'],v['same']) for k,v in cons['per_K'].items()}, '| q1', cons['q1'], '| depends', cons['depends_on_exposed_images'], '| overall20', str(cons['view_20_overall'])[:70])
