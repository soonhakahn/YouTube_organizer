#!/usr/bin/env python3
"""Sync YouTube playlists into public reports.

- Reads OAuth token from ./memory/youtube_token.json (gitignored)
- Fetches:
  - Watch Later (playlistId=WL)
  - Liked videos (playlistId=LL)
  - User playlists (mine=true)
- Writes:
  - reports/index.json (for PWA UI)
  - reports/summary.md

Then (optionally) commits + pushes to GitHub.

Usage:
  python3 scripts/yt_sync.py --push

Note:
- The output contains only titles/urls/channel/publishedAt/thumbnails; no auth secrets.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_PATH = Path("memory/youtube_token.json")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_creds() -> Credentials:
    if not TOKEN_PATH.exists():
        raise SystemExit("Missing token. Run scripts/yt_oauth_init.py first.")
    data = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes") or SCOPES,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # persist updated access token
        data["token"] = creds.token
        TOKEN_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.chmod(TOKEN_PATH, 0o600)
    return creds


def yt_service(creds: Credentials):
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def list_playlist_items(youtube, playlist_id: str, max_items: int = 50) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    page_token = None
    while True:
        req = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=min(50, max_items - len(items)),
            pageToken=page_token,
        )
        resp = req.execute()
        for it in resp.get("items", []):
            sn = it.get("snippet", {})
            cd = it.get("contentDetails", {})
            vid = cd.get("videoId") or (sn.get("resourceId", {}) or {}).get("videoId")
            if not vid:
                continue
            thumb = ((sn.get("thumbnails") or {}).get("medium") or {}).get("url")
            items.append(
                {
                    "videoId": vid,
                    "title": sn.get("title"),
                    "channel": sn.get("videoOwnerChannelTitle") or sn.get("channelTitle"),
                    "publishedAt": cd.get("videoPublishedAt") or sn.get("publishedAt"),
                    "thumbnail": thumb,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                }
            )
            if len(items) >= max_items:
                break
        if len(items) >= max_items:
            break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items


def list_playlists(youtube, max_playlists: int = 50) -> List[Dict[str, Any]]:
    out = []
    page_token = None
    while True:
        req = youtube.playlists().list(
            part="snippet,contentDetails",
            mine=True,
            maxResults=min(50, max_playlists - len(out)),
            pageToken=page_token,
        )
        resp = req.execute()
        for it in resp.get("items", []):
            sn = it.get("snippet", {})
            cd = it.get("contentDetails", {})
            out.append(
                {
                    "playlistId": it.get("id"),
                    "title": sn.get("title"),
                    "count": (cd.get("itemCount")),
                }
            )
            if len(out) >= max_playlists:
                break
        if len(out) >= max_playlists:
            break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return out


def build_report(youtube, max_items_each: int = 60, max_playlists: int = 30) -> Dict[str, Any]:
    updated_at = now_iso()

    sections = []

    # Watch Later / Liked are special playlist IDs
    for title, pid, kind in [
        ("Watch Later", "WL", "watch_later"),
        ("Liked", "LL", "liked"),
    ]:
        try:
            items = list_playlist_items(youtube, pid, max_items=max_items_each)
        except Exception as e:
            items = []
        for it in items:
            it["kind"] = kind
        sections.append({"title": title, "items": items})

    pls = list_playlists(youtube, max_playlists=max_playlists)

    # For each playlist, fetch a few items
    playlist_sections = []
    for pl in pls:
        pid = pl.get("playlistId")
        if not pid:
            continue
        try:
            items = list_playlist_items(youtube, pid, max_items=min(25, max_items_each))
        except Exception:
            items = []
        for it in items:
            it["kind"] = "playlist"
            it["playlistTitle"] = pl.get("title")
        playlist_sections.append({"title": pl.get("title"), "playlistId": pid, "count": pl.get("count"), "items": items})

    # Flatten playlist section into one section for PWA (simpler)
    flat_playlist_items = []
    for ps in playlist_sections:
        for it in ps.get("items", []):
            flat_playlist_items.append(it)

    sections.append({"title": "Playlists", "items": flat_playlist_items})

    # Summary markdown
    def count_items(sec_title: str) -> int:
        for s in sections:
            if s["title"] == sec_title:
                return len(s.get("items", []))
        return 0

    md = []
    md.append("# YouTube Organizer\n")
    md.append(f"업데이트: {updated_at}\n\n")
    md.append("## 개요\n")
    md.append(f"- Watch Later: {count_items('Watch Later')}개(표시 상위)\n")
    md.append(f"- Liked: {count_items('Liked')}개(표시 상위)\n")
    md.append(f"- Playlists: {len(pls)}개(표시 상위)\n")
    md.append("\n## 사용 팁\n")
    md.append("- PWA에서 항목을 누르면 YouTube로 이동해 재생됩니다.\n")
    md.append("- OAuth 토큰은 Mac 로컬에만 저장되며, GitHub에는 결과만 올라갑니다.\n")

    return {
        "updatedAt": updated_at,
        "status": "ok",
        "summary": "".join(md),
        "sections": sections,
    }


def write_outputs(report: Dict[str, Any]) -> None:
    Path("reports").mkdir(parents=True, exist_ok=True)
    Path("reports/index.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("reports/summary.md").write_text(report.get("summary", ""), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true", help="git commit & push")
    ap.add_argument("--max-items", type=int, default=60)
    ap.add_argument("--max-playlists", type=int, default=30)
    args = ap.parse_args()

    creds = load_creds()
    youtube = yt_service(creds)

    report = build_report(youtube, max_items_each=args.max_items, max_playlists=args.max_playlists)
    write_outputs(report)

    print("OK: wrote reports/index.json and reports/summary.md")

    if args.push:
        import subprocess

        subprocess.check_call(["git", "add", "reports/index.json", "reports/summary.md"])
        subprocess.check_call(["git", "commit", "-m", "Update YouTube Organizer reports"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call(["git", "push"])
        print("OK: pushed to GitHub")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
