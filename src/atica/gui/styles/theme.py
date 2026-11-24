"""Design tokens and the Qt stylesheet generator.

All colours live in :class:`Theme`; the stylesheet is a template filled from those tokens, so adding
a dark theme later means defining another ``Theme`` instance - no widget code changes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    navy: str  # sidebar / deepest brand colour
    navy_light: str  # sidebar gradient end
    primary: str
    primary_dark: str
    light_blue: str
    pale_blue: str
    surface: str  # cards, inputs
    background: str  # window background
    text: str
    text_secondary: str
    border: str
    danger: str
    danger_bg: str
    warning: str
    warning_bg: str
    success: str
    on_navy: str  # text on the sidebar
    on_navy_muted: str


LIGHT = Theme(
    name="light",
    navy="#102B50",
    navy_light="#16386A",
    primary="#2464A8",
    primary_dark="#1C5190",
    light_blue="#83C9F2",
    pale_blue="#EAF4FC",
    surface="#FFFFFF",
    background="#F5F8FC",
    text="#192B40",
    text_secondary="#64748B",
    border="#DCE6F0",
    danger="#B42318",
    danger_bg="#FEF3F2",
    warning="#8A5A00",
    warning_bg="#FFF8E6",
    success="#1B7F4B",
    on_navy="#FFFFFF",
    on_navy_muted="#A9BFDA",
)

FONT_STACK = '"Segoe UI", "Inter", "Helvetica Neue", "Noto Sans", Arial, sans-serif'


def build_stylesheet(t: Theme = LIGHT) -> str:
    """Return the application stylesheet for theme ``t``."""
    return _TEMPLATE.format(font=FONT_STACK, **t.__dict__)


_TEMPLATE = """
* {{ font-family: {font}; font-size: 13px; color: {text}; }}
QMainWindow, QWidget#page, QWidget#content {{ background: {background}; }}
QToolTip {{ background: {navy}; color: {on_navy}; border: 1px solid {primary}; padding: 6px 8px; border-radius: 6px; }}

/* ---------- sidebar ---------- */
QFrame#sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {navy_light}, stop:0.35 {navy}, stop:1 {navy});
    border: none;
}}
QLabel#brandName {{ color: {on_navy}; font-size: 20px; font-weight: 700; letter-spacing: 3px; }}
QLabel#brandTag {{ color: {on_navy_muted}; font-size: 11px; }}
QFrame#sidebarRule {{ background: rgba(131, 201, 242, 0.18); max-height: 1px; min-height: 1px; border: none; }}
QLabel#sidebarVersion {{ color: {on_navy_muted}; font-size: 11px; }}
QPushButton#navButton {{
    background: transparent; color: {on_navy_muted}; border: none; border-radius: 8px;
    text-align: left; padding: 10px 14px 10px 14px; font-size: 13px; font-weight: 500;
}}
QPushButton#navButton:hover {{ background: rgba(255, 255, 255, 0.08); color: {on_navy}; }}
QPushButton#navButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(131, 201, 242, 0.28), stop:1 rgba(131, 201, 242, 0.08));
    color: {on_navy}; font-weight: 600; border-left: 3px solid {light_blue};
}}
QPushButton#navButton:focus {{ outline: none; background: rgba(255, 255, 255, 0.06); }}

/* ---------- headers ---------- */
QLabel#pageTitle {{ font-size: 24px; font-weight: 700; color: {navy}; }}
QLabel#pageSubtitle {{ font-size: 13px; color: {text_secondary}; }}
QLabel#cardTitle {{ font-size: 15px; font-weight: 600; color: {navy}; }}
QLabel#sectionLabel {{ font-size: 11px; font-weight: 700; color: {text_secondary}; letter-spacing: 1px; }}
QLabel#muted {{ color: {text_secondary}; }}
QLabel#fieldLabel {{ color: {text}; font-weight: 500; }}
QLabel#unitSuffix {{ color: {text_secondary}; }}

/* ---------- cards ---------- */
QFrame#card {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {surface}, stop:1 #FBFDFF);
    border: 1px solid {border}; border-radius: 12px;
}}
QFrame#hero {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {navy}, stop:0.6 {primary_dark}, stop:1 {primary});
    border-radius: 14px; border: 1px solid {primary_dark};
}}
QFrame#hero QLabel {{ color: {on_navy}; background: transparent; }}
QLabel#heroTitle {{ font-size: 26px; font-weight: 700; }}
QLabel#heroText {{ font-size: 13px; color: #D8E8F8; }}
QFrame#moduleCard {{ background: {surface}; border: 1px solid {border}; border-radius: 12px; }}
QFrame#moduleCard:hover {{ border: 1px solid {light_blue}; background: {pale_blue}; }}
QLabel#moduleTitle {{ font-size: 14px; font-weight: 600; color: {navy}; background: transparent; }}
QLabel#moduleText {{ color: {text_secondary}; background: transparent; }}
QLabel#iconBadge {{ background: {pale_blue}; border-radius: 10px; border: 1px solid {border}; }}

