from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ApplicationError(Exception):
    code: str
    message: str
    status_code: int = 500
    fields: list[dict[str, Any]] = field(default_factory=list)
