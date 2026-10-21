from dataclasses import dataclass


@dataclass
class RouteError:
    error_type: str
    error_text: str
    source: str | None = None
