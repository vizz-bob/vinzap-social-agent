#!/usr/bin/env python3
"""Cheap gate (standard library only): prints due=true/false for GitHub Actions. Saves minutes at night."""
import os, json, time, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
c = dict(start_hour=8, end_hour=23, interval_minutes=60)
try: c.update(json.load(open(os.path.join(HERE, "config.json"))))
except Exception: pass
try: q = json.load(open(os.path.join(HERE, "state", "queue.json")))
except Exception: q = {}
hr = datetime.datetime.now().hour
inside = c["start_hour"] <= hr < c["end_hour"]
due = inside and (time.time() - q.get("last_post", 0) >= c["interval_minutes"] * 60 - 420)
print(f"hour={hr} inside_window={inside} due={due}")
out = os.environ.get("GITHUB_OUTPUT")
if out: open(out, "a").write(f"due={'true' if due else 'false'}\n")
