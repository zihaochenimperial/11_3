"""JR post-VERIFY descriptive tables (Opus terminal R-JT2). Imports the frozen reducer's q_auc/o_auc/load; changes no decision. Output: outputs/JR/verify_post_tables.txt"""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jr_reduce as R
runs = R.load(os.path.join(R.ROOT, 'outputs', 'JR', 'verify')); by = {}
for r in runs: by[(r['img'], r['cond'], r['armname'])] = r
imgs = sorted({r['img'] for r in runs}); psfs = R.PSFS; out = []
def Q(img, c, a): return R.q_auc(by[(img, c, a)])
out.append('Per-image dQ = Q-AUC(OBS-J) - Q-AUC(X) [dB], mean over the 4 PSFs of each image (descriptive; decision rule unchanged)')
out.append('img   ' + ' '.join('%8s' % a for a in R.CONTROLS))
wins = {a: 0 for a in R.CONTROLS}
for img in imgs:
    row = []
    for a in R.CONTROLS:
        d = float(np.mean([Q(img, c, 'OBS-J') - Q(img, c, a) for c in psfs])); row.append(d); wins[a] += d > 0
    out.append('%d ' % img + ' '.join('%+8.3f' % d for d in row))
out.append('wins ' + ' '.join('%8s' % ('%d/12' % wins[a]) for a in R.CONTROLS))
out.append('')
out.append('Per-PSF mean dQ over the 12 images [dB]')
out.append('PSF   ' + ' '.join('%8s' % a for a in R.CONTROLS))
for c in psfs: out.append('%-5s ' % c + ' '.join('%+8.3f' % float(np.mean([Q(i, c, 'OBS-J') - Q(i, c, a) for i in imgs])) for a in R.CONTROLS))
out.append('')
out.append('Selected configs (TUNE): ' + json.dumps({k: v['cfgid'] for k, v in json.load(open(os.path.join(R.ROOT, 'outputs', 'JR', 'tune', 'selection.json')))['final'].items()}))
open(os.path.join(R.ROOT, 'outputs', 'JR', 'verify_post_tables.txt'), 'w').write('\n'.join(out) + '\n'); print('\n'.join(out))
