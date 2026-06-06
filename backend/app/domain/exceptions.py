class DomainException(Exception):
    """Base domain exception class."""
    pass


class TenderNotFoundException(DomainException):
    """Raised when a requested tender does not exist."""
    def __init__(self, tender_id: str):
        super().__init__(f"Tender with ID {tender_id} not found")


class TenderAlreadyExistsException(DomainException):
    """Raised when attempting to create a tender with an already registered number."""
    def __init__(self, tender_number: str):
        super().__init__(f"Tender with number '{tender_number}' already exists")


class TenderNotParsedException(DomainException):
    """Raised when risk analysis or other engines require parsed tender metadata/text but it is missing."""
    def __init__(self, tender_id: str):
        super().__init__(f"Tender with ID {tender_id} has not been parsed yet. Please extract metadata first.")

