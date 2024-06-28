from __future__ import annotations

import inspect
import json
from collections import defaultdict
from enum import Enum
from typing import Callable, Union

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


class DIRECTION(Enum):
    U = "upstream"
    D = "downstream"


class Graph:
    """
    Represents network as a graph data structure.

    Args:
    - direction: The direction of the graph (either 'U' for undirected or 'D' for directed).

    Attributes:
    - direction: The direction of the graph.
    - nodes: A dictionary of nodes and their adjacent nodes.
    - pipes: A dictionary of nodes and the pipes associated with them.

    Methods:
    - _validate_direction(direction): Validates the input direction.
    - from_gdf(links: geopandas.GeoDataFrame | pandas.DataFrame): Converts a (Geo)DataFrame to a graph by adding edges.
    - from_dicts(links: list[dict]): Converts a list of dictionaries to a graph by adding edges.
    - add_edge(start_node, end_node, pipe_id): Adds an edge to the graph based on the direction.
    """

    def __init__(self, direction: DIRECTION):
        """Specify direction on initialisation"""
        self.direction = direction
        assert type(self.direction) is DIRECTION
        self.nodes: defaultdict[list] = defaultdict(list)
        self.pipes: defaultdict[list] = defaultdict(list)

    def __repr__(self) -> str:
        return f"Graph({self.direction}, {len(self.nodes)=})"

    def from_gdf(self, links) -> Self:
        """Takes a (Geo)DataFrame and add each row as an edge. Returns graph object."""
        for f in links.itertuples(index=False):
            self.add_edge(f.START_NODE, f.END_NODE, f.PIPE_ID)
        return self

    def from_dicts(self, links: list[dict]) -> Self:
        """Takes a list of dictionaries and add each row as an edge. Returns graph object."""
        for f in links:
            self.add_edge(f["START_NODE"], f["END_NODE"], f["PIPE_ID"])
        return self

    def add_edge(self, start_node, end_node, pipe_id) -> Self:
        """Add field values for a single feature as an edge. Returns graph object."""
        if self.direction == DIRECTION.U:
            self.nodes[end_node].append(start_node)
            self.pipes[end_node].append(pipe_id)
        elif self.direction == DIRECTION.D:
            self.nodes[start_node].append(end_node)
            self.pipes[start_node].append(pipe_id)
        else:
            msg = f"Graph direction {self.direction} is not valid. Use trace_sewer.DIRECTION.U or DIRECTION.D"
            raise NotImplementedError(msg)

        return self

    def to_file(self, filename: str):
        with open(filename, "w") as f:
            json.dump(self, f, cls=ExtendedEncoder, sort_keys=True)

    @classmethod
    def from_file(cls, filename: str) -> Self:
        with open(filename) as f:
            return json.load(f, cls=ExtendedDecoder)


class TraceResult:
    """
    Dataclass-like objects for accessing results of tracing.
    """

    def __init__(self, trace_summary, pipes: set, nodes: set, end_of_path_nodes: set):
        self.trace_summary = trace_summary
        self.pipes = pipes
        self.nodes = nodes
        self.end_of_path_nodes = end_of_path_nodes

    def __repr__(self):
        return f"TraceResult({self.trace_summary['direction']}, {self.trace_summary['start_node']})"


class Trace:
    """
    This class is used to trace a path through a graph. Option to provide a function that returns False to stop tracing.

    Args:
    - graph: The graph to be traced.
    - stop_node: Optional function to determine when to stop tracing.

    Methods:
    - trace(first_node): Traces a path through the graph starting from the first node.
    """

    def __init__(self, graph, stop_node: Callable | None = None):
        self.graph = graph
        self.stop_node = stop_node or (lambda x: True)

    def trace(self, first_node, trace_name=None, summary=False):
        """
        THis method tranverses graph object (depth-first) and returns a TraceResult
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
            elif next_node not in nodes_visited:
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
            trace_summary = None

        return TraceResult(
            trace_summary=trace_summary,
            pipes=pipes_visited,
            nodes=nodes_visited,
            end_of_path_nodes=end_of_path_nodes,
        )


class ExtendedEncoder(json.JSONEncoder):
    """
    Extends JSONEncoder to customize JSON serialization.

    Methods:
    - default(self, obj): Overrides default behavior for serializing objects and uses dynamic method lookup to encode the object.
    - encode_TraceResult(self, tr) -> dict[str, list]: Specifically encodes TraceResult objects into a dictionary.
    """

    def default(self, obj):
        name = obj.__class__.__name__

        try:
            encoder = getattr(self, f"encode_{name}")
        except AttributeError:
            super().default(obj)
        else:
            encoded = encoder(obj)
            encoded["__extended_json_type__"] = name
            return encoded

    def encode_defaultdict(self, obj):
        return {
            "__extended_json_type__": "defaultdict",
            "__default_factory__": obj.default_factory.__class__.__name__,
            "__dict__": dict(obj),
        }

    def encode_TraceResult(self, tr: TraceResult) -> dict[str, list]:  # noqa N802
        raise NotImplementedError

    def encode_DIRECTION(self, d: DIRECTION) -> dict[str, str]:  # noqa N802
        return {"__extended_json_type__": "DIRECTION", "_direction": d.value}

    def encode_Graph(self, g: Graph) -> dict[str, dict | list | str]:  # noqa N802
        return {
            "__extended_json_type__": "Graph",
            "_direction": self.default(g.direction),
            "_nodes": g.nodes,
            "_pipes": g.pipes,
        }


class ExtendedDecoder(json.JSONDecoder):
    def __init__(self, **kwargs):
        kwargs["object_hook"] = self.object_hook
        super().__init__(**kwargs)

    def object_hook(self, obj):
        try:
            name = obj["__extended_json_type__"]
            decoder = getattr(self, f"decode_{name}")
        except (KeyError, AttributeError, TypeError) as e:
            return obj
        else:
            return decoder(obj)

    def decode_TraceResult(self, tr: TraceResult) -> dict[str, list]:  # noqa N802
        raise NotImplementedError

    def decode_tuple(self, obj):
        return tuple(self.object_hook(element) for element in obj["value"])

    def decode_defaultdict(self, obj):
        return defaultdict(obj["__default_factory__"], map=self.object_hook(obj["__dict__"]))

    def decode_DIRECTION(self, obj):  # noqa N802
        return DIRECTION(obj["_direction"])

    def decode_Graph(self, g_dict: dict[str, list | dict]) -> dict[str, list]:  # noqa N802
        g = Graph(self.object_hook(g_dict["_direction"]))
        g.nodes = self.object_hook(g_dict["_nodes"])
        g.pipes = self.object_hook(g_dict["_pipes"])
        return g
