from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .identity import DirectoryNameResolver
from .validate import validate_directory

regen_app = typer.Typer(no_args_is_help=True)
console = Console()


@regen_app.command("validate", no_args_is_help=True)
def validate(
    directory: str = typer.Argument(..., help="Path to the ReGen submission directory"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
    id_mode: str = typer.Option(
        "dir", "--id-mode", help="Identity resolution mode: dir (directory name)"
    ),
) -> None:
    """
    Validate a ReGen bulk submission directory.

    Checks for:
    - Exactly one Data Entry_*.xlsx per subdirectory
    - Valid parent references (matching sibling subdirectories)
    - No cycles in the dependency graph
    - No self-references

    Outputs the dependency graph and creation order (parents before children).
    """
    submission_path = Path(directory)

    if not submission_path.exists():
        console.print(f"[red]Error: Path does not exist: {directory}[/red]")
        raise typer.Exit(code=1)

    if not submission_path.is_dir():
        console.print(f"[red]Error: Path is not a directory: {directory}[/red]")
        raise typer.Exit(code=1)

    resolver = DirectoryNameResolver()

    report = validate_directory(submission_path, resolver=resolver)

    if json:
        console.print_json(data=report.to_dict())
    else:
        report.print_human(console)

    if not report.ok:
        raise typer.Exit(code=1)
