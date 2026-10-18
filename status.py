#!/usr/bin/env python3
"""Shows what the GitHub agent posted. Run:  git pull -q && python3 status.py"""
import json, os, time, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
q = json.load(open(os.path.join(HERE, "state", "queue.json")))
t0 = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
today, fails = {}, []
for it in q["items"]:
    for k, r in it.get("posted", {}).items():
        if r.get("ts", 0) >= t0:
            if r.get("ok"): today[k] = today.get(k, 0) + 1
            else: fails.append((k, it.get("title", ""), r.get("error", "")[:120]))
print("POSTED TODAY (per account):")
for k, n in sorted(today.items()): print(f"  {k}: {n}")
if not today: print("  nothing yet")
last = q.get("last_post", 0)
if last: print(f"\nLast post: {datetime.datetime.fromtimestamp(last):%d %b %H:%M}  ({int((time.time()-last)/60)} minutes ago)")
print(f"\nFAILED today: {len(fails)}")
for f in fails[-5:]: print("  ", f)
print("\nLatest log:")
for l in q["log"][-8:]: print("  ", l)
