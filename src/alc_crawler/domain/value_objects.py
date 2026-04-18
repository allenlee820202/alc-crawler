"""Domain value objects.

Value objects are immutable and compared by value. They contain validation
invariants and have no dependencies on infrastructure.
"""
from __future__ import annotations

from dataclasses import dataclass

_SUPPORTED_CURRENCIES = frozenset({"TWD", "USD"})


@dataclass(frozen=True, slots=True)
class Price:
    amount: int
    currency: str = "TWD"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Price.amount must be non-negative")
        if self.currency not in _SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {self.currency}")


@dataclass(frozen=True, slots=True)
class Address:
    city: str
    district: str
    raw: str

    def __post_init__(self) -> None:
        if not self.city.strip():
            raise ValueError("Address.city must not be empty")


@dataclass(frozen=True, slots=True)
class ListingId:
    site: str
    external_id: str

    def __post_init__(self) -> None:
        if not self.site.strip():
            raise ValueError("ListingId.site must not be empty")
        if not self.external_id.strip():
            raise ValueError("ListingId.external_id must not be empty")

    def __str__(self) -> str:
        return f"{self.site}:{self.external_id}"
