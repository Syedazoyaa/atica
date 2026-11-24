"""Quantity conversion and breakdown between packaging levels.

All arithmetic is exact (fractions); results are Decimals.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any, Dict, Tuple

from ..core.exceptions import InvalidQuantityError
from ..core.precision import dec, display_decimal
from ..core.results import Result
from ..core.validation import non_negative
from .hierarchy import Product


@dataclass(frozen=True)
class PackagingBreakdown(Result):
    """Result of :func:`breakdown` (``quantity`` of ``from_level`` expressed in ``to_level`` packages).

    * ``exact_packages``    - the exact (possibly fractional) conversion, a ratio;
    * ``full_packages``     - complete ``to_level`` packages (``floor(exact_packages)``);
    * ``remainder``         - what is left after the full packages, in ``remainder_unit``
      (the *smaller* of the two levels, so going 250 piece -> carton leaves "10 piece");
    * ``packages_required`` - whole packages needed to hold **everything** (``ceil``);
    * ``packaged_quantity`` - quantity those required packages cover, in ``from_level`` units;
    * ``surplus``           - ``packaged_quantity - quantity`` (>= 0), in ``from_level`` units;
    * ``units_per_package`` - how many ``from_level`` units fill one ``to_level`` package.
    """

    product_id: str
    quantity: Decimal
    from_level: str
    to_level: str
    exact_packages: Decimal
    full_packages: Decimal
    remainder: Decimal
    remainder_unit: str
    packages_required: Decimal
    packaged_quantity: Decimal
    surplus: Decimal
    units_per_package: Decimal
    formula: str = "exact = quantity x size(from) / size(to); full = floor(exact); required = ceil(exact)"
    warnings: Tuple[str, ...] = ()

    def __str__(self) -> str:
        text = "%s %s = %s full %s" % (
            _f(self.quantity),
            self.from_level,
            _f(self.full_packages),
            self.to_level,
        )
        if self.remainder:
            text += " + %s %s remaining" % (_f(self.remainder), self.remainder_unit)
        return text + " (%s %s required)" % (_f(self.packages_required), self.to_level)


@dataclass(frozen=True)
class PackagingPlan(Result):
    """Result of :func:`decompose`: a quantity as whole packages at every level.

    ``counts`` lists ``(level, whole_count)`` from the largest level to the *second* smallest;
    ``remainder`` is what is left in the base unit (``base_unit``) and may be fractional.
    ``sum(count * size(level)) + remainder == quantity`` in base units.
    """

    product_id: str
    quantity: Decimal
    from_level: str
    counts: Tuple[Tuple[str, Decimal], ...]
    remainder: Decimal
    base_unit: str

    def by_level(self) -> Dict[str, Decimal]:
        """``{level: count}`` including the base level's remainder."""
        out = dict(self.counts)
        out[self.base_unit] = self.remainder
        return out


def _f(value: Decimal) -> str:
    return display_decimal(value)


def _quantity(quantity: Any, require_whole: bool) -> Fraction:
    q = non_negative(quantity, "quantity")
    if require_whole and q.denominator != 1:
        raise InvalidQuantityError(
            "quantity %s is not a whole number." % quantity,
            parameter="quantity",
            hint="Pass require_whole=False to allow fractional quantities.",
        )
    return q


def convert_quantity(product: Product, quantity: Any, from_level: str, to_level: str) -> Decimal:
    """Exact equivalent of ``quantity`` ``from_level`` in ``to_level`` (850 cartons -> 21.25 pallets).

    Formula: ``quantity x size(from_level) / size(to_level)`` where ``size`` counts base units.
    """
    q = _quantity(quantity, False)
    return dec(q * product._size(from_level) / product._size(to_level))


