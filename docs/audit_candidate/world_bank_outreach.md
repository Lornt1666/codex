# World Bank / BIS Outreach Automation Specification

This specification defines the automated coordination function responsible for notifying authorized multilateral banking supervisors about significant findings from the 0xABC... investigation. It assumes execution inside the approved zero-trust enclave jointly operated by the World Bank, BIS, and allied prudential authorities.

## 1. Objectives
- Ensure every relevant global banking supervisor receives the sanctioned audit briefing without manual duplication.
- Prevent unauthorized disclosure by enforcing legal gating, need-to-know segmentation, and cryptographic controls.
- Capture tamper-evident logs that demonstrate compliant delivery attempts, retries, and receipt confirmation.

## 2. Inputs
| Field | Description |
| --- | --- |
| `case_id` | Multilateral case number issued by the World Bank/BIS task force. |
| `legal_basis_doc` | Hash reference to the court order, subpoena, or treaty mandate authorizing multilateral disclosure. |
| `briefing_manifest` | Pointer to the signed evidence bundle hosted in the zero-trust enclave. |
| `contact_rosters` | Signed rosters retrieved from BIS, World Bank, IMF, and regional development bank directories. |
| `distribution_policy` | Ruleset defining which institutions receive each document class and escalation contact. |

## 3. High-Level Flow
1. **Validate legal basis**: Confirm the legal document hash matches the approval stored in the compliance vault. Abort if the mandate has expired or scope limits distribution.
2. **Ingest contact rosters**: Fetch the latest rosters over mutually authenticated channels. Compare signatures and versions; reject stale or unsigned data.
3. **Segment recipients**: Apply the distribution policy to allocate briefing components by supervisory role, jurisdiction, and sensitivity tier.
4. **Assemble packets**: For each recipient cluster, compile an encrypted package containing:
   - Executive summary
   - Top risk findings and red flags
   - Evidence manifest references
   - Recovery and normalization guidance excerpts relevant to the recipient scope
5. **Transmit via enclave**: Deliver packets using the enclave’s relay API with hardware-backed signing, per-recipient access expiry, and policy-driven retry logic.
6. **Log and reconcile**: Store delivery receipts, message hashes, and retry status in the communications ledger. Trigger counsel review on persistent failures.

## 4. Functional Blueprint
```pseudo
function coordinate_world_bank_outreach(case_id,
                                        legal_basis_doc,
                                        briefing_manifest,
                                        contact_rosters,
                                        distribution_policy):
    require legal_authority_valid(legal_basis_doc, case_id)
    recipients = load_verified_rosters(contact_rosters)
    allocations = apply_distribution_policy(recipients, distribution_policy)
    for allocation in allocations:
        packet = build_packet(case_id, allocation, briefing_manifest)
        result = send_packet_via_enclave(packet, allocation.recipient)
        record_comm_log(case_id, allocation.recipient, result)
        if result.status == "failure" and result.retry_count >= 3:
            escalate_to_counsel(case_id, allocation.recipient, result)
        if result.status == "failure" and result.fallback_channel_attempted:
            raise_control_alert(case_id, allocation.recipient, result)
    consolidate_receipts(case_id)
    return generate_outreach_report(case_id)
```

## 5. Controls and Safeguards
- **Authorization cache**: Scheduler validates authority before each run; cached approvals expire after 24 hours.
- **Segregated secrets**: API credentials and signing keys reside in HSM-backed secret stores; no plaintext keys on disk.
- **Rate limiting**: Enforce per-recipient throttles to avoid being flagged as spam and to respect supervisory portal constraints.
- **Monitoring**: Emit metrics (success count, retry rate, suppression count) to the multilateral observability dashboard.
- **Incident hooks**: If anomaly detection flags suspicious behavior (e.g., roster tampering, unauthorized policy changes), automatically suspend the job and alert security operations.
- **Bypass prohibition**: Disallow unapproved fallback transports; any request to use unsanctioned channels must be rejected automatically and surfaced for manual legal review with a documented denial entry.
- **Failure attestations**: For each unrecovered delivery after manual escalation, capture a compliance officer attestation confirming that no circumvention attempts were made prior to closing the ticket.

## 6. Deliverables
- Outreach execution report summarizing recipients contacted, successful deliveries, and outstanding escalations.
- Append-only communications ledger containing message hashes, timestamps, and acknowledgment identifiers.
- Updated evidence bundle entries for roster signatures, delivery receipts, and escalation correspondence.

## 7. Governance
- Quarterly review by the World Bank/BIS supervisory committee to verify control effectiveness.
- Annual penetration test of the outreach enclave to confirm resilience against misuse.
- Change management requiring dual approval (audit lead + compliance officer) for modifications to distribution policies or contact roster sources.

This function enables trusted, auditable dissemination of critical findings to world banking authorities without bypassing statutory guardrails.

## 8. Operational Tooling

Use `scripts/world_bank_outreach.py` to assemble the outbound package that will be transmitted through the enclave relay. The tool copies the latest case documentation, generates per-recipient dispatch memos, and produces a tamper-evident manifest of artifacts.

```bash
python scripts/world_bank_outreach.py \
  --contacts docs/audit_candidate/world_bank_contacts.example.json \
  --output out/world-bank-package \
  --zip
```

Inputs:
- `--contacts`: JSON array describing each authorized representative (see `world_bank_contacts.example.json`).
- `--documents`: Optional override list of files to include (defaults to the seven sanctioned artifacts).
- `--subject`: Subject line inserted into every generated message draft.
- `--zip`: Produce a `.zip` archive mirroring the generated folder for secure upload.
- `--delivery-plan`: Override the default `delivery_plan.json` location. Relative paths are created inside the output folder.
- `--overwrite`: Permit the script to clear an existing non-empty output directory before regenerating the bundle.

Outputs:
- `documents/`: Verified copies of all evidence files with preserved timestamps.
- `messages/`: Tailored communication drafts for each contact.
- `outreach_manifest.json`: Machine-readable ledger of contacts, hashes, and file paths for downstream tracking.
- `delivery_plan.json`: Structured dispatch instructions enumerating per-recipient tasks, hashes, and compliance controls.
- Optional `<output>.zip` archive ready for enclave ingestion.

### Dispatch Plan Automation

The dispatch plan provides investigators and compliance teams with an actionable queue that can be ingested by downstream case-management tooling. Each task contains:

- A unique identifier for ledger correlation and acknowledgement tracking.
- The validated communication channel and target (email, phone, or secure portal) derived from the roster entry.
- Cryptographic hashes of the corresponding message file to enforce tamper-evident delivery.
- Prescribed compliance controls, including roster signature verification and ledger logging requirements.

The JSON structure is intentionally compact so it can be imported into ticketing systems or scheduling platforms without manual transcription. If the roster specifies an unsupported channel or omits the required contact details (for example, a phone dispatch without a phone number), the tool raises an error before any files are generated, preventing incomplete outreach attempts.
