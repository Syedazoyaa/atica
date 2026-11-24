import subprocess
import sys
from decimal import Decimal

import pytest

from atica.core import IntegrationError, MissingDependencyError
from atica.integrations import bom_from_rows, convert_rows
from atica.integrations.csv import convert_csv, read_bom_csv, read_csv, write_csv


def write(path, text, encoding="utf-8"):
    path.write_text(text, encoding=encoding)
    return path


class TestCsv:
    def test_convert_file(self, tmp_path):
        src = write(
            tmp_path / "in.csv", "value,from_unit,to_unit,note\n25,kg,g,a\n212,F,C,b\n1,kg,m,bad\nx,kg,g,\n"
        )
        report = convert_csv(src, output_path=tmp_path / "out.csv")
        assert (report.total_rows, report.succeeded, report.failed) == (4, 2, 2)
        assert [e.row_number for e in report.errors] == [4, 5]  # source line numbers (header is line 1)
        assert report.errors[0].code == "INCOMPATIBLE_UNITS" and report.errors[0].hint
        assert report.rows[0]["result_value"] == "25000" and report.rows[1]["result_value"] == "100"
        _, rows, _ = read_csv(tmp_path / "out.csv")
        assert rows[0]["result_unit"] == "g" and rows[0]["note"] == "a"

    def test_original_rows_untouched_and_columns_preserved(self, tmp_path):
        src = write(tmp_path / "in.csv", "value,from_unit,to_unit,extra\n1,kg,g,keep\n")
        report = convert_csv(src)
        assert report.rows[0]["extra"] == "keep" and report.fieldnames[:4] == (
            "value",
            "from_unit",
            "to_unit",
            "extra",
        )

    def test_rounding_and_custom_registry(self, tmp_path, registry):
        src = write(tmp_path / "in.csv", "value,from_unit,to_unit\n1,bag,lb\n")
        r = convert_csv(src, registry=registry, rounding="half_up", places=2)
        assert r.rows[0]["result_value"] == "55.12"

    def test_custom_column_names(self, tmp_path):
        src = write(tmp_path / "in.csv", "qty,u1,u2\n2,kg,g\n")
        r = convert_csv(src, value_column="qty", from_column="u1", to_column="u2")
        assert r.rows[0]["result_value"] == "2000"

    def test_missing_column_is_whole_file_failure(self, tmp_path):
        src = write(tmp_path / "in.csv", "value,from_unit\n1,kg\n")
        with pytest.raises(IntegrationError) as info:
            convert_csv(src)
        assert "to_unit" in info.value.message

    @pytest.mark.parametrize(
        "content, message",
        [
            ("", "empty"),
            (",,\n1,2,3\n", "no header"),
            ("a,A\n1,2\n", "Duplicate"),
            ("value,from_unit,to_unit\n1,kg,g,extra\n", "more cells"),
        ],
    )
    def test_malformed(self, tmp_path, content, message):
        with pytest.raises(IntegrationError, match="(?i)" + message):
            convert_csv(write(tmp_path / "in.csv", content))

    def test_bad_encoding(self, tmp_path):
        p = tmp_path / "in.csv"
        p.write_bytes(b"value,from_unit,to_unit\n1,\xff\xfe,g\n")
        with pytest.raises(IntegrationError, match="UTF-8"):
            convert_csv(p)

    def test_bom_marker_accepted_and_blank_lines_skipped(self, tmp_path):
        p = tmp_path / "in.csv"
        p.write_bytes("value,from_unit,to_unit\n\n1,kg,g\n".encode("utf-8-sig"))
        assert convert_csv(p).succeeded == 1

    def test_file_checks(self, tmp_path):
        with pytest.raises(IntegrationError, match="not found"):
            read_csv(tmp_path / "none.csv")
        write(tmp_path / "x.txt", "a")
        with pytest.raises(IntegrationError, match="Unsupported"):
            read_csv(tmp_path / "x.txt")

    def test_no_overwrite_by_default(self, tmp_path):
        src = write(tmp_path / "in.csv", "value,from_unit,to_unit\n1,kg,g\n")
        out = write(tmp_path / "out.csv", "precious")
        with pytest.raises(IntegrationError, match="already exists"):
            convert_csv(src, output_path=out)
        assert out.read_text() == "precious"
        convert_csv(src, output_path=out, overwrite=True)
        assert "result_value" in out.read_text(encoding="utf-8-sig")

    def test_output_folder_must_exist(self, tmp_path):
        with pytest.raises(IntegrationError, match="folder"):
            write_csv(tmp_path / "nope" / "o.csv", ["a"], [])

    def test_formula_injection_neutralised(self, tmp_path):
        out = write_csv(
            tmp_path / "o.csv",
            ["a", "n"],
            [{"a": '=HYPERLINK("http://x")', "n": "-5"}, {"a": "@cmd", "n": "+1.5"}],
        )
        _, rows, _ = read_csv(out)
        assert rows[0]["a"].startswith("'=") and rows[1]["a"].startswith("'@")
        assert rows[0]["n"] == "-5" and rows[1]["n"] == "+1.5"  # real numbers are left alone

    def test_row_limit(self, tmp_path):
        src = write(tmp_path / "in.csv", "value,from_unit,to_unit\n" + "1,kg,g\n" * 5)
        with pytest.raises(IntegrationError, match="More than"):
            read_csv(src, max_rows=3)


