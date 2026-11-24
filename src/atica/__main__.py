"""``python -m atica`` starts the desktop application (same as the ``atica-gui`` command)."""

import sys

from atica.gui.app import main

if __name__ == "__main__":
    sys.exit(main())
