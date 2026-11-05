"""Purchasing and inventory quantities (M07)."""
from __future__ import annotations

from decimal import ROUND_CEILING, Decimal
from typing import Any, Dict, List, Optional

from ..calculations.numeric import calc_context, clean, format_quantity
from ..calculations.rounding import RoundingPolicy
from ..exceptions import AticaError, InventoryError
from ..results import CalculationResult
from ..units.registry import UnitRegistry
from ..validation.manufacturing_rules import validate_purchase_inputs
from ..validation.result import ValidationResult, parse_number


def _ceil_to_multiple(value: Decimal, multiple: Decimal) -> Decimal:
    return (value / multiple).to_integral_value(rounding=ROUND_CEILING) * multiple


def calculate_purchase_quantity(
    required_quantity: Any,
    order_multiple: Any = 1,
    minimum_order_quantity: Any = 0,
    *,
    on_hand: Any = 0,
    unit: Optional[str] = "pieces",
) -> CalculationResult:
    """Recommended order quantity.

    1. ``net = max(required - on_hand, 0)`` (nothing to order when ``net`` is 0);
    2. raise to ``minimum_order_quantity`` if lower;
    3. round **up** to the next multiple of ``order_multiple``.

    The result's ``metadata['constraints']`` lists which rules changed the quantity.

    >>> str(calculate_purchase_quantity(87, order_multiple=12, minimum_order_quantity=24))
    '96 pieces'
    """
    validate_purchase_inputs(required_quantity, order_multiple, minimum_order_quantity, on_hand).raise_if_invalid(
        InventoryError
    )
    from ..calculations.numeric import to_decimal

    required = to_decimal(required_quantity)
    multiple = to_decimal(order_multiple)
    moq = to_decimal(minimum_order_quantity)
    stock = to_decimal(on_hand)
    warnings: List[str] = []
    constraints: List[str] = []
    with calc_context():
        net = max(required - stock, Decimal(0))
        qty = net
        if net > 0:
            if moq > qty:
                qty = moq
                constraints.append("minimum_order_quantity")
            rounded = _ceil_to_multiple(qty, multiple)
            if rounded != qty:
                constraints.append("order_multiple")
            qty = rounded
            if moq > 0 and moq % multiple != 0:
                warnings.append(
                    "Minimum order quantity %s is not a multiple of the order multiple %s." % (format_quantity(moq), format_quantity(multiple))
                )
        qty = clean(qty)
        surplus = clean(qty - net)
    return CalculationResult(
        output_quantity=qty,
        output_unit=unit,
        input_quantity=required,
        input_unit=unit,
        formula="max(net, MOQ) rounded up to a multiple of order_multiple",
        rounding_policy=RoundingPolicy.CEILING_PACKAGE,
        warnings=tuple(warnings),
        metadata={
            "net_requirement": clean(net),
            "surplus": surplus,
            "constraints": constraints,
            "order_multiple": multiple,
            "minimum_order_quantity": moq,
        },
    )