class TestConvertRows:
    def test_basic_and_errors(self):
        rows = [
            {"value": "1", "from_unit": "kg", "to_unit": "g"},
            {"value": "", "from_unit": "kg", "to_unit": "g"},
            {"value": "1", "from_unit": "zz", "to_unit": "g"},
        ]
        r = convert_rows(rows)
        assert r.succeeded == 1 and r.failed == 2
        assert [e.code for e in r.errors] == ["INTEGRATION_ERROR", "UNKNOWN_UNIT"]

    def test_empty_input(self):
        r = convert_rows([])
        assert (r.total_rows, r.succeeded, r.failed) == (0, 0, 0)


class TestBomFiles:
    def test_read_bom_csv(self, tmp_path):
        p = write(
            tmp_path / "b.csv",
            "material_id,quantity_per_unit,unit,wastage_percent,name\nsteel,0.25,kg,2,Steel\npaint,40,mL,,\n",
        )
        bom = read_bom_csv(p, product_id="P1")
        assert [i.material_id for i in bom.items] == ["steel", "paint"]
        assert (
            bom.items[0].wastage_percent == 2 and bom.items[1].wastage_percent == 0 and bom.product_id == "P1"
        )

    @pytest.mark.parametrize(
        "rows, message",
        [
            ([], "no BOM rows"),
            ([{"material_id": "a"}], "Missing BOM column"),
            ([{"material_id": "a", "quantity_per_unit": "0", "unit": "kg"}], "Row 1"),
            (
                [
                    {"material_id": "a", "quantity_per_unit": "1", "unit": "kg"},
                    {"material_id": "a", "quantity_per_unit": "1", "unit": "kg"},
                ],
                "more than once",
            ),
        ],
    )
    def test_invalid_rows(self, rows, message):
        with pytest.raises(Exception, match=message):
            bom_from_rows(rows)


