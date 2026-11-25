"""Design tokens and the Qt stylesheet generator.

Every colour used by the GUI lives in :class:`Theme`; the stylesheet is a template filled from those
tokens and views take icon colours from the same object, so a dark theme later means defining another
``Theme`` instance - no widget code changes.

The ATICA identity is built on five colours, preserved exactly:

====================  =========  ==========================================
``background``        ``#F3F0F2``  soft off-white - the application background
``layer``             ``#E3E4E7``  light grey - controls, sidebar, table headers
``border``            ``#C9CCD2``  cool grey - borders, dividers, structure
``accent``            ``#D9C7C0``  muted warm beige - selected states, accents
``muted``             ``#B8B5B9``  grey mauve - secondary surfaces, drawings
====================  =========  ==========================================

Near-black ``ink`` is used for text and primary actions (contrast); white is used only for inputs
and cards that must stay crisp.  Semantic colours (error / warning / success) appear only where
they carry meaning.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

#: Families in order of preference; IBM Plex Sans is bundled with the package (see ``utils/fonts.py``).
FONT_FAMILY = "IBM Plex Sans"
FONT_STACK = '"IBM Plex Sans", "Segoe UI", "Helvetica Neue", "Noto Sans", Arial, sans-serif'

RESOURCES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")


@dataclass(frozen=True)
class Theme:
    name: str
    # --- the five identity colours
    background: str
    layer: str
    border: str
    accent: str
    muted: str
    # --- neutrals derived for contrast
    surface: str  # white cards and focused inputs
    layer_hover: str
    row_alt: str
    ink: str  # text and primary actions
    ink_secondary: str
    ink_placeholder: str
    ink_inverse: str
    formula: str  # neutral grey for formulas and their explanations
    primary: str
    primary_hover: str
    primary_pressed: str
    # --- semantic (functional communication only)
    error: str
    error_bg: str
    error_border: str
    warning: str
    warning_bg: str
    warning_border: str
    success: str
    success_bg: str
    success_border: str


LIGHT = Theme(
    name="light",
    background="#F3F0F2",
    layer="#E3E4E7",
    border="#C9CCD2",
    accent="#D9C7C0",
    muted="#B8B5B9",
    surface="#FFFFFF",
    layer_hover="#D9DADF",
    row_alt="#F8F6F7",
    ink="#23262B",
    ink_secondary="#50545C",
    ink_placeholder="#5C6068",
    ink_inverse="#F3F0F2",
    formula="#6A6E76",
    primary="#23262B",
    primary_hover="#3A3E46",
    primary_pressed="#101215",
    error="#A2191F",
    error_bg="#FBEDED",
    error_border="#E1B3B6",
    warning="#6B4E00",
    warning_bg="#F8F1DA",
    warning_border="#DDCB8E",
    success="#1E6B3A",
    success_bg="#E4F1E8",
    success_border="#A8D0B4",
)

#: Falcon Informatics brand colours (from its logo) for the two words of the copyright line.
FALCON_BLUE = "#2C75B6"
FALCON_GOLD = "#B88A00"

#: The theme used by Python-side painting (icons, backdrops); the stylesheet gets its own argument.
CURRENT = LIGHT


def asset_url(name: str) -> str:
    """Quoted ``url()`` for a file in ``resources/icons`` (forward slashes, safe for paths with spaces)."""
    path = os.path.join(RESOURCES, "icons", name).replace("\\", "/")
    return 'url("%s")' % path


def build_stylesheet(t: Theme = LIGHT) -> str:
    """Return the application stylesheet for theme ``t``."""
    values = dict(t.__dict__)
    values.update(
        font=FONT_STACK,
        chevron=asset_url("chevron_down.svg"),
        check=asset_url("check.svg"),
    )
    return _TEMPLATE.format(**values)


_TEMPLATE = """
* {{ font-family: {font}; font-size: 15px; color: {ink}; }}
QMainWindow {{ background: {background}; }}
QWidget#content {{ background: transparent; }}
QToolTip {{ background: {ink}; color: {ink_inverse}; border: none; padding: 6px 8px; }}