/* ---------- inputs ---------- */
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{
    background: {surface}; border: 1px solid {border}; border-radius: 8px; padding: 7px 10px;
    selection-background-color: {light_blue}; selection-color: {navy}; min-height: 20px;
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ border: 1px solid #B9CCE0; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{ border: 1px solid {primary}; background: #FDFEFF; }}
QLineEdit[invalid="true"], QComboBox[invalid="true"] {{ border: 1px solid {danger}; background: {danger_bg}; }}
QLineEdit:disabled, QComboBox:disabled {{ background: {background}; color: {text_secondary}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{
    background: {surface}; border: 1px solid {border}; selection-background-color: {pale_blue}; selection-color: {navy};
    outline: none; padding: 4px;
}}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid #B9CCE0; border-radius: 4px; background: {surface}; }}
QCheckBox::indicator:checked {{ background: {primary}; border: 1px solid {primary_dark}; }}

/* ---------- buttons ---------- */
QPushButton {{
    background: {surface}; color: {navy}; border: 1px solid {border}; border-radius: 8px; padding: 8px 16px; font-weight: 600;
}}
QPushButton:hover {{ background: {pale_blue}; border: 1px solid {light_blue}; }}
QPushButton:pressed {{ background: #DCEBF8; }}
QPushButton:focus {{ border: 1px solid {primary}; }}
QPushButton:disabled {{ color: {text_secondary}; background: {background}; }}
QPushButton#primary {{
    color: #FFFFFF; border: 1px solid {primary_dark};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3A7BC4, stop:0.5 {primary}, stop:1 {primary_dark});
}}
QPushButton#primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4A8AD0, stop:0.5 #2B70B8, stop:1 {primary}); }}
QPushButton#primary:pressed {{ background: {primary_dark}; }}
QPushButton#primary:disabled {{ background: #9DB9D8; border: 1px solid #9DB9D8; color: #FFFFFF; }}
QPushButton#linkButton {{ border: none; background: transparent; color: {primary}; padding: 4px 6px; }}
QPushButton#linkButton:hover {{ color: {primary_dark}; background: transparent; text-decoration: underline; }}

/* ---------- tabs ---------- */
QTabWidget::pane {{ border: none; background: transparent; top: -1px; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent; color: {text_secondary}; padding: 9px 16px; margin-right: 4px; border: none;
    border-bottom: 2px solid transparent; font-weight: 600;
}}
QTabBar::tab:hover {{ color: {navy}; }}
QTabBar::tab:selected {{ color: {primary}; border-bottom: 2px solid {primary}; }}

/* ---------- tables ---------- */
QTableWidget, QTableView {{
    background: {surface}; border: 1px solid {border}; border-radius: 8px; gridline-color: {border};
    alternate-background-color: {background}; selection-background-color: {pale_blue}; selection-color: {navy};
}}
QHeaderView::section {{
    background: {pale_blue}; color: {navy}; padding: 7px 8px; border: none; border-right: 1px solid {border};
    border-bottom: 1px solid {border}; font-weight: 600;
}}
QTableCornerButton::section {{ background: {pale_blue}; border: none; }}

/* ---------- results & messages ---------- */
QFrame#resultHeadline {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {pale_blue}, stop:1 #F4FAFE);
    border: 1px solid {light_blue}; border-radius: 10px;
}}
QLabel#headline {{ font-size: 24px; font-weight: 700; color: {navy}; background: transparent; }}
QLabel#headlineTitle {{ font-size: 11px; font-weight: 700; color: {primary}; letter-spacing: 1px; background: transparent; }}
QFrame#bannerError {{ background: {danger_bg}; border: 1px solid #F4C7C3; border-radius: 8px; }}
QFrame#bannerError QLabel {{ color: {danger}; background: transparent; }}
QFrame#bannerWarning {{ background: {warning_bg}; border: 1px solid #F3DDA6; border-radius: 8px; }}
QFrame#bannerWarning QLabel {{ color: {warning}; background: transparent; }}
QFrame#bannerInfo {{ background: {pale_blue}; border: 1px solid {light_blue}; border-radius: 8px; }}
QFrame#bannerSuccess {{ background: #ECFDF3; border: 1px solid #A6E4C1; border-radius: 8px; }}
QFrame#bannerSuccess QLabel {{ color: {success}; background: transparent; }}
QFrame#divider {{ background: {border}; max-height: 1px; min-height: 1px; border: none; }}

/* ---------- scrollbars ---------- */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C5D5E6; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {light_blue}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #C5D5E6; border-radius: 4px; min-width: 28px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
"""
