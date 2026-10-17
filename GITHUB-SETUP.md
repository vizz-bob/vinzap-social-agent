# Free 24/7 posting with GitHub Actions (Mac can be off)

GitHub runs `run_once.py` every hour on its own computers. Each run reads a product from vinzapstore.in, designs ONE Reel or poster (they alternate), posts it to Instagram, both Facebook Pages and (Reels only) YouTube, and saves what it did in `state/queue.json`.
Cost: GitHub Free, no card. Tested in dry-run: one run takes about 40 seconds of work.

## One-time setup (Mac Terminal)
1. Install GitHub's tool and log in (a browser window opens, no card needed):
   ```
   brew install gh
   gh auth login
   ```
2. Upload this folder as a PRIVATE repository:
   ```
   cd /Volumes/Testing/1A-1A-aaYoutube_tutorial/Shorts/social-agent-github
   mkdir -p .github/workflows && cp github-workflow/post.yml .github/workflows/post.yml
   git init -b main && git add . && git commit -m "social agent"
   gh repo create vinzap-social-agent --private --source=. --push
   ```
3. Give GitHub your keys as a secret (copied straight from your Mac, never typed in chat):
   ```
   gh secret set CONFIG_JSON < ../social-agent/config.json
   ```
4. Test once now:
   ```
   gh workflow run post.yml
   gh run watch
   ```
5. Stop the Mac copy (Ctrl+C in the Terminal running run.command) so nothing posts twice.

From then on it runs by itself every hour between your start/end hours in `config.json` (default 8-23 India time).

## Change settings
Edit `../social-agent/config.json` (hours, interval, `youtube_privacy`, `festival_discount_percent`), then run step 3 again.

## Check what happened
- GitHub > your repo > **Actions** tab: green tick = OK. Click a run to see the log (`POSTED ...` lines).
- `state/queue.json` in the repo holds the history.

## Good to know
- GitHub may start a run a few minutes late. The script allows for it.
- If you do not push for 60 days, GitHub pauses scheduled runs. Pressing "Run workflow" (or any commit) restarts them. The agent commits its state every run, so this normally does not happen.
- Private repos get 2,000 free minutes a month. Real work is about 1 minute per run plus setup, so usage is roughly 600-900 minutes a month.
- Keys live only in the GitHub secret. The workflow deletes config.json before saving state, and `.gitignore` also blocks it.
- Products already posted from your Mac are not remembered here, so an early product may repeat once.
