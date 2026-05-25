from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

from .parser import RegenSheet


@dataclass
class ValidationError:
    code: str
    subdir: Path | None
    message: str
    involved: list[str] = field(default_factory=list)


def build_graph(
    sheets: dict[str, RegenSheet],
) -> tuple[dict[str, list[str]], list[ValidationError]]:
    """
    Build dependency graph from sheets.
    Returns (graph, errors) where graph is {child_identity: [parent_identities]}.
    """
    graph = {}
    errors = []
    parent_identities = set(sheets.keys())

    for identity, sheet in sheets.items():
        parent_ids = []
        for parent_ref in sheet.parents:
            parent_id = parent_ref.value

            if parent_id == identity:
                errors.append(
                    ValidationError(
                        code="SELF_REFERENCE",
                        subdir=sheet.subdir,
                        message=f"Sheet {identity} references itself as a parent",
                        involved=[identity],
                    )
                )
                continue

            if parent_id not in parent_identities:
                errors.append(
                    ValidationError(
                        code="MISSING_PARENT",
                        subdir=sheet.subdir,
                        message=f"Parent '{parent_id}' not found in submission",
                        involved=[parent_id],
                    )
                )
                continue

            parent_ids.append(parent_id)

        graph[identity] = parent_ids

    return graph, errors


def topological_sort(
    graph: dict[str, list[str]],
) -> tuple[list[str], list[ValidationError]]:
    """
    Kahn's algorithm for topological sort.
    Returns (ordered_list, cycle_errors).
    If a cycle exists, returns partial order and error describing the cycle.
    """
    in_degree = defaultdict(int)
    all_nodes = set(graph.keys())

    for all_nodes_set in graph.values():
        for node in all_nodes_set:
            if node not in graph:
                graph[node] = []
            all_nodes.add(node)

    for node in all_nodes:
        if node not in graph:
            graph[node] = []

    for child, parents in graph.items():
        for _parent in parents:
            in_degree[child] += 1

    queue = deque([node for node in all_nodes if in_degree[node] == 0])
    topo_order = []

    while queue:
        node = queue.popleft()
        topo_order.append(node)

        for child, parents in graph.items():
            if node in parents:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

    errors = []
    if len(topo_order) != len(all_nodes):
        remaining = [n for n in all_nodes if in_degree[n] > 0]
        errors.append(
            ValidationError(
                code="CYCLE",
                subdir=None,
                message=f"Cycle detected in dependency graph: {remaining}",
                involved=remaining,
            )
        )
        return topo_order, errors

    return topo_order, errors
