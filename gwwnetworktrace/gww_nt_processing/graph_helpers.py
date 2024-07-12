from __future__ import annotations

import os.path

from qgis.core import (
    QgsProcessingFeedback,
    QgsVectorLayer,
)

from gwwnetworktrace.gww_gis_tools.trace_gis.trace_sewer import (
    DIRECTION,
    Graph,
)
from gwwnetworktrace.gww_nt_processing.layer_helpers import (
    LayerData,
    LayerMeta,
)


class GraphHelpers:
    @classmethod
    def generate_new_graph(
        cls,
        layers: list[QgsVectorLayer],
        direction: DIRECTION,
        feedback: QgsProcessingFeedback,
    ) -> Graph:
        feedback.pushInfo(f"{layers[0].featureCount()=} pipe features to graph")

        data = LayerData.get_trace_data(layer=layers[0], layer_type="pipe", fids=True)
        graph = Graph(direction).from_dicts(data)

        if len(layers) == 3:
            feedback.pushInfo(f"{layers[2].featureCount()=} parcel features to graph")
            parcel_data = LayerData.get_trace_data(layer=layers[2], layer_type="parcel", fids=True)  # gid, fid
            parcels_info = {p["GID"]: p["QGIS_FID"] for p in parcel_data}

            feedback.pushInfo(f"{layers[1].featureCount()=} branch features to graph")
            branch_data = LayerData.get_trace_data(
                layer=layers[1], layer_type="branch", fids=False
            )  # pipe_id, prcl_gid
            branch_info = [
                {"PIPE_ID": b["PIPE_ID"], "PARCEL_FID": parcels_info.get(b["PRCL_GID"])}
                for b in branch_data
                if parcels_info.get(b["PRCL_GID"])
            ]
            graph = graph.add_qgis_parcel_ids(branch_info)

        feedback.pushInfo(f"Generated graph: {graph}")
        return graph

    @classmethod
    def load_graph_from_file(cls, filename) -> Graph:
        graph = Graph.from_file(filename)
        return graph

    @classmethod
    def get_possible_graph_paths(cls, layers: list[QgsVectorLayer], direction: DIRECTION) -> list[str]:
        # order of custom layer property, layer directory, QGIS settings directory
        return [
            cls.get_graph_path_custom_property(layers=layers, direction=direction),
            cls.get_default_graph_path(layers=layers, direction=direction),
        ]

    @classmethod
    def get_graph_path_custom_property(cls, layers: list[QgsVectorLayer], direction: DIRECTION) -> str:
        num_layers = len(layers)
        return layers[0].customProperty(
            value=f"gwwnetworktrace_{direction.name}{num_layers}_graph",
            defaultValue="",
        )

    @classmethod
    def get_default_graph_path(cls, layers: list[QgsVectorLayer], direction: DIRECTION) -> str:
        hashes = [LayerMeta.get_layer_source_hash(layer) for layer in layers]
        filename = cls.get_graph_file_name(hashes, direction)
        dirname = os.path.dirname(layers[0].source())
        return os.path.join(dirname, filename)

    @classmethod
    def get_graph_file_name(cls, hashes: list[str], direction: DIRECTION) -> str:
        return "-".join([*hashes, direction.name]) + ".json"

    @classmethod
    def find_graph_file(cls, layers: list[QgsVectorLayer], direction: DIRECTION) -> str:
        for path in cls.get_possible_graph_paths(layers=layers, direction=direction):
            if os.path.isfile(path):
                return path
        return ""

    @classmethod
    def save_graph(
        cls,
        feedback: QgsProcessingFeedback,
        layers: list[QgsVectorLayer],
        graph: Graph,
    ) -> str:
        for path in cls.get_possible_graph_paths(layers=layers, direction=graph.direction):
            try:
                graph.to_file(path)
            except Exception as e:
                feedback.pushWarning(f"Failed to save graph to {path=}, {e.args=}")
            else:
                # return successful path
                feedback.pushInfo(f"Saved graph to {path=}")
                return path

        feedback.reportError(error="Failed to save graph", fatalError=False)
        return ""

    @classmethod
    def add_graph_to_layer(
        cls,
        feedback: QgsProcessingFeedback,
        layers: list[QgsVectorLayer],
        graph: Graph,
        graph_path: str,
    ) -> None:
        key = f"gwwnetworktrace_{graph.direction.name}_graph"
        layers[0].setCustomProperty(key=key, value=graph_path)
        feedback.pushInfo(f"Graph added to layer metadata: {str(key)}={str(graph_path)}")

    @classmethod
    def get_layer_graph(
        cls,
        feedback: QgsProcessingFeedback,
        layers: list[QgsVectorLayer],
        direction: DIRECTION,
        force: bool,
    ) -> Graph:
        """Load graph if found, or generates new graph"""
        graph_path = cls.find_graph_file(layers=layers, direction=direction)

        if graph_path and not force:
            feedback.pushInfo(f"Found graph: {graph_path}")
            graph = cls.load_graph_from_file(graph_path)
        else:
            feedback.pushInfo(f"{graph_path=}, {force=}")
            graph = cls.generate_new_graph(layers=layers, direction=direction, feedback=feedback)
            graph_path = cls.save_graph(feedback=feedback, layers=layers, graph=graph)
            feedback.pushInfo(f"New {graph_path=}, {force=}")

        cls.add_graph_to_layer(feedback=feedback, layers=layers, graph=graph, graph_path=graph_path)

        return graph
