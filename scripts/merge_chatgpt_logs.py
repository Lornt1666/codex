#!/usr/bin/env python3
"""Merge multiple ChatGPT export files into a unified timeline.

This helper reads exported ChatGPT conversations (the `conversations.json`
file produced by https://chat.openai.com/#settings->Data Controls->Export,
either directly or inside the ZIP archive you receive by email) for a set of
accounts that belong to the same individual. The script normalizes every
message into a timeline that records which account the message originated from
and keeps the original metadata so researchers can trace the merged log back to
its source.

Example usage::

    python scripts/merge_chatgpt_logs.py \
        --account Lornt_lyfe@Hotmail.com=/path/to/export1 \
        --account JusticeGraym@gmail.com=/path/to/export2 \
        --account Justlornt95@gmail.com=/path/to/export3 \
        --output justice_maciocha_chatlogs.json

By default the script writes to ``merged_chatgpt_logs.json`` in the current
working directory.
"""

from __future__ import annotations

import argparse
import dataclasses
import io
import json
import sys
import zipfile
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple


@dataclasses.dataclass
class NormalizedMessage:
    """Represents a single message event in a ChatGPT conversation."""

    email: str
    conversation_id: str
    conversation_title: str | None
    message_id: str
    role: str | None
    author_name: str | None
    create_time: float | None
    create_time_iso: str | None
    content: str
    metadata: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


def parse_account_mapping(value: str) -> Tuple[str, Path]:
    try:
        email, export_path = value.split("=", 1)
    except ValueError as exc:  # pragma: no cover - argparse handles user errors.
        raise argparse.ArgumentTypeError(
            "Accounts must be formatted as EMAIL=EXPORT_PATH",
        ) from exc
    email = email.strip()
    if not email:
        raise argparse.ArgumentTypeError("Email portion cannot be empty")

    path = Path(export_path).expanduser().resolve()
    return email, path


def load_conversations(export_root: Path) -> List[Dict[str, Any]]:
    """Load the exported conversations JSON for a single account."""

    if export_root.is_file():
        suffix = export_root.suffix.lower()
        if suffix == ".json":
            with export_root.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            source = str(export_root)
        elif suffix == ".zip":
            data = _load_from_zip(export_root)
            source = f"{export_root}!conversations.json"
        else:
            raise FileNotFoundError(
                f"Unrecognized export file {export_root}; expected conversations.json or an export .zip",
            )
    else:
        conv_path = export_root / "conversations.json"
        if not conv_path.exists():
            raise FileNotFoundError(
                f"Could not find conversations.json at {conv_path}; did you unzip the export?",
            )
        with conv_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        source = str(conv_path)

    if not isinstance(data, list):
        raise ValueError(f"Unexpected conversations payload at {source}")

    return data


def _load_from_zip(zip_path: Path) -> List[Dict[str, Any]]:
    """Read conversations from a ChatGPT export ZIP archive."""

    with zipfile.ZipFile(zip_path) as archive:
        try:
            with archive.open("conversations.json") as raw:
                with io.TextIOWrapper(raw, encoding="utf-8") as fh:
                    data = json.load(fh)
        except KeyError as exc:
            raise FileNotFoundError(
                f"{zip_path} does not contain conversations.json; check the export archive.",
            ) from exc

    return data


def iter_messages(email: str, conversation: Dict[str, Any]) -> Iterator[NormalizedMessage]:
    conversation_id = conversation.get("id") or conversation.get("conversation_id")
    title = conversation.get("title")

    mapping = conversation.get("mapping", {})
    if not isinstance(mapping, dict):
        return

    for message_id, node in mapping.items():
        message = node.get("message") if isinstance(node, dict) else None
        if not message:
            continue

        author = message.get("author") or {}
        metadata = {
            key: value
            for key, value in message.items()
            if key not in {"content", "create_time", "author"}
        }

        raw_time = message.get("create_time")
        iso_time = _safe_isoformat(raw_time)

        yield NormalizedMessage(
            email=email,
            conversation_id=conversation_id,
            conversation_title=title,
            message_id=message.get("id") or message_id,
            role=author.get("role"),
            author_name=author.get("name"),
            create_time=raw_time,
            create_time_iso=iso_time,
            content=_extract_content_text(message.get("content")),
            metadata={"author": author, **metadata},
        )


def _extract_content_text(content: Dict[str, Any] | None) -> str:
    if not isinstance(content, dict):
        return ""

    parts = content.get("parts")
    if isinstance(parts, list):
        return "\n\n".join(str(part) for part in parts if part is not None)

    # Fallback for unexpected content shapes (e.g., code interpreter payloads).
    return json.dumps(content, ensure_ascii=False, sort_keys=True)


def _safe_isoformat(timestamp: float | None) -> str | None:
    if not isinstance(timestamp, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def build_timeline(accounts: Iterable[Tuple[str, Path]]) -> List[Dict[str, Any]]:
    timeline: List[NormalizedMessage] = []
    for email, export_root in accounts:
        conversations = load_conversations(export_root)
        for conversation in conversations:
            timeline.extend(iter_messages(email, conversation))

    timeline.sort(key=lambda msg: (msg.create_time or float("inf"), msg.message_id))
    return [message.as_dict() for message in timeline]


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--account",
        action="append",
        type=parse_account_mapping,
        metavar="EMAIL=EXPORT_PATH",
        help=(
            "Account email and export path pairing. Repeat for each export that should be "
            "merged. The export path can be the extracted directory, the conversations.json file, "
            "or the untouched export .zip."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("merged_chatgpt_logs.json"),
        help="Destination file for the merged timeline (default: merged_chatgpt_logs.json).",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.account:
        raise SystemExit("At least one --account EMAIL=EXPORT_PATH pair is required")

    timeline = build_timeline(args.account)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        json.dump(timeline, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"Wrote merged timeline with {len(timeline)} messages to {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point guard.
    raise SystemExit(main())
