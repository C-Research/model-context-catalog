## ADDED Requirements

### Requirement: Hacker News search
The system SHALL provide a `hn_search` tool in `osint/news.yaml` (group: `news`) that queries the Algolia HN Search API and returns matching posts and comments. No API key required.

#### Scenario: Search by keyword
- **WHEN** `hn_search` is called with `q="vector database"`
- **THEN** the tool returns a JSON response from `http://hn.algolia.com/api/v1/search` containing matching HN items

#### Scenario: Search with type filter
- **WHEN** `hn_search` is called with `q="rust"` and `tags="story"`
- **THEN** only story-type results are returned

### Requirement: Hacker News item lookup
The system SHALL provide an `hn_item` tool in `osint/news.yaml` (group: `news`) that fetches a single HN item (story, comment, job, poll) by its integer ID from the Firebase API. No API key required.

#### Scenario: Fetch a story by ID
- **WHEN** `hn_item` is called with `item_id=1`
- **THEN** the tool returns the JSON object for that HN item from `https://hacker-news.firebaseio.com/v0/item/1.json`
