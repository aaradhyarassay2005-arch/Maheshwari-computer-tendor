import os
import asyncio
from app.domain.repositories import IStorageProvider


class LocalStorageProvider(IStorageProvider):
    """Handles binary file saving and deleting operations on the local file system using async wrappers."""
    def __init__(self, base_dir: str = "data/pdfs"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _sync_save(self, filename: str, content: bytes) -> str:
        file_path = os.path.join(self.base_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content)
        # Normalize path separators for consistency across platforms
        return file_path.replace("\\", "/")

    def _sync_delete(self, file_path: str) -> None:
        if os.path.exists(file_path):
            os.remove(file_path)

    async def save(self, filename: str, content: bytes) -> str:
        """Saves content buffer to local disk asynchronously and returns the file path."""
        return await asyncio.to_thread(self._sync_save, filename, content)

    async def delete(self, file_path: str) -> None:
        """Removes target file from local disk asynchronously."""
        await asyncio.to_thread(self._sync_delete, file_path)
