"""Host-side V1 unit-test runner (pump 'py' job). Runs tests/test_f0_units.py + tests/test_gsfast_equiv.py + tests/test_f3_units.py (v3) with the project venv and writes outputs/unit_tests_status.json
({passed, returncode, summary, hashes, utc}); experiments/f0_analyze.py reads it as gate V1. Never edits src/ or tests/."""
import hashlib, json, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
t0 = time.time()
r = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_f0_units.py', 'tests/test_gsfast_equiv.py', 'tests/test_f3_units.py', '-q', '-x', '--tb=short', '-p', 'no:cacheprovider'], cwd=str(ROOT), capture_output=True, text=True, timeout=2400)
tail = (r.stdout or '')[-6000:] + '\n--- stderr ---\n' + (r.stderr or '')[-2000:]
summary = [l for l in (r.stdout or '').splitlines() if ' passed' in l or ' failed' in l or ' error' in l][-1:] 
h = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / 'src').glob('*.py')) + [ROOT / 'tests' / 'test_f0_units.py', ROOT / 'tests' / 'test_gsfast_equiv.py', ROOT / 'tests' / 'test_f3_units.py']}
out = dict(passed=(r.returncode == 0), returncode=r.returncode, summary=summary, wall_s=time.time() - t0, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), hashes=h, tail=tail)
(ROOT / 'outputs').mkdir(exist_ok=True)
(ROOT / 'outputs' / 'unit_tests_status.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps({k: out[k] for k in ('passed', 'returncode', 'summary', 'wall_s')}))
sys.exit(0 if out['passed'] else 1)
