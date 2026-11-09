"""GEO phase V formal runner: runs tests/test_geo_core.py with pytest on the host venv; writes outputs/GEO-V/<tag>.txt (default V_RESULT_K1.txt; the j85 record V_RESULT.txt is never overwritten).
Records sha256 of every frozen code file. No fits beyond the unit tests. Usage: python geo_vtests.py [tag=V_RESULT_K1]"""
import os, sys, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('OMP_NUM_THREADS', '1'); os.environ.setdefault('OPENBLAS_NUM_THREADS', '1'); os.environ.setdefault('MKL_NUM_THREADS', '1')
kv = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a); tag = kv.get('tag', 'V_RESULT_K1')
FILES = ('src/geo_core.py', 'src/geo_flops.py', 'src/geo_gen.py', 'tests/test_geo_core.py', 'experiments/geo_run.py', 'experiments/geo_analyze.py', 'experiments/geo_L.py', 'experiments/geo_vtests.py', 'src/as_core.py', 'src/as_gen.py')
def sha(p): return hashlib.sha256(open(os.path.join(ROOT, p), 'rb').read()).hexdigest()
out = os.path.join(ROOT, 'outputs', 'GEO-V'); os.makedirs(out, exist_ok=True)
import pytest, numpy, scipy
code = pytest.main(['-q', '-s', os.path.join(ROOT, 'tests', 'test_geo_core.py'), '-p', 'no:cacheprovider'])
lines = ['exit_code=%s' % int(code), 'python=%s numpy=%s scipy=%s pytest=%s' % (sys.version.split()[0], numpy.__version__, scipy.__version__, pytest.__version__)] + ['%s %s' % (p, sha(p)) for p in FILES if os.path.exists(os.path.join(ROOT, p))]
open(os.path.join(out, tag + '.txt'), 'w').write('\n'.join(lines) + '\n'); print('\n'.join(lines)); sys.exit(int(code))
