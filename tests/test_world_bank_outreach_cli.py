import json
import subprocess
import sys
from pathlib import Path


def test_world_bank_outreach_cli(tmp_path):
    output_dir = tmp_path / "bundle"
    contacts_path = Path("docs/audit_candidate/world_bank_contacts.example.json").resolve()
    script_path = Path("scripts/world_bank_outreach.py").resolve()

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--contacts",
            str(contacts_path),
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    manifest_path = output_dir / "outreach_manifest.json"
    assert manifest_path.exists(), result.stdout + result.stderr
    manifest = json.loads(manifest_path.read_text())

    assert manifest["dispatch_summary"]["total_recipients"] == 3
    assert manifest.get("delivery_plan") == "delivery_plan.json"

    plan_path = output_dir / "delivery_plan.json"
    assert plan_path.exists(), result.stdout + result.stderr
    plan = json.loads(plan_path.read_text())

    assert plan["summary"]["total_tasks"] == 3
    assert plan["summary"]["channels"]["email"] == 1
    assert plan["summary"]["channels"]["secure_portal"] == 1
    assert plan["summary"]["channels"]["phone"] == 1

    for task in plan["tasks"]:
        assert task["status"] == "pending"
        assert len(task["message_sha256"]) == 64
        assert task["message_file"].startswith("messages/")
