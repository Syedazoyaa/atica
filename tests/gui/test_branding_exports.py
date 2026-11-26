"""Export file naming, branding assets, About page content, theme refinements."""

import datetime
import os
import pathlib
import re

import pytest

from atica.gui import branding as B
from atica.gui.services.exports import sanitize, suggest_filename, unique_path, with_extension

NOW = datetime.datetime(2026, 11, 25, 18, 30, 0)
ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "module, op, ext, expected",
    [
        ("Units", "bulk conversion", "xlsx", "ATICA_UNITS_BULK_CONVERSION_20261125_183000.xlsx"),
        ("BOM", "BOM requirements", "xlsx", "ATICA_MATERIALS_BOM_REQUIREMENTS_20261125_183000.xlsx"),
        ("Production", "capacity", ".csv", "ATICA_PRODUCTION_CAPACITY_20261125_183000.csv"),
        ("Data", "conversion/errors?", "csv", "ATICA_DATA_CONVERSION_ERRORS_20261125_183000.csv"),
        ("", "", "csv", "ATICA_MODULE_RESULT_20261125_183000.csv"),
    ],
)
def test_suggest_filename(module, op, ext, expected):
    assert suggest_filename(module, op, ext, now=NOW) == expected


def test_sanitize_and_default_clock():
    assert sanitize("a/b\\c:d*e") == "A_B_C_D_E"
    assert re.fullmatch(r"ATICA_X_Y_\d{8}_\d{6}\.csv", suggest_filename("x", "y"))


def test_extension_and_no_overwrite(tmp_path):
    assert with_extension("out", "Excel workbook (*.xlsx)") == "out.xlsx"
    assert with_extension("out", "CSV file (*.csv)") == "out.csv"
    assert with_extension("out.csv", "Excel (*.xlsx)") == "out.csv"
    first = tmp_path / "a.csv"
    assert unique_path(str(first)) == str(first)
    first.write_text("x")
    second = unique_path(str(first))
    assert second == str(tmp_path / "a (2).csv")
    pathlib.Path(second).write_text("y")
    assert unique_path(str(first)) == str(tmp_path / "a (3).csv")
    assert first.read_text() == "x"


def test_branding_assets_present_and_metadata():
    assert os.path.isfile(B.logo_path(B.ATICA_LOGO)) and os.path.isfile(B.logo_path(B.FALCON_LOGO))
    assert B.AUTHORS == (
        "Zabiullah Khan",
        "Syeda Zoya",
        "Juveria Talha",
        "Insiya Maryam",
        "RajuKumar Allam",
        "Sasi",
    )
    assert B.COMPANY_EMAILS == ("info@falconinformatics.com", "cs@falconinformatics.com")


@pytest.mark.gui
def test_logos_keep_aspect_and_about_content(qapp):
    from PySide6.QtWidgets import QLabel, QPlainTextEdit

    from atica.gui.services import AppState
    from atica.gui.views.about_view import AboutView

    pm = B.brand_pixmap(B.FALCON_LOGO, 64)
    assert not pm.isNull() and abs(pm.width() / pm.height() - 600 / 169) < 0.05
    assert not B.brand_pixmap(B.ATICA_LOGO, 64).isNull()
    assert B.logo_size(B.ATICA_LOGO, 100)[0] < 200  # transparent margin trimmed (raw is 1.79:1)
    view = AboutView(AppState())
    text = " ".join(lab.text() for lab in view.findChildren(QLabel))
    assert B.PRODUCT_DESCRIPTION == (
        "An integrated toolkit for smarter manufacturing, precision calculations, and industrial workflows."
    )
    assert B.PRODUCT_DESCRIPTION in text
    needles = (*B.AUTHORS, "mailto:info@falconinformatics.com", "mailto:cs@falconinformatics.com")
    for needle in (*needles, B.COMPANY_WEBSITE, B.COMPANY_LINKEDIN, "GPL-3.0", "All rights reserved."):
        assert needle in text, needle
    assert "MIT" not in text
    for removed in ("Environment", "Your data", "SIL Open Font License", "from Python"):
        assert removed not in text, removed
    titles = [lab.text() for lab in view.findChildren(QLabel) if lab.objectName() == "cardTitle"]
    assert titles.index("Company") < titles.index("Authors")
    assert ", ".join(B.AUTHORS) in text
    assert not view.findChildren(QPlainTextEdit)


@pytest.mark.gui
def test_brand_block_text_below_logo(qapp):
    from atica.gui.components.brand import BrandBlock

    block = BrandBlock(64)
    block.resize(200, 120)
    block.show()
    assert block.name.geometry().top() >= block.logo.geometry().bottom() - 1


def test_theme_refinements():
    from atica.gui.styles.theme import LIGHT, build_stylesheet

    css = build_stylesheet(LIGHT)
    assert "letter-spacing: 1px" not in css and "font-size: 15px; color" in css
    assert "QLabel#formula" in css and LIGHT.formula in css


def test_backdrops_are_faint():
    d = pathlib.Path(B.BRANDING_DIR).parent / "backgrounds"
    for f in d.glob("*.svg"):
        ops = [float(x) for x in re.findall(r'stroke-opacity="([0-9.]+)"', f.read_text(encoding="utf-8"))]
        assert ops and max(ops) <= 0.30, f.name


def test_license_is_gpl3():
    lic = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in lic and "Version 3, 29 June 2007" in lic
    assert "MIT License" not in lic
    assert 'license = "GPL-3.0-only"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
