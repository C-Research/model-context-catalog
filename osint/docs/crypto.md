---
icon: lucide/coins
---

# Cryptocurrency & Blockchain

Tools for querying Bitcoin and multi-chain blockchain data — transactions, blocks, and wallet addresses. Useful for tracing fund flows, investigating ransomware payments, and sanctions research.

All tools are free with no API key required.

---

### `blockchain_rawtx`

Fetch raw Bitcoin transaction data from [Blockchain.info](https://blockchain.info) by transaction hash.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `tx_hash` | str | Yes | — | Bitcoin transaction hash (txid). |

**Returns:** JSON with inputs, outputs, value, fee, block height, and confirmation count.  
**Auth:** None.

---

### `blockchain_rawblock`

Fetch raw Bitcoin block data from [Blockchain.info](https://blockchain.info) by block hash or height.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `block_hash` | str | Yes | — | Bitcoin block hash or block height number. |

**Returns:** JSON with block header, transaction list, timestamp, difficulty, and miner info.  
**Auth:** None.

---

### `blockchain_rawaddr`

Fetch Bitcoin address summary and transaction history from [Blockchain.info](https://blockchain.info).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `bitcoin_address` | str | Yes | — | Bitcoin address in base58 or bech32 format. |

**Returns:** JSON with total received, total sent, current balance, and transaction history.  
**Auth:** None.

---

### `blockchair`

Look up a transaction or address across 15+ blockchains via the [Blockchair](https://blockchair.com) API. Automatically detects whether the query is a transaction (64-char hex) or address.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `chain` | str | Yes | — | Blockchain to query. See supported chains below. |
| `query` | str | Yes | — | Transaction hash (64 hex chars) or wallet address. |

**Supported chains:** `bitcoin`, `ethereum`, `litecoin`, `bitcoin-cash`, `dogecoin`, `dash`, `zcash`, `bitcoin-sv`, `monero`, `ripple`, `stellar`, `cardano`, `polkadot`, `solana`, `tron`.

**Returns:** JSON with transaction or address details for the specified chain.  
**Auth:** None (1800 req/hour).
