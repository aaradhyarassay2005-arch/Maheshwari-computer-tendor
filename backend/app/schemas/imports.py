from typing import List, Dict, Any
from pydantic import BaseModel


class ExcelImportResponse(BaseModel):
    total_rows: int
    inserted: int
    duplicates: int
    failed: int
    errors: List[Dict[str, Any]] = []
