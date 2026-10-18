# Set 30-minute posting + 22 posts/day cap

Run in Terminal, inside the social-agent-github folder:

```
python3 - <<'PY'
import json
f = "../social-agent/config.json"
c = json.load(open(f))
c["interval_minutes"] = 30
c["daily_cap_per_platform"] = 22
c["start_hour"] = 12
c["end_hour"] = 23
json.dump(c, open(f, "w"), indent=2)
print("saved:", c["interval_minutes"], c["daily_cap_per_platform"], c["start_hour"], c["end_hour"])
PY
gh secret set CONFIG_JSON < ../social-agent/config.json
```

Expected: a line `saved: 30 22 12 23`, then a green tick for the secret.
