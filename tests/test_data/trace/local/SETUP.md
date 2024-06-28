# SETUP: Test data for gww_gis_tools.trace_gis.trace_sewer

In QGIS:

- Manually select suitable section of network from merged sewer layers: GWW_pipes, GWW_nodes
- With pipe layer active, get pipe ids of selected features: `pipes_ids = [f['PIPE_ID'] for f in iface.activeLayer().selectedFeatures()]`
- With branches layer active, select traceable branches: `iface.activeLayer().selectByExpression(f'\"PIPE_ID\" IN {tuple(pipe_ids)}');`
- With branches layer active, get parcel GIDs: `parcel_gids = [f['PRCL_GID'] for f in iface.activeLayer().selectedFeatures()]`
- With parcels layer active, select traceable parcels: `iface.activeLayer().selectByExpression(f'\"GID\" IN {tuple(parcel_gids)}');`
- Save selected features from each layer into test data folder ie. `./tests/test_data/trace/test_{pipes|nodes|branches|parcels}.geojson`

In python:

- Run python script to extract test data and put it into a single file: `./merge_gis> python ./tests/test_data/trace/extract_data.py`
