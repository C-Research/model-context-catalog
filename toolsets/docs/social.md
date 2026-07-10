---
icon: lucide/message-circle
---

# Social Data

Tools for searching X posts, users, timelines, and trends through [Xquik](https://xquik.com).

Set `XQUIK_API_KEY` in `toolsets/osint/osint.env` before using these tools.

---

### `xquik_tweet_search`

Search X posts by query, Tweet ID, X status URL, or account date-window query.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | - | Search query. |
| `query_type` | str | No | `Latest` | Sort order: `Latest` or `Top`. |
| `limit` | int | No | `20` | Maximum tweets to return, up to 200. |
| `cursor` | str | No | - | Pagination cursor from a previous response. |

**Returns:** JSON with tweets, author metadata, engagement metrics, and pagination cursors.

??? example "Usage example"
    ```
    xquik_tweet_search(q="model context protocol", query_type="Latest", limit=20)
    ```

### `xquik_user_search`

Search X users by name or username.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `q` | str | Yes | - | User search query. |
| `cursor` | str | No | - | Pagination cursor from a previous response. |

**Returns:** JSON with matching users and pagination cursors.

??? example "Usage example"
    ```
    xquik_user_search(q="open source intelligence")
    ```

### `xquik_user_tweets`

List recent X posts from a user by user ID or username.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `user_id` | str | Yes | - | X user ID or username. |
| `include_replies` | bool | No | `false` | Include reply tweets. |
| `include_parent_tweet` | bool | No | `false` | Include parent tweet data for replies when available. |
| `cursor` | str | No | - | Pagination cursor from a previous response. |

**Returns:** JSON with tweets, author metadata, engagement metrics, and pagination cursors.

??? example "Usage example"
    ```
    xquik_user_tweets(user_id="xquik", include_replies=false)
    ```

### `xquik_trends`

Fetch X trending topics by region.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `woeid` | int | No | `1` | Region WOEID, for example `1` worldwide or `23424977` US. |
| `count` | int | No | `30` | Number of trends to return, from 1 to 50. |

**Returns:** JSON with trend names, descriptions, encoded queries, and ranks.

??? example "Usage example"
    ```
    xquik_trends(woeid=1, count=30)
    ```
