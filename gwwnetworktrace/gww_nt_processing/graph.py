from __future__ import annotations

import os.path
from typing import Any

from qgis.core import (
    QgsApplication,
    QgsFeatureRequest,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeatureSource,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterVectorLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication

from gwwnetworktrace.gww_gis_tools.trace_gis.trace_sewer import (
    DIRECTION,
    Graph,
)
from gwwnetworktrace.gww_nt_processing.base_alg import BaseAlgorithm


class UpstreamTraceAlgorithm(BaseAlgorithm):
    def __init__(self) -> None:
        super().__init__()

        self._name = "upstream_graph"
        self._display_name = "Generate upstream graph"
        self._group_id = ""
        self._group = ""
        self._short_help_string = ""

    def initAlgorithm(self, config=None):  # noqa N802
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.settings = self.get_settings()

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                name=self.INPUT,
                description=self.tr("Input layer"),
                types=[QgsProcessing.TypeVectorAnyGeometry],
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                name=self.FORCE_GENERATE,
                description=self.tr("Force regenerate Graph"),
                defaultValue=True,
                optional=False,
            )
        )

    def processAlgorithm(  # noqa N802
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict:
        if feedback is None:
            feedback = QgsProcessingFeedback()

        feature_source = self.parameterAsSource(parameters, self.INPUT, context)
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        force_regenerate = self.parameterAsBoolean(parameters, self.FORCE_GENERATE, context)

        graph_path = self.find_graph_file(layer)
        if graph_path and not force_regenerate:
            source_graph = self.load_graph_from_file(graph_path)
        else:
            source_graph = self.generate_new_graph(layer, feature_source, feedback)
            graph_path = self.save_graph(layer=layer, graph=source_graph)

        layer.setCustomProperty(key="gwwnetworktrace_graph", value=graph_path)

        return {self.OUTPUT: graph_path}

    def generate_new_graph(
        self,
        layer: QgsVectorLayer,
        feature_source: QgsProcessingFeatureSource,
        feedback,
    ) -> Graph:
        feedback.pushInfo(f"{feature_source.featureCount()} features loaded")
        feature_request = (
            QgsFeatureRequest()
            .setFlags(QgsFeatureRequest.NoGeometry)
            .setSubsetOfAttributes(attrNames=["PIPE_ID", "START_NODE", "END_NODE"], fields=layer.fields())
        )
        features = feature_source.getFeatures(feature_request)
        graph_fields = ["PIPE_ID", "START_NODE", "END_NODE"]
        feature_data = [{k: f[k] for k in graph_fields} for f in features]

        return Graph(DIRECTION.U).from_dicts(feature_data)

    def load_graph_from_file(self, filename) -> Graph:
        return Graph.from_file(filename)

    def get_possible_graph_paths(self, layer: QgsVectorLayer) -> list[str]:
        filename = str(hex(abs(hash(os.path.basename(layer.source()))))) + ".json"
        dirname = os.path.dirname(layer.source())

        # order of custom layer property, layer directory, QGIS settings directory
        return [
            layer.customProperty(value="gwwnetworktrace_graph", defaultValue=""),
            os.path.join(dirname, filename),
            os.path.join(QgsApplication.qgisSettingsDirPath(), "providers", filename),
        ]

    def find_graph_file(self, layer: QgsVectorLayer) -> str:
        for path in self.get_possible_graph_paths(layer):
            if os.path.isfile(path):
                return path
        return ""

    def save_graph(self, layer: QgsVectorLayer, graph: Graph) -> str:
        for path in self.get_possible_graph_paths(layer):
            try:
                graph.to_file(path)
            except Exception as e:
                pass
                # TODO: warning that file could not be saved
            else:
                # return successful path
                return path

        return ""
