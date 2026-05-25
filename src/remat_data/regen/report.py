from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from .graph import ValidationError
from .parser import RegenSheet


@dataclass
class ValidationReport:
    """Aggregates validation results including ordering, graph, and any errors."""

    ordered_subdirs: list[Path]
    graph: dict[str, list[str]]
    roots: list[str]
    sheets: dict[str, RegenSheet]
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "ordered_subdirs": [str(p) for p in self.ordered_subdirs],
            "graph": self.graph,
            "roots": self.roots,
            "errors": [
                {
                    "code": e.code,
                    "subdir": str(e.subdir) if e.subdir else None,
                    "message": e.message,
                    "involved": e.involved,
                }
                for e in self.errors
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def print_human(self, console: Console | None = None):
        if console is None:
            console = Console()

        if self.errors:
            console.print("[red bold]Validation Errors:[/red bold]")
            for err in self.errors:
                subdir_str = f" ({err.subdir})" if err.subdir else ""
                console.print(f"  [{err.code}]{subdir_str}: {err.message}")
        else:
            self._print_graph_tree(console)
            self._print_order_table(console)

    def _print_graph_tree(self, console: Console):
        root = Tree("[cyan]Dependency Graph[/cyan]")

        def add_children(tree_node, node_id, visited=None):
            if visited is None:
                visited = set()
            if node_id in visited:
                return
            visited.add(node_id)

            children = [c for c, ps in self.graph.items() if node_id in ps]
            for child in sorted(children):
                child_tree = tree_node.add(f"[green]{child}[/green]")
                add_children(child_tree, child, visited)

        for root_id in sorted(self.roots):
            root_tree = root.add(f"[yellow]{root_id}[/yellow] (root)")
            add_children(root_tree, root_id)

        console.print(root)

    def _print_order_table(self, console: Console):
        table = Table(title="Creation Order")
        table.add_column("Order", style="cyan")
        table.add_column("Subdirectory", style="magenta")
        table.add_column("Type", style="green")

        for idx, subdir in enumerate(self.ordered_subdirs, 1):
            identity = subdir.name
            is_root = identity in self.roots
            type_str = "[yellow]root[/yellow]" if is_root else "[blue]child[/blue]"
            table.add_row(str(idx), str(subdir), type_str)

        console.print(table)
