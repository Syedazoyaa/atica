"""Convert a whole CSV file; problem rows are reported, never skipped silently."""

import tempfile
from pathlib import Path

from atica.integrations.csv import convert_csv

with tempfile.TemporaryDirectory() as folder:
    source = Path(folder) / "quantities.csv"
    source.write_text("value,from_unit,to_unit\n25,kg,g\n212,F,C\n1,kg,m\n", encoding="utf-8")

    report = convert_csv(source, output_path=Path(folder) / "converted.csv")
    print(report.succeeded, "converted,", report.failed, "problem(s)")
    for problem in report.errors:
        print(" row", problem.row_number, "-", problem.message)
    assert (report.succeeded, report.failed) == (2, 1)