class TestExcel:
    openpyxl = pytest.importorskip("openpyxl")

    def test_round_trip(self, tmp_path):
        from atica.integrations.excel import convert_xlsx, read_bom_xlsx, read_xlsx, write_xlsx

        p = write_xlsx(
            tmp_path / "in.xlsx",
            ["value", "from_unit", "to_unit"],
            [{"value": "3", "from_unit": "lb", "to_unit": "kg"}],
            sheet_name="Data",
        )
        report = convert_xlsx(p, sheet="Data", output_path=tmp_path / "out.xlsx")
        assert report.rows[0]["result_value"] == "1.36077711"
        fieldnames, rows, _ = read_xlsx(tmp_path / "out.xlsx")
        assert "result_value" in fieldnames and rows[0]["result_unit"] == "kg"
        b = write_xlsx(
            tmp_path / "bom.xlsx",
            ["material_id", "quantity_per_unit", "unit"],
            [{"material_id": "a", "quantity_per_unit": "2", "unit": "kg"}],
        )
        assert read_bom_xlsx(b).items[0].quantity_per_unit == Decimal(2)

    def test_numeric_cells_and_missing_sheet(self, tmp_path):
        from atica.integrations.excel import read_xlsx

        wb = self.openpyxl.Workbook()
        ws = wb.active
        ws.append(["value", "from_unit", "to_unit"])
        ws.append([2.0, "kg", "g"])
        ws.append([1.5, "kg", "g"])
        wb.save(tmp_path / "n.xlsx")
        _, rows, numbers = read_xlsx(tmp_path / "n.xlsx")
        assert [r["value"] for r in rows] == ["2", "1.5"] and numbers == [2, 3]
        with pytest.raises(IntegrationError, match="not found"):
            read_xlsx(tmp_path / "n.xlsx", sheet="Nope")

    def test_corrupt_file(self, tmp_path):
        from atica.integrations.excel import read_xlsx

        bad = write(tmp_path / "bad.xlsx", "not a zip")
        with pytest.raises(IntegrationError):
            read_xlsx(bad)


def test_excel_dependency_is_reported_clearly_when_missing(tmp_path):
    code = (
        "import sys; sys.modules['openpyxl'] = None\n"
        "from atica.integrations.excel import write_xlsx\n"
        "from atica.core import MissingDependencyError\n"
        "try:\n    write_xlsx(r'%s', ['a'], [])\nexcept MissingDependencyError as e:\n    print('OK', e.hint)\n"
        % (tmp_path / "x.xlsx")
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.startswith("OK") and "atica[excel]" in out
    assert issubclass(MissingDependencyError, ImportError)


# ---------------------------------------------------------------- import hygiene
@pytest.mark.parametrize(
    "module",
    [
        "atica",
        "atica.units",
        "atica.packaging",
        "atica.materials",
        "atica.production",
        "atica.quality",
        "atica.purchasing",
        "atica.integrations",
        "atica.integrations.csv",
        "atica.integrations.excel",
    ],
)
def test_core_imports_do_not_load_qt_or_optional_packages(module):
    code = (
        "import sys, importlib\n"
        "importlib.import_module(%r)\n"
        "bad = [m for m in sys.modules if m.split('.')[0] in ('PySide6','PyQt5','PyQt6','openpyxl','numpy','pandas','scipy','pint','sqlalchemy') or m.startswith('atica.gui')]\n"
        "print(','.join(bad))\n" % module
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == "", "unexpected imports: " + out


def test_core_uses_only_the_standard_library():
    """Every third-party import inside the calculation packages would be a hidden dependency."""
    import ast
    import pathlib

    import atica

    root = pathlib.Path(atica.__file__).parent
    if not hasattr(sys, "stdlib_module_names"):
        pytest.skip("sys.stdlib_module_names needs Python 3.10+ (the check runs on the other versions)")
    stdlib = set(sys.stdlib_module_names)
    offenders = []
    for path in root.rglob("*.py"):
        if "gui" in path.relative_to(root).parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                if top in ("atica", "__future__") or top in stdlib:
                    continue
                if top == "openpyxl" and path.name == "excel.py":
                    continue  # the one optional, lazily imported integration
                offenders.append((path.name, name))
    assert not offenders, offenders


def test_no_dynamic_code_execution_in_package():
    import pathlib
    import re

    import atica

    root = pathlib.Path(atica.__file__).parent
    pattern = re.compile(
        r"(?<![\w.])(eval|exec|compile)\(|__import__\(|pickle|os\.system|subprocess|socket|urllib|requests"
    )
    hits = [
        (p.name, m.group(0))
        for p in root.rglob("*.py")
        for m in [pattern.search(p.read_text(encoding="utf-8"))]
        if m
    ]
    assert not hits, hits
