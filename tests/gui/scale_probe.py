"""Run in a subprocess with QT_SCALE_FACTOR set (Windows display scaling emulation); prints problems or OK."""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from layout_checks import check_window

from atica.gui.app import build_window, create_application

app = create_application(["probe"])
window = build_window()
window.show()
scale = float(os.environ.get("QT_SCALE_FACTOR", "1"))
physical_w, physical_h = 1366, 768
problems = check_window(window, round(physical_w / scale), round(physical_h / scale))
print("scale %.2f -> %dx%d logical" % (scale, window.width(), window.height()))
for problem in problems:
    print("PROBLEM", problem)
print("OK" if not problems else "FAILED")
sys.exit(0 if not problems else 1)
