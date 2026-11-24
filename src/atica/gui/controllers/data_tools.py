"""Data Tools screen: file import/export through :mod:`atica.integrations`."""

from __future__ import annotations

import os
from typing import Any, List, Mapping

from atica.core import use_precision
from atica.integrations import ConversionReport
from atica.integrations import csv as csv_io
from atica.integrations import excel as excel_io

from ..models import Outcome
from ..services import AppState
from ._common import rounding_args


def _is_excel(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in (".xlsx", ".xlsm")


def convert_file(path: str, values: Mapping[str, Any], state: AppState) -> ConversionReport:
    """Convert every row of a CSV/Excel file (columns ``value``, ``from_unit``, ``to_unit``)."""
    rounding, places = rounding_args(values)
    with use_precision(state.precision):
        if _is_excel(path):
            return excel_io.convert_xlsx(path, registry=state.registry, rounding=rounding, places=places)
        return csv_io.convert_csv(path, registry=state.registry, rounding=rounding, places=places)


def export_report(report: ConversionReport, path: str, *, overwrite: bool = False) -> str:
    rows = list(report.rows)
    if _is_excel(path):
        return excel_io.write_xlsx(path, report.fieldnames, rows, overwrite=overwrite)
    return csv_io.write_csv(path, report.fieldnames, rows, overwrite=overwrite)


def export_errors(report: ConversionReport, path: str, *, overwrite: bool = False) -> str:
    rows = [
        {"row": str(e.row_number), "code": e.code, "message": e.message, "hint": e.hint or ""}
        for e in report.errors
    ]
    if _is_excel(path):
        return excel_io.write_xlsx(
            path, ["row", "code", "message", "hint"], rows, overwrite=overwrite, sheet_name="Errors"
        )
    return csv_io.write_csv(path, ["row", "code", "message", "hint"], rows, overwrite=overwrite)


def export_outcome(outcome: Outcome, path: str, *, overwrite: bool = False) -> str:
    """Structured export of any calculation result (section / item / value)."""
    rows = outcome.as_rows()
    if _is_excel(path):
        return excel_io.write_xlsx(
            path, ["section", "item", "value"], rows, overwrite=overwrite, sheet_name="Result"
        )
    return csv_io.write_csv(path, ["section", "item", "value"], rows, overwrite=overwrite)


def import_bom(path: str, state: AppState) -> Outcome:
    """Load a BOM file and make it the session BOM used by the Materials and Production screens."""
    bom = excel_io.read_bom_xlsx(path) if _is_excel(path) else csv_io.read_bom_csv(path)
    rows: List[List[str]] = [
        [i.material_id, format(i.quantity_per_unit, "f"), i.unit, format(i.wastage_percent, "f"), i.name]
        for i in bom.items
    ]
    state.bom_rows = rows
    state.changed()
    return Outcome(
        title="BOM imported",
        headline="%d material(s) loaded" % len(rows),
        summary="Imported BOM with %d material(s) from %s" % (len(rows), os.path.basename(path)),
    )
