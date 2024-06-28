from __future__ import annotations

import json
import os.path
from typing import Any

from qgis import processing
from qgis.core import (
    Qgis,
    QgsFeatureRequest,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterVectorLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication

from gwwnetworktrace.gww_gis_tools.trace_gis.trace_sewer import (
    Graph,
    Trace,
)
from gwwnetworktrace.gww_nt_processing.base_alg import BaseAlgorithm


class UpstreamTraceAlgorithm(BaseAlgorithm):
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

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    FORCE_REGENERATE = "FORCE_REGENERATE"

    def __init__(self) -> None:
        super().__init__()

        self._name = "upstream_trace"
        self._display_name = "Run upstream trace"
        self._group_id = ""
        self._group = ""
        self._short_help_string = ""

    def initAlgorithm(self, config=None):  # noqa N802
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr("Input layer"),
                [QgsProcessing.TypeVectorAnyGeometry],
            )
        )

        # TODO: add regenerate Graph option
        # TODO: add specify custom Graph option

    def processAlgorithm(  # noqa N802
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict:
        # Initialize feedback if it is None
        if feedback is None:
            feedback = QgsProcessingFeedback()

        layer: QgsVectorLayer = self.parameterAsVectorLayer(parameters, self.INPUT, context)

        # ensure single feature selected
        if layer.selectedFeatureCount() != 1:
            msg = "Select one feature"
            raise NotImplementedError(msg)

        source_graph = self._get_layer_graph(layer, context, feedback)
        first_node = next(iter(layer.selectedFeatures()))["START_NODE"]
        t_result = Trace(source_graph).trace(first_node=first_node, summary=True)
        pipes_list = list(t_result.pipes)

        # get feature IDs for target PIPE_IDs
        single_attr_request = (
            QgsFeatureRequest()
            .setFlags(QgsFeatureRequest.NoGeometry)
            .setSubsetOfAttributes(["PIPE_ID"], fields=layer.fields())
        )
        ids = (f.id() for f in layer.getFeatures(request=single_attr_request) if f["PIPE_ID"] in pipes_list)

        # select features
        layer.selectByIds(ids)

        return {self.OUTPUT: parameters[self.INPUT]}

    def _get_layer_graph(
        self,
        layer: QgsVectorLayer | QgsProcessingParameterVectorLayer,
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> Graph:
        graph_path = layer.customProperty(value="gwwnetworktrace_graph", defaultValue=None)

        if not graph_path:
            graph_path = processing.run(
                algorithm="gwwnetworktrace:gwwnetworktrace.gww_nt_processing.graph:UpstreamTraceAlgorithm",
                parameter={
                    "INPUT": layer,
                    "FORCE_GENERATE": False,  # add regenerate option SELF.FORCE_REGENERATE
                },
                context=context,
                feedback=feedback,
            )

        return Graph.from_file(graph_path)
