import httpx

UAS = {
    True: "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-User/1.0; +Claude-User@anthropic.com)",
    False: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
}


async def request(
    method: str,
    url: str,
    params: dict = None,
    headers: dict = None,
    json: dict = None,
    content: str = None,
    responsible: bool = True,
) -> dict:
    """
    Performs an HTTP request using httpx.request and given parameters

    If responsible is True, it uses the Claude agent string otherwise uses a Chrome browser
    """
    async with httpx.AsyncClient() as client:
        if headers is None:
            headers = {}
        headers["User-Agent"] = UAS[responsible]
        response = await client.request(
            method, url, params=params, headers=headers, json=json, content=content
        )
        content = (
            response.json()
            if "application/json" in response.headers.get("content-type", "")
            else response.text
        )
        return {
            "status": response.status_code,
            "headers": dict(response.headers),
            "content": content,
        }
