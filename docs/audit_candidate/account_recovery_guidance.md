# Crypto Account Recovery Guidance

This document outlines compliant steps for investigating and documenting lost-access cryptocurrency accounts while respecting security and privacy obligations.

The guidance now reflects requirements from a **multilateral central bank/World Bank task force**, ensuring recovery workbooks can be executed by cross-border prudential supervisors collaborating under Basel Committee, FATF, and IMF information-sharing compacts. Steps that involve domestic-only processes now include an international counterpart to support coordinated enforcement actions.

## 1. Scope and Constraints
- **No circumvention**: Do not attempt to bypass wallet security mechanisms or brute-force seed phrases. Such actions are likely unlawful and violate professional ethics.
- **Legal mandate**: Ensure there is statutory authority (court order, subpoena, or client consent) before taking investigative action.
- **Data protection**: Handle personal data in accordance with jurisdictional privacy requirements (e.g., PIPEDA in Canada, GDPR in the EU) and multilateral information-sharing safeguards (e.g., BIS Central Bank Data Protection Charter, IMF safeguards policy).

## 2. Immediate Actions
1. **Validate authority**
   - Confirm statutory power (court order, subpoena, treaty-based request, or explicit written consent) before requesting third-party assistance.
   - Record legal references and authorization identifiers in the audit diary.
   - When operating under a multilateral mandate, register the case with the designated central bank coordination hub (e.g., BIS Innovation Hub secure case manager) and obtain a joint case identifier.
2. **Gather documentation**
   - Government-issued identification of the claimant.
   - Proof of wallet ownership (transaction history, device serials, exchange receipts).
   - Incident timeline (when access was lost, prior custodians, suspected compromise details).
3. **Contact custodial services**
   - If funds were held with a centralized exchange, initiate the exchange’s official recovery process.
   - Request account locks to prevent further movement while identity is verified.
   - Where multi-signature or managed custody is involved, coordinate with all cosigners per governing agreements.
   - Notify the World Bank Financial Sector Integrity team and relevant regional development banks when custodial entities fall within their supervisory perimeter to prevent duplicate recovery orders and align systemic risk monitoring.
4. **Preserve evidence**
   - Capture blockchain snapshots of relevant addresses.
   - Hash and archive all supplied documents and communications.
   - Store forensic images of affected devices when available, observing digital evidence handling standards.

## 3. Identity Assurance and Network Attribution
- **Government ID validation**: Require high-resolution scans or in-person notarized copies of passports, driver’s licenses, or provincial ID cards. Cross-check document numbers against issuing authority databases where permitted and log confirmations in the multilateral KYC registry before sharing with partner central banks.
- **IP address correlation**: Request historical login IPs from exchanges and custodians; compare against claimant-provided IP history or ISP billing records. Note geolocation discrepancies that may signal compromise.
- **Device provenance**: Collect device serial numbers, MAC addresses, secure element identifiers, and firmware versions from hardware wallets or authenticating devices. Confirm alignment with metadata disclosed by custodians.
- **Behavioral analytics**: Compare claimant-stated usage patterns (time-of-day, device fingerprints, geolocation) with custodian telemetry; escalate mismatches to counsel before progressing.
- **Multi-factor proof**: Require recovery sign-offs via previously enrolled MFA channels (e.g., authenticator apps, recovery emails) and document successful challenge responses or fallback method usage.
- **Third-party attestations**: Obtain sworn statements from employers, business partners, fiduciaries, or correspondent banks confirming operational control in multi-signature or corporate wallet contexts.
- **Documentation trail**: Log each verification artifact, reviewer, validation outcome, and cross-reference to legal authority identifiers in the audit diary to satisfy evidentiary standards.

