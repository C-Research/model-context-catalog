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

??? example "Usage examples"
    Find all subdomains of a domain:
    ```
    crtsh(domain="%.example.com")
    ```

    Look up certificates issued for a specific host:
    ```
    crtsh(domain="mail.example.com")
    ```

---

### `virustotal`

Look up a file hash, URL, domain, or IP address in [VirusTotal](https://www.virustotal.com)'s multi-engine threat database. Returns detection results from 70+ antivirus engines.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `indicator` | str | Yes | — | SHA256 hash, URL, domain, or IP address. |
| `type` | str | No | `file` | One of: `file`, `url`, `domain`, `ip_address`. |

**Returns:** JSON with engine detections and threat intelligence metadata.  
**Auth:** `VIRUSTOTAL_API_KEY` — [register free](https://www.virustotal.com/gui/join-us) (4 req/min, 500 req/day).

??? example "Usage examples"
    Check a file hash against 70+ AV engines:
    ```
    virustotal(indicator="275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f", type="file")
    ```

    Look up a suspicious domain:
    ```
    virustotal(indicator="malware-staging.example.com", type="domain")
    ```

    Check an IP address for malicious activity:
    ```
    virustotal(indicator="185.220.101.45", type="ip_address")
    ```

---

### `abuseipdb`

Check an IP address against [AbuseIPDB](https://www.abuseipdb.com), a crowdsourced database of reported malicious IPs.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `ip` | str | Yes | — | IPv4 or IPv6 address. |
| `max_age_days` | int | No | `90` | Only count reports within this many days. |

**Returns:** JSON with abuse confidence score (0–100), ISP, usage type, country, and recent report count.  
**Auth:** `ABUSEIPDB_API_KEY` — [register free](https://www.abuseipdb.com/register) (1000 req/day).

??? example "Usage examples"
    Check an IP's abuse history:
    ```
    abuseipdb(ip="185.220.101.45")
    ```

    Restrict to reports from the last 7 days:
    ```
    abuseipdb(ip="185.220.101.45", max_age_days=7)
    ```

---

### `nvd_cve`

Look up a CVE by ID in the [NIST National Vulnerability Database](https://nvd.nist.gov).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `cve_id` | str | Yes | — | CVE identifier, e.g. `CVE-2021-44228`. |

**Returns:** JSON with CVSS scores, description, affected products, and references.  
**Auth:** None.

??? example "Usage examples"
    Look up Log4Shell:
    ```
    nvd_cve(cve_id="CVE-2021-44228")
    ```

    Look up the HTTP/2 Rapid Reset vulnerability:
    ```
    nvd_cve(cve_id="CVE-2023-44487")
    ```

---

### `malwarebazaar`

Look up a file hash in [MalwareBazaar](https://bazaar.abuse.ch) to check if it is a known malware sample.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `hash` | str | Yes | — | MD5, SHA1, or SHA256 hash. |

**Returns:** JSON with sample metadata, malware family, tags, first seen date, and file type.  
**Auth:** None.

??? example "Usage examples"
    Check a SHA256 hash:
    ```
    malwarebazaar(hash="275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f")
    ```

    Check an MD5 hash:
    ```
    malwarebazaar(hash="44d88612fea8a8f36de82e1278abb02f")
    ```

---

### `dnsdumpster`

Discover hosts related to a domain using [DNSDumpster](https://dnsdumpster.com). Returns A, MX, NS, and TXT records alongside open port information.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `domain` | str | Yes | — | Domain name or IPv4/IPv6 address. |

**Returns:** JSON with DNS records and attack surface information.  
**Auth:** `DNSDUMPSTER_API_KEY` — [register free](https://dnsdumpster.com).

??? example "Usage examples"
    Enumerate DNS records and attack surface for a domain:
    ```
    dnsdumpster(domain="example.com")
    ```

    Look up DNS info for an IP address:
    ```
    dnsdumpster(domain="192.0.2.1")
    ```

---

### `urlscan_search`

Search the [urlscan.io](https://urlscan.io) public index of existing website scans. Supports Elasticsearch-style queries.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | — | Query string, e.g. `domain:example.com`, `ip:1.2.3.4`, `hash:<sha256>`. |
| `size` | int | No | `10` | Number of results to return (max 10000). |

**Returns:** JSON with scan results including screenshot URLs, page metadata, detected technologies, certificates, and IP/ASN info.  
**Auth:** None for searching public scans.

??? example "Usage examples"
    Find all scans for a domain:
    ```
    urlscan_search(q="domain:suspicious-site.com")
    ```

    Find scans originating from a specific IP:
    ```
    urlscan_search(q="ip:185.220.101.45", size=20)
    ```

    Search by page hash:
    ```
    urlscan_search(q="hash:abc123def456")
    ```

---

### `urlscan_submit`

Submit a URL to [urlscan.io](https://urlscan.io) for scanning. The scan visits the URL in a browser and captures a screenshot, DOM, cookies, and HTTP requests.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `url` | str | Yes | — | URL to scan (include scheme, e.g. `https://example.com`). |
| `visibility` | str | No | `public` | One of: `public` (searchable by anyone), `unlisted`, `private`. |

**Returns:** JSON with scan UUID and result URL (available ~10 seconds after submission).  
**Auth:** `URLSCAN_API_KEY` — [register free](https://urlscan.io/user/signup) (100 scans/day).

??? example "Usage examples"
    Submit a suspicious URL for public scanning:
    ```
    urlscan_submit(url="https://suspicious-phishing-site.example.com")
    ```

    Submit a URL as unlisted (not publicly searchable):
    ```
    urlscan_submit(url="https://internal-test.example.com", visibility="unlisted")
    ```

---

### `geolocate`

Geolocate an IP address or domain using [ip-api.com](https://ip-api.com).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | str | No | _(current IP)_ | IPv4/IPv6 address or domain name. |
| `fields` | list | No | `[]` | Specific fields to return, e.g. `["country", "city", "isp"]`. |

**Returns:** JSON with country, region, city, ISP, ASN, and coordinates.  
**Auth:** None (45 req/min on free tier).

??? example "Usage examples"
    Geolocate an IP address:
    ```
    geolocate(query="8.8.8.8")
    ```

    Return only specific fields:
    ```
    geolocate(query="185.220.101.45", fields=["country", "city", "isp", "org"])
    ```

    Geolocate the server's own outbound IP:
    ```
    geolocate()
    ```

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

??? example "Usage examples"
    Scan common ports on a single host:
    ```
    nmap_scan(target="192.168.1.1")
    ```

    Scan specific ports across a subnet:
    ```
    nmap_scan(target="10.0.0.0/24", ports="22,80,443,8080")
    ```

    Service and OS detection:
    ```
    nmap_scan(target="example.com", arguments="-sV -O")
    ```

!!! warning "Authorized use only"
    Only scan hosts you own or have explicit written permission to test.
