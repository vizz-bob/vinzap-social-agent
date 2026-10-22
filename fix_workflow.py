"""One-time fix for .github/workflows/post.yml: step timeout + conflict-proof state save. Keeps your cron lines as they are."""
f = ".github/workflows/post.yml"
y = open(f).read()
y = y.replace("timeout-minutes: 25", "timeout-minutes: 20")
if "timeout-minutes: 10" not in y:
    y = y.replace("        run: python3 run_once.py\n", "        timeout-minutes: 10\n        run: python3 run_once.py\n", 1)
old = '          git diff --cached --quiet || { git commit -m "state $(date -u +%FT%TZ)" && git pull --rebase -q && git push; }'
new = '''          if ! git diff --cached --quiet; then
            git commit -m "state $(date -u +%FT%TZ)"
            for i in 1 2 3 4; do
              if git pull --rebase -X theirs -q && git push; then break; fi
              git rebase --abort 2>/dev/null || true
              sleep 4
            done
          fi'''
assert old in y or "rebase -X theirs" in y, "save-state step not found - send me the file"
y = y.replace(old, new)
open(f, "w").write(y)
print("workflow fixed")
