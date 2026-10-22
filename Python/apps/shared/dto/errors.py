from dataclasses import dataclass


@dataclass
class RouteError:
    error_type: str
    error_text: str
    source: str | None = None


class NotFoundError(Exception):
    """The requested entity was not found."""


class ValidationError(Exception):
    """The input data failed validation."""


class ResourcePermissionError(PermissionError):
    """The caller is not allowed to perform the operation."""
