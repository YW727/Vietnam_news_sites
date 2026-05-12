# Vietnam News Sites

Monorepo containing two Vercel-deployed news sites that get auto-updated each morning.

## Sites

| Folder | Production URL | Topic |
|--------|----------------|-------|
| `pv-power-news/` | https://pv-power-news.vercel.app | Vietnam PV Power / Quynh Lap LNG project progress |
| `vietnam-ai-dc-news/` | https://vietnam-ai-dc-news.vercel.app | Vietnam AI Data Center industry news |
| `rafael-attendance/` | (deploy separately) | Rafael 주말 봉사활동 출석/역할 관리 정적 웹앱 (localStorage 기반) |

## Daily Update Routine

A scheduled Claude Code routine runs every morning at **07:00 Asia/Seoul** (22:00 UTC prev day):

1. Searches for new news about each topic since the last run
2. Updates the 5-article block in each site's HTML (newest first, oldest dropped)
3. Commits + pushes to this repo
4. Vercel auto-deploys both sites on push
5. Sends an email summary to `youngwookyoo@gmail.com`

## Local Layout

Each subfolder contains:
- `*.html` — the static page
- `vercel.json` — Vercel rewrite to serve the HTML at `/`
- Any supporting images (LNG map, AI DC map, etc.)
