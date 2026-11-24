"""Data Tools screen: source row numbers, export formats, Excel safety and BOM names, through the widgets."""

import pytest
from PySide6.QtWidgets import QFileDialog

import atica.gui.views.data_tools_view as dtv

openpyxl = pytest.importorskip("openpyxl")


def make_xlsx(path, rows):
    book = openpyxl.Workbook()
    for row in rows:
        book.active.append(row)
    book.save(path)
    return str(path)


def table_column(view, column):
    return [view._table.item(r, column).text() for r in range(view._table.rowCount())]


def test_the_table_shows_the_real_source_row_numbers(window, tmp_path):
    view = window.views["data"]
    src = tmp_path / "in.csv"
    # line 1 header, line 2 blank, line 3 ok, line 4 bad unit, line 5 ok, line 6 incompatible
    src.write_bytes(b"value,from_unit,to_unit\n\n1,kg,g\n2,zz,g\n3,lb,kg\n4,kg,m\n")
    view.set_file(str(src))
    view._convert()
    assert table_column(view, 0) == [
        "3",
        "5",
        "4",
        "6",
    ]  # converted rows first (3, 5), then the problems (4, 6)
    assert table_column(view, 1)[:2] == ["Converted", "Converted"]
    assert all(s.startswith("Problem:") for s in table_column(view, 1)[2:])
    assert "2 of 4 row(s) converted" in view._banner.message_text()


def test_excel_rows_are_numbered_like_the_worksheet(window, tmp_path):
    view = window.views["data"]
    path = make_xlsx(
        tmp_path / "in.xlsx",
        [["title"], ["value", "from_unit", "to_unit"], [1, "kg", "g"], [], [2, "kg", "q"]],
    )
    view.set_file(path)
    view._convert()
    # first non-empty row ("title") is the header, so the next one has no value/from_unit/to_unit columns -> file-level error
    assert not view._banner.isHidden()
    path = make_xlsx(
        tmp_path / "ok.xlsx", [["value", "from_unit", "to_unit"], [1, "kg", "g"], [], [2, "kg", "q"]]
    )
    view.set_file(path)
    view._convert()
    assert table_column(view, 0) == ["2", "4"]


def test_a_populated_excel_cell_beyond_the_header_is_reported_not_dropped(window, tmp_path):
    view = window.views["data"]
    view.set_file(
        make_xlsx(tmp_path / "wide.xlsx", [["value", "from_unit", "to_unit"], [1, "kg", "g", "unexpected"]])
    )
    view._convert()
    text = view._banner.message_text()
    assert (
        not view._banner.isHidden()
        and "no header" in text
        and "unexpected" in text
        and view._table.rowCount() == 0
    )


def test_xlsm_is_readable_but_never_offered_for_export():
    assert "*.xlsm" in dtv._file_filter("Data files")  # a workbook saved as .xlsm can be read
    export = dtv._export_filter()
    assert "xlsm" not in export and "*.csv" in export and "*.xlsx" in export


def test_exporting_to_xlsm_is_refused_with_a_clear_message(window, tmp_path, monkeypatch):
    view = window.views["data"]
    src = tmp_path / "in.csv"
    src.write_bytes(b"value,from_unit,to_unit\n1,kg,g\n")
    view.set_file(str(src))
    view._convert()
    target = tmp_path / "out.xlsm"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
    view._export(errors=False)
    assert not target.exists() and ".xlsx" in view._banner.message_text()


@pytest.mark.parametrize(
    "chosen, suffix", [("Excel workbook (*.xlsx)", ".xlsx"), ("CSV file (*.csv)", ".csv")]
)
def test_a_missing_extension_follows_the_chosen_filter(window, tmp_path, monkeypatch, chosen, suffix):
    view = window.views["data"]
    src = tmp_path / "in.csv"
    src.write_bytes(b"value,from_unit,to_unit\n1,kg,g\n")
    view.set_file(str(src))
    view._convert()
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(tmp_path / "result"), chosen))
    )
    view._export(errors=False)
    assert (tmp_path / ("result" + suffix)).exists()


def test_exported_conversions_can_be_read_back_with_their_values(window, tmp_path, monkeypatch):
    view = window.views["data"]
    src = tmp_path / "in.csv"
    src.write_bytes(b"value,from_unit,to_unit\n25,kg,g\n212,F,C\n")
    view.set_file(str(src))
    view._convert()
    out = tmp_path / "out.xlsx"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), "")))
    view._export(errors=False)
    rows = list(openpyxl.load_workbook(out).active.iter_rows(values_only=True))
    assert rows[0][-3:] == ("result_value", "result_unit", "warnings") and [r[3] for r in rows[1:]] == [
        "25000",
        "100",
    ]


def test_bom_names_from_excel_reach_the_materials_editor(window, tmp_path):
    view = window.views["data"]
    path = make_xlsx(
        tmp_path / "bom.xlsx",
        [
            ["material_id", "quantity_per_unit", "unit", "wastage_percent", "name"],
            ["resin", 2, "kg", 5, "Epoxy resin"],
            ["dye", 3, "g", None, None],
        ],
    )
    view.import_bom(path)
    assert window.views["materials"].bom.rows() == [
        ["resin", "2", "kg", "5", "Epoxy resin"],
        ["dye", "3", "g", "0", ""],
    ]
    out = window.views["materials"].requirements
    out.form.set_values({"production_quantity": "10"})
    assert out.calculate().tables[0].rows[0][:3] == ["resin", "21.052632", "kg"]  # 2 x 10 / (1 - 5 %)


def test_bom_with_duplicate_ids_is_rejected_with_a_message(window, tmp_path):
    view = window.views["data"]
    bad = tmp_path / "dup.csv"
    bad.write_bytes(b"material_id,quantity_per_unit,unit\nresin,1,kg\nresin,2,kg\n")
    view.import_bom(str(bad))
    assert not view._bom_error.isHidden() and "more than once" in view._bom_error.message_text()
    assert window.state.bom_rows[0][0] == "steel"  # the previous BOM is untouched


def test_bom_editor_keeps_names_through_a_calculation(window):
    materials = window.views["materials"]
    materials.bom.set_rows([["a", "1", "kg", "0", "Alpha part"]])
    materials.requirements.calculate()
    assert window.state.bom_rows == [["a", "1", "kg", "0", "Alpha part"]]
