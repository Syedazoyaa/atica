"""The GUI controllers must call the real, public ATICA calculation APIs - and contain no formulas."""

import ast
import pathlib
from decimal import Decimal

import pytest

import atica
from atica.core import AticaError
from atica.gui.controllers import (
    data_tools,
    materials_calc,
    packaging_calc,
    production_calc,
    purchasing_calc,
    quality_calc,
    unit_conversion,
)


def spy(monkeypatch, module, name):
    """Wrap ``module.name`` so that calls are recorded and still reach the real implementation."""
    real = getattr(module, name)
    calls = []

    def wrapper(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)

    monkeypatch.setattr(module, name, wrapper)
    return calls


class TestControllersCallTheCore:
    def test_unit_conversion(self, monkeypatch, state):
        import atica.units as units

        calls = spy(monkeypatch, units, "convert")
        out = unit_conversion.convert(
            {"value": "212", "from_unit": "F", "to_unit": "C", "rounding": "none"}, state
        )
        assert len(calls) == 1 and calls[0][0][:3] == ("212", "F", "C")
        assert out.headline == "100 C"

    def test_packaging_breakdown_matches_spec_example(self, monkeypatch, state):
        import atica.packaging as packaging

        calls = spy(monkeypatch, packaging, "breakdown")
        out = packaging_calc.breakdown(
            {"quantity": "250", "from_level": "piece", "to_level": "carton"}, state
        )
        assert len(calls) == 1
        rows = dict(out.rows)
        assert rows["Full carton packages"] == "1" and rows["Remaining quantity"] == "10 piece"
        assert rows["Minimum whole carton needed"] == "2"

    def test_packaging_plan(self, monkeypatch, state):
        import atica.packaging as packaging

        calls = spy(monkeypatch, packaging, "decompose")
        out = packaging_calc.decompose({"quantity": "250", "from_level": "piece"}, state)
        assert len(calls) == 1 and out.headline == "1 carton + 10 piece"

    def test_bom(self, monkeypatch, state):
        import atica.materials as materials

        calls = spy(monkeypatch, materials, "calculate_bom_requirements")
        out = materials_calc.requirements(
            {"production_quantity": "1000", "scrap_percent": "0", "rounding": "none"}, state
        )
        assert len(calls) == 1
        assert out.tables[0].rows[0][:3] == ["steel", "250", "kg"]

    def test_capacity(self, monkeypatch, state):
        import atica.materials as materials

        calls = spy(monkeypatch, materials, "calculate_producible_quantity")
        out = materials_calc.capacity(
            {"scrap_percent": "0", "rounding": "floor", "places": "0"},
            [["steel", "100", "kg"], ["paint", "100", "L"], ["screws", "1000", ""]],
            state,
        )
        assert (
            len(calls) == 1
            and out.headline.startswith("250 units")
            and dict(out.rows)["Limiting material"] == "screws"
        )

    def test_production(self, monkeypatch, state):
        import atica.production as production

        batches = spy(monkeypatch, production, "calculate_batches")
        mats = spy(monkeypatch, production, "calculate_batch_materials")
        out = production_calc.batches(
            {"quantity": "250", "batch_size": "100", "include_materials": True, "rounding": "none"}, state
        )
        assert len(batches) == 1
        assert len(mats) == 1 and out.headline == "3 batch(es) required"
        assert out.tables[0].rows[0] == ["steel", "25", "12.5", "62.5", "kg"]

    def test_production_time_and_capacity(self, monkeypatch, state):
        import atica.production as production

        t = spy(monkeypatch, production, "production_time")
        c = spy(monkeypatch, production, "production_capacity")
        assert (
            production_calc.time(
                {"quantity": "1000", "rate": "250", "per": "h", "unit": "min", "efficiency_percent": "100"},
                state,
            ).headline
            == "240 min"
        )
        assert (
            production_calc.capacity(
                {
                    "rate": "250",
                    "per": "h",
                    "available_time": "8",
                    "time_unit": "h",
                    "rounding": "floor",
                    "places": "0",
                },
                state,
            ).headline
            == "2000 units"
        )
        assert len(t) == 1 and len(c) == 1

    def test_quality(self, monkeypatch, state):
        import atica.quality as quality

        y = spy(monkeypatch, quality, "calculate_yield")
        s = spy(monkeypatch, quality, "calculate_required_input")
        out = quality_calc.yield_(
            {
                "input_quantity": "1000",
                "good_first_pass": "900",
                "sent_to_rework": "60",
                "recovered_from_rework": "45",
            },
            state,
        )
        assert len(y) == 1 and out.headline == "Final yield 94.5 %"
        out = quality_calc.scrap(
            {"mode": "required_input", "good_output": "950", "scrap_percent": "5", "rounding": "none"}, state
        )
        assert len(s) == 1 and out.headline == "1000"

    def test_100_percent_scrap_expected_output_is_zero(self, state):
        out = quality_calc.scrap(
            {"mode": "expected_output", "input_quantity": "500", "scrap_percent": "100", "rounding": "none"},
            state,
        )
        assert out.headline == "0"

    def test_purchasing(self, monkeypatch, state):
        import atica.purchasing as purchasing

        calls = spy(monkeypatch, purchasing, "calculate_purchase_quantity")
        out = purchasing_calc.purchase(
            {
                "required_quantity": "87",
                "unit": "piece",
                "minimum_order_quantity": "24",
                "order_multiple": "12",
                "stock_on_hand": "0",
            },
            state,
        )
        assert len(calls) == 1 and out.headline == "96 piece"

    def test_custom_unit_round_trip(self, state):
        out = unit_conversion.define_unit({"name": "bag", "factor": "25", "reference_unit": "kg"}, state)
        assert out.headline == "1 bag = 25 kg"
        r = unit_conversion.convert(
            {"value": "4", "from_unit": "bag", "to_unit": "kg", "rounding": "none"}, state
        )
        assert r.headline == "100 kg"
        purchase = purchasing_calc.purchase(
            {"required_quantity": "130", "unit": "kg", "purchase_unit": "bag", "order_multiple": "1"}, state
        )
        assert purchase.headline == "6 bag" and dict(purchase.rows)["You will receive"] == "150 kg"

    def test_registry_is_per_session(self, state):
        from atica.gui.services import AppState

        unit_conversion.define_unit({"name": "bag", "factor": "25", "reference_unit": "kg"}, state)
        other = AppState()
        with pytest.raises(AticaError):
            unit_conversion.convert({"value": "1", "from_unit": "bag", "to_unit": "kg"}, other)

    def test_precision_setting_reaches_the_core(self, state):
        state.precision = 10
        r = unit_conversion.convert(
            {"value": "1", "from_unit": "d", "to_unit": "wk", "rounding": "none"}, state
        )
        assert len(r.headline.split()[0].replace(".", "").lstrip("0")) <= 10

    def test_display_places_only_affect_display(self, state):
        state.display_places = 2
        out = production_calc.time({"quantity": "1", "rate": "3", "per": "h", "unit": "h"}, state)
        assert out.headline == "0.33 h"
        state.display_places = 8
        assert (
            production_calc.time({"quantity": "1", "rate": "3", "per": "h", "unit": "h"}, state).headline
            == "0.33333333 h"
        )


