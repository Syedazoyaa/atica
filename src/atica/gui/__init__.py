"""ATICA desktop application (PySide6).

The GUI is a presentation layer over the public calculation API: it imports ``atica.units``,
``atica.packaging`` and the other calculation packages, never the other way round.  Importing this
package does not import Qt; launch the application with the ``atica-gui`` command, ``python -m atica``
or :func:`atica.gui.app.main`.
"""

from atica.version import __version__

__all__ = ["__version__"]
