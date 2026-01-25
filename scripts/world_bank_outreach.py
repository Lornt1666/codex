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
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from zipfile import ZipFile
from collections import Counter

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

    def channel_key(self) -> str:
        return _normalize_channel(self.preferred_channel)


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


@dataclass
class DispatchTask:
    task_id: str
    contact: Contact
    method: str
    target: str
    message_file: Path
    instructions: str
    status: str = "pending"


def _normalize_channel(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower())


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rel_path(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


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


def prepare_output_dir(path: Path, overwrite: bool) -> None:
    if path.exists():
        if any(path.iterdir()):
            if not overwrite:
                raise FileExistsError(
                    f"Output directory {path} is not empty. Use --overwrite to regenerate the bundle"
                )
            shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


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


def _resolve_dispatch_details(contact: Contact) -> Dict[str, str]:
    channel = contact.channel_key()

    if channel in {"email", "e_mail"}:
        if not contact.email:
            raise ValueError(
                f"Contact {contact.name} does not have an email address for email dispatch"
            )
        return {
            "method": "email",
            "target": contact.email,
            "instructions": (
                "Send the message via encrypted email (S/MIME or PGP) and attach the manifest "
                "hash reference. Log the acknowledgement ID in the communications ledger."
            ),
        }

    if channel in {"phone", "telephone", "voice", "voice_call"}:
        if not contact.phone:
            raise ValueError(
                f"Contact {contact.name} does not have a phone number for phone dispatch"
            )
        return {
            "method": "phone",
            "target": contact.phone,
            "instructions": (
                "Place a recorded compliance-reviewed call referencing the message file. "
                "Confirm the recipient's identity using the roster passphrase before "
                "summarizing key actions and email the manifest hash upon completion."
            ),
        }

    if channel in {"secure_portal", "portal", "secure_gateway"}:
        return {
            "method": "secure_portal",
            "target": contact.organization,
            "instructions": (
                "Upload the message file to the institution's authenticated supervisory portal. "
                "Reference the case identifier and manifest hash, then capture the portal "
                "receipt number for the outreach ledger."
            ),
        }

    raise ValueError(
        f"Unsupported preferred channel '{contact.preferred_channel}' for contact {contact.name}"
    )


def generate_dispatch_tasks(
    messages: Iterable[MessageRecord],
) -> List[DispatchTask]:
    tasks: List[DispatchTask] = []
    for message in messages:
        details = _resolve_dispatch_details(message.contact)
        tasks.append(
            DispatchTask(
                task_id=uuid.uuid4().hex,
                contact=message.contact,
                method=details["method"],
                target=details["target"],
                message_file=message.filename,
                instructions=details["instructions"],
            )
        )
    return tasks


def build_dispatch_plan(output_dir: Path, tasks: Iterable[DispatchTask]) -> dict:
    task_list = list(tasks)
    now = dt.datetime.utcnow().replace(microsecond=0)
    ack_deadline = (now + dt.timedelta(days=2)).isoformat() + "Z"
    channel_counts = Counter(task.method for task in task_list)

    return {
        "generated_at": now.isoformat() + "Z",
        "acknowledgment_deadline": ack_deadline,
        "summary": {
            "total_tasks": len(task_list),
            "channels": dict(channel_counts),
        },
        "tasks": [
            {
                "task_id": task.task_id,
                "contact": {
                    "name": task.contact.name,
                    "organization": task.contact.organization,
                },
                "method": task.method,
                "target": task.target,
                "message_file": _rel_path(task.message_file, output_dir),
                "message_sha256": _hash_file(task.message_file),
                "instructions": task.instructions,
                "status": task.status,
                "compliance_controls": [
                    "Verify roster signature before dispatch",
                    "Record delivery attempt in the outreach ledger with manifest hash",
                ],
            }
            for task in task_list
        ],
    }


def write_dispatch_plan(plan: dict, path: Path) -> None:
    path.write_text(json.dumps(plan, indent=2), encoding="utf-8")


def build_manifest(
    output_dir: Path,
    contacts: Iterable[Contact],
    documents: Iterable[DocumentRecord],
    messages: Iterable[MessageRecord],
    dispatch_plan_path: Optional[Path],
    dispatch_tasks: Iterable[DispatchTask],
) -> dict:
    contact_list = list(contacts)
    document_list = list(documents)
    message_list = list(messages)
    task_list = list(dispatch_tasks)
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
            for record in document_list
        ],
        "contacts": [
            {
                "name": contact.name,
                "organization": contact.organization,
                "preferred_channel": contact.preferred_channel,
                **({"email": contact.email} if contact.email else {}),
                **({"phone": contact.phone} if contact.phone else {}),
            }
            for contact in contact_list
        ],
        "dispatch_summary": {
            "total_recipients": len(contact_list),
            "channels": dict(Counter(task.method for task in task_list)),
        },
        **(
            {"delivery_plan": _rel_path(dispatch_plan_path, output_dir)}
            if dispatch_plan_path is not None
            else {}
        ),
        "messages": [
            {
                "contact": message.contact.name,
                "organization": message.contact.organization,
                "subject": message.subject,
                "file": str(message.filename.relative_to(output_dir)),
            }
            for message in message_list
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
    parser.add_argument(
        "--delivery-plan",
        type=Path,
        default=None,
        help="Optional path for the generated dispatch plan JSON (defaults to <output>/delivery_plan.json)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow regenerating the bundle if the output directory already exists and is not empty",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    contacts = load_contacts(args.contacts)
    ensure_documents_exist(args.documents)

    output_dir = args.output.resolve()
    prepare_output_dir(output_dir, args.overwrite)
    documents_dir = output_dir / "documents"
    messages_dir = output_dir / "messages"
    manifest_path = output_dir / "outreach_manifest.json"
    if args.delivery_plan:
        delivery_plan_path = args.delivery_plan
        if not delivery_plan_path.is_absolute():
            delivery_plan_path = output_dir / delivery_plan_path
    else:
        delivery_plan_path = output_dir / "delivery_plan.json"

    documents = copy_documents(args.documents, documents_dir)
    messages = write_messages(contacts, args.subject, messages_dir)
    dispatch_tasks = generate_dispatch_tasks(messages)
    dispatch_plan = build_dispatch_plan(output_dir, dispatch_tasks)
    delivery_plan_path.parent.mkdir(parents=True, exist_ok=True)
    write_dispatch_plan(dispatch_plan, delivery_plan_path)
    manifest = build_manifest(
        output_dir,
        contacts,
        documents,
        messages,
        delivery_plan_path,
        dispatch_tasks,
    )
    write_manifest(manifest, manifest_path)

    print(f"Generated {len(documents)} documents and {len(messages)} messages into {output_dir}")
    print(f"Manifest written to {manifest_path}")
    print(f"Dispatch plan written to {delivery_plan_path}")

    if args.zip_archive:
        archive_path = output_dir.with_suffix(".zip")
        if args.overwrite and archive_path.exists():
            archive_path.unlink()
        archive_bundle(output_dir, archive_path)
        print(f"Archive generated at {archive_path}")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
