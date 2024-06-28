# run as script in QGIS python console

import random
import time

from qgis.core import (
    Qgis,
    QgsExpression,
    QgsFeatureRequest,
    QgsVectorLayer,
)

sample_sizes = [500, 1000]

layer: QgsVectorLayer = iface.activeLayer()
assert "PIPE_ID" in [field.name() for field in layer.fields()]
assert "START_NODE" in [field.name() for field in layer.fields()]

single_attr_request = (
    QgsFeatureRequest()
    .setFlags(QgsFeatureRequest.NoGeometry)
    .setSubsetOfAttributes(["PIPE_ID"], fields=layer.fields())
)
all_features = list(layer.getFeatures(request=single_attr_request))

timing_subop = []
timing_op = []
current_time = time.time()

for sample_size in sample_sizes:
    # page_limits = [pl for pl in sample_sizes if pl <= sample_size]
    # current_time = time.time()

    # for page_limit in page_limits:
    #     # Test setup 1: by expression
    #     layer.removeSelection()
    #     rand_features = random.sample(all_features, sample_size)
    #     attr_list = [f['PIPE_ID'] for f in rand_features]
    #     timing_subop.append(f'time taken: {time.time() - current_time}, {page_limit=}, {sample_size=}, by expression: setup')
    #     current_time = time.time()

    #     # Test procedure 1: by expression
    #     timing_op.append((time.time(), 0.0, page_limit, sample_size, 'start procedure: by expression'))

    #     for i in range(0, len(attr_list), page_limit):
    #         result_slice = attr_list[i:i+page_limit]
    #         expression = f'"PIPE_ID" in {tuple(result_slice)!s}'
    #         layer.selectByExpression(expression=expression, behavior=Qgis.SelectBehavior.AddToSelection)
    #         timing_subop.append(f'time taken: {time.time() - current_time}, {page_limit=}, {sample_size=}, by expression: select {i}')
    #         current_time = time.time()

    #     timing_op.append((time.time(), time.time() - timing_op[-1][0], page_limit, sample_size, 'by expression'))

    #     # Test setup 2: by id
    #     layer.removeSelection()
    #     rand_features = random.sample(all_features, sample_size)
    #     attr_list = [f['PIPE_ID'] for f in rand_features]
    #     timing_subop.append(f'time taken: {time.time() - current_time}, {page_limit=}, {sample_size=}, by id: setup')
    #     current_time = time.time()

    #     # Test procedure 2: by id
    #     timing_op.append((time.time(), 0.0, page_limit, sample_size, 'start procedure: by id'))

    #     ids = []
    #     for i in range(0, len(attr_list), page_limit):
    #         result_slice = attr_list[i:i+page_limit]
    #         expression = f'"PIPE_ID" in {tuple(result_slice)!s}'
    #         no_attr_request = (
    #             QgsFeatureRequest()
    #             .setFilterExpression(expression)
    #             .setFlags(QgsFeatureRequest.NoGeometry)
    #             .setSubsetOfAttributes([])
    #         )
    #         features_slice = layer.getFeatures(request=no_attr_request)
    #         ids += [f.id() for f in features_slice]
    #         timing_subop.append(f'time taken: {time.time() - current_time}, {page_limit=}, {sample_size=}, by id: get ids {i}')
    #         current_time = time.time()

    #     layer.selectByIds(ids)
    #     timing_subop.append(f'time taken: {time.time() - current_time}, {page_limit=}, {sample_size=}, by id: select by ids')
    #     current_time = time.time()

    #     timing_op.append((time.time(), time.time() - timing_op[-1][0], page_limit, sample_size, 'end procedure: by id'))

    # Test setup 3: by id
    layer.removeSelection()
    rand_features = random.sample(all_features, sample_size)
    attr_list = [f["PIPE_ID"] for f in rand_features]
    timing_subop.append(
        f"time taken: {time.time() - current_time}, {sample_size=}, setup by iterator"
    )
    current_time = time.time()

    # Test procedure 3: by id
    timing_op.append((time.time(), 0.0, sample_size, "start procedure: by iterator"))

    ids = [
        f.id()
        for f in layer.getFeatures(request=single_attr_request)
        if f["PIPE_ID"] in attr_list
    ]
    timing_subop.append(
        f"time taken: {time.time() - current_time}, {sample_size=}, iterate layer by iterator"
    )
    current_time = time.time()

    layer.selectByIds(ids)
    timing_subop.append(
        f"time taken: {time.time() - current_time}, {sample_size=}, finish by iterator"
    )
    current_time = time.time()

    timing_op.append(
        (
            time.time(),
            time.time() - timing_op[-1][0],
            sample_size,
            "end procedure: by iterator",
        )
    )

print("\n".join(timing_subop))
print("\n".join(" ".join(map(str, line[1:])) for line in timing_op if line[1] != 0))

# Example output:
