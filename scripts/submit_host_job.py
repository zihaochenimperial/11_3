#!/usr/bin/env python3
"""Prospective host-job submission: create the run record FIRST (start event, inputs, config), then drop the job into queue/inbox.
ingest_host_results.py later completes the same run (end event) instead of inventing a post-hoc one.
usage: submit_host_job.py --job-id j08-hostinfo-v2 --type hostinfo --task "why" [--fields '{"role":"literature-scout","task_file":"tasks\\\\001.md"}'] [--inputs path ...] [--model ...]"""
import argparse, json, re, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument('--job-id', required=True); ap.add_argument('--type', required=True); ap.add_argument('--task', required=True)
ap.add_argument('--fields', default='{}'); ap.add_argument('--inputs', nargs='*', default=[]); ap.add_argument('--model', default='n/a (no model call)')
ap.add_argument('--provider', default='windows-host-pump'); ap.add_argument('--seed', default='n/a')
a = ap.parse_args()
if not re.match(r'^[A-Za-z0-9_\-]+$', a.job_id): sys.exit('bad job id')
fields = json.loads(a.fields)
kind = 'opencode-worker' if a.type == 'worker' else 'host-' + a.type
if a.type == 'worker': a.model = 'configured via opencode.jsonc agent %s (actual serving model not reported)' % fields.get('role')
cmd = [sys.executable, str(ROOT / 'scripts' / 'runlog.py'), 'start', '--kind', kind, '--role', fields.get('role', 'host'), '--model', a.model, '--provider', a.provider,
       '--task', 'queue job %s: %s' % (a.job_id, a.task), '--seed', a.seed, '--config', json.dumps({'job': {**fields, 'job_id': a.job_id, 'type': a.type}}, ensure_ascii=False)]
if a.inputs: cmd += ['--inputs'] + a.inputs
rid = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1]
job = {'job_id': a.job_id, 'type': a.type, 'run_id': rid, 'submitted_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), **fields}
(ROOT / 'queue' / 'submitted').mkdir(parents=True, exist_ok=True)
(ROOT / 'queue' / 'submitted' / (a.job_id + '.json')).write_text(json.dumps(job, indent=1), encoding='utf-8')
(ROOT / 'queue' / 'inbox' / (a.job_id + '.json')).write_text(json.dumps(job), encoding='utf-8')
print(rid)
