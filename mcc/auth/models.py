from typing import Optional

from pydantic import BaseModel


class UserModel(BaseModel):
    username: str
    email: Optional[str] = None
    groups: list[str] = []
    tools: list[str] = []
