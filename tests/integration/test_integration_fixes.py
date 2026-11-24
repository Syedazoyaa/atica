"""Regression and edge-case tests for the CSV / Excel integrations."""

import pytest

from atica.core import IntegrationError
from atica.integrations import bom_from_rows, convert_rows
from atica.integrations.csv import convert_csv, read_bom_csv, read_csv, write_csv

openpyxl = pytest.importorskip("openpyxl")

from atica.integrations.excel import (  # noqa: E402
    convert_xlsx,
    read_bom_xlsx,
    read_xlsx,
    write_xlsx,
)


def make_xlsx(path, rows, sheet="Data"):
    book = openpyxl.Workbook()
    book.active.title = sheet
    for row in rows:
        book.active.append(row)
    book.save(path)
    return path


class TestCsvEdgeCases:
    def test_quoted_commas_and_embedded_newlines_survive(self, tmp_path):
        src = tmp_path / "in.csv"
        src.write_bytes(  # bytes: write_text would turn the embedded newline into CRLF on Windows
            b'value,from_unit,to_unit,note\n1,kg,g,"steel, grade 2"\n2,kg,g,"line one\nline two"\n3,kg,m,"bad, row"\n'
        )
        _, rows, numbers = read_csv(src)
        assert rows[0]["note"] == "steel, grade 2" and rows[1]["note"] == "line one\nline two"
        # a record with an embedded newline spans two physical lines: the *last* line number is reported
        assert numbers == [2, 4, 5]
        report = convert_csv(src)
        assert [e.row_number for e in report.errors] == [5]
        out = write_csv(tmp_path / "out.csv", report.fieldnames, list(report.rows))
        again = read_csv(out)[1]
        assert again[1]["note"] == "line one\nline two" and again[0]["note"] == "steel, grade 2"

    def test_utf8_bom_and_non_ascii(self, tmp_path):
        src = tmp_path / "in.csv"
        src.write_bytes("value,from_unit,to_unit,note\n1,kg,g,Müller GmbH – Stahl\n".encode("utf-8-sig"))
        _, rows, _ = read_csv(src)
        assert rows[0]["note"] == "Müller GmbH – Stahl"
        out = write_csv(tmp_path / "o.csv", ["a"], [{"a": "Ünïcode ✓"}])
        assert read_csv(out)[1][0]["a"] == "Ünïcode ✓"

    def test_latin1_file_is_reported_not_garbled(self, tmp_path):
        src = tmp_path / "in.csv"
        src.write_bytes("value,from_unit,to_unit,note\n1,kg,g,Müller\n".encode("latin-1"))
        with pytest.raises(IntegrationError, match="UTF-8"):
            read_csv(src)

    def test_populated_cell_under_a_blank_header_is_refused(self, tmp_path):
        src = tmp_path / "in.csv"
        src.write_text("value,from_unit,,to_unit\n1,kg,oops,g\n", encoding="utf-8")
        with pytest.raises(IntegrationError, match="no header"):
            read_csv(src)

    def test_blank_header_with_empty_cells_is_harmless(self, tmp_path):
        src = tmp_path / "in.csv"
        src.write_text("value,from_unit,,to_unit\n1,kg,,g\n", encoding="utf-8")
        assert convert_csv(src).rows[0]["result_value"] == "1000"

    def test_missing_and_duplicate_headers_and_extra_columns(self, tmp_path):
        for text, message in (
            ("value,from_unit\n1,kg\n", "to_unit"),
            ("value,Value,to_unit\n1,2,g\n", "Duplicate"),
            ("value,from_unit,to_unit\n1,kg,g,extra\n", "more cells"),
        ):
            src = tmp_path / "x.csv"
            src.write_text(text, encoding="utf-8")
            with pytest.raises(IntegrationError, match=message):
                convert_csv(src)

    def test_empty_rows_are_skipped_but_numbering_stays_true(self, tmp_path):
        src = tmp_path / "in.csv"
        src.write_text("value,from_unit,to_unit\n\n1,kg,g\n,,\n\n2,kg,m\n3,kg,g\n", encoding="utf-8")
        report = convert_csv(src)
        assert report.row_numbers == (3, 7) and [e.row_number for e in report.errors] == [6]


