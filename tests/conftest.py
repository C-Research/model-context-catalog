import os

os.environ.setdefault("MCC_GITHUB_CLIENT_ID", "test-client-id")
os.environ.setdefault("MCC_GITHUB_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("MCC_BASE_URL", "http://localhost:8000")
os.environ["MCC_AUTH"] = "dangerous"

_base_user_index = os.environ.get("MCC_ELASTICSEARCH__USER_INDEX", "mcc-users")
os.environ["MCC_ELASTICSEARCH__USER_INDEX"] = f"{_base_user_index}-test"
_base_tool_index = os.environ.get("MCC_ELASTICSEARCH__TOOL_INDEX", "mcc-tools")
os.environ["MCC_ELASTICSEARCH__TOOL_INDEX"] = f"{_base_tool_index}-test"
