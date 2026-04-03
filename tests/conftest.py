import os

os.environ.setdefault("MCC_GITHUB_CLIENT_ID", "test-client-id")
os.environ.setdefault("MCC_GITHUB_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("MCC_BASE_URL", "http://localhost:8000")
os.environ.setdefault("MCC_USERS_DB", "tests/users.db")
