from __future__ import annotations

import importlib
from typing import Any

from qgis import processing  # noqa: TCH002
from qgis.core import (
    QgsFeatureRequest,
    QgsFeatureSink,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
)
from qgis.PyQt.QtCore import QCoreApplication

from gwwnetworktrace.gww_nt_processing.gww_gis_tools.trace_gis.trace_sewer import (
    DIRECTION,
    Graph,
    Trace,
)


class UpstreamTraceAlgorithm(QgsProcessingAlgorithm):
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

    def __init__(self) -> None:
        super().__init__()

        self._name = "upstream_trace"
        self._display_name = "Run upstream trace"
        self._group_id = ""
        self._group = ""
        self._short_help_string = ""

    def tr(self, string) -> str:
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):  # noqa N802
        return self.__class__()

    def name(self) -> str:
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return self._name

    def displayName(self) -> str:  # noqa N802
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self._display_name)

    def groupId(self) -> str:  # noqa N802
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return self._group_id

    def group(self) -> str:
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self._group)

    def shortHelpString(self) -> str:  # noqa N802
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr(self._short_help_string)

    def initAlgorithm(self, config=None):  # noqa N802
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Input layer"),
                [QgsProcessing.TypeVectorAnyGeometry],
            )
        )

        # TODO: add regenerate Graph option
        # TODO: add specify custom Graph option

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Output layer"))
        )

    def processAlgorithm(  # noqa N802
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict:
        """
        Here is where the processing itself takes place.
        """

        # Initialize feedback if it is None
        if feedback is None:
            feedback = QgsProcessingFeedback()

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        feature_source = self.parameterAsSource(parameters, self.INPUT, context)
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)

        # TODO: move this to Generate Graph algorithm
        feedback.pushInfo(f"{feature_source.featureCount()} features loaded")
        feature_request = (
            QgsFeatureRequest()
            .setFlags(QgsFeatureRequest.NoGeometry)
            .setSubsetOfAttributes(["START_NODE", "END_NODE"])
        )
        features = feature_source.getFeatures(feature_request)
        feature_data = [
            {
                "PIPE_ID": f.id(),
                "START_NODE": f['START_NODE'],
                "END_NODE": f['END_NODE']
            } for f in features
        ]

        source_graph = Graph(DIRECTION.U).from_dicts(feature_data)

        # ensure single feature selected
        if layer.selectedFeatureCount() != 1:
            msg = "Select one feature"
            raise NotImplementedError(msg)

        first_node = next(layer.selectedFeatures()).id()
        t_result = Trace(source_graph).trace(first_node=first_node)
        layer.selectByIds(t_result.pipes)

        return {self.OUTPUT: ""}