/* ---------- navigation ---------- */
QLabel#brandTag {{ color: {ink_secondary}; font-size: 12px; }}
QLabel#brandName {{ color: {ink}; font-size: 17px; font-weight: 600; letter-spacing: 0.5px; }}
QLabel#sidebarVersion {{ color: {ink_secondary}; font-size: 12px; }}
QPushButton#navButton {{
    background: transparent; color: {ink_secondary}; border: none; border-left: 3px solid transparent;
    border-radius: 0; text-align: left; padding: 10px 12px; font-weight: 500;
}}
QPushButton#navButton:hover {{ background: {layer_hover}; color: {ink}; }}
QPushButton#navButton:checked {{
    background: {accent}; color: {ink}; font-weight: 600; border-left: 3px solid {ink};
}}
QPushButton#navButton:focus {{ outline: none; border: 2px solid {ink}; }}
QPushButton#navButton[compact="true"] {{ text-align: center; padding: 10px 0; }}

/* ---------- typography ---------- */
QLabel#pageTitle {{ font-size: 25px; font-weight: 600; color: {ink}; }}
QLabel#pageSubtitle {{ font-size: 15px; color: {ink_secondary}; }}
QLabel#cardTitle {{ font-size: 17px; font-weight: 500; color: {ink}; }}
QLabel#sectionLabel {{ font-size: 12px; font-weight: 500; color: {ink_secondary}; letter-spacing: 0.2px; }}
QLabel#muted {{ color: {ink_secondary}; }}
QLabel#formula {{ color: {formula}; }}
QLabel#fieldLabel {{ color: {ink}; font-weight: 500; }}
QLabel#unitSuffix {{ color: {ink_secondary}; }}
QLabel#value {{ color: {ink}; font-weight: 500; }}

/* ---------- surfaces ---------- */
QFrame#card {{ background: {surface}; border: 1px solid {border}; border-radius: 0; }}
QFrame#moduleCard {{ background: {surface}; border: 1px solid {border}; border-radius: 0; }}
QFrame#moduleCard:hover {{ background: {layer}; border: 1px solid {ink}; }}
QLabel#moduleTitle {{ font-size: 16px; font-weight: 500; color: {ink}; background: transparent; }}
QLabel#moduleText {{ color: {ink_secondary}; background: transparent; }}
QLabel#iconBadge {{ background: {layer}; border: 1px solid {border}; border-radius: 0; }}
QFrame#divider {{ background: {border}; max-height: 1px; min-height: 1px; border: none; }}
QFrame#activityRow {{ background: transparent; border: none; border-bottom: 1px solid {border}; }}

