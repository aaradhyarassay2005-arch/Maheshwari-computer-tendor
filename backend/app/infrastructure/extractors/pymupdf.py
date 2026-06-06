import fitz  # PyMuPDF
import asyncio
from app.domain.repositories import IPDFExtractor


class PyMuPDFExtractor(IPDFExtractor):
    """Fallback PDF text extractor strategy using PyMuPDF (fitz)."""
    def _sync_extract(self, file_path: str) -> str:
        text_pages = []
        doc = fitz.open(file_path)
        for page_num in range(min(5, len(doc))):
            page = doc[page_num]
            page_text = page.get_text()
            if page_text:
                text_pages.append(page_text)
        doc.close()
        return "\n--- PAGE BREAK ---\n".join(text_pages)

    async def extract_text(self, file_path: str) -> str:
        """Extracts text from a local PDF asynchronously using PyMuPDF."""
        return await asyncio.to_thread(self._sync_extract, file_path)
