import tempfile
import time
import os.path

try:
    import fiona
    import geopandas as gpd
except ImportError:
    GPD_SUPPORT = False
    raise NotImplementedError(
        "geopandas not installed. Install with 'conda install -c conda-forge geopandas'"
    )
else:
    GPD_SUPPORT = True


class AssetType:
    """Enum-like class to prevent typos"""

    PARCELS = "parcels"
    PIPES = "pipes"
    BRANCHES = "branches"
    NODES = "nodes"


class W:
    SHORT = "W"
    COMPANY = "WW"
    FULL = "Western Region"
    SERVER = "wro-gisapp"


class C:
    SHORT = "C"
    COMPANY = "CWW"
    FULL = "Central Region"
    SERVER = "citywestwater.com.au"


class Config:
    local_files = {
        AssetType.PARCELS: {
            W: [
                "C:\\Users\\holmest1\\Greater Western Water\\IP - Spatial - Documents\\Input\\2. GWW GIS Exports\\Existing Assets\\Central Region\\Cadastre\\Parcels.tab"
            ],
            C: [
                "C:\\Users\\holmest1\\Greater Western Water\\IP - Spatial - Documents\\Input\\2. GWW GIS Exports\\Existing Assets\\Western Region\\Cadastre\\SP_PROPERTY.shp"
            ],
        },
        AssetType.PIPES: {
            W: [
                "C:\\Users\\holmest1\\Greater Western Water\\IP - Spatial - Documents\\Input\\2. GWW GIS Exports\\Existing Assets\\Western Region\\Sewer\\SP_SEWGPIPE.shp",
                "C:\\Users\\holmest1\\Greater Western Water\\IP - Spatial - Documents\\Input\\2. GWW GIS Exports\\Existing Assets\\Western Region\\Sewer\\SP_SEWVPIPE.shp",
                "C:\\Users\\holmest1\\Greater Western Water\\IP - Spatial - Documents\\Input\\2. GWW GIS Exports\\Existing Assets\\Western Region\\Sewer\\SP_SEWRPIPE.shp",
            ],
            C: [
                "C:\\Users\\holmest1\\Greater Western Water\\IP - Spatial - Documents\\Input\\2. GWW GIS Exports\\Existing Assets\\Central Region\\Sewer\\Sewer_Pipe.TAB"
            ],
        },
        AssetType.BRANCHES: {
            W: [
                "C:\\Users\\holmest1\\Greater Western Water\\IP - Spatial - Documents\\Input\\2. GWW GIS Exports\\Existing Assets\\Western Region\\Sewer\\SP_SEWSERV.shp"
            ],
            C: [
                "C:\\Users\\holmest1\\Greater Western Water\\IP - Spatial - Documents\\Input\\2. GWW GIS Exports\\Existing Assets\\Central Region\\Sewer\\Sewer_Branch.tab"
            ],
        },
        AssetType.NODES: {
            W: [
                "C:\\Users\\holmest1\\Greater Western Water\\IP - Spatial - Documents\\Input\\2. GWW GIS Exports\\Existing Assets\\Western Region\\Sewer\\SP_SEWNODE.shp"
            ],
            C: [
                "C:\\Users\\holmest1\\Greater Western Water\\IP - Spatial - Documents\\Input\\2. GWW GIS Exports\\Existing Assets\\Central Region\\Sewer\\Sewer_Node.tab"
            ],
        },
    }

    network_files = {
        AssetType.PARCELS: {
            W: ["\\\\wro-gisapp\\MunsysExport\\SP_PROPERTY.shp"],
            C: [
                "\\\\citywestwater.com.au\\data\\pccommon\\Asset Information\\MUNSYS MapInfo Data\\Production\\Data\\Cadastre\\Parcels.tab"
            ],
        },
        AssetType.PIPES: {
            W: [
                "\\\\wro-gisapp\\MunsysExport\\SP_SEWGPIPE.shp",
                "\\\\wro-gisapp\\MunsysExport\\SP_SEWVPIPE.shp",
                "\\\\wro-gisapp\\MunsysExport\\SP_SEWRPIPE.shp",
            ],
            C: [
                "\\\\citywestwater.com.au\\data\\pccommon\\Asset Information\\MUNSYS MapInfo Data\\Production\\Data\\Sewer\\Sewer_Pipe.TAB"
            ],
        },
        AssetType.BRANCHES: {
            W: ["\\\\wro-gisapp\\MunsysExport\\SP_SEWSERV.shp"],
            C: [
                "\\\\citywestwater.com.au\\data\\pccommon\\Asset Information\\MUNSYS MapInfo Data\\Production\\Data\\Sewer\\Sewer_Branch.tab"
            ],
        },
        AssetType.NODES: {
            W: ["\\\\wro-gisapp\\MunsysExport\\SP_SEWNODE.shp"],
            C: [
                "\\\\citywestwater.com.au\\data\\pccommon\\Asset Information\\MUNSYS MapInfo Data\\Production\\Data\\Sewer\\Sewer_Node.tab"
            ],
        },
    }

    # cloud_queries = {
    #     AssetType.PIPES: {
    #         W: "SELECT * FROM SP_SEWGPIPE",
    #         C: "SELECT * FROM SP_SEWVPIPE UNION SELECT * FROM SP_SEWRPIPE",
    #     },
    #     AssetType.BRANCHES: {
    #         W: "SELECT * FROM SP_SEWSERV",
    #         C: "SELECT * FROM SP_SEWSERV",
    #     },
    #     AssetType.NODES: {W: "SELECT * FROM SP_SEWNODE", C: "SELECT * FROM SP_SEWNODE"},
    #     AssetType.PARCELS: {
    #         W: "SELECT * FROM SP_PROPERTY",
    #         C: "SELECT * FROM SP_PROPERTY",
    #     },
    # }

    output_template = r"C:\Users\holmest1\Greater Western Water\IP - Spatial - Documents\Input\2. GWW GIS Exports\Existing Assets\Merged Regions\Sewer\GWW_{id}.tab"

    asset_uids = {
        "END_NODE",
        "START_NODE",
        "PIPE_ID",
        "GID",  # pipes
        "NODE_ID",
        "GID",  # nodes
        "GID",
        "SERV_ID" "GID",  # branches
        "PRCL_GID",
        "PROP_GID",  # parcels
    }

    column_map = {
        "ECOVELEV": "END_COVELEV",
        "SCOVELEV": "START_COVELEV",
        "E_INVELEV": "END_INVELEV",
        "S_INVELEV": "START_INVELEV",
        "GEOMLENGTH": "GEOM_LENGTH",
        "NODECOVELE": "NODE_COVELEV",
        "PGRADIENT": "PIPE_GRADIENT",
    }

    def __init__(self):
        self._files = None

    @property
    def files(self):
        return self._files or self.network_files

    @files.setter
    def files(self, data_source):
        self._files = data_source

    def possible_outpaths(self):
        outpaths = {
            id: os.path.getmtime(self.output_template.format(id=id))
            for id in self.files
            if os.path.exists(self.output_template.format(id=id))
        }

        return outpaths

    def get_filepaths(self, asset_type: str, region: str):
        return self.files.get(asset_type, {}).get(region, [])


