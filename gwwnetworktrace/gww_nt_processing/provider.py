from qgis.core import QgsProcessingProvider

from gwwnetworktrace.gww_nt_processing.trace import UpstreamTraceAlgorithm


class Provider(QgsProcessingProvider):
    def __init__(self) -> None:
        super().__init__()

        self._id = "gwwnetworktrace"
        self._name = "GWW Network Trace"

    def id(self) -> str:
        """The ID of your plugin, used to identify the provider.

        This string should be a unique, short, character only string,
        eg "qgis" or "gdal". This string should not be localised.
        """
        return self._id

    def name(self) -> str:
        """
        The display name of your plugin in Processing.

        This string should be as short as possible and localised.
        """
        return self._name

    def load(self) -> bool:
        self.refreshAlgorithms()
        return True

    def icon(self):
        """
        Returns a QIcon which is used for your provider inside the Processing toolbox.
        """
        return QgsProcessingProvider.icon(self)

    def loadAlgorithms(self) -> None:  # noqa N802
        """
        Adds individual processing algorithms to the provider.
        """
        # upstream_graph = UpstreamGraphAlgorithm()
        # self.addAlgorithm(upstream_graph)

        upstream_trace = UpstreamTraceAlgorithm()
        self.addAlgorithm(upstream_trace)

