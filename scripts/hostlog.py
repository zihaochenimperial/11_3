#!/usr/bin/env python3
"""Print a Windows-host log with encoding fallback (PS5.1 redirects are GBK/UTF-16/UTF-8-BOM). Usage: hostlog.py FILE [maxchars]"""
import sys
b = open(sys.argv[1], 'rb').read(); n = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
if b[:2] in (b'\xff\xfe', b'\xfe\xff'): encs = ['utf-16']
else: encs = ['utf-8-sig', 'gbk', 'latin-1']
for e in encs:
    try: print(b.decode(e)[:n]); break
    except Exception: continue
