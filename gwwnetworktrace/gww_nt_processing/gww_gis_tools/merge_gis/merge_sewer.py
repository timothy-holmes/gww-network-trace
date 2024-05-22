from typing import Union
from functools import reduce
import os.path

try:
    import geopandas as gpd
    import pandas as pd
except ImportError:
    # GPD_SUPPORT = False
    # import pandas as pd
    raise NotImplementedError(
        "geopandas not installed. Install with 'conda install -c conda-forge geopandas'"
    )
else:
    # GPD_SUPPORT = True
    pass

from gww_gis_tools.merge_gis.sewer_helpers import (
    Config,
    AssetType,
    W,
    C,
    DataHelpers,
    FieldsHelpers,
    Corrections,
)


def merge(config, output: dict):
    for a in config.files.keys():
        ww_files = {
            DataHelpers.get_table_name(fp, a, W): fp
            for fp in DataHelpers.get_filepaths(a, W)
        }
        cww_files = DataHelpers.get_filepaths(a, C)

        if (not len(ww_files)) or (not len(cww_files)):
            print("Skipping", a)

        ww_gdfs = [
            DataHelpers.read_file(fp).assign(SRC_TABLE=src)
            for src, fp in ww_files.items()
        ]
        ww_gdf = gpd.GeoDataFrame(
            pd.concat(ww_gdfs, ignore_index=True), crs=ww_gdfs[0].crs
        )

        cww_gdf = DataHelpers.read_file(cww_files[0])

        if "ASSET_OWNER" in cww_gdf.columns:
            cww_owner_mask = cww_gdf[~(cww_gdf["ASSET_OWNER"] == C.COMPANY)]
            cww_gdf.drop(cww_owner_mask.index, inplace=True)

        ww_gdf["ASSET_OWNER"] = W.COMPANY

        for c in config.asset_uids:
            if c in cww_gdf.columns:
                cww_gdf[c] = cww_gdf[c].astype(int).astype(str) + "_" + C.COMPANY
            if c in ww_gdf.columns:
                ww_gdf[c] = ww_gdf[c].astype(str) + "_" + W.COMPANY

        ww_gdf.rename(
            columns={
                c2: c1 for c2, c1 in config.column_map.items() if c2 in ww_gdf.columns
            },
            inplace=True,
        )

        if "PIPE_DIA" in cww_gdf.columns:
            cww_gdf["PIPE_DIA"] = (
                cww_gdf["PIPE_DIA"].apply(FieldsHelpers.dia_to_int).astype(int)
            )

        fields = FieldsHelpers.intersect(cww_gdf, ww_gdf)

        # concat C and W
        crs = cww_gdf.crs
        ww_gdf.to_crs(crs, inplace=True)

        joined_gdf = gpd.GeoDataFrame(
            pd.concat([cww_gdf[fields], ww_gdf[fields]], ignore_index=True), crs=crs
        )
        joined_gdf.reset_index(inplace=True)

        output[a] = joined_gdf

    return output


def make_corrections(config, output: dict):
    if AssetType.PIPES in output:
        pipes_gdf = output[AssetType.PIPES]

        pipe_corrections = [{"pipe_id": "104368_CWW", "action": Corrections.swap_nodes}]

        for c in pipe_corrections:
            row = pipes_gdf.loc[pipes_gdf["PIPE_ID"] == c["pipe_id"]]
            pipes_gdf.loc[pipes_gdf["PIPE_ID"] == c["pipe_id"]] = c["action"](row)

        # temporary fix for START_NODE/END_NODE = 0_CWW, 0_WW
        pipes_gdf.drop(
            pipes_gdf[
                (pipes_gdf["START_NODE"] == "0_CWW")
                | (pipes_gdf["START_NODE"] == "0_WW")
                | (pipes_gdf["END_NODE"] == "0_CWW")
                | (pipes_gdf["END_NODE"] == "0_WW")
            ].index,
            inplace=True,
        )

        output[AssetType.PIPES] = pipes_gdf

    return output


def classify_parcels(config, output: dict):
    if AssetType.PARCELS in output and AssetType.BRANCHES in output:
        branches_gdf = output[AssetType.BRANCHES]
        parcels_gdf = output[AssetType.PARCELS]

        drop_parcel_mask = parcels_gdf["GID"].isin(branches_gdf["PRCL_GID"])
        parcels_unserved_gdf = parcels_gdf[~drop_parcel_mask].copy()
        parcels_gdf.drop(parcels_gdf[~drop_parcel_mask].index, inplace=True)

        output["parcels_unserved"] = parcels_unserved_gdf
        output["parcels"] = parcels_gdf

    return output


def save_file(gdf, filename):
    schema = gpd.io.file.infer_schema(
        gdf
    )  # ordinarily this is inferred within gpd.to_file()
    for col, dtype in schema["properties"].items():
        if dtype == "int" or dtype == "int64":
            schema["properties"][col] = "int32"
    gdf.to_file(filename, driver="MapInfo File", schema=schema)


def save_output(config: Config, output: dict):
    outpaths = [config.output_template.format(id=id) for id in output]

    for id, gdf in output.items():
        save_file(gdf=gdf, filename=config.output_template.format(id=id))
    print(f"{id} saved")

    return outpaths


def possible_outpaths(config):
    possible_ids = list(config.files.keys()) + ["parcels_unserved", "parcels"]

    outpaths = {
        id: os.path.getmtime(config.output_template.format(id=id))
        for id in possible_ids
        if os.path.exists(config.output_template.format(id=id))
    }

    return outpaths


# example usage
def run():
    config = Config()
    output = dict()

    func_list = [merge, make_corrections, classify_parcels, save_output]
    outpaths = reduce(lambda o, func: func(config, o), func_list, output)

    return outpaths


if __name__ == "__main__":
    result = run()
    print(result)
