import json
import os.path

asset_types = ["pipes", "parcels", "branches", "nodes"]
test_data = {a: [] for a in asset_types}

for a in asset_types:
    data_path = f"./tests/test_data/trace/test_{a}.geojson"
    if os.path.exists(data_path):
        with open(data_path) as f:
            geonjson = json.load(f)

        for f in geonjson.get("features", []):
            feature_data = f.get("properties")
            feature_data["geometry"] = f.get("geometry")
            test_data[a].append(feature_data)
    else:
        print("NOT FOUND", data_path)

json.dump(test_data, open("tests/test_data/trace/test_data.json", "w"))
