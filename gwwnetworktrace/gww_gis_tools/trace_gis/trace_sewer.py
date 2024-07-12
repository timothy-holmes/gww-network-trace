"""Trace Sewer."""

from __future__ import annotations

import builtins
import contextlib
import inspect
import json
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Union

with contextlib.suppress(ImportError):
    from typing import Any, Self

if TYPE_CHECKING:
    with contextlib.suppress(ImportError):
        import geopandas as gpd  # pyright: ignore[reportMissingImports]


class DIRECTION(Enum):
    """Specify direction on initialisation."""

    U = "upstream"
    D = "downstream"


class Graph:
    """Represents network as a graph data structure.

    Args:
    ----
    - direction: The direction of the graph
        (either 'U' for undirected or 'D' for directed).

    Attributes:
    ----------
    - direction: The direction of the graph.
    - nodes: A dictionary of nodes and their adjacent nodes.
    - pipes: A dictionary of nodes and the pipes associated with them.

    Methods:
    -------
    - _validate_direction(direction): Validates the input direction.
    - from_gdf(links: geopandas.GeoDataFrame | pandas.DataFrame):
        Converts a (Geo)DataFrame to a graph by adding edges.
    - from_dicts(links: list[dict]):
        Converts a list of dictionaries to a graph by adding edges.
    - add_edge(start_node, end_node, pipe_id):
        Adds an edge to the graph based on the direction.

    """

    def __init__(self, direction: DIRECTION) -> None:
        """Specify direction on initialisation."""
        self.direction = direction

        self.nodes: defaultdict[Union[str, int], list] = defaultdict(list)
        self.pipes: defaultdict[Union[str, int], list] = defaultdict(list)
        self.qgis_fids: dict[Union[str, int], int] = {}  # pipes only
        self.qgis_parcel_fids: defaultdict[Union[str, int], list] = defaultdict(list)

    def __repr__(self) -> str:
        """Return a string representation of the graph."""
        return f"Graph({self.direction}, {len(self.nodes)=})"

    def from_gdf(self, links: gpd.GeoDataFrame) -> Self:
        """Use a (Geo)DataFrame to add each row as an edge. Returns graph object."""
        for f in links.itertuples(index=False):
            self.add_edge(f.START_NODE, f.END_NODE, f.PIPE_ID)
        return self

    def from_dicts(self, links: list[dict]) -> Self:
        """Use a list of dictionaries to add rows as an edges. Returns graph object."""
        SUPPORTED_KEYS = ["START_NODE", "END_NODE", "PIPE_ID", "QGIS_FID"]
        fields = next(iter(links)).keys()
        keys = [f for f in SUPPORTED_KEYS if f in fields]

        for link in links:
            self.add_edge(*tuple(link[k] for k in keys))
        return self

    def add_edge(
        self,
        start_node: Union[str, int],
        end_node: Union[str, int],
        pipe_id: Union[str, int],
        qgis_fid: Union[int, None] = None,
    ) -> Self:
        """Add field values for a single feature as an edge. Returns graph object."""
        if self.direction == DIRECTION.U:
            self.nodes[end_node].append(start_node)
            self.pipes[end_node].append(pipe_id)
        elif self.direction == DIRECTION.D:
            self.nodes[start_node].append(end_node)
            self.pipes[start_node].append(pipe_id)

        if qgis_fid:
            self.qgis_fids[pipe_id] = qgis_fid

        return self

    def add_qgis_parcel_ids(
        self,
        branches_info: list[dict[str, Union[str, int]]],
    ) -> Self:
        """Adds info from branches to enable selecting parcels from pipe ids."""
        for branch in branches_info:
            self.qgis_parcel_fids[branch["PIPE_ID"]].append(branch["PARCEL_FID"])

        return self

    def to_file(self, filename: str) -> None:
        """Write graph object to file."""
        with Path(filename).open("w") as f:
            json.dump(self, f, cls=ExtendedEncoder, sort_keys=True)

    @classmethod
    def from_file(cls, filename: str) -> Self:
        """Read graph object from file."""
        with Path(filename).open() as f:
            return json.load(f, cls=ExtendedDecoder)


class TraceResult:
    """Dataclass-like objects for accessing results of tracing."""

    def __init__(
        self,
        trace_summary: dict,
        pipes: set,
        nodes: set,
        end_of_path_nodes: set,
    ) -> None:
        """Initialize TraceResult."""
        self.trace_summary = trace_summary
        self.pipes = pipes
        self.nodes = nodes
        self.end_of_path_nodes = end_of_path_nodes

    def __repr__(self) -> str:
        """Return string representation of TraceResult."""
        return "TraceResult({}, {})".format(
            self.trace_summary["direction"],
            self.trace_summary["start_node"],
        )