class TestErrorsComeFromTheCore:
    def test_invalid_input_raises_core_errors_with_parameter(self, state):
        with pytest.raises(AticaError) as info:
            purchasing_calc.purchase({"required_quantity": "-5"}, state)
        assert info.value.parameter == "required_quantity"

    def test_missing_product(self):
        from atica.gui.services import AppState

        with pytest.raises(AticaError, match="No packaging hierarchy"):
            packaging_calc.breakdown({"quantity": "1", "from_level": "a", "to_level": "b"}, AppState())

    def test_blank_required_field(self, state):
        with pytest.raises(AticaError) as info:
            unit_conversion.convert({"value": "", "from_unit": "kg", "to_unit": "g"}, state)
        assert info.value.parameter == "value"

    def test_incompatible_units(self, state):
        with pytest.raises(AticaError) as info:
            unit_conversion.convert({"value": "1", "from_unit": "kg", "to_unit": "m"}, state)
        assert info.value.code == "INCOMPATIBLE_UNITS"

    def test_bom_without_rows(self):
        from atica.gui.services import AppState

        with pytest.raises(AticaError, match="no materials"):
            materials_calc.requirements({"production_quantity": "1"}, AppState())

    def test_capacity_requires_every_material(self, state):
        with pytest.raises(AticaError, match="steel"):
            materials_calc.capacity({"rounding": "floor", "places": "0"}, [["steel", "", "kg"]], state)


