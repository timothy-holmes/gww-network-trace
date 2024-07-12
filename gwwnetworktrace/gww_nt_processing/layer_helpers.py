import os.path
from functools import reduce
from typing import Union

from qgis.core import (
    QgsFeature,
    QgsFeatureRequest,
    QgsVectorLayer,
)

LAYER_FIELDS = {
    "pipe": ["PIPE_ID", "START_NODE", "END_NODE"],
    "parcel": ["GID"],
    "branch": ["PIPE_ID", "PRCL_GID"],
}


class LayerMeta:
    @classmethod
    def validate_layer(cls, layer_type, layer: QgsVectorLayer):
        required_fields = LAYER_FIELDS[layer_type]
        layer_fields = (field.name() for field in layer.fields())
        check = (f in layer_fields for f in required_fields)
        return all(check)

    @classmethod
    def get_layer_source_hash(cls, layer: QgsVectorLayer) -> str:
        ops = [os.path.basename, hash, abs, hex, str]
        return reduce(lambda o, func: func(o), ops, layer.source())[-8:]


class LayerData:
    @classmethod
    def get_trace_data(
        cls,
        layer: QgsVectorLayer,
        layer_type: str = "pipe",
        fids: bool = False,
    ) -> list[dict[str, Union[int, str]]]:
        feature_request = (
            QgsFeatureRequest()
            .setFlags(QgsFeatureRequest.NoGeometry)
            .setSubsetOfAttributes(
                attrNames=LAYER_FIELDS[layer_type],
                fields=layer.fields(),
            )
        )
        features = layer.getFeatures(feature_request)

        return [cls.extract_feature_data(f=f, fields=LAYER_FIELDS[layer_type], fid=fids) for f in features]

    @classmethod
    def extract_feature_data(cls, f: QgsFeature, fields: list[str], fid: bool = False) -> dict[str, Union[int, str]]:
        data = {k: f[k] for k in fields}

        if fid:
            data |= {"QGIS_FID": f.id()}

        return data
