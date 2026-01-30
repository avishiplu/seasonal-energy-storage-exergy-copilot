from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RefusalError(Exception):
    """
    Raise this when the app must REFUSE to compute.
    It is not a bug; it is a safety refusal.
    """
    code: str
    user_message: str
    why: str
    missing: Optional[List[str]] = None
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return f"{self.code}: {self.user_message}"
