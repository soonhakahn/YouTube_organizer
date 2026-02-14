# YouTube_organizer

A lightweight PWA + sync pipeline to organize your YouTube content:
- Watch Later (WL)
- Liked videos (LL)
- Your playlists

## PWA
- https://soonhakahn.github.io/YouTube_organizer/

## Security
- **OAuth secrets/tokens are stored locally and are gitignored.**
- Only public-friendly outputs are committed:
  - `reports/index.json`
  - `reports/summary.md`

## One-time setup (Google Cloud)
1) Create a project in Google Cloud Console.
2) Enable **YouTube Data API v3**.
3) Configure OAuth consent screen.
4) Create OAuth Client ID → **Desktop app**.
5) Download the client secret JSON.

## Local setup (macOS)
```bash
cd ~/.openclaw/workspace/projects/YouTube_organizer

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 1) OAuth init (first time)
```bash
python3 scripts/yt_oauth_init.py --client-secrets ~/Downloads/client_secret_*.json
```

This writes a refreshable token to:
- `memory/youtube_token.json` (local only, gitignored)

## 2) Sync + publish
```bash
./scripts/run_sync.sh
```

## Cron example (after first OAuth)
Run daily at 06:45 KST:

```cron
45 6 * * * cd ~/.openclaw/workspace/projects/YouTube_organizer && ./scripts/run_sync.sh >> ./memory/cron.log 2>&1
```

(If you want a different schedule, change the cron expression.)
