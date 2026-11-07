"""In-memory inventory operations for the Group 3 Phase 2 proof of concept.

This prototype is deliberately single-process and non-persistent. SKU strings are
unique dictionary keys; all stock adjustments must be nonzero and may not bring
quantities below zero. Only successful stock adjustments enter history.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import math
from typing import Dict, List, Set


@dataclass
class Product:
    sku: str
    name: str
    quantity: int
    min_stock: int


@dataclass(frozen=True)
class Transaction:
    timestamp_utc: str
    sku: str
    change: int
    before: int
    after: int


class InventoryManager:
    """Store products in a dict, low-stock SKUs in a set, and changes in a list."""

    def __init__(self) -> None:
        self.products: Dict[str, Product] = {}
        self.low_stock: Set[str] = set()
        self.transactions: List[Transaction] = []

    @staticmethod
    def _valid_nonnegative_int(value: object, label: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{label} must be a nonnegative integer")
        return value

    @staticmethod
    def _required_text(value: object, label: str) -> str:
        # Reject values that are not strings.
        if not isinstance(value, str):
            raise ValueError(f"{label} cannot be empty")

        # Remove surrounding whitespace once.
        cleaned = value.strip()

        # Reject empty strings and whitespace-only input.
        if not cleaned:
            raise ValueError(f"{label} cannot be empty")
        return cleaned

    def _update_low_stock(self, product: Product) -> None:
        """Maintain low-stock invariant immediately after an accepted change."""
        if product.quantity <= product.min_stock:
            self.low_stock.add(product.sku)
        else:
            self.low_stock.discard(product.sku)

    def add_product(self, sku: str, name: str, quantity: int, min_stock: int) -> Product:
        """Register unique SKU with starting stock; no transaction is logged."""
        sku = self._required_text(sku, "SKU")
        name = self._required_text(name, "Product name")
        quantity = self._valid_nonnegative_int(quantity, "Quantity")
        min_stock = self._valid_nonnegative_int(min_stock, "Minimum stock")
        if sku in self.products:
            raise ValueError(f"SKU '{sku}' already exists")
        product = Product(sku, name, quantity, min_stock)
        self.products[sku] = product
        self._update_low_stock(product)
        return product

    def get_product(self, sku: str) -> Product | None:
        """Return a product by its unique SKU, or None if absent (average O(1))."""
        return self.products.get(self._required_text(sku, "SKU"))

    def adjust_stock(self, sku: str, change: int) -> Product:
        """Apply nonzero stock delta, rejecting overselling and logging success."""
        sku = self._required_text(sku, "SKU")
        if isinstance(change, bool) or not isinstance(change, int) or change == 0:
            raise ValueError("Stock adjustment must be a nonzero integer")
        product = self.products.get(sku)
        if product is None:
            raise KeyError(f"Unknown SKU: {sku}")
        new_quantity = product.quantity + change
        if new_quantity < 0:
            raise ValueError("Insufficient stock: quantity cannot become negative")
        before = product.quantity
        product.quantity = new_quantity
        self._update_low_stock(product)
        self.transactions.append(Transaction(
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            sku, change, before, new_quantity,
        ))
        return product

    def low_stock_report(self) -> list[Product]:
        """Return flagged products sorted by SKU (O(k log k) for k low-stock SKUs)."""
        return [self.products[sku] for sku in sorted(self.low_stock)]

    def inventory_report(self) -> list[Product]:
        """Return all products in SKU order (O(n log n) including sorting)."""
        return [self.products[sku] for sku in sorted(self.products)]

    def transaction_history(self, sku: str | None = None) -> list[Transaction]:
        """Return accepted adjustments in append order, optionally filtered by SKU."""
        if sku is None:
            return list(self.transactions)
        sku = self._required_text(sku, "SKU")
        return [item for item in self.transactions if item.sku == sku]
