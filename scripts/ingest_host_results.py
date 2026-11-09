#!/usr/bin/env python3
"""Turn queue/done/*.result.json (written by the Windows host pump) into runs/<run_id>/ records + tasks/ledger.jsonl lines.
Idempotent (queue/ingested.json). Worker jobs: reads the OpenCode output.jsonl for text/tokens/cost (as returned by the service) and
maps role->configured model from opencode.jsonc. Self-reported model text is evidence, not proof."""
import json, re, sys, hashlib
from pathlib import Path
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo; LON = ZoneInfo("Europe/London")
except Exception: LON = None
ROOT = Path(__file__).resolve().parent.parent
def dec(b):
    if b[:2] in (b'\xff\xfe', b'\xfe\xff'): return b.decode('utf-16', 'replace')
    for e in ('utf-8-sig', 'gbk'):
        try: return b.decode(e)
        except Exception: pass
    return b.decode('latin-1')
def rj(p): return json.loads(dec(Path(p).read_bytes()))
def sha(p):
    p = Path(p); return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def loc(p):  # host path D:\Gaussian\x -> ROOT/x
    return ROOT / str(p).replace('D:\\Gaussian\\', '').replace('\\', '/')
def iso(s):  # '2026-11-05T07:39:04.3103209Z' -> aware dt
    s = s.replace('Z', '+00:00'); m = re.match(r'(.*\.\d{6})\d*(\+.*)', s)
    return datetime.fromisoformat(m.group(1) + m.group(2) if m else s)
