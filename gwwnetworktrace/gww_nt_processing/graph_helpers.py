from __future__ import annotations

import os.path

from qgis.core import (
    QgsFeatureRequest,
    QgsProcessingFeedback,
    QgsVectorLayer,
)

from gwwnetworktrace.gww_gis_tools.trace_gis.trace_sewer import (
    DIRECTION,
    Graph,
)


class GraphHelpers:
    @classmethod
    def generate_new_graph(
        cls,
        layer: QgsVectorLayer,
        direction: DIRECTION,
        feedback: QgsProcessingFeedback,
    ) -> Graph:
        feedback.pushInfo(f"{layer.featureCount()} features to graph")

        feature_request = (
            QgsFeatureRequest()
            .setFlags(QgsFeatureRequest.NoGeometry)
            .setSubsetOfAttributes(attrNames=["PIPE_ID", "START_NODE", "END_NODE"], fields=layer.fields())
        )
        features = layer.getFeatures(feature_request)

        graph_fields = ["PIPE_ID", "START_NODE", "END_NODE"]
        feature_data = [dict({k: f[k] for k in graph_fields}, QGIS_FID=f.id()) for f in features]

        graph = Graph(direction).from_dicts(feature_data)

        feedback.pushInfo(f"Generated graph: {graph.direction}")
        return graph

    @classmethod
    def load_graph_from_file(cls, filename) -> Graph:
        graph = Graph.from_file(filename)
        return graph

    @classmethod
    def get_possible_graph_paths(cls, layer: QgsVectorLayer, direction: DIRECTION) -> list[str]:
        source_hash = str(hex(abs(hash(os.path.basename(layer.source())))))[2:]
        filename = f"{source_hash}-{direction.name}.json"
        dirname = os.path.dirname(layer.source())

        # order of custom layer property, layer directory, QGIS settings directory
        return [
            layer.customProperty(value=f"gwwnetworktrace_{direction.name}_graph", defaultValue=""),
            os.path.join(dirname, filename),
            # os.path.join(QgsApplication.qgisSettingsDirPath(), "providers", filename),
        ]

    @classmethod
    def find_graph_file(cls, layer: QgsVectorLayer, direction: DIRECTION) -> str:
        for path in cls.get_possible_graph_paths(layer, direction):
            if os.path.isfile(path):
                return path
        return ""

    @classmethod
    def save_graph(
        cls,
        feedback: QgsProcessingFeedback,
        layer: QgsVectorLayer,
        graph: Graph,
    ) -> str:
        for path in cls.get_possible_graph_paths(layer, graph.direction):
            try:
                graph.to_file(path)
            except Exception as e:
                feedback.pushWarning(f'Failed to save graph to {path=}, {e.args=}')
            else:
                # return successful path
                feedback.pushInfo(f'Saved graph to {path=}')
                return path

        feedback.reportError(
            error='Failed to save graph',
            fatalError=False
        )
        return ""

    @classmethod
    def add_graph_to_layer(
        cls,
        feedback: QgsProcessingFeedback,
        layer: QgsVectorLayer,
        graph: Graph,
        graph_path: str,
    ) -> None:
        key=f"gwwnetworktrace_{graph.direction.name}_graph"
        layer.setCustomProperty(
            key=key,
            value=graph_path
        )
        feedback.pushInfo(f'Graph added to layer metadata: {str(key)}={str(graph_path)}')
