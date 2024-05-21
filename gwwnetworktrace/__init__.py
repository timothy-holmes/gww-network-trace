import os
from typing import TYPE_CHECKING

from gwwnetworktrace.qgis_plugin_tools.infrastructure.debugging import (
    setup_debugpy,  # noqa F401
    setup_ptvsd,  # noqa F401
    setup_pydevd,  # noqa F401
)

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

debugger = os.environ.get("QGIS_PLUGIN_USE_DEBUGGER", "").lower()
if debugger in {"debugpy", "ptvsd", "pydevd"}:
    locals()["setup_" + debugger]()


def classFactory(iface: "QgisInterface"):  # noqa N802
    from gwwnetworktrace.plugin import Plugin

    return Plugin()