class DataHelpers:
    @staticmethod
    def get_table_name(filepath, asset_type, region):
        if (asset_type, region) == (AssetType.PIPES, W):
            return filepath.split("\\")[-1][:-4]
        else:
            return filepath

    @staticmethod
    def load_invalid_file(src_path):
        """Modify read_file to handle invalid geometry"""
        # Create a temporary file for writing the modified shapefile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = temp_dir + "\modified_file.noext"

            # Parse original file
            with fiona.open(src_path) as src:
                # Start temp file
                with fiona.open(temp_file, "w", **src.meta) as dst:
                    # Check each feature for valid LineString geometry
                    for feature in src:
                        if feature["geometry"]["type"] == "LineString":
                            if len(feature["geometry"]["coordinates"]) > 1:
                                dst.write(feature)
                        if feature["geometry"]["type"] == "MultiLineString":
                            feature["geometry"]["coordinates"] = [
                                f
                                for f in feature["geometry"]["coordinates"]
                                if len(f) > 1
                            ]
                            dst.write(feature)

            # Read the modified shapefile
            gdf = gpd.read_file(temp_file)
        return gdf

    @classmethod
    def read_file(cls, *args, **kwargs) -> gpd.GeoDataFrame:
        """Modified read_file to handle invalid geometry"""
        try:
            gdf = gpd.read_file(*args, **kwargs)
            filename = args[0].split("\\")[-1]
            print(f"Loaded {gdf.shape[0]} rows from {filename}")
            return gdf
        except Exception as e:
            if e.args == ("LineStrings must have at least 2 coordinate tuples",):
                print(f"Warning: naughty file found. Fixing error: {e.args}")
                gdf = cls.load_invalid_file(*args, **kwargs)
                print(f"Loaded {gdf.shape[0]} rows from {args[0]}")
                return gdf
            else:
                print(f"Unhandled error {args}, {kwargs}: {e.args}")


class FieldsHelpers:
    @staticmethod
    def intersect(x, y):
        return list(sorted(set(x.columns).intersection(y.columns)))

    @staticmethod
    def diff(x, y):
        return list(sorted(set(x.columns).difference(y.columns)))

    @staticmethod
    def dia_to_height_width(x):
        hw = str(x).split("x")

        if len(hw) == 1:
            hw.append(hw[0])

        try:
            hw = tuple(map(int, hw))
        except ValueError:  # commonly 'UNKN'
            hw = (0, 0)

        return hw


class Corrections:
    @staticmethod
    def reverse_direction(row):
        row.END_NODE, row.START_NODE = row.START_NODE, row.END_NODE
        row.END_COVELEV, row.START_COVELEV = row.START_COVELEV, row.END_COVELEV
        row.END_INVELEV, row.START_INVELEV = row.START_INVELEV, row.START_INVELEV
        return row

    @staticmethod
    def swap_nodes(row):
        row.END_NODE, row.START_NODE = row.START_NODE, row.END_NODE
        return row
