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

??? example "Usage examples"
    Fetch a Bitcoin transaction by hash:
    ```
    blockchain_rawtx(tx_hash="4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b")
    ```

---

### `blockchain_rawblock`

Fetch raw Bitcoin block data from [Blockchain.info](https://blockchain.info) by block hash or height.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `block_hash` | str | Yes | — | Bitcoin block hash or block height number. |

**Returns:** JSON with block header, transaction list, timestamp, difficulty, and miner info.  
**Auth:** None.

??? example "Usage examples"
    Fetch the Bitcoin genesis block:
    ```
    blockchain_rawblock(block_hash="000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f")
    ```

    Fetch a block by height:
    ```
    blockchain_rawblock(block_hash="700000")
    ```

---

### `blockchain_rawaddr`

Fetch Bitcoin address summary and transaction history from [Blockchain.info](https://blockchain.info).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `bitcoin_address` | str | Yes | — | Bitcoin address in base58 or bech32 format. |

**Returns:** JSON with total received, total sent, current balance, and transaction history.  
**Auth:** None.

??? example "Usage examples"
    Fetch transaction history for a Bitcoin address:
    ```
    blockchain_rawaddr(bitcoin_address="1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf")
    ```

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

??? example "Usage examples"
    Look up an Ethereum wallet address:
    ```
    blockchair(chain="ethereum", query="0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
    ```

    Look up a Bitcoin address:
    ```
    blockchair(chain="bitcoin", query="1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf")
    ```

    Trace a Solana transaction:
    ```
    blockchair(chain="solana", query="5UfgJ5vVZxUxefDGqzqkVLHzHxVTyYH9StYyHKpbdXsT")
    ```