class TestDataTools:
    def test_convert_and_export(self, state, tmp_path):
        src = tmp_path / "in.csv"
        src.write_text("value,from_unit,to_unit\n25,kg,g\n1,kg,m\n", encoding="utf-8")
        report = data_tools.convert_file(str(src), {"rounding": "none"}, state)
        assert (report.succeeded, report.failed) == (1, 1)
        out = data_tools.export_report(report, str(tmp_path / "out.csv"))
        err = data_tools.export_errors(report, str(tmp_path / "err.csv"))
        assert "25000" in pathlib.Path(out).read_text(encoding="utf-8-sig")
        assert "INCOMPATIBLE_UNITS" in pathlib.Path(err).read_text(encoding="utf-8-sig")

    def test_import_bom_sets_session_bom(self, state, tmp_path):
        src = tmp_path / "bom.csv"
        src.write_text("material_id,quantity_per_unit,unit\nresin,2,kg\n", encoding="utf-8")
        data_tools.import_bom(str(src), state)
        assert state.bom_rows == [["resin", "2", "kg", "0"]]
        out = materials_calc.requirements({"production_quantity": "10", "rounding": "none"}, state)
        assert out.tables[0].rows[0][:3] == ["resin", "20", "kg"]

    def test_export_outcome_structured(self, state, tmp_path):
        outcome = purchasing_calc.purchase(
            {"required_quantity": "87", "unit": "piece", "order_multiple": "12"}, state
        )
        path = data_tools.export_outcome(outcome, str(tmp_path / "r.csv"))
        text = pathlib.Path(path).read_text(encoding="utf-8-sig")
        assert text.splitlines()[0] == "section,item,value" and "96 piece" in text

    def test_excel_export_if_available(self, state, tmp_path):
        pytest.importorskip("openpyxl")
        outcome = purchasing_calc.purchase({"required_quantity": "87", "unit": "piece"}, state)
        assert data_tools.export_outcome(outcome, str(tmp_path / "r.xlsx")).endswith(".xlsx")


# --------------------------------------------------------------- architecture rules
GUI_ROOT = pathlib.Path(atica.__file__).parent / "gui"


def _py_files(*parts):
    return sorted((GUI_ROOT.joinpath(*parts)).rglob("*.py"))


@pytest.mark.parametrize("folder", ["controllers", "services"])
def test_no_arithmetic_in_controllers_and_services(folder):
    """Calculations live in the core. Formatting with ``%`` and string ``+`` is fine; maths is not."""
    forbidden = (ast.Mult, ast.Div, ast.FloorDiv, ast.Pow, ast.Sub, ast.MatMult)
    offenders = []
    for path in _py_files(folder):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.BinOp) and isinstance(node.op, forbidden):
                offenders.append("%s:%d" % (path.name, node.lineno))
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") in (
                "sum",
                "round",
                "pow",
                "divmod",
            ):
                offenders.append("%s:%d call" % (path.name, node.lineno))
    assert not offenders, offenders


def test_gui_does_not_import_private_core_modules():
    """The GUI uses the public API only (atica.units, atica.packaging ... and atica.core)."""
    offenders = []
    for path in _py_files():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            is_absolute_atica = (
                isinstance(node, ast.ImportFrom)
                and node.level == 0
                and (node.module or "").startswith("atica.")
            )
            if is_absolute_atica and any(part.startswith("_") for part in node.module.split(".")):
                offenders.append((path.name, node.module))
    assert not offenders, offenders


def test_core_never_imports_gui():
    """No module outside atica/gui imports the GUI or Qt (docstrings may mention them)."""
    root = pathlib.Path(atica.__file__).parent
    offenders = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if "gui" in rel.parts or path.name == "__main__.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [(node.module or "") + "." + a.name for a in node.names]
                if node.level:  # relative import of a sibling called gui
                    names += [a.name for a in node.names if a.name == "gui"]
            if any(n.startswith(("atica.gui", "PySide6", "gui")) for n in names):
                offenders.append(str(rel))
    assert not offenders, offenders


def test_decimal_results_are_never_formatted_through_float():
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        assert "float(" not in text, path.name


def test_formatting_helper_uses_decimal_exactly():
    from atica.gui.services import AppState, fmt

    s = AppState()
    assert fmt(Decimal("1234567.5"), s) == "1234567.5"  # plain numbers paste into spreadsheets as numbers
    assert fmt(Decimal("-0.1250"), s) == "-0.125"
    assert fmt(None, s) == "n/a"
    s.display_places = 0
    assert fmt(Decimal("2.4"), s) == "2"  # display-only rounding to the chosen places