class PurchasingConfig:
    """Supplier-specific purchasing rules (data model 7.5).

    ``minimum_order_quantity`` and ``order_multiple`` are expressed in ``purchase_unit``.
    ``conversion_configuration`` may contain ``{"stock_units_per_purchase_unit": "12"}``
    to state the conversion explicitly; otherwise it is derived from the product's
    packaging levels or from the unit registry.
    """

    def __init__(
        self,
        supplier_id: str,
        product_id: str,
        purchase_unit: str,
        stock_unit: str,
        minimum_order_quantity: Any = 0,
        order_multiple: Any = 1,
        conversion_configuration: Optional[Dict[str, Any]] = None,
    ) -> None:
        result = ValidationResult()
        for name, val in (("supplier_id", supplier_id), ("product_id", product_id),
                          ("purchase_unit", purchase_unit), ("stock_unit", stock_unit)):
            if not isinstance(val, str) or not val.strip():
                result.add_error("MISSING_CONFIGURATION", name, "%s is required." % name)
        moq = parse_number(result, minimum_order_quantity, "minimum_order_quantity", minimum=Decimal(0),
                           code="INVALID_MINIMUM_ORDER_QUANTITY", label="Minimum order quantity")
        mult = parse_number(result, order_multiple, "order_multiple", minimum=Decimal(0), allow_equal_minimum=False,
                            code="INVALID_ORDER_MULTIPLE", label="Order multiple")
        conv = dict(conversion_configuration or {})
        explicit = conv.get("stock_units_per_purchase_unit")
        if explicit is not None:
            parse_number(result, explicit, "conversion_configuration", minimum=Decimal(0), allow_equal_minimum=False,
                         code="INVALID_CONVERSION_CONFIGURATION", label="stock_units_per_purchase_unit")
        result.raise_if_invalid(InventoryError)
        self.supplier_id = supplier_id.strip()
        self.product_id = product_id.strip()
        self.purchase_unit = purchase_unit.strip()
        self.stock_unit = stock_unit.strip()
        self.minimum_order_quantity = moq
        self.order_multiple = mult
        self.conversion_configuration = conv

    def stock_per_purchase_unit(self, *, product: Any = None, registry: Optional[UnitRegistry] = None) -> Decimal:
        """How many stock units one purchase unit contains."""
        from ..calculations.numeric import to_decimal

        explicit = self.conversion_configuration.get("stock_units_per_purchase_unit")
        if explicit is not None:
            return to_decimal(explicit)
        if self.purchase_unit == self.stock_unit:
            return Decimal(1)
        if product is not None and product.has_level(self.purchase_unit) and product.has_level(self.stock_unit):
            return product.units_per(self.purchase_unit, self.stock_unit)
        if registry is None:
            from ..units.converter import get_default_registry

            registry = get_default_registry()
        if registry.has_unit(self.purchase_unit) and registry.has_unit(self.stock_unit):
            try:
                return registry.convert(1, self.purchase_unit, self.stock_unit).output_quantity
            except AticaError as exc:
                raise InventoryError(exc.message, code=exc.code, field="stock_unit") from exc
        raise InventoryError(
            "Cannot convert %s to %s: provide stock_units_per_purchase_unit, a product with both packaging "
            "levels, or physical units." % (self.purchase_unit, self.stock_unit),
            code="MISSING_CONVERSION",
            field="conversion_configuration",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supplier_id": self.supplier_id,
            "product_id": self.product_id,
            "purchase_unit": self.purchase_unit,
            "stock_unit": self.stock_unit,
            "minimum_order_quantity": format_quantity(self.minimum_order_quantity),
            "order_multiple": format_quantity(self.order_multiple),
            "conversion_configuration": dict(self.conversion_configuration),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PurchasingConfig":
        try:
            return cls(
                data["supplier_id"], data["product_id"], data["purchase_unit"], data["stock_unit"],
                data.get("minimum_order_quantity", 0), data.get("order_multiple", 1),
                data.get("conversion_configuration"),
            )
        except (KeyError, TypeError) as exc:
            raise InventoryError("Invalid purchasing configuration: %s" % exc, code="INVALID_CONFIGURATION") from None


def calculate_purchase_order(
    config: PurchasingConfig,
    required_quantity: Any,
    *,
    on_hand: Any = 0,
    product: Any = None,
    registry: Optional[UnitRegistry] = None,
    whole_units: bool = True,
) -> CalculationResult:
    """Order quantity in the supplier's ``purchase_unit`` for a need stated in ``stock_unit``.

    Flow: required stock -> subtract ``on_hand`` stock -> convert to purchase units ->
    (whole units) -> minimum order quantity -> order multiple.
    ``metadata['stock_quantity']`` is what arrives in stock units.
    """
    from ..calculations.numeric import to_decimal

    validate_purchase_inputs(required_quantity, 1, 0, on_hand).raise_if_invalid(InventoryError)
    ratio = config.stock_per_purchase_unit(product=product, registry=registry)
    with calc_context():
        net_stock = max(to_decimal(required_quantity) - to_decimal(on_hand), Decimal(0))
        need = net_stock / ratio
        if whole_units:
            need = need.to_integral_value(rounding=ROUND_CEILING)
    order = calculate_purchase_quantity(
        need, config.order_multiple, config.minimum_order_quantity, unit=config.purchase_unit
    )
    with calc_context():
        stock_received = clean(order.output_quantity * ratio)
        surplus_stock = clean(stock_received - net_stock)
    meta = dict(order.metadata)
    meta.update(
        supplier_id=config.supplier_id,
        product_id=config.product_id,
        stock_unit=config.stock_unit,
        stock_per_purchase_unit=clean(ratio),
        net_stock_requirement=clean(net_stock),
        stock_quantity=stock_received,
        surplus_stock=surplus_stock,
    )
    return CalculationResult(
        output_quantity=order.output_quantity,
        output_unit=config.purchase_unit,
        input_quantity=to_decimal(required_quantity),
        input_unit=config.stock_unit,
        formula=order.formula,
        rounding_policy=order.rounding_policy,
        warnings=order.warnings,
        metadata=meta,
    )
