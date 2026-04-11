## Requirements

### Requirement: arXiv paper search
The system SHALL provide an `arxiv_search` tool in `osint/academic.yaml` (group: `academic`) that queries the arXiv API and returns matching preprints. No API key required.

#### Scenario: Search by keyword
- **WHEN** `arxiv_search` is called with `query="diffusion models"`
- **THEN** the tool returns an Atom feed response from `http://export.arxiv.org/api/query` with matching papers

#### Scenario: Limit result count
- **WHEN** `arxiv_search` is called with `query="llm"` and `max_results=5`
- **THEN** at most 5 results are returned

### Requirement: CrossRef DOI and article search
The system SHALL provide a `crossref_search` tool in `osint/academic.yaml` (group: `academic`) that queries the CrossRef REST API for journal articles, books, and conference papers by keyword. No API key required.

#### Scenario: Search by title keyword
- **WHEN** `crossref_search` is called with `query="attention is all you need"`
- **THEN** the tool returns a JSON response from `https://api.crossref.org/works` with matching works

### Requirement: Semantic Scholar paper search
The system SHALL provide a `semantic_scholar_search` tool in `osint/academic.yaml` (group: `academic`) that queries the Semantic Scholar Graph API for academic papers. No API key required for basic access.

#### Scenario: Search for papers by keyword
- **WHEN** `semantic_scholar_search` is called with `query="reinforcement learning from human feedback"`
- **THEN** the tool returns a JSON response from `https://api.semanticscholar.org/graph/v1/paper/search` with matching papers and metadata

### Requirement: OpenAlex works search
The system SHALL provide an `openalex_search` tool in `osint/academic.yaml` (group: `academic`) that queries the OpenAlex API for scholarly works. No API key required.

#### Scenario: Search by keyword
- **WHEN** `openalex_search` is called with `query="CRISPR gene editing"`
- **THEN** the tool returns a JSON response from `https://api.openalex.org/works` with matching works including citation counts and open access status
