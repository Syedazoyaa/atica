import csv

import pytest

from atica.exceptions import BulkProcessingError
from atica.io import (
    export_errors,
    export_results,
    map_columns,
    process_file,
    process_rows,
    read_csv,
    read_xlsx,
    write_csv,
    write_xlsx,
)

SPEC_CSV = (
    "Product,Quantity,From Unit,To Unit\n"
    "Product A,100,kg,g\n"
    "Product B,50,carton,pallet\n"
    "Product C,250,mm,m\n"
)


def write(tmp_path, text, name="in.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def test_spec_example(tmp_path, product_b):
    bulk = process_file(write(tmp_path, SPEC_CSV), products=[product_b])
    assert bulk.summary == {"total_rows": 3, "succeeded": 3, "failed": 0, "stopped_early": False,
                            "source": str(tmp_path / "in.csv")}
    a, b, c = bulk.rows
    assert a.output["result_quantity"] == "100000" and a.output["result_unit"] == "g"
    assert b.output["operation"] == "breakdown" and b.output["full_packages"] == "1"
    assert b.output["remaining_quantity"] == "0 carton"
    assert c.output["result_quantity"] == "0.25"
    # product A / C are not configured: physical conversion works but warns
    assert a.warnings and not b.warnings


def test_row_errors_do_not_corrupt_other_rows(tmp_path, product_b):
    text = (
        "Product,Quantity,From Unit,To Unit\n"
        "P1,10,kg,g\n"
        "P2,abc,kg,g\n"
        "P3,10,kg,m\n"
        "P4,10,kg,nonsense\n"
        "P5,,kg,g\n"
        "Product B,10,carton,kg\n"
        "Ghost,10,carton,pallet\n"
        "P8,5,kg,g\n"
    )
    bulk = process_file(write(tmp_path, text), products=[product_b])
    assert [r.ok for r in bulk.rows] == [True, False, False, False, False, False, False, True]
    codes = [r.errors[0]["code"] if r.errors else None for r in bulk.rows]
    assert codes == [None, "INVALID_NUMBER", "INCOMPATIBLE_UNITS", "UNKNOWN_UNIT", "EMPTY_VALUE",
                     "INCOMPATIBLE_UNITS", "UNKNOWN_PRODUCT", None]
    assert bulk.rows[0].output["result_quantity"] == "10000"
    assert bulk.rows[7].output["result_quantity"] == "5000"
    assert bulk.summary["failed"] == 6
    # row numbers are file line numbers (header = line 1)
    assert [r.row_number for r in bulk.rows] == [2, 3, 4, 5, 6, 7, 8, 9]


def test_original_data_preserved(tmp_path):
    bulk = process_file(write(tmp_path, SPEC_CSV))
    assert bulk.rows[0].original == {"Product": "Product A", "Quantity": "100", "From Unit": "kg", "To Unit": "g"}
    assert bulk.fieldnames == ["Product", "Quantity", "From Unit", "To Unit"]


def test_error_policies(tmp_path):
    text = "Quantity,From Unit,To Unit\n1,kg,g\n1,kg,m\n1,kg,g\n"
    path = write(tmp_path, text)
    assert len(process_file(path).rows) == 3
    stopped = process_file(path, on_error="stop")
    assert len(stopped.rows) == 2 and stopped.stopped_early
    with pytest.raises(BulkProcessingError) as e:
        process_file(path, on_error="raise")
    assert e.value.code == "INCOMPATIBLE_UNITS"
    with pytest.raises(BulkProcessingError):
        process_file(path, on_error="whatever")


def test_missing_columns_fail_the_whole_file(tmp_path):
    path = write(tmp_path, "Product,Quantity,From Unit\nA,1,kg\n")
    with pytest.raises(BulkProcessingError) as e:
        process_file(path)
    assert e.value.code == "MISSING_COLUMN" and "to_unit" in e.value.message


def test_column_mapping_and_aliases(tmp_path):
    path = write(tmp_path, "item;qty;a;b\n".replace(";", ",") + "x,2,kg,g\n")
    with pytest.raises(BulkProcessingError):
        process_file(path)
    bulk = process_file(path, column_map={"from_unit": "a", "to_unit": "b"})
    assert bulk.rows[0].output["result_quantity"] == "2000"
    assert map_columns(["SKU", "QTY", "From_Unit", "to unit"]) == {
        "product": "SKU", "quantity": "QTY", "from_unit": "From_Unit", "to_unit": "to unit"}
    with pytest.raises(BulkProcessingError):
        map_columns(["a"], {"bogus": "a"})
    with pytest.raises(BulkProcessingError):
        map_columns(["Quantity", "From Unit", "To Unit"], {"product": "Nope"})


def test_extra_cells_are_rejected_not_dropped(tmp_path):
    bulk = process_file(write(tmp_path, "Quantity,From Unit,To Unit\n1,kg,g,SURPRISE\n"))
    assert bulk.rows[0].errors[0]["code"] == "TOO_MANY_COLUMNS"


def test_blank_lines_skipped_and_short_rows_flagged(tmp_path):
    bulk = process_file(write(tmp_path, "Quantity,From Unit,To Unit\n\n,,\n1,kg\n"))
    assert len(bulk.rows) == 1 and bulk.rows[0].errors[0]["code"] == "EMPTY_VALUE"


def test_ambiguous_product(tmp_path, product_a):
    from conftest import build_product

    twin = build_product("OTHER", "Product A", 6, 6, 6)
    path = write(tmp_path, "Product,Quantity,From Unit,To Unit\nProduct A,5,carton,pallet\nPROD-A,5,carton,pallet\n")
    bulk = process_file(path, products=[product_a, twin])
    assert bulk.rows[0].errors[0]["code"] == "AMBIGUOUS_PRODUCT"
    assert bulk.rows[1].ok


def test_fractional_packages_need_opt_in(tmp_path, product_a):
    path = write(tmp_path, "Product,Quantity,From Unit,To Unit\nPROD-A,850.5,carton,pallet\n")
    assert process_file(path, products=[product_a]).rows[0].errors[0]["code"] == "PARTIAL_NOT_ALLOWED"
    assert process_file(path, products=[product_a], allow_partial=True).rows[0].ok


def test_precision_option(tmp_path):
    path = write(tmp_path, "Quantity,From Unit,To Unit\n1,minute,hour\n")
    assert process_file(path, precision=3).rows[0].output["result_quantity"] == "0.017"


def test_export_results_and_errors(tmp_path, product_b):
    text = SPEC_CSV + "Bad,1,kg,m\n"
    bulk = process_file(write(tmp_path, text), products=[product_b])
    ok_path = export_results(bulk, tmp_path / "out.csv")
    rows = read_rows(ok_path)
    assert len(rows) == 3 and rows[0]["result_quantity"] == "100000" and rows[0]["Product"] == "Product A"
    err_path = export_errors(bulk, tmp_path / "errors.csv")
    errs = read_rows(err_path)
    assert len(errs) == 1 and errs[0]["error_code"] == "INCOMPATIBLE_UNITS" and errs[0]["row_number"] == "5"


def test_export_never_overwrites_silently(tmp_path):
    bulk = process_file(write(tmp_path, SPEC_CSV))
    out = tmp_path / "out.csv"
    export_results(bulk, out)
    with pytest.raises(BulkProcessingError) as e:
        export_results(bulk, out)
    assert e.value.code == "FILE_EXISTS"
    export_results(bulk, out, overwrite=True)
    with pytest.raises(BulkProcessingError):
        export_results(bulk, tmp_path / "missing_dir" / "x.csv")
    with pytest.raises(BulkProcessingError):
        export_results(bulk, tmp_path / "x.txt")


def test_export_result_column_collisions(tmp_path):
    path = write(tmp_path, "Quantity,From Unit,To Unit,result_quantity\n1,kg,g,keep-me\n")
    out = export_results(process_file(path), tmp_path / "o.csv")
    row = read_rows(out)[0]
    assert row["result_quantity"] == "keep-me" and row["result_quantity_atica"] == "1000"


def test_formula_injection_neutralised_on_export(tmp_path):
    path = write(tmp_path, 'Product,Quantity,From Unit,To Unit\n"=HYPERLINK(""http://x"")",1,kg,g\n-5,1,kg,g\n')
    out = export_results(process_file(path), tmp_path / "o.csv")
    rows = read_rows(out)
    assert rows[0]["Product"].startswith("'=")
    assert rows[1]["Product"] == "-5"  # plain negative numbers are untouched


def test_file_validation(tmp_path):
    with pytest.raises(BulkProcessingError) as e:
        process_file(tmp_path / "nope.csv")
    assert e.value.code == "FILE_NOT_FOUND"
    (tmp_path / "e.csv").write_text("")
    with pytest.raises(BulkProcessingError) as e:
        read_csv(tmp_path / "e.csv")
    assert e.value.code == "EMPTY_FILE"
    (tmp_path / "x.dat").write_text("a")
    with pytest.raises(BulkProcessingError) as e:
        process_file(tmp_path / "x.dat")
    assert e.value.code == "UNSUPPORTED_FILE_TYPE"
    (tmp_path / "bin.csv").write_bytes(b"\xff\xfe\x00bad\x80")
    with pytest.raises(BulkProcessingError) as e:
        read_csv(tmp_path / "bin.csv", encoding="utf-8")
    assert e.value.code == "ENCODING_ERROR"
    with pytest.raises(BulkProcessingError) as e:
        read_csv(write(tmp_path, "a,a\n1,2\n", "dup.csv"))
    assert e.value.code == "DUPLICATE_COLUMN"


def test_row_limit_protects_resources(tmp_path):
    path = write(tmp_path, "Quantity,From Unit,To Unit\n" + "1,kg,g\n" * 6)
    with pytest.raises(BulkProcessingError) as e:
        read_csv(path, max_rows=5)
    assert e.value.code == "TOO_MANY_ROWS"


def test_process_rows_from_dicts():
    bulk = process_rows([{"Quantity": "3", "From Unit": "kg", "To Unit": "g"}])
    assert bulk.rows[0].output["result_quantity"] == "3000" and bulk.rows[0].row_number == 1


def test_excel_round_trip(tmp_path, product_b):
    pytest.importorskip("openpyxl")
    src = tmp_path / "in.xlsx"
    write_xlsx(src, ["Product", "Quantity", "From Unit", "To Unit"],
               [{"Product": "Product B", "Quantity": 100, "From Unit": "carton", "To Unit": "pallet"},
                {"Product": "x", "Quantity": 2.5, "From Unit": "kg", "To Unit": "g"}])
    table = read_xlsx(src)
    assert table.rows[0]["Quantity"] == "100" and table.rows[1]["Quantity"] == "2.5"
    bulk = process_file(src, products=[product_b])
    assert bulk.rows[0].output["full_packages"] == "2" and bulk.rows[1].output["result_quantity"] == "2500"
    out = export_results(bulk, tmp_path / "out.xlsx")
    assert read_xlsx(out).rows[0]["full_packages"] == "2"
    with pytest.raises(BulkProcessingError):
        read_xlsx(src, sheet="Nope")
    (tmp_path / "bad.xlsx").write_text("not a zip")
    with pytest.raises(BulkProcessingError):
        read_xlsx(tmp_path / "bad.xlsx")


def test_write_csv_direct(tmp_path):
    p = write_csv(tmp_path / "w.csv", ["a", "b"], [{"a": 1, "b": "=1+1"}])
    assert read_rows(p) == [{"a": "1", "b": "'=1+1"}]