class Trace:
    """Used to trace a path through a graph.

    Option to provide a function that returns False to stop tracing.

    Args:
    ----
    - graph: The graph to be traced.
    - stop_node: Optional function to determine when to stop tracing.

    Methods:
    -------
    - trace(first_node): Traces a path through the graph starting from the first node.
    """

    def __init__(self, graph: Graph, stop_node: Union[Callable, None] = None) -> None:
        """Initialise Trace."""
        self.graph = graph
        self.stop_node = stop_node or (lambda x: True)  # noqa: ARG005

    def trace(
        self,
        first_node: Union[str, int],
        trace_name: str = "",
        summary: bool = False,  # noqa: FBT001, FBT002
    ) -> TraceResult:
        """
        Main trace method.

        This method tranverses graph object (depth-first) and returns a TraceResult
        containing nodes and pipes visited, and end of path nodes.
        """
        nodes = self.graph.nodes
        pipes = self.graph.pipes

        node_queue = [first_node]
        pipes_visited = set()
        nodes_visited = set()
        end_of_path_nodes = set()

        while node_queue:
            next_node = node_queue.pop()

            if not self.stop_node(next_node):
                nodes_visited.add(next_node)
                end_of_path_nodes.add(next_node)
                break

            if next_node not in nodes_visited:
                nodes_visited.add(next_node)
                next_nodes = nodes[next_node]
                next_pipes = pipes[next_node]

                if not next_nodes:
                    end_of_path_nodes.add(next_node)

                node_queue.extend(next_nodes)
                pipes_visited.update(next_pipes)

        if summary:
            trace_summary = {
                "trace_name": trace_name,
                "g_size": len(self.graph.nodes),
                "direction": self.graph.direction,
                "start_node": first_node,
                "stop_node_predicate": str(inspect.getsource(self.stop_node)).strip(),
            }
        else:
            trace_summary = {}

        return TraceResult(
            trace_summary=trace_summary,
            pipes=pipes_visited,
            nodes=nodes_visited,
            end_of_path_nodes=end_of_path_nodes,
        )


class ExtendedEncoder(json.JSONEncoder):
    """Extends JSONEncoder to customize JSON serialization.

    Methods:
    -------
    - default(self, obj): Overrides default behavior for serializing objects
        and uses dynamic method lookup to encode the object.
    - encode_TraceResult(self, tr) -> dict[str, list]: Specifically encodes
        TraceResult objects into a dictionary.

    """

    def default(self, o: Any) -> str:  # noqa: ANN401
        # TODO @timothy-holmes: create JSON type list # noqa: FIX002, TD003
        """
        Overrides default behavior for serializing objects.

        Uses dynamic method lookup to encode the object.
        """
        name = o.__class__.__name__

        try:
            encoder = getattr(self, f"_encode_{name}")
        except AttributeError:
            return o
        else:
            encoded = encoder(o)
            encoded["__extended_json_type__"] = name
            return encoded

    def _encode_defaultdict(self, o: defaultdict) -> dict[str, Union[str, dict]]:
        return {
            "__default_factory__": self.default(o.default_factory),
            "__dict__": dict(o),
        }

    def _encode_type(self, o: type) -> dict[str, str]:
        return {"_type": o.__name__}

    def _encode_TraceResult(self, tr: TraceResult) -> dict[str, list]:  # noqa: N802
        raise NotImplementedError

    def _encode_DIRECTION(self, d: DIRECTION) -> dict[str, str]:  # noqa: N802
        return {"_direction": d.value}

    def _encode_Graph(self, g: Graph) -> dict[str, Union[dict, list, str]]:  # noqa: N802
        return {
            "_direction": self.default(g.direction),
            "_nodes": self.default(g.nodes),
            "_pipes": self.default(g.pipes),
            "_qgis_fids": self.default(g.qgis_fids),
        }


class ExtendedDecoder(json.JSONDecoder):
    """
    Extends JSONDecoder to customize JSON deserialization.

    Methods:
    -------
    - object_hook(self, obj): Overrides default behavior for deserializing objects
        and uses dynamic method lookup to decode the object.
    """

    def __init__(self, **kwargs) -> None:  # noqa: ANN003
        """Initialize the class."""
        kwargs["object_hook"] = self.object_hook
        super().__init__(**kwargs)

    def object_hook(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        obj: dict,
    ) -> Any:  # noqa: ANN401
        """
        Replace method for extended JSON deserialization.

        Uses dynamic method lookup to decode the object.
        """
        try:
            name = obj["__extended_json_type__"]
            decoder = getattr(self, f"_decode_{name}")
        except (KeyError, AttributeError, TypeError):
            return obj
        else:
            return decoder(obj)

    def _decode_TraceResult(self, obj: dict) -> TraceResult:  # noqa: N802
        raise NotImplementedError

    def _decode_defaultdict(self, obj: dict) -> defaultdict:
        return defaultdict(self.object_hook(obj["__default_factory__"]), self.object_hook(obj["__dict__"]))

    def _decode_type(self, obj: dict) -> type:  # noqa: N802
        possible_types = {
            type(getattr(builtins, b)).__name__: getattr(builtins, b)
            for b in dir(builtins)
            if type(getattr(builtins, b)) is type
        }
        possible_types |= {type(g).__name__: g for g in globals() if type(g) is type}
        return possible_types[obj["_type"]]

    def _decode_DIRECTION(self, obj: dict) -> DIRECTION:  # noqa: N802
        return DIRECTION(obj["_direction"])

    def _decode_Graph(self, g_dict: dict[str, Union[dict, list]]) -> Graph:  # noqa: N802
        g = Graph(self.object_hook(g_dict["_direction"]))  # pyright: ignore[reportArgumentType]
        g.nodes = self.object_hook(g_dict["_nodes"])  # pyright: ignore[reportArgumentType]
        g.pipes = self.object_hook(g_dict["_pipes"])  # pyright: ignore[reportArgumentType]
        g.qgis_fids = self.object_hook(g_dict["_qgis_fids"])  # pyright: ignore[reportArgumentType]
        return g


if __name__ == "__main__":
    with open(
        r"C:/Users/holmest1/Greater Western Water/IP - Planning(Local) - Sewer/4. General/System Schematic/v2/data\\622d700622e88e2f.json"
    ) as jf:
        j = json.load(jf, cls=ExtendedDecoder)