class TestSourceRowNumbers:
    def test_successful_and_failed_rows_keep_their_source_numbers(self, tmp_path):
        src = tmp_path / "in.csv"
        src.write_text("value,from_unit,to_unit\n1,kg,g\nx,kg,g\n2,kg,g\n3,zz,g\n4,kg,g\n", encoding="utf-8")
        report = convert_csv(src)
        assert report.row_numbers == (2, 4, 6)
        assert [e.row_number for e in report.errors] == [3, 5]
        assert [r["value"] for r in report.rows] == ["1", "2", "4"]
        assert len(report.row_numbers) == report.succeeded

    def test_excel_numbers_are_worksheet_rows(self, tmp_path):
        path = make_xlsx(
            tmp_path / "in.xlsx",
            [
                [None, None, None],
                ["value", "from_unit", "to_unit"],
                [1, "kg", "g"],
                [],
                [2, "kg", "m"],
                [3, "kg", "g"],
            ],
        )
        report = convert_xlsx(path, sheet="Data")
        assert report.row_numbers == (3, 6) and [e.row_number for e in report.errors] == [5]

    def test_in_memory_rows_default_to_positions(self):
        report = convert_rows(
            [
                {"value": "1", "from_unit": "kg", "to_unit": "g"},
                {"value": "x", "from_unit": "kg", "to_unit": "g"},
            ]
        )
        assert report.row_numbers == (1,) and report.errors[0].row_number == 2


class TestExcelNeverDropsData:
    def test_cell_beyond_the_header_width_raises_with_position(self, tmp_path):
        path = make_xlsx(
            tmp_path / "in.xlsx", [["value", "from_unit", "to_unit"], [1, "kg", "g", "SURPRISE"]]
        )
        with pytest.raises(IntegrationError) as info:
            read_xlsx(path)
        assert (
            "Row 2" in info.value.message
            and "column D" in info.value.message
            and "SURPRISE" in info.value.message
        )
        assert info.value.hint

    def test_cell_under_a_blank_header_in_the_middle_raises(self, tmp_path):
        path = make_xlsx(tmp_path / "in.xlsx", [["value", None, "to_unit"], [1, "lost", "g"]])
        with pytest.raises(IntegrationError, match="column B"):
            read_xlsx(path)

    def test_trailing_empty_cells_are_not_data(self, tmp_path):
        path = make_xlsx(tmp_path / "in.xlsx", [["value", "from_unit", "to_unit"], [1, "kg", "g", None, ""]])
        assert read_xlsx(path)[1][0]["to_unit"] == "g"

    def test_conversion_reports_the_problem_instead_of_converting_a_truncated_row(self, tmp_path):
        path = make_xlsx(tmp_path / "in.xlsx", [["value", "from_unit", "to_unit"], [1, "kg", "g", "x"]])
        with pytest.raises(IntegrationError):
            convert_xlsx(path)


class TestExcelFilesAndNames:
    def test_xlsm_cannot_be_written(self, tmp_path):
        with pytest.raises(IntegrationError, match=r"\.xlsx"):
            write_xlsx(tmp_path / "out.xlsm", ["a"], [])
        assert not (tmp_path / "out.xlsm").exists()

    def test_xlsm_can_still_be_read_when_it_is_a_plain_workbook(self, tmp_path):
        path = make_xlsx(tmp_path / "in.xlsx", [["value", "from_unit", "to_unit"], [1, "kg", "g"]])
        macro_named = tmp_path / "in.xlsm"
        macro_named.write_bytes(path.read_bytes())
        assert read_xlsx(macro_named)[1][0]["value"] == "1"

    @pytest.mark.parametrize(
        "name", ["bad/name", "a:b", "x*y", "q?", "[sheet]", "back\\slash", "", "   ", "x" * 32, "'quoted"]
    )
    def test_invalid_worksheet_names_are_rejected_clearly(self, tmp_path, name):
        with pytest.raises(IntegrationError) as info:
            write_xlsx(tmp_path / "o.xlsx", ["a"], [], sheet_name=name)
        assert "worksheet name" in info.value.message and info.value.hint
        assert not (tmp_path / "o.xlsx").exists()

    def test_valid_names_including_the_31_character_limit(self, tmp_path):
        assert write_xlsx(tmp_path / "o.xlsx", ["a"], [{"a": 1}], sheet_name="x" * 31)
        assert openpyxl.load_workbook(tmp_path / "o.xlsx").sheetnames == ["x" * 31]

    def test_missing_sheet_lists_the_available_ones(self, tmp_path):
        path = make_xlsx(
            tmp_path / "in.xlsx", [["value", "from_unit", "to_unit"], [1, "kg", "g"]], sheet="Quantities"
        )
        with pytest.raises(IntegrationError) as info:
            read_xlsx(path, sheet="Nope")
        assert "Quantities" in info.value.hint

    def test_malformed_and_empty_workbooks(self, tmp_path):
        bad = tmp_path / "bad.xlsx"
        bad.write_text("this is not a workbook", encoding="utf-8")
        with pytest.raises(IntegrationError, match="Cannot open"):
            read_xlsx(bad)
        empty = make_xlsx(tmp_path / "empty.xlsx", [])
        with pytest.raises(IntegrationError, match="empty"):
            read_xlsx(empty)

    def test_control_characters_are_reported_not_crashed(self, tmp_path):
        with pytest.raises(IntegrationError, match="cannot be stored") as info:
            write_xlsx(tmp_path / "o.xlsx", ["a"], [{"a": "bad\x00value"}])
        assert info.value.hint and not (tmp_path / "o.xlsx").exists()

    def test_formula_injection_is_neutralised_in_both_formats(self, tmp_path):
        rows = [{"a": "=1+1", "b": "@SUM(A1)", "c": "-5", "d": "+CMD|' /C calc'!A0"}]
        x = write_xlsx(tmp_path / "o.xlsx", ["a", "b", "c", "d"], rows)
        _, back, _ = read_xlsx(x)
        assert back[0]["a"] == "'=1+1" and back[0]["b"] == "'@SUM(A1)" and back[0]["d"].startswith("'+")
        assert back[0]["c"] == "-5"
        c = write_csv(tmp_path / "o.csv", ["a", "b", "c", "d"], rows)
        assert read_csv(c)[1][0]["a"] == "'=1+1"


