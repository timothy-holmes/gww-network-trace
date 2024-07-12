from __future__ import annotations

from typing import Any, Union

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
    Trace,
)
from gwwnetworktrace.gww_nt_processing.base_alg import BaseAlgorithm
from gwwnetworktrace.gww_nt_processing.graph_helpers import GraphHelpers


class TraceParcelsAlgorithm(BaseAlgorithm):
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

    INPUT_PIPES = "INPUT_PIPES"
    INPUT_BRANCHES = "INPUT_BRANCHES"
    INPUT_PARCELS = "INPUT_PARCELS"

    def __init__(self) -> None:
        super().__init__()

        self._name = "trace_parcels"
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
                optional=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                name=self.INPUT_BRANCHES,
                description=self.tr("Input layer"),
                types=[QgsProcessing.TypeVectorLine],
                optional=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                name=self.INPUT_PARCELS,
                description=self.tr("Input layer"),
                types=[QgsProcessing.TypeVectorPolygon],
                optional=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                name=self.TRACE_DIRECTION,
                description=self.tr("Trace Direction"),
                options=[d.value.upper() for d in DIRECTION],
                allowMultiple=False,
                defaultValue=DIRECTION.U.value,
                optional=False,
                usesStaticStrings=True,
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
        feedback: Union[QgsProcessingFeedback, None],
    ) -> dict:
        # Initialize feedback if it is None
        if feedback is None:
            feedback = QgsProcessingFeedback()

        layers = [
            self.parameterAsVectorLayer(parameters, p, context)
            for p in [
                self.INPUT_PIPES,
                self.INPUT_BRANCHES,
                self.INPUT_PARCELS,
            ]
        ]

        force = self.parameterAsBoolean(parameters, self.FORCE_GENERATE, context)
        direction = self.parameterAsString(parameters, self.TRACE_DIRECTION, context).lower()
        direction = DIRECTION(direction)

        feedback.pushInfo(f"{layers}, {direction=}, {force=}")

        # ensure single feature selected
        if layers[0].selectedFeatureCount() != 1:
            msg = "Select one feature"
            feedback.reportError(
                error=msg,
                fatalError=True,
            )

        graph = GraphHelpers.get_layer_graph(
            feedback=feedback,
            layers=layers,
            direction=direction,
            force=force,
        )
        first_node = next(iter(layers[0].selectedFeatures()))["START_NODE"]
        feedback.pushInfo(f"{first_node=}")

        trace_result = Trace(graph).trace(first_node=first_node, summary=True)
        pipe_fids = [graph.qgis_fids[p] for p in trace_result.pipes]
        feedback.pushInfo(f"Found {len(pipe_fids)} pipes upstream")
        layers[0].selectByIds(pipe_fids)

        parcel_fids = [
            p_fid
            for p in trace_result.pipes
            for p_fid in graph.qgis_parcel_fids[p]
        ]
        feedback.pushInfo(f"Found {len(parcel_fids)} parcels upstream")
        layers[2].selectByIds(parcel_fids)

        # select features

        return {self.OUTPUT: parameters[self.INPUT_PIPES]}
