from pydantic import BaseModel


class UserModel(BaseModel):
    username: str
    email: str | None = None
    groups: list[str] = []
    tools: list[str] = []