cfg = json.loads((ROOT / 'opencode.jsonc').read_text(encoding='utf-8'))
role_model = {k: v.get('model') for k, v in cfg.get('agents', {}).items()}
led = ROOT / 'tasks' / 'ledger.jsonl'; ing_p = ROOT / 'queue' / 'ingested.json'
ing = json.loads(ing_p.read_text()) if ing_p.exists() else {}
new = 0
for rp in sorted((ROOT / 'queue' / 'done').glob('*.result.json')):
    r = rj(rp); jid = r.get('job_id', rp.stem.split('.')[0])
    if jid in ing: continue
    jp = ROOT / 'queue' / 'done' / (jid + '.job.json')
    typ = r.get('type', 'rejected'); sd = r.get('started_utc'); ed = r.get('finished_utc')
    if not sd:  # hostinfo has no started_utc
        sd = ed = (r.get('info') or {}).get('utc') or datetime.now(timezone.utc).isoformat()
    s, e = iso(sd), iso(ed or sd)
    kind = 'opencode-worker' if typ == 'worker' else 'host-' + typ
    sub_p = ROOT / 'queue' / 'submitted' / (jid + '.json'); pre = None
    if sub_p.exists():
        try:
            pre_id = json.loads(sub_p.read_text(encoding='utf-8')).get('run_id')
            if pre_id and (ROOT / 'runs' / pre_id / 'status.json').exists(): pre = json.loads((ROOT / 'runs' / pre_id / 'status.json').read_text(encoding='utf-8')); pre['run_id'] = pre_id
        except Exception: pre = None
    rid = pre['run_id'] if pre else '%s-%s-%s' % (s.strftime('%Y%m%dT%H%M%SZ'), kind, jid); rd = ROOT / 'runs' / rid; rd.mkdir(parents=True, exist_ok=True)
    st = {'run_id': rid, 'kind': kind, 'job_id': jid, 'provider': 'windows-host-pump', 'recorded_by': 'ingest_host_results.py (post-hoc from pump result; pump has no logger)',
          'started_utc': s.strftime('%Y-%m-%dT%H:%M:%SZ'), 'started_london': s.astimezone(LON).isoformat(timespec='seconds') if LON else 'unknown',
          'ended_utc': e.strftime('%Y-%m-%dT%H:%M:%SZ'), 'ended_london': e.astimezone(LON).isoformat(timespec='seconds') if LON else 'unknown',
          'duration_s': round((e - s).total_seconds(), 1), 'exit_code': r.get('exit_code'), 'tokens': 'unknown', 'cost': 'unknown', 'seed': 'n/a',
          'evidence': [str(rp.relative_to(ROOT))], 'result': None, 'failure': None, 'next': None, 'hardware': 'Windows host i7-12700H/31.8GB/RTX3070Ti 8GB (see host-hostinfo run)'}
    jobsrc = ROOT / 'queue' / 'inbox_archive' / (jid + '.json')
    if typ == 'worker':
        out = dec(Path(loc(r['stdout'])).read_bytes()).strip(); wd = loc(out) if out else None
        role = None
        for m in re.finditer(r'"role":\s*"([^"]+)"', dec((wd / 'status.json').read_bytes()) if wd and (wd / 'status.json').exists() else ''): role = m.group(1)
        st['role'] = role; st['model'] = 'configured: ' + str(role_model.get(role)) + ' (via opencode.jsonc agent %s; actual model not reported in output.jsonl events)' % role
        st['provider'] = 'opencode-go'; st['task'] = 'queue job %s: worker role %s' % (jid, role)
        st['inputs'] = [{'path': 'tasks/000-smoke.md', 'sha256': sha(ROOT / 'tasks' / '000-smoke.md')}]
        if wd and (wd / 'output.jsonl').exists():
            tok = {'input': 0, 'output': 0, 'reasoning': 0, 'cache_read': 0}; cost = 0; txt = []
            for l in dec((wd / 'output.jsonl').read_bytes()).splitlines():
                try: x = json.loads(l)
                except Exception: continue
                p = x.get('part', {})
                if x.get('type') == 'text': txt.append(p.get('text', ''))
                if x.get('type') == 'step_finish':
                    t = p.get('tokens', {}); tok['input'] += t.get('input', 0); tok['output'] += t.get('output', 0); tok['reasoning'] += t.get('reasoning', 0)
                    tok['cache_read'] += (t.get('cache') or {}).get('read', 0); cost += p.get('cost', 0) or 0
            if txt: st['tokens'] = tok; st['cost'] = '%s (as returned by service)' % cost
            st['result'] = ' '.join(txt)[:600]; st['evidence'].append(str(wd.relative_to(ROOT) / 'output.jsonl'))
        if r.get('exit_code') not in (0, None):
            st['failure'] = dec(Path(loc(r['stderr'])).read_bytes())[:600] if r.get('stderr') else 'exit %s' % r.get('exit_code')
    else:
        st['model'] = 'n/a (no model call)'; st['task'] = 'queue job %s: %s' % (jid, typ)
        if typ == 'contention':
            ok = sum(1 for p in r['processes'] if p['exit_code'] == 0); st['result'] = 'n=%d launched at once; %d got a slot, %d rejected' % (r['n'], ok, r['n'] - ok); st['status'] = 'ok' if (ok == min(r['n'], 5) and r['n'] - ok == max(0, r['n'] - 5)) else 'failed'
        elif typ == 'hostinfo':
            i = r.get('info', {}); st['result'] = 'pump=%s ps=%s os=%s cpus=%s ram_gb=%s gpu=%s d_free_gb=%s opencode_cmd=%s credential_file=%s venv=%s python_on_path=%s py_launcher=%s python_candidates=%s' % (i.get('pump_version'), i.get('ps_version'), i.get('os'), i.get('logical_cpus'), i.get('ram_gb'), i.get('gpu', i.get('nvidia_smi')), i.get('d_free_gb'), i.get('opencode_cmd_exists'), i.get('credential_file_exists'), i.get('venv_exists'), i.get('python_on_path', i.get('python')), i.get('py_launcher'), i.get('python_candidates'))
        elif typ == 'slotprobe': st['result'] = 'slot probe exit %s' % r.get('exit_code')
        else: st['failure'] = r.get('error')
    st['status'] = st.get('status') or ('ok' if r.get('exit_code') == 0 else 'failed')
    if pre:
        st['pump_started_utc'] = st['started_utc']; st['started_utc'] = pre.get('started_utc', st['started_utc']); st['started_london'] = pre.get('started_london', st['started_london'])
        st['recorded_by'] = 'prospective start (submit_host_job.py at dispatch); end/result filled by ingest_host_results.py from pump result'
        for k in ('inputs', 'config', 'cmd_line', 'owner_files', 'host', 'git'):
            if pre.get(k) is not None and k not in st: st[k] = pre[k]
        if pre.get('inputs'): st['inputs'] = pre['inputs']
        st['model'] = pre.get('model', st.get('model'))
        st['duration_s'] = round((e - iso(st['started_utc'])).total_seconds(), 1)
    (rd / 'status.json').write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')
    with open(rd / 'events.jsonl', 'a', encoding='utf-8') as f:
        if not pre: f.write(json.dumps({'t': st['started_utc'], 'event': 'start'}) + '\n')
        f.write(json.dumps({'t': st['ended_utc'], 'event': 'end', 'status': st['status']}) + '\n')
    with open(led, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'t': st['ended_utc'], 'run_id': rid, 'event': 'end', 'kind': kind, 'status': st['status'], 'result': st['result'], 'failure': st['failure']}, ensure_ascii=False) + '\n')
    ing[jid] = rid; new += 1; print(rid, st['status'])
ing_p.write_text(json.dumps(ing, indent=1)); print('ingested', new)
