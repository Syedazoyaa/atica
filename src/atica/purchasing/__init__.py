"""Purchasing calculations (Module 06, standalone): MOQ, order multiples, stock and unit conversion.

>>> from atica.purchasing import calculate_purchase_quantity
>>> str(calculate_purchase_quantity(87, unit="piece", minimum_order_quantity=24, order_multiple=12))
'96 piece'
"""

from .calculations import PurchaseQuantity, calculate_purchase_quantity

__all__ = ["PurchaseQuantity", "calculate_purchase_quantity"]
