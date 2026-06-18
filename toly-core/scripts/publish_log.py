#!/usr/bin/env python3
"""Internal CLI tool for publishing Toly company news updates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "news.json"


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower().strip())
    return value.strip("-")


def load_posts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array.")
    return data


def save_posts(path: Path, posts: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(posts, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def sort_posts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(posts, key=lambda item: item.get("date", ""), reverse=True)


def build_post(title: str, summary: str, category: str, date: str, body: str) -> dict[str, Any]:
    if not title or not summary or not category or not date:
        raise ValueError("title, summary, category, and date are required.")

    normalized_date = date.strip()
    try:
        datetime.strptime(normalized_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("date must use YYYY-MM-DD format.") from exc

    return {
        "id": f"{normalized_date}-{slugify(title)}",
        "date": normalized_date,
        "category": category,
        "title": title,
        "summary": summary,
        "body": body or summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a new internal log entry to the Toly website data file."
    )
    parser.add_argument("--title", required=True, help="Post title")
    parser.add_argument("--summary", required=True, help="Short summary shown in the public feed")
    parser.add_argument(
        "--category",
        required=True,
        choices=["company", "tools", "games", "studio"],
        help="Post category",
    )
    parser.add_argument(
        "--date",
        required=False,
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="Post date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--body",
        required=False,
        default="",
        help="Optional longer body text for the entry",
    )
    parser.add_argument(
        "--file",
        required=False,
        default=str(DEFAULT_DATA_FILE),
        help="Path to the JSON file to update",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the result without writing the file",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.file).resolve()

    try:
        new_post = build_post(
            title=args.title,
            summary=args.summary,
            category=args.category,
            date=args.date,
            body=args.body,
        )
        posts = load_posts(output_path)

        # Remove any existing post with the same id and place the new one at the top.
        posts = [item for item in posts if item.get("id") != new_post["id"]]
        posts = [new_post, *posts]
        posts = sort_posts(posts)

        if args.dry_run:
            json.dump(posts[:5], sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
            print(f"Dry run complete; no file was written to {output_path}", file=sys.stderr)
            return 0

        save_posts(output_path, posts)
        print(f"Published {new_post['title']} to {output_path}")
        return 0
    except Exception as exc:  # pragma: no cover - CLI output is the main behavior
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
