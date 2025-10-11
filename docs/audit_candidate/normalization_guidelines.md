# Transaction Normalization Specification

## Input Schema
Expect CSV or JSON with fields: `tx_hash`, `timestamp`, `from`, `to`, `value`, `token`, `token_symbol`, `gas`, `meta_tags`.

## Processing Steps
1. Parse `timestamp` into UTC ISO-8601 (`ts`).
2. Determine `direction` relative to subject wallet cluster (inbound/outbound/self) using ownership mapping.
3. Assign or create `counterparty_cluster_id` via clustering heuristics (multi-input, shared memo strings, exchange tag datasets).
4. Fetch historical fiat price (CAD) for `token_symbol` at `timestamp` using reliable API (e.g., Coin Metrics, Kaiko). Multiply by `value` to compute `fiat_value_at_tx`; include gas converted at same rate. Capture parallel USD/EUR conversions using BIS reference rates for world-bank comparability.
5. Evaluate `taxable_event` per CRA guidance:
   - Mark true for disposals (sales/swaps), staking rewards, airdrops, mining income.
   - Mark false for self-transfers or wallet consolidations with demonstrable common control.
6. Determine `event_type`:
   - `sale`: crypto to fiat on KYC exchange or stablecoin conversion followed by fiat exit within 48h (track via heuristic linking stablecoin tx to exchange withdrawal).
   - `swap`: token-to-token DEX trades without fiat exit.
   - `transfer`: non-taxable movement between controlled wallets.
   - `mining`, `airdrop`, `staking_reward`, `other` as applicable.
7. Populate `reason` with concise justification referencing heuristics, e.g., "Outbound to Binance hot wallet; fiat ramp per subpoena response".
8. Flag suspicious behavior by attaching `meta_tags` such as `suspicious_flow` when interacting with mixers, cross-chain bridges, or >3 hop rapid transfers within 6 hours, and annotate counterparties under multilateral sanctions regimes.
9. Correlate custodial recovery events by recording ticket IDs, reset timestamps, or MFA challenge references when on-chain movement aligns with account recovery activity; include references to world-bank systemic risk alerts when applicable.

## Output Record Template
```
{
  "id": "<tx_hash>",
  "ts": "<ISO timestamp>",
  "direction": "inbound|outbound|self",
  "counterparty_cluster_id": "<cluster id or null>",
  "fiat_value_at_tx": <numeric CAD>,
  "taxable_event": true|false,
  "event_type": "sale|swap|transfer|mining|airdrop|staking_reward|other",
  "reason": "<short rationale>",
  "meta": {
    "suspicious_flow": true|false,
    "source_references": ["<explorer_url>", "<price_api_reference>"],
    "authorization_reference": "<legal_order_id>",
    "multilateral_case_id": "<world_bank_bis_case_id>",
    "kyc_match_status": "match|mismatch|pending",
    "recovery_event_id": "<ticket_or_reset_id>",
    "zero_trust_session_id": "<workstation_log_id>"
  }
}
```

## Aggregated Dashboard Metrics
- `total_inflows`: Sum of fiat values for inbound events.
- `total_outflows`: Sum of fiat values for outbound events.
- `realized_gains_estimate`: Sum over taxable disposals of (proceeds - adjusted cost base), with supplemental USD/EUR tallies for central bank stress testing.
- `suspicious_tx_count`: Count of transactions flagged with `suspicious_flow` true.
- Provide breakdowns by token, settlement layer, and fiscal year.
- Provide cross-currency summaries aligned to BIS/World Bank systemic dashboards (CAD/USD/EUR equivalents).
- Summarize IP/device correlation findings (e.g., number of events with mismatched KYC metadata).
- Track `recovery_event_count`: Transactions associated with password/MFA reset activity or custodial recovery tickets.

## Evidence Notes
- Store normalization scripts with version control tags.
- Log API sources, response hashes, and rate-limit considerations.
- Include reproducibility manifest detailing software versions and configuration.
- Reference legal authorization IDs tied to each dataset and confirm that inputs were obtained without attempting unauthorized key reconstruction or wallet intrusion; include world-bank/BIS data-sharing approval identifiers when shared across borders.
- Record investigator attestation dates acknowledging compliance with recovery constraints.
- Archive zero-trust monitoring artifacts that underpin `zero_trust_session_id` references and capture BIS enclave session attestations when applicable.
