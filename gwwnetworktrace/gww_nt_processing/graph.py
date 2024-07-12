from __future__ import annotations

import inspect
from typing import Any

from qgis.core import (
    QgsProcessing,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterVectorLayer,
)

from gwwnetworktrace.gww_gis_tools.trace_gis.trace_sewer import (
    DIRECTION,
    Graph,
)
from gwwnetworktrace.gww_nt_processing.base_alg import BaseAlgorithm
from gwwnetworktrace.gww_nt_processing.graph_helpers import GraphHelpers


class GraphGenerateAlgorithm(BaseAlgorithm):
    def __init__(self) -> None:
        super().__init__()

        self._name = "graph"
        self._display_name = "Generate network graph"
        self._group_id = ""
        self._group = ""
        self._short_help_string = ""

    def initAlgorithm(self, configuration=None):  # noqa N802
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                name=self.INPUT,
                description=self.tr("Input layer"),
                types=[QgsProcessing.TypeVectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                name=self.TRACE_DIRECTION,
                description=self.tr('Trace Direction'),
                options=[d.value for d in DIRECTION],
                allowMultiple=False,
                defaultValue=DIRECTION.U.value,
                optional=False,
                usesStaticStrings=True
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                name=self.FORCE_GENERATE,
                description=self.tr("Force generate Graph"),
                defaultValue=False,
                optional=False,
            )
        )

    def processAlgorithm(  # noqa N802
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict:
        if feedback is None:
            feedback = QgsProcessingFeedback()

        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        force_regenerate = self.parameterAsBoolean(parameters, self.FORCE_GENERATE, context)
        direction = self.parameterAsString(parameters, self.TRACE_DIRECTION, context)
        direction = DIRECTION(direction)

        feedback.pushInfo(f'{str(layer)[:500]=}, {force_regenerate=}, {direction=}')

        graph_path = GraphHelpers.find_graph_file(layer, direction)
        feedback.pushInfo(f'Found {graph_path=}')

        if graph_path and not force_regenerate:
            source_graph = GraphHelpers.load_graph_from_file(graph_path)
        else:
            source_graph = GraphHelpers.generate_new_graph(layer, direction, feedback)
            graph_path = GraphHelpers.save_graph(
                feedback=feedback,
                layer=layer,
                graph=source_graph
            )

        feedback.pushInfo(f'Generated graph {graph_path}')

        return {self.OUTPUT: graph_path}
