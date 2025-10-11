#!/usr/bin/env python3
"""Generate a packaged outreach bundle for multilateral banking supervisors.

This script turns the documentation in ``docs/audit_candidate`` into a
structured deliverable that can be transmitted to external partners.  It copies
all required evidence, produces individualized message drafts, and emits a
manifest that downstream dispatch tooling can consume.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_DOC_ROOT = REPO_ROOT / "docs" / "audit_candidate"
DEFAULT_DOCUMENTS = [
    AUDIT_DOC_ROOT / "plan.json",
    AUDIT_DOC_ROOT / "triage_summary.txt",
    AUDIT_DOC_ROOT / "evidence_bundle.json",
    AUDIT_DOC_ROOT / "account_recovery_guidance.md",
    AUDIT_DOC_ROOT / "normalization_guidelines.md",
    AUDIT_DOC_ROOT / "world_bank_outreach.md",
    AUDIT_DOC_ROOT / "subpoena_template.md",
]
DEFAULT_SUBJECT = (
    "Coordinated crypto audit package – wallet 0xABC… (2018-2024 review)"
)


@dataclass
class Contact:
    name: str
    organization: str
    email: Optional[str]
    phone: Optional[str]
    preferred_channel: str

    @classmethod
    def from_dict(cls, data: dict) -> "Contact":
        missing = [key for key in ("name", "organization", "preferred_channel") if key not in data]
        if missing:
            raise ValueError(f"Contact entry missing required keys: {', '.join(missing)}")
        email = data.get("email")
        phone = data.get("phone")
        preferred_channel = data.get("preferred_channel")
        return cls(
            name=str(data["name"]).strip(),
            organization=str(data["organization"]).strip(),
            email=str(email).strip() if email else None,
            phone=str(phone).strip() if phone else None,
            preferred_channel=str(preferred_channel).strip().lower(),
        )

    def short_name(self) -> str:
        return re.sub(r"[^A-Za-z0-9]+", "_", self.name or "contact").strip("_") or "contact"


@dataclass
class DocumentRecord:
    source: Path
    dest: Path
    sha256: str


@dataclass
class MessageRecord:
    contact: Contact
    subject: str
    filename: Path


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contacts(path: Path) -> List[Contact]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Contacts file must contain a list of contact objects")
    contacts = [Contact.from_dict(item) for item in data]
    if not contacts:
        raise ValueError("Contacts list is empty")
    return contacts


def ensure_documents_exist(documents: Iterable[Path]) -> None:
    missing = [str(path) for path in documents if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "The following required documentation was not found: " + ", ".join(missing)
        )


def copy_documents(documents: Iterable[Path], target_dir: Path) -> List[DocumentRecord]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: List[DocumentRecord] = []
    for source in documents:
        destination = target_dir / source.name
        shutil.copy2(source, destination)
        copied.append(DocumentRecord(source=source, dest=destination, sha256=_hash_file(destination)))
    return copied


def compose_message(contact: Contact, subject: str) -> str:
    greeting = contact.name or "Representative"
    channel_line = f"Preferred channel: {contact.preferred_channel.upper()}"
    if contact.email:
        channel_line += f" | Email: {contact.email}"
    if contact.phone:
        channel_line += f" | Phone: {contact.phone}"

    body = f"""Dear {greeting},

The World Bank/BIS joint task force has prepared the enclosed cryptocurrency audit package for wallet 0xABC… covering the 2018-01-01 through 2024-12-31 review window. The bundle contains the prioritized audit plan, triage summary, subpoena-ready evidence inventory, and account recovery safeguards required for coordinated supervisory action.

Key requests:
  • Acknowledge receipt within two business days.
  • Confirm your designated escalation point for cross-border enforcement.
  • Share any overlapping investigations, risk assessments, or sanctions that touch this wallet cluster.

Chain-of-custody safeguards, document hashes, and outreach attestations are embedded in the manifest. Please initiate secure follow-up on the documented preferred channel.

Regards,
World Bank/BIS Crypto Forensics Coordination Cell
"""
    return f"Subject: {subject}\n{channel_line}\n\n{body}"


def write_messages(contacts: Iterable[Contact], subject: str, target_dir: Path) -> List[MessageRecord]:
    target_dir.mkdir(parents=True, exist_ok=True)
    messages: List[MessageRecord] = []
    for contact in contacts:
        filename = target_dir / f"{contact.short_name().lower()}_message.txt"
        content = compose_message(contact, subject)
        filename.write_text(content, encoding="utf-8")
        messages.append(MessageRecord(contact=contact, subject=subject, filename=filename))
    return messages


def build_manifest(
    output_dir: Path,
    contacts: Iterable[Contact],
    documents: Iterable[DocumentRecord],
    messages: Iterable[MessageRecord],
) -> dict:
    timestamp = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    return {
        "generated_at": timestamp,
        "repo_root": str(REPO_ROOT),
        "output_dir": str(output_dir),
        "documents": [
            {
                "source": str(record.source.relative_to(REPO_ROOT)),
                "copied_to": str(record.dest.relative_to(output_dir)),
                "sha256": record.sha256,
            }
            for record in documents
        ],
        "contacts": [
            {
                "name": contact.name,
                "organization": contact.organization,
                "preferred_channel": contact.preferred_channel,
                **({"email": contact.email} if contact.email else {}),
                **({"phone": contact.phone} if contact.phone else {}),
            }
            for contact in contacts
        ],
        "messages": [
            {
                "contact": message.contact.name,
                "organization": message.contact.organization,
                "subject": message.subject,
                "file": str(message.filename.relative_to(output_dir)),
            }
            for message in messages
        ],
    }


def write_manifest(manifest: dict, path: Path) -> None:
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def archive_bundle(output_dir: Path, archive_path: Path) -> Path:
    with ZipFile(archive_path, "w") as bundle:
        for file_path in sorted(output_dir.rglob("*")):
            if file_path.is_file():
                bundle.write(file_path, file_path.relative_to(output_dir))
    return archive_path


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble a world-bank outreach package")
    parser.add_argument("--contacts", required=True, type=Path, help="Path to JSON contact list")
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output directory where the outreach bundle will be generated",
    )
    parser.add_argument(
        "--subject",
        default=DEFAULT_SUBJECT,
        help="Email/letter subject line for all generated messages",
    )
    parser.add_argument(
        "--zip",
        dest="zip_archive",
        action="store_true",
        help="If set, also produce a ZIP archive of the outreach bundle",
    )
    parser.add_argument(
        "--documents",
        nargs="*",
        type=Path,
        default=DEFAULT_DOCUMENTS,
        help="Optional override list of documentation paths to include",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    contacts = load_contacts(args.contacts)
    ensure_documents_exist(args.documents)

    output_dir = args.output.resolve()
    documents_dir = output_dir / "documents"
    messages_dir = output_dir / "messages"
    manifest_path = output_dir / "outreach_manifest.json"

    documents = copy_documents(args.documents, documents_dir)
    messages = write_messages(contacts, args.subject, messages_dir)
    manifest = build_manifest(output_dir, contacts, documents, messages)
    write_manifest(manifest, manifest_path)

    print(f"Generated {len(documents)} documents and {len(messages)} messages into {output_dir}")
    print(f"Manifest written to {manifest_path}")

    if args.zip_archive:
        archive_path = output_dir.with_suffix(".zip")
        archive_bundle(output_dir, archive_path)
        print(f"Archive generated at {archive_path}")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
