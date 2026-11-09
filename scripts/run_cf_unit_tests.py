"""Host-side V1 unit-test runner for the CF-birth line (pump 'py' job). Writes outputs/cf_unit_tests_status.json (does NOT touch outputs/unit_tests_status.json, the F0/F3 evidence)."""
import hashlib, json, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
t0 = time.time()
files = ['tests/test_cf_units.py', 'tests/test_cf_analyze.py', 'tests/test_gsfast_equiv.py']
r = subprocess.run([sys.executable, '-m', 'pytest', *files, '-q', '--tb=short', '-p', 'no:cacheprovider'], cwd=str(ROOT), capture_output=True, text=True, timeout=2400)
tail = (r.stdout or '')[-6000:] + '\n--- stderr ---\n' + (r.stderr or '')[-2000:]
summary = [l for l in (r.stdout or '').splitlines() if ' passed' in l or ' failed' in l or ' error' in l][-1:]
extra = ['scripts/run_cf_unit_tests.py', 'experiments/cf_run.py', 'experiments/cf_analyze.py']
h = {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / 'src').glob('*.py')) + [ROOT / f for f in files + extra]}
out = dict(passed=(r.returncode == 0), returncode=r.returncode, summary=summary, wall_s=time.time() - t0, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), hashes=h, tail=tail)
(ROOT / 'outputs').mkdir(exist_ok=True)
(ROOT / 'outputs' / 'cf_unit_tests_status.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps({k: out[k] for k in ('passed', 'returncode', 'summary', 'wall_s')}))
sys.exit(0 if out['passed'] else 1)
