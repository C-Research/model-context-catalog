---
icon: lucide/book-open
---

# Academic Research

Tools for searching scholarly literature across preprints, journal articles, and citation graphs. All sources are free and openly accessible — no API keys required.

---

### `arxiv_search`

Search [arXiv](https://arxiv.org) preprints across physics, computer science, mathematics, quantitative biology, statistics, and more.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | str | Yes | — | Search query. Supports field prefixes: `ti:` (title), `au:` (author), `abs:` (abstract). |
| `max_results` | int | No | `10` | Maximum results (max 2000). |

**Returns:** Atom XML feed with paper titles, authors, abstracts, submission dates, and PDF links.  
**Auth:** None.

??? example "Query examples"
    - `ti:transformer attention` — papers with both words in the title
    - `au:Hinton` — papers by authors named Hinton
    - `abs:large language model` — papers mentioning LLMs in the abstract

---

### `crossref_search`

Search the [CrossRef](https://www.crossref.org) database of journal articles, books, conference papers, and other scholarly works.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | str | Yes | — | Keyword search query. |
| `rows` | int | No | `10` | Number of results to return. |

**Returns:** JSON with DOIs, titles, authors, publication dates, publisher, and citation counts.  
**Auth:** None.

---

### `semantic_scholar_search`

Search the [Semantic Scholar](https://www.semanticscholar.org) academic graph by keyword.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | str | Yes | — | Search query string. |
| `limit` | int | No | `10` | Results to return (max 100). |

**Returns:** JSON with titles, authors, year, abstract, citation counts, and open-access PDF links.  
**Auth:** None for basic access (rate limits apply).

---

### `openalex_search`

Search [OpenAlex](https://openalex.org), a fully open catalog of 250M+ scholarly works, authors, institutions, and concepts.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | str | Yes | — | Search query string. |
| `per_page` | int | No | `10` | Results per page (max 200). |

**Returns:** JSON with titles, authors, year, citation counts, open access status, and concept tags.  
**Auth:** None.
