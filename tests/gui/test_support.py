"""Error handling, settings storage, parsing and models of the GUI."""

import logging
import pathlib

from atica.core import AticaError
from atica.gui.models import Outcome, ResultTable
from atica.gui.services import AppState
from atica.gui.services.parsing import build_bom, build_product
from atica.gui.services.settings_store import load_settings, save_settings
from atica.gui.utils import errors


def test_describe_translates_core_errors_and_hides_internal_ones(tmp_path):
    friendly = errors.describe(AticaError("Bad input.", parameter="x", hint="Fix x."))
    assert (friendly.message, friendly.hint, friendly.parameter, friendly.unexpected) == (
        "Bad input.",
        "Fix x.",
        "x",
        False,
    )
    other = errors.describe(KeyError("secret internal detail"))
    assert other.unexpected and "secret" not in other.message + (other.hint or "")


def test_logging_goes_to_the_given_folder_and_contains_the_traceback(tmp_path):
    logger = logging.getLogger("atica.gui")
    handlers = list(logger.handlers)
    try:
        path = errors.setup_logging(str(tmp_path / "logs"))
        assert path and path.endswith("atica-gui.log")
        try:
            raise RuntimeError("diagnostic detail")
        except RuntimeError as exc:
            errors.describe(exc)
        for handler in logger.handlers:
            handler.flush()
        text = pathlib.Path(path).read_text(encoding="utf-8")
        assert "diagnostic detail" in text and "Traceback" in text
    finally:
        for handler in list(logger.handlers):
            if handler not in handlers:
                logger.removeHandler(handler)
                handler.close()
        errors._log_file = None


def test_logging_unavailable_is_not_fatal():
    assert errors.setup_logging(None) is None


def test_guard():
    assert errors.guard(lambda: 5) == (5, None)
    value, err = errors.guard(lambda: 1 / 0)
    assert value is None and err.unexpected


def test_settings_round_trip_and_bounds(monkeypatch, tmp_path):
    from PySide6.QtCore import QSettings

    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, str(tmp_path))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    s = AppState()
    s.display_places, s.precision = 3, 80
    save_settings(s)
    loaded = AppState()
    load_settings(loaded)
    assert (loaded.display_places, loaded.precision) == (3, 80)
    s.display_places, s.precision = 99, 1
    save_settings(s)
    load_settings(loaded)
    assert (loaded.display_places, loaded.precision) == (30, 10)  # clamped to the supported range
    s.display_places, s.precision = 6, 50
    save_settings(s)  # leave sane values behind


def test_parsing_product_and_bom():
    product = build_product("P", "A", [["piece", "1"], ["", ""], ["box", "12"]])
    assert product.level_names == ("piece", "box") and str(product.size_of("box")) == "12"
    bom = build_bom([["a", "1", "kg", ""], ["", "", "", ""], ["b", "2", "g", "5"]])
    assert [i.material_id for i in bom.items] == ["a", "b"]
    for bad in ([["piece", "1"], ["box", ""]], []):
        try:
            build_product("P", "A", bad)
        except AticaError as exc:
            assert exc.hint
        else:  # pragma: no cover
            raise AssertionError("expected an error")
    try:
        build_bom([["a", "0", "kg", ""]])
    except AticaError as exc:
        assert exc.message.startswith("BOM row 1")


def test_outcome_text_and_rows():
    outcome = Outcome(
        "T",
        "10 kg",
        [("a", "1")],
        [ResultTable("tbl", ["x", "y"], [["r", "2"]])],
        ["careful"],
        "f = 1",
        ["assume"],
    )
    text = outcome.as_text()
    assert "10 kg" in text and "a: 1" in text and "Formula: f = 1" in text and "Warning: careful" in text
    rows = outcome.as_rows()
    assert rows[0] == {"section": "T", "item": "result", "value": "10 kg"}
    assert {"section": "tbl", "item": "r", "value": "y=2"} in rows
    assert rows[-1]["item"] == "warning"


def test_state_activity_is_capped_and_notifies():
    s = AppState()
    seen = []
    s.on_change(lambda: seen.append(1))
    for i in range(40):
        s.record("t", str(i))
    assert len(s.activity) == 25 and s.activity[0].summary == "39" and len(seen) == 40
    s.clear_activity()
    assert s.activity == []
