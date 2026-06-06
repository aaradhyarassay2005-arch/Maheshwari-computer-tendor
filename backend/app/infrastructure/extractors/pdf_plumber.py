import pdfplumber
import asyncio
from app.domain.repositories import IPDFExtractor


class PDFPlumberExtractor(IPDFExtractor):
    """Primary PDF text extractor strategy using pdfplumber."""
    def _sync_extract(self, file_path: str) -> str:
        text_pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages[:5]:
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)
        return "\n--- PAGE BREAK ---\n".join(text_pages)

    async def extract_text(self, file_path: str) -> str:
        """Extracts text from a local PDF asynchronously using pdfplumber."""
        return await asyncio.to_thread(self._sync_extract, file_path)
