#!/usr/bin/env python3
"""Gaussian unified run logger (stdlib only, Windows/Linux).
  start : create runs/<run_id>/status.json + events.jsonl, append tasks/ledger.jsonl, print run_id
  event : append one event line to a run
  end   : finalize status (ok|failed|blocked|aborted) with result, evidence hashes, next step
A run without an `end` record is treated as INCOMPLETE (process existence is not a result)."""
import argparse, hashlib, json, os, platform, secrets, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
try:
    from zoneinfo import ZoneInfo
    LON = ZoneInfo("Europe/London")
except Exception:
    LON = None
ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
LEDGER = ROOT / "tasks" / "ledger.jsonl"

def now():
    u = datetime.now(timezone.utc)
    l = u.astimezone(LON).isoformat(timespec="seconds") if LON else "unknown"
    return u.strftime("%Y-%m-%dT%H:%M:%SZ"), l, u

def sha256(p):
    p = Path(p)
    if not p.is_absolute(): p = ROOT / p
    if not p.is_file(): return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def hashes(paths):
    return [{"path": str(x), "sha256": sha256(x)} for x in (paths or [])]

def gpu():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else "nvidia-smi rc=%d" % r.returncode
    except Exception as e:
        return "unavailable (%s)" % type(e).__name__

def append(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f: f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def load(rid):
    return json.loads((RUNS / rid / "status.json").read_text(encoding="utf-8"))

def save(rid, st):
    (RUNS / rid / "status.json").write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

def lock_cmd(a, u, dt):
    """Session lock so a scheduled wake never duplicates a live session. status: exit 10 = BUSY."""
    p = RUNS / "SESSION_LOCK.json"
    cur = None
    if p.exists():
        try: cur = json.loads(p.read_text(encoding="utf-8"))
        except Exception: cur = None
    def fresh(c):
        if not c: return False
        t = datetime.strptime(c["heartbeat_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return (dt - t).total_seconds() < float(c.get("ttl_min", 50)) * 60
    if a.action == "status":
        if cur and fresh(cur): print("BUSY", json.dumps(cur, ensure_ascii=False)); sys.exit(10)
        print("FREE" + (" (stale lock of %s)" % cur.get("owner") if cur else "")); return
    if a.action == "acquire":
        if cur and fresh(cur) and cur.get("owner") not in (a.owner, a.replace_owner):
            print("BUSY", json.dumps(cur, ensure_ascii=False)); sys.exit(10)
        p.write_text(json.dumps({"owner": a.owner, "acquired_utc": u, "heartbeat_utc": u, "ttl_min": a.ttl_min, "note": a.note}, ensure_ascii=False), encoding="utf-8")
        chk = json.loads(p.read_text(encoding="utf-8"))
        if chk.get("owner") != a.owner: print("LOST_RACE"); sys.exit(10)
        print("ACQUIRED", a.owner); return
    if not cur or cur.get("owner") != a.owner:
        print("NOT_OWNER"); sys.exit(11)
    if a.action == "heartbeat":
        cur["heartbeat_utc"] = u; p.write_text(json.dumps(cur, ensure_ascii=False), encoding="utf-8"); print("HEARTBEAT", u)
    elif a.action == "release":
        cur.update({"owner": None, "released_by": a.owner, "released_utc": u, "heartbeat_utc": "1970-01-01T00:00:00Z"}); p.write_text(json.dumps(cur, ensure_ascii=False), encoding="utf-8"); print("RELEASED", a.owner)

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--kind", required=True); s.add_argument("--role", default="main")
    s.add_argument("--model", default="claude-sonnet-5-5 (configured id; serving model may differ)")
    s.add_argument("--provider", default="anthropic/claude-code-app")
    s.add_argument("--task", required=True); s.add_argument("--inputs", nargs="*", default=[])
    s.add_argument("--owner-files", nargs="*", default=[]); s.add_argument("--seed", default="n/a")
    s.add_argument("--cmd-line", default=""); s.add_argument("--config", default="{}")
    e = sub.add_parser("event"); e.add_argument("--run", required=True); e.add_argument("--msg", required=True); e.add_argument("--data", default="{}")
    d = sub.add_parser("end"); d.add_argument("--run", required=True)
    d.add_argument("--status", required=True, choices=["ok", "failed", "blocked", "aborted"])
    d.add_argument("--result", default=""); d.add_argument("--evidence", nargs="*", default=[])
    d.add_argument("--failure", default=""); d.add_argument("--next", dest="nxt", default="")
    d.add_argument("--exit-code", default="n/a"); d.add_argument("--tokens", default="unknown"); d.add_argument("--cost", default="unknown")
    k = sub.add_parser("lock"); k.add_argument("action", choices=["acquire", "heartbeat", "release", "status"])
    k.add_argument("--owner", default=""); k.add_argument("--ttl-min", type=float, default=50); k.add_argument("--note", default=""); k.add_argument("--replace-owner", default="__none__")
    a = ap.parse_args()
    u, l, dt = now()
    if a.cmd == "lock":
        lock_cmd(a, u, dt); return
    if a.cmd == "start":
        rid = "%s-%s-%s" % (dt.strftime("%Y%m%dT%H%M%SZ"), a.kind, secrets.token_hex(2))
        (RUNS / rid).mkdir(parents=True, exist_ok=False)
        try: cfg = json.loads(a.config)
        except Exception: cfg = {"raw": a.config}
        st = {"run_id": rid, "kind": a.kind, "role": a.role, "model": a.model, "provider": a.provider, "task": a.task,
              "status": "running", "started_utc": u, "started_london": l, "ended_utc": None, "ended_london": None,
              "duration_s": None, "owner_files": a.owner_files, "inputs": hashes(a.inputs), "seed": a.seed,
              "command": a.cmd_line, "config": cfg,
              "hardware": {"platform": platform.platform(), "python": sys.version.split()[0], "cpu_count": os.cpu_count(), "gpu": gpu()},
              "exit_code": None, "tokens": "unknown", "cost": "unknown", "result": None, "evidence": [], "failure": None, "next": None}
        save(rid, st)
        append(RUNS / rid / "events.jsonl", {"t": u, "event": "start", "task": a.task})
        append(LEDGER, {"t": u, "run_id": rid, "event": "start", "kind": a.kind, "model": a.model, "task": a.task})
        print(rid)
    elif a.cmd == "event":
        try: data = json.loads(a.data)
        except Exception: data = {"raw": a.data}
        append(RUNS / a.run / "events.jsonl", {"t": u, "event": "note", "msg": a.msg, "data": data})
    else:
        st = load(a.run)
        t0 = datetime.strptime(st["started_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        st.update({"status": a.status, "ended_utc": u, "ended_london": l, "duration_s": int((dt - t0).total_seconds()),
                   "exit_code": a.exit_code, "tokens": a.tokens, "cost": a.cost, "result": a.result,
                   "evidence": hashes(a.evidence), "failure": a.failure or None, "next": a.nxt})
        save(a.run, st)
        append(RUNS / a.run / "events.jsonl", {"t": u, "event": "end", "status": a.status})
        append(LEDGER, {"t": u, "run_id": a.run, "event": "end", "status": a.status, "result": a.result, "next": a.nxt})
        print("ended", a.run, a.status)

if __name__ == "__main__":
    main()
