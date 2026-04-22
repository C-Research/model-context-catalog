---
icon: lucide/newspaper
---

# News & Media

Tools for searching technology news and community discussions. See also [Conflict & Humanitarian](conflict.md) for GDELT global news coverage and [Academic Research](academic.md) for arXiv preprints.

---

### `hn_search`

Search [Hacker News](https://news.ycombinator.com) posts, comments, jobs, and polls via the [Algolia HN Search API](https://hn.algolia.com/api).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | — | Search query string. |
| `tags` | str | No | _(all)_ | Filter by type: `story`, `comment`, `job`, `poll`, `show_hn`, `ask_hn`. |

**Returns:** JSON with matching items — titles, authors, scores, comment counts, and URLs.  
**Auth:** None.

??? example "Usage examples"
    Search for stories mentioning a technology:
    ```
    hn_search(q="model context protocol")
    ```

    Find Show HN posts about a topic:
    ```
    hn_search(q="open source", tags="show_hn")
    ```

    Search comments only:
    ```
    hn_search(q="FastMCP", tags="comment")
    ```

---

### `hn_item`

Fetch a single Hacker News item by its integer ID from the [official Firebase API](https://github.com/HackerNews/API).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `item_id` | int | Yes | — | Integer ID of the HN item (story, comment, job, or poll). |

**Returns:** Raw item JSON with title, text, score, author, creation time, and child IDs.  
**Auth:** None.

??? example "Usage examples"
    Fetch a specific story by ID:
    ```
    hn_item(item_id=36517058)
    ```

    Fetch the first-ever HN submission:
    ```
    hn_item(item_id=1)
    ```
