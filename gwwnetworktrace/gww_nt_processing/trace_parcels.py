from __future__ import annotations

from typing import Any

from qgis.core import (
    QgsProcessing,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterVectorLayer,
    QgsVectorLayer,
)

from gwwnetworktrace.gww_gis_tools.trace_gis.trace_sewer import (
    DIRECTION,
    Graph,
    Trace,
)
from gwwnetworktrace.gww_nt_processing.base_alg import BaseAlgorithm
from gwwnetworktrace.gww_nt_processing.graph_helpers import GraphHelpers


class TraceAlgorithm(BaseAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    INPUT_PIPES = 'INPUT_PIPES'
    INPUT_BRANCHES = 'INPUT_BRANCHES'
    INPUT_PARCELS = 'INPUT_PARCELS'

    def __init__(self) -> None:
        super().__init__()

        self._name = "trace"
        self._display_name = "Trace network (select pipes and parcels)"
        self._group_id = ""
        self._group = ""
        self._short_help_string = ""

    def initAlgorithm(self, configuration=None):  # noqa N802
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                name=self.INPUT_PIPES,
                description=self.tr("Input layer"),
                types=[QgsProcessing.TypeVectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                name=self.INPUT_BRANCHES,
                description=self.tr("Input layer"),
                types=[QgsProcessing.TypeVectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                name=self.INPUT_PARCELS,
                description=self.tr("Input layer"),
                types=[QgsProcessing.TypeVectorPolygon],
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                name=self.TRACE_DIRECTION,
                description=self.tr('Trace Direction'),
                options=[d.value.upper() for d in DIRECTION],
                allowMultiple=False,
                defaultValue=DIRECTION.U.value,
                optional=False,
                usesStaticStrings=True
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                name=self.FORCE_GENERATE,
                description=self.tr("Force generation of network graph"),
                defaultValue=False,
                optional=False,
            )
        )

        # TODO: add specify custom Graph option

    def processAlgorithm(  # noqa N802
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict:
        # Initialize feedback if it is None
        if feedback is None:
            feedback = QgsProcessingFeedback()

        pipe_layer = self.parameterAsVectorLayer(parameters, self.INPUT_PIPES, context)
        branch_layer = self.parameterAsVectorLayer(parameters, self.INPUT_BRANCHES, context)
        parcel_layer = self.parameterAsVectorLayer(parameters, self.INPUT_PARCELS, context)
        force_regenerate = self.parameterAsBoolean(parameters, self.FORCE_GENERATE, context)
        direction = self.parameterAsString(parameters, self.TRACE_DIRECTION, context).lower()
        direction = DIRECTION(direction)

        feedback.pushInfo(f"{pipe_layer=}, {branch_layer=}, {parcel_layer=}, {direction=}, {force_regenerate=}")

        # ensure single feature selected
        if layer.selectedFeatureCount() != 1:
            msg = "Select one feature"
            feedback.reportError(
                error=msg,
                fatalError=True,
            )

        graph = self._get_layer_graph(
            feedback,
            layer,
            direction,
            force_regenerate,
        )
        first_node = next(iter(layer.selectedFeatures()))["START_NODE"]
        feedback.pushInfo(f'{first_node=}')

        trace_result = Trace(graph).trace(first_node=first_node, summary=True)
        feedback.pushInfo(f'Found {len(trace_result.pipes)} pipes upstream')
        ids = [graph.qgis_fids[p] for p in trace_result.pipes]

        # select features
        layer.selectByIds(ids)

        return {self.OUTPUT: parameters[self.INPUT]}

    def _get_layer_graph(
        self,
        feedback: QgsProcessingFeedback,
        layer: QgsVectorLayer | QgsProcessingParameterVectorLayer,
        direction: DIRECTION,
        force_regenerate: bool,
    ) -> Graph:
            """Load graph if found, or generates new graph"""
            graph_path = GraphHelpers.find_graph_file(layer, direction)

            if graph_path and not force_regenerate:
                feedback.pushInfo(f'Found graph: {graph_path}')
                graph = GraphHelpers.load_graph_from_file(graph_path)
            else:
                feedback.pushInfo(f'{graph_path=}, {force_regenerate=}')
                graph = GraphHelpers.generate_new_graph(layer, direction, feedback)
                graph_path = GraphHelpers.save_graph(feedback=feedback, layer=layer, graph=graph)
                feedback.pushInfo(f'New {graph_path=}, {force_regenerate=}')

            GraphHelpers.add_graph_to_layer(feedback, layer, graph, graph_path)

            return graph