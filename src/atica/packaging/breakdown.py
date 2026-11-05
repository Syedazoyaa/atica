"""Quantity conversion and package breakdown (M04)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Any, Dict, List

from ..calculations.numeric import calc_context, clean, format_quantity, plain_number, to_decimal
from ..exceptions import InvalidQuantityError, PackagingError
from .product import Product


@dataclass(frozen=True)
class BreakdownResult:
    """Result of :func:`breakdown`.

    * ``full_packages``      - complete ``to_unit`` packages;
    * ``remaining_quantity`` - leftover, in ``from_unit`` (never discarded);
    * ``packages_required``  - packages needed to hold the *entire* quantity;
    * ``exact_equivalent``   - exact (possibly fractional) package equivalent;
    * ``total_quantity``     - the input quantity, in ``from_unit``.
    """

    product_id: str
    from_unit: str
    to_unit: str
    total_quantity: Decimal
    full_packages: Decimal
    remaining_quantity: Decimal
    packages_required: Decimal
    exact_equivalent: Decimal
    package_size: Decimal  # from_units per to_unit (<1 when converting to a smaller unit)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "full_packages": plain_number(self.full_packages),
            "remaining_quantity": plain_number(self.remaining_quantity),
            "packages_required": plain_number(self.packages_required),
            "total_quantity": plain_number(self.total_quantity),
            "exact_equivalent": plain_number(self.exact_equivalent),
        }

    def __str__(self) -> str:
        f = format_quantity
        text = "%s %s = %s full %s" % (f(self.total_quantity), self.from_unit, f(self.full_packages), self.to_unit)
        if self.remaining_quantity:
            text += " + %s %s remaining" % (f(self.remaining_quantity), self.from_unit)
        return text + " (%s %s required)" % (f(self.packages_required), self.to_unit)


def _prepare(product: Product, quantity: Any, from_unit: str, allow_partial: bool) -> Decimal:
    if not isinstance(product, Product):
        raise PackagingError("A Product is required.", code="UNKNOWN_PRODUCT", field="product")
    product.require_valid()
    qty = to_decimal(quantity, field="quantity")
    if qty < 0:
        raise InvalidQuantityError("Quantity cannot be negative (got %s)." % qty, code="NEGATIVE_QUANTITY", field="quantity")
    if not allow_partial and qty != qty.to_integral_value():
        raise InvalidQuantityError(
            "Quantity %s is fractional; pass allow_partial=True to allow partial packages." % qty,
            code="PARTIAL_NOT_ALLOWED",
            field="quantity",
        )
    return qty


def convert_quantity(product: Product, quantity: Any, from_unit: str, to_unit: str, *, allow_partial: bool = True) -> Decimal:
    """Exact package equivalent of ``quantity`` (e.g. 850 cartons -> 21.25 pallets)."""
    qty = _prepare(product, quantity, from_unit, allow_partial)
    with calc_context():
        return clean(qty * product.base_size(from_unit) / product.base_size(to_unit))


def breakdown(
    product: Product,
    quantity: Any,
    from_unit: str,
    to_unit: str,
    *,
    allow_partial: bool = False,
) -> BreakdownResult:
    """Break ``quantity`` of ``from_unit`` into whole ``to_unit`` packages.

    >>> breakdown(product, "850", "carton", "pallet").to_dict()["full_packages"]
    21
    """
    qty = _prepare(product, quantity, from_unit, allow_partial)
    src = product.get_level(from_unit).name
    dst = product.get_level(to_unit).name
    size_src, size_dst = product.base_size(src), product.base_size(dst)
    with calc_context():
        if size_dst >= size_src:
            per_package = size_dst / size_src  # from_units per to_unit (a whole number)
            exact = qty / per_package
            full = exact.to_integral_value(rounding=ROUND_FLOOR)
            remaining = qty - full * per_package
            required = exact.to_integral_value(rounding=ROUND_CEILING)
            size = per_package
        else:  # converting to a smaller unit: everything is "full"
            per_unit = size_src / size_dst  # to_units per from_unit
            exact = qty * per_unit
            full = exact.to_integral_value(rounding=ROUND_FLOOR)
            remaining = Decimal(0)
            required = exact.to_integral_value(rounding=ROUND_CEILING)
            if full != exact:
                remaining = (exact - full) / per_unit  # in from_unit, keeps the fractional part
            size = Decimal(1) / per_unit
        return BreakdownResult(
            product_id=product.product_id,
            from_unit=src,
            to_unit=dst,
            total_quantity=clean(qty),
            full_packages=clean(full),
            remaining_quantity=clean(remaining),
            packages_required=clean(required),
            exact_equivalent=clean(exact),
            package_size=clean(size),
        )


def decompose(product: Product, quantity: Any, from_unit: str) -> Dict[str, Decimal]:
    """Express ``quantity`` as whole packages at every level, largest first.

    With 1 box = 12 pieces, 1 carton = 20 boxes and 1 pallet = 40 cartons,
    ``decompose(product, 262, "piece")`` -> ``{"pallet": 0, "carton": 1, "box": 1, "piece": 10}``.
    The quantity must be a whole number of base units.
    """
    qty = _prepare(product, quantity, from_unit, allow_partial=True)
    with calc_context():
        total_base = qty * product.base_size(from_unit)
        if total_base != total_base.to_integral_value():
            raise InvalidQuantityError(
                "Quantity is not a whole number of base units (%s)." % format_quantity(total_base),
                code="PARTIAL_NOT_ALLOWED",
                field="quantity",
            )
        result: Dict[str, Decimal] = {}
        remaining = total_base
        for level in reversed(product.levels):
            size = product.base_size(level.name)
            count = (remaining // size)
            result[level.name] = clean(count)
            remaining -= count * size
    return result
