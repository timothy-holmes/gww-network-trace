from functools import reduce
from typing import Union

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
    AssetType,
    C,
    Config,
    Corrections,
    DataHelpers,
    FieldsHelpers,
    W,
)


def merge(config, output: dict):
    # TODO: this loop is convoluted, but it works
    for a in config.files.keys():  # a == AssetType
        # get file paths
        ww_files = {
            DataHelpers.get_table_name(fp, a, W): fp
            for fp in config.get_filepaths(a, W)
        }
        cww_files = config.get_filepaths(a, C)

        if (not len(ww_files)) or (not len(cww_files)):
            print("Skipping", a)

        # load files into single gdf for each company
        ww_gdfs = [
            DataHelpers.read_file(fp).assign(SRC_TABLE=src)
            for src, fp in ww_files.items()
        ]
        ww_gdf = gpd.GeoDataFrame(
            pd.concat(ww_gdfs, ignore_index=True), crs=ww_gdfs[0].crs
        )
        cww_gdf = DataHelpers.read_file(cww_files[0])

        #  drop WW abandonded assets
        abandoned_where = ww_gdf["OP_STATUS"] == 3
        ww_gdf.drop(abandoned_where, inplace=True)

        # set ASSET_OWNER
        if "ASSET_OWNER" in cww_gdf.columns:
            cww_owner_mask = ~(cww_gdf["ASSET_OWNER"] == C.COMPANY)
            cww_gdf.loc[cww_owner_mask, "ASSET_OWNER"] = f"NOT_{C.COMPANY}"
            ww_gdf["ASSET_OWNER"] = W.COMPANY

        for c in config.asset_uids:
            if c in cww_gdf.columns:
                cww_gdf[c] = cww_gdf[c].astype(int).astype(str) + f"_{C.COMPANY}"
            if c in ww_gdf.columns:
                ww_gdf[c] = ww_gdf[c].astype(str) + f"_{W.COMPANY}"

        ww_gdf.rename(
            columns={
                c2: c1 for c2, c1 in config.column_map.items() if c2 in ww_gdf.columns
            },
            inplace=True,
        )

        if "PIPE_DIA" in cww_gdf.columns:
            cww_gdf["PIPE_HEIGHT"], cww_gdf["PIPE_WIDTH"] = (
                cww_gdf["PIPE_DIA"].apply(FieldsHelpers.dia_to_int).astype(int)
            )
            cww_gdf.drop(columns="PIPE_DIA", inplace=True)

        fields = FieldsHelpers.intersect(cww_gdf, ww_gdf)
        print(f"Intersecting Fields: {fields}")
        print(FieldsHelpers.diff(cww_gdf, ww_gdf))
        print(FieldsHelpers.diff(ww_gdf, cww_gdf))

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
            index_where = pipes_gdf["PIPE_ID"] == c["pipe_id"]
            pipes_gdf.loc[index_where, :] = pipes_gdf.loc[index_where, :].apply(
                c["action"], axis=1
            )

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
