# Transaction Normalization Specification

## Input Schema
Expect CSV or JSON with fields: `tx_hash`, `timestamp`, `from`, `to`, `value`, `token`, `token_symbol`, `gas`, `meta_tags`.

## Processing Steps
1. Parse `timestamp` into UTC ISO-8601 (`ts`).
2. Determine `direction` relative to subject wallet cluster (inbound/outbound/self) using ownership mapping.
3. Assign or create `counterparty_cluster_id` via clustering heuristics (multi-input, shared memo strings, exchange tag datasets).
4. Fetch historical fiat price (CAD) for `token_symbol` at `timestamp` using reliable API (e.g., Coin Metrics, Kaiko). Multiply by `value` to compute `fiat_value_at_tx`; include gas converted at same rate.
5. Evaluate `taxable_event` per CRA guidance:
   - Mark true for disposals (sales/swaps), staking rewards, airdrops, mining income.
   - Mark false for self-transfers or wallet consolidations with demonstrable common control.
6. Determine `event_type`:
   - `sale`: crypto to fiat on KYC exchange or stablecoin conversion followed by fiat exit within 48h (track via heuristic linking stablecoin tx to exchange withdrawal).
   - `swap`: token-to-token DEX trades without fiat exit.
   - `transfer`: non-taxable movement between controlled wallets.
   - `mining`, `airdrop`, `staking_reward`, `other` as applicable.
7. Populate `reason` with concise justification referencing heuristics, e.g., "Outbound to Binance hot wallet; fiat ramp per subpoena response".
8. Flag suspicious behavior by attaching `meta_tags` such as `suspicious_flow` when interacting with mixers, cross-chain bridges, or >3 hop rapid transfers within 6 hours.

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
    "kyc_match_status": "match|mismatch|pending"
  }
}
```

## Aggregated Dashboard Metrics
- `total_inflows`: Sum of fiat values for inbound events.
- `total_outflows`: Sum of fiat values for outbound events.
- `realized_gains_estimate`: Sum over taxable disposals of (proceeds - adjusted cost base).
- `suspicious_tx_count`: Count of transactions flagged with `suspicious_flow` true.
- Provide breakdowns by token, settlement layer, and fiscal year.
- Summarize IP/device correlation findings (e.g., number of events with mismatched KYC metadata).

## Evidence Notes
- Store normalization scripts with version control tags.
- Log API sources, response hashes, and rate-limit considerations.
- Include reproducibility manifest detailing software versions and configuration.
- Reference legal authorization IDs tied to each dataset and confirm that inputs were obtained without attempting unauthorized key reconstruction or wallet intrusion.
- Record investigator attestation dates acknowledging compliance with recovery constraints.
