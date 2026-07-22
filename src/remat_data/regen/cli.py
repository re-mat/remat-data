from __future__ import annotations

from pathlib import Path

import typer
from pyclowder.client import ClowderClient
from rich.console import Console
from rich.table import Table

from ..config import config, space_map
from .identity import DirectoryNameResolver, FilenameStemResolver
from .upload import upload_regen_directory
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

    resolver = FilenameStemResolver() if id_mode == "file" else DirectoryNameResolver()

    report = validate_directory(submission_path, resolver=resolver)

    if json:
        console.print_json(data=report.to_dict())
    else:
        report.print_human(console)

    if not report.ok:
        raise typer.Exit(code=1)


@regen_app.command("upload", no_args_is_help=True)
def upload(
    directory: str = typer.Argument(..., help="Path to the ReGen submission directory"),
    space: str = typer.Option(
        ..., "--space", help="Clowder space name (e.g. 'Test') or raw space UUID"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Validate only; do not upload anything"
    ),
) -> None:
    """
    Validate and upload a ReGen bulk submission directory to Clowder.

    Experiments are uploaded in topological order (parents before children).
    For child experiments, a 'Parent Dataset URL' column is appended to the
    oligomers tab of the xlsx file before uploading.
    """
    submission_path = Path(directory)

    if not submission_path.exists():
        console.print(f"[red]Error: Path does not exist: {directory}[/red]")
        raise typer.Exit(code=1)

    if not submission_path.is_dir():
        console.print(f"[red]Error: Path is not a directory: {directory}[/red]")
        raise typer.Exit(code=1)

    space_id = space_map.get(space, space)

    if dry_run:
        report = validate_directory(submission_path)
        if report.ok:
            report.print_human(console)
        else:
            report.print_human(console)
            raise typer.Exit(code=1)
        return

    key_path = Path("clowder_key.txt")
    if not key_path.exists():
        console.print(
            "[red]Error: clowder_key.txt not found in current directory[/red]"
        )
        raise typer.Exit(code=1)

    key = key_path.read_text(encoding="utf-8").strip()
    clowder = ClowderClient(host=config["clowder_base_url"], key=key)

    console.print(f"Uploading to space: {space} ({space_id})")
    dataset_id_map = upload_regen_directory(submission_path, clowder, space_id, console)

    if not dataset_id_map:
        raise typer.Exit(code=1)

    table = Table(title="Upload Summary")
    table.add_column("Experiment", style="cyan")
    table.add_column("Dataset ID", style="magenta")
    table.add_column("URL", style="green")

    for identity, dataset_id in dataset_id_map.items():
        url = (
            f"{config['clowder_base_url']}/{config['dataset_path']}"
            f"/{dataset_id}?space={space_id}"
        )
        table.add_row(identity, dataset_id, url)

    console.print(table)
