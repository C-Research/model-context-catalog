## Requirements

### Requirement: Blockchain.info raw transaction/block/address lookup (moved from search.yaml)
The system SHALL provide `blockchain_rawtx`, `blockchain_rawblock`, and `blockchain_rawaddr` tools in `osint/crypto.yaml` (group: `crypto`). These tools are moved from `osint/search.yaml` with no functional changes — they query Blockchain.info for Bitcoin transaction, block, and address data.

#### Scenario: Look up a transaction by hash
- **WHEN** `blockchain_rawtx` is called with `tx_hash="<hash>"`
- **THEN** the tool returns raw transaction JSON from `https://blockchain.info/rawtx/<hash>`

#### Scenario: Look up an address
- **WHEN** `blockchain_rawaddr` is called with `bitcoin_address="<address>"`
- **THEN** the tool returns address history and balance JSON from `https://blockchain.info/rawaddr/<address>`

### Requirement: Blockchair multi-chain lookup
The system SHALL provide a `blockchair` tool in `osint/crypto.yaml` (group: `crypto`) that queries the Blockchair API for transaction or address data across multiple blockchains. No API key required for basic lookups.

#### Scenario: Look up a Bitcoin transaction
- **WHEN** `blockchair` is called with `chain="bitcoin"` and `query="<tx_hash>"`
- **THEN** the tool returns JSON from `https://api.blockchair.com/bitcoin/dashboards/transaction/<tx_hash>`

#### Scenario: Look up an Ethereum address
- **WHEN** `blockchair` is called with `chain="ethereum"` and `query="<address>"`
- **THEN** the tool returns JSON from `https://api.blockchair.com/ethereum/dashboards/address/<address>`

#### Scenario: Supported chains
- **WHEN** `blockchair` is called with an unsupported chain value
- **THEN** the Blockchair API returns an error response (no client-side validation required)
