#!/usr/bin/env python3
"""Initialize YouTube OAuth tokens locally (DO NOT COMMIT).

Usage:
  python3 scripts/yt_oauth_init.py --client-secrets /path/to/client_secret.json

It writes a refreshable token file under ./memory/ (gitignored).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-secrets", required=True, help="OAuth client secret JSON (Desktop app)")
    ap.add_argument("--out", default="memory/youtube_token.json", help="Where to write token JSON")
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    flow = InstalledAppFlow.from_client_secrets_file(args.client_secrets, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")

    payload = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or []),
    }

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.chmod(out_path, 0o600)

    print(f"OK: wrote token to {out_path}")
    print("Next: run scripts/yt_sync.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
