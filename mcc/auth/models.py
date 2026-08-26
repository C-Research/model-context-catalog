
from pydantic import BaseModel


class UserModel(BaseModel):
    username: str
    email: str | None = None
    groups: list[str] = []
    tools: list[str] = []
    # Populated only by list_users() (never the hash/raw key, just
    # {"prefix", "created_at", "expires_at"}), and never persisted — every
    # write site (create_user, _update_user) excludes it explicitly so a
    # stale key snapshot never round-trips into the users index.
    key: dict | None = None
