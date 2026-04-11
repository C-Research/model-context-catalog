---
icon: lucide/shield
---

# Infosec & Network

Tools for threat intelligence, network reconnaissance, and vulnerability research. Covers certificate transparency, malware analysis, IP reputation, CVE lookup, DNS enumeration, URL scanning, port scanning, and IP geolocation.

---

### `crtsh`

Search [crt.sh](https://crt.sh) certificate transparency logs for TLS certificates issued for a domain. Useful for subdomain enumeration and certificate monitoring.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `domain` | str | Yes | — | Domain name. Use `%.example.com` to include all subdomains. |

**Returns:** JSON array of certificate records with SANs, issuer, and validity dates.  
**Auth:** None.

---

### `virustotal`

Look up a file hash, URL, domain, or IP address in [VirusTotal](https://www.virustotal.com)'s multi-engine threat database. Returns detection results from 70+ antivirus engines.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `indicator` | str | Yes | — | SHA256 hash, URL, domain, or IP address. |
| `type` | str | No | `file` | One of: `file`, `url`, `domain`, `ip_address`. |

**Returns:** JSON with engine detections and threat intelligence metadata.  
**Auth:** `VIRUSTOTAL_API_KEY` — [register free](https://www.virustotal.com/gui/join-us) (4 req/min, 500 req/day).

---

### `abuseipdb`

Check an IP address against [AbuseIPDB](https://www.abuseipdb.com), a crowdsourced database of reported malicious IPs.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `ip` | str | Yes | — | IPv4 or IPv6 address. |
| `max_age_days` | int | No | `90` | Only count reports within this many days. |

**Returns:** JSON with abuse confidence score (0–100), ISP, usage type, country, and recent report count.  
**Auth:** `ABUSEIPDB_API_KEY` — [register free](https://www.abuseipdb.com/register) (1000 req/day).

---

### `nvd_cve`

Look up a CVE by ID in the [NIST National Vulnerability Database](https://nvd.nist.gov).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `cve_id` | str | Yes | — | CVE identifier, e.g. `CVE-2021-44228`. |

**Returns:** JSON with CVSS scores, description, affected products, and references.  
**Auth:** None.

---

### `malwarebazaar`

Look up a file hash in [MalwareBazaar](https://bazaar.abuse.ch) to check if it is a known malware sample.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `hash` | str | Yes | — | MD5, SHA1, or SHA256 hash. |

**Returns:** JSON with sample metadata, malware family, tags, first seen date, and file type.  
**Auth:** None.

---

### `dnsdumpster`

Discover hosts related to a domain using [DNSDumpster](https://dnsdumpster.com). Returns A, MX, NS, and TXT records alongside open port information.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `domain` | str | Yes | — | Domain name or IPv4/IPv6 address. |

**Returns:** JSON with DNS records and attack surface information.  
**Auth:** `DNSDUMPSTER_API_KEY` — [register free](https://dnsdumpster.com).

---

### `urlscan_search`

Search the [urlscan.io](https://urlscan.io) public index of existing website scans. Supports Elasticsearch-style queries.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | — | Query string, e.g. `domain:example.com`, `ip:1.2.3.4`, `hash:<sha256>`. |
| `size` | int | No | `10` | Number of results to return (max 10000). |

**Returns:** JSON with scan results including screenshot URLs, page metadata, detected technologies, certificates, and IP/ASN info.  
**Auth:** None for searching public scans.

---

### `urlscan_submit`

Submit a URL to [urlscan.io](https://urlscan.io) for scanning. The scan visits the URL in a browser and captures a screenshot, DOM, cookies, and HTTP requests.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `url` | str | Yes | — | URL to scan (include scheme, e.g. `https://example.com`). |
| `visibility` | str | No | `public` | One of: `public` (searchable by anyone), `unlisted`, `private`. |

**Returns:** JSON with scan UUID and result URL (available ~10 seconds after submission).  
**Auth:** `URLSCAN_API_KEY` — [register free](https://urlscan.io/user/signup) (100 scans/day).

---

### `geolocate`

Geolocate an IP address or domain using [ip-api.com](https://ip-api.com).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | str | No | _(current IP)_ | IPv4/IPv6 address or domain name. |
| `fields` | list | No | `[]` | Specific fields to return, e.g. `["country", "city", "isp"]`. |

**Returns:** JSON with country, region, city, ISP, ASN, and coordinates.  
**Auth:** None (45 req/min on free tier).

---

### `nmap_scan`

Scan a host, IP address, or CIDR range using [nmap](https://nmap.org). Requires `nmap` installed on the host system (`brew install nmap` / `apt install nmap`).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `target` | str | Yes | — | Host, IP, or CIDR range (e.g. `192.168.1.1`, `10.0.0.0/24`). |
| `ports` | str | No | common ports | Comma-separated list or range (e.g. `1-1024`). Use `-` for all 65535. |
| `timing` | str | No | `4` | Timing template 0–5 (0=paranoid, 3=normal, 4=aggressive, 5=insane). |
| `arguments` | str | No | `-sV` | Extra nmap flags. Use `-O` for OS detection, `-A` for all. |

**Returns:** Nmap normal text output with open ports, service names, and version info.  
**Auth:** None. OS detection (`-O`) and SYN scan (`-sS`) require root privileges.

!!! warning "Authorized use only"
    Only scan hosts you own or have explicit written permission to test.
