from fastmcp.server.auth.providers.github import GitHubProvider

from mcc.settings import settings


def get_provider() -> GitHubProvider:
    missing = [
        k
        for k, v in {
            "github.client_id": settings.github_oauth.client_id,
            "github.client_secret": settings.github_oauth.client_secret,
            "github.base_url": settings.github_oauth.base_url,
        }.items()
        if not v
    ]
    if missing:
        raise RuntimeError(f"Missing required settings: {', '.join(missing)}")
    return GitHubProvider(
        client_id=settings.github.client_id,
        client_secret=settings.github.client_secret,
        base_url=settings.github.base_url,
        required_scopes=["read:user", "user:email"],
    )
