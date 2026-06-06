import httpx
from app.domain.repositories import IPDFDownloader


class HTTPXPDFDownloader(IPDFDownloader):
    """Downloads files over HTTP using httpx.AsyncClient and verifies Content-Type."""
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def download(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            # Verify Content-Type header
            content_type = response.headers.get("content-type", "")
            if "application/pdf" not in content_type.lower():
                raise ValueError(f"Invalid Content-Type: {content_type}. Expected application/pdf")
                
            return response.content