## 4. Zero-Trust Recovery Operations
- **Segregate workspaces**: Conduct recovery efforts from hardened investigation environments with logging enabled; disallow personal accounts or unmanaged devices. For world-bank-led engagements, operate within the shared zero-trust enclave maintained under BIS Innovation Hub standards and record enclave session IDs in the audit log.
- **Role-based access**: Grant least-privilege access to recovery case files and custodial portals; require dual-authorization for sensitive submissions (e.g., exchange account unlock requests) and document approvals in the multilateral supervisory case manager.
- **Continuous monitoring**: Capture screen recordings, network telemetry, and command logs during recovery tasks to demonstrat
e procedural integrity.
- **Key material handling**: When custodians issue temporary credentials or reset links, store them in sealed evidence containe
rs; document every interaction, expiration, and destruction event.
- **Incident response triggers**: Define criteria for halting recovery (e.g., detection of active compromise indicators, legal a
uthority ambiguities) and escalate to counsel before resumption.

## 5. Cooperative Recovery Channels
- **Centralized exchanges**: Submit notarized affidavits and KYC packets through compliance desks. Require acknowledgement of freeze/lock status and ticket numbers for traceability. When exchanges operate under non-domestic prudential regimes, route requests through the relevant central bank supervisory college or World Bank Financial Sector Integrity liaison to leverage supervisory memoranda of understanding.
- **Hardware/software wallet vendors**: Engage support for logs, firmware guidance, or warranty records. Vendors cannot restore seed phrases but may confirm device usage patterns or assist with firmware integrity checks.
- **Institutional custodians**: Where third-party custodians hold partial keys, follow contractual recovery procedures and ensure multi-party approvals are recorded. Engage global custodian oversight forums (e.g., CPMI-IOSCO) if custodians are systemically important to coordinate supervisory responses.
- **Law enforcement liaison**: If criminal activity is suspected, coordinate with cybercrime units; provide investigative briefs and warrants as required. Notify partner jurisdictions via Egmont Secure Web, INTERPOL, and World Bank integrity networks when cross-border enforcement is anticipated.

## 6. Investigative Analytics
- Map on-chain flows from the claimant’s addresses to identify custodial endpoints.
- Use clustering heuristics to associate related addresses; document confidence levels and methodologies.
- Monitor outbound transfers for mixers, privacy-enhancing tools, or off-ramps that signal third-party custody.
- Record any indications that keys may have been compromised (e.g., sudden change in spending patterns) to inform potential criminal complaints.
- Correlate recovery ticket activity, MFA resets, and zero-trust logs with on-chain value shifts to validate or refute compromise narratives.

## 7. Communication Templates
- Prepare standardized questionnaires for exchanges and wallet providers, focusing on ownership proof, access logs, and recovery eligibility. Include annexes that satisfy FATF Recommendation 40 typologies and World Bank integrity due-diligence fields to streamline mutual legal assistance.
- Maintain audit trails of requests, responses, and authorization letters.
- Document responses declining assistance and the legal rationale cited to support potential follow-up orders, referencing applicable treaties (e.g., UN Convention Against Corruption, OECD Multilateral Convention) when escalation to world-bank partners or MLAT channels is contemplated.

## 8. Escalation and Resolution
- If ownership is corroborated, facilitate the subject’s engagement with custodial services to regain access through official recovery channels.
- Coordinate with the world-bank supervisory task force to ensure recovered funds tied to systemic risk indicators are routed to macroprudential monitoring dashboards and, if required, temporary holding arrangements consistent with international sanctions regimes.
- When on-chain assets remain in self-custody wallets, advise on civil remedies (e.g., court orders compelling assistance from involved parties).
- Document final outcomes, including unsuccessful recovery attempts, to support future legal or regulatory actions. File summary outcomes with the multilateral supervisory college to enrich typology libraries and inform future cooperative audits.

## 9. Compliance Checklist
- [ ] Authority validated (warrant, subpoena, treaty request, or written consent)
- [ ] Identity verified against trusted sources
- [ ] Evidence preserved with hashes and timestamps
- [ ] Requests logged with unique identifiers
- [ ] Responses reviewed by legal/compliance counsel
- [ ] Unauthorized key reconstruction attempts expressly ruled out and documented
- [ ] Zero-trust logging reviewed and archived, including network telemetry and access approvals, plus BIS enclave session IDs when applicable
- [ ] Recovery ticket, MFA reset, and transaction correlations independently reviewed and signed off
- [ ] Final report issued to the requesting agency or client

Adhering to these steps ensures investigative rigor while honoring legal and ethical boundaries.
