"""Regression tests for the 0.5.0 test report, plus the window identity and start-up state."""

import re

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox, QLabel

from atica.core import IntegrationError
from atica.gui import branding
from atica.gui.components import CalculatorPanel
from atica.gui.styles import LIGHT, build_stylesheet
from atica.gui.styles.theme import FALCON_BROWN
from atica.integrations import csv as csv_io
from atica.integrations import excel as excel_io


def settle():
    for _ in range(3):
        QApplication.processEvents()


def wheel(widget, steps=-1):
    centre = QPointF(widget.rect().center())
    event = QWheelEvent(
        centre,
        QPointF(widget.mapToGlobal(widget.rect().center())),
        QPoint(0, 0),
        QPoint(0, 120 * steps),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(widget, event)
    settle()


def panels(window, name):
    if name == "units":
        return [window.views["units"].convert_panel]
    return window.views[name].findChildren(CalculatorPanel)


# ------------------------------------------------------------------ 1. mouse wheel over drop-downs
class TestWheelOverDropDowns:
    def test_no_closed_drop_down_on_any_screen_changes(self, window):
        checked = 0
        for key, view in window.views.items():
            window.navigate(key)
            for combo in view.findChildren(QComboBox):
                if combo.count() < 2:
                    continue
                combo.setFocus()
                before = combo.currentIndex()
                for steps in (-1, 1, -3):
                    wheel(combo, steps)
                assert combo.currentIndex() == before, (key, combo.objectName())
                checked += 1
        assert checked > 20

    def test_a_closed_list_passes_the_wheel_on_and_an_open_list_keeps_it(self, window, monkeypatch):
        # "ignored and filtered" is what makes Qt hand a real wheel event to the surrounding scroll area
        # (synthetic events are not propagated, so scrolling itself cannot be simulated here)
        from atica.gui.utils.wheel_guard import ComboWheelGuard

        guard = QApplication.instance().findChild(ComboWheelGuard)
        combo = window.views["production"].capacity.form.widget("time_unit")
        event = QWheelEvent(
            QPointF(1, 1), QPointF(1, 1), QPoint(0, 0), QPoint(0, -120), Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False,
        )  # fmt: skip
        event.accept()
        assert guard.eventFilter(combo, event) is True and not event.isAccepted()
        monkeypatch.setattr(combo.view(), "isVisible", lambda: True)
        assert guard.eventFilter(combo, event) is False


# ------------------------------------------------------------------ 2. stale validation messages
class TestValidationMessagesFollowTheInput:
    def test_editing_the_field_in_error_removes_the_message(self, window):
        panel = window.views["purchasing"].panel
        panel.form.set_values({"required_quantity": "abc"})
        panel.calculate()
        assert not panel.error_banner.isHidden()
        panel.form.set_values({"required_quantity": "12"})
        assert panel.error_banner.isHidden()

    def test_editing_an_unrelated_field_keeps_it(self, window):
        panel = window.views["purchasing"].panel
        panel.form.set_values({"required_quantity": "abc"})
        panel.calculate()
        panel.form.set_values({"stock_on_hand": "3"})
        assert not panel.error_banner.isHidden()

    def test_every_field_named_in_the_message_counts(self, window):
        panel = window.views["quality"].yield_panel
        panel.form.set_values({"good_first_pass": "990"})
        panel.calculate()
        panel.form.set_values({"sent_to_rework": "5"})  # also named by the message
        assert panel.error_banner.isHidden()

    def test_drop_down_that_hides_the_field_removes_the_message(self, window):
        panel = window.views["quality"].scrap
        panel.form.set_values({"good_output": ""})
        panel.calculate()
        assert not panel.error_banner.isHidden()
        panel.form.set_values({"mode": "scrap_percentage"})
        assert panel.error_banner.isHidden()

    def test_table_errors_clear_when_the_table_changes(self, window):
        panel = window.views["materials"].requirements
        view = window.views["materials"]
        view.bom.set_rows([["resin", "", "kg", "0"]])
        panel.calculate()
        assert "BOM row 1: Enter a number for Qty per unit." in panel.error_banner.message_text()
        view.bom.set_rows([["resin", "2", "kg", "0"]])
        assert panel.error_banner.isHidden()


# ------------------------------------------------------------------ 3. stale results
class TestResultsFollowTheInput:
    @pytest.mark.parametrize(
        "screen, key, value",
        [("purchasing", "required_quantity", "7"), ("units", "value", "2"), ("units", "to_unit", "t")],
    )
    def test_changing_an_input_clears_the_result(self, window, screen, key, value):
        panel = panels(window, screen)[0]
        assert panel.calculate() is not None
        panel.form.set_values({key: value})
        assert panel.result.outcome is None

    def test_running_other_calculations_keeps_the_result(self, window):
        first, other = window.views["units"].convert_panel, window.views["purchasing"].panel
        first.calculate()
        other.calculate()
        assert first.result.outcome is not None and other.result.outcome is not None

    def test_importing_a_bom_clears_the_results_that_used_it(self, window, tmp_path):
        materials, production = window.views["materials"], window.views["production"]
        production.batches.form.set_values({"include_materials": True})
        assert materials.requirements.calculate() and production.batches.calculate()
        unrelated = window.views["units"].convert_panel
        unrelated.calculate()
        path = tmp_path / "bom.csv"
        path.write_text("material_id,quantity_per_unit,unit\nresin,2,kg\n", encoding="utf-8")
        window.views["data"].import_bom(str(path))
        assert materials.requirements.result.outcome is None
        assert production.batches.result.outcome is None
        assert unrelated.result.outcome is not None

    def test_editing_the_bom_table_clears_the_requirements(self, window):
        materials = window.views["materials"]
        assert materials.requirements.calculate()
        materials.bom.set_rows([["resin", "2", "kg", "0"]])
        assert materials.requirements.result.outcome is None

    def test_a_new_packaging_hierarchy_clears_packaging_results(self, window):
        packaging = window.views["packaging"]
        assert packaging.breakdown.calculate()
        packaging.levels.set_rows([["piece", "1"], ["box", "10"], ["carton", "5"]])
        assert packaging.hierarchy.calculate()
        assert packaging.breakdown.result.outcome is None
        assert packaging.hierarchy.result.outcome is not None

    def test_a_new_file_or_option_clears_the_file_conversion(self, window, tmp_path):
        view = window.views["data"]
        path = tmp_path / "v.csv"
        path.write_text("value,from_unit,to_unit\n1,kg,g\n1,kg,m\n", encoding="utf-8")
        for change in (
            lambda: view.set_file(str(path)),
            lambda: view._form.set_values({"rounding": "half_up"}),
        ):
            view.set_file(str(path))
            view._convert()
            assert view._table.rowCount() == 2 and view._export_results.isEnabled()
            change()
            assert view._table.rowCount() == 0 and view._banner.isHidden()
            assert not view._export_results.isEnabled() and not view._export_errors.isEnabled()


# ------------------------------------------------------------------ 4. every bad BOM row is reported
BAD_BOM = [
    ["material_id", "quantity_per_unit", "unit", "wastage_percent"],
    ["steel", "1", "kg", "0"],
    ["resin", "abc", "kg", "0"],
    ["dye", "2", "g", "150"],
    ["", "", "kg", "0"],
]


class TestBomImportReportsEveryRow:
    @pytest.mark.parametrize("suffix", ["csv", "xlsx"])
    def test_all_rows_and_fields_are_listed(self, tmp_path, suffix):
        path = tmp_path / ("bom." + suffix)
        if suffix == "csv":
            path.write_text("\n".join(",".join(r) for r in BAD_BOM) + "\n", encoding="utf-8")
            read = csv_io.read_bom_csv
        else:
            openpyxl = pytest.importorskip("openpyxl")
            book = openpyxl.Workbook()
            for row in BAD_BOM:
                book.active.append(row)
            book.save(path)
            read = excel_io.read_bom_xlsx
        with pytest.raises(IntegrationError) as info:
            read(path)
        errors = info.value.errors
        assert [(e.row_number, re.match(r"\w+", e.message)[0]) for e in errors] == [
            (3, "quantity_per_unit"),
            (4, "wastage_percent"),
            (5, "material_id"),
            (5, "quantity_per_unit"),
        ]
        for number in (3, 4, 5):
            assert "Row %d:" % number in info.value.message
        assert "Pass an int" not in str(info.value)

    def test_nothing_is_imported_and_the_screen_lists_the_rows(self, window, tmp_path):
        path = tmp_path / "bom.csv"
        path.write_text("\n".join(",".join(r) for r in BAD_BOM) + "\n", encoding="utf-8")
        before = [list(r) for r in window.state.bom_rows]
        view = window.views["data"]
        view.import_bom(str(path))
        text = view._bom_error.message_text()
        assert "Row 3:" in text and "Row 4:" in text and "150" in text
        assert window.state.bom_rows == before


# ------------------------------------------------------------------ 5 and 6. wording
class TestPlainMessages:
    @pytest.mark.parametrize(
        "screen, index, key, value, expected",
        [
            ("units", 0, "value", "", "Enter a number for Value."),
            ("units", 0, "value", "abc", "Enter a valid number for Value."),
            ("purchasing", 0, "required_quantity", "", "Enter a number for Quantity required."),
            ("production", 2, "available_time", "", "Enter a number for Available time."),
        ],
    )
    def test_blank_and_invalid_numbers(self, window, screen, index, key, value, expected):
        panel = panels(window, screen)[index]
        panel.form.set_values({key: value})
        assert panel.calculate() is None
        assert expected in panel.error_banner.message_text()

    def test_out_of_range_stays_distinct(self, window):
        panel = window.views["quality"].recovery
        panel.form.set_values({"recovery_percent": "500"})
        panel.calculate()
        text = panel.error_banner.message_text()
        assert "between 0 and 100" in text and "5%%" not in text and "Enter a" not in text

    def test_no_internal_names_or_optional_suffixes(self, window):
        from PySide6.QtWidgets import QLineEdit

        window.views["materials"]._fill_stock()
        seen = 0
        for view in window.views.values():
            for panel in view.findChildren(CalculatorPanel):
                for key, widget in panel.form._widgets.items():
                    if not isinstance(widget, QLineEdit):
                        continue
                    for value in ("", "abc", "-5", "500"):
                        panel.reset()
                        panel.form.set_values({key: value})
                        if panel.calculate() is None:
                            text = panel.error_banner.message_text()
                            assert not re.search(r"\b[a-z]+(_[a-z]+)+\b", text), (key, value, text)
                            assert "(optional)" not in text, (key, value, text)
                            assert "None is not" not in text and "Pass an int" not in text, text
                            seen += 1
        assert seen > 100


# ------------------------------------------------------------------ identity and start-up
class TestIdentityAndStartUp:
    def test_the_application_is_called_atica_with_a_descriptive_footer(self, window):
        assert window.windowTitle() == "ATICA"
        assert window.title_bar.findChild(QLabel, "titleBarTitle").text() == "ATICA"
        assert window.footer.text() == "ATICA - Manufacturing Calculations"
        window.show()
        assert window.footer.isVisible() and window.footer.geometry().bottom() <= window.height()

    def test_company_name_in_the_sidebar_is_dark_chocolate(self, window):
        label = window.sidebar.findChild(QLabel, "sidebarCompany")
        assert label.text() == branding.COMPANY_NAME.upper()
        assert FALCON_BROWN == "#2A1306"
        assert "QLabel#sidebarCompany {{ color: %s" % FALCON_BROWN not in build_stylesheet(LIGHT)  # formatted
        assert "QLabel#sidebarCompany { color: %s" % FALCON_BROWN in build_stylesheet(LIGHT)

    def test_the_window_opens_maximized_not_full_screen(self, window):
        from atica.gui.app import show_main_window

        window.hide()
        show_main_window(window)
        settle()
        assert window.isMaximized() and not window.isFullScreen()
        window.showNormal()
        settle()
        assert not window.isMaximized()
        window.showMinimized()
        settle()
        assert window.isMinimized()
