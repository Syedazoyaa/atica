"""Bulk conversion of CSV / Excel files (M08).

Each row is processed independently. Original input is preserved untouched;
errors are reported per row, while problems that make the whole file unusable
(missing columns, unreadable file) raise :class:`BulkProcessingError`.

Row logic
---------
* both units are packaging levels of the row's product -> packaging :func:`breakdown`;
* both units are physical units -> unit conversion;
* otherwise the row is rejected with a precise error code.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

from ..calculations.numeric import format_quantity
from ..exceptions import AticaError, BulkProcessingError, IncompatibleUnitError, UnknownProductError, UnknownUnitError
from ..packaging.breakdown import breakdown
from ..packaging.product import Product
from ..units.converter import get_default_registry
from ..units.registry import UnitRegistry
from ..validation.bulk_rules import validate_columns, validate_row_fields
from ._common import Table
from .csv_handler import EXTRA, read_csv, write_csv
from .excel_handler import read_xlsx, write_xlsx

_COLUMN_ALIASES = {
    "product": ("product", "productid", "productname", "sku", "item", "itemcode"),
    "quantity": ("quantity", "qty", "amount", "value"),
    "from_unit": ("fromunit", "from", "unitfrom", "sourceunit", "unit", "inputunit"),
    "to_unit": ("tounit", "to", "unitto", "targetunit", "outputunit"),
}
RESULT_COLUMNS = (
    "operation",
    "result_quantity",
    "result_unit",
    "full_packages",
    "remaining_quantity",
    "packages_required",
    "warnings",
)


def _norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.casefold())


def map_columns(fieldnames: Sequence[str], column_map: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    """Map logical fields (product, quantity, from_unit, to_unit) to real column headers.

    ``column_map`` overrides auto-detection. Raises :class:`BulkProcessingError` when
    a required column is missing (a *complete file failure*).
    """
    mapping: Dict[str, str] = dict(column_map or {})
    unknown = set(mapping) - set(_COLUMN_ALIASES)
    if unknown:
        raise BulkProcessingError("Unknown logical field(s) in column_map: %s." % ", ".join(sorted(unknown)), code="INVALID_COLUMN_MAP")
    by_norm = {}
    for name in fieldnames:
        by_norm.setdefault(_norm(name), name)
    for logical, aliases in _COLUMN_ALIASES.items():
        if logical in mapping:
            continue
        for alias in aliases:
            if alias in by_norm:
                mapping[logical] = by_norm[alias]
                break
    check = validate_columns(fieldnames, mapping)
    if not check.valid:
        raise BulkProcessingError(
            "; ".join(e.message for e in check.errors), code="MISSING_COLUMN", details=check
        )
    if "product" in mapping and mapping["product"] not in fieldnames:
        raise BulkProcessingError("Column %r (product) is not in the file." % mapping["product"], code="MISSING_COLUMN")
    return mapping


@dataclass
class RowResult:
    row_number: int
    original: Dict[str, Any]
    ok: bool
    output: Dict[str, str] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class BulkResult:
    fieldnames: List[str]
    rows: List[RowResult] = field(default_factory=list)
    stopped_early: bool = False
    source: Optional[str] = None

    def successes(self) -> List[RowResult]:
        return [r for r in self.rows if r.ok]

    def failures(self) -> List[RowResult]:
        return [r for r in self.rows if not r.ok]

    @property
    def summary(self) -> Dict[str, Any]:
        ok = len(self.successes())
        return {
            "total_rows": len(self.rows),
            "succeeded": ok,
            "failed": len(self.rows) - ok,
            "stopped_early": self.stopped_early,
            "source": self.source,
        }


class _ProductIndex:
    def __init__(self, products: Union[None, Mapping[str, Product], Iterable[Product]]) -> None:
        if products is None:
            items: List[Product] = []
        elif isinstance(products, Mapping):
            items = list(products.values())
        else:
            items = list(products)
        self._by_key: Dict[str, List[Product]] = {}
        for p in items:
            for key in {p.product_id.casefold(), str(p.name).casefold()}:
                bucket = self._by_key.setdefault(key, [])
                if p not in bucket:
                    bucket.append(p)

    def find(self, text: str) -> Optional[Product]:
        found = self._by_key.get(text.strip().casefold())
        if not found:
            return None
        if len(found) > 1:
            raise UnknownProductError(
                "Product %r is ambiguous (%d products share it); use the product ID." % (text, len(found)),
                code="AMBIGUOUS_PRODUCT",
                field="product",
            )
        return found[0]


def _convert_row(
    row: Mapping[str, Any],
    mapping: Mapping[str, str],
    index: _ProductIndex,
    registry: UnitRegistry,
    precision: Optional[int],
    rounding: Any,
    allow_partial: bool,
):
    name = str(row.get(mapping["product"], "") if "product" in mapping else "").strip()
    qty = str(row[mapping["quantity"]]).strip()
    src = str(row[mapping["from_unit"]]).strip()
    dst = str(row[mapping["to_unit"]]).strip()
    product = index.find(name) if name else None
    warnings: List[str] = []

    if product is not None and product.has_level(src) and product.has_level(dst):
        r = breakdown(product, qty, src, dst, allow_partial=allow_partial)
        return (
            {
                "operation": "breakdown",
                "result_quantity": format_quantity(r.exact_equivalent),
                "result_unit": r.to_unit,
                "full_packages": format_quantity(r.full_packages),
                "remaining_quantity": "%s %s" % (format_quantity(r.remaining_quantity), r.from_unit),
                "packages_required": format_quantity(r.packages_required),
            },
            warnings,
        )
    if registry.has_unit(src) and registry.has_unit(dst):
        if name and product is None:
            warnings.append("Product %r not configured; plain unit conversion used." % name)
        r = registry.convert(qty, src, dst, precision=precision, rounding=rounding)
        warnings.extend(r.warnings)
        return (
            {
                "operation": "convert",
                "result_quantity": format_quantity(r.output_quantity),
                "result_unit": r.output_unit,
            },
            warnings,
        )

    def kind(unit: str) -> Optional[str]:
        if product is not None and product.has_level(unit):
            return "packaging level"
        return "physical unit" if registry.has_unit(unit) else None

    ks, kd = kind(src), kind(dst)
    if ks and kd:
        raise IncompatibleUnitError(
            "Cannot convert %s %r to %s %r." % (ks, src, kd, dst), field="to_unit"
        )
    for fld, unit, k in (("from_unit", src, ks), ("to_unit", dst, kd)):
        if k is None:
            # Only blame the product when neither unit is understood; if one side is a known
            # physical unit the user clearly meant a plain conversion with a mistyped unit.
            if name and product is None and ks is None and kd is None:
                raise UnknownProductError(
                    "Product %r is not configured, so %r cannot be resolved as a packaging level." % (name, unit),
                    field="product",
                )
            raise UnknownUnitError("Unknown unit %r." % unit, field=fld)
    raise AssertionError("unreachable")  # pragma: no cover


def process_rows(
    data: Union[Table, Sequence[Mapping[str, Any]]],
    *,
    products: Union[None, Mapping[str, Product], Iterable[Product]] = None,
    registry: Optional[UnitRegistry] = None,
    column_map: Optional[Mapping[str, str]] = None,
    on_error: str = "collect",
    precision: Optional[int] = None,
    rounding: Any = None,
    allow_partial: bool = False,
    source: Optional[str] = None,
) -> BulkResult:
    """Process many rows.

    ``on_error``: ``"collect"`` (default) records row errors and continues;
    ``"stop"`` halts at the first failing row (``stopped_early=True``);
    ``"raise"`` raises :class:`BulkProcessingError` at the first failing row.
    """
    if on_error not in ("collect", "stop", "raise"):
        raise BulkProcessingError("on_error must be 'collect', 'stop' or 'raise'.", code="INVALID_ERROR_POLICY")
    if isinstance(data, Table):
        table = data
    else:
        rows = [dict(r) for r in data]
        fieldnames: List[str] = []
        for r in rows:
            for k in r:
                if k not in fieldnames:
                    fieldnames.append(k)
        table = Table(fieldnames, rows, list(range(1, len(rows) + 1)))
    reg = registry or get_default_registry()
    mapping = map_columns(table.fieldnames, column_map)
    index = _ProductIndex(products)
    result = BulkResult(fieldnames=list(table.fieldnames), source=source)

    for number, row in zip(table.row_numbers, table.rows):
        original = dict(row)  # preserved untouched
        errors: List[Dict[str, Any]] = []
        output: Dict[str, str] = {}
        warnings: List[str] = []
        if EXTRA in row:
            errors.append({"code": "TOO_MANY_COLUMNS", "field": None, "message": "Row has more cells than the header has columns."})
        else:
            check = validate_row_fields(row, mapping)
            if not check.valid:
                errors.extend(e.to_dict() for e in check.errors)
            else:
                try:
                    output, warnings = _convert_row(row, mapping, index, reg, precision, rounding, allow_partial)
                except AticaError as exc:
                    errors.append(exc.to_dict())
        item = RowResult(number, original, not errors, output, errors, warnings)
        result.rows.append(item)
        if errors and on_error == "raise":
            raise BulkProcessingError(
                "Row %d: %s" % (number, errors[0]["message"]), code=errors[0]["code"], details=item
            )
        if errors and on_error == "stop":
            result.stopped_early = True
            break
    return result


def process_file(path: Any, *, sheet: Optional[str] = None, max_rows: Optional[int] = None, **options: Any) -> BulkResult:
    """Read a ``.csv`` / ``.xlsx`` file and run :func:`process_rows` on it."""
    p = os.fspath(path)
    kwargs = {} if max_rows is None else {"max_rows": max_rows}
    ext = os.path.splitext(p)[1].lower()
    if ext == ".csv":
        table = read_csv(p, **kwargs)
    elif ext in (".xlsx", ".xlsm"):
        table = read_xlsx(p, sheet=sheet, **kwargs)
    else:
        raise BulkProcessingError("Unsupported file type %r; use .csv or .xlsx." % ext, code="UNSUPPORTED_FILE_TYPE")
    return process_rows(table, source=p, **options)


def _unique(names: Sequence[str], existing: Sequence[str]) -> List[str]:
    taken = set(existing)
    out = []
    for n in names:
        while n in taken:
            n += "_atica"
        taken.add(n)
        out.append(n)
    return out


def _write(path: Any, fieldnames: List[str], rows: List[Dict[str, Any]], overwrite: bool) -> str:
    ext = os.path.splitext(os.fspath(path))[1].lower()
    if ext == ".xlsx":
        return write_xlsx(path, fieldnames, rows, overwrite=overwrite)
    return write_csv(path, fieldnames, rows, overwrite=overwrite)


def export_results(bulk: BulkResult, path: Any, *, overwrite: bool = False) -> str:
    """Write successful rows (original columns + result columns) to a ``.csv`` / ``.xlsx``."""
    new = _unique(RESULT_COLUMNS, bulk.fieldnames)
    fieldnames = bulk.fieldnames + new
    rows = []
    for r in bulk.successes():
        line = dict(r.original)
        for src_name, col in zip(RESULT_COLUMNS, new):
            line[col] = "; ".join(r.warnings) if src_name == "warnings" else r.output.get(src_name, "")
        rows.append(line)
    return _write(path, fieldnames, rows, overwrite)


def export_errors(bulk: BulkResult, path: Any, *, overwrite: bool = False) -> str:
    """Write failed rows with their error codes and messages."""
    new = _unique(("row_number", "error_code", "error_field", "error_message"), bulk.fieldnames)
    fieldnames = new + bulk.fieldnames
    rows = []
    for r in bulk.failures():
        for err in r.errors:
            line = dict(r.original)
            line.pop(EXTRA, None)
            line.update(zip(new, (r.row_number, err["code"], err.get("field") or "", err["message"])))
            rows.append(line)
    return _write(path, fieldnames, rows, overwrite)
