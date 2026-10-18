# Reliable timer for the GitHub agent (free)

Problem: GitHub's own schedule is unreliable on small repos (runs late or is skipped, you saw 2-3 hour gaps).
Fix: cron-job.org (free) tells GitHub to start the workflow every 15 minutes. The script still posts only when a post is due (every 30 minutes).

## 1. Limited GitHub token
https://github.com/settings/personal-access-tokens/new
- Name: cron trigger. Expiration: 1 year (put a reminder to renew it).
- Repository access: Only select repositories > vinzap-social-agent
- Repository permissions: Actions = Read and write
- Generate token, copy it. Never paste it in a chat.

## 2. cron-job.org
Create cronjob:
- URL: https://api.github.com/repos/vizz-bob/vinzap-social-agent/actions/workflows/post.yml/dispatches
- Schedule: every 15 minutes, hours 11-23 only, time zone Asia/Kolkata
- Advanced: Request method POST
- Headers:
  - Authorization: Bearer YOUR_TOKEN
  - Accept: application/vnd.github+json
  - Content-Type: application/json
- Request body: {"ref":"main"}
- Save, then "Test run". HTTP 204 = OK.

## 3. Check
git pull -q && python3 status.py

## Free minutes
48 checks a day, about 1 minute each = roughly 1,450 minutes a month (limit for a private repo: 2,000).
Settings you can change in ../social-agent/config.json (then: gh secret set CONFIG_JSON < ../social-agent/config.json):
interval_minutes (30), daily_cap_per_platform (22), start_hour (12), end_hour (23), youtube_privacy.