/* ---------- inputs ---------- */
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{
    background: {layer}; border: 1px solid transparent; border-bottom: 1px solid {muted}; border-radius: 2px;
    padding: 7px 10px; selection-background-color: {accent}; selection-color: {ink}; min-height: 20px;
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ background: {layer_hover}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{
    background: {surface}; border: 1px solid {ink};
}}
QLineEdit[invalid="true"], QComboBox[invalid="true"] {{
    background: {error_bg}; border: 1px solid {error};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{ background: {background}; color: {ink_placeholder}; }}
QLineEdit[readOnly="true"] {{ background: {background}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{ image: {chevron}; width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {surface}; border: 1px solid {ink}; selection-background-color: {accent}; selection-color: {ink};
    outline: none; padding: 2px;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox:focus {{ outline: none; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {ink_secondary}; border-radius: 0; background: {surface}; }}
QCheckBox::indicator:checked {{ background: {ink}; border: 1px solid {ink}; image: {check}; }}
QCheckBox::indicator:focus {{ border: 2px solid {ink}; }}
QToolButton#moreToggle {{ border: none; color: {ink}; font-weight: 500; padding: 2px 0; }}
QToolButton#moreToggle:focus {{ border: 1px solid {ink}; }}

/* ---------- buttons ---------- */
QPushButton {{
    background: {surface}; color: {ink}; border: 1px solid {muted}; border-radius: 2px; padding: 8px 16px; font-weight: 500;
}}
QPushButton:hover {{ background: {layer}; border: 1px solid {ink_secondary}; }}
QPushButton:pressed {{ background: {border}; }}
QPushButton:focus {{ border: 2px solid {ink}; padding: 7px 15px; }}
QPushButton:disabled {{ color: {ink_placeholder}; background: {layer}; border: 1px solid {border}; }}
QPushButton#primary {{ background: {primary}; color: {ink_inverse}; border: 1px solid {primary}; }}
QPushButton#primary:hover {{ background: {primary_hover}; border: 1px solid {primary_hover}; }}
QPushButton#primary:pressed {{ background: {primary_pressed}; }}
QPushButton#primary:focus {{ border: 2px solid {accent}; padding: 7px 15px; }}
QPushButton#primary:disabled {{ background: {muted}; border: 1px solid {muted}; color: {ink_inverse}; }}
QPushButton#danger {{ color: {error}; padding: 3px 8px; }}
QPushButton#linkButton {{ border: none; background: transparent; color: {ink}; padding: 4px 6px; text-decoration: underline; }}

/* ---------- tabs ---------- */
QTabWidget::pane {{ border: none; background: transparent; top: -1px; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent; color: {ink_secondary}; padding: 9px 16px; margin-right: 2px; border: none;
    border-bottom: 2px solid transparent; font-weight: 500;
}}
QTabBar::tab:hover {{ color: {ink}; background: {layer}; }}
QTabBar::tab:selected {{ color: {ink}; border-bottom: 2px solid {ink}; font-weight: 600; }}
QTabBar::tab:focus {{ border-bottom: 2px solid {ink}; }}

/* ---------- tables ---------- */
QTableWidget, QTableView {{
    background: {surface}; border: 1px solid {border}; border-radius: 0; gridline-color: {border};
    alternate-background-color: {row_alt}; selection-background-color: {accent}; selection-color: {ink};
}}
QTableWidget::item:focus {{ border: 1px solid {ink}; }}
QHeaderView::section {{
    background: {layer}; color: {ink}; padding: 7px 8px; border: none; border-right: 1px solid {border};
    border-bottom: 1px solid {muted}; font-weight: 500;
}}
QTableCornerButton::section {{ background: {layer}; border: none; }}

/* ---------- results & messages ---------- */
QFrame#resultHeadline {{ background: {layer}; border: none; border-left: 4px solid {ink}; border-radius: 0; }}
QLabel#headline {{ font-size: 27px; font-weight: 600; color: {ink}; background: transparent; }}
QLabel#headlineTitle {{ font-size: 12px; font-weight: 500; color: {ink_secondary}; letter-spacing: 0.2px; background: transparent; }}
QFrame#bannerError {{ background: {error_bg}; border: 1px solid {error_border}; border-left: 4px solid {error}; border-radius: 0; }}
QFrame#bannerError QLabel {{ color: {error}; background: transparent; }}
QFrame#bannerWarning {{ background: {warning_bg}; border: 1px solid {warning_border}; border-left: 4px solid {warning}; border-radius: 0; }}
QFrame#bannerWarning QLabel {{ color: {warning}; background: transparent; }}
QFrame#bannerInfo {{ background: {layer}; border: 1px solid {border}; border-left: 4px solid {ink}; border-radius: 0; }}
QFrame#bannerSuccess {{ background: {success_bg}; border: 1px solid {success_border}; border-left: 4px solid {success}; border-radius: 0; }}
QFrame#bannerSuccess QLabel {{ color: {success}; background: transparent; }}

/* ---------- scrolling ---------- */
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QSplitter::handle {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {muted}; border-radius: 2px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {ink_secondary}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {muted}; border-radius: 2px; min-width: 28px; }}
QScrollBar::handle:horizontal:hover {{ background: {ink_secondary}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
"""