class TestExportErrors:
    def test_missing_folder(self, tmp_path):
        for write in (write_csv, write_xlsx):
            ext = ".csv" if write is write_csv else ".xlsx"
            with pytest.raises(IntegrationError, match="folder"):
                write(tmp_path / "nope" / ("o" + ext), ["a"], [])

    def test_existing_file_is_protected_and_wrong_extension_refused(self, tmp_path):
        existing = tmp_path / "o.csv"
        existing.write_text("keep me", encoding="utf-8")
        with pytest.raises(IntegrationError, match="already exists"):
            write_csv(existing, ["a"], [])
        assert existing.read_text() == "keep me"
        with pytest.raises(IntegrationError, match="must end with"):
            write_csv(tmp_path / "o.txt", ["a"], [])

    def test_unwritable_target_gives_an_actionable_message(self, tmp_path):
        target = tmp_path / "taken.csv"
        target.mkdir()  # a directory where the file should go: opening it for writing fails
        with pytest.raises(IntegrationError, match="Cannot write"):
            write_csv(target, ["a"], [], overwrite=True)
        folder_as_xlsx = tmp_path / "taken.xlsx"
        folder_as_xlsx.mkdir()
        with pytest.raises(IntegrationError) as info:
            write_xlsx(folder_as_xlsx, ["a"], [], overwrite=True)
        assert info.value.hint


class TestBomNamesAndNumbers:
    def test_names_survive_csv_and_xlsx_import(self, tmp_path):
        src = tmp_path / "bom.csv"
        src.write_text(
            "material_id,quantity_per_unit,unit,wastage_percent,name\nsteel,0.25,kg,2,Structural steel\npaint,40,mL,,\n",
            encoding="utf-8",
        )
        bom = read_bom_csv(src)
        assert [i.name for i in bom.items] == ["Structural steel", ""]
        x = make_xlsx(
            tmp_path / "bom.xlsx",
            [["material_id", "quantity_per_unit", "unit", "name"], ["steel", 0.25, "kg", "Structural steel"]],
        )
        assert read_bom_xlsx(x).items[0].name == "Structural steel"

    def test_bad_row_message_uses_the_source_row_number(self, tmp_path):
        src = tmp_path / "bom.csv"
        src.write_text("material_id,quantity_per_unit,unit\n\nsteel,1,kg\nwood,0,kg\n", encoding="utf-8")
        with pytest.raises(IntegrationError, match="Row 4"):
            read_bom_csv(src)
        x = make_xlsx(
            tmp_path / "bom.xlsx",
            [
                ["material_id", "quantity_per_unit", "unit"],
                ["steel", 1, "kg"],
                [None, None, None],
                ["wood", -1, "kg"],
            ],
        )
        with pytest.raises(IntegrationError, match="Row 4"):
            read_bom_xlsx(x)

    def test_in_memory(self):
        bom = bom_from_rows([{"material_id": "a", "quantity_per_unit": "1", "unit": "kg", "name": "Alpha"}])
        assert bom.items[0].name == "Alpha"
