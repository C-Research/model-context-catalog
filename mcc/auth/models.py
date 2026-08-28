
from pydantic import BaseModel


class UserModel(BaseModel):
    username: str
    email: str | None = None
    groups: list[str] = []
    tools: list[str] = []
    # Populated by list_users()'s batch enrichment ({"prefix", "created_at",
    # "expires_at"}) or, per-request, by get_current_user()/get_user_by_key()
    # when the caller authenticated via an API key ({"prefix"} only) — never
    # the hash or raw key. Never persisted — every write site (create_user,
    # _update_user) excludes it explicitly so a stale key snapshot never
    # round-trips into the users index.
    key: dict | None = None