def breakdown(
    product: Product,
    quantity: Any,
    from_level: str,
    to_level: str,
    *,
    require_whole: bool = False,
) -> PackagingBreakdown:
    """Break ``quantity`` of ``from_level`` into ``to_level`` packages.

    :param product: the :class:`Product` that defines the hierarchy.
    :param quantity: non-negative amount of ``from_level`` units (fractions allowed).
    :param from_level: level the quantity is measured in, e.g. ``"piece"``.
    :param to_level: level to pack into, e.g. ``"carton"`` (may be larger or smaller).
    :param require_whole: reject fractional quantities.
    :returns: :class:`PackagingBreakdown`.
    :raises UnknownPackagingLevelError: a level is not in the product.
    :raises InvalidQuantityError: negative / non-numeric / (with ``require_whole``) fractional quantity.

    With 1 carton = 20 boxes = 240 pieces, 250 pieces give ``full_packages=1``,
    ``remainder=10 piece`` and ``packages_required=2``.

    >>> from atica.packaging import PackagingLevel, Product
    >>> p = Product("P", "A", levels=[PackagingLevel("piece"), PackagingLevel("box", 12, "piece"),
    ...                               PackagingLevel("carton", 20, "box")])
    >>> r = breakdown(p, 250, "piece", "carton")
    >>> (int(r.full_packages), int(r.remainder), int(r.packages_required))
    (1, 10, 2)
    """
    q = _quantity(quantity, require_whole)
    src, dst = product.level(from_level), product.level(to_level)
    size_src, size_dst = product._size(src.name), product._size(dst.name)
    exact = q * size_src / size_dst
    full = math.floor(exact)
    required = math.ceil(exact)
    per_package = size_dst / size_src  # from_level units per to_level package
    if size_dst >= size_src:  # packing up: the leftover is in from_level units
        remainder, remainder_unit = q - full * per_package, src.name
    else:  # splitting down: the leftover is a fraction of one to_level unit
        remainder, remainder_unit = exact - full, dst.name
    packaged = required * per_package
    return PackagingBreakdown(
        product_id=product.product_id,
        quantity=dec(q),
        from_level=src.name,
        to_level=dst.name,
        exact_packages=dec(exact),
        full_packages=Decimal(full),
        remainder=dec(remainder),
        remainder_unit=remainder_unit,
        packages_required=Decimal(required),
        packaged_quantity=dec(packaged),
        surplus=dec(packaged - q),
        units_per_package=dec(per_package),
    )


def packages_required(product: Product, quantity: Any, from_level: str, to_level: str) -> Decimal:
    """Minimum whole ``to_level`` packages needed to hold ``quantity`` of ``from_level`` (package ceiling)."""
    return breakdown(product, quantity, from_level, to_level).packages_required


def decompose(product: Product, quantity: Any, from_level: str = "") -> PackagingPlan:
    """Express ``quantity`` as whole packages at every level, largest first.

    ``from_level`` defaults to the base level.  With 1 box = 12 pieces, 1 carton = 20 boxes,
    250 pieces -> 1 carton, 0 boxes, 10 pieces.

    >>> from atica.packaging import PackagingLevel, Product
    >>> p = Product("P", "A", levels=[PackagingLevel("piece"), PackagingLevel("box", 12, "piece"),
    ...                               PackagingLevel("carton", 20, "box")])
    >>> {k: int(v) for k, v in decompose(p, 250).by_level().items()}
    {'carton': 1, 'box': 0, 'piece': 10}
    """
    q = _quantity(quantity, False)
    src = product.level(from_level) if from_level else product.base_level
    remaining = q * product._size(src.name)  # in base units
    counts = []
    for level in reversed(product.levels[1:]):
        size = product._size(level.name)
        n = math.floor(remaining / size)
        counts.append((level.name, Decimal(n)))
        remaining -= n * size
    return PackagingPlan(
        product_id=product.product_id,
        quantity=dec(q),
        from_level=src.name,
        counts=tuple(counts),
        remainder=dec(remaining),
        base_unit=product.base_level.name,
    )
