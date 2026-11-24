"""Optional file integrations.

``atica.integrations.csv`` needs nothing extra; ``atica.integrations.excel`` needs
``pip install "atica[excel]"``.  Nothing here is imported by the calculation modules.
"""

from ._rows import ConversionReport, RowError, bom_from_rows, convert_rows

__all__ = ["ConversionReport", "RowError", "bom_from_rows", "convert_rows"]
