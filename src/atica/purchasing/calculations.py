"""Purchase quantity calculation: stock deduction, minimum order quantity, order multiples, unit conversion."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any, List, Optional, Tuple

from ..core.exceptions import MissingInputError
from ..core.precision import dec, display_decimal
from ..core.results import Result
from ..core.validation import non_negative, positive
from ..units import UnitRegistry, default_registry


@dataclass(frozen=True)
class PurchaseQuantity(Result):
    """Recommended order.

    All quantities except ``received_quantity`` are in ``unit`` (the *purchase* unit);
    ``received_quantity`` is what arrives in ``stock_unit``.  ``constraints`` lists which rules
    raised the quantity (``'minimum_order_quantity'``, ``'order_multiple'``).
    ``surplus = order_quantity - net_requirement`` (>= 0).
    """

    order_quantity: Decimal
    unit: str
    required_quantity: Decimal
    stock_deducted: Decimal
    net_requirement: Decimal
    surplus: Decimal
    constraints: Tuple[str, ...]
    minimum_order_quantity: Decimal
    order_multiple: Optional[Decimal]
    received_quantity: Decimal
    stock_unit: str
    formula: str = "net = max(required - stock, 0); order = ceil_to_multiple(max(net, MOQ)); 0 if net = 0"
    warnings: Tuple[str, ...] = ()

    def __str__(self) -> str:
        return ("%s %s" % (display_decimal(self.order_quantity), self.unit)).strip()


def calculate_purchase_quantity(
    required_quantity: Any,
    *,
    unit: str = "",
    stock_on_hand: Any = 0,
    minimum_order_quantity: Any = 0,
    order_multiple: Any = None,
    purchase_unit: Optional[str] = None,
    registry: Optional[UnitRegistry] = None,
) -> PurchaseQuantity:
    """How much to order to cover ``required_quantity``.

    Steps (all exact):

    1. ``net = max(required - stock_on_hand, 0)``; if ``net`` is 0 nothing is ordered (the minimum
       order quantity is **not** forced on an order you do not need);
    2. raise to ``minimum_order_quantity`` if lower;
    3. round **up** to a multiple of ``order_multiple`` (package ceiling).

    :param required_quantity: needed amount (``>= 0``) in ``unit``.
    :param unit: unit of ``required_quantity`` and ``stock_on_hand`` (a registry unit when
        ``purchase_unit`` is used, otherwise just a label).
    :param stock_on_hand: available stock in ``unit`` (``>= 0``).
    :param minimum_order_quantity: supplier minimum, in the **purchase unit** (default 0 = none).
    :param order_multiple: orders must be a multiple of this, in the purchase unit (``None`` = any
        amount; pass ``1`` for indivisible units such as bags).
    :param purchase_unit: the unit you buy in, e.g. a custom ``"bag"`` registered as 25 kg.  Must
        be convertible from ``unit``; omit to buy in ``unit``.
    :param registry: registry with custom units.

    >>> r = calculate_purchase_quantity(87, unit="piece", minimum_order_quantity=24, order_multiple=12)
    >>> str(r)
    '96 piece'
    """
    required = non_negative(required_quantity, "required_quantity")
    stock = non_negative(stock_on_hand, "stock_on_hand")
    moq = non_negative(minimum_order_quantity, "minimum_order_quantity")
    multiple = positive(order_multiple, "order_multiple") if order_multiple is not None else None
    k = Fraction(1)
    buy_unit = unit
    if purchase_unit is not None:
        if not unit:
            raise MissingInputError(
                "unit is required when purchase_unit is given.",
                parameter="unit",
                hint="State the unit of required_quantity.",
            )
        reg = registry or default_registry()
        k = reg.factor(unit, purchase_unit)
        buy_unit = reg.get(purchase_unit).symbol
        unit = reg.get(unit).symbol
    required_p, stock_p = required * k, stock * k
    net = max(required_p - stock_p, Fraction(0))
    quantity = net
    constraints: List[str] = []
    warnings: List[str] = []
    if net > 0:
        if moq > quantity:
            quantity = moq
            constraints.append("minimum_order_quantity")
        if multiple is not None:
            rounded = math.ceil(quantity / multiple) * multiple
            if rounded != quantity:
                quantity = rounded
                constraints.append("order_multiple")
            if moq > 0 and (moq / multiple).denominator != 1:
                warnings.append(
                    "The minimum order quantity %s is not a multiple of the order multiple %s."
                    % (dec(moq), dec(multiple))
                )
    return PurchaseQuantity(
        order_quantity=dec(quantity),
        unit=buy_unit,
        required_quantity=dec(required_p),
        stock_deducted=dec(min(stock_p, required_p)),
        net_requirement=dec(net),
        surplus=dec(quantity - net),
        constraints=tuple(constraints),
        minimum_order_quantity=dec(moq),
        order_multiple=dec(multiple) if multiple is not None else None,
        received_quantity=dec(quantity / k),
        stock_unit=unit,
        warnings=tuple(warnings),
    )
