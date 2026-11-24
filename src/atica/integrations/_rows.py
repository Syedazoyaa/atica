"""Shared, format-independent row processing for the CSV and Excel integrations."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, cast

from ..core.exceptions import AticaError, IntegrationError
from ..core.results import Result
from ..core.rounding import Rounding
from ..materials import Bom, BomItem
from ..units import UnitRegistry, default_registry

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_ROWS = 100_000

Row = Dict[str, str]
_NUMBER = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


@dataclass(frozen=True)
class RowError:
    """A problem found in one row (``row_number`` is the position in the source file)."""

    row_number: int
    message: str
    code: str = ""
    hint: Optional[str] = None


@dataclass(frozen=True)
class ConversionReport(Result):
    """Outcome of converting many rows: converted rows (original columns + result columns) and errors.

    ``row_numbers[i]`` is the position **in the source file** (CSV line / Excel row) of ``rows[i]``;
    every :class:`RowError` carries its source row number too.
    """

    fieldnames: Tuple[str, ...]
    rows: Tuple[Row, ...]
    errors: Tuple[RowError, ...] = ()
    total_rows: int = 0
    row_numbers: Tuple[int, ...] = ()

    @property
    def succeeded(self) -> int:
        return len(self.rows)

    @property
    def failed(self) -> int:
        return len(self.errors)


RESULT_COLUMNS = ("result_value", "result_unit", "warnings")


def check_input_path(path: Any, suffixes: Sequence[str]) -> str:
    p = str(os.fspath(path))
    if not os.path.isfile(p):
        raise IntegrationError("File not found: %s" % p, parameter="path")
    if os.path.splitext(p)[1].lower() not in suffixes:
        raise IntegrationError(
            "Unsupported file type %r." % os.path.splitext(p)[1],
            parameter="path",
            hint="Expected: %s." % ", ".join(suffixes),
        )
    if os.path.getsize(p) > MAX_FILE_BYTES:
        raise IntegrationError("File is larger than %d MB." % (MAX_FILE_BYTES // 2**20), parameter="path")
    return p


def check_output_path(path: Any, suffixes: Sequence[str], overwrite: bool) -> str:
    p = str(os.fspath(path))
    if os.path.splitext(p)[1].lower() not in suffixes:
        raise IntegrationError("Output file must end with %s." % " or ".join(suffixes), parameter="path")
    folder = os.path.dirname(os.path.abspath(p))
    if not os.path.isdir(folder):
        raise IntegrationError("Output folder does not exist: %s" % folder, parameter="path")
    if os.path.exists(p) and not overwrite:
        raise IntegrationError(
            "%s already exists." % p, parameter="path", hint="Pass overwrite=True to replace it."
        )
    return p


def sanitize_cell(value: Any) -> Any:
    """Neutralise spreadsheet formula injection: text starting with = + - @ gets a leading apostrophe."""
    if isinstance(value, str) and value and value[0] in "=+-@\t\r" and not _NUMBER.match(value.strip()):
        return "'" + value
    return value


def check_headers(headers: Sequence[str]) -> List[str]:
    cleaned = [h.strip() for h in headers]
    seen = set()
    for h in cleaned:
        if h and h.casefold() in seen:
            raise IntegrationError("Duplicate column %r in the header row." % h, parameter="header")
        seen.add(h.casefold())
    return cleaned


def column_letter(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA (for messages about spreadsheet columns)."""
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def check_cells_have_headers(cells: Sequence[str], headers: Sequence[str], row_number: int) -> None:
    """A populated cell without a header would be dropped silently - refuse instead.

    ``cells`` are the row's texts; ``headers`` the cleaned header row (blank = no header).
    """
    for index, text in enumerate(cells):
        if text and (index >= len(headers) or not headers[index]):
            raise IntegrationError(
                "Row %d has a value (%r) in column %s, which has no header."
                % (row_number, text, column_letter(index)),
                parameter="path",
                hint="Add a header for that column or clear the cell; ATICA will not drop data silently.",
            )


def convert_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    value_column: str = "value",
    from_column: str = "from_unit",
    to_column: str = "to_unit",
    rounding: Any = Rounding.NONE,
    places: int = 0,
    registry: Optional[UnitRegistry] = None,
    row_numbers: Optional[Sequence[int]] = None,
) -> ConversionReport:
    """Convert every row with :func:`atica.units.convert`; rows that fail are reported, not skipped silently.

    A missing *column* is a whole-input failure (:class:`IntegrationError`); a bad *value in a row*
    is reported for that row only.
    """
    reg = registry or default_registry()
    names: List[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    for needed in (value_column, from_column, to_column):
        if rows and needed not in names:
            raise IntegrationError(
                "Column %r not found." % needed,
                parameter="columns",
                hint="Columns present: %s." % ", ".join(names),
            )
    fieldnames = tuple(names) + tuple(c for c in RESULT_COLUMNS if c not in names)
    ok: List[Row] = []
    ok_numbers: List[int] = []
    errors: List[RowError] = []
    for index, row in enumerate(rows):
        number = row_numbers[index] if row_numbers else index + 1
        try:
            raw = row.get(value_column)
            if raw is None or str(raw).strip() == "":
                raise IntegrationError("%r is empty." % value_column, parameter=value_column)
            result = reg.convert(
                str(raw).strip(),
                str(row.get(from_column, "")).strip(),
                str(row.get(to_column, "")).strip(),
                rounding=rounding,
                places=places,
            )
        except AticaError as exc:
            errors.append(RowError(number, exc.message, exc.code, exc.hint))
            continue
        out = {k: ("" if v is None else str(v)) for k, v in row.items()}
        out.update(
            result_value=format(result.value, "f"),
            result_unit=result.unit,
            warnings="; ".join(result.warnings),
        )
        ok.append(out)
        ok_numbers.append(number)
    return ConversionReport(fieldnames, tuple(ok), tuple(errors), len(rows), tuple(ok_numbers))


BOM_COLUMNS = ("material_id", "quantity_per_unit", "unit")


def bom_from_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    product_id: str = "",
    allow_duplicates: bool = False,
    row_numbers: Optional[Sequence[int]] = None,
) -> Bom:
    """Build a :class:`~atica.materials.Bom` from rows with ``material_id, quantity_per_unit, unit``
    (optional ``wastage_percent`` and ``name``).  Any invalid row raises with its row number."""
    if not rows:
        raise IntegrationError("The file contains no BOM rows.", parameter="rows")
    names: Set[str] = set()
    for row in rows:
        names.update(row)
    missing = [c for c in BOM_COLUMNS if c not in names]
    if missing:
        raise IntegrationError(
            "Missing BOM column(s): %s." % ", ".join(missing),
            parameter="columns",
            hint="Required columns: %s (optional: wastage_percent, name)." % ", ".join(BOM_COLUMNS),
        )
    items: List[BomItem] = []
    for index, row in enumerate(rows):
        number = row_numbers[index] if row_numbers else index + 1
        try:
            items.append(
                BomItem(
                    str(row.get("material_id", "")),
                    cast(Any, str(row.get("quantity_per_unit", "")).strip()),
                    str(row.get("unit", "")),
                    cast(Any, str(row.get("wastage_percent") or "0").strip()),
                    str(row.get("name") or ""),
                )
            )
        except AticaError as exc:
            raise IntegrationError(
                "Row %d: %s" % (number, exc.message), parameter="rows", hint=exc.hint
            ) from exc
    return Bom(tuple(items), product_id=product_id, allow_duplicates=allow_duplicates)
