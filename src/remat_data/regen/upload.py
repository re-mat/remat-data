from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from rich.console import Console

from ..config import config
from .parser import RegenSheet
from .validate import validate_directory


def _add_parent_url_column(
    sheet: RegenSheet,
    dataset_id_map: dict[str, str],
    space_id: str,
) -> None:
    """Append a 'Parent Dataset URL' column to the oligomers tab for each parent ref."""
    # Release any read-only file handle held from validation before writing
    if sheet.workbook_handle is not None:
        sheet.workbook_handle.close()
        sheet.workbook_handle = None

    wb = load_workbook(sheet.xlsx_path, data_only=False)
    ws = wb["oligomers"]

    url_col = 3  # column C — fixed position, overwrite if already present
    ws.cell(row=1, column=url_col).value = "Parent Dataset URL"

    for parent_ref in sheet.parents:
        row_num = int(parent_ref.cell[1:])
        dataset_id = dataset_id_map[parent_ref.value]
        url = (
            f"{config['clowder_base_url']}/{config['dataset_path']}"
            f"/{dataset_id}?space={space_id}"
        )
        ws.cell(row=row_num, column=url_col).value = url

    wb.save(sheet.xlsx_path)


def upload_regen_directory(
    submission_path: Path,
    clowder,
    space_id: str,
    console: Console | None = None,
) -> dict[str, str]:
    """
    Validate and upload a ReGen submission directory to Clowder.

    Experiments are uploaded in topological order (parents before children).
    For child experiments, a 'Parent Dataset URL' column is appended to the
    oligomers tab in the xlsx before uploading.

    Returns a mapping of experiment identity (directory name) → Clowder dataset ID.
    Returns an empty dict if validation fails.
    """
    if console is None:
        console = Console()

    report = validate_directory(submission_path)
    if not report.ok:
        console.print("[red bold]Validation failed — aborting upload.[/red bold]")
        for err in report.errors:
            console.print(f"  [red][{err.code}][/red] {err.message}")
        return {}

    report.print_human(console)

    dataset_id_map: dict[str, str] = {}

    for subdir in report.ordered_subdirs:
        identity = subdir.name
        sheet = report.sheets[identity]

        if not sheet.is_root:
            _add_parent_url_column(sheet, dataset_id_map, space_id)

        payload = {
            "name": identity,
            "description": "ReGen experiment uploaded by remat-data CLI",
            "space": [space_id],
            "collection": [],
        }
        resp = clowder.post("/datasets/createempty", payload)
        if not resp:
            console.print(f"[red]Failed to create dataset for {identity}[/red]")
            return dataset_id_map

        dataset_id = resp["id"]
        dataset_id_map[identity] = dataset_id

        for f in sorted(subdir.iterdir()):
            if f.is_file():
                file_id = clowder.post_file(f"/uploadToDataset/{dataset_id}", str(f))
                if not file_id:
                    console.print(
                        f"[yellow]Warning: failed to upload {f.name} for {identity}[/yellow]"
                    )

        url = (
            f"{config['clowder_base_url']}/{config['dataset_path']}"
            f"/{dataset_id}?space={space_id}"
        )
        console.print(f"  [green]✓[/green] {identity} → {url}")

    return dataset_id_map
